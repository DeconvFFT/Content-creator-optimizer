from collections import Counter
from typing import Any
from uuid import UUID

from all_about_llms.agents import skill_cards_for_agent
from all_about_llms.contracts import (
    AgentMessage,
    AgentTaskStatus,
    AgentWorkerCycleRequest,
    ArtifactRecord,
    ArtifactType,
    FeedbackStatus,
    RunCheckpoint,
    RunCheckpointCreate,
    RunCheckpointResult,
    RunEvent,
    RunResumePlan,
    RunResumePlanRequest,
    RunResumeRequest,
    RunResumeResult,
    RunStatus,
    RunWorkPlanRequest,
    WorkerProfileStatus,
)
from all_about_llms.orchestration.source_quality import evaluate_source_quality
from all_about_llms.orchestration.retrieval_evidence import (
    order_sources_by_retrieval_evidence,
)
from all_about_llms.orchestration.project_memory_retrieval import (
    ProjectMemoryRetrievalWorkflow,
    project_memory_retrieval_digest,
)
from all_about_llms.contracts import ProjectMemoryRetrievalRequest


class RunResumeError(RuntimeError):
    """Base error for run checkpoint and resume planning."""


class RunResumeRunNotFoundError(RunResumeError):
    """Raised when a run cannot be found for checkpoint or resume planning."""


