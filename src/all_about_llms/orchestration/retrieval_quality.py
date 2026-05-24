import ipaddress
from uuid import UUID
from urllib.parse import urlparse

from all_about_llms.contracts import (
    ArtifactRecord,
    ArtifactType,
    ClaimSupportStatus,
    KnowledgeGraphCoverageEntry,
    RetrievalCandidateEntry,
    RetrievalQualityLedgerRequest,
    RetrievalQualityLedgerResult,
    RetrievalQualityStatus,
    RunEvent,
    SourceFreshnessStatus,
    SourceQualityStatus,
)
from all_about_llms.orchestration.source_quality import evaluate_source_quality
from all_about_llms.providers.interfaces import RerankCandidate, RerankRequest
from all_about_llms.providers.rerank import DeterministicRerankerProvider


_COMMON_TWO_PART_PUBLIC_SUFFIXES = {
    "ac.uk",
    "co.nz",
    "co.za",
    "co.in",
    "co.jp",
    "co.uk",
    "com.au",
    "com.br",
    "com.cn",
    "com.mx",
    "com.sg",
    "com.tr",
    "com.tw",
    "com.ua",
    "edu.au",
    "gov.au",
    "gov.in",
    "gov.uk",
    "net.au",
    "org.au",
    "org.uk",
}

_COMMON_COUNTRY_CODE_SECOND_LEVEL_LABELS = {
    "ac",
    "co",
    "com",
    "edu",
    "go",
    "gob",
    "gov",
    "mil",
    "ne",
    "net",
    "nom",
    "or",
    "org",
    "sch",
}


class RetrievalQualityLedgerError(RuntimeError):
    """Base error for retrieval quality ledger generation."""


class RetrievalQualityLedgerRunNotFoundError(RetrievalQualityLedgerError):
    """Raised when a run cannot be found for retrieval quality work."""


