from datetime import datetime, timezone
from typing import Any

from all_about_llms.contracts import AgentMessage, AgentTaskStatus


def build_handoff_trace_entry(
    *,
    actor: str,
    action: str,
    status: AgentTaskStatus | str,
    notes: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "at": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "status": status.value if isinstance(status, AgentTaskStatus) else status,
        "notes": notes,
        "metadata": metadata or {},
    }


def append_handoff_trace(
    message: AgentMessage,
    *,
    actor: str,
    action: str,
    status: AgentTaskStatus | str,
    notes: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AgentMessage:
    message.handoff_trace.append(
        build_handoff_trace_entry(
            actor=actor,
            action=action,
            status=status,
            notes=notes,
            metadata=metadata,
        )
    )
    return message


def ensure_message_accepted_trace(message: AgentMessage) -> AgentMessage:
    if message.handoff_trace:
        return message
    return append_handoff_trace(
        message,
        actor=message.sender_agent_id,
        action="accepted",
        status=message.status,
        notes="A2A task was accepted into the durable message ledger.",
        metadata={
            "recipient_agent_id": message.recipient_agent_id,
            "task_type": message.task_type,
            "depends_on_message_ids": [
                str(message_id) for message_id in message.depends_on_message_ids
            ],
        },
    )
