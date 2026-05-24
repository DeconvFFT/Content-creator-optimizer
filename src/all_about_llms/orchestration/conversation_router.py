from typing import Any
from uuid import UUID

from all_about_llms.contracts import (
    AgentMessage,
    ArtifactRecord,
    ArtifactType,
    ConversationRouteIntent,
    ConversationRouteRequest,
    ConversationRouteResult,
    ConversationTurn,
    MultimodalIntakeRequest,
    MultimodalIntakeResult,
    OrchestrationRequest,
    RevisionRequest,
    RunEvent,
    RunState,
    RunStatus,
)
from all_about_llms.orchestration.a2a_projection import (
    public_a2a_message_event_payload,
)
from all_about_llms.orchestration.content_workflow import ContentStudioWorkflow
from all_about_llms.orchestration.multimodal_intake import MultimodalIntakeWorkflow
from all_about_llms.orchestration.revision_workflow import (
    RevisionWorkflow,
)
from all_about_llms.orchestration.services import ContentWorkflowServices
from all_about_llms.realtime_safety import safe_realtime_metadata


class ConversationRouterRunNotFoundError(RuntimeError):
    """Raised when a conversational turn references a missing run."""


class ConversationRouterRevisionUnavailableError(RuntimeError):
    """Raised when forced feedback routing has no artifacts to revise."""