class RetrievalQualityLedgerWorkflow:
    """Build a durable retrieval, reranking, and graph coverage proof."""

    def __init__(self, store, reranker_provider=None):
        self._store = store
        self._reranker_provider = reranker_provider or DeterministicRerankerProvider()

    async def build(
        self, run_id: UUID, request: RetrievalQualityLedgerRequest
    ) -> RetrievalQualityLedgerResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise RetrievalQualityLedgerRunNotFoundError(f"Run not found: {run_id}")

        topic = request.topic or _topic_from_run(run)
        sources = await self._store.list_sources(run_id)
        claims = await self._store.list_claims(run_id)
        artifacts = await self._store.list_artifacts(run_id)

        candidates = await _candidate_entries(
            sources=sources,
            candidate_window=request.candidate_window,
            topic=topic,
            reranker_provider=self._reranker_provider,
        )
        accepted_source_ids = {
            candidate.source_id
            for candidate in candidates
            if candidate.accepted_for_context and candidate.source_id is not None
        }
        graph_coverage = _graph_coverage_entries(
            sources=sources,
            claims=claims,
            artifacts=artifacts,
            require_graph_coverage=request.require_graph_coverage,
            accepted_source_ids=accepted_source_ids,
        )
        graph_coverage.extend(
            _retrieval_diversity_gap_entries(
                candidates=candidates,
                min_accepted_sources=request.min_accepted_sources,
            )
        )
        graph_coverage.extend(
            _source_independence_gap_entries(
                candidates=candidates,
                min_accepted_sources=request.min_accepted_sources,
            )
        )
        accepted_candidate_count = sum(
            1 for candidate in candidates if candidate.accepted_for_context
        )
        precision_risk_count = sum(
            len(candidate.precision_risks) for candidate in candidates
        )
        recall_gap_count = _recall_gap_count(
            accepted_candidate_count=accepted_candidate_count,
            min_accepted_sources=request.min_accepted_sources,
            graph_coverage=graph_coverage,
        )
        coverage_gap_count = sum(
            1 for entry in graph_coverage if entry.coverage_status != "covered"
        )
        status = _status(
            candidate_count=len(candidates),
            accepted_candidate_count=accepted_candidate_count,
            min_accepted_sources=request.min_accepted_sources,
            precision_risk_count=precision_risk_count,
            recall_gap_count=recall_gap_count,
            require_reranking=request.require_reranking,
        )
        recommended_queries = _recommended_queries(
            topic=topic,
            accepted_candidate_count=accepted_candidate_count,
            min_accepted_sources=request.min_accepted_sources,
            graph_coverage=graph_coverage,
            candidates=candidates,
        )

        result = RetrievalQualityLedgerResult(
            run_id=run_id,
            topic=topic,
            status=status,
            candidate_count=len(candidates),
            accepted_candidate_count=accepted_candidate_count,
            reranked_candidate_count=len(candidates),
            graph_node_count=len(graph_coverage),
            precision_risk_count=precision_risk_count,
            recall_gap_count=recall_gap_count,
            coverage_gap_count=coverage_gap_count,
            recommended_queries=recommended_queries,
            candidates=candidates,
            graph_coverage=graph_coverage,
            summary=_summary(
                topic=topic,
                status=status,
                candidate_count=len(candidates),
                accepted_candidate_count=accepted_candidate_count,
                precision_risk_count=precision_risk_count,
                recall_gap_count=recall_gap_count,
                coverage_gap_count=coverage_gap_count,
            ),
        )

        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.RETRIEVAL_QUALITY_LEDGER,
                title=f"Retrieval quality ledger: {topic}",
                uri=f"artifact://runs/{run_id}/retrieval-quality-ledger",
                content=result.model_dump(
                    mode="json", exclude={"ledger_artifact_id", "event_id"}
                ),
                provenance={
                    "workflow": "retrieval_quality_ledger_v1",
                    "agent_id": "retrieval-intelligence-agent",
                    "knowledge_graph_agent_id": "knowledge-graph-curator-agent",
                    "candidate_window": request.candidate_window,
                    "min_accepted_sources": request.min_accepted_sources,
                    "require_reranking": request.require_reranking,
                    "require_graph_coverage": request.require_graph_coverage,
                },
                source_ids=[
                    candidate.source_id
                    for candidate in candidates
                    if candidate.source_id is not None
                ],
                revision_history=[
                    {
                        "actor": "retrieval-intelligence-agent",
                        "note": "Recorded hybrid retrieval, reranking, graph coverage, and FP/FN risk evidence.",
                    }
                ],
            )
            result.ledger_artifact_id = artifact.artifact_id
            artifact.content["ledger_artifact_id"] = str(artifact.artifact_id)
            await self._store.record_artifact(artifact)
            await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="artifact_recorded",
                    actor="artifact-librarian",
                    payload=artifact.model_dump(mode="json"),
                )
            )

        if hasattr(self._store, "record_retrieval_quality_result"):
            await self._store.record_retrieval_quality_result(result)

        event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="retrieval_quality_ledger_built",
                actor="retrieval-intelligence-agent",
                payload={
                    "topic": topic,
                    "status": result.status.value,
                    "candidate_count": result.candidate_count,
                    "accepted_candidate_count": result.accepted_candidate_count,
                    "reranked_candidate_count": result.reranked_candidate_count,
                    "graph_node_count": result.graph_node_count,
                    "precision_risk_count": result.precision_risk_count,
                    "recall_gap_count": result.recall_gap_count,
                    "coverage_gap_count": result.coverage_gap_count,
                    "ledger_artifact_id": (
                        str(result.ledger_artifact_id)
                        if result.ledger_artifact_id
                        else None
                    ),
                },
            )
        )
        result.event_id = event.event_id
        return result