class RunResumeWorkflow:
    """Build durable run checkpoints and resume plans from current Postgres state."""

    def __init__(self, store):
        self._store = store

    async def create_checkpoint(
        self, run_id: UUID, request: RunCheckpointCreate
    ) -> RunCheckpointResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise RunResumeRunNotFoundError(f"Run not found: {run_id}")

        state = await _collect_resume_state(self._store, run_id)
        checkpoint = RunCheckpoint(
            run_id=run_id,
            checkpoint_kind=request.checkpoint_kind,
            status=run.status,
            conversation_state=run.conversation_state,
            active_agents=run.active_agents,
            source_record_ids=run.source_record_ids,
            artifact_ids=run.artifact_ids,
            feedback_item_ids=run.feedback_item_ids,
            event_cursor=state.latest_event_id,
            state_digest=state.digest,
            created_by=request.created_by,
            notes=request.notes,
        )
        await self._store.record_run_checkpoint(checkpoint)
        event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="run_checkpoint_recorded",
                actor=request.created_by,
                payload={
                    "checkpoint_id": str(checkpoint.checkpoint_id),
                    "checkpoint_kind": checkpoint.checkpoint_kind,
                    "event_cursor": checkpoint.event_cursor,
                    "state_digest": checkpoint.state_digest,
                },
            )
        )
        return RunCheckpointResult(
            checkpoint=checkpoint,
            event_id=event.event_id,
            summary=(
                f"Recorded {checkpoint.checkpoint_kind} checkpoint at event "
                f"{checkpoint.event_cursor or 0}."
            ),
        )

    async def list_checkpoints(self, run_id: UUID, limit: int = 25) -> list[RunCheckpoint]:
        if await self._store.get_run(run_id) is None:
            raise RunResumeRunNotFoundError(f"Run not found: {run_id}")
        return await self._store.list_run_checkpoints(run_id, limit=limit)

    async def build_resume_plan(
        self, run_id: UUID, request: RunResumePlanRequest
    ) -> RunResumePlan:
        run = await self._store.get_run(run_id)
        if run is None:
            raise RunResumeRunNotFoundError(f"Run not found: {run_id}")

        state = await _collect_resume_state(self._store, run_id)
        checkpoint = None
        if request.create_checkpoint:
            checkpoint_result = await self.create_checkpoint(
                run_id,
                RunCheckpointCreate(
                    checkpoint_kind=request.checkpoint_kind,
                    created_by=request.agent_id or "agent-harness-engineer",
                    notes=request.notes,
                ),
            )
            checkpoint = checkpoint_result.checkpoint
            state = await _collect_resume_state(self._store, run_id)

        blocked_reasons = _blocked_reasons(run.status, state)
        recommended_next_actions = _recommended_next_actions(run.status, state)
        resume_allowed = not blocked_reasons
        memory_results = await self._store.search_memories(
            agent_id=request.agent_id,
            run_id=run_id,
            include_global_memories=request.include_global_memories,
            limit=request.memory_limit,
        )
        project_memory_retrieval = None
        if request.include_project_memory_retrieval:
            project_memory_retrieval = await ProjectMemoryRetrievalWorkflow(
                self._store
            ).retrieve(
                run_id,
                ProjectMemoryRetrievalRequest(
                    query=request.project_memory_query or run.goal,
                    agent_id=request.agent_id,
                    query_embedding=request.project_memory_query_embedding,
                    include_global_memories=request.include_global_memories,
                    seed_limit=request.project_memory_seed_limit,
                    memory_limit=request.project_memory_retrieval_limit,
                    graph_depth=request.project_memory_graph_depth,
                    record_artifact=False,
                ),
            )
        project_memory_retrieval_summary = project_memory_retrieval_digest(
            project_memory_retrieval
        )

        context_summary = {
            **state.digest,
            "agent_id": request.agent_id,
            "skill_ids": (
                [skill.id for skill in skill_cards_for_agent(request.agent_id)]
                if request.agent_id
                else []
            ),
            "include_global_memories": request.include_global_memories,
            "memory_limit": request.memory_limit,
            "memories": len(memory_results),
            "project_memory_retrieval": project_memory_retrieval_summary,
            "project_memory_retrieval_memory_count": (
                project_memory_retrieval_summary.get("memory_count", 0)
                if project_memory_retrieval_summary
                else 0
            ),
            "project_memory_retrieval_graph_edge_count": (
                project_memory_retrieval_summary.get("graph_edge_count", 0)
                if project_memory_retrieval_summary
                else 0
            ),
        }
        event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="resume_plan_built",
                actor=request.agent_id or "agent-harness-engineer",
                payload={
                    "checkpoint_id": (
                        str(checkpoint.checkpoint_id) if checkpoint else None
                    ),
                    "resume_allowed": resume_allowed,
                    "blocked_reasons": blocked_reasons,
                    "recommended_next_actions": recommended_next_actions,
                    "context_summary": context_summary,
                },
            )
        )
        return RunResumePlan(
            run=run,
            checkpoint=checkpoint,
            latest_event_id=state.latest_event_id,
            event_stream_after_id=event.event_id,
            resume_allowed=resume_allowed,
            blocked_reasons=blocked_reasons,
            recommended_next_actions=recommended_next_actions,
            pending_agent_messages=state.pending_agent_messages,
            open_feedback_items=state.open_feedback_items,
            active_worker_profiles=state.active_worker_profiles,
            context_summary=context_summary,
            event_id=event.event_id,
            summary=_resume_summary(
                resume_allowed=resume_allowed,
                blocked_reasons=blocked_reasons,
                pending_count=len(state.pending_agent_messages),
                open_feedback_count=len(state.open_feedback_items),
                active_profile_count=len(state.active_worker_profiles),
            ),
        )

    async def resume_run(
        self,
        run_id: UUID,
        request: RunResumeRequest,
        services=None,
    ) -> RunResumeResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise RunResumeRunNotFoundError(f"Run not found: {run_id}")
        status_before = run.status

        plan = await self.build_resume_plan(
            run_id,
            RunResumePlanRequest(
                agent_id=request.agent_id,
                include_global_memories=request.include_global_memories,
                memory_limit=request.memory_limit,
                create_checkpoint=request.create_checkpoint,
                checkpoint_kind=request.checkpoint_kind,
                notes=request.notes,
            ),
        )
        if not plan.resume_allowed:
            event = await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="run_resume_blocked",
                    actor=request.agent_id or "agent-harness-engineer",
                    payload={
                        "blocked_reasons": plan.blocked_reasons,
                        "checkpoint_id": (
                            str(plan.checkpoint.checkpoint_id)
                            if plan.checkpoint
                            else None
                        ),
                        "recommended_next_actions": plan.recommended_next_actions,
                    },
                )
            )
            latest_run = await self._store.get_run(run_id)
            return RunResumeResult(
                run_id=run_id,
                resumed=False,
                resume_plan=plan,
                status_before=status_before,
                status_after=latest_run.status if latest_run else status_before,
                event_id=event.event_id,
                summary=(
                    "Run resume blocked by "
                    f"{', '.join(plan.blocked_reasons) or 'unknown gate'}."
                ),
            )

        await self._store.update_run_status(run_id, RunStatus.RUNNING)
        start_event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="run_resume_started",
                actor=request.agent_id or "agent-harness-engineer",
                payload={
                    "checkpoint_id": (
                        str(plan.checkpoint.checkpoint_id) if plan.checkpoint else None
                    ),
                    "pending_agent_messages": len(plan.pending_agent_messages),
                    "active_worker_profiles": len(plan.active_worker_profiles),
                    "agent_ids": request.agent_ids,
                },
            )
        )

        work_plan = None
        if request.build_work_plan:
            from all_about_llms.orchestration.work_plan import RunWorkPlanWorkflow

            work_plan = await RunWorkPlanWorkflow(self._store).build(
                run_id,
                RunWorkPlanRequest(
                    record_artifact=True,
                    create_followup_tasks=request.create_followup_tasks,
                ),
            )

        from all_about_llms.orchestration.agent_worker import AgentWorker

        worker = AgentWorker(self._store, services)
        profile_heartbeats = []
        if request.heartbeat_active_profiles:
            for profile in plan.active_worker_profiles:
                profile_heartbeats.append(
                    await worker.run_profile_heartbeat(profile.profile_id)
                )

        worker_cycle = None
        if request.run_worker_cycle:
            worker_cycle = await worker.run_cycle(
                AgentWorkerCycleRequest(
                    run_id=run_id,
                    agent_ids=request.agent_ids
                    or _resume_cycle_agent_ids(plan.pending_agent_messages, work_plan),
                    max_tasks_per_agent=request.max_tasks_per_agent,
                    max_rounds=request.max_worker_rounds,
                    include_global_memories=request.include_global_memories,
                    memory_limit=request.memory_limit,
                    use_gemma=request.use_gemma,
                    fail_on_provider_error=request.fail_on_provider_error,
                )
            )

        latest_run = await self._store.get_run(run_id)
        completed_event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="run_resume_completed",
                actor=request.agent_id or "agent-harness-engineer",
                payload={
                    "start_event_id": start_event.event_id,
                    "checkpoint_id": (
                        str(plan.checkpoint.checkpoint_id) if plan.checkpoint else None
                    ),
                    "work_plan_artifact_id": (
                        str(work_plan.artifact_id)
                        if work_plan and work_plan.artifact_id
                        else None
                    ),
                    "work_plan_created_task_message_ids": (
                        [
                            str(message_id)
                            for message_id in work_plan.created_task_message_ids
                        ]
                        if work_plan
                        else []
                    ),
                    "profile_heartbeat_count": len(profile_heartbeats),
                    "profile_heartbeat_ledger_artifact_ids": [
                        str(heartbeat.heartbeat_ledger_artifact.artifact_id)
                        for heartbeat in profile_heartbeats
                        if heartbeat.heartbeat_ledger_artifact
                        and heartbeat.heartbeat_ledger_artifact.artifact_id
                    ],
                    "worker_cycle_processed_tasks": (
                        worker_cycle.total_processed_tasks if worker_cycle else 0
                    ),
                },
            )
        )
        processed_tasks = worker_cycle.total_processed_tasks if worker_cycle else 0
        processed_tasks += sum(
            heartbeat.cycle_result.total_processed_tasks
            for heartbeat in profile_heartbeats
            if heartbeat.cycle_result is not None
        )
        return RunResumeResult(
            run_id=run_id,
            resumed=True,
            resume_plan=plan,
            status_before=status_before,
            status_after=latest_run.status if latest_run else RunStatus.RUNNING,
            work_plan=work_plan,
            worker_cycle=worker_cycle,
            profile_heartbeats=profile_heartbeats,
            event_id=completed_event.event_id,
            summary=(
                "Run resumed from durable checkpoint and processed "
                f"{processed_tasks} task(s)."
            ),
        )


