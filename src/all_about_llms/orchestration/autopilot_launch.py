from uuid import UUID

from all_about_llms.agents import get_agent_card
from all_about_llms.contracts import (
    ArtifactRecord,
    ArtifactType,
    AutopilotLaunchRequest,
    AutopilotLaunchResult,
    RunEvent,
    WorkerProfile,
    WorkerProfileExecutionMode,
    WorkerProfileHeartbeatResult,
    WorkerProfileStatus,
)


class AutopilotLaunchRunNotFoundError(RuntimeError):
    """Raised when an autopilot launch references a missing run."""


class AutopilotLaunchAgentNotFoundError(RuntimeError):
    """Raised when an autopilot launch references an unknown agent."""


class AutopilotLaunchWorkflow:
    """Create or resume an always-on autonomous profile with durable evidence."""

    def __init__(self, store, worker):
        self._store = store
        self._worker = worker

    async def launch(
        self, run_id: UUID, request: AutopilotLaunchRequest
    ) -> AutopilotLaunchResult:
        self._validate_agents(request)
        run = await self._store.get_run(run_id)
        if run is None:
            raise AutopilotLaunchRunNotFoundError(f"Run not found: {run_id}")

        profile, created_profile = await self._get_or_create_profile(run_id, request)
        reused_profile = not created_profile
        started_profile = False

        if profile.status != WorkerProfileStatus.ACTIVE:
            updated = await self._store.update_worker_profile_status(
                profile.profile_id, WorkerProfileStatus.ACTIVE
            )
            if updated is not None:
                profile = updated
            started_profile = True
            await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="worker_profile_active",
                    actor="agent-harness-engineer",
                    payload=profile.model_dump(mode="json"),
                )
            )
        elif created_profile:
            started_profile = True

        heartbeat_result = None
        if request.run_first_heartbeat:
            heartbeat_result = await self._worker.run_profile_heartbeat(
                profile.profile_id
            )
            profile = heartbeat_result.profile

        launch_ledger_artifact = None
        event_id = None
        if request.record_artifact:
            launch_ledger_artifact, event_id = await self._record_launch_ledger(
                run_id=run_id,
                profile=profile,
                request=request,
                created_profile=created_profile,
                reused_profile=reused_profile,
                started_profile=started_profile,
                heartbeat_result=heartbeat_result,
            )

        state = _heartbeat_state(heartbeat_result)
        summary = (
            "Autopilot launch recorded for autonomous profile "
            f"{profile.profile_id}; heartbeat state: {state}."
        )
        return AutopilotLaunchResult(
            run_id=run_id,
            profile=profile,
            created_profile=created_profile,
            reused_profile=reused_profile,
            started_profile=started_profile,
            heartbeat_result=heartbeat_result,
            launch_ledger_artifact=launch_ledger_artifact,
            event_id=event_id,
            summary=summary,
        )

    async def _get_or_create_profile(
        self, run_id: UUID, request: AutopilotLaunchRequest
    ) -> tuple[WorkerProfile, bool]:
        if request.reuse_existing_profile:
            profile = await self._select_existing_profile(run_id, request.profile_name)
            if profile is not None:
                return profile, False

        profile = WorkerProfile(
            run_id=run_id,
            name=request.profile_name,
            execution_mode=WorkerProfileExecutionMode.AUTONOMOUS_PASS,
            agent_ids=request.agent_ids,
            max_tasks_per_agent=request.max_tasks_per_agent,
            max_rounds=request.max_rounds,
            poll_interval_seconds=request.poll_interval_seconds,
            include_global_memories=request.include_global_memories,
            memory_limit=request.memory_limit,
            autonomous_auto_refresh_research_sources=(
                request.autonomous_auto_refresh_research_sources
            ),
            autonomous_block_on_research_freshness_blocked=(
                request.autonomous_block_on_research_freshness_blocked
            ),
            autonomous_block_on_retrieval_quality_blocked=(
                request.autonomous_block_on_retrieval_quality_blocked
            ),
            autonomous_export_memory_summary_to_obsidian=(
                request.autonomous_export_memory_summary_to_obsidian
            ),
            autonomous_memory_summary_agent_id=(
                request.autonomous_memory_summary_agent_id
            ),
            autonomous_memory_summary_limit=request.autonomous_memory_summary_limit,
            use_gemma=request.use_gemma,
            fail_on_provider_error=request.fail_on_provider_error,
            status=WorkerProfileStatus.ACTIVE,
        )
        await self._store.record_worker_profile(profile)
        await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="worker_profile_created",
                actor="agent-harness-engineer",
                payload=profile.model_dump(mode="json"),
            )
        )
        return profile, True

    async def _select_existing_profile(
        self, run_id: UUID, profile_name: str
    ) -> WorkerProfile | None:
        profiles = await self._store.list_worker_profiles(run_id)
        autonomous_profiles = [
            profile
            for profile in profiles
            if profile.execution_mode == WorkerProfileExecutionMode.AUTONOMOUS_PASS
            and profile.status != WorkerProfileStatus.STOPPED
        ]
        if not autonomous_profiles:
            return None
        return (
            next(
                (
                    profile
                    for profile in autonomous_profiles
                    if profile.status == WorkerProfileStatus.ACTIVE
                    and profile.name == profile_name
                ),
                None,
            )
            or next(
                (
                    profile
                    for profile in autonomous_profiles
                    if profile.name == profile_name
                ),
                None,
            )
            or next(
                (
                    profile
                    for profile in autonomous_profiles
                    if profile.status == WorkerProfileStatus.ACTIVE
                ),
                None,
            )
            or autonomous_profiles[-1]
        )

    async def _record_launch_ledger(
        self,
        *,
        run_id: UUID,
        profile: WorkerProfile,
        request: AutopilotLaunchRequest,
        created_profile: bool,
        reused_profile: bool,
        started_profile: bool,
        heartbeat_result: WorkerProfileHeartbeatResult | None,
    ) -> tuple[ArtifactRecord, int | None]:
        linked_artifacts = _linked_artifacts(heartbeat_result)
        content = {
            "profile": profile.model_dump(mode="json"),
            "created_profile": created_profile,
            "reused_profile": reused_profile,
            "started_profile": started_profile,
            "run_first_heartbeat": request.run_first_heartbeat,
            "heartbeat": _heartbeat_summary(heartbeat_result),
            "linked_artifacts": linked_artifacts,
            "operator_next_actions": _operator_next_actions(heartbeat_result),
        }
        artifact = ArtifactRecord(
            run_id=run_id,
            artifact_type=ArtifactType.AUTOPILOT_LAUNCH_LEDGER,
            title="Autopilot Launch Ledger",
            uri=f"artifact://runs/{run_id}/autopilot-launch-ledger",
            content=content,
            provenance={
                "workflow": "autopilot_launch_v1",
                "created_by": "agent-harness-engineer",
                "profile_id": str(profile.profile_id),
                "request": request.model_dump(mode="json"),
            },
        )
        await self._store.record_artifact(artifact)
        event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="autopilot_launch_recorded",
                actor="agent-harness-engineer",
                payload={
                    "profile_id": str(profile.profile_id),
                    "created_profile": created_profile,
                    "reused_profile": reused_profile,
                    "started_profile": started_profile,
                    "heartbeat_state": _heartbeat_state(heartbeat_result),
                    "heartbeat_skipped": (
                        heartbeat_result.skipped if heartbeat_result else None
                    ),
                    "skipped_reason": (
                        heartbeat_result.skipped_reason if heartbeat_result else None
                    ),
                    "launch_ledger_artifact_id": str(artifact.artifact_id),
                    **linked_artifacts,
                },
            )
        )
        return artifact, event.event_id

    def _validate_agents(self, request: AutopilotLaunchRequest) -> None:
        for agent_id in request.agent_ids:
            if get_agent_card(agent_id) is None:
                raise AutopilotLaunchAgentNotFoundError(
                    f"Agent not found: {agent_id}"
                )
        if (
            request.autonomous_memory_summary_agent_id is not None
            and get_agent_card(request.autonomous_memory_summary_agent_id) is None
        ):
            raise AutopilotLaunchAgentNotFoundError(
                "Agent not found: "
                f"{request.autonomous_memory_summary_agent_id}"
            )


def _heartbeat_state(heartbeat_result: WorkerProfileHeartbeatResult | None) -> str:
    if heartbeat_result is None:
        return "not_run"
    if heartbeat_result.skipped:
        return "blocked" if heartbeat_result.skipped_reason else "skipped"
    return "completed"


def _heartbeat_summary(
    heartbeat_result: WorkerProfileHeartbeatResult | None,
) -> dict[str, object]:
    if heartbeat_result is None:
        return {
            "state": "not_run",
            "summary": "Autopilot profile was prepared without running a heartbeat.",
        }
    return {
        "state": _heartbeat_state(heartbeat_result),
        "skipped": heartbeat_result.skipped,
        "skipped_reason": heartbeat_result.skipped_reason,
        "summary": heartbeat_result.summary,
        "resume_allowed": (
            heartbeat_result.resume_plan.resume_allowed
            if heartbeat_result.resume_plan
            else None
        ),
        "autonomous_pass_event_id": (
            heartbeat_result.autonomous_pass_result.event_id
            if heartbeat_result.autonomous_pass_result
            else None
        ),
        "processed_tasks": (
            heartbeat_result.cycle_result.total_processed_tasks
            if heartbeat_result.cycle_result
            else 0
        ),
    }


def _linked_artifacts(
    heartbeat_result: WorkerProfileHeartbeatResult | None,
) -> dict[str, str | None]:
    if heartbeat_result is None:
        return {
            "heartbeat_ledger_artifact_id": None,
            "context_packet_artifact_id": None,
            "work_plan_artifact_id": None,
            "realtime_dialogue_artifact_id": None,
            "feedback_resolution_artifact_id": None,
        }
    return {
        "heartbeat_ledger_artifact_id": _artifact_id(
            heartbeat_result.heartbeat_ledger_artifact
        ),
        "context_packet_artifact_id": _artifact_id(
            heartbeat_result.context_packet_artifact
        ),
        "work_plan_artifact_id": (
            str(heartbeat_result.work_plan.artifact_id)
            if heartbeat_result.work_plan and heartbeat_result.work_plan.artifact_id
            else None
        ),
        "realtime_dialogue_artifact_id": (
            str(heartbeat_result.realtime_dialogue_ledger.ledger_artifact_id)
            if heartbeat_result.realtime_dialogue_ledger
            and heartbeat_result.realtime_dialogue_ledger.ledger_artifact_id
            else None
        ),
        "feedback_resolution_artifact_id": (
            str(heartbeat_result.feedback_resolution_ledger.ledger_artifact_id)
            if heartbeat_result.feedback_resolution_ledger
            and heartbeat_result.feedback_resolution_ledger.ledger_artifact_id
            else None
        ),
    }


def _artifact_id(artifact: ArtifactRecord | None) -> str | None:
    return str(artifact.artifact_id) if artifact else None


def _operator_next_actions(
    heartbeat_result: WorkerProfileHeartbeatResult | None,
) -> list[str]:
    if heartbeat_result is None:
        return ["Run a heartbeat or scheduler pass to begin autonomous work."]
    if heartbeat_result.skipped_reason == "heartbeat_already_running":
        return ["Wait for the active heartbeat lease to expire or finish."]
    if heartbeat_result.skipped_reason:
        return [
            "Resolve the blocked heartbeat reason before expecting autonomous progress.",
            "Review the heartbeat ledger and feedback gates for exact blockers.",
        ]
    if heartbeat_result.skipped:
        return ["Review the heartbeat ledger before the next scheduler pass."]
    return [
        "Review the autonomous heartbeat ledger and context packet.",
        "Use the scheduler to continue due always-on profile work.",
    ]
