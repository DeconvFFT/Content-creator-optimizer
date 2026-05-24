from uuid import UUID

from all_about_llms.agents import get_agent_card
from all_about_llms.contracts import (
    AgentMemory,
    ProjectMemoryKind,
    ProjectMemoryRecordRequest,
    ProjectMemoryRecordResult,
    ProjectMemoryScope,
    RunEvent,
)
from all_about_llms.realtime_safety import safe_realtime_metadata


class ProjectMemoryRunNotFoundError(RuntimeError):
    """Raised when a project memory references a missing run."""


class ProjectMemoryAgentNotFoundError(RuntimeError):
    """Raised when a project memory is assigned to an unknown agent."""


DEFAULT_PROJECT_MEMORY_AGENT_IDS = {
    ProjectMemoryKind.USER_PREFERENCE: "context-engineering-agent",
    ProjectMemoryKind.PROJECT_DECISION: "product-manager",
}


class ProjectMemoryWorkflow:
    """Record typed project memory on top of the pgvector-backed memory store."""

    def __init__(self, store):
        self._store = store

    async def record(
        self,
        run_id: UUID,
        request: ProjectMemoryRecordRequest,
    ) -> ProjectMemoryRecordResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise ProjectMemoryRunNotFoundError(f"Run not found: {run_id}")

        agent_id = request.agent_id or DEFAULT_PROJECT_MEMORY_AGENT_IDS[
            request.memory_kind
        ]
        if get_agent_card(agent_id) is None:
            raise ProjectMemoryAgentNotFoundError(f"Agent not found: {agent_id}")

        memory = AgentMemory(
            agent_id=agent_id,
            run_id=run_id if request.scope == ProjectMemoryScope.RUN else None,
            memory_kind=request.memory_kind.value,
            content=request.content,
            embedding=request.embedding,
            metadata={
                **request.metadata,
                "project_memory_kind": request.memory_kind.value,
                "memory_scope": request.scope.value,
                "source_run_id": str(run_id),
                "confidence": request.confidence,
                "tags": request.tags,
                "source_artifact_ids": [
                    str(artifact_id) for artifact_id in request.source_artifact_ids
                ],
                "target_wiki_notes": request.target_wiki_notes,
                "workflow": "project_memory_record_v1",
            },
        )
        await self._store.record_memory(memory)
        event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="project_memory_recorded",
                actor=agent_id,
                payload=safe_realtime_metadata(
                    {
                        "memory": memory.model_dump(mode="json"),
                        "memory_kind": request.memory_kind.value,
                        "memory_scope": request.scope.value,
                        "source_run_id": str(run_id),
                        "target_wiki_notes": request.target_wiki_notes,
                        "source_artifact_ids": [
                            str(artifact_id)
                            for artifact_id in request.source_artifact_ids
                        ],
                    }
                ),
            )
        )
        return ProjectMemoryRecordResult(
            run_id=run_id,
            memory=memory,
            memory_scope=request.scope,
            event_id=event.event_id,
            summary=(
                f"Recorded {request.scope.value} {request.memory_kind.value} "
                f"memory for {agent_id}."
            ),
        )