class ConversationRouter:
    """Route one natural voice/text turn into durable studio work."""

    def __init__(self, store, services: ContentWorkflowServices | None = None):
        self._store = store
        self._services = services or ContentWorkflowServices()

    async def route(self, request: ConversationRouteRequest) -> ConversationRouteResult:
        if request.run_id is None:
            return await self._start_content_run(request)

        run = await self._store.get_run(request.run_id)
        if run is None:
            raise ConversationRouterRunNotFoundError(
                f"Run not found: {request.run_id}"
            )

        artifacts = await self._store.list_artifacts(run.run_id)
        routed_intent = _resolve_intent(
            request=request,
            run=run,
            artifact_count=len(artifacts),
        )
        turn = await self._record_turn(run, request, routed_intent)

        if routed_intent == ConversationRouteIntent.REVISE_CONTENT:
            if not artifacts:
                if request.intent == ConversationRouteIntent.REVISE_CONTENT:
                    raise ConversationRouterRevisionUnavailableError(
                        "No content artifacts are available for revision."
                    )
                return await self._route_task(run, turn, request, routed_intent)
            return await self._revise_content(
                run,
                turn,
                request,
                routed_intent,
                artifacts=artifacts,
            )

        if routed_intent == ConversationRouteIntent.RECORD_ONLY:
            multimodal_intake = await self._record_multimodal_intake(
                run=run,
                turn=turn,
                request=request,
            )
            intake_task_message_ids = (
                multimodal_intake.task_message_ids if multimodal_intake else []
            )
            intake_artifact_ids = (
                [multimodal_intake.intake_artifact_id]
                if multimodal_intake and multimodal_intake.intake_artifact_id
                else []
            )
            response_text = (
                "I recorded that turn and routed the attached multimodal references."
                if multimodal_intake
                else "I recorded that turn on the durable run."
            )
            response_turn = await self._record_assistant_reply(
                run=run,
                user_turn=turn,
                response_text=response_text,
                routed_intent=routed_intent,
                action="record_only",
            )
            await self._append_route_event(
                run=run,
                turn=turn,
                response_turn=response_turn,
                requested_intent=request.intent,
                routed_intent=routed_intent,
                action="record_only",
                task_message_ids=intake_task_message_ids,
                artifact_ids=intake_artifact_ids,
                feedback_gate_opened=run.status == RunStatus.WAITING_FOR_HUMAN,
                multimodal_intake=multimodal_intake,
            )
            return ConversationRouteResult(
                run_id=run.run_id,
                turn_id=turn.turn_id,
                response_turn_id=response_turn.turn_id,
                routed_intent=routed_intent,
                response_text=response_text,
                created_run=False,
                task_message_ids=intake_task_message_ids,
                artifact_ids=intake_artifact_ids,
                multimodal_intake=multimodal_intake,
                feedback_gate_opened=run.status == RunStatus.WAITING_FOR_HUMAN,
                summary="Recorded conversational turn without routing new work.",
            )

        return await self._route_task(run, turn, request, routed_intent)

    async def _start_content_run(
        self, request: ConversationRouteRequest
    ) -> ConversationRouteResult:
        orchestration = await ContentStudioWorkflow(
            self._store, self._services
        ).run(
            OrchestrationRequest(
                transcript=request.transcript,
                modality=request.modality,
                speaker=request.speaker,
                audio_uri=request.audio_uri,
                topic=request.topic,
                target_formats=request.target_formats,
                require_human_feedback=request.require_human_feedback,
            )
        )
        run = await self._store.get_run(orchestration.run_id)
        if run is None:
            raise ConversationRouterRunNotFoundError(
                f"Run not found after orchestration: {orchestration.run_id}"
            )
        turn = ConversationTurn(
            turn_id=orchestration.turn_id,
            run_id=orchestration.run_id,
            speaker=request.speaker,
            modality=request.modality,
            transcript=request.transcript,
            audio_uri=request.audio_uri,
            metadata={"workflow": "conversation_router_v1"},
        )
        response_text = (
            "I started a source-backed content run and opened the specialist "
            "agent loop."
        )
        multimodal_intake = await self._record_multimodal_intake(
            run=run,
            turn=turn,
            request=request,
        )
        task_message_ids = [
            *orchestration.task_message_ids,
            *(multimodal_intake.task_message_ids if multimodal_intake else []),
        ]
        artifact_ids = [
            *orchestration.artifact_ids,
            *(
                [multimodal_intake.intake_artifact_id]
                if multimodal_intake and multimodal_intake.intake_artifact_id
                else []
            ),
        ]
        response_turn = await self._record_assistant_reply(
            run=run,
            user_turn=turn,
            response_text=response_text,
            routed_intent=ConversationRouteIntent.CREATE_CONTENT,
            action="content_workflow_started",
        )
        await self._append_route_event(
            run=run,
            turn=turn,
            response_turn=response_turn,
            requested_intent=request.intent,
            routed_intent=ConversationRouteIntent.CREATE_CONTENT,
            action="content_workflow_started",
            task_message_ids=task_message_ids,
            artifact_ids=artifact_ids,
            feedback_gate_opened=orchestration.feedback_gate_opened,
            multimodal_intake=multimodal_intake,
        )
        return ConversationRouteResult(
            run_id=orchestration.run_id,
            turn_id=orchestration.turn_id,
            response_turn_id=response_turn.turn_id,
            routed_intent=ConversationRouteIntent.CREATE_CONTENT,
            response_text=response_text,
            created_run=True,
            task_message_ids=task_message_ids,
            artifact_ids=artifact_ids,
            multimodal_intake=multimodal_intake,
            feedback_gate_opened=orchestration.feedback_gate_opened,
            orchestration_result=orchestration,
            summary=orchestration.summary,
        )

    async def _record_turn(
        self,
        run: RunState,
        request: ConversationRouteRequest,
        routed_intent: ConversationRouteIntent,
    ) -> ConversationTurn:
        metadata = {
            **request.metadata,
            "workflow": "conversation_router_v1",
            "requested_intent": request.intent.value,
            "routed_intent": routed_intent.value,
        }
        turn = ConversationTurn(
            run_id=run.run_id,
            speaker=request.speaker,
            modality=request.modality,
            transcript=request.transcript,
            audio_uri=request.audio_uri,
            metadata=metadata,
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

    async def _record_assistant_reply(
        self,
        *,
        run: RunState,
        user_turn: ConversationTurn,
        response_text: str,
        routed_intent: ConversationRouteIntent,
        action: str,
    ) -> ConversationTurn:
        realtime_metadata = {
            key: user_turn.metadata[key]
            for key in (
                "realtime_session_id",
                "provider",
                "provider_session_id",
                "audio_mode",
                "interrupted",
            )
            if key in user_turn.metadata
        }
        reply = ConversationTurn(
            run_id=run.run_id,
            speaker="assistant",
            modality=user_turn.modality,
            transcript=response_text,
            metadata={
                **realtime_metadata,
                "workflow": "conversation_router_v1",
                "responds_to_turn_id": str(user_turn.turn_id),
                "routed_intent": routed_intent.value,
                "action": action,
                "response_kind": "dialogue_ack",
            },
        )
        await self._store.record_conversation_turn(reply)
        await self._store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="conversation_turn_recorded",
                actor="realtime-conversation-host",
                payload=safe_realtime_metadata(reply.model_dump(mode="json")),
            )
        )
        return reply

    async def _revise_content(
        self,
        run: RunState,
        turn: ConversationTurn,
        request: ConversationRouteRequest,
        routed_intent: ConversationRouteIntent,
        *,
        artifacts: list[ArtifactRecord],
    ) -> ConversationRouteResult:
        target_artifact_ids = _conversation_revision_target_ids(
            request=request,
            artifacts=artifacts,
        )
        revision = await RevisionWorkflow(self._store, self._services).run(
            run.run_id,
            RevisionRequest(
                feedback_text=request.transcript,
                author=request.speaker,
                target_artifact_ids=target_artifact_ids,
                require_human_feedback=request.require_human_feedback,
            ),
        )
        multimodal_intake = await self._record_multimodal_intake(
            run=run,
            turn=turn,
            request=request,
        )
        task_message_ids = [
            *revision.task_message_ids,
            *(multimodal_intake.task_message_ids if multimodal_intake else []),
        ]
        artifact_ids = [
            *revision.revised_artifact_ids,
            *(
                [multimodal_intake.intake_artifact_id]
                if multimodal_intake and multimodal_intake.intake_artifact_id
                else []
            ),
        ]
        response_text = (
            (
                "I treated that as targeted feedback, routed it through the "
                f"revision agents, and revised {len(target_artifact_ids)} "
                "selected artifact(s)."
            )
            if target_artifact_ids
            else (
                "I treated that as feedback, routed it through the revision "
                "agents, and created revised artifacts."
            )
        )
        response_turn = await self._record_assistant_reply(
            run=run,
            user_turn=turn,
            response_text=response_text,
            routed_intent=routed_intent,
            action="feedback_revision_started",
        )
        await self._append_route_event(
            run=run,
            turn=turn,
            response_turn=response_turn,
            requested_intent=request.intent,
            routed_intent=routed_intent,
            action="feedback_revision_started",
            task_message_ids=task_message_ids,
            artifact_ids=artifact_ids,
            target_artifact_ids=target_artifact_ids,
            feedback_gate_opened=revision.feedback_gate_opened,
            multimodal_intake=multimodal_intake,
        )
        return ConversationRouteResult(
            run_id=run.run_id,
            turn_id=turn.turn_id,
            response_turn_id=response_turn.turn_id,
            routed_intent=routed_intent,
            response_text=response_text,
            created_run=False,
            task_message_ids=task_message_ids,
            artifact_ids=artifact_ids,
            target_artifact_ids=target_artifact_ids,
            multimodal_intake=multimodal_intake,
            feedback_id=revision.feedback_id,
            feedback_gate_opened=revision.feedback_gate_opened,
            revision_result=revision,
            summary=revision.summary,
        )

    async def _route_task(
        self,
        run: RunState,
        turn: ConversationTurn,
        request: ConversationRouteRequest,
        routed_intent: ConversationRouteIntent,
    ) -> ConversationRouteResult:
        multimodal_intake = await self._record_multimodal_intake(
            run=run,
            turn=turn,
            request=request,
        )
        message = AgentMessage(
            run_id=run.run_id,
            sender_agent_id="realtime-conversation-host",
            recipient_agent_id="intent-router",
            task_type="route_conversation_turn",
            payload={
                "turn_id": str(turn.turn_id),
                "transcript": request.transcript,
                "topic": request.topic,
                "target_formats": request.target_formats,
                "requested_intent": request.intent.value,
                "routed_intent": routed_intent.value,
                "instruction": (
                    "Classify this conversational turn and hand it to the next "
                    "specialist without blocking the live dialogue."
                ),
                "multimodal_intake": (
                    {
                        "intake_artifact_id": (
                            str(multimodal_intake.intake_artifact_id)
                            if multimodal_intake.intake_artifact_id
                            else None
                        ),
                        "asset_count": multimodal_intake.asset_count,
                        "recommended_agent_ids": (
                            multimodal_intake.recommended_agent_ids
                        ),
                        "task_message_ids": [
                            str(message_id)
                            for message_id in multimodal_intake.task_message_ids
                        ],
                    }
                    if multimodal_intake
                    else None
                ),
            },
        )
        await self._store.record_agent_message(message)
        await self._store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="agent_message_accepted",
                actor=message.sender_agent_id,
                payload=public_a2a_message_event_payload(message),
            )
        )
        response_text = (
            "I routed that turn to the intent router so the right specialist "
            "can continue in the background."
        )
        response_turn = await self._record_assistant_reply(
            run=run,
            user_turn=turn,
            response_text=response_text,
            routed_intent=routed_intent,
            action="intent_router_task_created",
        )
        handoff = await self._record_conversation_handoff(
            run=run,
            turn=turn,
            response_turn=response_turn,
            message=message,
            request=request,
            routed_intent=routed_intent,
            multimodal_intake=multimodal_intake,
        )
        task_message_ids = [
            message.message_id,
            *(multimodal_intake.task_message_ids if multimodal_intake else []),
        ]
        artifact_ids = [
            handoff.artifact_id,
            *(
                [multimodal_intake.intake_artifact_id]
                if multimodal_intake and multimodal_intake.intake_artifact_id
                else []
            ),
        ]
        await self._append_route_event(
            run=run,
            turn=turn,
            response_turn=response_turn,
            requested_intent=request.intent,
            routed_intent=routed_intent,
            action="intent_router_task_created",
            task_message_ids=task_message_ids,
            artifact_ids=artifact_ids,
            feedback_gate_opened=run.status == RunStatus.WAITING_FOR_HUMAN,
            multimodal_intake=multimodal_intake,
        )
        return ConversationRouteResult(
            run_id=run.run_id,
            turn_id=turn.turn_id,
            response_turn_id=response_turn.turn_id,
            routed_intent=routed_intent,
            response_text=response_text,
            created_run=False,
            task_message_ids=task_message_ids,
            artifact_ids=artifact_ids,
            multimodal_intake=multimodal_intake,
            feedback_gate_opened=run.status == RunStatus.WAITING_FOR_HUMAN,
            summary=(
                "Created a durable A2A task and conversation handoff packet for "
                "the intent router."
            ),
        )

    async def _record_conversation_handoff(
        self,
        *,
        run: RunState,
        turn: ConversationTurn,
        response_turn: ConversationTurn,
        message: AgentMessage,
        request: ConversationRouteRequest,
        routed_intent: ConversationRouteIntent,
        multimodal_intake: MultimodalIntakeResult | None = None,
    ) -> ArtifactRecord:
        turns = await self._store.list_conversation_turns(run.run_id)
        messages = await self._store.list_agent_messages(run.run_id, limit=50)
        artifacts = await self._store.list_artifacts(run.run_id)
        feedback_items = await self._store.list_feedback(run.run_id)
        pending_messages = [
            current_message
            for current_message in messages
            if current_message.status.value
            in {"accepted", "claimed", "in_progress", "waiting_for_human", "blocked"}
        ]
        open_feedback = [
            feedback
            for feedback in feedback_items
            if feedback.status.value in {"open", "routed"}
        ]
        handoff = ArtifactRecord(
            run_id=run.run_id,
            artifact_type=ArtifactType.CONVERSATION_HANDOFF,
            title="Conversation handoff packet",
            uri=f"artifact://runs/{run.run_id}/conversation-handoff/{turn.turn_id}",
            content={
                "format": "conversation_handoff_packet",
                "handoff_message_id": str(message.message_id),
                "target_agent_id": message.recipient_agent_id,
                "user_turn": _turn_packet(turn),
                "assistant_reply": _turn_packet(response_turn),
                "recent_turns": [_turn_packet(current_turn) for current_turn in turns[-8:]],
                "routing": {
                    "requested_intent": request.intent.value,
                    "routed_intent": routed_intent.value,
                    "topic": request.topic,
                    "target_formats": request.target_formats,
                    "modality": request.modality,
                    "requires_human_feedback": request.require_human_feedback,
                    "attached_asset_count": len(request.assets),
                    "multimodal_intake_artifact_id": (
                        str(multimodal_intake.intake_artifact_id)
                        if multimodal_intake and multimodal_intake.intake_artifact_id
                        else None
                    ),
                },
                "run_snapshot": {
                    "run_id": str(run.run_id),
                    "status": run.status.value,
                    "goal": run.goal,
                    "active_agents": run.active_agents,
                    "conversation_state": run.conversation_state,
                },
                "durable_context_counts": {
                    "conversation_turns": len(turns),
                    "agent_messages": len(messages),
                    "artifacts": len(artifacts),
                    "feedback_items": len(feedback_items),
                    "pending_messages": len(pending_messages),
                    "open_feedback_items": len(open_feedback),
                },
                "pending_message_ids": [
                    str(current_message.message_id)
                    for current_message in pending_messages
                ],
                "open_feedback_ids": [
                    str(feedback.feedback_id) for feedback in open_feedback
                ],
                "recommended_next_steps": [
                    "Classify the live turn without blocking the conversation.",
                    "Create idempotent specialist A2A tasks when the request implies work.",
                    "Use the multimodal intake ledger before asking the user to restate asset context.",
                    "Use recent turns and open feedback before asking the user to repeat context.",
                ],
            },
            provenance={
                "workflow": "conversation_router_handoff_v1",
                "agent_id": "intent-router",
                "source_turn_id": str(turn.turn_id),
                "response_turn_id": str(response_turn.turn_id),
                "source_message_id": str(message.message_id),
                "requested_intent": request.intent.value,
                "routed_intent": routed_intent.value,
            },
            revision_history=[
                {
                    "actor": "realtime-conversation-host",
                    "note": "Created turn-level handoff packet for background specialist routing.",
                }
            ],
        )
        await self._store.record_artifact(handoff)
        await self._store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=handoff.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="conversation_handoff_recorded",
                actor="intent-router",
                payload={
                    "artifact_id": str(handoff.artifact_id),
                    "handoff_message_id": str(message.message_id),
                    "turn_id": str(turn.turn_id),
                    "response_turn_id": str(response_turn.turn_id),
                    "pending_message_count": len(pending_messages),
                    "open_feedback_count": len(open_feedback),
                    "recent_turn_count": min(len(turns), 8),
                },
            )
        )
        return handoff

    async def _append_route_event(
        self,
        *,
        run: RunState,
        turn: ConversationTurn,
        response_turn: ConversationTurn,
        requested_intent: ConversationRouteIntent,
        routed_intent: ConversationRouteIntent,
        action: str,
        task_message_ids: list,
        artifact_ids: list,
        feedback_gate_opened: bool,
        multimodal_intake: MultimodalIntakeResult | None = None,
        target_artifact_ids: list[UUID] | None = None,
    ) -> RunEvent:
        return await self._store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="conversation_turn_routed",
                actor="intent-router",
                payload={
                    "turn_id": str(turn.turn_id),
                    "response_turn_id": str(response_turn.turn_id),
                    "requested_intent": requested_intent.value,
                    "routed_intent": routed_intent.value,
                    "action": action,
                    "task_message_ids": [
                        str(message_id) for message_id in task_message_ids
                    ],
                    "artifact_ids": [str(artifact_id) for artifact_id in artifact_ids],
                    "target_artifact_ids": [
                        str(artifact_id)
                        for artifact_id in target_artifact_ids or []
                    ],
                    "multimodal_intake_artifact_id": (
                        str(multimodal_intake.intake_artifact_id)
                        if multimodal_intake and multimodal_intake.intake_artifact_id
                        else None
                    ),
                    "attached_asset_count": (
                        multimodal_intake.asset_count if multimodal_intake else 0
                    ),
                    "feedback_gate_opened": feedback_gate_opened,
                },
            )
        )

    async def _record_multimodal_intake(
        self,
        *,
        run: RunState,
        turn: ConversationTurn,
        request: ConversationRouteRequest,
    ) -> MultimodalIntakeResult | None:
        if not request.assets or not request.record_multimodal_intake:
            return None
        assets = [
            asset.model_copy(
                update={
                    "metadata": {
                        **asset.metadata,
                        "conversation_turn_id": str(turn.turn_id),
                        "conversation_modality": request.modality,
                        "conversation_topic": request.topic,
                        "conversation_audio_uri": request.audio_uri,
                    }
                }
            )
            for asset in request.assets
        ]
        return await MultimodalIntakeWorkflow(self._store).record(
            run.run_id,
            MultimodalIntakeRequest(
                assets=assets,
                record_artifact=True,
                create_agent_tasks=True,
                require_human_feedback=request.require_human_feedback,
                notes=f"Attached to conversation turn {turn.turn_id}.",
            ),
        )


