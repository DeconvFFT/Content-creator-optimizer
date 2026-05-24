import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus

from all_about_llms.contracts import (
    AgentMessage,
    ArtifactRecord,
    ArtifactType,
    ClaimRecord,
    ClaimSupportStatus,
    ConversationTurn,
    DEFAULT_TARGET_FORMATS,
    OrchestrationRequest,
    OrchestrationResult,
    RunEvent,
    RunState,
    RunStatus,
    SourceRecord,
)
from all_about_llms.orchestration.a2a_projection import (
    public_a2a_message_event_payload,
)
from all_about_llms.orchestration.services import ContentWorkflowServices
from all_about_llms.providers.interfaces import (
    GemmaRequest,
    ProviderConfigurationError,
    SearchRequest,
)
from all_about_llms.realtime_safety import safe_realtime_metadata


class ContentStudioWorkflow:
    """First durable orchestration loop for source-backed content generation."""

    def __init__(
        self, store, services: ContentWorkflowServices | None = None
    ):
        self._store = store
        self._services = services or ContentWorkflowServices()

    async def run(self, request: OrchestrationRequest) -> OrchestrationResult:
        topic = request.topic or _derive_topic(request.transcript)
        run = await self._create_run(request, topic)
        turn = await self._record_turn(run, request)
        task_messages = await self._route_tasks(run, request, topic)
        sources = await self._record_sources(run, topic)
        claims = await self._record_claims(run, topic, sources)
        artifacts = await self._record_content_pack(
            run=run,
            topic=topic,
            request=request,
            sources=sources,
            claims=claims,
        )
        feedback_gate_opened = await self._open_review_loop_if_needed(run, request)
        await self._store.update_run_status(
            run.run_id,
            RunStatus.WAITING_FOR_HUMAN
            if feedback_gate_opened
            else RunStatus.COMPLETED,
        )

        return OrchestrationResult(
            run_id=run.run_id,
            turn_id=turn.turn_id,
            task_message_ids=[message.message_id for message in task_messages],
            source_ids=[source.source_id for source in sources],
            claim_ids=[claim.claim_id for claim in claims],
            artifact_ids=[artifact.artifact_id for artifact in artifacts],
            feedback_gate_opened=feedback_gate_opened,
            summary=(
                f"Created a durable content workflow for '{topic}' with "
                f"{len(task_messages)} agent tasks, {len(sources)} sources, "
                f"{len(claims)} claims, and {len(artifacts)} artifacts."
            ),
        )

    async def _create_run(self, request: OrchestrationRequest, topic: str) -> RunState:
        run = RunState(
            goal=f"Create source-backed content about {topic}",
            status=RunStatus.RUNNING,
            active_agents=[
                "realtime-conversation-host",
                "intent-router",
                "web-research-agent",
                "source-ledger-agent",
                "claim-verification-agent",
                "content-strategist",
                "eli5-short-form-writer",
                "substack-essay-writer",
                "editor-in-chief",
                "guardrails-agent",
                "forward-deployed-engineer",
            ],
            conversation_state={
                "topic": topic,
                "target_formats": request.target_formats,
                "modality": request.modality,
            },
        )
        await self._store.create_run(run)
        await self._store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="orchestration_started",
                actor="realtime-conversation-host",
                payload={
                    "topic": topic,
                    "target_formats": request.target_formats,
                    "modality": request.modality,
                },
            )
        )
        return run

    async def _record_turn(
        self, run: RunState, request: OrchestrationRequest
    ) -> ConversationTurn:
        turn = ConversationTurn(
            run_id=run.run_id,
            speaker=request.speaker,
            modality=request.modality,
            transcript=request.transcript,
            audio_uri=request.audio_uri,
            metadata={"workflow": "content_studio_v1"},
        )
        await self._store.record_conversation_turn(turn)
        await self._store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="conversation_turn_recorded",
                actor=request.speaker,
                payload=safe_realtime_metadata(turn.model_dump(mode="json")),
            )
        )
        return turn

    async def _route_tasks(
        self, run: RunState, request: OrchestrationRequest, topic: str
    ) -> list[AgentMessage]:
        messages = [
            AgentMessage(
                run_id=run.run_id,
                sender_agent_id="intent-router",
                recipient_agent_id="web-research-agent",
                task_type="research_topic",
                payload={"topic": topic, "freshness": "current"},
            ),
            AgentMessage(
                run_id=run.run_id,
                sender_agent_id="intent-router",
                recipient_agent_id="claim-verification-agent",
                task_type="verify_content_claims",
                payload={"topic": topic, "policy": "source_or_unsupported"},
            ),
            AgentMessage(
                run_id=run.run_id,
                sender_agent_id="intent-router",
                recipient_agent_id="content-strategist",
                task_type="create_content_brief",
                payload={
                    "topic": topic,
                    "target_formats": request.target_formats,
                    "style": (
                        "ELI5 for social posts and short-form; detailed plus "
                        "ELI5 for Substack"
                    ),
                },
            ),
            AgentMessage(
                run_id=run.run_id,
                sender_agent_id="content-strategist",
                recipient_agent_id="guardrails-agent",
                task_type="review_before_user_feedback",
                payload={"topic": topic, "required_gate": "claims_mapped_to_sources"},
                requires_human_feedback=request.require_human_feedback,
            ),
        ]
        for message in messages:
            await self._store.record_agent_message(message)
            await self._store.append_event(
                RunEvent(
                    run_id=run.run_id,
                    event_type="agent_message_accepted",
                    actor=message.sender_agent_id,
                    payload=public_a2a_message_event_payload(message),
                )
            )
        return messages

    async def _record_sources(
        self, run: RunState, topic: str
    ) -> list[SourceRecord]:
        search_sources, search_blocker_reason = await self._search_sources(run, topic)
        if search_sources:
            sources = search_sources
        else:
            sources = self._seed_sources(run, topic)
        for source in sources:
            await self._store.record_source(source)
            await self._store.append_event(
                RunEvent(
                    run_id=run.run_id,
                    event_type="source_recorded",
                    actor="source-ledger-agent",
                    payload=source.model_dump(mode="json"),
                )
            )
        if search_blocker_reason is not None:
            seed_source_count = sum(
                1 for source in sources if _source_requires_web_search(source)
            )
            await self._store.append_event(
                RunEvent(
                    run_id=run.run_id,
                    event_type="web_research_blocked",
                    actor="web-research-agent",
                    payload={
                        "query": topic,
                        "blocker": "web_search_provider_configuration",
                        "reason": search_blocker_reason,
                        "accepted_source_count": 0,
                        "seed_source_count": seed_source_count,
                        "fallback_source_count": len(sources),
                        "source_ids": [str(source.source_id) for source in sources],
                        "source_mode": "seed_sources_pending_web_search",
                    },
                )
            )
        return sources

    async def _search_sources(
        self, run: RunState, topic: str
    ) -> tuple[list[SourceRecord], str | None]:
        if not self._services.search_provider:
            return [], None

        try:
            results = await self._services.search_provider.search(
                SearchRequest(
                    query=topic,
                    freshness="current",
                    max_results=5,
                )
            )
        except ProviderConfigurationError as exc:
            safe_reason = _redact_provider_failure_text(str(exc))
            await self._store.append_event(
                RunEvent(
                    run_id=run.run_id,
                    event_type="provider_fallback",
                    actor="web-research-agent",
                    payload={"provider": "web_search", "reason": safe_reason},
                )
            )
            return [], safe_reason

        sources = []
        seen_urls = set()
        for index, result in enumerate(results, start=1):
            normalized_url = str(result.url).rstrip("/")
            if normalized_url in seen_urls:
                continue
            seen_urls.add(normalized_url)
            published_at = _parse_provider_datetime(result.published_at)
            retrieved_at = _parse_provider_datetime(result.retrieved_at)
            sources.append(
                SourceRecord(
                    run_id=run.run_id,
                    citation_id=f"S{len(sources) + 1}",
                    title=result.title,
                    url=result.url,
                    publisher=result.publisher,
                    retrieved_at=retrieved_at or datetime.now(timezone.utc),
                    published_at=published_at,
                    metadata={
                        "source_type": "web_search_result",
                        "snippet": result.snippet,
                        "published_at": result.published_at,
                        "retrieved_at": result.retrieved_at,
                        "search_query": topic,
                        "retriever": "web_search",
                        "search_rank": index,
                        "freshness": "current",
                        "max_results": 5,
                        "agent_id": "web-research-agent",
                    },
                )
            )
        await self._store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="web_research_completed",
                actor="web-research-agent",
                payload={
                    "query": topic,
                    "freshness": "current",
                    "max_results": 5,
                    "provider_result_count": len(results),
                    "accepted_source_count": len(sources),
                    "deduplicated_result_count": len(results) - len(sources),
                    "source_ids": [str(source.source_id) for source in sources],
                    "citation_ids": [source.citation_id for source in sources],
                    "source_titles": [source.title for source in sources],
                },
            )
        )
        return sources, None

    def _seed_sources(self, run: RunState, topic: str) -> list[SourceRecord]:
        query = quote_plus(topic)
        return [
            SourceRecord(
                run_id=run.run_id,
                citation_id="S1",
                title=f"Live web search required for {topic}",
                url=f"https://www.google.com/search?q={query}",
                publisher="Web search task",
                metadata={
                    "source_type": "search_query_seed",
                    "requires_web_search": True,
                    "search_query": topic,
                    "freshness": "current",
                    "max_results": 5,
                    "agent_id": "web-research-agent",
                },
            ),
            SourceRecord(
                run_id=run.run_id,
                citation_id="S2",
                title="Hugging Face Gemma 4 chat completion provider docs",
                url="https://huggingface.co/docs/inference-providers/tasks/chat-completion",
                publisher="Hugging Face",
                metadata={
                    "source_type": "provider_reference",
                    "agent_id": "source-ledger-agent",
                },
            ),
        ]

    async def _record_claims(
        self, run: RunState, topic: str, sources: list[SourceRecord]
    ) -> list[ClaimRecord]:
        grounding_source = sources[0]
        grounding_source_accepted = _source_can_support_claim(grounding_source)
        claims = [
            ClaimRecord(
                run_id=run.run_id,
                claim_text=(
                    f"Content about {topic} must be grounded in live source records "
                    "before final approval."
                ),
                support_status=(
                    ClaimSupportStatus.SUPPORTED
                    if grounding_source_accepted
                    else ClaimSupportStatus.NEEDS_REVIEW
                ),
                source_ids=[grounding_source.source_id],
                reviewer_agent_id="claim-verification-agent",
                notes=(
                    "Live source grounding was recorded."
                    if grounding_source_accepted
                    else (
                        "Search query seed is not accepted evidence; provider-backed "
                        "web research must refresh this claim before approval."
                    )
                ),
            ),
            ClaimRecord(
                run_id=run.run_id,
                claim_text=(
                    "Gemma 4 expert agents should handle reasoning, synthesis, "
                    "writing, critique, and multimodal review."
                ),
                support_status=ClaimSupportStatus.NEEDS_REVIEW,
                source_ids=[sources[-1].source_id],
                reviewer_agent_id="claim-verification-agent",
                notes="Provider reference is recorded; model-specific claim still requires current source review.",
            ),
        ]
        for claim in claims:
            await self._store.record_claim(claim)
            await self._store.append_event(
                RunEvent(
                    run_id=run.run_id,
                    event_type="claim_recorded",
                    actor="claim-verification-agent",
                    payload=claim.model_dump(mode="json"),
                )
            )
        return claims

    async def _record_content_pack(
        self,
        *,
        run: RunState,
        topic: str,
        request: OrchestrationRequest,
        sources: list[SourceRecord],
        claims: list[ClaimRecord],
    ) -> list[ArtifactRecord]:
        source_ids = [source.source_id for source in sources]
        claim_ids = [claim.claim_id for claim in claims]
        source_citations = _source_citations(sources)
        claim_trace = _claim_trace(claims, sources)
        content_pack = await self._build_content_pack(
            run=run,
            topic=topic,
            request=request,
            sources=sources,
            claim_ids=claim_ids,
        )
        grounding_contract = {
            "source_citations": source_citations,
            "claim_trace": claim_trace,
            "source_dependency_ids": [str(source_id) for source_id in source_ids],
            "claim_dependency_ids": [str(claim_id) for claim_id in claim_ids],
            "unsupported_claim_count": sum(
                1
                for claim in claims
                if claim.support_status == ClaimSupportStatus.UNSUPPORTED
            ),
            "claims_needing_review_count": sum(
                1
                for claim in claims
                if claim.support_status == ClaimSupportStatus.NEEDS_REVIEW
            ),
        }
        requested_formats = _requested_formats(request.target_formats)
        artifacts = []
        if "post" in requested_formats:
            artifacts.append(
                ArtifactRecord(
                    run_id=run.run_id,
                    artifact_type=ArtifactType.POST,
                    title=f"Social post draft: {topic}",
                    uri=f"artifact://runs/{run.run_id}/social-post-draft",
                    content=_content_with_grounding(
                        content_pack["post"], grounding_contract
                    ),
                    provenance=_artifact_provenance(
                        content_pack=content_pack,
                        agent_id="eli5-short-form-writer",
                        source_ids=source_ids,
                        claim_ids=claim_ids,
                        source_citations=source_citations,
                        claim_trace=claim_trace,
                    ),
                    source_ids=source_ids,
                    reviewer_decisions=[_initial_reviewer_decision()],
                    revision_history=[
                        {
                            "actor": "content-strategist",
                            "note": "Created first durable social post draft.",
                        }
                    ],
                )
            )
        if "reel" in requested_formats:
            artifacts.append(
                ArtifactRecord(
                    run_id=run.run_id,
                    artifact_type=ArtifactType.REEL_SCRIPT,
                    title=f"ELI5 reel draft: {topic}",
                    uri=f"artifact://runs/{run.run_id}/eli5-reel-draft",
                    content=_content_with_grounding(
                        content_pack["short_form"], grounding_contract
                    ),
                    provenance=_artifact_provenance(
                        content_pack=content_pack,
                        agent_id="eli5-short-form-writer",
                        source_ids=source_ids,
                        claim_ids=claim_ids,
                        source_citations=source_citations,
                        claim_trace=claim_trace,
                    ),
                    source_ids=source_ids,
                    reviewer_decisions=[_initial_reviewer_decision()],
                    revision_history=[
                        {
                            "actor": "content-strategist",
                            "note": "Created first durable ELI5 reel draft.",
                        }
                    ],
                )
            )
        if "substack" in requested_formats:
            artifacts.append(
                ArtifactRecord(
                    run_id=run.run_id,
                    artifact_type=ArtifactType.SUBSTACK_ARTICLE,
                    title=f"Substack draft: {topic}",
                    uri=f"artifact://runs/{run.run_id}/substack-draft",
                    content=_content_with_grounding(
                        content_pack["substack"], grounding_contract
                    ),
                    provenance=_artifact_provenance(
                        content_pack=content_pack,
                        agent_id="substack-essay-writer",
                        source_ids=source_ids,
                        claim_ids=claim_ids,
                        source_citations=source_citations,
                        claim_trace=claim_trace,
                    ),
                    source_ids=source_ids,
                    reviewer_decisions=[_initial_reviewer_decision()],
                    revision_history=[
                        {
                            "actor": "content-strategist",
                            "note": "Created first durable Substack draft.",
                        }
                    ],
                )
            )
        for artifact in artifacts:
            await self._store.record_artifact(artifact)
            await self._store.append_event(
                RunEvent(
                    run_id=run.run_id,
                    event_type="artifact_recorded",
                    actor="artifact-librarian",
                    payload=artifact.model_dump(mode="json"),
                )
            )
        await self._store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="artifact_grounding_contract_recorded",
                actor="source-ledger-agent",
                payload={
                    "artifact_ids": [
                        str(artifact.artifact_id) for artifact in artifacts
                    ],
                    "artifact_count": len(artifacts),
                    "source_count": len(sources),
                    "claim_count": len(claims),
                    "source_citation_ids": [
                        source["citation_id"] for source in source_citations
                    ],
                    "claims_needing_review_count": grounding_contract[
                        "claims_needing_review_count"
                    ],
                    "unsupported_claim_count": grounding_contract[
                        "unsupported_claim_count"
                    ],
                },
            )
        )
        return artifacts

    async def _build_content_pack(
        self,
        *,
        run: RunState,
        topic: str,
        request: OrchestrationRequest,
        sources: list[SourceRecord],
        claim_ids: list,
    ) -> dict:
        if self._services.gemma_provider:
            source_evidence = _source_evidence(sources)
            try:
                gemma_response = await self._services.gemma_provider.complete(
                    GemmaRequest(
                        model_id="google/gemma-4-31b-it",
                        agent_id="content-strategist",
                        system_context=(
                            "Create source-backed social content. Include social "
                            "posts, short-form ELI5, and Substack detailed plus "
                            "ELI5 when requested. Return concise drafts."
                        ),
                        user_input=(
                            f"Topic: {topic}\n"
                            f"Transcript: {request.transcript}\n"
                            "Source evidence JSON: "
                            f"{json.dumps(source_evidence, sort_keys=True)}\n"
                            f"Formats: {request.target_formats}"
                        ),
                        metadata={"workflow": "content_studio_v1"},
                    )
                )
                await self._store.append_event(
                    RunEvent(
                        run_id=run.run_id,
                        event_type="gemma_synthesis_completed",
                        actor="content-strategist",
                        payload={
                            "model_id": gemma_response.model_id,
                            "agent_id": gemma_response.agent_id,
                            "usage": gemma_response.usage,
                        },
                    )
                )
                return _provider_content_pack(
                    topic=topic,
                    target_formats=request.target_formats,
                    gemma_content=gemma_response.content,
                    source_count=len(sources),
                    claim_ids=claim_ids,
                    source_titles=[source.title for source in sources],
                    source_evidence=source_evidence,
                    transcript=request.transcript,
                    model_id=gemma_response.model_id,
                    usage=gemma_response.usage,
                )
            except ProviderConfigurationError as exc:
                safe_reason = _redact_provider_failure_text(str(exc))
                await self._store.append_event(
                    RunEvent(
                        run_id=run.run_id,
                        event_type="provider_fallback",
                        actor="content-strategist",
                        payload={"provider": "gemma", "reason": safe_reason},
                    )
                )

        return _deterministic_content_pack(
            topic=topic,
            target_formats=request.target_formats,
            claim_ids=claim_ids,
            source_titles=[source.title for source in sources],
            source_evidence=_source_evidence(sources),
            transcript=request.transcript,
        )

    async def _open_review_loop_if_needed(
        self, run: RunState, request: OrchestrationRequest
    ) -> bool:
        if not request.require_human_feedback:
            await self._store.append_event(
                RunEvent(
                    run_id=run.run_id,
                    event_type="orchestration_completed",
                    actor="product-manager",
                    payload={"feedback_gate_opened": False},
                )
            )
            return False

        await self._store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="human_feedback_gate_opened",
                actor="forward-deployed-engineer",
                payload={
                    "question": "Review the first content pack and provide direction for the next revision."
                },
            )
        )
        return True