async def _candidate_entries(
    *,
    sources,
    candidate_window: int,
    topic: str,
    reranker_provider,
) -> list[RetrievalCandidateEntry]:
    prepared = []
    rerank_candidates = []
    for index, source in enumerate(sources, start=1):
        quality = evaluate_source_quality(source)
        metadata = source.metadata or {}
        search_rank = int(metadata.get("search_rank") or index)
        candidate_id = f"source:{source.source_id}"
        prepared.append((candidate_id, search_rank, source, quality))
        rerank_candidates.append(
            RerankCandidate(
                candidate_id=candidate_id,
                title=source.title,
                url=str(source.url),
                snippet=metadata.get("snippet"),
                query=metadata.get("search_query"),
                retrievers=_retrievers(metadata),
                rank=search_rank,
                metadata={
                    "source_id": str(source.source_id),
                    "citation_id": source.citation_id,
                    "source_type": quality.source_type,
                    "quality_status": quality.quality_status.value,
                    "freshness_status": quality.freshness_status.value,
                    "search_rank": search_rank,
                    "has_published_at": source.published_at is not None,
                    "coverage_topics": _coverage_topics(source, metadata),
                },
            )
        )

    rerank_results = await reranker_provider.rerank(
        RerankRequest(
            query=topic,
            candidates=rerank_candidates,
            top_k=candidate_window,
            metadata={"workflow": "retrieval_quality_ledger_v1"},
        )
    )
    result_by_candidate_id = {
        result.candidate_id: result for result in rerank_results
    }
    prepared_by_candidate_id = {
        candidate_id: (search_rank, source, quality)
        for candidate_id, search_rank, source, quality in prepared
    }
    ordered_candidate_ids = [
        result.candidate_id
        for result in sorted(
            rerank_results,
            key=lambda item: (item.rank_after, -item.relevance_score),
        )
        if result.candidate_id in prepared_by_candidate_id
    ][:candidate_window]
    entries: list[RetrievalCandidateEntry] = []
    for fused_rank, candidate_id in enumerate(
        ordered_candidate_ids,
        start=1,
    ):
        result = result_by_candidate_id[candidate_id]
        _search_rank, source, quality = prepared_by_candidate_id[candidate_id]
        metadata = source.metadata or {}
        precision_risks = _precision_risks(
            source,
            quality,
            result.relevance_score,
        )
        recall_risks = _source_recall_risks(source, metadata)
        accepted = (
            not precision_risks
            and quality.quality_status
            in {SourceQualityStatus.STRONG, SourceQualityStatus.ACCEPTABLE}
            and quality.freshness_status != SourceFreshnessStatus.STALE
            and result.relevance_score >= 0.5
        )
        entries.append(
            RetrievalCandidateEntry(
                candidate_id=candidate_id,
                source_id=source.source_id,
                citation_id=source.citation_id,
                title=source.title,
                url=str(source.url),
                retrievers=_retrievers(metadata),
                query=metadata.get("search_query"),
                source_type=quality.source_type,
                fused_rank=fused_rank,
                rerank_score=result.relevance_score,
                reranker=str(
                    result.metadata.get("provider_id")
                    or type(reranker_provider).__name__
                ),
                rerank_reason=result.reason,
                accepted_for_context=accepted,
                quality_status=quality.quality_status,
                freshness_status=quality.freshness_status,
                precision_risks=precision_risks,
                recall_risks=recall_risks,
                coverage_topics=_coverage_topics(source, metadata),
            )
        )
    return entries


