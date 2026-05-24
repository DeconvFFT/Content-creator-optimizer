from typing import Any
from uuid import UUID

from all_about_llms.agents import get_agent_card
from all_about_llms.contracts import RunEvent


class AgentToolPolicyError(RuntimeError):
    """Raised when an agent tries to use a tool outside its agent card."""


class AgentModelPolicyError(RuntimeError):
    """Raised when an agent tries to use a model outside its agent card."""


async def require_tool_allowed(
    store,
    *,
    run_id: UUID,
    agent_id: str,
    tool_name: str,
    reason: str,
    message_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    agent = get_agent_card(agent_id)
    allowed_tools = list(agent.allowed_tools) if agent is not None else []
    approved = tool_name in allowed_tools
    await store.append_event(
        RunEvent(
            run_id=run_id,
            event_type=(
                "agent_tool_use_approved" if approved else "agent_tool_use_denied"
            ),
            actor="agent-harness-engineer",
            payload={
                "agent_id": agent_id,
                "tool_name": tool_name,
                "allowed_tools": allowed_tools,
                "reason": reason,
                "message_id": str(message_id) if message_id else None,
                "metadata": metadata or {},
            },
        )
    )
    if not approved:
        raise AgentToolPolicyError(
            f"{agent_id} is not allowed to use tool '{tool_name}'."
        )


async def require_model_allowed(
    store,
    *,
    run_id: UUID,
    agent_id: str,
    model_id: str,
    reason: str,
    message_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    agent = get_agent_card(agent_id)
    allowed_models = list(agent.allowed_models) if agent is not None else []
    approved = any(
        _model_matches(model_id, allowed_model) for allowed_model in allowed_models
    )
    await store.append_event(
        RunEvent(
            run_id=run_id,
            event_type=(
                "agent_model_use_approved" if approved else "agent_model_use_denied"
            ),
            actor="agent-harness-engineer",
            payload={
                "agent_id": agent_id,
                "model_id": model_id,
                "allowed_models": allowed_models,
                "reason": reason,
                "message_id": str(message_id) if message_id else None,
                "metadata": metadata or {},
            },
        )
    )
    if not approved:
        raise AgentModelPolicyError(
            f"{agent_id} is not allowed to use model '{model_id}'."
        )


def _model_matches(model_id: str, allowed_model: str) -> bool:
    normalized_model = model_id.removeprefix("google/")
    normalized_allowed = allowed_model.removeprefix("google/")
    return model_id == allowed_model or normalized_model == normalized_allowed
