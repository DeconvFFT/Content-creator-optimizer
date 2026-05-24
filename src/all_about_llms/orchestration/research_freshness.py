from collections import defaultdict
from uuid import UUID

from all_about_llms.contracts import (
    ArtifactRecord,
    ArtifactType,
    ResearchFreshnessLedgerRequest,
    ResearchFreshnessLedgerResult,
    ResearchFreshnessQueryEntry,
    ResearchFreshnessSourceEntry,
    ResearchFreshnessStatus,
    RunEvent,
    SourceFreshnessStatus,
    SourceQualityStatus,
)
from all_about_llms.orchestration.source_quality import evaluate_source_quality


class ResearchFreshnessLedgerError(RuntimeError):
    """Base error for research freshness ledger generation."""


class ResearchFreshnessLedgerRunNotFoundError(ResearchFreshnessLedgerError):
    """Raised when a run cannot be found for research freshness work."""


class ResearchFreshnessLedgerWorkflow:
    """Build a durable proof of search freshness and source acceptance state."""

    def __init__(self, store):
        self._store = store

    async def build(
        self, run_id: UUID, request: ResearchFreshnessLedgerRequest
    ) -> ResearchFreshnessLedgerResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise ResearchFreshnessLedgerRunNotFoundError(f"Run not found: {run_id}")

        sources = await self._store.list_sources(run_id)
        topic = request.topic or _topic_from_run(run)
        source_entries = [_source_entry(source) for source in sources]
        query_entries = _query_entries(
            topic=topic,
            source_entries=source_entries,
            freshness_required=request.freshness_required,
        )

        seed_source_count = sum(
            1 for entry in source_entries if entry.requires_web_search
        )
        weak_source_count = sum(
            1
            for entry in source_entries
            if entry.quality_status == SourceQualityStatus.WEAK
        )
        stale_source_count = sum(
            1
            for entry in source_entries
            if entry.freshness_status == SourceFreshnessStatus.STALE
        )
        unknown_freshness_source_count = sum(
            1
            for entry in source_entries
            if entry.freshness_status == SourceFreshnessStatus.UNKNOWN
        )
        needs_review_source_count = sum(
            1
            for entry in source_entries
            if entry.quality_status == SourceQualityStatus.NEEDS_REVIEW
            or entry.freshness_status
            in {SourceFreshnessStatus.UNKNOWN, SourceFreshnessStatus.STALE}
        )
        accepted_source_count = sum(
            1 for entry in source_entries if entry.accepted_for_drafting
        )
        status = _overall_status(
            source_count=len(source_entries),
            accepted_source_count=accepted_source_count,
            seed_source_count=seed_source_count,
            weak_source_count=weak_source_count,
            stale_source_count=stale_source_count,
            unknown_freshness_source_count=unknown_freshness_source_count,
            freshness_required=request.freshness_required,
        )
        result = ResearchFreshnessLedgerResult(
            run_id=run_id,
            topic=topic,
            status=status,
            source_count=len(source_entries),
            accepted_source_count=accepted_source_count,
            seed_source_count=seed_source_count,
            weak_source_count=weak_source_count,
            stale_source_count=stale_source_count,
            unknown_freshness_source_count=unknown_freshness_source_count,
            needs_review_source_count=needs_review_source_count,
            query_entries=query_entries,
            source_entries=source_entries,
            summary=_summary(
                status=status,
                topic=topic,
                source_count=len(source_entries),
                accepted_source_count=accepted_source_count,
                seed_source_count=seed_source_count,
                needs_review_source_count=needs_review_source_count,
            ),
        )

        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.RESEARCH_FRESHNESS_LEDGER,
                title=f"Research freshness ledger: {topic}",
                uri=f"artifact://runs/{run_id}/research-freshness-ledger",
                content=result.model_dump(
                    mode="json", exclude={"ledger_artifact_id", "event_id"}
                ),
                provenance={
                    "workflow": "research_freshness_ledger_v1",
                    "agent_id": "web-research-agent",
                    "freshness_required": request.freshness_required,
                    "topic": topic,
                },
                source_ids=[entry.source_id for entry in source_entries],
                revision_history=[
                    {
                        "actor": "web-research-agent",
                        "note": "Recorded source freshness, search query, and acceptance state.",
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

        event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="research_freshness_ledger_built",
                actor="web-research-agent",
                payload={
                    "topic": topic,
                    "status": result.status.value,
                    "source_count": result.source_count,
                    "accepted_source_count": result.accepted_source_count,
                    "seed_source_count": result.seed_source_count,
                    "needs_review_source_count": result.needs_review_source_count,
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


def _source_entry(source) -> ResearchFreshnessSourceEntry:
    quality = evaluate_source_quality(source)
    metadata = source.metadata or {}
    requires_web_search = bool(metadata.get("requires_web_search")) or (
        quality.source_type == "search_query_seed"
    )
    accepted = (
        not requires_web_search
        and quality.quality_status != SourceQualityStatus.WEAK
        and quality.freshness_status != SourceFreshnessStatus.STALE
    )
    return ResearchFreshnessSourceEntry(
        source_id=source.source_id,
        citation_id=source.citation_id,
        title=source.title,
        url=source.url,
        publisher=source.publisher,
        source_type=quality.source_type,
        search_query=metadata.get("search_query"),
        requires_web_search=requires_web_search,
        accepted_for_drafting=accepted,
        quality_status=quality.quality_status,
        freshness_status=quality.freshness_status,
        flags=quality.flags,
        notes=quality.notes,
    )


def _query_entries(
    *,
    topic: str,
    source_entries: list[ResearchFreshnessSourceEntry],
    freshness_required: bool,
) -> list[ResearchFreshnessQueryEntry]:
    grouped: dict[str, list[ResearchFreshnessSourceEntry]] = defaultdict(list)
    for entry in source_entries:
        grouped[entry.search_query or topic].append(entry)
    if not grouped:
        return [
            ResearchFreshnessQueryEntry(
                query=topic,
                source_count=0,
                status=ResearchFreshnessStatus.BLOCKED,
                notes="No sources are recorded for this topic yet.",
            )
        ]
    entries = []
    for query, grouped_sources in sorted(grouped.items()):
        seed_count = sum(1 for source in grouped_sources if source.requires_web_search)
        accepted_count = sum(
            1 for source in grouped_sources if source.accepted_for_drafting
        )
        needs_review_count = sum(
            1
            for source in grouped_sources
            if source.quality_status == SourceQualityStatus.NEEDS_REVIEW
            or source.freshness_status
            in {SourceFreshnessStatus.UNKNOWN, SourceFreshnessStatus.STALE}
        )
        status = _overall_status(
            source_count=len(grouped_sources),
            accepted_source_count=accepted_count,
            seed_source_count=seed_count,
            weak_source_count=sum(
                1
                for source in grouped_sources
                if source.quality_status == SourceQualityStatus.WEAK
            ),
            stale_source_count=sum(
                1
                for source in grouped_sources
                if source.freshness_status == SourceFreshnessStatus.STALE
            ),
            unknown_freshness_source_count=sum(
                1
                for source in grouped_sources
                if source.freshness_status == SourceFreshnessStatus.UNKNOWN
            ),
            freshness_required=freshness_required,
        )
        entries.append(
            ResearchFreshnessQueryEntry(
                query=query,
                source_count=len(grouped_sources),
                accepted_source_count=accepted_count,
                seed_source_count=seed_count,
                needs_review_source_count=needs_review_count,
                status=status,
                notes=_query_notes(status, seed_count, needs_review_count),
            )
        )
    return entries


def _overall_status(
    *,
    source_count: int,
    accepted_source_count: int,
    seed_source_count: int,
    weak_source_count: int,
    stale_source_count: int,
    unknown_freshness_source_count: int,
    freshness_required: bool,
) -> ResearchFreshnessStatus:
    if source_count == 0 or accepted_source_count == 0:
        return ResearchFreshnessStatus.BLOCKED
    if seed_source_count or weak_source_count or stale_source_count:
        return ResearchFreshnessStatus.NEEDS_REFRESH
    if freshness_required and unknown_freshness_source_count:
        return ResearchFreshnessStatus.NEEDS_REFRESH
    return ResearchFreshnessStatus.READY


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
    status: ResearchFreshnessStatus,
    topic: str,
    source_count: int,
    accepted_source_count: int,
    seed_source_count: int,
    needs_review_source_count: int,
) -> str:
    return (
        f"Research freshness for '{topic}' is {status.value}: "
        f"{accepted_source_count}/{source_count} source(s) accepted, "
        f"{seed_source_count} seed source(s), and "
        f"{needs_review_source_count} source(s) needing freshness or quality review."
    )


def _query_notes(
    status: ResearchFreshnessStatus,
    seed_count: int,
    needs_review_count: int,
) -> str:
    if status == ResearchFreshnessStatus.BLOCKED:
        return "Run web research before drafting or approving content."
    if seed_count:
        return "Replace placeholder search seeds with concrete source records."
    if needs_review_count:
        return "Verify publisher and publication dates before final approval."
    return "Query has enough accepted source evidence for this stage."