def _deterministic_content_pack(
    *,
    topic: str,
    target_formats: list[str],
    claim_ids: list,
    source_titles: list[str],
    source_evidence: list[dict[str, Any]],
    transcript: str,
) -> dict:
    return {
        "generation_mode": "deterministic_fallback",
        "model_provider": "deterministic_fallback",
        "model_id": "local-deterministic-content-template",
        "provider_usage": {},
        "prompt_input": {
            "topic": topic,
            "transcript": transcript,
            "target_formats": target_formats,
            "source_titles": source_titles,
            "source_evidence": source_evidence,
            "claim_ids": [str(claim_id) for claim_id in claim_ids],
        },
        "topic": topic,
        "formats": target_formats,
        "post": {
            "generation_mode": "deterministic_fallback",
            "format": "social_post",
            "hook": (
                f"ELI5: {topic} is easier to trust when every big claim "
                "points back to a source."
            ),
            "body": (
                f"Think of {topic} like a studio team: one person explains it "
                "simply, one checks the evidence, and one keeps the final post "
                "honest about what is still uncertain."
            ),
            "cta": "Ask for the source ledger before treating the draft as final.",
            "hashtags": ["#AI", "#LLMs", "#SourceBacked"],
            "claim_ids": [str(claim_id) for claim_id in claim_ids],
        },
        "short_form": {
            "generation_mode": "deterministic_fallback",
            "hook": f"Explain {topic} like I am five, but keep the facts real.",
            "beats": [
                "Start with a concrete everyday analogy.",
                "Show why the topic matters right now.",
                "Name the one caveat the audience should remember.",
                "Invite feedback or a follow-up question.",
            ],
            "claim_ids": [str(claim_id) for claim_id in claim_ids],
        },
        "substack": {
            "generation_mode": "deterministic_fallback",
            "title": f"{topic}: ELI5 first, details second",
            "sections": [
                "ELI5 summary",
                "What is actually happening",
                "Real-world data and sources to verify",
                "Risks, caveats, and what is still unknown",
                "Practical takeaways",
            ],
            "claim_ids": [str(claim_id) for claim_id in claim_ids],
        },
    }


