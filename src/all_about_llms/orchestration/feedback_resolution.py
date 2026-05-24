from typing import Any
from uuid import UUID

from all_about_llms.contracts import (
    AgentTaskStatus,
    ArtifactRecord,
    ArtifactType,
    FeedbackResolutionFeedbackEntry,
    FeedbackResolutionLedgerRequest,
    FeedbackResolutionLedgerResult,
    FeedbackResolutionTaskEntry,
    FeedbackStatus,
    RunEvent,
)


class FeedbackResolutionLedgerError(RuntimeError):
    """Base error for feedback resolution ledger generation."""


class FeedbackResolutionLedgerRunNotFoundError(FeedbackResolutionLedgerError):
    """Raised when a run cannot be found for feedback resolution work."""


PENDING_TASK_STATUSES = {
    AgentTaskStatus.ACCEPTED,
    AgentTaskStatus.CLAIMED,
    AgentTaskStatus.IN_PROGRESS,
    AgentTaskStatus.WAITING_FOR_HUMAN,
    AgentTaskStatus.BLOCKED,
}

BLOCKING_TASK_STATUSES = {
    AgentTaskStatus.WAITING_FOR_HUMAN,
    AgentTaskStatus.BLOCKED,
}

FAILED_TASK_STATUSES = {
    AgentTaskStatus.FAILED,
    AgentTaskStatus.CANCELED,
}

FEEDBACK_OUTCOME_ORDER = ("accepted", "revised", "held", "rejected")


