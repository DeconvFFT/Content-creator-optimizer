from collections import Counter
from uuid import UUID

from all_about_llms.agents import get_agent_card
from all_about_llms.contracts import (
    A2ACollaborationEdge,
    A2ACollaborationGraphRequest,
    A2ACollaborationGraphResult,
    A2ACollaborationNode,
    AgentMessage,
    AgentTaskStatus,
    ArtifactRecord,
    ArtifactType,
    RunEvent,
)
from all_about_llms.realtime_safety import (
    redact_realtime_string,
    safe_realtime_metadata,
)


class A2ACollaborationGraphError(RuntimeError):
    """Base error for A2A collaboration graph generation."""


class A2ACollaborationGraphRunNotFoundError(A2ACollaborationGraphError):
    """Raised when a collaboration graph references a missing run."""


ACTIVE_TASK_STATUSES = {
    AgentTaskStatus.ACCEPTED,
    AgentTaskStatus.CLAIMED,
    AgentTaskStatus.IN_PROGRESS,
    AgentTaskStatus.WAITING_FOR_HUMAN,
    AgentTaskStatus.BLOCKED,
}


class A2ACollaborationGraphWorkflow:
    """Build a dependency and handoff graph for current A2A coordination."""

    def __init__(self, store):
        self._store = store

    async def build(
        self,
        run_id: UUID,
        request: A2ACollaborationGraphRequest,
    ) -> A2ACollaborationGraphResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise A2ACollaborationGraphRunNotFoundError(f"Run not found: {run_id}")

        messages = await self._store.list_agent_messages(
            run_id,
            limit=request.max_messages,
        )
        if not request.include_completed_tasks:
            messages = [
                message
                for message in messages
                if message.status in ACTIVE_TASK_STATUSES
            ]
        messages_by_id = {message.message_id: message for message in messages}
        dependency_cycles = _dependency_cycles(messages, messages_by_id)
        dependency_cycle_message_ids = sorted(
            {message_id for cycle in dependency_cycles for message_id in cycle},
            key=str,
        )
        dependency_cycle_message_id_set = set(dependency_cycle_message_ids)
        nodes = _agent_nodes(run.active_agents, messages)
        nodes.extend(
            _task_node(
                message,
                messages_by_id,
                dependency_cycle_message_id_set,
            )
            for message in messages
        )
        nodes.extend(_missing_dependency_nodes(messages, messages_by_id))
        edges = _edges(messages, messages_by_id, dependency_cycle_message_id_set)

        ready_task_ids = [
            message.message_id
            for message in messages
            if _claimable(message, messages_by_id)
        ]
        dependency_waiting_task_ids = [
            message.message_id
            for message in messages
            if message.status == AgentTaskStatus.ACCEPTED
            and _unmet_dependency_message_ids(message, messages_by_id)
        ]
        blocked_task_ids = [
            message.message_id
            for message in messages
            if message.status
            in {AgentTaskStatus.WAITING_FOR_HUMAN, AgentTaskStatus.BLOCKED}
        ]
        retry_exhausted_task_ids = [
            message.message_id for message in messages if _retry_exhausted(message)
        ]
        trace_gap_task_ids = [
            message.message_id for message in messages if not message.handoff_trace
        ]
        recommended_actions = _recommended_actions(
            ready_task_ids=ready_task_ids,
            dependency_waiting_task_ids=dependency_waiting_task_ids,
            retry_exhausted_task_ids=retry_exhausted_task_ids,
            trace_gap_task_ids=trace_gap_task_ids,
            dependency_cycle_message_ids=dependency_cycle_message_ids,
            messages_by_id=messages_by_id,
        )
        result = A2ACollaborationGraphResult(
            run_id=run_id,
            agent_count=sum(1 for node in nodes if node.node_type == "agent"),
            task_count=sum(1 for node in nodes if node.node_type == "task"),
            edge_count=len(edges),
            ready_task_ids=ready_task_ids,
            dependency_waiting_task_ids=dependency_waiting_task_ids,
            blocked_task_ids=blocked_task_ids,
            retry_exhausted_task_ids=retry_exhausted_task_ids,
            trace_gap_task_ids=trace_gap_task_ids,
            dependency_cycle_message_ids=dependency_cycle_message_ids,
            dependency_cycles=dependency_cycles,
            nodes=nodes,
            edges=edges,
            recommended_actions=recommended_actions,
            summary=_summary(
                messages=messages,
                ready_task_ids=ready_task_ids,
                dependency_waiting_task_ids=dependency_waiting_task_ids,
                blocked_task_ids=blocked_task_ids,
                retry_exhausted_task_ids=retry_exhausted_task_ids,
                trace_gap_task_ids=trace_gap_task_ids,
                dependency_cycles=dependency_cycles,
            ),
        )

        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.A2A_COLLABORATION_GRAPH,
                title="A2A collaboration graph",
                uri=f"artifact://runs/{run_id}/a2a-collaboration-graph",
                content=result.model_dump(
                    mode="json",
                    exclude={"artifact_id", "event_id"},
                ),
                provenance={
                    "workflow": "a2a_collaboration_graph_v1",
                    "agent_id": "a2a-protocol-agent",
                    "include_completed_tasks": request.include_completed_tasks,
                    "max_messages": request.max_messages,
                    "source_message_ids": [
                        str(message.message_id) for message in messages
                    ],
                },
                revision_history=[
                    {
                        "actor": "a2a-protocol-agent",
                        "note": "Built dependency, handoff, and readiness graph for active multi-agent coordination.",
                    }
                ],
            )
            result.artifact_id = artifact.artifact_id
            artifact.content["artifact_id"] = str(artifact.artifact_id)
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
                event_type="a2a_collaboration_graph_built",
                actor="a2a-protocol-agent",
                payload={
                    "artifact_id": str(result.artifact_id)
                    if result.artifact_id
                    else None,
                    "agent_count": result.agent_count,
                    "task_count": result.task_count,
                    "edge_count": result.edge_count,
                    "ready_task_count": len(result.ready_task_ids),
                    "dependency_waiting_task_count": len(
                        result.dependency_waiting_task_ids
                    ),
                    "blocked_task_count": len(result.blocked_task_ids),
                    "retry_exhausted_task_count": len(
                        result.retry_exhausted_task_ids
                    ),
                    "trace_gap_task_count": len(result.trace_gap_task_ids),
                    "dependency_cycle_count": len(result.dependency_cycles),
                    "dependency_cycle_message_count": len(
                        result.dependency_cycle_message_ids
                    ),
                },
            )
        )
        result.event_id = event.event_id
        return result


