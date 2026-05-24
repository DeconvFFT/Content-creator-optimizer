import re
from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from all_about_llms.contracts import (
    AgentMessage,
    ArtifactRecord,
    ArtifactType,
    FeedbackItem,
    ReviewDecision,
    ReviewDecisionStatus,
    RevisionRequest,
    RevisionResult,
    RunEvent,
    RunStatus,
)
from all_about_llms.orchestration.a2a_projection import (
    public_a2a_message_event_payload,
)
from all_about_llms.orchestration.services import ContentWorkflowServices
from all_about_llms.providers.interfaces import (
    GemmaRequest,
    ProviderConfigurationError,
)
from all_about_llms.realtime_safety import safe_realtime_metadata


class RevisionWorkflowError(RuntimeError):
    """Base error for feedback-driven revision orchestration."""


class RunNotFoundError(RevisionWorkflowError):
    """Raised when a revision is requested for a missing run."""


class NoArtifactsToReviseError(RevisionWorkflowError):
    """Raised when feedback cannot be mapped to any existing artifacts."""


REVISION_TARGET_TYPES = {
    ArtifactType.POST,
    ArtifactType.REEL_SCRIPT,
    ArtifactType.SUBSTACK_ARTICLE,
    ArtifactType.SOCIAL_PACKAGE,
    ArtifactType.VISUAL_BRIEF,
    ArtifactType.IMAGE,
    ArtifactType.AUDIO,
    ArtifactType.VIDEO,
}