def _graph_coverage_entries(
    *,
    sources,
    claims,
    artifacts,
    require_graph_coverage: bool,
    accepted_source_ids: set[UUID],
) -> list[KnowledgeGraphCoverageEntry]:
    entries: list[KnowledgeGraphCoverageEntry] = []
    for source in sources:
        entries.append(
            KnowledgeGraphCoverageEntry(
                node_id=f"source:{source.source_id}",
                node_type="source",
                label=source.title,
                source_ids=[source.source_id],
                traversal_role="evidence_anchor",
                coverage_status="covered",
                notes="Source node anchors retrieved evidence to durable provenance.",
            )
        )
    for claim in claims:
        has_sources = bool(claim.source_ids)
        has_accepted_overlap = _has_accepted_source_overlap(
            claim.source_ids,
            accepted_source_ids,
        )
        covered = (
            claim.support_status == ClaimSupportStatus.SUPPORTED
            and has_sources
            and has_accepted_overlap
        )
        if covered:
            notes = "Claim has explicit source support from accepted retrieval evidence."
        elif (
            claim.support_status == ClaimSupportStatus.SUPPORTED
            and has_sources
            and not has_accepted_overlap
        ):
            notes = (
                "Claim has source support, but none of its source dependencies overlap "
                "accepted retrieval evidence from the latest retrieval ledger."
            )
        else:
            notes = "Claim needs source support or an unsupported label before final synthesis."
        entries.append(
            KnowledgeGraphCoverageEntry(
                node_id=f"claim:{claim.claim_id}",
                node_type="claim",
                label=claim.claim_text[:160],
                source_ids=claim.source_ids,
                claim_ids=[claim.claim_id],
                traversal_role="claim_support",
                coverage_status="covered" if covered else "gap",
                notes=notes,
            )
        )
    for artifact in artifacts:
        source_ids = artifact.source_ids or []
        claim_ids = _artifact_claim_ids(artifact)
        has_accepted_overlap = _has_accepted_source_overlap(
            source_ids,
            accepted_source_ids,
        )
        covered = bool(source_ids) and bool(claim_ids) and has_accepted_overlap
        if covered:
            notes = (
                "Artifact carries source and claim dependencies connected to "
                "accepted retrieval evidence."
            )
        elif source_ids and claim_ids and not has_accepted_overlap:
            notes = (
                "Artifact has source and claim dependencies, but its source path "
                "does not overlap accepted retrieval evidence."
            )
        else:
            notes = "Artifact is missing source or claim dependency coverage."
        entries.append(
            KnowledgeGraphCoverageEntry(
                node_id=f"artifact:{artifact.artifact_id}",
                node_type="artifact",
                label=artifact.title,
                source_ids=source_ids,
                claim_ids=claim_ids,
                traversal_role="artifact_dependency",
                coverage_status="covered" if covered else "gap",
                notes=notes,
            )
        )
    if require_graph_coverage and not entries:
        entries.append(
            KnowledgeGraphCoverageEntry(
                node_id="graph:empty",
                node_type="graph",
                label="No graph evidence",
                traversal_role="coverage_gate",
                coverage_status="gap",
                notes="No source, claim, or artifact nodes exist for graph traversal.",
            )
        )
    return entries


def _has_accepted_source_overlap(
    source_ids: list[UUID],
    accepted_source_ids: set[UUID],
) -> bool:
    return any(source_id in accepted_source_ids for source_id in source_ids)


def _artifact_claim_ids(artifact) -> list[UUID]:
    raw_claim_ids = [
        *_raw_id_values(artifact.content.get("claim_dependency_ids")),
        *_raw_id_values(artifact.content.get("claim_ids")),
        *_raw_id_values(artifact.provenance.get("claim_ids")),
    ]
    claim_ids: list[UUID] = []
    for raw_claim_id in raw_claim_ids:
        try:
            claim_id = UUID(str(raw_claim_id))
        except (TypeError, ValueError):
            continue
        if claim_id not in claim_ids:
            claim_ids.append(claim_id)
    return claim_ids