def _provider_content_pack(
    *,
    topic: str,
    target_formats: list[str],
    gemma_content: str,
    source_count: int,
    claim_ids: list,
    source_titles: list[str],
    source_evidence: list[dict[str, Any]],
    transcript: str,
    model_id: str,
    usage: dict[str, Any],
) -> dict:
    return {
        "generation_mode": "gemma_provider",
        "model_provider": "huggingface",
        "model_id": model_id,
        "provider_usage": usage,
        "prompt_input": {
            "topic": topic,
            "transcript": transcript,
            "target_formats": target_formats,
            "source_titles": source_titles,
            "source_evidence": source_evidence,
            "claim_ids": [str(claim_id) for claim_id in claim_ids],
        },
        "topic": topic,
        "formats": target_formats,
        "post": {
            "generation_mode": "gemma_provider",
            "draft": gemma_content,
            "source_count": source_count,
            "claim_ids": [str(claim_id) for claim_id in claim_ids],
        },
        "short_form": {
            "generation_mode": "gemma_provider",
            "draft": gemma_content,
            "source_count": source_count,
            "claim_ids": [str(claim_id) for claim_id in claim_ids],
        },
        "substack": {
            "generation_mode": "gemma_provider",
            "draft": gemma_content,
            "source_count": source_count,
            "claim_ids": [str(claim_id) for claim_id in claim_ids],
        },
    }