def _resolve_intent(
    *,
    request: ConversationRouteRequest,
    run: RunState,
    artifact_count: int,
) -> ConversationRouteIntent:
    if request.intent != ConversationRouteIntent.AUTO:
        return request.intent
    text = request.transcript.lower()
    feedback_terms = {
        "revise",
        "revision",
        "change",
        "improve",
        "feedback",
        "make it",
        "shorter",
        "longer",
        "hook",
        "tone",
        "add",
        "remove",
        "rewrite",
    }
    if artifact_count and (
        run.status == RunStatus.WAITING_FOR_HUMAN
        or any(term in text for term in feedback_terms)
    ):
        return ConversationRouteIntent.REVISE_CONTENT
    if text.startswith("note:") or text.startswith("remember:"):
        return ConversationRouteIntent.RECORD_ONLY
    return ConversationRouteIntent.ROUTE_TASK


CONVERSATION_REVISION_TYPE_TERMS = {
    ArtifactType.POST: {
        "post",
        "caption",
        "carousel",
        "instagram post",
        "linkedin post",
        "social post",
    },
    ArtifactType.REEL_SCRIPT: {
        "reel",
        "short",
        "short-form",
        "script",
        "hook",
        "retention",
        "subtitle",
        "voiceover",
    },
    ArtifactType.SUBSTACK_ARTICLE: {
        "substack",
        "essay",
        "article",
        "long-form",
        "newsletter",
    },
    ArtifactType.IMAGE: {"image", "visual", "thumbnail", "graphic"},
    ArtifactType.AUDIO: {"audio", "voice", "tts", "spoken", "narration"},
    ArtifactType.VIDEO: {"video", "storyboard", "scene"},
}


