from uuid import UUID

from all_about_llms.contracts import (
    ArtifactRecord,
    ArtifactType,
    ClaimSupportStatus,
    RunEvent,
    SourceLedgerClaimSourceMatrixEntry,
    SourceFreshnessStatus,
    SourceLedgerArtifactEntry,
    SourceLedgerClaimEntry,
    SourceLedgerSnapshotRequest,
    SourceLedgerSnapshotResult,
    SourceLedgerSourceEntry,
    SourceQualityStatus,
)
from all_about_llms.orchestration.retrieval_evidence import (
    accepted_retrieval_evidence_by_source,
    latest_retrieval_quality_ledger,
    retrieval_quality_ledger_status,
)
from all_about_llms.orchestration.source_quality import evaluate_source_quality


class SourceLedgerError(RuntimeError):
    """Base error for source ledger snapshot generation."""


class SourceLedgerRunNotFoundError(SourceLedgerError):
    """Raised when a run cannot be found for source ledger work."""


class SourceLedgerWorkflow:
    """Build a consolidated source, claim, and artifact provenance snapshot."""

    def __init__(self, store):
        self._store = store

    async def build(
        self, run_id: UUID, request: SourceLedgerSnapshotRequest
    ) -> SourceLedgerSnapshotResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise SourceLedgerRunNotFoundError(f"Run not found: {run_id}")

        sources = await self._store.list_sources(run_id)
        claims = await self._store.list_claims(run_id)
        all_artifacts = await self._store.list_artifacts(run_id)
        retrieval_ledger = latest_retrieval_quality_ledger(all_artifacts)
        retrieval_evidence_by_source_id = accepted_retrieval_evidence_by_source(
            all_artifacts
        )
        artifacts = [
            artifact
            for artifact in all_artifacts
            if artifact.artifact_type
            not in {
                ArtifactType.SOURCE_LEDGER,
                ArtifactType.ARTIFACT_INDEX,
                ArtifactType.CONVERSATION_HANDOFF,
                ArtifactType.CONTEXT_PACKET,
                ArtifactType.RUN_RESUME_PLAN,
                ArtifactType.CLAIM_REVISION_PLAN,
                ArtifactType.CLAIM_REVISION_LEDGER,
                ArtifactType.RUN_REPLAY_LEDGER,
                ArtifactType.RUNTIME_HEALTH_LEDGER,
                ArtifactType.MODEL_ROUTING_LEDGER,
                ArtifactType.PROVIDER_OPERATIONS_LEDGER,
                ArtifactType.FOUNDATION_AUDIT,
                ArtifactType.RESEARCH_FRESHNESS_LEDGER,
                ArtifactType.RETRIEVAL_QUALITY_LEDGER,
                ArtifactType.MULTIMODAL_INTAKE_LEDGER,
                ArtifactType.MULTIMODAL_REVIEW,
                ArtifactType.HTML_NOTE,
                ArtifactType.OBSIDIAN_NOTE,
                ArtifactType.OBSIDIAN_MEMORY_PROMOTION,
            }
        ]

        source_by_id = {source.source_id: source for source in sources}
        claim_by_id = {claim.claim_id: claim for claim in claims}
        source_entries = [
            _source_entry_with_retrieval_evidence(
                evaluate_source_quality(source),
                retrieval_evidence_by_source_id.get(source.source_id),
            )
            for source in sources
        ]
        source_entry_by_id = {entry.source_id: entry for entry in source_entries}
        accepted_retrieval_source_count = sum(
            1 for entry in source_entries if entry.accepted_for_context
        )

        claim_entries = [
            SourceLedgerClaimEntry(
                claim_id=claim.claim_id,
                claim_text=claim.claim_text,
                support_status=claim.support_status,
                source_ids=claim.source_ids,
                source_citation_ids=[
                    source_by_id[source_id].citation_id
                    for source_id in claim.source_ids
                    if source_id in source_by_id
                ],
                missing_source_ids=[
                    source_id
                    for source_id in claim.source_ids
                    if source_id not in source_by_id
                ],
                reviewer_agent_id=claim.reviewer_agent_id,
                notes=claim.notes,
            )
            for claim in claims
        ]
        artifact_entries = [
            _artifact_entry(
                artifact=artifact,
                source_by_id=source_by_id,
                source_entry_by_id=source_entry_by_id,
                claim_by_id=claim_by_id,
                include_content=request.include_artifact_content,
            )
            for artifact in artifacts
        ]

        missing_source_claim_ids = [
            entry.claim_id for entry in claim_entries if entry.missing_source_ids
        ]
        unsupported_claim_ids = [
            entry.claim_id
            for entry in claim_entries
            if entry.support_status == ClaimSupportStatus.UNSUPPORTED
        ]
        weak_source_ids = [
            entry.source_id
            for entry in source_entries
            if entry.quality_status == SourceQualityStatus.WEAK
        ]
        stale_source_ids = [
            entry.source_id
            for entry in source_entries
            if entry.freshness_status == SourceFreshnessStatus.STALE
        ]
        unknown_freshness_source_ids = [
            entry.source_id
            for entry in source_entries
            if entry.freshness_status == SourceFreshnessStatus.UNKNOWN
        ]
        artifacts_missing_claims = [
            entry.artifact_id
            for entry in artifact_entries
            if not entry.claim_ids or entry.missing_claim_ids
        ]
        artifacts_missing_sources = [
            entry.artifact_id
            for entry in artifact_entries
            if entry.missing_source_ids
        ]
        supported_claim_count = sum(
            1 for claim in claims if claim.support_status == ClaimSupportStatus.SUPPORTED
        )
        needs_review_claim_count = sum(
            1
            for claim in claims
            if claim.support_status == ClaimSupportStatus.NEEDS_REVIEW
        )
        unsupported_claim_count = sum(
            1
            for claim in claims
            if claim.support_status == ClaimSupportStatus.UNSUPPORTED
        )
        claim_source_matrix_count = sum(
            len(entry.claim_source_matrix) for entry in artifact_entries
        )
        claim_source_verdict_counts = _value_counts(
            matrix_entry.verdict
            for artifact_entry in artifact_entries
            for matrix_entry in artifact_entry.claim_source_matrix
        )

        ledger_artifact_id = None
        result = SourceLedgerSnapshotResult(
            run_id=run_id,
            source_count=len(sources),
            claim_count=len(claims),
            artifact_count=len(artifacts),
            supported_claim_count=supported_claim_count,
            needs_review_claim_count=needs_review_claim_count,
            unsupported_claim_count=unsupported_claim_count,
            missing_source_claim_ids=missing_source_claim_ids,
            unsupported_claim_ids=unsupported_claim_ids,
            weak_source_ids=weak_source_ids,
            stale_source_ids=stale_source_ids,
            unknown_freshness_source_ids=unknown_freshness_source_ids,
            accepted_retrieval_source_count=accepted_retrieval_source_count,
            retrieval_evidence_status=_retrieval_evidence_status(
                retrieval_ledger,
                accepted_retrieval_source_count,
            ),
            retrieval_ledger_artifact_id=(
                retrieval_ledger.artifact_id if retrieval_ledger else None
            ),
            artifacts_missing_claims=artifacts_missing_claims,
            artifacts_missing_sources=artifacts_missing_sources,
            claim_source_matrix_count=claim_source_matrix_count,
            claim_source_verdict_counts=claim_source_verdict_counts,
            source_entries=source_entries,
            claim_entries=claim_entries,
            artifact_entries=artifact_entries,
            summary=_summary(
                source_count=len(sources),
                claim_count=len(claims),
                artifact_count=len(artifacts),
                accepted_retrieval_source_count=accepted_retrieval_source_count,
                needs_review_claim_count=needs_review_claim_count,
                unsupported_claim_count=unsupported_claim_count,
                weak_source_count=len(weak_source_ids),
                source_freshness_review_count=(
                    len(stale_source_ids) + len(unknown_freshness_source_ids)
                ),
                artifacts_missing_claims=len(artifacts_missing_claims),
                artifacts_missing_sources=len(artifacts_missing_sources),
                claim_source_matrix_count=claim_source_matrix_count,
            ),
        )
        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.SOURCE_LEDGER,
                title="Source ledger snapshot",
                uri=f"artifact://runs/{run_id}/source-ledger",
                content={},
                provenance={
                    "workflow": "source_ledger_snapshot_v1",
                    "agent_id": "source-ledger-agent",
                    "source_count": len(sources),
                    "claim_count": len(claims),
                    "artifact_count": len(artifacts),
                    "accepted_retrieval_source_count": (
                        accepted_retrieval_source_count
                    ),
                    "retrieval_evidence_status": result.retrieval_evidence_status,
                    "retrieval_ledger_artifact_id": (
                        str(result.retrieval_ledger_artifact_id)
                        if result.retrieval_ledger_artifact_id
                        else None
                    ),
                },
                source_ids=[source.source_id for source in sources],
            )
            ledger_artifact_id = artifact.artifact_id
            result.ledger_artifact_id = ledger_artifact_id
            artifact.content = result.model_dump(mode="json", exclude={"event_id"})
            await self._store.record_artifact(artifact)
            await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="artifact_recorded",
                    actor="artifact-librarian",
                    payload=artifact.model_dump(mode="json"),
                )
            )

        event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="source_ledger_snapshot_built",
                actor="source-ledger-agent",
                payload={
                    "source_count": result.source_count,
                    "claim_count": result.claim_count,
                    "artifact_count": result.artifact_count,
                    "supported_claim_count": result.supported_claim_count,
                    "needs_review_claim_count": result.needs_review_claim_count,
                    "unsupported_claim_count": result.unsupported_claim_count,
                    "weak_source_count": len(result.weak_source_ids),
                    "stale_source_count": len(result.stale_source_ids),
                    "unknown_freshness_source_count": len(
                        result.unknown_freshness_source_ids
                    ),
                    "accepted_retrieval_source_count": (
                        result.accepted_retrieval_source_count
                    ),
                    "retrieval_evidence_status": result.retrieval_evidence_status,
                    "retrieval_ledger_artifact_id": (
                        str(result.retrieval_ledger_artifact_id)
                        if result.retrieval_ledger_artifact_id
                        else None
                    ),
                    "artifacts_missing_claims": [
                        str(artifact_id)
                        for artifact_id in result.artifacts_missing_claims
                    ],
                    "artifacts_missing_sources": [
                        str(artifact_id)
                        for artifact_id in result.artifacts_missing_sources
                    ],
                    "claim_source_matrix_count": result.claim_source_matrix_count,
                    "claim_source_verdict_counts": (
                        result.claim_source_verdict_counts
                    ),
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


def _source_entry_with_retrieval_evidence(
    entry: SourceLedgerSourceEntry,
    evidence,
) -> SourceLedgerSourceEntry:
    if evidence is None:
        return entry
    return entry.model_copy(
        update={
            "accepted_for_context": True,
            "retrieval_candidate_id": evidence.candidate_id,
            "retrieval_rank": evidence.fused_rank,
            "retrieval_rerank_score": evidence.rerank_score,
            "retrieval_reranker": evidence.reranker,
            "retrieval_rerank_reason": evidence.rerank_reason,
            "retrieval_precision_risks": list(evidence.precision_risks),
            "retrieval_recall_risks": list(evidence.recall_risks),
            "retrieval_coverage_topics": list(evidence.coverage_topics),
            "retrieval_ledger_artifact_id": evidence.ledger_artifact_id,
            "retrieval_ledger_status": evidence.ledger_status,
        }
    )


def _retrieval_evidence_status(
    retrieval_ledger: ArtifactRecord | None,
    accepted_retrieval_source_count: int,
) -> str:
    if retrieval_ledger is None:
        return "missing_retrieval_quality_ledger"
    status = retrieval_quality_ledger_status(retrieval_ledger)
    if status and status != "ready":
        return f"retrieval_quality_{status}"
    if accepted_retrieval_source_count:
        return "accepted_evidence_available"
    return "no_accepted_source_evidence"


def _artifact_entry(
    *,
    artifact: ArtifactRecord,
    source_by_id: dict[UUID, object],
    source_entry_by_id: dict[UUID, object],
    claim_by_id: dict[UUID, object],
    include_content: bool,
) -> SourceLedgerArtifactEntry:
    claim_ids = _extract_claim_ids(artifact)
    source_ids = list(dict.fromkeys(artifact.source_ids))
    missing_source_ids = [
        source_id for source_id in source_ids if source_id not in source_by_id
    ]
    missing_claim_ids = [claim_id for claim_id in claim_ids if claim_id not in claim_by_id]
    linked_claims = [
        claim_by_id[claim_id] for claim_id in claim_ids if claim_id in claim_by_id
    ]
    linked_claim_source_ids = {
        source_id
        for claim in linked_claims
        for source_id in claim.source_ids
    }
    missing_source_ids.extend(
        source_id
        for source_id in linked_claim_source_ids
        if source_id not in source_by_id and source_id not in missing_source_ids
    )
    linked_source_entries = [
        source_entry_by_id[source_id]
        for source_id in set([*source_ids, *linked_claim_source_ids])
        if source_id in source_entry_by_id
    ]
    claim_source_matrix = _claim_source_matrix(
        linked_claims=linked_claims,
        source_by_id=source_by_id,
        source_entry_by_id=source_entry_by_id,
    )
    if not claim_ids or missing_claim_ids:
        coverage_status = "missing_claims"
    elif missing_source_ids:
        coverage_status = "missing_sources"
    elif any(
        entry.quality_status == SourceQualityStatus.WEAK
        for entry in linked_source_entries
    ):
        coverage_status = "weak_sources"
    elif any(
        claim.support_status == ClaimSupportStatus.UNSUPPORTED
        for claim in linked_claims
    ):
        coverage_status = "unsupported_claims"
    elif any(
        claim.support_status == ClaimSupportStatus.NEEDS_REVIEW
        for claim in linked_claims
    ):
        coverage_status = "needs_review"
    elif any(
        entry.freshness_status
        in {SourceFreshnessStatus.STALE, SourceFreshnessStatus.UNKNOWN}
        for entry in linked_source_entries
    ):
        coverage_status = "source_freshness_review"
    else:
        coverage_status = "supported"
    return SourceLedgerArtifactEntry(
        artifact_id=artifact.artifact_id,
        artifact_type=artifact.artifact_type,
        title=artifact.title,
        uri=artifact.uri,
        source_ids=source_ids,
        source_citation_ids=[
            source_by_id[source_id].citation_id
            for source_id in source_ids
            if source_id in source_by_id
        ],
        claim_ids=claim_ids,
        missing_source_ids=missing_source_ids,
        missing_claim_ids=missing_claim_ids,
        claim_source_matrix=claim_source_matrix,
        coverage_status=coverage_status,
        content_preview=artifact.content if include_content else {},
    )


def _claim_source_matrix(
    *,
    linked_claims: list[object],
    source_by_id: dict[UUID, object],
    source_entry_by_id: dict[UUID, object],
) -> list[SourceLedgerClaimSourceMatrixEntry]:
    matrix = []
    for claim in linked_claims:
        source_citation_ids = [
            source_by_id[source_id].citation_id
            for source_id in claim.source_ids
            if source_id in source_by_id
        ]
        missing_source_ids = [
            source_id for source_id in claim.source_ids if source_id not in source_by_id
        ]
        source_quality_statuses = {
            source_by_id[source_id].citation_id: source_entry_by_id[
                source_id
            ].quality_status
            for source_id in claim.source_ids
            if source_id in source_by_id and source_id in source_entry_by_id
        }
        source_freshness_statuses = {
            source_by_id[source_id].citation_id: source_entry_by_id[
                source_id
            ].freshness_status
            for source_id in claim.source_ids
            if source_id in source_by_id and source_id in source_entry_by_id
        }
        matrix.append(
            SourceLedgerClaimSourceMatrixEntry(
                claim_id=claim.claim_id,
                claim_text=claim.claim_text,
                support_status=claim.support_status,
                source_ids=claim.source_ids,
                source_citation_ids=source_citation_ids,
                missing_source_ids=missing_source_ids,
                source_quality_statuses=source_quality_statuses,
                source_freshness_statuses=source_freshness_statuses,
                verdict=_claim_source_verdict(
                    claim=claim,
                    missing_source_ids=missing_source_ids,
                    source_quality_statuses=source_quality_statuses,
                    source_freshness_statuses=source_freshness_statuses,
                ),
            )
        )
    return matrix


def _claim_source_verdict(
    *,
    claim,
    missing_source_ids: list[UUID],
    source_quality_statuses: dict[str, SourceQualityStatus],
    source_freshness_statuses: dict[str, SourceFreshnessStatus],
) -> str:
    if missing_source_ids or not claim.source_ids:
        return "missing_sources"
    if claim.support_status == ClaimSupportStatus.UNSUPPORTED:
        return "unsupported"
    if any(status == SourceQualityStatus.WEAK for status in source_quality_statuses.values()):
        return "weak_sources"
    if claim.support_status == ClaimSupportStatus.NEEDS_REVIEW:
        return "needs_review"
    if any(
        status in {SourceFreshnessStatus.STALE, SourceFreshnessStatus.UNKNOWN}
        for status in source_freshness_statuses.values()
    ):
        return "source_freshness_review"
    return "supported"


def _extract_claim_ids(artifact: ArtifactRecord) -> list[UUID]:
    raw_claim_ids = [
        *artifact.provenance.get("claim_ids", []),
        *artifact.content.get("claim_ids", []),
    ]
    claim_ids = []
    for raw_claim_id in raw_claim_ids:
        try:
            claim_id = UUID(str(raw_claim_id))
        except (TypeError, ValueError):
            continue
        if claim_id not in claim_ids:
            claim_ids.append(claim_id)
    return claim_ids


def _summary(
    *,
    source_count: int,
    claim_count: int,
    artifact_count: int,
    accepted_retrieval_source_count: int,
    needs_review_claim_count: int,
    unsupported_claim_count: int,
    weak_source_count: int,
    source_freshness_review_count: int,
    artifacts_missing_claims: int,
    artifacts_missing_sources: int,
    claim_source_matrix_count: int,
) -> str:
    return (
        f"Source ledger snapshot covers {source_count} source(s), "
        f"{claim_count} claim(s), and {artifact_count} artifact(s): "
        f"{accepted_retrieval_source_count} source(s) are accepted retrieval evidence, "
        f"{needs_review_claim_count} claim(s) need review, "
        f"{unsupported_claim_count} claim(s) are unsupported, "
        f"{weak_source_count} source(s) are weak, "
        f"{source_freshness_review_count} source(s) need freshness review, "
        f"{artifacts_missing_claims} artifact(s) need claim links, and "
        f"{artifacts_missing_sources} artifact(s) need source repair. "
        f"{claim_source_matrix_count} claim-to-source artifact link(s) are indexed."
    )


def _value_counts(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts
