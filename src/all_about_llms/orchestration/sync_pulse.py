from collections import Counter
from uuid import UUID

from all_about_llms.agents import get_agent_card
from all_about_llms.contracts import (
    AgentMessage,
    AgentSyncState,
    AgentTaskStatus,
    ArtifactRecord,
    ArtifactType,
    FeedbackItem,
    FeedbackStatus,
    RunEvent,
    RunSyncPulseRequest,
    RunSyncPulseResult,
    RunWorkPlanRequest,
    WorkerProfile,
    WorkerProfileStatus,
)
from all_about_llms.orchestration.work_plan import RunWorkPlanWorkflow


class RunSyncPulseError(RuntimeError):
    """Base error for multi-agent sync pulse generation."""


class RunSyncPulseRunNotFoundError(RunSyncPulseError):
    """Raised when a sync pulse references a missing run."""


ACTIVE_TASK_STATUSES = {
    AgentTaskStatus.ACCEPTED,
    AgentTaskStatus.CLAIMED,
    AgentTaskStatus.IN_PROGRESS,
    AgentTaskStatus.WAITING_FOR_HUMAN,
    AgentTaskStatus.BLOCKED,
}

CLAIM_REVISION_BLOCKING_STATUSES = {
    "blocked",
    "no_followups_created",
    "followups_pending",
    "awaiting_revised_artifacts",
    "needs_claim_reverification",
    "needs_editor_review",
    "in_progress",
}


class RunSyncPulseWorkflow:
    """Create a durable collaboration pulse for manager/scrum/agent handoffs."""

    def __init__(self, store):
        self._store = store

    async def build(
        self,
        run_id: UUID,
        request: RunSyncPulseRequest,
    ) -> RunSyncPulseResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise RunSyncPulseRunNotFoundError(f"Run not found: {run_id}")

        messages = await self._store.list_agent_messages(run_id)
        feedback_items = await self._store.list_feedback(run_id)
        artifacts = await self._store.list_artifacts(run_id)
        claims = await self._store.list_claims(run_id)
        audits = await self._store.list_guardrail_audits(run_id)
        sources = await self._store.list_sources(run_id)
        worker_profiles = await self._store.list_worker_profiles(run_id)
        events = await self._store.list_events(run_id, limit=1000)
        claim_revision = _latest_claim_revision_ledger_summary(artifacts)

        work_plan = None
        if request.build_work_plan:
            work_plan = await RunWorkPlanWorkflow(self._store).build(
                run_id,
                RunWorkPlanRequest(
                    record_artifact=False,
                    include_completed_tasks=request.include_completed_tasks,
                    create_followup_tasks=request.create_followup_tasks,
                    max_items=request.max_work_items,
                    refresh_reason=request.refresh_reason,
                ),
            )

        agent_ids = _sync_agent_ids(
            run_active_agents=run.active_agents,
            messages=messages,
            feedback_items=feedback_items,
            worker_profiles=worker_profiles,
            work_plan_recommended_agent_ids=(
                work_plan.recommended_agent_ids if work_plan else []
            ),
            include_all_active_agents=request.include_all_active_agents,
        )
        messages_by_id = {message.message_id: message for message in messages}
        dependency_cycle_message_ids = _dependency_cycle_message_ids(
            messages,
            messages_by_id,
        )
        agent_states = [
            _agent_sync_state(
                agent_id=agent_id,
                messages=messages,
                messages_by_id=messages_by_id,
                dependency_cycle_message_ids=dependency_cycle_message_ids,
                feedback_items=feedback_items,
                worker_profiles=worker_profiles,
            )
            for agent_id in agent_ids
        ]
        blockers = _blockers(
            feedback_items=feedback_items,
            messages=messages,
            dependency_cycle_message_ids=dependency_cycle_message_ids,
            work_plan_blocked_count=work_plan.blocked_item_count if work_plan else 0,
            claim_revision=claim_revision,
        )
        recommended_agent_ids = _recommended_agent_ids(agent_states, work_plan)
        latest_event_id = max(
            (event.event_id for event in events if event.event_id is not None),
            default=None,
        )
        summary_snapshot = {
            "run_status": run.status.value,
            "latest_event_id": latest_event_id,
            "agent_count": len(agent_states),
            "message_count": len(messages),
            "active_task_count": sum(
                1 for message in messages if message.status in ACTIVE_TASK_STATUSES
            ),
            "open_feedback_count": sum(
                1 for feedback in feedback_items if feedback.status == FeedbackStatus.OPEN
            ),
            "routed_feedback_count": sum(
                1
                for feedback in feedback_items
                if feedback.status == FeedbackStatus.ROUTED
            ),
            "artifact_count": len(artifacts),
            "claim_count": len(claims),
            "source_count": len(sources),
            "audit_count": len(audits),
            "active_worker_profile_count": sum(
                1
                for profile in worker_profiles
                if profile.status == WorkerProfileStatus.ACTIVE
            ),
            "work_plan_item_count": len(work_plan.plan_items) if work_plan else 0,
            "dependency_cycle_message_count": len(dependency_cycle_message_ids),
            "claim_revision": claim_revision,
            "notes": request.notes,
            "refresh_reason": request.refresh_reason,
        }

        artifact_id = None
        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.SYSTEM_PLAN,
                title="Multi-agent sync pulse",
                uri="",
                content={
                    "summary": summary_snapshot,
                    "agent_states": [
                        state.model_dump(mode="json") for state in agent_states
                    ],
                    "blockers": blockers,
                    "recommended_agent_ids": recommended_agent_ids,
                    "work_plan": (
                        work_plan.model_dump(mode="json") if work_plan else None
                    ),
                    "refresh_reason": request.refresh_reason,
                },
                provenance={
                    "workflow": "run_sync_pulse_v1",
                    "created_by": "product-manager",
                    "refresh_reason": request.refresh_reason,
                    "collaborators": [
                        "sprint-progress-agent",
                        "agent-harness-engineer",
                        "forward-deployed-engineer",
                    ],
                    "latest_event_id": latest_event_id,
                    "source_message_ids": [
                        str(message.message_id) for message in messages
                    ],
                    "source_feedback_ids": [
                        str(feedback.feedback_id) for feedback in feedback_items
                    ],
                    "work_plan_artifact_id": (
                        str(work_plan.artifact_id)
                        if work_plan and work_plan.artifact_id
                        else None
                    ),
                },
            )
            artifact.uri = f"artifact://runs/{run_id}/sync-pulses/{artifact.artifact_id}"
            await self._store.record_artifact(artifact)
            artifact_id = artifact.artifact_id

        event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="multi_agent_sync_pulse_recorded",
                actor="product-manager",
                payload={
                    "artifact_id": str(artifact_id) if artifact_id else None,
                    "agent_count": len(agent_states),
                    "blockers": blockers,
                    "recommended_agent_ids": recommended_agent_ids,
                    "work_plan_event_id": work_plan.event_id if work_plan else None,
                    "work_plan_item_count": len(work_plan.plan_items)
                    if work_plan
                    else 0,
                    "refresh_reason": request.refresh_reason,
                    "summary": summary_snapshot,
                },
            )
        )

        return RunSyncPulseResult(
            run_id=run_id,
            agent_states=agent_states,
            work_plan=work_plan,
            blockers=blockers,
            recommended_agent_ids=recommended_agent_ids,
            artifact_id=artifact_id,
            event_id=event.event_id,
            refresh_reason=request.refresh_reason,
            summary=_summary(agent_states, blockers, work_plan),
        )


def _sync_agent_ids(
    *,
    run_active_agents: list[str],
    messages: list[AgentMessage],
    feedback_items: list[FeedbackItem],
    worker_profiles: list[WorkerProfile],
    work_plan_recommended_agent_ids: list[str],
    include_all_active_agents: bool,
) -> list[str]:
    agent_ids = [
        "product-manager",
        "sprint-progress-agent",
        "agent-harness-engineer",
        "forward-deployed-engineer",
    ]
    candidates = []
    if include_all_active_agents:
        candidates.extend(run_active_agents)
    for message in messages:
        candidates.extend([message.sender_agent_id, message.recipient_agent_id])
    candidates.extend(
        feedback.target_agent_id
        for feedback in feedback_items
        if feedback.target_agent_id
    )
    for profile in worker_profiles:
        candidates.extend(profile.agent_ids)
    candidates.extend(work_plan_recommended_agent_ids)

    for agent_id in candidates:
        if agent_id and agent_id not in agent_ids:
            agent_ids.append(agent_id)
    return agent_ids


def _agent_sync_state(
    *,
    agent_id: str,
    messages: list[AgentMessage],
    messages_by_id: dict[UUID, AgentMessage],
    dependency_cycle_message_ids: set[UUID],
    feedback_items: list[FeedbackItem],
    worker_profiles: list[WorkerProfile],
) -> AgentSyncState:
    card = get_agent_card(agent_id)
    related_messages = [
        message
        for message in messages
        if message.sender_agent_id == agent_id or message.recipient_agent_id == agent_id
    ]
    inbox_messages = [
        message for message in messages if message.recipient_agent_id == agent_id
    ]
    pending_messages = [
        message for message in inbox_messages if message.status in ACTIVE_TASK_STATUSES
    ]
    blocked_messages = [
        message
        for message in inbox_messages
        if message.status
        in {AgentTaskStatus.WAITING_FOR_HUMAN, AgentTaskStatus.BLOCKED}
    ]
    dependency_waiting_messages = [
        message
        for message in pending_messages
        if message.status == AgentTaskStatus.ACCEPTED
        and _unmet_dependency_message_ids(message, messages_by_id)
    ]
    dependency_cycle_messages = [
        message
        for message in pending_messages
        if message.message_id in dependency_cycle_message_ids
    ]
    routed_feedback = [
        feedback
        for feedback in feedback_items
        if feedback.target_agent_id == agent_id
        and feedback.status in {FeedbackStatus.OPEN, FeedbackStatus.ROUTED}
    ]
    active_profiles = [
        profile
        for profile in worker_profiles
        if profile.status == WorkerProfileStatus.ACTIVE and agent_id in profile.agent_ids
    ]
    task_counts = Counter(message.status.value for message in related_messages)
    return AgentSyncState(
        agent_id=agent_id,
        name=card.name if card else None,
        role=card.role if card else None,
        task_counts=dict(task_counts),
        pending_message_ids=[message.message_id for message in pending_messages],
        blocked_message_ids=[message.message_id for message in blocked_messages],
        routed_feedback_ids=[feedback.feedback_id for feedback in routed_feedback],
        active_profile_ids=[profile.profile_id for profile in active_profiles],
        current_focus=_current_focus(
            pending_messages=pending_messages,
            blocked_messages=blocked_messages,
            dependency_cycle_messages=dependency_cycle_messages,
            dependency_waiting_messages=dependency_waiting_messages,
            routed_feedback=routed_feedback,
            active_profiles=active_profiles,
        ),
        recommended_next_action=_recommended_action(
            agent_id=agent_id,
            pending_messages=pending_messages,
            blocked_messages=blocked_messages,
            dependency_cycle_messages=dependency_cycle_messages,
            dependency_waiting_messages=dependency_waiting_messages,
            routed_feedback=routed_feedback,
            active_profiles=active_profiles,
        ),
    )


def _current_focus(
    *,
    pending_messages: list[AgentMessage],
    blocked_messages: list[AgentMessage],
    dependency_cycle_messages: list[AgentMessage],
    dependency_waiting_messages: list[AgentMessage],
    routed_feedback: list[FeedbackItem],
    active_profiles: list[WorkerProfile],
) -> str:
    if any(_retry_exhausted(message) for message in blocked_messages):
        return "retry_authorization"
    if blocked_messages:
        return "blocked_task_resolution"
    if dependency_cycle_messages:
        return "dependency_cycle"
    if dependency_waiting_messages:
        return "dependency_waiting"
    if routed_feedback:
        return "human_feedback"
    if pending_messages:
        return "pending_a2a_work"
    if active_profiles:
        return "always_on_profile_ready"
    return "standby"


def _recommended_action(
    *,
    agent_id: str,
    pending_messages: list[AgentMessage],
    blocked_messages: list[AgentMessage],
    dependency_cycle_messages: list[AgentMessage],
    dependency_waiting_messages: list[AgentMessage],
    routed_feedback: list[FeedbackItem],
    active_profiles: list[WorkerProfile],
) -> str:
    if blocked_messages:
        if any(_retry_exhausted(message) for message in blocked_messages):
            return (
                "Review exhausted retry task and authorize retry from the cockpit "
                f"or retry endpoint for {agent_id}."
            )
        return f"Forward-deployed engineer should unblock {agent_id}."
    if dependency_cycle_messages:
        return (
            f"Ask Agent Harness Engineer to break circular A2A dependencies before "
            f"running {agent_id}."
        )
    if dependency_waiting_messages:
        return (
            f"Wait for upstream A2A dependencies before running {agent_id}, "
            "or repair failed upstream tasks."
        )
    if routed_feedback:
        return f"Route feedback into the next {agent_id} worker pass."
    if pending_messages:
        return f"Run worker for {agent_id}."
    if active_profiles:
        return f"Heartbeat active worker profile for {agent_id}."
    if agent_id == "product-manager":
        return "Review blocker list and approve the next autonomous pass."
    if agent_id == "sprint-progress-agent":
        return "Keep the sync pulse and work plan current."
    return "No immediate action."


def _blockers(
    *,
    feedback_items: list[FeedbackItem],
    messages: list[AgentMessage],
    dependency_cycle_message_ids: set[UUID],
    work_plan_blocked_count: int,
    claim_revision: dict[str, object] | None,
) -> list[str]:
    blockers = []
    open_feedback = [
        feedback for feedback in feedback_items if feedback.status == FeedbackStatus.OPEN
    ]
    if open_feedback:
        blockers.append(f"{len(open_feedback)} open human feedback item(s).")
    blocked_messages = [
        message
        for message in messages
        if message.status in {AgentTaskStatus.WAITING_FOR_HUMAN, AgentTaskStatus.BLOCKED}
    ]
    if blocked_messages:
        retry_exhausted_count = sum(
            1 for message in blocked_messages if _retry_exhausted(message)
        )
        if retry_exhausted_count:
            blockers.append(
                f"{retry_exhausted_count} retry-exhausted A2A task(s) need "
                "human-authorized retry."
            )
        remaining_blocked_count = len(blocked_messages) - retry_exhausted_count
        if remaining_blocked_count:
            blockers.append(
                f"{remaining_blocked_count} blocked or waiting A2A task(s)."
            )
    messages_by_id = {message.message_id: message for message in messages}
    dependency_waiting_count = sum(
        1
        for message in messages
        if message.status == AgentTaskStatus.ACCEPTED
        and _unmet_dependency_message_ids(message, messages_by_id)
    )
    if dependency_waiting_count:
        blockers.append(
            f"{dependency_waiting_count} A2A task(s) are waiting on upstream dependencies."
        )
    if dependency_cycle_message_ids:
        blockers.append(
            f"{len(dependency_cycle_message_ids)} A2A task(s) are in circular dependencies."
        )
    if work_plan_blocked_count:
        blockers.append(f"{work_plan_blocked_count} blocked work-plan item(s).")
    if claim_revision is not None:
        claim_revision_status = claim_revision.get("status")
        if claim_revision_status in CLAIM_REVISION_BLOCKING_STATUSES:
            blockers.append(
                "Claim revision is "
                f"{claim_revision_status}: "
                f"{claim_revision.get('open_held_claim_count', 0)} open held claim(s), "
                f"{claim_revision.get('pending_followup_count', 0)} pending follow-up task(s)."
            )
    return blockers


def _latest_claim_revision_ledger_summary(
    artifacts: list[ArtifactRecord],
) -> dict[str, object] | None:
    ledgers = [
        artifact
        for artifact in artifacts
        if artifact.artifact_type == ArtifactType.CLAIM_REVISION_LEDGER
    ]
    if not ledgers:
        return None
    ledger = max(ledgers, key=lambda artifact: artifact.created_at)
    recommended_next_actions = ledger.content.get("recommended_next_actions", [])
    if not isinstance(recommended_next_actions, list):
        recommended_next_actions = []
    return {
        "artifact_id": str(ledger.artifact_id),
        "status": ledger.content.get("status"),
        "claim_revision_plan_artifact_id": ledger.content.get(
            "claim_revision_plan_artifact_id"
        ),
        "held_claim_count": ledger.content.get("held_claim_count", 0),
        "open_held_claim_count": ledger.content.get("open_held_claim_count", 0),
        "pending_followup_count": ledger.content.get("pending_followup_count", 0),
        "blocked_followup_count": ledger.content.get("blocked_followup_count", 0),
        "completed_followup_count": ledger.content.get("completed_followup_count", 0),
        "revised_artifact_count": ledger.content.get("revised_artifact_count", 0),
        "recommended_next_actions": recommended_next_actions,
        "summary": ledger.content.get("summary"),
    }


def _retry_exhausted(message: AgentMessage) -> bool:
    retry_policy = message.result.get("retry_policy", {})
    retry_policy_attempts = retry_policy.get("attempt_count", message.attempt_count)
    retry_policy_max_attempts = retry_policy.get("max_attempts", message.max_attempts)
    return (
        message.status == AgentTaskStatus.BLOCKED
        and retry_policy_attempts >= retry_policy_max_attempts
    )


def _unmet_dependency_message_ids(
    message: AgentMessage,
    messages_by_id: dict[UUID, AgentMessage],
) -> list[UUID]:
    unmet_dependency_ids = []
    for dependency_id in message.depends_on_message_ids:
        dependency = messages_by_id.get(dependency_id)
        if dependency is None or dependency.status != AgentTaskStatus.COMPLETED:
            unmet_dependency_ids.append(dependency_id)
    return unmet_dependency_ids


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


def _recommended_agent_ids(
    agent_states: list[AgentSyncState],
    work_plan,
) -> list[str]:
    agent_ids = []
    if work_plan is not None:
        agent_ids.extend(work_plan.recommended_agent_ids)
    for state in agent_states:
        if (
            state.pending_message_ids
            or state.blocked_message_ids
            or state.routed_feedback_ids
        ) and state.agent_id not in agent_ids:
            agent_ids.append(state.agent_id)
    return agent_ids


def _summary(
    agent_states: list[AgentSyncState],
    blockers: list[str],
    work_plan,
) -> str:
    work_items = len(work_plan.plan_items) if work_plan else 0
    if blockers:
        return (
            f"Recorded sync pulse for {len(agent_states)} agent(s) with "
            f"{len(blockers)} blocker group(s) and {work_items} work-plan item(s)."
        )
    return (
        f"Recorded sync pulse for {len(agent_states)} agent(s); "
        f"no blockers and {work_items} work-plan item(s)."
    )