class RevisionWorkflow:
    """Turn human feedback into routed specialist work and revised artifacts."""

    def __init__(
        self, store, services: ContentWorkflowServices | None = None
    ):
        self._store = store
        self._services = services or ContentWorkflowServices()

    async def run(
        self, run_id: UUID, request: RevisionRequest
    ) -> RevisionResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise RunNotFoundError(f"Run not found: {run_id}")

        await self._store.update_run_status(run_id, RunStatus.RUNNING)
        existing_feedback = await _find_existing_revision_feedback(
            self._store,
            run_id=run_id,
            request=request,
        )
        if existing_feedback is not None:
            artifacts = await _artifacts_for_revision_feedback(
                self._store,
                run_id=run_id,
                feedback=existing_feedback,
            )
            if not artifacts:
                artifacts = await _artifacts_from_existing_revision_parents(
                    self._store,
                    run_id=run_id,
                    feedback=existing_feedback,
                )
            if not artifacts:
                artifacts = await self._select_revision_targets(run_id, request)
            feedback = existing_feedback
            feedback_recorded = False
        else:
            artifacts = await self._select_revision_targets(run_id, request)
            feedback, feedback_recorded = await self._record_feedback(
                run_id, request, artifacts
            )
        await self._append_revision_event_once(
            run_id=run_id,
            event_type="feedback_recorded",
            actor="forward-deployed-engineer",
            feedback_id=feedback.feedback_id,
            idempotency_key=_revision_event_idempotency_key(
                run_id=run_id,
                event_type="feedback_recorded",
                feedback_id=feedback.feedback_id,
            ),
            payload=safe_realtime_metadata(feedback.model_dump(mode="json")),
        )
        await self._append_revision_event_once(
            run_id=run_id,
            event_type="revision_loop_started",
            actor="forward-deployed-engineer",
            feedback_id=feedback.feedback_id,
            idempotency_key=_revision_event_idempotency_key(
                run_id=run_id,
                event_type="revision_loop_started",
                feedback_id=feedback.feedback_id,
            ),
            payload={
                "author": request.author,
                "feedback_id": str(feedback.feedback_id),
                "target_artifact_ids": [
                    str(artifact.artifact_id) for artifact in artifacts
                ],
                "reused_existing": not feedback_recorded,
            },
        )
        task_messages = await self._route_revision_tasks(
            run_id=run_id,
            request=request,
            feedback=feedback,
            artifacts=artifacts,
        )
        revised_artifacts, review_decisions = await self._revise_artifacts(
            run_id=run_id,
            request=request,
            feedback=feedback,
            artifacts=artifacts,
        )
        feedback_gate_opened = await self._close_or_reopen_gate(
            run_id=run_id,
            request=request,
            feedback=feedback,
            revised_artifacts=revised_artifacts,
        )

        return RevisionResult(
            run_id=run_id,
            feedback_id=feedback.feedback_id,
            task_message_ids=[message.message_id for message in task_messages],
            revised_artifact_ids=[
                artifact.artifact_id for artifact in revised_artifacts
            ],
            review_decisions=review_decisions,
            feedback_gate_opened=feedback_gate_opened,
            summary=(
                f"Processed feedback into {len(task_messages)} routed agent "
                f"tasks, {len(revised_artifacts)} revised artifacts, and "
                f"{len(review_decisions)} reviewer decisions."
            ),
        )

    async def _record_feedback(
        self,
        run_id: UUID,
        request: RevisionRequest,
        artifacts: list[ArtifactRecord],
    ) -> tuple[FeedbackItem, bool]:
        feedback_id = _revision_feedback_id(
            run_id=run_id,
            request=request,
            artifacts=artifacts,
        )
        feedback = FeedbackItem(
            feedback_id=feedback_id,
            run_id=run_id,
            author=request.author,
            target_agent_id="content-strategist",
            feedback_text=request.feedback_text,
            metadata={
                "workflow": "feedback_revision_v1",
                "revision_request_signature": _revision_request_signature(
                    run_id=run_id,
                    request=request,
                    artifacts=artifacts,
                ),
                "target_artifact_ids": [
                    str(artifact.artifact_id) for artifact in artifacts
                ],
                "require_human_feedback": request.require_human_feedback,
            },
        )
        recorder = getattr(self._store, "record_feedback_if_absent", None)
        recorded = await recorder(feedback) if callable(recorder) else None
        if recorded is None:
            existing = await self._store.get_feedback(feedback.feedback_id)
            if existing is not None:
                return existing, False
            await self._store.record_feedback(feedback)
            recorded = feedback
        return recorded, True

    async def _select_revision_targets(
        self, run_id: UUID, request: RevisionRequest
    ) -> list[ArtifactRecord]:
        artifacts = await self._store.list_artifacts(run_id)
        if request.target_artifact_ids:
            requested_ids = set(request.target_artifact_ids)
            selected = [
                artifact
                for artifact in artifacts
                if artifact.artifact_id in requested_ids
                and artifact.artifact_type in REVISION_TARGET_TYPES
            ]
        else:
            selected = _leaf_content_artifacts(artifacts)

        if not selected:
            raise NoArtifactsToReviseError(
                "No content artifacts are available for revision."
            )
        return selected

    async def _route_revision_tasks(
        self,
        *,
        run_id: UUID,
        request: RevisionRequest,
        feedback: FeedbackItem,
        artifacts: list[ArtifactRecord],
    ) -> list[AgentMessage]:
        target_ids = [str(artifact.artifact_id) for artifact in artifacts]
        base_payload = {
            "feedback_id": str(feedback.feedback_id),
            "feedback_text": request.feedback_text,
            "target_artifact_ids": target_ids,
        }
        messages = [
            AgentMessage(
                message_id=_revision_task_message_id(
                    run_id=run_id,
                    feedback_id=feedback.feedback_id,
                    recipient_agent_id="content-strategist",
                    task_type="incorporate_human_feedback",
                ),
                run_id=run_id,
                sender_agent_id="forward-deployed-engineer",
                recipient_agent_id="content-strategist",
                task_type="incorporate_human_feedback",
                payload={
                    **base_payload,
                    "instruction": "Turn user feedback into revision requirements.",
                },
            ),
            AgentMessage(
                message_id=_revision_task_message_id(
                    run_id=run_id,
                    feedback_id=feedback.feedback_id,
                    recipient_agent_id="script-doctor",
                    task_type="revise_hook_and_pacing",
                ),
                run_id=run_id,
                sender_agent_id="content-strategist",
                recipient_agent_id="script-doctor",
                task_type="revise_hook_and_pacing",
                payload={
                    **base_payload,
                    "instruction": "Improve hooks, spoken clarity, and pacing.",
                },
            ),
            AgentMessage(
                message_id=_revision_task_message_id(
                    run_id=run_id,
                    feedback_id=feedback.feedback_id,
                    recipient_agent_id="editor-in-chief",
                    task_type="editorial_revision_review",
                ),
                run_id=run_id,
                sender_agent_id="content-strategist",
                recipient_agent_id="editor-in-chief",
                task_type="editorial_revision_review",
                payload={
                    **base_payload,
                    "instruction": "Review revised drafts for coherence and audience fit.",
                },
            ),
            AgentMessage(
                message_id=_revision_task_message_id(
                    run_id=run_id,
                    feedback_id=feedback.feedback_id,
                    recipient_agent_id="guardrails-agent",
                    task_type="guardrails_revision_review",
                ),
                run_id=run_id,
                sender_agent_id="editor-in-chief",
                recipient_agent_id="guardrails-agent",
                task_type="guardrails_revision_review",
                payload={
                    **base_payload,
                    "instruction": (
                        "Check source dependencies, unsupported claims, "
                        "and publishing risk."
                    ),
                },
                requires_human_feedback=request.require_human_feedback,
            ),
        ]
        for message in messages:
            recorded = await _record_agent_message_if_absent(self._store, message)
            if recorded is None:
                existing = await self._store.get_agent_message(message.message_id)
                if existing is None:
                    await self._store.record_agent_message(message)
                    recorded = message
                else:
                    recorded = existing
            await self._append_revision_event_once(
                run_id=run_id,
                event_type="agent_message_accepted",
                actor=recorded.sender_agent_id,
                feedback_id=feedback.feedback_id,
                idempotency_key=_revision_event_idempotency_key(
                    run_id=run_id,
                    event_type="agent_message_accepted",
                    feedback_id=feedback.feedback_id,
                    message_id=recorded.message_id,
                ),
                payload=public_a2a_message_event_payload(recorded),
            )
        return messages

    async def _revise_artifacts(
        self,
        *,
        run_id: UUID,
        request: RevisionRequest,
        feedback: FeedbackItem,
        artifacts: list[ArtifactRecord],
    ) -> tuple[list[ArtifactRecord], list[ReviewDecision]]:
        revised_artifacts: list[ArtifactRecord] = []
        review_decisions: list[ReviewDecision] = []
        for artifact in artifacts:
            revision_artifact_id = _revision_artifact_id(
                run_id=run_id,
                feedback_id=feedback.feedback_id,
                parent_artifact_id=artifact.artifact_id,
            )
            existing_revision = await _find_artifact_by_id(
                self._store,
                run_id,
                revision_artifact_id,
            )
            if existing_revision is not None:
                decisions = _review_decisions_from_artifact(existing_revision)
                await self._append_artifact_revision_events_once(
                    run_id=run_id,
                    feedback=feedback,
                    parent_artifact=artifact,
                    revised_artifact=existing_revision,
                    generation_mode=str(
                        existing_revision.provenance.get(
                            "generation_mode", "unknown"
                        )
                    ),
                    decisions=decisions,
                )
                revised_artifacts.append(existing_revision)
                review_decisions.extend(decisions)
                continue
            revised_content, generation_mode = await self._build_revised_content(
                run_id=run_id,
                request=request,
                feedback=feedback,
                artifact=artifact,
            )
            decisions = _review_decisions_for(artifact)
            revision_history = [
                *artifact.revision_history,
                {
                    "actor": "forward-deployed-engineer",
                    "feedback_id": str(feedback.feedback_id),
                    "parent_artifact_id": str(artifact.artifact_id),
                    "note": request.feedback_text,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            ]
            revised_artifact = ArtifactRecord(
                artifact_id=revision_artifact_id,
                run_id=run_id,
                artifact_type=artifact.artifact_type,
                title=_revision_title(artifact),
                uri=(
                    f"artifact://runs/{run_id}/revisions/"
                    f"{feedback.feedback_id}/{artifact.artifact_id}"
                ),
                content=revised_content,
                provenance={
                    "workflow": "feedback_revision_v1",
                    "parent_artifact_id": str(artifact.artifact_id),
                    "feedback_id": str(feedback.feedback_id),
                    "source_ids": [
                        str(source_id) for source_id in artifact.source_ids
                    ],
                    "generation_mode": generation_mode,
                    "parent_provenance": artifact.provenance,
                    "reviewer_agents": [
                        decision.reviewer_agent_id for decision in decisions
                    ],
                },
                source_ids=artifact.source_ids,
                reviewer_decisions=[
                    decision.model_dump(mode="json") for decision in decisions
                ],
                revision_history=revision_history,
            )
            recorded_artifact = await _record_artifact_if_absent(
                self._store,
                revised_artifact,
            )
            if recorded_artifact is None:
                existing_revision = await _find_artifact_by_id(
                    self._store,
                    run_id,
                    revision_artifact_id,
                )
                if existing_revision is not None:
                    decisions = _review_decisions_from_artifact(existing_revision)
                    await self._append_artifact_revision_events_once(
                        run_id=run_id,
                        feedback=feedback,
                        parent_artifact=artifact,
                        revised_artifact=existing_revision,
                        generation_mode=str(
                            existing_revision.provenance.get(
                                "generation_mode", generation_mode
                            )
                        ),
                        decisions=decisions,
                    )
                    revised_artifacts.append(existing_revision)
                    review_decisions.extend(decisions)
                    continue
                await self._store.record_artifact(revised_artifact)
                recorded_artifact = revised_artifact
            await self._append_artifact_revision_events_once(
                run_id=run_id,
                feedback=feedback,
                parent_artifact=artifact,
                revised_artifact=recorded_artifact,
                generation_mode=generation_mode,
                decisions=decisions,
            )
            revised_artifacts.append(recorded_artifact)
            review_decisions.extend(decisions)
        return revised_artifacts, review_decisions

    async def _append_artifact_revision_events_once(
        self,
        *,
        run_id: UUID,
        feedback: FeedbackItem,
        parent_artifact: ArtifactRecord,
        revised_artifact: ArtifactRecord,
        generation_mode: str,
        decisions: list[ReviewDecision],
    ) -> None:
        await self._append_revision_event_once(
            run_id=run_id,
            event_type="artifact_revised",
            actor="artifact-librarian",
            feedback_id=feedback.feedback_id,
            idempotency_key=_revision_event_idempotency_key(
                run_id=run_id,
                event_type="artifact_revised",
                feedback_id=feedback.feedback_id,
                artifact_id=revised_artifact.artifact_id,
            ),
            payload={
                "artifact_id": str(revised_artifact.artifact_id),
                "parent_artifact_id": str(parent_artifact.artifact_id),
                "feedback_id": str(feedback.feedback_id),
                "generation_mode": generation_mode,
            },
        )
        for decision in decisions:
            await self._append_revision_event_once(
                run_id=run_id,
                event_type="review_decision_recorded",
                actor=decision.reviewer_agent_id,
                feedback_id=feedback.feedback_id,
                idempotency_key=_revision_event_idempotency_key(
                    run_id=run_id,
                    event_type="review_decision_recorded",
                    feedback_id=feedback.feedback_id,
                    artifact_id=revised_artifact.artifact_id,
                    reviewer_agent_id=decision.reviewer_agent_id,
                ),
                payload={
                    "artifact_id": str(revised_artifact.artifact_id),
                    "parent_artifact_id": str(parent_artifact.artifact_id),
                    "feedback_id": str(feedback.feedback_id),
                    "decision": decision.model_dump(mode="json"),
                },
            )

    async def _build_revised_content(
        self,
        *,
        run_id: UUID,
        request: RevisionRequest,
        feedback: FeedbackItem,
        artifact: ArtifactRecord,
    ) -> tuple[dict[str, Any], str]:
        if self._services.gemma_provider:
            try:
                gemma_response = await self._services.gemma_provider.complete(
                    GemmaRequest(
                        model_id="google/gemma-4-31b-it",
                        agent_id="content-strategist",
                        system_context=(
                            "Revise the existing source-backed content artifact. "
                            "Preserve source dependencies, incorporate the human "
                            "feedback, keep short-form ELI5 when relevant, and "
                            "keep long-form detailed plus ELI5 when relevant."
                        ),
                        user_input=(
                            f"Feedback: {request.feedback_text}\n"
                            f"Artifact title: {artifact.title}\n"
                            f"Artifact type: {artifact.artifact_type.value}\n"
                            f"Existing content: {artifact.content}\n"
                            f"Source ids: {[str(source_id) for source_id in artifact.source_ids]}"
                        ),
                        metadata={
                            "workflow": "feedback_revision_v1",
                            "feedback_id": str(feedback.feedback_id),
                            "parent_artifact_id": str(artifact.artifact_id),
                        },
                    )
                )
                await self._store.append_event(
                    RunEvent(
                        run_id=run_id,
                        event_type="gemma_revision_completed",
                        actor="content-strategist",
                        payload={
                            "model_id": gemma_response.model_id,
                            "agent_id": gemma_response.agent_id,
                            "feedback_id": str(feedback.feedback_id),
                            "parent_artifact_id": str(artifact.artifact_id),
                            "usage": gemma_response.usage,
                        },
                    )
                )
                return (
                    {
                        "generation_mode": "gemma_provider",
                        "revision_feedback": request.feedback_text,
                        "draft": gemma_response.content,
                        "parent_artifact_id": str(artifact.artifact_id),
                        "source_ids": [
                            str(source_id) for source_id in artifact.source_ids
                        ],
                    },
                    "gemma_provider",
                )
            except ProviderConfigurationError as exc:
                safe_reason = _redact_provider_failure_text(str(exc))
                await self._store.append_event(
                    RunEvent(
                        run_id=run_id,
                        event_type="provider_fallback",
                        actor="content-strategist",
                        payload={"provider": "gemma", "reason": safe_reason},
                    )
                )

        return (
            _deterministic_revision_content(
                artifact=artifact,
                feedback_text=request.feedback_text,
            ),
            "deterministic_fallback",
        )

    async def _close_or_reopen_gate(
        self,
        *,
        run_id: UUID,
        request: RevisionRequest,
        feedback: FeedbackItem,
        revised_artifacts: list[ArtifactRecord],
    ) -> bool:
        if request.require_human_feedback:
            await self._store.update_run_status(run_id, RunStatus.WAITING_FOR_HUMAN)
            await self._append_revision_event_once(
                run_id=run_id,
                event_type="human_feedback_gate_opened",
                actor="forward-deployed-engineer",
                feedback_id=feedback.feedback_id,
                idempotency_key=_revision_event_idempotency_key(
                    run_id=run_id,
                    event_type="human_feedback_gate_opened",
                    feedback_id=feedback.feedback_id,
                ),
                payload={
                    "feedback_id": str(feedback.feedback_id),
                    "revised_artifact_ids": [
                        str(artifact.artifact_id)
                        for artifact in revised_artifacts
                    ],
                    "question": (
                        "Review the revised artifacts and approve or provide "
                        "the next direction."
                    ),
                },
            )
            return True

        await self._store.update_run_status(run_id, RunStatus.COMPLETED)
        await self._append_revision_event_once(
            run_id=run_id,
            event_type="revision_loop_completed",
            actor="product-manager",
            feedback_id=feedback.feedback_id,
            idempotency_key=_revision_event_idempotency_key(
                run_id=run_id,
                event_type="revision_loop_completed",
                feedback_id=feedback.feedback_id,
            ),
            payload={
                "feedback_id": str(feedback.feedback_id),
                "feedback_gate_opened": False,
            },
        )
        return False

    async def _append_revision_event_once(
        self,
        *,
        run_id: UUID,
        event_type: str,
        actor: str,
        feedback_id: UUID,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> RunEvent | None:
        event_payload = dict(payload)
        event_payload["event_idempotency_key"] = idempotency_key
        if await _event_exists_for_revision_event(
            self._store,
            run_id=run_id,
            event_type=event_type,
            feedback_id=feedback_id,
            idempotency_key=idempotency_key,
            payload=event_payload,
        ):
            return None
        event = RunEvent(
            run_id=run_id,
            event_type=event_type,
            actor=actor,
            payload=event_payload,
        )
        appender = getattr(self._store, "append_event_if_absent", None)
        if callable(appender):
            return await appender(event, idempotency_key=idempotency_key)
        return await self._store.append_event(event)


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
        if artifact.artifact_type in REVISION_TARGET_TYPES
        and artifact.artifact_id not in parent_ids
    ]


def _revision_request_signature(
    *,
    run_id: UUID,
    request: RevisionRequest,
    artifacts: list[ArtifactRecord],
) -> str:
    target_ids = ",".join(sorted(str(artifact.artifact_id) for artifact in artifacts))
    return (
        f"{run_id}:{request.author}:"
        f"{request.feedback_text.strip()}:{target_ids}:"
        f"{request.require_human_feedback}"
    )


def _revision_feedback_id(
    *,
    run_id: UUID,
    request: RevisionRequest,
    artifacts: list[ArtifactRecord],
) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        "all-about-llms:feedback_revision:"
        + _revision_request_signature(
            run_id=run_id,
            request=request,
            artifacts=artifacts,
        ),
    )


