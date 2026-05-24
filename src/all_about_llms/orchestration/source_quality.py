from datetime import datetime, timezone

from all_about_llms.contracts import (
    SourceFreshnessStatus,
    SourceLedgerSourceEntry,
    SourceQualityStatus,
    SourceRecord,
)


AUTHORITATIVE_PUBLISHERS = (
    "anthropic",
    "cartesia",
    "elevenlabs",
    "google",
    "hugging face",
    "langchain",
    "livekit",
    "openai",
    "pipecat",
)


def evaluate_source_quality(
    source: SourceRecord, *, now: datetime | None = None
) -> SourceLedgerSourceEntry:
    """Score a source without requiring extra storage schema.

    The score is intentionally conservative. Placeholder search seeds are weak,
    official provider docs are strong/evergreen, and ordinary web results need a
    publication date for strong freshness confidence.
    """

    now = now or datetime.now(timezone.utc)
    metadata = source.metadata or {}
    source_type = str(metadata.get("source_type") or "manual_source")
    flags: list[str] = []

    quality_status, quality_score = _quality_status(source, source_type, flags)
    published_at = _published_at(source)
    freshness_status, freshness_score = _freshness_status(
        source=source,
        source_type=source_type,
        published_at=published_at,
        now=now,
        flags=flags,
    )
    return SourceLedgerSourceEntry(
        source_id=source.source_id,
        citation_id=source.citation_id,
        title=source.title,
        url=source.url,
        publisher=source.publisher,
        source_type=source_type,
        quality_status=quality_status,
        freshness_status=freshness_status,
        quality_score=quality_score,
        freshness_score=freshness_score,
        published_at=published_at,
        retrieved_at=source.retrieved_at,
        flags=flags,
        notes=_notes(quality_status, freshness_status, flags),
    )


def _quality_status(
    source: SourceRecord, source_type: str, flags: list[str]
) -> tuple[SourceQualityStatus, float]:
    metadata = source.metadata or {}
    publisher = (source.publisher or "").lower()
    if bool(metadata.get("requires_web_search")) or source_type == "search_query_seed":
        flags.append("placeholder_search_seed")
        return SourceQualityStatus.WEAK, 0.15
    if (
        source_type in {"provider_reference", "official_documentation"}
        or any(name in publisher for name in AUTHORITATIVE_PUBLISHERS)
    ):
        return SourceQualityStatus.STRONG, 0.9
    if source_type in {"web_search_result", "worker_web_search_result"}:
        if source.publisher:
            return SourceQualityStatus.ACCEPTABLE, 0.72
        flags.append("missing_publisher")
        return SourceQualityStatus.NEEDS_REVIEW, 0.55
    if source.publisher:
        return SourceQualityStatus.ACCEPTABLE, 0.66
    flags.append("unknown_publisher")
    return SourceQualityStatus.NEEDS_REVIEW, 0.5


def _freshness_status(
    *,
    source: SourceRecord,
    source_type: str,
    published_at: datetime | None,
    now: datetime,
    flags: list[str],
) -> tuple[SourceFreshnessStatus, float]:
    metadata = source.metadata or {}
    if bool(metadata.get("requires_web_search")) or source_type == "search_query_seed":
        flags.append("live_search_required")
        return SourceFreshnessStatus.UNKNOWN, 0.1
    if published_at is None and source_type in {
        "provider_reference",
        "official_documentation",
    }:
        return SourceFreshnessStatus.EVERGREEN, 0.8
    if published_at is None:
        flags.append("missing_published_at")
        return SourceFreshnessStatus.UNKNOWN, 0.4

    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    age_days = max((now - published_at).days, 0)
    if age_days <= 365:
        return SourceFreshnessStatus.CURRENT, 0.92
    if age_days <= 1095:
        return SourceFreshnessStatus.ACCEPTABLE, 0.7
    flags.append("stale_published_at")
    return SourceFreshnessStatus.STALE, 0.25


def _published_at(source: SourceRecord) -> datetime | None:
    if source.published_at:
        return source.published_at
    raw = (source.metadata or {}).get("published_at")
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        normalized = raw.strip()
        if not normalized:
            return None
        try:
            return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _notes(
    quality_status: SourceQualityStatus,
    freshness_status: SourceFreshnessStatus,
    flags: list[str],
) -> str:
    if quality_status == SourceQualityStatus.WEAK:
        return "Replace this placeholder or weak source with a concrete source record."
    if freshness_status == SourceFreshnessStatus.STALE:
        return "Refresh this source or add a newer corroborating source before publishing."
    if freshness_status == SourceFreshnessStatus.UNKNOWN:
        return "Publication date is unknown; verify freshness before approval."
    if flags:
        return "Source is usable but still carries review flags."
    return "Source quality and freshness are acceptable for this stage."
