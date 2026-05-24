from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from all_about_llms.agents import get_agent_card
from all_about_llms.contracts import (
    AgentMemory,
    AgentMessage,
    ArtifactRecord,
    ArtifactType,
    FeedbackItem,
    FeedbackRoutingResult,
    FeedbackStatus,
    RunEvent,
)
from all_about_llms.orchestration.a2a_projection import (
    public_a2a_message_event_payload,
)
from all_about_llms.realtime_safety import safe_realtime_metadata


class FeedbackRoutingError(RuntimeError):
    """Base error for durable feedback routing."""


class FeedbackRoutingRunNotFoundError(FeedbackRoutingError):
    """Raised when feedback references a missing run."""


class FeedbackRoutingAgentNotFoundError(FeedbackRoutingError):
    """Raised when feedback targets an unknown agent."""


FOCUS_AGENT_MAP = {
    "architecture": "principal-software-engineer",
    "audio": "audio-producer",
    "claim": "claim-verification-agent",
    "content": "content-strategist",
    "conversation": "realtime-conversation-host",
    "data": "data-analyst-agent",
    "design": "lead-ui-ux-designer",
    "feedback": "forward-deployed-engineer",
    "guardrail": "guardrails-agent",
    "image": "image-generation-agent",
    "observability": "observability-agent",
    "outreach": "outreach-agent",
    "planning": "interactive-systems-designer",
    "platform": "platform-optimization-agent",
    "protocol": "a2a-protocol-agent",
    "progress": "sprint-progress-agent",
    "research": "web-research-agent",
    "realtime": "realtime-conversation-host",
    "source": "source-ledger-agent",
    "substack": "substack-essay-writer",
    "ui": "lead-ui-ux-designer",
    "ux": "lead-ui-ux-designer",
    "video": "video-reel-producer",
    "visual": "visual-director",
    "voice": "realtime-conversation-host",
}


KEYWORD_AGENT_MAP = (
    (("citation", "source", "sources", "ledger", "provenance"), "source-ledger-agent"),
    (
        ("claim", "fact", "factual", "verify", "unsupported"),
        "claim-verification-agent",
    ),
    (("research", "web", "freshness", "latest", "data source"), "web-research-agent"),
    (("guardrail", "risk", "policy", "safety", "copyright"), "guardrails-agent"),
    (("observability", "trace", "health", "latency", "cost"), "observability-agent"),
    (("audio", "tts", "voiceover", "pacing", "sound"), "audio-producer"),
    (
        ("realtime", "conversation", "interrupt", "turn-taking", "voice chat"),
        "realtime-conversation-host",
    ),
    (("a2a", "agent card", "handoff", "message contract"), "a2a-protocol-agent"),
    (("visual", "thumbnail", "image", "asset", "diagram"), "visual-director"),
    (("ui", "ux", "cockpit", "interface", "layout"), "lead-ui-ux-designer"),
    (
        ("planning html", "system design", "animation", "diagram"),
        "interactive-systems-designer",
    ),
    (("substack", "essay", "long-form", "article"), "substack-essay-writer"),
    (("eli5", "caption", "carousel", "short-form"), "eli5-short-form-writer"),
    (("hook", "script", "retention", "spoken"), "script-doctor"),
    (("hashtag", "keyword", "audience", "influencer"), "influencer-strategy-agent"),
    (("platform", "instagram", "tiktok", "linkedin", "youtube"), "platform-optimization-agent"),
    (("outreach", "community", "collaboration"), "outreach-agent"),
    (("video", "reel", "storyboard", "subtitle"), "video-reel-producer"),
    (("progress", "sprint", "timeline", "decision log"), "sprint-progress-agent"),
    (("architecture", "backend", "orchestration", "postgres"), "principal-software-engineer"),
)


FEEDBACK_TARGET_ARTIFACT_TYPES = {
    ArtifactType.POST,
    ArtifactType.REEL_SCRIPT,
    ArtifactType.SUBSTACK_ARTICLE,
    ArtifactType.SOCIAL_PACKAGE,
    ArtifactType.VISUAL_BRIEF,
    ArtifactType.IMAGE,
    ArtifactType.AUDIO,
    ArtifactType.VIDEO,
}