def _revision_task_message_id(
    *,
    run_id: UUID,
    feedback_id: UUID,
    recipient_agent_id: str,
    task_type: str,
) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        (
            "all-about-llms:feedback_revision_task:"
            f"{run_id}:{feedback_id}:{recipient_agent_id}:{task_type}"
        ),
    )


def _revision_artifact_id(
    *,
    run_id: UUID,
    feedback_id: UUID,
    parent_artifact_id: UUID,
) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        (
            "all-about-llms:feedback_revision_artifact:"
            f"{run_id}:{feedback_id}:{parent_artifact_id}"
        ),
    )


def _revision_event_idempotency_key(
    *,
    run_id: UUID,
    event_type: str,
    feedback_id: UUID,
    message_id: UUID | None = None,
    artifact_id: UUID | None = None,
    reviewer_agent_id: str | None = None,
) -> str:
    parts = [
        "feedback_revision_v1",
        str(run_id),
        event_type,
        str(feedback_id),
    ]
    if message_id is not None:
        parts.append(str(message_id))
    if artifact_id is not None:
        parts.append(str(artifact_id))
    if reviewer_agent_id:
        parts.append(reviewer_agent_id)
    return ":".join(parts)


async def _record_agent_message_if_absent(
    store,
    message: AgentMessage,
) -> AgentMessage | None:
    recorder = getattr(store, "record_agent_message_if_absent", None)
    if callable(recorder):
        return await recorder(message)
    return None


