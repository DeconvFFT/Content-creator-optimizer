from typing import Any

from all_about_llms.contracts import (
    AgentMessage,
    AgentMessagePublicProjection,
    AgentTaskStatus,
)
from all_about_llms.realtime_safety import redact_realtime_string, safe_realtime_metadata


def public_a2a_message_projection(message: AgentMessage) -> AgentMessagePublicProjection:
    return AgentMessagePublicProjection(
        message_id=message.message_id,
        run_id=message.run_id,
        sender_agent_id=_safe_public_a2a_text(message.sender_agent_id),
        recipient_agent_id=_safe_public_a2a_text(message.recipient_agent_id),
        task_type=_safe_public_a2a_text(message.task_type),
        payload=safe_realtime_metadata(message.payload),
        depends_on_message_ids=message.depends_on_message_ids,
        requires_human_feedback=message.requires_human_feedback,
        status=message.status,
        claimed_by_agent_id=(
            _safe_public_a2a_text(message.claimed_by_agent_id)
            if message.claimed_by_agent_id is not None
            else None
        ),
        attempt_count=message.attempt_count,
        max_attempts=message.max_attempts,
        result=safe_realtime_metadata(message.result),
        handoff_trace=[
            safe_realtime_metadata(entry) for entry in message.handoff_trace
        ],
        error=redact_realtime_string(message.error) if message.error else None,
        created_at=message.created_at,
        updated_at=message.updated_at,
        redaction={
            "projection": "public",
            "raw_fields_redacted": True,
            "policy": "agent-message-public-projection-v1",
        },
    )


def public_a2a_message_event_payload(message: AgentMessage) -> dict[str, Any]:
    return public_a2a_message_projection(message).model_dump(mode="json")


def public_a2a_status_event_payload(
    *,
    message: AgentMessage,
    from_status: AgentTaskStatus | str,
    to_status: AgentTaskStatus | str,
    notes: str | None,
    has_result: bool,
    has_error: bool,
    skill_ids: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "message_id": str(message.message_id),
        "from_status": _status_value(from_status),
        "to_status": _status_value(to_status),
        "task_type": _safe_public_a2a_text(message.task_type),
        "sender_agent_id": _safe_public_a2a_text(message.sender_agent_id),
        "recipient_agent_id": _safe_public_a2a_text(message.recipient_agent_id),
        "notes": _safe_public_a2a_text(notes) if notes is not None else None,
        "has_result": has_result,
        "has_error": has_error,
    }
    if skill_ids is not None:
        payload["skill_ids"] = skill_ids
    return payload


def public_a2a_retry_event_payload(
    *,
    message: AgentMessage,
    from_status: AgentTaskStatus | str,
    to_status: AgentTaskStatus | str,
    previous_attempt_count: int,
    attempt_count: int,
    previous_max_attempts: int,
    max_attempts: int,
    reset_attempt_count: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "message_id": str(message.message_id),
        "from_status": _status_value(from_status),
        "to_status": _status_value(to_status),
        "sender_agent_id": _safe_public_a2a_text(message.sender_agent_id),
        "recipient_agent_id": _safe_public_a2a_text(message.recipient_agent_id),
        "task_type": _safe_public_a2a_text(message.task_type),
        "previous_attempt_count": previous_attempt_count,
        "attempt_count": attempt_count,
        "previous_max_attempts": previous_max_attempts,
        "max_attempts": max_attempts,
        "reset_attempt_count": reset_attempt_count,
        "reason": _safe_public_a2a_text(reason),
    }


def public_a2a_dependency_repair_event_payload(
    *,
    message: AgentMessage,
    removed_dependency_message_ids: list[Any],
    remaining_dependency_message_ids: list[Any],
    reason: str,
) -> dict[str, Any]:
    return {
        "message_id": str(message.message_id),
        "sender_agent_id": _safe_public_a2a_text(message.sender_agent_id),
        "recipient_agent_id": _safe_public_a2a_text(message.recipient_agent_id),
        "task_type": _safe_public_a2a_text(message.task_type),
        "removed_dependency_message_ids": [
            str(dependency_id) for dependency_id in removed_dependency_message_ids
        ],
        "remaining_dependency_message_ids": [
            str(dependency_id) for dependency_id in remaining_dependency_message_ids
        ],
        "reason": _safe_public_a2a_text(reason),
    }


def public_a2a_dependency_waiting_event_payload(
    *,
    message: AgentMessage,
    worker_agent_id: str,
    unmet_dependency_message_ids: list[Any],
    notes: str,
) -> dict[str, Any]:
    return {
        "message_id": str(message.message_id),
        "recipient_agent_id": _safe_public_a2a_text(message.recipient_agent_id),
        "worker_agent_id": _safe_public_a2a_text(worker_agent_id),
        "task_type": _safe_public_a2a_text(message.task_type),
        "depends_on_message_ids": [
            str(dependency_id) for dependency_id in message.depends_on_message_ids
        ],
        "unmet_dependency_message_ids": [
            str(dependency_id) for dependency_id in unmet_dependency_message_ids
        ],
        "notes": _safe_public_a2a_text(notes),
    }


def public_a2a_retry_exhausted_event_payload(
    *,
    message: AgentMessage,
    worker_agent_id: str,
    notes: str,
) -> dict[str, Any]:
    return {
        "message_id": str(message.message_id),
        "status": _status_value(message.status),
        "recipient_agent_id": _safe_public_a2a_text(message.recipient_agent_id),
        "worker_agent_id": _safe_public_a2a_text(worker_agent_id),
        "task_type": _safe_public_a2a_text(message.task_type),
        "attempt_count": message.attempt_count,
        "max_attempts": message.max_attempts,
        "notes": _safe_public_a2a_text(notes),
    }


def public_a2a_recovered_event_payload(
    *,
    message: AgentMessage,
    from_status: AgentTaskStatus | str,
    to_status: AgentTaskStatus | str,
    previous_claimed_by_agent_id: str | None,
    previous_updated_at: Any,
    worker_agent_id: str,
    stale_after_seconds: float,
    notes: str,
) -> dict[str, Any]:
    return {
        "message_id": str(message.message_id),
        "from_status": _status_value(from_status),
        "to_status": _status_value(to_status),
        "previous_claimed_by_agent_id": (
            _safe_public_a2a_text(previous_claimed_by_agent_id)
            if previous_claimed_by_agent_id is not None
            else None
        ),
        "previous_updated_at": (
            previous_updated_at.isoformat()
            if hasattr(previous_updated_at, "isoformat")
            else previous_updated_at
        ),
        "recipient_agent_id": _safe_public_a2a_text(message.recipient_agent_id),
        "worker_agent_id": _safe_public_a2a_text(worker_agent_id),
        "task_type": _safe_public_a2a_text(message.task_type),
        "stale_after_seconds": stale_after_seconds,
        "notes": _safe_public_a2a_text(notes),
    }


def public_a2a_context_packet_event_payload(
    context_summary: dict[str, Any],
) -> dict[str, Any]:
    return safe_realtime_metadata(context_summary)


def public_a2a_skill_invocation_event_payload(
    *,
    skill_usage: dict[str, Any],
    status: AgentTaskStatus | str,
    notes: str,
) -> dict[str, Any]:
    return safe_realtime_metadata(
        {
            **skill_usage,
            "status": _status_value(status),
            "notes": notes,
        }
    )


def _status_value(status: AgentTaskStatus | str) -> str:
    return status.value if isinstance(status, AgentTaskStatus) else status


def _safe_public_a2a_text(value: str) -> str:
    return redact_realtime_string(value)