def _agent_nodes(
    run_active_agents: list[str],
    messages: list[AgentMessage],
) -> list[A2ACollaborationNode]:
    agent_ids = set(run_active_agents)
    for message in messages:
        agent_ids.update(
            agent_id
            for agent_id in [
                message.sender_agent_id,
                message.recipient_agent_id,
                message.claimed_by_agent_id,
            ]
            if agent_id
        )
        agent_ids.update(
            actor
            for trace in message.handoff_trace
            if (actor := _safe_trace_text(trace.get("actor")))
        )
    task_counts = Counter(message.recipient_agent_id for message in messages)
    nodes = []
    for agent_id in sorted(agent_ids):
        card = get_agent_card(agent_id)
        nodes.append(
            A2ACollaborationNode(
                node_id=_agent_node_id(agent_id),
                node_type="agent",
                label=card.name if card else agent_id,
                agent_id=agent_id,
                metadata={
                    "role": card.role if card else None,
                    "inbox_task_count": task_counts.get(agent_id, 0),
                    "known_agent": card is not None,
                },
            )
        )
    return nodes


def _missing_dependency_nodes(
    messages: list[AgentMessage],
    messages_by_id: dict[UUID, AgentMessage],
) -> list[A2ACollaborationNode]:
    missing_dependency_ids = sorted(
        {
            dependency_id
            for message in messages
            for dependency_id in message.depends_on_message_ids
            if dependency_id not in messages_by_id
        },
        key=str,
    )
    return [
        A2ACollaborationNode(
            node_id=_task_node_id(dependency_id),
            node_type="task",
            label=f"Missing dependency {dependency_id}",
            message_id=dependency_id,
            status="missing",
            metadata={"missing_dependency": True},
        )
        for dependency_id in missing_dependency_ids
    ]