def _raw_id_values(value) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _retrieval_diversity_gap_entries(
    *,
    candidates: list[RetrievalCandidateEntry],
    min_accepted_sources: int,
) -> list[KnowledgeGraphCoverageEntry]:
    accepted = [candidate for candidate in candidates if candidate.accepted_for_context]
    if min_accepted_sources <= 1 or len(accepted) < min_accepted_sources:
        return []

    missing_metadata = any(
        "missing_search_query" in candidate.recall_risks
        or "unknown_retriever" in candidate.recall_risks
        for candidate in accepted
    )
    if missing_metadata:
        for candidate in accepted:
            if (
                "missing_search_query" in candidate.recall_risks
                or "unknown_retriever" in candidate.recall_risks
            ) and "unproven_query_retriever_diversity" not in candidate.recall_risks:
                candidate.recall_risks.append(
                    "unproven_query_retriever_diversity"
                )
        return [
            _retrieval_diversity_gap_entry(
                node_id="retrieval_diversity:metadata",
                label="Unproven query and retriever diversity",
                accepted=accepted,
                notes=(
                    "Accepted context sources are missing query or retriever metadata; "
                    "add explicit query/retriever proof before treating recall coverage "
                    "as complete."
                ),
            )
        ]

    query_signatures = {
        _normalized_signature(candidate.query)
        for candidate in accepted
    }
    retriever_signatures = set()
    for candidate in accepted:
        for retriever in candidate.retrievers:
            normalized = _normalized_signature(retriever)
            if normalized:
                retriever_signatures.add(normalized)
    if len(query_signatures) != 1 or len(retriever_signatures) != 1:
        return []

    for candidate in accepted:
        if "single_query_single_retriever_cluster" not in candidate.recall_risks:
            candidate.recall_risks.append("single_query_single_retriever_cluster")

    return [
        _retrieval_diversity_gap_entry(
            node_id="retrieval_diversity:query_retriever",
            label="Single query and retriever evidence cluster",
            accepted=accepted,
            notes=(
                "Accepted context sources came from a single query and retriever"
                f"{_accepted_host_note(accepted)}; add independent retrieval queries or another retrieval "
                "signal before treating recall coverage as complete."
            ),
        )
    ]


def _retrieval_diversity_gap_entry(
    *,
    node_id: str,
    label: str,
    accepted: list[RetrievalCandidateEntry],
    notes: str,
) -> KnowledgeGraphCoverageEntry:
    return KnowledgeGraphCoverageEntry(
        node_id=node_id,
        node_type="retrieval_diversity",
        label=label,
        source_ids=[
            candidate.source_id
            for candidate in accepted
            if candidate.source_id is not None
        ],
        traversal_role="retrieval_diversity_gate",
        coverage_status="gap",
        notes=notes,
    )


def _source_independence_gap_entries(
    *,
    candidates: list[RetrievalCandidateEntry],
    min_accepted_sources: int,
) -> list[KnowledgeGraphCoverageEntry]:
    accepted = [candidate for candidate in candidates if candidate.accepted_for_context]
    if min_accepted_sources <= 1 or len(accepted) < min_accepted_sources:
        return []
    hosts = {
        _source_host(candidate.url)
        for candidate in accepted
        if _source_host(candidate.url)
    }
    if len(hosts) != 1:
        return []

    for candidate in accepted:
        if "single_host_source_cluster" not in candidate.recall_risks:
            candidate.recall_risks.append("single_host_source_cluster")

    host = next(iter(hosts))
    return [
        KnowledgeGraphCoverageEntry(
            node_id="source_independence:host",
            node_type="source_independence",
            label="Single-host accepted evidence cluster",
            source_ids=[
                candidate.source_id
                for candidate in accepted
                if candidate.source_id is not None
            ],
            traversal_role="source_independence_gate",
            coverage_status="gap",
            notes=(
                "Accepted context sources came from one host "
                f"({host}); add an independently hosted source before treating "
                "recall coverage as complete."
            ),
        )
    ]


def _accepted_host_note(accepted: list[RetrievalCandidateEntry]) -> str:
    hosts = sorted(
        {
            _source_host(candidate.url)
            for candidate in accepted
            if candidate.url
        }
    )
    return f" across {len(hosts)} host(s)" if hosts else ""