async def _record_artifact_if_absent(
    store,
    artifact: ArtifactRecord,
) -> ArtifactRecord | None:
    recorder = getattr(store, "record_artifact_if_absent", None)
    if callable(recorder):
        return await recorder(artifact)
    return None


async def _find_artifact_by_id(
    store,
    run_id: UUID,
    artifact_id: UUID,
) -> ArtifactRecord | None:
    for artifact in await store.list_artifacts(run_id):
        if artifact.artifact_id == artifact_id:
            return artifact
    return None


async def _find_existing_revision_feedback(
    store,
    *,
    run_id: UUID,
    request: RevisionRequest,
) -> FeedbackItem | None:
    feedback_items = await store.list_feedback(run_id)
    requested_target_ids = {str(artifact_id) for artifact_id in request.target_artifact_ids}
    for feedback in reversed(feedback_items):
        feedback_target_ids = {
            str(artifact_id)
            for artifact_id in feedback.metadata.get("target_artifact_ids", [])
        }
        if (
            feedback.author == request.author
            and feedback.feedback_text.strip() == request.feedback_text.strip()
            and feedback.metadata.get("workflow") == "feedback_revision_v1"
            and feedback.metadata.get("require_human_feedback")
            == request.require_human_feedback
            and (
                not requested_target_ids
                or feedback_target_ids == requested_target_ids
            )
        ):
            return feedback
    return None


