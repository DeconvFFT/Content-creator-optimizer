from dataclasses import dataclass
from typing import Any
from uuid import UUID

from all_about_llms.contracts import ArtifactRecord, ArtifactType


@dataclass(frozen=True)
class AcceptedRetrievalEvidence:
    candidate_id: str
    source_id: UUID
    citation_id: str | None
    title: str
    url: str | None
    fused_rank: int | None
    rerank_score: float | None
    reranker: str | None
    rerank_reason: str | None
    precision_risks: tuple[str, ...]
    recall_risks: tuple[str, ...]
    coverage_topics: tuple[str, ...]
    ledger_artifact_id: UUID | None
    ledger_status: str | None


def latest_retrieval_quality_ledger(
    artifacts: list[ArtifactRecord],
) -> ArtifactRecord | None:
    ledgers = [
        artifact
        for artifact in artifacts
        if artifact.artifact_type == ArtifactType.RETRIEVAL_QUALITY_LEDGER
    ]
    if not ledgers:
        return None
    return max(ledgers, key=lambda artifact: artifact.created_at)


def retrieval_quality_ledger_status(ledger: ArtifactRecord | None) -> str | None:
    if ledger is None:
        return None
    status = ledger.content.get("status")
    if status is None:
        return None
    text = str(status).strip()
    return text or None


def retrieval_quality_ledger_ready(ledger: ArtifactRecord | None) -> bool:
    return retrieval_quality_ledger_status(ledger) == "ready"


def retrieval_quality_source_evidence_ready(
    ledger: ArtifactRecord | None,
) -> bool:
    if ledger is None:
        return False
    if retrieval_quality_ledger_ready(ledger):
        return True
    status = retrieval_quality_ledger_status(ledger)
    if status in {None, "blocked"}:
        return False

    accepted_count = _int_or_none(ledger.content.get("accepted_candidate_count")) or 0
    min_accepted = _int_or_none(ledger.provenance.get("min_accepted_sources")) or 1
    if accepted_count < min_accepted:
        return False
    candidates = ledger.content.get("candidates", [])
    if not isinstance(candidates, list):
        return False
    for candidate in candidates:
        if not isinstance(candidate, dict) or not candidate.get("accepted_for_context"):
            continue
        if _string_tuple(candidate.get("precision_risks", [])):
            return False
        recall_risks = _string_tuple(candidate.get("recall_risks", []))
        if any(
            risk
            in {
                "single_query_single_retriever_cluster",
                "unproven_query_retriever_diversity",
                "single_host_source_cluster",
            }
            for risk in recall_risks
        ):
            return False

    graph_coverage = ledger.content.get("graph_coverage", [])
    if not isinstance(graph_coverage, list):
        return False
    source_evidence_gap_types = {
        "graph",
        "retrieval_diversity",
        "source_independence",
    }
    for entry in graph_coverage:
        if not isinstance(entry, dict):
            continue
        if entry.get("coverage_status") == "covered":
            continue
        if entry.get("node_type") in source_evidence_gap_types:
            return False
    return accepted_count > 0


def accepted_retrieval_evidence_by_source(
    artifacts: list[ArtifactRecord],
    *,
    require_ready: bool = True,
) -> dict[UUID, AcceptedRetrievalEvidence]:
    ledger = latest_retrieval_quality_ledger(artifacts)
    if ledger is None:
        return {}
    if require_ready and not retrieval_quality_source_evidence_ready(ledger):
        return {}

    accepted: dict[UUID, AcceptedRetrievalEvidence] = {}
    candidates = ledger.content.get("candidates", [])
    if not isinstance(candidates, list):
        return accepted

    for candidate in candidates:
        evidence = _accepted_evidence_from_candidate(candidate, ledger)
        if evidence is None:
            continue
        current = accepted.get(evidence.source_id)
        if current is None or _evidence_sort_key(evidence) < _evidence_sort_key(current):
            accepted[evidence.source_id] = evidence

    return dict(sorted(accepted.items(), key=lambda item: _evidence_sort_key(item[1])))