def _task_node(
    message: AgentMessage,
    messages_by_id: dict[UUID, AgentMessage],
    dependency_cycle_message_ids: set[UUID],
) -> A2ACollaborationNode:
    unmet_dependency_ids = _unmet_dependency_message_ids(message, messages_by_id)
    return A2ACollaborationNode(
        node_id=_task_node_id(message.message_id),
        node_type="task",
        label=f"{message.task_type} -> {message.recipient_agent_id}",
        message_id=message.message_id,
        status=message.status.value,
        metadata={
            "sender_agent_id": message.sender_agent_id,
            "recipient_agent_id": message.recipient_agent_id,
            "claimed_by_agent_id": message.claimed_by_agent_id,
            "task_type": message.task_type,
            "attempt_count": message.attempt_count,
            "max_attempts": message.max_attempts,
            "depends_on_message_ids": [
                str(message_id) for message_id in message.depends_on_message_ids
            ],
            "unmet_dependency_message_ids": [
                str(message_id) for message_id in unmet_dependency_ids
            ],
            "claimable": _claimable(message, messages_by_id),
            "retry_exhausted": _retry_exhausted(message),
            "in_dependency_cycle": message.message_id
            in dependency_cycle_message_ids,
            "handoff_trace_count": len(message.handoff_trace),
            "latest_handoff_action": (
                _safe_trace_text(message.handoff_trace[-1].get("action"))
                if message.handoff_trace
                else None
            ),
        },
    )


def _edges(
    messages: list[AgentMessage],
    messages_by_id: dict[UUID, AgentMessage],
    dependency_cycle_message_ids: set[UUID],
) -> list[A2ACollaborationEdge]:
    edges = []
    for message in messages:
        task_node_id = _task_node_id(message.message_id)
        edges.append(
            A2ACollaborationEdge(
                source_node_id=_agent_node_id(message.sender_agent_id),
                target_node_id=task_node_id,
                edge_type="created",
                metadata={"task_type": message.task_type},
            )
        )
        edges.append(
            A2ACollaborationEdge(
                source_node_id=task_node_id,
                target_node_id=_agent_node_id(message.recipient_agent_id),
                edge_type="assigned_to",
                status=message.status.value,
                metadata={"task_type": message.task_type},
            )
        )
        if message.claimed_by_agent_id:
            edges.append(
                A2ACollaborationEdge(
                    source_node_id=task_node_id,
                    target_node_id=_agent_node_id(message.claimed_by_agent_id),
                    edge_type="claimed_by",
                    status=message.status.value,
                    metadata={"attempt_count": message.attempt_count},
                )
            )
        for dependency_id in message.depends_on_message_ids:
            dependency = messages_by_id.get(dependency_id)
            if (
                dependency_id in dependency_cycle_message_ids
                and message.message_id in dependency_cycle_message_ids
            ):
                status = "cycle"
            elif dependency and dependency.status == AgentTaskStatus.COMPLETED:
                status = "satisfied"
            else:
                status = "waiting"
            edges.append(
                A2ACollaborationEdge(
                    source_node_id=_task_node_id(dependency_id),
                    target_node_id=task_node_id,
                    edge_type="depends_on",
                    status=status,
                    metadata={
                        "dependency_message_id": str(dependency_id),
                        "dependency_status": (
                            dependency.status.value if dependency else "missing"
                        ),
                        "in_dependency_cycle": status == "cycle",
                    },
                )
            )
        for trace in message.handoff_trace:
            actor = _safe_trace_text(trace.get("actor"))
            action = _safe_trace_text(trace.get("action"))
            if not actor or not action:
                continue
            status = _safe_trace_text(trace.get("status") or message.status.value)
            edges.append(
                A2ACollaborationEdge(
                    source_node_id=_agent_node_id(actor),
                    target_node_id=task_node_id,
                    edge_type=f"trace:{action}",
                    status=status or "unknown",
                    metadata=safe_realtime_metadata(
                        {
                            "at": trace.get("at"),
                            "notes": trace.get("notes"),
                        }
                    ),
                )
            )
    return edges


def _safe_trace_text(value: object) -> str | None:
    if value is None:
        return None
    text = redact_realtime_string(str(value)).strip()
    return text or None


def _claimable(
    message: AgentMessage,
    messages_by_id: dict[UUID, AgentMessage],
) -> bool:
    return (
        message.status == AgentTaskStatus.ACCEPTED
        and message.attempt_count < message.max_attempts
        and not _unmet_dependency_message_ids(message, messages_by_id)
    )


def _unmet_dependency_message_ids(
    message: AgentMessage,
    messages_by_id: dict[UUID, AgentMessage],
) -> list[UUID]:
    unmet = []
    for dependency_id in message.depends_on_message_ids:
        dependency = messages_by_id.get(dependency_id)
        if dependency is None or dependency.status != AgentTaskStatus.COMPLETED:
            unmet.append(dependency_id)
    return unmet