class _ResumeState:
    def __init__(
        self,
        *,
        latest_event_id: int | None,
        pending_agent_messages: list[AgentMessage],
        dependency_cycle_message_ids: set[UUID],
        open_feedback_items,
        active_worker_profiles,
        digest: dict,
    ):
        self.latest_event_id = latest_event_id
        self.pending_agent_messages = pending_agent_messages
        self.dependency_cycle_message_ids = dependency_cycle_message_ids
        self.open_feedback_items = open_feedback_items
        self.active_worker_profiles = active_worker_profiles
        self.digest = digest


async def _collect_resume_state(store, run_id: UUID) -> _ResumeState:
    events = await store.list_events(run_id, limit=10000)
    messages = await store.list_agent_messages(run_id)
    turns = await store.list_conversation_turns(run_id)
    realtime_sessions = await store.list_realtime_sessions(run_id)
    sources = await store.list_sources(run_id)
    claims = await store.list_claims(run_id)
    artifacts = await store.list_artifacts(run_id)
    audits = await store.list_guardrail_audits(run_id)
    feedback_items = await store.list_feedback(run_id)
    worker_profiles = await store.list_worker_profiles(run_id)

    pending_statuses = {
        AgentTaskStatus.ACCEPTED,
        AgentTaskStatus.CLAIMED,
        AgentTaskStatus.IN_PROGRESS,
        AgentTaskStatus.WAITING_FOR_HUMAN,
        AgentTaskStatus.BLOCKED,
    }
    pending_messages = [
        message for message in messages if message.status in pending_statuses
    ]
    messages_by_id = {message.message_id: message for message in messages}
    dependency_cycle_message_ids = _dependency_cycle_message_ids(
        messages,
        messages_by_id,
    )
    open_feedback_items = [
        feedback for feedback in feedback_items if feedback.status == FeedbackStatus.OPEN
    ]
    active_profiles = [
        profile for profile in worker_profiles if profile.status == WorkerProfileStatus.ACTIVE
    ]
    message_status_counts = Counter(message.status.value for message in messages)
    artifact_type_counts = Counter(
        artifact.artifact_type.value for artifact in artifacts
    )
    audit_status_counts = Counter(audit.status.value for audit in audits)
    feedback_status_counts = Counter(feedback.status.value for feedback in feedback_items)
    latest_realtime_ledger = _latest_artifact_of_type(
        artifacts,
        ArtifactType.REALTIME_DIALOGUE_LEDGER,
    )
    latest_feedback_ledger = _latest_artifact_of_type(
        artifacts,
        ArtifactType.FEEDBACK_RESOLUTION_LEDGER,
    )
    latest_retrieval_ledger = _latest_artifact_of_type(
        artifacts,
        ArtifactType.RETRIEVAL_QUALITY_LEDGER,
    )
    latest_foundation_audit = _latest_artifact_of_type(
        artifacts,
        ArtifactType.FOUNDATION_AUDIT,
    )
    latest_artifact_index = _latest_artifact_of_type(
        artifacts,
        ArtifactType.ARTIFACT_INDEX,
    )
    latest_work_plan = _latest_artifact_with_workflow(
        artifacts,
        "run_work_plan_v1",
    )
    latest_sync_pulse = _latest_artifact_with_workflow(
        artifacts,
        "run_sync_pulse_v1",
    )
    source_evidence = _source_evidence_digest(sources, claims, artifacts)
    latest_event = max(
        (event.event_id for event in events if event.event_id is not None),
        default=None,
    )
    digest = {
        "latest_event_id": latest_event,
        "latest_event_type": events[-1].event_type if events else None,
        "events": len(events),
        "conversation_turns": len(turns),
        "voice_conversation_turns": sum(1 for turn in turns if turn.modality == "voice"),
        "realtime_sessions": len(realtime_sessions),
        "agent_messages": len(messages),
        "pending_agent_messages": len(pending_messages),
        "dependency_cycle_agent_tasks": len(dependency_cycle_message_ids),
        "message_status_counts": dict(message_status_counts),
        "sources": len(sources),
        "source_evidence": source_evidence,
        "source_evidence_items": len(source_evidence),
        "source_evidence_with_snippets": sum(
            1 for item in source_evidence if item.get("snippet")
        ),
        "source_evidence_with_published_dates": sum(
            1 for item in source_evidence if item.get("published_at")
        ),
        "accepted_retrieval_evidence_items": sum(
            1 for item in source_evidence if item.get("accepted_for_context")
        ),
        "source_evidence_missing_snippets": sum(
            1 for item in source_evidence if not item.get("snippet")
        ),
        "source_evidence_missing_published_dates": sum(
            1 for item in source_evidence if not item.get("published_at")
        ),
        "latest_web_research": _latest_web_research_digest(events),
        "claims": len(claims),
        "artifacts": len(artifacts),
        "artifact_type_counts": dict(artifact_type_counts),
        "realtime_dialogue_ledger": _ledger_digest(latest_realtime_ledger),
        "feedback_resolution_ledger": _ledger_digest(latest_feedback_ledger),
        "retrieval_quality": _ledger_digest(latest_retrieval_ledger),
        "publishing_handoff": _publishing_handoff_digest(latest_artifact_index),
        "foundation_audit": _foundation_audit_digest(latest_foundation_audit),
        "work_plan": _work_plan_digest(latest_work_plan),
        "sync_pulse": _sync_pulse_digest(latest_sync_pulse),
        "guardrail_audits": len(audits),
        "audit_status_counts": dict(audit_status_counts),
        "feedback_items": len(feedback_items),
        "open_feedback_items": len(open_feedback_items),
        "feedback_status_counts": dict(feedback_status_counts),
        "worker_profiles": len(worker_profiles),
        "active_worker_profiles": len(active_profiles),
    }
    return _ResumeState(
        latest_event_id=latest_event,
        pending_agent_messages=pending_messages,
        dependency_cycle_message_ids=dependency_cycle_message_ids,
        open_feedback_items=open_feedback_items,
        active_worker_profiles=active_profiles,
        digest=digest,
    )