ARTIFACT_TARGETING_AGENTS = {
    "audio-producer",
    "claim-verification-agent",
    "content-strategist",
    "editor-in-chief",
    "eli5-short-form-writer",
    "guardrails-agent",
    "image-generation-agent",
    "influencer-strategy-agent",
    "outreach-agent",
    "platform-optimization-agent",
    "script-doctor",
    "source-ledger-agent",
    "substack-essay-writer",
    "video-reel-producer",
    "visual-director",
}


class FeedbackRoutingWorkflow:
    """Convert human feedback into specialist A2A work and reusable memories."""

    def __init__(self, store):
        self._store = store

    async def run(self, feedback: FeedbackItem) -> FeedbackRoutingResult:
        run = await self._store.get_run(feedback.run_id)
        if run is None:
            raise FeedbackRoutingRunNotFoundError(
                f"Run not found: {feedback.run_id}"
            )

        routed_agent_id, route_reason = _select_recipient(feedback)
        target_artifacts, target_selection = await _select_target_artifacts(
            self._store,
            feedback=feedback,
            routed_agent_id=routed_agent_id,
        )
        routed_at = datetime.now(timezone.utc)
        routed_feedback = feedback.model_copy(
            update={
                "target_agent_id": routed_agent_id,
                "status": FeedbackStatus.ROUTED,
                "updated_at": routed_at,
                "metadata": {
                    **feedback.metadata,
                    "routing_workflow": "feedback_routing_v1",
                    "routed_by": "forward-deployed-engineer",
                    "routed_to": routed_agent_id,
                    "route_reason": route_reason,
                    "routed_at": routed_at.isoformat(),
                    **_target_artifact_metadata(
                        target_artifacts,
                        target_selection=target_selection,
                    ),
                },
            }
        )

        await self._store.record_feedback(routed_feedback)
        feedback_event = await self._store.append_event(
            RunEvent(
                run_id=routed_feedback.run_id,
                event_type="feedback_recorded",
                actor="forward-deployed-engineer",
                payload=safe_realtime_metadata(
                    routed_feedback.model_dump(mode="json")
                ),
            )
        )

        message = _build_agent_message(
            routed_feedback,
            route_reason,
            target_artifacts=target_artifacts,
        )
        await self._store.record_agent_message(message)
        message_event = await self._store.append_event(
            RunEvent(
                run_id=routed_feedback.run_id,
                event_type="agent_message_accepted",
                actor=message.sender_agent_id,
                payload=public_a2a_message_event_payload(message),
            )
        )

        support_messages, support_message_events = await self._record_support_tasks(
            feedback=routed_feedback,
            primary_message=message,
            route_reason=route_reason,
        )

        memories, memory_events = await self._record_feedback_memories(
            feedback=routed_feedback,
            message=message,
            route_reason=route_reason,
        )

        routed_event = await self._store.append_event(
            RunEvent(
                run_id=routed_feedback.run_id,
                event_type="feedback_routed",
                actor="forward-deployed-engineer",
                payload=safe_realtime_metadata(
                    {
                        "feedback_id": str(routed_feedback.feedback_id),
                        "routed_agent_id": routed_agent_id,
                        "route_reason": route_reason,
                        "task_message_id": str(message.message_id),
                        **_target_context_payload(routed_feedback),
                        "support_task_message_ids": [
                            str(support_message.message_id)
                            for support_message in support_messages
                        ],
                        "memory_ids": [
                            str(memory.memory_id) for memory in memories
                        ],
                    }
                ),
            )
        )

        event_ids = [
            event_id
            for event_id in [
                feedback_event.event_id,
                message_event.event_id,
                *[event.event_id for event in support_message_events],
                *[event.event_id for event in memory_events],
                routed_event.event_id,
            ]
            if event_id is not None
        ]
        return FeedbackRoutingResult(
            feedback=routed_feedback,
            routed_agent_id=routed_agent_id,
            route_reason=route_reason,
            task_message_id=message.message_id,
            support_task_message_ids=[
                support_message.message_id for support_message in support_messages
            ],
            memory_ids=[memory.memory_id for memory in memories],
            event_ids=event_ids,
            summary=(
                f"Routed feedback {routed_feedback.feedback_id} to "
                f"{routed_agent_id}, created {len(support_messages)} support "
                f"task(s), and recorded {len(memories)} memory note(s)."
            ),
        )

    async def _record_support_tasks(
        self,
        *,
        feedback: FeedbackItem,
        primary_message: AgentMessage,
        route_reason: str,
    ) -> tuple[list[AgentMessage], list[RunEvent]]:
        support_specs = [
            (
                "interactive-note-taking-agent",
                "record_routed_feedback_note",
                "Record this routed feedback in the next interactive run note.",
            ),
            (
                "sprint-progress-agent",
                "track_routed_feedback_work_item",
                "Add this routed feedback to the next progress/work-plan pass.",
            ),
        ]
        existing_keys = {
            (
                existing.recipient_agent_id,
                existing.task_type,
                existing.payload.get("feedback_id"),
            )
            for existing in await self._store.list_agent_messages(feedback.run_id)
        }
        support_messages: list[AgentMessage] = []
        support_events: list[RunEvent] = []
        for recipient_agent_id, task_type, instruction in support_specs:
            key = (recipient_agent_id, task_type, str(feedback.feedback_id))
            if key in existing_keys:
                continue
            support_message = AgentMessage(
                run_id=feedback.run_id,
                sender_agent_id="forward-deployed-engineer",
                recipient_agent_id=recipient_agent_id,
                task_type=task_type,
                payload={
                    "workflow": "feedback_routing_support_v1",
                    "feedback_id": str(feedback.feedback_id),
                    "primary_task_message_id": str(primary_message.message_id),
                    "routed_agent_id": primary_message.recipient_agent_id,
                    "route_reason": route_reason,
                    "feedback_text": feedback.feedback_text,
                    "author": feedback.author,
                    "feedback_metadata": feedback.metadata,
                    **_target_context_payload(feedback),
                    "title": "Routed feedback note",
                    "instruction": instruction,
                },
            )
            await self._store.record_agent_message(support_message)
            event = await self._store.append_event(
                RunEvent(
                    run_id=feedback.run_id,
                    event_type="agent_message_accepted",
                    actor=support_message.sender_agent_id,
                    payload=public_a2a_message_event_payload(support_message),
                )
            )
            support_messages.append(support_message)
            support_events.append(event)
        return support_messages, support_events

    async def _record_feedback_memories(
        self,
        *,
        feedback: FeedbackItem,
        message: AgentMessage,
        route_reason: str,
    ) -> tuple[list[AgentMemory], list[RunEvent]]:
        memory_agents = _unique_memory_agents(
            [
                (
                    feedback.target_agent_id or message.recipient_agent_id,
                    "routed_feedback",
                ),
                ("interactive-note-taking-agent", "feedback_note"),
                ("sprint-progress-agent", "feedback_work_item"),
            ]
        )
        memories: list[AgentMemory] = []
        events: list[RunEvent] = []
        for agent_id, memory_kind in memory_agents:
            memory = AgentMemory(
                agent_id=agent_id,
                run_id=feedback.run_id,
                memory_kind=memory_kind,
                content=_memory_content(feedback, agent_id, route_reason),
                metadata={
                    "feedback_id": str(feedback.feedback_id),
                    "task_message_id": str(message.message_id),
                    "routed_agent_id": message.recipient_agent_id,
                    "route_reason": route_reason,
                    "routing_workflow": "feedback_routing_v1",
                    "feedback_author": feedback.author,
                    **_target_context_payload(feedback),
                },
            )
            await self._store.record_memory(memory)
            event = await self._store.append_event(
                RunEvent(
                    run_id=feedback.run_id,
                    event_type="memory_recorded",
                    actor=memory.agent_id,
                    payload=safe_realtime_metadata(memory.model_dump(mode="json")),
                )
            )
            memories.append(memory)
            events.append(event)
        return memories, events