async def _artifacts_for_revision_feedback(
    store,
    *,
    run_id: UUID,
    feedback: FeedbackItem,
) -> list[ArtifactRecord]:
    target_ids = [
        str(artifact_id)
        for artifact_id in feedback.metadata.get("target_artifact_ids", [])
    ]
    if not target_ids:
        return []
    artifacts_by_id = {
        str(artifact.artifact_id): artifact
        for artifact in await store.list_artifacts(run_id)
    }
    return [
        artifacts_by_id[artifact_id]
        for artifact_id in target_ids
        if artifact_id in artifacts_by_id
        and artifacts_by_id[artifact_id].artifact_type in REVISION_TARGET_TYPES
    ]


async def _artifacts_from_existing_revision_parents(
    store,
    *,
    run_id: UUID,
    feedback: FeedbackItem,
) -> list[ArtifactRecord]:
    artifacts = await store.list_artifacts(run_id)
    artifacts_by_id = {artifact.artifact_id: artifact for artifact in artifacts}
    parent_ids: list[UUID] = []
    for artifact in artifacts:
        if (
            artifact.provenance.get("workflow") != "feedback_revision_v1"
            or artifact.provenance.get("feedback_id") != str(feedback.feedback_id)
        ):
            continue
        parent_id = artifact.provenance.get("parent_artifact_id")
        if not isinstance(parent_id, str):
            continue
        try:
            parsed_parent_id = UUID(parent_id)
        except ValueError:
            continue
        if parsed_parent_id not in parent_ids:
            parent_ids.append(parsed_parent_id)
    return [
        artifacts_by_id[parent_id]
        for parent_id in parent_ids
        if parent_id in artifacts_by_id
        and artifacts_by_id[parent_id].artifact_type in REVISION_TARGET_TYPES
    ]