def _resume_cycle_agent_ids(
    pending_messages: list[AgentMessage],
    work_plan,
) -> list[str]:
    if work_plan is not None and work_plan.recommended_agent_ids:
        return work_plan.recommended_agent_ids
    agent_ids = []
    runnable_statuses = {AgentTaskStatus.ACCEPTED, AgentTaskStatus.CLAIMED}
    for message in pending_messages:
        if message.status not in runnable_statuses:
            continue
        if message.recipient_agent_id not in agent_ids:
            agent_ids.append(message.recipient_agent_id)
    return agent_ids


def _blocked_reasons(run_status: RunStatus, state: _ResumeState) -> list[str]:
    reasons = []
    if run_status == RunStatus.WAITING_FOR_HUMAN:
        reasons.append("waiting_for_human")
    if run_status == RunStatus.FAILED:
        reasons.append("run_failed")
    if run_status == RunStatus.CANCELED:
        reasons.append("run_canceled")
    if run_status == RunStatus.COMPLETED and not _has_resume_work(state):
        reasons.append("run_completed")
    if state.open_feedback_items:
        reasons.append("open_human_feedback")
    if any(_retry_exhausted(message) for message in state.pending_agent_messages):
        reasons.append("retry_exhausted_agent_tasks")
    if state.dependency_cycle_message_ids:
        reasons.append("dependency_cycle_agent_tasks")
    if any(
        message.status in {AgentTaskStatus.WAITING_FOR_HUMAN, AgentTaskStatus.BLOCKED}
        and not _retry_exhausted(message)
        for message in state.pending_agent_messages
    ):
        reasons.append("blocked_agent_tasks")
    return reasons