def _conversation_revision_target_ids(
    *,
    request: ConversationRouteRequest,
    artifacts: list[ArtifactRecord],
) -> list[UUID]:
    explicit_target_ids = _explicit_conversation_target_ids(request)
    leaf_artifacts = _leaf_revision_artifacts(artifacts)
    if explicit_target_ids:
        return [
            artifact.artifact_id
            for artifact in leaf_artifacts
            if _artifact_matches_target_or_descendant(
                artifact,
                target_ids=explicit_target_ids,
                artifact_by_id={item.artifact_id: item for item in artifacts},
            )
        ]

    target_types = _inferred_revision_target_types(request.transcript)
    if not target_types:
        return []
    return [
        artifact.artifact_id
        for artifact in leaf_artifacts
        if artifact.artifact_type in target_types
    ]


def _explicit_conversation_target_ids(
    request: ConversationRouteRequest,
) -> set[UUID]:
    raw_values: list[Any] = [*request.target_artifact_ids]
    for key in (
        "artifact_id",
        "target_artifact_id",
        "artifact_ids",
        "target_artifact_ids",
    ):
        value = request.metadata.get(key)
        if isinstance(value, list):
            raw_values.extend(value)
        elif value:
            raw_values.append(value)
    target_ids = set()
    for raw_value in raw_values:
        try:
            target_ids.add(UUID(str(raw_value)))
        except (TypeError, ValueError):
            continue
    return target_ids