def _redact_provider_failure_text(value: str) -> str:
    redacted = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [redacted]", value)
    redacted = re.sub(r"hf_[A-Za-z0-9]{20,}", "hf_[redacted]", redacted)
    redacted = re.sub(r"tvly-[A-Za-z0-9-]{20,}", "tvly-[redacted]", redacted)
    return redacted


async def _event_exists_for_revision_event(
    store,
    *,
    run_id: UUID,
    event_type: str,
    feedback_id: UUID,
    idempotency_key: str,
    payload: dict[str, Any],
) -> bool:
    lister = getattr(store, "list_events_by_type", None)
    if callable(lister):
        events = await lister(run_id, event_type, limit=500)
    else:
        events = [
            event
            for event in await store.list_events(run_id, limit=500)
            if event.event_type == event_type
        ]
    return any(
        _matches_revision_event(
            event=event,
            event_type=event_type,
            feedback_id=feedback_id,
            idempotency_key=idempotency_key,
            payload=payload,
        )
        for event in events
    )


def _matches_revision_event(
    *,
    event: RunEvent,
    event_type: str,
    feedback_id: UUID,
    idempotency_key: str,
    payload: dict[str, Any],
) -> bool:
    if event.payload.get("event_idempotency_key") == idempotency_key:
        return True
    if str(event.payload.get("feedback_id")) != str(feedback_id):
        return False
    if event_type in {
        "feedback_recorded",
        "revision_loop_started",
        "human_feedback_gate_opened",
        "revision_loop_completed",
    }:
        return True
    if event_type == "agent_message_accepted":
        return str(event.payload.get("message_id")) == str(payload.get("message_id"))
    if event_type == "artifact_revised":
        return str(event.payload.get("artifact_id")) == str(payload.get("artifact_id"))
    if event_type == "review_decision_recorded":
        decision = payload.get("decision")
        reviewer_agent_id = (
            decision.get("reviewer_agent_id") if isinstance(decision, dict) else None
        )
        return (
            str(event.payload.get("artifact_id")) == str(payload.get("artifact_id"))
            and event.actor == reviewer_agent_id
        )
    return False