def _recommended_next_actions(run_status: RunStatus, state: _ResumeState) -> list[str]:
    actions = []
    if run_status == RunStatus.WAITING_FOR_HUMAN:
        actions.append("Resolve the human gate before autonomous work continues.")
    if run_status == RunStatus.FAILED:
        actions.append("Inspect the latest failure event before retrying the run.")
    if run_status == RunStatus.CANCELED:
        actions.append("Create a new run or explicitly reopen the canceled work.")
    if run_status == RunStatus.COMPLETED and not _has_resume_work(state):
        actions.append("Start a new revision request if more work is needed.")
    if state.open_feedback_items:
        actions.append("Resolve open feedback gates before autonomous work continues.")
    retry_exhausted_messages = [
        message for message in state.pending_agent_messages if _retry_exhausted(message)
    ]
    if retry_exhausted_messages:
        actions.append(
            "Authorize retry for exhausted A2A task(s) before resume: "
            + ", ".join(str(message.message_id) for message in retry_exhausted_messages)
            + "."
        )
    if state.dependency_cycle_message_ids:
        actions.append(
            "Break circular A2A dependencies before resume: "
            + ", ".join(
                str(message_id)
                for message_id in sorted(state.dependency_cycle_message_ids, key=str)
            )
            + "."
        )
    if any(
        message.status in {AgentTaskStatus.WAITING_FOR_HUMAN, AgentTaskStatus.BLOCKED}
        and not _retry_exhausted(message)
        for message in state.pending_agent_messages
    ):
        actions.append("Route blocked agent tasks to the forward deployed engineer.")
    runnable_agents = sorted(
        {
            message.recipient_agent_id
            for message in state.pending_agent_messages
            if message.message_id not in state.dependency_cycle_message_ids
            if message.status in {AgentTaskStatus.ACCEPTED, AgentTaskStatus.CLAIMED}
        }
    )
    if runnable_agents:
        actions.append(
            "Run worker cycle for pending agents: " + ", ".join(runnable_agents) + "."
        )
    if state.active_worker_profiles:
        actions.append("Heartbeat active worker profiles or run the profile scheduler.")
    if state.digest["artifacts"] and not state.digest["guardrail_audits"]:
        actions.append("Run guardrail audit before publishing checks.")
    if state.digest["artifacts"] and not state.open_feedback_items:
        actions.append("Run publishing readiness before using generated artifacts.")
    realtime_ledger = state.digest.get("realtime_dialogue_ledger")
    if realtime_ledger is None and (
        state.digest.get("realtime_sessions", 0)
        or state.digest.get("voice_conversation_turns", 0)
    ):
        actions.append(
            "Build the realtime dialogue ledger before resuming voice-led work."
        )
    elif realtime_ledger is not None and realtime_ledger.get("status") not in {
        None,
        "ready",
    }:
        if realtime_ledger.get("unresolved_control_event_ids"):
            actions.append(
                "Resolve realtime control events before resuming voice-led work."
            )
        else:
            actions.append(
                "Review the realtime dialogue ledger before resuming voice-led work."
            )
    feedback_ledger = state.digest.get("feedback_resolution_ledger")
    if feedback_ledger is None and state.digest.get("feedback_items", 0):
        actions.append(
            "Build the feedback resolution ledger before clearing human-feedback work."
        )
    elif feedback_ledger is not None and feedback_ledger.get("status") not in {
        None,
        "ready",
    }:
        actions.append(
            "Review the feedback resolution ledger before clearing human-feedback work."
        )
    publishing_handoff = state.digest.get("publishing_handoff")
    publishable_artifact_count = _publishable_artifact_count(
        state.digest.get("artifact_type_counts", {})
    )
    retrieval_quality = state.digest.get("retrieval_quality")
    if retrieval_quality is None and (
        state.digest.get("sources", 0)
        or state.digest.get("claims", 0)
        or publishable_artifact_count
    ):
        actions.append(
            "Build the retrieval quality ledger before source-backed synthesis resumes."
        )
    elif retrieval_quality is not None and retrieval_quality.get("status") not in {
        None,
        "ready",
    }:
        actions.append(
            "Review retrieval precision, recall, reranking, and graph coverage before final synthesis."
        )
    if publishing_handoff is None and publishable_artifact_count:
        actions.append(
            "Build the Artifact Librarian publishing handoff before final content resume."
        )
    elif publishing_handoff is not None and publishing_handoff.get("status") not in {
        "ready",
        "ready_for_publish_readiness",
    }:
        actions.append(
            "Review the latest publishing handoff before final editor or publish-readiness work."
        )
    if publishable_artifact_count and (
        state.digest.get("source_evidence_missing_snippets", 0)
        or state.digest.get("source_evidence_missing_published_dates", 0)
        or state.digest.get("latest_web_research") is None
    ):
        actions.append(
            "Refresh provider-backed web research/source evidence before final content resume."
        )
    foundation_audit = state.digest.get("foundation_audit")
    if foundation_audit is not None and foundation_audit.get("remediation_count", 0):
        work_plan = state.digest.get("work_plan")
        if work_plan is not None and work_plan.get(
            "foundation_audit_remediation_count",
            0,
        ):
            owners = work_plan.get("recommended_agent_ids", [])
            actions.append(
                "Continue refreshed foundation-audit remediation work plan"
                + (": " + ", ".join(owners) if owners else ".")
            )
        else:
            actions.append(
                "Run the Sprint/Progress work plan to route foundation audit remediation."
            )
    if not actions:
        actions.append("Record a conversation turn or create the next A2A task.")
    return actions


