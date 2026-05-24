import asyncio
import json
from pathlib import Path
from typing import Any

from all_about_llms.providers.interfaces import (
    ProviderConfigurationError,
    RerankCandidate,
    RerankRequest,
    RerankResult,
)


class DeterministicRerankerProvider:
    """Local reranker used when no external reranking provider is configured."""

    provider_id = "deterministic_source_quality_v1"

    async def rerank(self, request: RerankRequest) -> list[RerankResult]:
        scored = [
            (_score_candidate(candidate), candidate.rank, candidate)
            for candidate in request.candidates
        ]
        scored.sort(key=lambda item: (-item[0], item[1], item[2].candidate_id))
        if request.top_k is not None:
            scored = scored[: request.top_k]
        return [
            RerankResult(
                candidate_id=candidate.candidate_id,
                rank_before=candidate.rank,
                rank_after=rank_after,
                relevance_score=score,
                reason=_reason(candidate, score),
                metadata={
                    "provider_id": self.provider_id,
                    "quality_status": candidate.metadata.get("quality_status"),
                    "freshness_status": candidate.metadata.get("freshness_status"),
                    "search_rank": candidate.metadata.get("search_rank"),
                    "has_snippet": bool(candidate.snippet),
                    "has_published_at": bool(candidate.metadata.get("has_published_at")),
                },
            )
            for rank_after, (score, _rank_before, candidate) in enumerate(
                scored,
                start=1,
            )
        ]


def _score_candidate(candidate: RerankCandidate) -> float:
    metadata = candidate.metadata or {}
    quality_status = str(metadata.get("quality_status") or "needs_review")
    freshness_status = str(metadata.get("freshness_status") or "unknown")
    score = {
        "strong": 0.86,
        "acceptable": 0.7,
        "needs_review": 0.48,
        "weak": 0.22,
    }.get(quality_status, 0.48)
    if freshness_status == "current":
        score += 0.06
    elif freshness_status == "evergreen":
        score += 0.04
    elif freshness_status == "unknown":
        score -= 0.08
    elif freshness_status == "stale":
        score -= 0.22
    if candidate.snippet:
        score += 0.04
    if metadata.get("has_published_at"):
        score += 0.04
    search_rank = int(metadata.get("search_rank") or candidate.rank)
    score -= min(max(search_rank - 1, 0), 20) * 0.01
    return max(0.0, min(1.0, round(score, 3)))


def _reason(candidate: RerankCandidate, score: float) -> str:
    metadata = candidate.metadata or {}
    reasons = [
        f"quality={metadata.get('quality_status') or 'unknown'}",
        f"freshness={metadata.get('freshness_status') or 'unknown'}",
    ]
    if candidate.snippet:
        reasons.append("snippet")
    if metadata.get("has_published_at"):
        reasons.append("published_at")
    if score < 0.5:
        reasons.append("low_score")
    return "; ".join(reasons)


class RustRetrievalRankerProvider:
    """Subprocess adapter for the Rust retrieval-ranker service boundary."""

    provider_id = "rust_retrieval_ranker_v1"

    def __init__(
        self,
        binary_path: str | Path,
        timeout_seconds: float = 2.0,
    ) -> None:
        self.binary_path = Path(binary_path)
        self.timeout_seconds = timeout_seconds

    async def rerank(self, request: RerankRequest) -> list[RerankResult]:
        if not self.binary_path.exists():
            raise ProviderConfigurationError(
                f"Rust retrieval ranker binary not found: {self.binary_path}"
            )

        payload = _build_rust_rank_payload(request)
        process = await asyncio.create_subprocess_exec(
            str(self.binary_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(json.dumps(payload).encode("utf-8")),
                timeout=self.timeout_seconds,
            )
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise RuntimeError(
                f"Rust retrieval ranker timed out after {self.timeout_seconds}s"
            ) from exc

        if process.returncode != 0:
            raise RuntimeError(
                "Rust retrieval ranker failed: "
                f"{stderr.decode('utf-8', errors='replace').strip()}"
            )

        try:
            response = json.loads(stdout.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError("Rust retrieval ranker returned invalid JSON") from exc

        if response.get("kind") != "rank":
            raise RuntimeError(
                f"Rust retrieval ranker returned unexpected response: {response.get('kind')}"
            )

        candidates = {candidate.candidate_id: candidate for candidate in request.candidates}
        diagnostics = response.get("diagnostics", {})
        results: list[RerankResult] = []
        for item in response.get("results", []):
            candidate_id = str(item["id"])
            candidate = candidates[candidate_id]
            explanation = item.get("explanation", {})
            results.append(
                RerankResult(
                    candidate_id=candidate_id,
                    rank_before=candidate.rank,
                    rank_after=int(item["rank"]),
                    relevance_score=float(item["score"]),
                    reason=_rust_reason(explanation),
                    metadata={
                        "provider_id": self.provider_id,
                        "rust_diagnostics": diagnostics,
                        "rust_explanation": explanation,
                        "source_uri": item.get("source_uri"),
                        **(item.get("metadata") or {}),
                    },
                )
            )
        return results


def _build_rust_rank_payload(request: RerankRequest) -> dict[str, Any]:
    config = {
        "limit": request.top_k or len(request.candidates) or 20,
    }
    scoring_config = request.metadata.get("scoring_config")
    if isinstance(scoring_config, dict):
        for key in (
            "vector_weight",
            "lexical_weight",
            "graph_weight",
            "authority_weight",
            "freshness_weight",
            "limit",
        ):
            if key in scoring_config:
                config[key] = scoring_config[key]

    return {
        "kind": "rank",
        "request_id": str(request.metadata.get("request_id") or ""),
        "query": request.query,
        "config": config,
        "candidates": [
            {
                "id": candidate.candidate_id,
                "title": candidate.title,
                "text": candidate.snippet or candidate.title,
                "source_uri": candidate.url,
                "metadata": _string_metadata(candidate.metadata),
                "signals": {
                    "vector_score": _optional_float(candidate.metadata, "vector_score"),
                    "lexical_score": _optional_float(candidate.metadata, "lexical_score"),
                    "graph_distance": _optional_int(candidate.metadata, "graph_distance"),
                    "authority": _optional_float(candidate.metadata, "authority"),
                    "freshness_days": _optional_int(candidate.metadata, "freshness_days"),
                },
            }
            for candidate in request.candidates
        ],
    }


def _string_metadata(metadata: dict[str, Any]) -> dict[str, str]:
    return {
        str(key): json.dumps(value, sort_keys=True)
        if isinstance(value, (dict, list))
        else str(value)
        for key, value in metadata.items()
        if value is not None
    }


def _optional_float(metadata: dict[str, Any], key: str) -> float | None:
    value = metadata.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(metadata: dict[str, Any], key: str) -> int | None:
    value = metadata.get(key)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _rust_reason(explanation: dict[str, Any]) -> str:
    if not explanation:
        return "rust weighted score"
    parts = [
        f"vector={float(explanation.get('vector_component', 0.0)):.3f}",
        f"lexical={float(explanation.get('lexical_component', 0.0)):.3f}",
        f"graph={float(explanation.get('graph_component', 0.0)):.3f}",
        f"authority={float(explanation.get('authority_component', 0.0)):.3f}",
        f"freshness={float(explanation.get('freshness_component', 0.0)):.3f}",
    ]
    return "rust weighted score; " + "; ".join(parts)