def _normalized_signature(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _source_host(url: str | None) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    try:
        host = parsed.hostname
    except ValueError:
        host = ""
    host = host or parsed.netloc
    return _registrable_domain(host)


def _registrable_domain(host: str | None) -> str:
    normalized = str(host or "").strip().lower().rstrip(".")
    if normalized.startswith("[") and "]" in normalized:
        normalized = normalized[1 : normalized.index("]")]
    if "@" in normalized:
        normalized = normalized.rsplit("@", 1)[1]
    while normalized.startswith("www."):
        normalized = normalized.removeprefix("www.")
    if not normalized:
        return ""
    if ":" in normalized and normalized.count(":") == 1:
        host_part, port_part = normalized.rsplit(":", 1)
        if port_part.isdigit():
            normalized = host_part
    try:
        return str(ipaddress.ip_address(normalized))
    except ValueError:
        pass
    labels = [label for label in normalized.split(".") if label]
    if len(labels) <= 2:
        return normalized
    second_level = labels[-2]
    top_level = labels[-1]
    suffix = f"{second_level}.{top_level}"
    has_country_code_second_level = (
        len(top_level) == 2
        and second_level in _COMMON_COUNTRY_CODE_SECOND_LEVEL_LABELS
    )
    if (
        suffix in _COMMON_TWO_PART_PUBLIC_SUFFIXES
        or has_country_code_second_level
    ) and len(labels) >= 3:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def _precision_risks(source, quality, score: float) -> list[str]:
    metadata = source.metadata or {}
    risks = _contradiction_precision_risks(metadata)
    if quality.quality_status == SourceQualityStatus.WEAK:
        risks.append("weak_source_quality")
    if quality.quality_status == SourceQualityStatus.NEEDS_REVIEW:
        risks.append("source_quality_needs_review")
    if quality.freshness_status == SourceFreshnessStatus.STALE:
        risks.append("stale_source")
    if quality.freshness_status == SourceFreshnessStatus.UNKNOWN:
        risks.append("unknown_freshness")
    if source.published_at is None:
        risks.append("missing_published_at")
    if score < 0.5:
        risks.append("low_rerank_score")
    return risks


def _contradiction_precision_risks(metadata: dict) -> list[str]:
    risks: list[str] = []
    contradiction_status = _normalized_signature(metadata.get("contradiction_status"))
    if contradiction_status in {"contradicts", "conflicts", "conflicting", "refutes"}:
        risks.append("contradictory_source")
    if _metadata_bool(metadata.get("contradicts")):
        risks.append("contradictory_source")
    if _valid_uuid_values(
        [
            *_raw_id_values(metadata.get("contradicts_claim_ids")),
            *_raw_id_values(metadata.get("contradiction_claim_ids")),
        ]
    ):
        risks.append("contradicts_supported_claim")
    if _normalized_signature(metadata.get("contradiction_review")) in {
        "needed",
        "needs_review",
        "required",
    }:
        risks.append("contradiction_review_required")
    return list(dict.fromkeys(risks))


def _metadata_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"", "false", "0", "no", "n", "off"}:
            return False
    return False


def _valid_uuid_values(values: list) -> list[UUID]:
    uuids: list[UUID] = []
    for value in values:
        try:
            parsed = UUID(str(value))
        except (TypeError, ValueError):
            continue
        if parsed not in uuids:
            uuids.append(parsed)
    return uuids


def _source_recall_risks(source, metadata: dict) -> list[str]:
    risks = []
    if not metadata.get("snippet"):
        risks.append("missing_snippet")
    if not metadata.get("search_query"):
        risks.append("missing_search_query")
    if not metadata.get("retriever") and not metadata.get("retrievers"):
        risks.append("unknown_retriever")
    return risks