def _select_recipient(feedback: FeedbackItem) -> tuple[str, str]:
    explicit_target = feedback.target_agent_id or _metadata_string(
        feedback.metadata,
        "target_agent_id",
        "route_to",
        "agent_id",
    )
    if explicit_target:
        agent_id = explicit_target.strip()
        if get_agent_card(agent_id) is None:
            raise FeedbackRoutingAgentNotFoundError(f"Agent not found: {agent_id}")
        return agent_id, "explicit_agent_target"

    focus = _metadata_string(feedback.metadata, "focus", "category", "area")
    if focus:
        focus_key = focus.lower().strip()
        if focus_key in FOCUS_AGENT_MAP:
            return FOCUS_AGENT_MAP[focus_key], f"metadata_focus:{focus_key}"
        for keyword, agent_id in FOCUS_AGENT_MAP.items():
            if keyword in focus_key:
                return agent_id, f"metadata_focus_keyword:{keyword}"

    searchable_text = _searchable_text(feedback)
    for keywords, agent_id in KEYWORD_AGENT_MAP:
        for keyword in keywords:
            if keyword in searchable_text:
                return agent_id, f"feedback_keyword:{keyword}"
    return "product-manager", "default_product_triage"


def _build_agent_message(
    feedback: FeedbackItem,
    route_reason: str,
    *,
    target_artifacts: list[ArtifactRecord],
) -> AgentMessage:
    return AgentMessage(
        run_id=feedback.run_id,
        sender_agent_id="forward-deployed-engineer",
        recipient_agent_id=feedback.target_agent_id or "product-manager",
        task_type="incorporate_human_feedback",
        payload={
            "feedback_id": str(feedback.feedback_id),
            "feedback_text": feedback.feedback_text,
            "author": feedback.author,
            "route_reason": route_reason,
            "feedback_metadata": feedback.metadata,
            **_target_context_payload(feedback),
            "target_artifacts": [
                _target_artifact_packet(artifact) for artifact in target_artifacts
            ],
            "instruction": (
                "Review the human feedback, decide the concrete next change, "
                "and update the run through durable artifacts, tasks, or notes."
            ),
        },
    )