def _source_citations(sources: list[SourceRecord]) -> list[dict[str, Any]]:
    return [
        {
            "source_id": str(source.source_id),
            "citation_id": source.citation_id,
            "title": source.title,
            "url": str(source.url),
            "publisher": source.publisher,
            "source_type": str(
                (source.metadata or {}).get("source_type") or "manual_source"
            ),
            "retrieved_at": source.retrieved_at.isoformat(),
            "published_at": (
                source.published_at.isoformat() if source.published_at else None
            ),
        }
        for source in sources
    ]


def _source_evidence(sources: list[SourceRecord]) -> list[dict[str, Any]]:
    evidence = []
    for source in sources:
        metadata = source.metadata or {}
        evidence.append(
            {
                "source_id": str(source.source_id),
                "citation_id": source.citation_id,
                "title": source.title,
                "url": str(source.url),
                "publisher": source.publisher,
                "source_type": str(metadata.get("source_type") or "manual_source"),
                "snippet": metadata.get("snippet"),
                "published_at": _source_published_at(source),
                "retrieved_at": source.retrieved_at.isoformat(),
                "search_query": metadata.get("search_query"),
            }
        )
    return evidence


def _parse_provider_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _source_published_at(source: SourceRecord) -> str | None:
    if source.published_at:
        return source.published_at.isoformat()
    published_at = (source.metadata or {}).get("published_at")
    parsed = _parse_provider_datetime(published_at)
    if parsed:
        return parsed.isoformat()
    return str(published_at) if published_at else None