def accepted_retrieval_source_ids(
    artifacts: list[ArtifactRecord],
    *,
    allowed_source_ids: list[UUID] | None = None,
) -> list[UUID]:
    evidence_by_source_id = accepted_retrieval_evidence_by_source(artifacts)
    if not evidence_by_source_id:
        return []
    allowed = set(allowed_source_ids or evidence_by_source_id.keys())
    return [
        source_id
        for source_id in evidence_by_source_id
        if source_id in allowed
    ]


def order_sources_by_retrieval_evidence(
    sources: list[Any],
    artifacts: list[ArtifactRecord],
) -> tuple[list[Any], dict[UUID, AcceptedRetrievalEvidence], bool]:
    evidence_by_source_id = accepted_retrieval_evidence_by_source(artifacts)
    if not evidence_by_source_id:
        return sources, {}, False

    source_by_id = {source.source_id: source for source in sources}
    accepted_sources = [
        source_by_id[source_id]
        for source_id in evidence_by_source_id
        if source_id in source_by_id
    ]
    remaining_sources = [
        source
        for source in sources
        if source.source_id not in evidence_by_source_id
    ]
    return [*accepted_sources, *remaining_sources], evidence_by_source_id, bool(
        accepted_sources
    )


def retrieval_evidence_payload(
    evidence: AcceptedRetrievalEvidence,
) -> dict[str, Any]:
    return {
        "candidate_id": evidence.candidate_id,
        "source_id": str(evidence.source_id),
        "citation_id": evidence.citation_id,
        "title": evidence.title,
        "url": evidence.url,
        "fused_rank": evidence.fused_rank,
        "rerank_score": evidence.rerank_score,
        "reranker": evidence.reranker,
        "rerank_reason": evidence.rerank_reason,
        "precision_risks": list(evidence.precision_risks),
        "recall_risks": list(evidence.recall_risks),
        "coverage_topics": list(evidence.coverage_topics),
        "ledger_artifact_id": (
            str(evidence.ledger_artifact_id) if evidence.ledger_artifact_id else None
        ),
        "ledger_status": evidence.ledger_status,
    }


def retrieval_evidence_payloads_for_source_ids(
    source_ids: list[UUID],
    evidence_by_source_id: dict[UUID, AcceptedRetrievalEvidence],
) -> list[dict[str, Any]]:
    return [
        retrieval_evidence_payload(evidence_by_source_id[source_id])
        for source_id in source_ids
        if source_id in evidence_by_source_id
    ]


def _accepted_evidence_from_candidate(
    candidate: Any,
    ledger: ArtifactRecord,
) -> AcceptedRetrievalEvidence | None:
    if not isinstance(candidate, dict):
        return None
    if not candidate.get("accepted_for_context"):
        return None
    source_id = _uuid_or_none(candidate.get("source_id"))
    if source_id is None:
        return None
    return AcceptedRetrievalEvidence(
        candidate_id=str(candidate.get("candidate_id") or f"source:{source_id}"),
        source_id=source_id,
        citation_id=_string_or_none(candidate.get("citation_id")),
        title=str(candidate.get("title") or "Untitled source"),
        url=_string_or_none(candidate.get("url")),
        fused_rank=_int_or_none(candidate.get("fused_rank")),
        rerank_score=_float_or_none(candidate.get("rerank_score")),
        reranker=_string_or_none(candidate.get("reranker")),
        rerank_reason=_string_or_none(candidate.get("rerank_reason")),
        precision_risks=_string_tuple(candidate.get("precision_risks", [])),
        recall_risks=_string_tuple(candidate.get("recall_risks", [])),
        coverage_topics=_string_tuple(candidate.get("coverage_topics", [])),
        ledger_artifact_id=ledger.artifact_id,
        ledger_status=_string_or_none(ledger.content.get("status")),
    )


def _evidence_sort_key(evidence: AcceptedRetrievalEvidence) -> tuple[int, float, str]:
    rank = evidence.fused_rank if evidence.fused_rank is not None else 999_999
    score = -(evidence.rerank_score if evidence.rerank_score is not None else 0.0)
    return (rank, score, evidence.candidate_id)


def _uuid_or_none(value: Any) -> UUID | None:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if str(item).strip())