def _retrievers(metadata: dict) -> list[str]:
    retrievers = metadata.get("retrievers")
    if isinstance(retrievers, list) and retrievers:
        return [str(retriever) for retriever in retrievers]
    retriever = metadata.get("retriever") or metadata.get("provider")
    if retriever:
        return [str(retriever)]
    if metadata.get("search_query"):
        return ["web_search"]
    return ["source_ledger"]


def _coverage_topics(source, metadata: dict) -> list[str]:
    topics = metadata.get("coverage_topics")
    if isinstance(topics, list) and topics:
        return [str(topic) for topic in topics]
    query = metadata.get("search_query")
    if query:
        return [str(query)]
    return [source.title]


def _recall_gap_count(
    *,
    accepted_candidate_count: int,
    min_accepted_sources: int,
    graph_coverage: list[KnowledgeGraphCoverageEntry],
) -> int:
    source_gap = max(min_accepted_sources - accepted_candidate_count, 0)
    graph_gaps = sum(1 for entry in graph_coverage if entry.coverage_status != "covered")
    return source_gap + graph_gaps


def _status(
    *,
    candidate_count: int,
    accepted_candidate_count: int,
    min_accepted_sources: int,
    precision_risk_count: int,
    recall_gap_count: int,
    require_reranking: bool,
) -> RetrievalQualityStatus:
    if candidate_count == 0 or accepted_candidate_count == 0:
        return RetrievalQualityStatus.BLOCKED
    if accepted_candidate_count < min_accepted_sources or recall_gap_count:
        return RetrievalQualityStatus.NEEDS_MORE_RECALL
    if require_reranking and precision_risk_count:
        return RetrievalQualityStatus.NEEDS_RERANK
    return RetrievalQualityStatus.READY


def _recommended_queries(
    *,
    topic: str,
    accepted_candidate_count: int,
    min_accepted_sources: int,
    graph_coverage: list[KnowledgeGraphCoverageEntry],
    candidates: list[RetrievalCandidateEntry],
) -> list[str]:
    queries: list[str] = []
    if accepted_candidate_count < min_accepted_sources:
        queries.append(f"{topic} official source latest")
        queries.append(f"{topic} benchmark data primary source")
    if any(
        entry.node_type == "retrieval_diversity"
        and entry.coverage_status != "covered"
        for entry in graph_coverage
    ):
        queries.append(f"{topic} independent corroborating sources")
        queries.append(f"{topic} alternate search query primary evidence")
    if any(
        entry.node_type == "source_independence"
        and entry.coverage_status != "covered"
        for entry in graph_coverage
    ):
        queries.append(f"{topic} independent source corroboration")
    if any(entry.node_type == "claim" and entry.coverage_status != "covered" for entry in graph_coverage):
        queries.append(f"{topic} claims evidence verification")
    if any(
        any("contradict" in risk for risk in candidate.precision_risks)
        for candidate in candidates
    ):
        queries.append(f"{topic} contradictory evidence review")
    if any("unknown_freshness" in candidate.precision_risks for candidate in candidates):
        queries.append(f"{topic} publication date source")
    if not queries:
        queries.append(f"{topic} contradictory evidence")
    return queries


def _topic_from_run(run) -> str:
    topic = (run.conversation_state or {}).get("topic")
    if topic:
        return str(topic)
    prefix = "Create source-backed content about "
    if run.goal.startswith(prefix):
        return run.goal.removeprefix(prefix)
    return run.goal


def _summary(
    *,
    topic: str,
    status: RetrievalQualityStatus,
    candidate_count: int,
    accepted_candidate_count: int,
    precision_risk_count: int,
    recall_gap_count: int,
    coverage_gap_count: int,
) -> str:
    return (
        f"Retrieval quality for '{topic}' is {status.value}: "
        f"{accepted_candidate_count}/{candidate_count} candidate(s) accepted, "
        f"{precision_risk_count} precision risk(s), "
        f"{recall_gap_count} recall gap(s), and "
        f"{coverage_gap_count} graph coverage gap(s)."
    )