class FeedbackResolutionLedgerWorkflow:
    """Build a run ledger that closes the human-feedback loop."""

    def __init__(self, store):
        self._store = store

    async def build(
        self, run_id: UUID, request: FeedbackResolutionLedgerRequest
    ) -> FeedbackResolutionLedgerResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise FeedbackResolutionLedgerRunNotFoundError(f"Run not found: {run_id}")

        feedback_items = (
            await self._store.list_feedback(run_id)
        )[-request.max_feedback_items :]
        messages = (await self._store.list_agent_messages(run_id))[
            -request.max_messages :
        ]
        message_feedback_ids = {
            message.message_id: _message_feedback_id(message)
            for message in messages
        }
        linked_message_ids_by_feedback = _linked_messages_by_feedback(
            message_feedback_ids
        )
        task_entries = [
            _task_entry(message, message_feedback_ids[message.message_id])
            for message in messages
            if message_feedback_ids[message.message_id] is not None
        ]
        task_entries_by_feedback = _task_entries_by_feedback(task_entries)
        feedback_entries = [
            _feedback_entry(
                feedback,
                linked_message_ids_by_feedback.get(feedback.feedback_id, []),
                task_entries_by_feedback.get(feedback.feedback_id, []),
            )
            for feedback in feedback_items
        ]
        feedback_outcomes = _feedback_outcomes(feedback_entries)
        targeted_feedback = [
            entry
            for entry in feedback_entries
            if entry.target_artifact_ids
            or entry.target_source_ids
            or entry.target_claim_ids
        ]
        targeted_artifact_ids = _unique_entry_ids(
            feedback_entries,
            "target_artifact_ids",
        )
        targeted_source_ids = _unique_entry_ids(feedback_entries, "target_source_ids")
        targeted_claim_ids = _unique_entry_ids(feedback_entries, "target_claim_ids")
        open_feedback = [
            feedback for feedback in feedback_items if feedback.status == FeedbackStatus.OPEN
        ]
        routed_feedback = [
            feedback
            for feedback in feedback_items
            if feedback.status == FeedbackStatus.ROUTED
        ]
        resolved_feedback = [
            feedback
            for feedback in feedback_items
            if feedback.status == FeedbackStatus.RESOLVED
        ]
        rejected_feedback = [
            feedback
            for feedback in feedback_items
            if feedback.status == FeedbackStatus.REJECTED
        ]
        pending_task_ids = [
            entry.message_id
            for entry in task_entries
            if entry.status in PENDING_TASK_STATUSES
        ]
        blocked_task_ids = [
            entry.message_id
            for entry in task_entries
            if entry.status in BLOCKING_TASK_STATUSES
        ]
        failed_task_ids = [
            entry.message_id
            for entry in task_entries
            if entry.status in FAILED_TASK_STATUSES
        ]
        status = _ledger_status(
            open_feedback_count=len(open_feedback),
            routed_feedback_count=len(routed_feedback),
            pending_linked_task_count=len(pending_task_ids),
            blocked_linked_task_count=len(blocked_task_ids),
            failed_linked_task_count=len(failed_task_ids),
        )
        result = FeedbackResolutionLedgerResult(
            run_id=run_id,
            status=status,
            feedback_count=len(feedback_items),
            open_feedback_count=len(open_feedback),
            routed_feedback_count=len(routed_feedback),
            accepted_feedback_count=feedback_outcomes["accepted"],
            revised_feedback_count=feedback_outcomes["revised"],
            held_feedback_count=feedback_outcomes["held"],
            resolved_feedback_count=len(resolved_feedback),
            rejected_feedback_count=len(rejected_feedback),
            feedback_outcomes=feedback_outcomes,
            targeted_feedback_count=len(targeted_feedback),
            targeted_artifact_count=len(targeted_artifact_ids),
            targeted_source_count=len(targeted_source_ids),
            targeted_claim_count=len(targeted_claim_ids),
            linked_task_count=len(task_entries),
            pending_linked_task_count=len(pending_task_ids),
            blocked_linked_task_count=len(blocked_task_ids),
            failed_linked_task_count=len(failed_task_ids),
            open_feedback_ids=[feedback.feedback_id for feedback in open_feedback],
            routed_feedback_ids=[feedback.feedback_id for feedback in routed_feedback],
            recently_resolved_feedback_ids=[
                feedback.feedback_id for feedback in resolved_feedback[-10:]
            ],
            pending_task_ids=pending_task_ids,
            failed_task_ids=failed_task_ids,
            feedback_entries=feedback_entries,
            task_entries=task_entries,
            recommended_next_actions=_recommended_next_actions(
                open_feedback_count=len(open_feedback),
                routed_feedback_count=len(routed_feedback),
                pending_linked_task_count=len(pending_task_ids),
                blocked_linked_task_count=len(blocked_task_ids),
                failed_linked_task_count=len(failed_task_ids),
                resolved_feedback_count=len(resolved_feedback),
            ),
            summary=(
                f"Feedback resolution ledger is {status}: {len(open_feedback)} open, "
                f"{len(routed_feedback)} routed, {len(resolved_feedback)} resolved, "
                f"{len(pending_task_ids)} pending linked task(s), "
                f"{len(failed_task_ids)} failed/canceled linked task(s), "
                f"{feedback_outcomes['accepted']} accepted, "
                f"{feedback_outcomes['revised']} revised, "
                f"{feedback_outcomes['held']} held, "
                f"{feedback_outcomes['rejected']} rejected, and "
                f"{len(targeted_feedback)} artifact/source/claim-targeted feedback item(s)."
            ),
        )

        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.FEEDBACK_RESOLUTION_LEDGER,
                title="Feedback resolution ledger",
                uri=f"artifact://runs/{run_id}/feedback-resolution-ledger",
                content=result.model_dump(
                    mode="json", exclude={"ledger_artifact_id", "event_id"}
                ),
                provenance={
                    "workflow": "feedback_resolution_ledger_v1",
                    "agent_id": "forward-deployed-engineer",
                    "source_feedback_ids": [
                        str(feedback.feedback_id) for feedback in feedback_items
                    ],
                    "source_message_ids": [
                        str(entry.message_id) for entry in task_entries
                    ],
                },
                reviewer_decisions=[
                    {
                        "reviewer_agent_id": "forward-deployed-engineer",
                        "status": (
                            "approved_with_notes"
                            if status != "blocked"
                            else "needs_revision"
                        ),
                        "notes": "Feedback resolution state was converted into resume guidance for the agent loop.",
                    }
                ],
                revision_history=[
                    {
                        "actor": "forward-deployed-engineer",
                        "note": "Built a feedback resolution ledger from durable feedback items and linked A2A tasks.",
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
                event_type="feedback_resolution_ledger_built",
                actor="forward-deployed-engineer",
                payload={
                    "status": result.status,
                    "feedback_count": result.feedback_count,
                    "open_feedback_count": result.open_feedback_count,
                    "routed_feedback_count": result.routed_feedback_count,
                    "accepted_feedback_count": result.accepted_feedback_count,
                    "revised_feedback_count": result.revised_feedback_count,
                    "held_feedback_count": result.held_feedback_count,
                    "resolved_feedback_count": result.resolved_feedback_count,
                    "rejected_feedback_count": result.rejected_feedback_count,
                    "feedback_outcomes": result.feedback_outcomes,
                    "targeted_feedback_count": result.targeted_feedback_count,
                    "targeted_artifact_count": result.targeted_artifact_count,
                    "targeted_source_count": result.targeted_source_count,
                    "targeted_claim_count": result.targeted_claim_count,
                    "pending_linked_task_count": result.pending_linked_task_count,
                    "blocked_linked_task_count": result.blocked_linked_task_count,
                    "failed_linked_task_count": result.failed_linked_task_count,
                    "failed_task_ids": [
                        str(task_id) for task_id in result.failed_task_ids
                    ],
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


def _feedback_entry(
    feedback,
    linked_message_ids: list[UUID],
    linked_task_entries: list[FeedbackResolutionTaskEntry],
):
    metadata = feedback.metadata or {}
    return FeedbackResolutionFeedbackEntry(
        feedback_id=feedback.feedback_id,
        status=feedback.status,
        outcome=_feedback_outcome(feedback, linked_task_entries),
        target_agent_id=feedback.target_agent_id,
        author=feedback.author,
        route_reason=metadata.get("route_reason"),
        priority=metadata.get("priority"),
        target_artifact_ids=_metadata_uuid_list(metadata, "target_artifact_ids"),
        target_artifact_titles=_metadata_str_list(metadata, "target_artifact_titles"),
        target_artifact_types=_metadata_str_list(metadata, "target_artifact_types"),
        target_source_ids=_metadata_uuid_list(
            metadata,
            "target_artifact_source_ids",
            "target_source_ids",
        ),
        target_claim_ids=_metadata_uuid_list(
            metadata,
            "target_artifact_claim_ids",
            "target_claim_ids",
        ),
        target_artifact_selection=_metadata_string(
            metadata,
            "target_artifact_selection",
        ),
        linked_message_ids=linked_message_ids,
        resolution_notes=feedback.resolution_notes,
        resolved_by=feedback.resolved_by,
        resolved_at=feedback.resolved_at,
    )


def _task_entry(message, feedback_id: UUID | None):
    return FeedbackResolutionTaskEntry(
        message_id=message.message_id,
        feedback_id=feedback_id,
        recipient_agent_id=message.recipient_agent_id,
        task_type=message.task_type,
        status=message.status,
        requires_human_feedback=message.requires_human_feedback,
        blocking=message.status in BLOCKING_TASK_STATUSES,
    )


def _linked_messages_by_feedback(
    message_feedback_ids: dict[UUID, UUID | None]
) -> dict[UUID, list[UUID]]:
    linked: dict[UUID, list[UUID]] = {}
    for message_id, feedback_id in message_feedback_ids.items():
        if feedback_id is None:
            continue
        linked.setdefault(feedback_id, []).append(message_id)
    return linked


def _task_entries_by_feedback(
    task_entries: list[FeedbackResolutionTaskEntry],
) -> dict[UUID, list[FeedbackResolutionTaskEntry]]:
    entries: dict[UUID, list[FeedbackResolutionTaskEntry]] = {}
    for entry in task_entries:
        if entry.feedback_id is None:
            continue
        entries.setdefault(entry.feedback_id, []).append(entry)
    return entries


def _feedback_outcomes(
    feedback_entries: list[FeedbackResolutionFeedbackEntry],
) -> dict[str, int]:
    outcomes = {outcome: 0 for outcome in FEEDBACK_OUTCOME_ORDER}
    for entry in feedback_entries:
        outcomes.setdefault(entry.outcome, 0)
        outcomes[entry.outcome] += 1
    return {outcome: outcomes.get(outcome, 0) for outcome in FEEDBACK_OUTCOME_ORDER}


def _feedback_outcome(
    feedback,
    linked_task_entries: list[FeedbackResolutionTaskEntry],
) -> str:
    explicit_outcome = _metadata_string(
        feedback.metadata or {},
        "feedback_outcome",
        "resolution_outcome",
        "outcome",
    )
    normalized_outcome = (
        explicit_outcome.strip().lower().replace(" ", "_")
        if explicit_outcome
        else None
    )
    if normalized_outcome in FEEDBACK_OUTCOME_ORDER:
        return normalized_outcome
    if feedback.status == FeedbackStatus.REJECTED:
        return "rejected"
    if feedback.status in {FeedbackStatus.OPEN, FeedbackStatus.ROUTED}:
        return "held"
    if any(
        entry.status in PENDING_TASK_STATUSES | FAILED_TASK_STATUSES
        for entry in linked_task_entries
    ):
        return "held"
    if any(entry.status == AgentTaskStatus.COMPLETED for entry in linked_task_entries):
        return "revised"
    resolution_notes = (feedback.resolution_notes or "").lower()
    if any(
        token in resolution_notes
        for token in ("revise", "revised", "updated", "changed", "incorporated")
    ):
        return "revised"
    return "accepted"


def _message_feedback_id(message) -> UUID | None:
    payload = message.payload or {}
    candidate = payload.get("feedback_id") or payload.get("source_feedback_id")
    if candidate is None and isinstance(payload.get("feedback"), dict):
        candidate = payload["feedback"].get("feedback_id")
    if candidate is None and isinstance(payload.get("metadata"), dict):
        candidate = payload["metadata"].get("feedback_id")
    if candidate is None:
        return None
    try:
        return UUID(str(candidate))
    except (TypeError, ValueError):
        return None


def _metadata_uuid_list(metadata: dict[str, Any], *keys: str) -> list[UUID]:
    uuids: list[UUID] = []
    for raw_value in _metadata_values(metadata, *keys):
        try:
            value = UUID(str(raw_value))
        except (TypeError, ValueError):
            continue
        if value not in uuids:
            uuids.append(value)
    return uuids


def _metadata_str_list(metadata: dict[str, Any], *keys: str) -> list[str]:
    values: list[str] = []
    for raw_value in _metadata_values(metadata, *keys):
        value = str(raw_value).strip()
        if value and value not in values:
            values.append(value)
    return values


def _metadata_values(metadata: dict[str, Any], *keys: str) -> list[Any]:
    values: list[Any] = []
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, list):
            values.extend(value)
        elif value is not None:
            values.append(value)
        if values:
            break
    return values


def _metadata_string(metadata: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _unique_entry_ids(entries, attribute: str) -> list[UUID]:
    unique: list[UUID] = []
    for entry in entries:
        for value in getattr(entry, attribute):
            if value not in unique:
                unique.append(value)
    return unique


def _ledger_status(
    *,
    open_feedback_count: int,
    routed_feedback_count: int,
    pending_linked_task_count: int,
    blocked_linked_task_count: int,
    failed_linked_task_count: int,
) -> str:
    if open_feedback_count or blocked_linked_task_count:
        return "blocked"
    if routed_feedback_count or pending_linked_task_count or failed_linked_task_count:
        return "needs_attention"
    return "ready"


def _recommended_next_actions(
    *,
    open_feedback_count: int,
    routed_feedback_count: int,
    pending_linked_task_count: int,
    blocked_linked_task_count: int,
    failed_linked_task_count: int,
    resolved_feedback_count: int,
) -> list[str]:
    actions: list[str] = []
    if open_feedback_count:
        actions.append("Resolve or route open human feedback before resuming autonomous work.")
    if blocked_linked_task_count:
        actions.append("Review blocked feedback-linked A2A tasks before another autonomous pass.")
    if failed_linked_task_count:
        actions.append(
            "Review or retry failed or canceled feedback-linked A2A tasks before closing feedback."
        )
    if routed_feedback_count:
        actions.append("Run the specialist workers that own routed feedback tasks.")
    if pending_linked_task_count:
        actions.append("Run a worker cycle or active profile heartbeat for pending feedback-linked tasks.")
    if resolved_feedback_count and not actions:
        actions.append("Feedback gates are resolved; continue with guardrails and publish readiness.")
    if not actions:
        actions.append("No feedback blockers are present.")
    return actions