def _dependency_cycles(
    messages: list[AgentMessage],
    messages_by_id: dict[UUID, AgentMessage],
) -> list[list[UUID]]:
    active_message_ids = {
        message.message_id
        for message in messages
        if message.status != AgentTaskStatus.COMPLETED
    }
    adjacency = {
        message.message_id: sorted(
            [
                dependency_id
                for dependency_id in message.depends_on_message_ids
                if dependency_id in messages_by_id
                and dependency_id in active_message_ids
            ],
            key=str,
        )
        for message in messages
        if message.message_id in active_message_ids
    }
    cycles_by_key: dict[tuple[str, ...], list[UUID]] = {}

    def visit(node_id: UUID, path: list[UUID]) -> None:
        if node_id in path:
            cycle = path[path.index(node_id) :]
            key = _canonical_cycle_key(cycle)
            cycles_by_key.setdefault(key, cycle)
            return
        for dependency_id in adjacency.get(node_id, []):
            visit(dependency_id, [*path, node_id])

    for message_id in sorted(adjacency, key=str):
        visit(message_id, [])
    return [
        cycles_by_key[key]
        for key in sorted(cycles_by_key)
    ]


def _canonical_cycle_key(cycle: list[UUID]) -> tuple[str, ...]:
    cycle_values = [str(message_id) for message_id in cycle]
    rotations = [
        tuple(cycle_values[index:] + cycle_values[:index])
        for index in range(len(cycle_values))
    ]
    return min(rotations)


def _retry_exhausted(message: AgentMessage) -> bool:
    retry_policy = message.result.get("retry_policy", {})
    retry_policy_attempts = retry_policy.get("attempt_count", message.attempt_count)
    retry_policy_max_attempts = retry_policy.get("max_attempts", message.max_attempts)
    return (
        message.status == AgentTaskStatus.BLOCKED
        and retry_policy_attempts >= retry_policy_max_attempts
    )


def _recommended_actions(
    *,
    ready_task_ids: list[UUID],
    dependency_waiting_task_ids: list[UUID],
    retry_exhausted_task_ids: list[UUID],
    trace_gap_task_ids: list[UUID],
    dependency_cycle_message_ids: list[UUID],
    messages_by_id: dict[UUID, AgentMessage],
) -> list[str]:
    actions = []
    if dependency_cycle_message_ids:
        actions.append(
            "Break A2A dependency cycles before waiting tasks can make progress."
        )
    if ready_task_ids:
        agents = sorted(
            {
                messages_by_id[message_id].recipient_agent_id
                for message_id in ready_task_ids
                if message_id in messages_by_id
            }
        )
        actions.append("Run workers for ready agents: " + ", ".join(agents) + ".")
    if dependency_waiting_task_ids:
        actions.append(
            "Complete upstream dependency tasks before dependent A2A work is claimable."
        )
    if retry_exhausted_task_ids:
        actions.append(
            "Authorize retry or revise blocked retry-exhausted tasks before resume."
        )
    if trace_gap_task_ids:
        actions.append(
            "Inspect legacy A2A tasks missing handoff_trace before relying on audit history."
        )
    if not actions:
        actions.append("No immediate A2A coordination action required.")
    return actions


def _summary(
    *,
    messages: list[AgentMessage],
    ready_task_ids: list[UUID],
    dependency_waiting_task_ids: list[UUID],
    blocked_task_ids: list[UUID],
    retry_exhausted_task_ids: list[UUID],
    trace_gap_task_ids: list[UUID],
    dependency_cycles: list[list[UUID]],
) -> str:
    return (
        f"A2A graph mapped {len(messages)} task(s): "
        f"{len(ready_task_ids)} ready, "
        f"{len(dependency_waiting_task_ids)} waiting on dependencies, "
        f"{len(blocked_task_ids)} blocked/waiting, "
        f"{len(retry_exhausted_task_ids)} retry-exhausted, and "
        f"{len(trace_gap_task_ids)} missing trace evidence, with "
        f"{len(dependency_cycles)} dependency cycle(s)."
    )


def _agent_node_id(agent_id: str) -> str:
    return f"agent:{agent_id}"


def _task_node_id(message_id: UUID) -> str:
    return f"task:{message_id}"