def _inferred_revision_target_types(transcript: str) -> set[ArtifactType]:
    text = transcript.lower()
    target_types = {
        artifact_type
        for artifact_type, terms in CONVERSATION_REVISION_TYPE_TERMS.items()
        if any(term in text for term in terms)
    }
    if ArtifactType.AUDIO in target_types and ArtifactType.REEL_SCRIPT in target_types:
        return {ArtifactType.REEL_SCRIPT}
    if ArtifactType.VIDEO in target_types and ArtifactType.REEL_SCRIPT in target_types:
        return {ArtifactType.REEL_SCRIPT}
    return target_types


def _leaf_revision_artifacts(
    artifacts: list[ArtifactRecord],
) -> list[ArtifactRecord]:
    parent_ids = set()
    for artifact in artifacts:
        parent_id = artifact.provenance.get("parent_artifact_id")
        if parent_id is None:
            continue
        try:
            parent_ids.add(UUID(str(parent_id)))
        except (TypeError, ValueError):
            continue
    return [
        artifact
        for artifact in artifacts
        if artifact.artifact_type in CONVERSATION_REVISION_TYPE_TERMS
        and artifact.artifact_id not in parent_ids
    ]


def _artifact_matches_target_or_descendant(
    artifact: ArtifactRecord,
    *,
    target_ids: set[UUID],
    artifact_by_id: dict[UUID, ArtifactRecord],
) -> bool:
    current: ArtifactRecord | None = artifact
    seen: set[UUID] = set()
    while current is not None and current.artifact_id not in seen:
        if current.artifact_id in target_ids:
            return True
        seen.add(current.artifact_id)
        parent_id = current.provenance.get("parent_artifact_id")
        if parent_id is None:
            return False
        try:
            current = artifact_by_id.get(UUID(str(parent_id)))
        except (TypeError, ValueError):
            return False
    return False


def _turn_packet(turn: ConversationTurn) -> dict[str, object]:
    return {
        "turn_id": str(turn.turn_id),
        "speaker": turn.speaker,
        "modality": turn.modality,
        "transcript": turn.transcript,
        "audio_uri": turn.audio_uri,
        "metadata": turn.metadata,
        "created_at": turn.created_at.isoformat(),
    }