def _source_can_support_claim(source: SourceRecord) -> bool:
    if _source_requires_web_search(source):
        return False
    return True


def _source_requires_web_search(source: SourceRecord) -> bool:
    metadata = source.metadata or {}
    if metadata.get("source_type") == "search_query_seed":
        return True
    if bool(metadata.get("requires_web_search")):
        return True
    return False


def _claim_trace(
    claims: list[ClaimRecord], sources: list[SourceRecord]
) -> list[dict[str, Any]]:
    source_by_id = {source.source_id: source for source in sources}
    return [
        {
            "claim_id": str(claim.claim_id),
            "claim_text": claim.claim_text,
            "support_status": claim.support_status.value,
            "source_ids": [str(source_id) for source_id in claim.source_ids],
            "source_citation_ids": [
                source_by_id[source_id].citation_id
                for source_id in claim.source_ids
                if source_id in source_by_id
            ],
            "unsupported": claim.support_status == ClaimSupportStatus.UNSUPPORTED,
            "needs_review": claim.support_status == ClaimSupportStatus.NEEDS_REVIEW,
            "reviewer_agent_id": claim.reviewer_agent_id,
            "notes": claim.notes,
        }
        for claim in claims
    ]


def _content_with_grounding(
    content: dict[str, Any], grounding_contract: dict[str, Any]
) -> dict[str, Any]:
    return {
        **content,
        "source_citations": grounding_contract["source_citations"],
        "claim_trace": grounding_contract["claim_trace"],
        "source_dependency_ids": grounding_contract["source_dependency_ids"],
        "claim_dependency_ids": grounding_contract["claim_dependency_ids"],
        "claims_needing_review_count": grounding_contract[
            "claims_needing_review_count"
        ],
        "unsupported_claim_count": grounding_contract["unsupported_claim_count"],
    }