def _source_evidence_digest(
    sources,
    claims,
    artifacts,
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    claim_ids_by_source_id: dict[UUID, list[str]] = {}
    for claim in claims:
        for source_id in claim.source_ids:
            claim_ids_by_source_id.setdefault(source_id, []).append(str(claim.claim_id))

    artifact_ids_by_source_id: dict[UUID, list[str]] = {}
    for artifact in artifacts:
        for source_id in artifact.source_ids:
            artifact_ids_by_source_id.setdefault(source_id, []).append(
                str(artifact.artifact_id)
            )

    ordered_sources, evidence_by_source_id, _ = order_sources_by_retrieval_evidence(
        sources,
        artifacts,
    )
    evidence = []
    for source in ordered_sources[:limit]:
        metadata = source.metadata or {}
        quality = evaluate_source_quality(source)
        retrieval_evidence = evidence_by_source_id.get(source.source_id)
        evidence.append(
            {
                "source_id": str(source.source_id),
                "citation_id": source.citation_id,
                "title": source.title,
                "url": str(source.url),
                "publisher": source.publisher,
                "source_type": str(metadata.get("source_type") or "manual_source"),
                "snippet": metadata.get("snippet"),
                "search_query": metadata.get("search_query"),
                "search_rank": metadata.get("search_rank"),
                "published_at": _source_published_at(source),
                "retrieved_at": source.retrieved_at.isoformat(),
                "quality_status": quality.quality_status.value,
                "freshness_status": quality.freshness_status.value,
                "quality_flags": quality.flags,
                "claim_ids": claim_ids_by_source_id.get(source.source_id, []),
                "artifact_ids": artifact_ids_by_source_id.get(source.source_id, []),
                "accepted_for_context": retrieval_evidence is not None,
                "retrieval_rank": (
                    retrieval_evidence.fused_rank if retrieval_evidence else None
                ),
                "retrieval_rerank_score": (
                    retrieval_evidence.rerank_score if retrieval_evidence else None
                ),
                "retrieval_reranker": (
                    retrieval_evidence.reranker if retrieval_evidence else None
                ),
                "retrieval_rerank_reason": (
                    retrieval_evidence.rerank_reason if retrieval_evidence else None
                ),
                "retrieval_precision_risks": (
                    list(retrieval_evidence.precision_risks)
                    if retrieval_evidence
                    else []
                ),
                "retrieval_recall_risks": (
                    list(retrieval_evidence.recall_risks)
                    if retrieval_evidence
                    else []
                ),
                "retrieval_coverage_topics": (
                    list(retrieval_evidence.coverage_topics)
                    if retrieval_evidence
                    else []
                ),
            }
        )
    return evidence


def _source_published_at(source) -> str | None:
    if source.published_at:
        return source.published_at.isoformat()
    published_at = (source.metadata or {}).get("published_at")
    return str(published_at) if published_at else None


def _latest_web_research_digest(events: list[RunEvent]) -> dict[str, Any] | None:
    for event in reversed(events):
        if event.event_type != "web_research_completed":
            continue
        payload = event.payload or {}
        return {
            "event_id": event.event_id,
            "query": payload.get("query"),
            "freshness": payload.get("freshness"),
            "provider_result_count": payload.get("provider_result_count"),
            "accepted_source_count": payload.get("accepted_source_count"),
            "deduplicated_result_count": payload.get("deduplicated_result_count"),
            "citation_ids": payload.get("citation_ids", []),
        }
    return None


def _latest_artifact_of_type(
    artifacts: list[ArtifactRecord],
    artifact_type: ArtifactType,
) -> ArtifactRecord | None:
    for artifact in reversed(artifacts):
        if artifact.artifact_type == artifact_type:
            return artifact
    return None


def _latest_artifact_with_workflow(
    artifacts: list[ArtifactRecord],
    workflow: str,
) -> ArtifactRecord | None:
    for artifact in reversed(artifacts):
        if artifact.provenance.get("workflow") == workflow:
            return artifact
    return None


def _ledger_digest(artifact: ArtifactRecord | None) -> dict | None:
    if artifact is None:
        return None
    digest = {
        "artifact_id": str(artifact.artifact_id),
        "artifact_type": artifact.artifact_type.value,
        "status": artifact.content.get("status"),
        "summary": artifact.content.get("summary"),
        "recommended_next_actions": artifact.content.get(
            "recommended_next_actions",
            [],
        ),
    }
    for key in [
        "session_count",
        "turn_count",
        "voice_turn_count",
        "interrupted_turn_count",
        "pending_followup_task_ids",
        "unacknowledged_interruption_turn_ids",
        "unanswered_user_turn_ids",
        "control_event_count",
        "unresolved_control_event_ids",
        "control_action_counts",
        "feedback_count",
        "open_feedback_count",
        "routed_feedback_count",
        "resolved_feedback_count",
        "pending_linked_task_count",
        "blocked_linked_task_count",
        "candidate_count",
        "accepted_candidate_count",
        "reranked_candidate_count",
        "graph_node_count",
        "precision_risk_count",
        "recall_gap_count",
        "coverage_gap_count",
        "recommended_queries",
    ]:
        if key not in artifact.content:
            continue
        value = artifact.content[key]
        digest[key] = len(value) if isinstance(value, list) else value
    return digest


def _publishing_handoff_digest(artifact: ArtifactRecord | None) -> dict | None:
    if artifact is None:
        return None
    handoff = artifact.content.get("publishing_handoff")
    if not isinstance(handoff, dict):
        return None
    guardrail = handoff.get("guardrail")
    if not isinstance(guardrail, dict):
        guardrail = {}
    feedback_gates = handoff.get("feedback_gates")
    if not isinstance(feedback_gates, dict):
        feedback_gates = {}
    source_ledger = handoff.get("source_ledger")
    if not isinstance(source_ledger, dict):
        source_ledger = {}
    claim_revision = handoff.get("claim_revision")
    if not isinstance(claim_revision, dict):
        claim_revision = {}
    latest_publish_readiness = handoff.get("latest_publish_readiness")
    if not isinstance(latest_publish_readiness, dict):
        latest_publish_readiness = None
    recommended_next_actions = handoff.get("recommended_next_actions", [])
    if not isinstance(recommended_next_actions, list):
        recommended_next_actions = []
    return {
        "artifact_id": str(artifact.artifact_id),
        "artifact_type": artifact.artifact_type.value,
        "status": handoff.get("status"),
        "publishable_artifact_count": handoff.get("publishable_artifact_count", 0),
        "source_draft_count": handoff.get("source_draft_count", 0),
        "distribution_package_count": handoff.get("distribution_package_count", 0),
        "media_artifact_count": handoff.get("media_artifact_count", 0),
        "source_dependency_count": handoff.get("source_dependency_count", 0),
        "claim_dependency_count": handoff.get("claim_dependency_count", 0),
        "unsupported_claim_count": _list_count(handoff, "unsupported_claim_ids"),
        "needs_review_claim_count": _list_count(handoff, "needs_review_claim_ids"),
        "missing_source_count": _list_count(handoff, "missing_source_ids"),
        "claim_revision_status": claim_revision.get("status"),
        "claim_revision_open_held_claim_count": claim_revision.get(
            "open_held_claim_count",
            0,
        ),
        "claim_revision_pending_followup_count": claim_revision.get(
            "pending_followup_count",
            0,
        ),
        "claim_revision_blocked_followup_count": claim_revision.get(
            "blocked_followup_count",
            0,
        ),
        "claim_revision_revised_artifact_count": claim_revision.get(
            "revised_artifact_count",
            0,
        ),
        "source_ledger_artifact_count": _list_count(source_ledger, "artifact_ids"),
        "source_ledger_snapshot_event_count": _list_count(
            source_ledger,
            "snapshot_event_ids",
        ),
        "guardrail_audit_count": guardrail.get("audit_count", 0),
        "missing_guardrail_artifact_count": _list_count(
            guardrail,
            "missing_guardrail_artifact_ids",
        ),
        "non_approved_audit_count": _list_count(
            guardrail,
            "non_approved_audit_ids",
        ),
        "open_feedback_count": feedback_gates.get("open_or_routed_count", 0),
        "latest_publish_readiness_status": (
            latest_publish_readiness.get("status")
            if latest_publish_readiness
            else None
        ),
        "latest_publish_readiness_event_id": (
            latest_publish_readiness.get("event_id")
            if latest_publish_readiness
            else None
        ),
        "recommended_next_actions": recommended_next_actions,
    }


def _list_count(payload: dict, key: str) -> int:
    value = payload.get(key, [])
    return len(value) if isinstance(value, list) else 0


def _publishable_artifact_count(artifact_type_counts: dict) -> int:
    return sum(
        int(artifact_type_counts.get(artifact_type.value, 0) or 0)
        for artifact_type in {
            ArtifactType.POST,
            ArtifactType.REEL_SCRIPT,
            ArtifactType.SUBSTACK_ARTICLE,
            ArtifactType.SOCIAL_PACKAGE,
        }
    )


def _work_plan_digest(artifact: ArtifactRecord | None) -> dict | None:
    if artifact is None:
        return None
    plan_items = artifact.content.get("plan_items", [])
    if not isinstance(plan_items, list):
        plan_items = []
    remediation_items = [
        item
        for item in plan_items
        if isinstance(item, dict)
        and item.get("item_type") == "foundation_audit_remediation"
    ]
    created_task_ids = artifact.content.get("created_task_message_ids", [])
    if not isinstance(created_task_ids, list):
        created_task_ids = []
    recommended_agent_ids = artifact.content.get("recommended_agent_ids", [])
    if not isinstance(recommended_agent_ids, list):
        recommended_agent_ids = []
    return {
        "artifact_id": str(artifact.artifact_id),
        "refresh_reason": artifact.content.get("refresh_reason")
        or artifact.provenance.get("refresh_reason"),
        "plan_item_count": len(plan_items),
        "foundation_audit_remediation_count": len(remediation_items),
        "blocked_item_count": artifact.content.get("blocked_item_count", 0),
        "pending_task_count": artifact.content.get("pending_task_count", 0),
        "created_task_count": len(created_task_ids),
        "recommended_agent_ids": recommended_agent_ids,
    }


def _sync_pulse_digest(artifact: ArtifactRecord | None) -> dict | None:
    if artifact is None:
        return None
    blockers = artifact.content.get("blockers", [])
    if not isinstance(blockers, list):
        blockers = []
    recommended_agent_ids = artifact.content.get("recommended_agent_ids", [])
    if not isinstance(recommended_agent_ids, list):
        recommended_agent_ids = []
    agent_states = artifact.content.get("agent_states", [])
    if not isinstance(agent_states, list):
        agent_states = []
    work_plan = artifact.content.get("work_plan") or {}
    if not isinstance(work_plan, dict):
        work_plan = {}
    return {
        "artifact_id": str(artifact.artifact_id),
        "refresh_reason": artifact.content.get("refresh_reason")
        or artifact.provenance.get("refresh_reason"),
        "blocker_count": len(blockers),
        "agent_count": len(agent_states),
        "recommended_agent_ids": recommended_agent_ids,
        "work_plan_refresh_reason": work_plan.get("refresh_reason"),
        "work_plan_item_count": len(work_plan.get("plan_items", []))
        if isinstance(work_plan.get("plan_items"), list)
        else 0,
    }


def _foundation_audit_digest(artifact: ArtifactRecord | None) -> dict | None:
    if artifact is None:
        return None
    remediation_items = _foundation_audit_remediation_items(artifact)
    return {
        "artifact_id": str(artifact.artifact_id),
        "status": artifact.content.get("status"),
        "check_count": artifact.content.get("check_count"),
        "completion_score": artifact.content.get("completion_score"),
        "remediation_count": _foundation_audit_remediation_count(
            artifact,
            remediation_items,
        ),
        "blocking_remediation_count": _foundation_audit_blocking_count(
            artifact,
            remediation_items,
        ),
        "owner_agent_ids": _foundation_audit_owner_agent_ids(remediation_items),
    }


def _foundation_audit_remediation_items(
    artifact: ArtifactRecord,
) -> list[dict]:
    items = artifact.content.get("remediation_items", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _foundation_audit_remediation_count(
    artifact: ArtifactRecord,
    remediation_items: list[dict],
) -> int:
    value = artifact.content.get("remediation_count")
    if isinstance(value, int):
        return value
    if remediation_items:
        return len(remediation_items)
    checks = artifact.content.get("checks", [])
    if not isinstance(checks, list):
        return 0
    return sum(
        1
        for check in checks
        if isinstance(check, dict) and check.get("status") != "pass"
    )


def _foundation_audit_blocking_count(
    artifact: ArtifactRecord,
    remediation_items: list[dict],
) -> int:
    value = artifact.content.get("blocking_remediation_count")
    if isinstance(value, int):
        return value
    return sum(1 for item in remediation_items if item.get("blocking"))


def _foundation_audit_owner_agent_ids(remediation_items: list[dict]) -> list[str]:
    owner_ids = []
    for item in remediation_items:
        owner = item.get("owner_agent_id")
        if isinstance(owner, str) and owner and owner not in owner_ids:
            owner_ids.append(owner)
    return owner_ids


def _retry_exhausted(message: AgentMessage) -> bool:
    retry_policy = message.result.get("retry_policy", {})
    retry_policy_attempts = retry_policy.get("attempt_count", message.attempt_count)
    retry_policy_max_attempts = retry_policy.get("max_attempts", message.max_attempts)
    return (
        message.status == AgentTaskStatus.BLOCKED
        and retry_policy_attempts >= retry_policy_max_attempts
    )


def _dependency_cycle_message_ids(
    messages: list[AgentMessage],
    messages_by_id: dict[UUID, AgentMessage],
) -> set[UUID]:
    active_message_ids = {
        message.message_id
        for message in messages
        if message.status != AgentTaskStatus.COMPLETED
    }
    adjacency = {
        message.message_id: [
            dependency_id
            for dependency_id in message.depends_on_message_ids
            if dependency_id in messages_by_id
            and dependency_id in active_message_ids
        ]
        for message in messages
        if message.message_id in active_message_ids
    }
    cycle_message_ids: set[UUID] = set()

    def visit(node_id: UUID, path: list[UUID]) -> None:
        if node_id in path:
            cycle_message_ids.update(path[path.index(node_id) :])
            return
        for dependency_id in adjacency.get(node_id, []):
            visit(dependency_id, [*path, node_id])

    for message_id in adjacency:
        visit(message_id, [])
    return cycle_message_ids


def _has_resume_work(state: _ResumeState) -> bool:
    return bool(state.active_worker_profiles) or any(
        message.status
        in {
            AgentTaskStatus.ACCEPTED,
            AgentTaskStatus.CLAIMED,
            AgentTaskStatus.IN_PROGRESS,
        }
        for message in state.pending_agent_messages
    )


def _resume_summary(
    *,
    resume_allowed: bool,
    blocked_reasons: list[str],
    pending_count: int,
    open_feedback_count: int,
    active_profile_count: int,
) -> str:
    if resume_allowed:
        return (
            "Run can resume with "
            f"{pending_count} pending task(s) and {active_profile_count} "
            "active worker profile(s)."
        )
    return (
        "Run is not ready for autonomous resume: "
        f"{', '.join(blocked_reasons)}. "
        f"{open_feedback_count} open feedback item(s), "
        f"{pending_count} pending task(s), "
        f"{active_profile_count} active worker profile(s)."
    )