async def _select_target_artifacts(
    store,
    *,
    feedback: FeedbackItem,
    routed_agent_id: str,
) -> tuple[list[ArtifactRecord], str]:
    artifacts = await store.list_artifacts(feedback.run_id)
    explicit_ids = _explicit_artifact_ids(feedback.metadata)
    if explicit_ids:
        return (
            [
                artifact
                for artifact in artifacts
                if artifact.artifact_id in explicit_ids
            ],
            "explicit_metadata",
        )
    if not _should_auto_target_artifacts(feedback, routed_agent_id):
        return [], "not_applicable"
    leaf_artifacts = _leaf_target_artifacts(artifacts)
    return leaf_artifacts[-3:], "latest_publishable_artifacts"


def _explicit_artifact_ids(metadata: dict[str, Any]) -> set[UUID]:
    raw_values: list[Any] = []
    for key in (
        "artifact_id",
        "target_artifact_id",
        "artifact_ids",
        "target_artifact_ids",
        "source_artifact_ids",
    ):
        value = metadata.get(key)
        if isinstance(value, list):
            raw_values.extend(value)
        elif value:
            raw_values.append(value)
    artifact_ids = set()
    for raw_value in raw_values:
        try:
            artifact_ids.add(UUID(str(raw_value)))
        except (TypeError, ValueError):
            continue
    return artifact_ids


def _should_auto_target_artifacts(
    feedback: FeedbackItem,
    routed_agent_id: str,
) -> bool:
    if routed_agent_id in ARTIFACT_TARGETING_AGENTS:
        return True
    searchable_text = _searchable_text(feedback)
    return any(
        term in searchable_text
        for term in (
            "artifact",
            "caption",
            "draft",
            "hook",
            "post",
            "reel",
            "script",
            "substack",
            "thumbnail",
            "voiceover",
        )
    )


def _leaf_target_artifacts(artifacts: list[ArtifactRecord]) -> list[ArtifactRecord]:
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
        if artifact.artifact_type in FEEDBACK_TARGET_ARTIFACT_TYPES
        and artifact.artifact_id not in parent_ids
    ]