def _review_decisions_from_artifact(artifact: ArtifactRecord) -> list[ReviewDecision]:
    decisions: list[ReviewDecision] = []
    for decision in artifact.reviewer_decisions:
        try:
            decisions.append(ReviewDecision(**decision))
        except (TypeError, ValueError):
            continue
    return decisions


def _review_decisions_for(artifact: ArtifactRecord) -> list[ReviewDecision]:
    has_sources = bool(artifact.source_ids)
    guardrail_status = (
        ReviewDecisionStatus.APPROVED_WITH_NOTES
        if has_sources
        else ReviewDecisionStatus.NEEDS_REVISION
    )
    guardrail_notes = (
        "Source dependencies are preserved; final publish still needs human approval."
        if has_sources
        else "Artifact has no source dependencies and needs source grounding before publishing."
    )
    blocking_issues = [] if has_sources else ["missing_source_dependencies"]
    return [
        ReviewDecision(
            reviewer_agent_id="editor-in-chief",
            status=ReviewDecisionStatus.APPROVED_WITH_NOTES,
            notes=(
                "Feedback was incorporated into a new artifact version; "
                "review tone and audience fit before publishing."
            ),
        ),
        ReviewDecision(
            reviewer_agent_id="guardrails-agent",
            status=guardrail_status,
            notes=guardrail_notes,
            blocking_issues=blocking_issues,
        ),
    ]


def _deterministic_revision_content(
    *, artifact: ArtifactRecord, feedback_text: str
) -> dict[str, Any]:
    original_claim_ids = artifact.content.get("claim_ids", [])
    return {
        "generation_mode": "deterministic_fallback",
        "revision_feedback": feedback_text,
        "parent_artifact_id": str(artifact.artifact_id),
        "revision_directive": (
            "Apply the human feedback while preserving source dependencies and "
            "claim provenance."
        ),
        "previous_content": artifact.content,
        "changes_requested": [feedback_text],
        "claim_ids": original_claim_ids,
        "source_ids": [str(source_id) for source_id in artifact.source_ids],
    }


def _revision_title(artifact: ArtifactRecord) -> str:
    revision_count = sum(
        1 for item in artifact.revision_history if item.get("feedback_id")
    )
    return f"{artifact.title} v{revision_count + 2}"