def _artifact_provenance(
    *,
    content_pack: dict[str, Any],
    agent_id: str,
    source_ids: list,
    claim_ids: list,
    source_citations: list[dict[str, Any]],
    claim_trace: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "workflow": "content_studio_v1",
        "agent_id": agent_id,
        "source_ids": [str(source_id) for source_id in source_ids],
        "claim_ids": [str(claim_id) for claim_id in claim_ids],
        "source_citation_ids": [
            source["citation_id"] for source in source_citations
        ],
        "source_dependency_ids": [str(source_id) for source_id in source_ids],
        "claim_trace": claim_trace,
        "generation_mode": content_pack["generation_mode"],
        "model_provider": content_pack["model_provider"],
        "model_id": content_pack["model_id"],
        "provider_usage": content_pack["provider_usage"],
        "prompt_input": content_pack["prompt_input"],
        "grounding_contract": {
            "source_count": len(source_citations),
            "claim_count": len(claim_trace),
            "requires_claim_review": any(
                claim["needs_review"] or claim["unsupported"]
                for claim in claim_trace
            ),
        },
    }


def _initial_reviewer_decision() -> dict[str, str]:
    return {
        "reviewer_agent_id": "guardrails-agent",
        "decision": "needs_revision",
        "reason": (
            "First draft must pass claim verification, source ledger review, "
            "and human feedback before publishing."
        ),
    }


def _redact_provider_failure_text(value: str) -> str:
    redacted = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [redacted]", value)
    redacted = re.sub(r"hf_[A-Za-z0-9]{20,}", "hf_[redacted]", redacted)
    redacted = re.sub(r"tvly-[A-Za-z0-9-]{20,}", "tvly-[redacted]", redacted)
    return redacted


def _requested_formats(target_formats: list[str]) -> set[str]:
    aliases = {
        "post": "post",
        "posts": "post",
        "social": "post",
        "social_post": "post",
        "social-post": "post",
        "caption": "post",
        "captions": "post",
        "reel": "reel",
        "reels": "reel",
        "short": "reel",
        "short_form": "reel",
        "short-form": "reel",
        "substack": "substack",
        "essay": "substack",
        "article": "substack",
        "longform": "substack",
        "long-form": "substack",
    }
    normalized = {
        aliases[format_name.strip().lower()]
        for format_name in target_formats
        if format_name.strip().lower() in aliases
    }
    if normalized:
        return normalized
    return set(DEFAULT_TARGET_FORMATS)


def _derive_topic(transcript: str) -> str:
    cleaned = " ".join(transcript.strip().split())
    if len(cleaned) <= 90:
        return cleaned
    return cleaned[:87].rstrip() + "..."
