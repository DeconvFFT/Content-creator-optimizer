from typing import Any, TypedDict

from langgraph.graph import END, StateGraph


class FoundationGraphState(TypedDict, total=False):
    run_id: str
    goal: str
    conversation_turn: str
    active_agents: list[str]
    source_required: bool
    feedback_required: bool
    events: list[dict[str, Any]]


def _route_intent(state: FoundationGraphState) -> FoundationGraphState:
    events = state.get("events", [])
    return {
        **state,
        "active_agents": [
            "intent-router",
            "content-strategist",
            "web-research-agent",
            "claim-verification-agent",
        ],
        "source_required": True,
        "events": events
        + [{"actor": "intent-router", "event_type": "task_plan_created"}],
    }


def _wait_for_human_feedback(state: FoundationGraphState) -> FoundationGraphState:
    events = state.get("events", [])
    return {
        **state,
        "feedback_required": True,
        "events": events
        + [
            {
                "actor": "forward-deployed-engineer",
                "event_type": "human_feedback_gate_opened",
            }
        ],
    }


def build_foundation_graph():
    """Build the first durable orchestration graph.

    The production runtime wires this graph to LangGraph's Postgres checkpointer.
    """

    graph = StateGraph(FoundationGraphState)
    graph.add_node("route_intent", _route_intent)
    graph.add_node("human_feedback_gate", _wait_for_human_feedback)
    graph.set_entry_point("route_intent")
    graph.add_edge("route_intent", "human_feedback_gate")
    graph.add_edge("human_feedback_gate", END)
    return graph.compile()
