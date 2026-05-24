from datetime import datetime, timezone
from uuid import UUID

from all_about_llms.contracts import (
    ArtifactRecord,
    ArtifactType,
    ClaimRecord,
    ClaimSupportStatus,
    DistributionPackageRequest,
    DistributionPackageResult,
    DistributionPlatformVariant,
    RunEvent,
    SourceRecord,
)


class DistributionPackageError(RuntimeError):
    """Base error for platform distribution packaging."""


class DistributionPackageRunNotFoundError(DistributionPackageError):
    """Raised when a distribution package targets a missing run."""


class NoArtifactsForDistributionPackageError(DistributionPackageError):
    """Raised when there are no source content artifacts to package."""


SOURCE_CONTENT_TYPES = {
    ArtifactType.POST,
    ArtifactType.REEL_SCRIPT,
    ArtifactType.SUBSTACK_ARTICLE,
}

DEFAULT_HASHTAGS = [
    "#AI",
    "#LLMs",
    "#AIAgents",
    "#SourceBacked",
    "#BuildInPublic",
]

DEFAULT_KEYWORDS = [
    "source-backed AI",
    "multi-agent workflow",
    "realtime agents",
    "Gemma 4 experts",
    "content studio",
]


class DistributionPackageWorkflow:
    """Create durable platform packaging from source-backed content drafts."""

    def __init__(self, store):
        self._store = store

    async def run(
        self, run_id: UUID, request: DistributionPackageRequest
    ) -> DistributionPackageResult:
        result, _ = await self._run(run_id, request)
        return result

    async def run_idempotent(
        self,
        run_id: UUID,
        request: DistributionPackageRequest,
        *,
        artifact_id: UUID,
    ) -> tuple[DistributionPackageResult, bool]:
        return await self._run(
            run_id,
            request,
            artifact_id=artifact_id,
            record_if_absent=True,
        )

    async def _run(
        self,
        run_id: UUID,
        request: DistributionPackageRequest,
        *,
        artifact_id: UUID | None = None,
        record_if_absent: bool = False,
    ) -> tuple[DistributionPackageResult, bool]:
        run = await self._store.get_run(run_id)
        if run is None:
            raise DistributionPackageRunNotFoundError(f"Run not found: {run_id}")

        source_artifacts = await self._select_source_artifacts(run_id, request)
        if not source_artifacts:
            raise NoArtifactsForDistributionPackageError(
                "No content artifacts are available for distribution packaging."
            )

        sources = await self._store.list_sources(run_id)
        claims = await self._store.list_claims(run_id)
        source_ids = _union_source_ids(source_artifacts)
        claim_ids = _union_claim_ids(source_artifacts)
        topic = _topic_from_run(run, source_artifacts)
        platforms = _normalized_platforms(request.platforms)
        initiated_by_agent_id = (
            request.initiated_by_agent_id or request.created_by_agent_id
        )
        variants = _platform_variants(
            topic=topic,
            request=request,
            platforms=platforms,
            source_artifacts=source_artifacts,
            sources=sources,
            claim_ids=claim_ids,
        )
        content = {
            "workflow": "distribution_package_v1",
            "topic": topic,
            "audience": request.audience,
            "campaign_goal": request.campaign_goal,
            "platforms": [variant.model_dump(mode="json") for variant in variants],
            "outreach": _outreach_brief(topic, request, sources)
            if request.include_outreach
            else None,
            "claim_review_state": _claim_review_state(claims, claim_ids),
            "source_dependencies": _source_dependencies(sources, source_ids),
            "source_artifact_ids": [
                str(artifact.artifact_id) for artifact in source_artifacts
            ],
            "source_ids": [str(source_id) for source_id in source_ids],
            "claim_ids": [str(claim_id) for claim_id in claim_ids],
            "review_checklist": [
                "Confirm every factual hook still maps to the source ledger.",
                "Remove or relabel unsupported claims before publishing.",
                "Run guardrail audit and publish readiness before external use.",
                "Keep ELI5 wording for social surfaces and deeper caveats for Substack.",
            ],
        }
        artifact = ArtifactRecord(
            run_id=run_id,
            artifact_type=ArtifactType.SOCIAL_PACKAGE,
            title=f"Distribution package: {topic}",
            uri="",
            content=content,
            provenance={
                "workflow": "distribution_package_v1",
                "agent_ids": [
                "influencer-strategy-agent",
                "platform-optimization-agent",
                "outreach-agent",
                "editor-in-chief",
            ],
            "created_by_agent_id": request.created_by_agent_id,
            "initiated_by_agent_id": initiated_by_agent_id,
            "audience": request.audience,
            "campaign_goal": request.campaign_goal,
            "include_outreach": request.include_outreach,
            "source_artifact_ids": [
                str(artifact.artifact_id) for artifact in source_artifacts
            ],
                "source_ids": [str(source_id) for source_id in source_ids],
                "claim_ids": [str(claim_id) for claim_id in claim_ids],
                "platforms": platforms,
                "generation_mode": "deterministic_distribution_package",
            },
            source_ids=source_ids,
            reviewer_decisions=[
                {
                    "reviewer_agent_id": "editor-in-chief",
                    "status": "needs_revision",
                    "notes": (
                        "Distribution package is ready for growth review, "
                        "then guardrail audit and human approval."
                    ),
                    "blocking_issues": ["requires_guardrail_audit"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
            revision_history=[
                {
                    "actor": initiated_by_agent_id,
                    "note": "Created first durable platform distribution package.",
                }
            ],
        )
        if artifact_id is not None:
            artifact.artifact_id = artifact_id
        artifact.uri = (
            f"artifact://runs/{run_id}/distribution-packages/{artifact.artifact_id}"
        )
        recorded = True
        if record_if_absent:
            recorder = getattr(self._store, "record_artifact_if_absent", None)
            if callable(recorder):
                persisted = await recorder(artifact)
                recorded = persisted is not None
                if persisted is not None:
                    artifact = persisted
                else:
                    artifact = await _find_artifact_by_id(
                        self._store, run_id, artifact.artifact_id
                    ) or artifact
            else:
                await self._store.record_artifact(artifact)
        else:
            await self._store.record_artifact(artifact)

        event = None
        if recorded:
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
                    event_type="distribution_package_built",
                    actor=initiated_by_agent_id,
                    payload={
                        "distribution_artifact_id": str(artifact.artifact_id),
                        "source_artifact_ids": [
                            str(source_artifact.artifact_id)
                            for source_artifact in source_artifacts
                        ],
                        "platforms": platforms,
                        "audience": request.audience,
                        "campaign_goal": request.campaign_goal,
                        "include_outreach": request.include_outreach,
                        "created_by_agent_id": request.created_by_agent_id,
                        "initiated_by_agent_id": initiated_by_agent_id,
                    },
                )
            )
        summary_action = "Created" if recorded else "Reused"
        return (
            DistributionPackageResult(
                run_id=run_id,
                source_artifact_ids=[
                    artifact.artifact_id for artifact in source_artifacts
                ],
                distribution_artifact_id=artifact.artifact_id,
                platforms=platforms,
                event_id=event.event_id if event is not None else None,
                summary=(
                    f"{summary_action} a source-backed distribution package for "
                    f"{len(platforms)} platform(s) from {len(source_artifacts)} "
                    "content artifact(s)."
                ),
            ),
            recorded,
        )

    async def _select_source_artifacts(
        self, run_id: UUID, request: DistributionPackageRequest
    ) -> list[ArtifactRecord]:
        artifacts = await self._store.list_artifacts(run_id)
        if request.target_artifact_ids:
            target_ids = set(request.target_artifact_ids)
            return [
                artifact
                for artifact in artifacts
                if artifact.artifact_id in target_ids
                and artifact.artifact_type in SOURCE_CONTENT_TYPES
            ]
        return _leaf_content_artifacts(artifacts)


def _leaf_content_artifacts(artifacts: list[ArtifactRecord]) -> list[ArtifactRecord]:
    parent_ids = set()
    for artifact in artifacts:
        parent_id = artifact.provenance.get("parent_artifact_id")
        if isinstance(parent_id, str):
            try:
                parent_ids.add(UUID(parent_id))
            except ValueError:
                continue
    return [
        artifact
        for artifact in artifacts
        if artifact.artifact_type in SOURCE_CONTENT_TYPES
        and artifact.artifact_id not in parent_ids
    ]


async def _find_artifact_by_id(
    store, run_id: UUID, artifact_id: UUID
) -> ArtifactRecord | None:
    for artifact in await store.list_artifacts(run_id):
        if artifact.artifact_id == artifact_id:
            return artifact
    return None


def _union_source_ids(artifacts: list[ArtifactRecord]) -> list[UUID]:
    source_ids: list[UUID] = []
    for artifact in artifacts:
        for source_id in artifact.source_ids:
            if source_id not in source_ids:
                source_ids.append(source_id)
    return source_ids


def _union_claim_ids(artifacts: list[ArtifactRecord]) -> list[UUID]:
    claim_ids: list[UUID] = []
    for artifact in artifacts:
        for claim_id in _extract_claim_ids(artifact):
            if claim_id not in claim_ids:
                claim_ids.append(claim_id)
    return claim_ids


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


def _topic_from_run(run, artifacts: list[ArtifactRecord]) -> str:
    state_topic = run.conversation_state.get("topic")
    if isinstance(state_topic, str) and state_topic.strip():
        return state_topic.strip()
    for artifact in artifacts:
        topic = artifact.content.get("topic")
        if isinstance(topic, str) and topic.strip():
            return topic.strip()
    goal = run.goal.removeprefix("Create source-backed content about ").strip()
    return goal or "source-backed AI content"


def _normalized_platforms(platforms: list[str]) -> list[str]:
    aliases = {
        "instagram": "instagram_post",
        "insta": "instagram_post",
        "ig": "instagram_post",
        "reel": "instagram_reel",
        "reels": "instagram_reel",
        "x": "x_thread",
        "twitter": "x_thread",
        "substack_article": "substack",
    }
    normalized = []
    for platform in platforms or []:
        value = aliases.get(platform.strip().lower(), platform.strip().lower())
        if value and value not in normalized:
            normalized.append(value)
    return normalized or [
        "instagram_post",
        "instagram_reel",
        "linkedin",
        "x_thread",
        "substack",
    ]


def _platform_variants(
    *,
    topic: str,
    request: DistributionPackageRequest,
    platforms: list[str],
    source_artifacts: list[ArtifactRecord],
    sources: list[SourceRecord],
    claim_ids: list[UUID],
) -> list[DistributionPlatformVariant]:
    citation_ids = _citation_ids_for_artifacts(sources, source_artifacts)
    variants = []
    for platform in platforms:
        variants.append(
            DistributionPlatformVariant(
                platform=platform,
                hook=_hook(platform, topic),
                primary_copy=_primary_copy(platform, topic, request),
                cta=_cta(platform),
                hashtags=_hashtags(platform),
                keywords=_keywords(platform),
                format_notes=_format_notes(platform),
                source_citation_ids=citation_ids,
                claim_ids=claim_ids,
            )
        )
    return variants


def _citation_ids_for_artifacts(
    sources: list[SourceRecord], artifacts: list[ArtifactRecord]
) -> list[str]:
    source_by_id = {source.source_id: source for source in sources}
    citation_ids = []
    for source_id in _union_source_ids(artifacts):
        source = source_by_id.get(source_id)
        if source and source.citation_id not in citation_ids:
            citation_ids.append(source.citation_id)
    return citation_ids


def _hook(platform: str, topic: str) -> str:
    hooks = {
        "instagram_post": f"ELI5: {topic} without the hype.",
        "instagram_reel": f"POV: {topic} explained before the claims outrun the sources.",
        "linkedin": f"A practical way to explain {topic}: keep the story simple and the evidence visible.",
        "x_thread": f"{topic}, explained in a source-backed thread.",
        "substack": f"{topic}: the ELI5 story, then the evidence trail.",
    }
    return hooks.get(platform, f"{topic}, explained with sources first.")


def _primary_copy(
    platform: str, topic: str, request: DistributionPackageRequest
) -> str:
    copies = {
        "instagram_post": (
            f"Think of {topic} like a studio conversation: one part explains it "
            "simply, one part checks sources, and one part keeps the caveats "
            f"visible for {request.audience}."
        ),
        "instagram_reel": (
            "Beat 1: start with the simplest analogy. Beat 2: show the real-world "
            "source trail. Beat 3: name the caveat. Beat 4: ask the audience what "
            "they want checked next."
        ),
        "linkedin": (
            f"{topic} works best as an evidence-backed operating story: explain "
            "the idea plainly, show what is sourced, and separate confidence from "
            "open questions before asking people to act on it."
        ),
        "x_thread": (
            f"1/ {topic} should be explained simply, but not loosely.\n"
            "2/ Keep claims tied to sources.\n"
            "3/ Mark uncertainty instead of hiding it.\n"
            "4/ Turn audience questions into the next research pass."
        ),
        "substack": (
            "Open with an ELI5 summary, then walk through the mechanism, source "
            "ledger, caveats, and practical takeaways. Keep social phrasing out "
            "of the deeper sections."
        ),
    }
    return copies.get(
        platform,
        f"Use a source-first explanation of {topic} for {request.audience}.",
    )


def _cta(platform: str) -> str:
    ctas = {
        "instagram_post": "Comment with the claim you want checked next.",
        "instagram_reel": "Save this, then ask for the source ledger.",
        "linkedin": "Reply with the workflow risk you would stress-test first.",
        "x_thread": "Reply with a counterexample or a source worth adding.",
        "substack": "Invite readers to challenge the weakest claim before publication.",
    }
    return ctas.get(platform, "Ask for the next source-backed revision.")


def _hashtags(platform: str) -> list[str]:
    if platform == "linkedin":
        return ["#ArtificialIntelligence", "#AIAgents", "#ProductEngineering"]
    if platform == "substack":
        return []
    if platform == "x_thread":
        return ["AI", "LLMs", "AIAgents", "SourceBacked"]
    return DEFAULT_HASHTAGS


def _keywords(platform: str) -> list[str]:
    if platform == "substack":
        return [
            "evidence-backed AI",
            "agentic workflows",
            "source ledger",
            "human feedback gates",
        ]
    if platform == "instagram_reel":
        return ["ELI5", "AI agents", "source-backed", "realtime workflow"]
    return DEFAULT_KEYWORDS


def _format_notes(platform: str) -> list[str]:
    notes = {
        "instagram_post": [
            "Lead with the hook on line one.",
            "Keep line breaks short for mobile scanning.",
            "Do not bury the caveat after hashtags.",
        ],
        "instagram_reel": [
            "Keep the opening spoken line under three seconds.",
            "Reserve safe space for captions and platform UI.",
            "End with a concrete source-ledger prompt.",
        ],
        "linkedin": [
            "Use a professional first line, then concrete bullets.",
            "Avoid hype words that cannot be sourced.",
        ],
        "x_thread": [
            "One claim per post.",
            "Keep citation pointers visible in the thread body.",
        ],
        "substack": [
            "Use ELI5 blocks before technical sections.",
            "Put source caveats before practical takeaways.",
        ],
    }
    return notes.get(platform, ["Keep claims source-backed and caveats visible."])


def _source_dependencies(
    sources: list[SourceRecord], source_ids: list[UUID]
) -> list[dict]:
    source_by_id = {source.source_id: source for source in sources}
    dependencies = []
    for source_id in source_ids:
        source = source_by_id.get(source_id)
        if source is None:
            continue
        dependencies.append(
            {
                "source_id": str(source.source_id),
                "citation_id": source.citation_id,
                "title": source.title,
                "url": str(source.url),
                "publisher": source.publisher,
                "published_at": (
                    source.published_at.isoformat() if source.published_at else None
                ),
            }
        )
    return dependencies


def _claim_review_state(
    claims: list[ClaimRecord], claim_ids: list[UUID]
) -> dict[str, object]:
    claim_by_id = {claim.claim_id: claim for claim in claims}
    linked_claims = [
        claim_by_id[claim_id] for claim_id in claim_ids if claim_id in claim_by_id
    ]
    return {
        "claim_count": len(linked_claims),
        "supported_claim_ids": [
            str(claim.claim_id)
            for claim in linked_claims
            if claim.support_status == ClaimSupportStatus.SUPPORTED
        ],
        "needs_review_claim_ids": [
            str(claim.claim_id)
            for claim in linked_claims
            if claim.support_status == ClaimSupportStatus.NEEDS_REVIEW
        ],
        "unsupported_claim_ids": [
            str(claim.claim_id)
            for claim in linked_claims
            if claim.support_status == ClaimSupportStatus.UNSUPPORTED
        ],
    }


def _outreach_brief(
    topic: str, request: DistributionPackageRequest, sources: list[SourceRecord]
) -> dict[str, object]:
    publisher_names = [
        source.publisher
        for source in sources
        if source.publisher and source.publisher != "Web search task"
    ]
    return {
        "audience_segments": [
            request.audience,
            "technical creators explaining AI systems",
            "operators evaluating agent workflows",
        ],
        "community_angles": [
            f"Ask what people misunderstand most about {topic}.",
            "Invite source suggestions before the next revision.",
            "Position the piece as a transparent build-and-review loop.",
        ],
        "collaboration_pitch": (
            f"I am building a source-backed explainer on {topic}. "
            "Want to challenge the weakest claim before I publish it?"
        ),
        "source_people_or_publishers_to_reference": publisher_names[:5],
        "do_not_say": [
            "Do not imply unsupported benchmarks, safety guarantees, or model access.",
            "Do not present generated visuals, audio, or video plans as finished assets.",
        ],
    }