def _target_artifact_metadata(
    target_artifacts: list[ArtifactRecord],
    *,
    target_selection: str,
) -> dict[str, Any]:
    if not target_artifacts:
        return {
            "target_artifact_selection": target_selection,
            "target_artifact_count": 0,
            "target_artifact_ids": [],
            "target_artifact_titles": [],
            "target_artifact_types": [],
            "target_artifact_source_ids": [],
            "target_artifact_claim_ids": [],
        }
    source_ids = sorted(
        {
            str(source_id)
            for artifact in target_artifacts
            for source_id in artifact.source_ids
        }
    )
    claim_ids = sorted(
        {
            str(claim_id)
            for artifact in target_artifacts
            for claim_id in _artifact_claim_ids(artifact)
        }
    )
    return {
        "target_artifact_selection": target_selection,
        "target_artifact_count": len(target_artifacts),
        "target_artifact_ids": [
            str(artifact.artifact_id) for artifact in target_artifacts
        ],
        "target_artifact_titles": [artifact.title for artifact in target_artifacts],
        "target_artifact_types": [
            artifact.artifact_type.value for artifact in target_artifacts
        ],
        "target_artifact_source_ids": source_ids,
        "target_artifact_claim_ids": claim_ids,
    }


def _target_context_payload(feedback: FeedbackItem) -> dict[str, Any]:
    artifact_ids = _metadata_list(feedback.metadata, "target_artifact_ids")
    source_ids = _metadata_list(
        feedback.metadata,
        "target_artifact_source_ids",
        "target_source_ids",
    )
    claim_ids = _metadata_list(
        feedback.metadata,
        "target_artifact_claim_ids",
        "target_claim_ids",
    )
    return {
        "target_artifact_selection": _metadata_string(
            feedback.metadata,
            "target_artifact_selection",
        ),
        "target_artifact_count": _metadata_int(
            feedback.metadata,
            "target_artifact_count",
            default=len(artifact_ids),
        ),
        "target_artifact_ids": artifact_ids,
        "target_artifact_titles": _metadata_list(
            feedback.metadata,
            "target_artifact_titles",
        ),
        "target_artifact_types": _metadata_list(
            feedback.metadata,
            "target_artifact_types",
        ),
        "target_artifact_source_ids": source_ids,
        "target_artifact_claim_ids": claim_ids,
        "target_source_ids": source_ids,
        "target_claim_ids": claim_ids,
    }


def _target_artifact_packet(artifact: ArtifactRecord) -> dict[str, Any]:
    return {
        "artifact_id": str(artifact.artifact_id),
        "artifact_type": artifact.artifact_type.value,
        "title": artifact.title,
        "uri": artifact.uri,
        "source_ids": [str(source_id) for source_id in artifact.source_ids],
        "claim_ids": [str(claim_id) for claim_id in _artifact_claim_ids(artifact)],
        "generation_mode": artifact.provenance.get("generation_mode"),
        "workflow": artifact.provenance.get("workflow"),
    }


def _artifact_claim_ids(artifact: ArtifactRecord) -> list[UUID]:
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


def _unique_memory_agents(items: list[tuple[str, str]]) -> list[tuple[str, str]]:
    unique: list[tuple[str, str]] = []
    seen: set[str] = set()
    for agent_id, memory_kind in items:
        if agent_id in seen:
            continue
        unique.append((agent_id, memory_kind))
        seen.add(agent_id)
    return unique


def _memory_content(
    feedback: FeedbackItem,
    agent_id: str,
    route_reason: str,
) -> str:
    agent_card = get_agent_card(agent_id)
    agent_name = agent_card.name if agent_card else agent_id
    return (
        f"Feedback from {feedback.author} routed to {agent_name}. "
        f"Reason: {route_reason}. Feedback: {feedback.feedback_text}"
    )


def _metadata_string(metadata: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _metadata_list(metadata: dict[str, Any], *keys: str) -> list[str]:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, list):
            values = []
            for item in value:
                if item is None:
                    continue
                text = str(item).strip()
                if text:
                    values.append(text)
            return values
        if value:
            text = str(value).strip()
            return [text] if text else []
    return []


def _metadata_int(
    metadata: dict[str, Any],
    key: str,
    *,
    default: int = 0,
) -> int:
    value = metadata.get(key)
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _searchable_text(feedback: FeedbackItem) -> str:
    metadata_values = [
        str(value)
        for value in feedback.metadata.values()
        if isinstance(value, str | int | float | bool)
    ]
    return " ".join([feedback.feedback_text, *metadata_values]).lower()
