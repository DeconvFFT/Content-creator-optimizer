from collections import Counter
from datetime import datetime, timezone
from uuid import UUID

from all_about_llms.contracts import (
    ArtifactRecord,
    ArtifactType,
    ClaimSupportStatus,
    CockpitWalkthroughLedgerRequest,
    CockpitWalkthroughLedgerResult,
    CockpitWalkthroughStep,
    ProviderReadinessResult,
    RunEvent,
    RuntimeHealthLedgerRequest,
    RuntimeHealthStatus,
    RealtimeSessionStatus,
)
from all_about_llms.orchestration.runtime_health import RuntimeHealthLedgerWorkflow


class CockpitWalkthroughLedgerError(RuntimeError):
    """Base error for cockpit walkthrough ledger generation."""


class CockpitWalkthroughLedgerRunNotFoundError(CockpitWalkthroughLedgerError):
    """Raised when a run cannot be found for cockpit walkthrough work."""


class CockpitWalkthroughLedgerWorkflow:
    """Build a durable proof packet for cockpit demo and provider smoke readiness."""

    def __init__(self, store):
        self._store = store

    async def build(
        self,
        run_id: UUID,
        request: CockpitWalkthroughLedgerRequest,
        provider_readiness: ProviderReadinessResult,
    ) -> CockpitWalkthroughLedgerResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise CockpitWalkthroughLedgerRunNotFoundError(f"Run not found: {run_id}")

        runtime_health = None
        if request.include_runtime_health:
            runtime_health = await RuntimeHealthLedgerWorkflow(self._store).build(
                run_id,
                RuntimeHealthLedgerRequest(
                    record_artifact=request.record_artifact,
                    event_limit=request.event_limit,
                    include_static_checks=request.include_static_runtime_checks,
                    include_run_evidence=True,
                    record_live_store_evidence=request.record_live_store_evidence,
                ),
            )

        events = await self._store.list_events(run_id, limit=request.event_limit)
        artifacts = await self._store.list_artifacts(run_id)
        sources = await self._store.list_sources(run_id)
        claims = await self._store.list_claims(run_id)
        feedback_items = await self._store.list_feedback(run_id)
        realtime_sessions = await self._store.list_realtime_sessions(run_id)
        memories = [
            memory
            for memory, _score in await self._store.search_memories(
                run_id=run_id,
                include_global_memories=True,
                limit=25,
            )
        ]

        steps = [
            _runtime_health_step(runtime_health),
            _provider_readiness_step(provider_readiness),
            _provider_free_demo_step(
                sources=sources,
                claims=claims,
                artifacts=artifacts,
                feedback_items=feedback_items,
                memories=memories,
                events=events,
            ),
            _source_coverage_step(artifacts=artifacts, claims=claims),
            _realtime_smoke_step(
                provider_readiness=provider_readiness,
                realtime_sessions=realtime_sessions,
                artifacts=artifacts,
                events=events,
            ),
            _provider_observability_step(artifacts=artifacts, events=events),
            _feedback_loop_step(feedback_items=feedback_items, events=events),
        ]
        status_counts = Counter(
            step.status for step in steps if step.required
        )
        required_step_count = sum(1 for step in steps if step.required)
        status = _overall_status(status_counts)
        result = CockpitWalkthroughLedgerResult(
            run_id=run_id,
            status=status,
            required_step_count=required_step_count,
            ready_required_count=status_counts["ready"],
            needs_review_required_count=status_counts["needs_review"],
            blocked_required_count=status_counts["blocked"],
            optional_ready_count=sum(
                1 for step in steps if not step.required and step.status == "ready"
            ),
            steps=steps,
            runtime_health=runtime_health,
            provider_readiness=provider_readiness,
            summary=(
                f"Cockpit walkthrough ledger: {status_counts['ready']}/"
                f"{required_step_count} required steps ready, "
                f"{status_counts['needs_review']} need review, "
                f"{status_counts['blocked']} blocked."
            ),
        )

        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.COCKPIT_WALKTHROUGH_LEDGER,
                title="Cockpit walkthrough ledger",
                uri=f"artifact://runs/{run_id}/cockpit-walkthrough-ledger",
                content=result.model_dump(
                    mode="json", exclude={"ledger_artifact_id", "event_id"}
                ),
                provenance={
                    "workflow": "cockpit_walkthrough_ledger_v1",
                    "agent_id": "forward-deployed-engineer",
                    "event_limit": request.event_limit,
                    "include_runtime_health": request.include_runtime_health,
                    "provider_backed_smoke_ready": (
                        provider_readiness.provider_backed_smoke_ready
                    ),
                },
                revision_history=[
                    {
                        "actor": "forward-deployed-engineer",
                        "note": (
                            "Captured cockpit demo, runtime, provider, realtime, "
                            "source-ledger, and feedback-loop proof in one ledger."
                        ),
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
                event_type="cockpit_walkthrough_ledger_built",
                actor="forward-deployed-engineer",
                payload={
                    "status": result.status,
                    "required_step_count": result.required_step_count,
                    "ready_required_count": result.ready_required_count,
                    "needs_review_required_count": result.needs_review_required_count,
                    "blocked_required_count": result.blocked_required_count,
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


def _runtime_health_step(runtime_health) -> CockpitWalkthroughStep:
    if runtime_health is None:
        return CockpitWalkthroughStep(
            step_id="runtime-health",
            title="Runtime health proof",
            status="needs_review",
            evidence=[],
            missing_evidence=["Runtime health ledger was not built."],
            next_actions=["Build the runtime health ledger before live smoke execution."],
        )
    missing = [
        f"{check.check_id}: {check.status.value}"
        for check in runtime_health.checks
        if check.status != RuntimeHealthStatus.READY
    ]
    return CockpitWalkthroughStep(
        step_id="runtime-health",
        title="Runtime health proof",
        status=_runtime_status(runtime_health.status),
        evidence=[
            runtime_health.summary,
            f"ledger_artifact_id={runtime_health.ledger_artifact_id}",
        ],
        missing_evidence=missing,
        next_actions=[
            check.recommended_action
            for check in runtime_health.checks
            if check.status != RuntimeHealthStatus.READY
        ][:5],
        linked_artifact_ids=(
            [runtime_health.ledger_artifact_id]
            if runtime_health.ledger_artifact_id
            else []
        ),
        linked_event_types=["runtime_health_ledger_built"],
    )


def _provider_readiness_step(
    provider_readiness: ProviderReadinessResult,
) -> CockpitWalkthroughStep:
    missing = [
        f"Set {env_name}" for env_name in provider_readiness.missing_required_env
    ]
    return CockpitWalkthroughStep(
        step_id="provider-readiness",
        title="Provider-backed smoke readiness",
        status=(
            "ready" if provider_readiness.provider_backed_smoke_ready else "blocked"
        ),
        evidence=[
            provider_readiness.summary,
            f"ready_provider_ids={provider_readiness.ready_provider_ids}",
        ],
        missing_evidence=missing,
        next_actions=[
            action
            for step in provider_readiness.smoke_test_plan
            for action in step.next_actions
            if step.status != "ready"
        ][:8],
    )


def _provider_free_demo_step(
    *,
    sources,
    claims,
    artifacts: list[ArtifactRecord],
    feedback_items,
    memories,
    events,
) -> CockpitWalkthroughStep:
    artifact_types = {artifact.artifact_type for artifact in artifacts}
    event_types = {event.event_type for event in events}
    required_types = {
        ArtifactType.POST,
        ArtifactType.REEL_SCRIPT,
        ArtifactType.SUBSTACK_ARTICLE,
        ArtifactType.RETRIEVAL_QUALITY_LEDGER,
        ArtifactType.SOURCE_LEDGER,
    }
    checks = {
        "source_records>=3": len(sources) >= 3,
        "supported_claims": any(
            claim.support_status == ClaimSupportStatus.SUPPORTED for claim in claims
        ),
        "draft_artifacts": required_types.issubset(artifact_types),
        "feedback_gate": any(
            getattr(feedback, "metadata", {}).get("gate") == "demo_review_gate"
            for feedback in feedback_items
        ),
        "project_memory": bool(memories)
        or "project_memory_recorded" in event_types,
        "demo_seed_event": "cockpit_demo_run_seeded" in event_types,
    }
    missing = [name for name, ok in checks.items() if not ok]
    return CockpitWalkthroughStep(
        step_id="provider-free-demo",
        title="Provider-free cockpit demo proof",
        status="ready" if not missing else "blocked" if len(missing) > 3 else "needs_review",
        evidence=[
            f"sources={len(sources)}",
            f"claims={len(claims)}",
            f"artifact_types={sorted(artifact_type.value for artifact_type in artifact_types)}",
            f"feedback_items={len(feedback_items)}",
            f"memories={len(memories)}",
        ],
        missing_evidence=missing,
        next_actions=[
            "Click Load demo run in the cockpit, then rebuild this ledger."
        ]
        if missing
        else ["Use the source ledger and feedback gate to review the demo run."],
        linked_artifact_ids=[
            artifact.artifact_id
            for artifact in artifacts
            if artifact.artifact_type in required_types
        ],
        linked_event_types=[
            event_type
            for event_type in ["cockpit_demo_run_seeded", "project_memory_recorded"]
            if event_type in event_types
        ],
    )


def _source_coverage_step(
    *, artifacts: list[ArtifactRecord], claims
) -> CockpitWalkthroughStep:
    source_ledger = _latest_artifact(artifacts, ArtifactType.SOURCE_LEDGER)
    retrieval_ledger = _latest_artifact(artifacts, ArtifactType.RETRIEVAL_QUALITY_LEDGER)
    missing = []
    if source_ledger is None:
        missing.append("source_ledger")
    if retrieval_ledger is None:
        missing.append("retrieval_quality_ledger")
    if not claims:
        missing.append("claims")
    unsupported_claims = (
        source_ledger.content.get("unsupported_claim_count", 0)
        if source_ledger
        else 0
    )
    accepted_sources = (
        source_ledger.content.get("accepted_retrieval_source_count", 0)
        if source_ledger
        else 0
    )
    if source_ledger and unsupported_claims:
        missing.append(f"unsupported_claims={unsupported_claims}")
    if source_ledger and accepted_sources <= 0:
        missing.append("accepted_retrieval_source_count=0")
    return CockpitWalkthroughStep(
        step_id="source-ledger-coverage",
        title="Source-ledger and claim coverage proof",
        status="ready" if not missing else "blocked" if "source_ledger" in missing else "needs_review",
        evidence=[
            f"accepted_retrieval_source_count={accepted_sources}",
            f"unsupported_claim_count={unsupported_claims}",
            f"claim_count={len(claims)}",
        ],
        missing_evidence=missing,
        next_actions=[
            "Build retrieval quality and source ledger, then resolve unsupported claims."
        ]
        if missing
        else ["Use source-ledger drilldowns for final content QA."],
        linked_artifact_ids=[
            artifact.artifact_id
            for artifact in [source_ledger, retrieval_ledger]
            if artifact is not None
        ],
        linked_event_types=["retrieval_quality_ledger_built", "source_ledger_snapshot_built"],
    )


def _realtime_smoke_step(
    *,
    provider_readiness: ProviderReadinessResult,
    realtime_sessions,
    artifacts: list[ArtifactRecord],
    events,
) -> CockpitWalkthroughStep:
    event_types = {event.event_type for event in events}
    ledger = _latest_artifact(artifacts, ArtifactType.REALTIME_DIALOGUE_LEDGER)
    selected_realtime = provider_readiness.default_realtime_provider
    provider_backed_sessions = [
        session
        for session in realtime_sessions
        if session.provider == selected_realtime
        and not session.metadata.get("dry_run")
        and not session.metadata.get("not_provider_backed")
    ]
    active_provider_backed_sessions = [
        session
        for session in provider_backed_sessions
        if _is_active_unexpired_realtime_session(session)
    ]
    provider_backed_session_ids = {
        str(session.realtime_session_id) for session in active_provider_backed_sessions
    }
    rehearsal_sessions = [
        session for session in realtime_sessions if session.metadata.get("dry_run")
    ]
    realtime_turn_events = [
        event
        for event in events
        if event.event_type in {"realtime_turn_recorded", "realtime_turn_routed"}
    ]
    provider_backed_turn_events = [
        event
        for event in realtime_turn_events
        if str(event.payload.get("realtime_session_id")) in provider_backed_session_ids
    ]
    missing = []
    if not provider_readiness.provider_backed_smoke_ready:
        missing.append("provider_backed_smoke_ready=false")
    if not provider_backed_sessions:
        missing.append(f"provider_backed_realtime_session:{selected_realtime}")
    elif not active_provider_backed_sessions:
        if any(_is_expired_realtime_session(session) for session in provider_backed_sessions):
            missing.append(f"unexpired_provider_backed_realtime_session:{selected_realtime}")
        else:
            missing.append(f"active_provider_backed_realtime_session:{selected_realtime}")
    if ledger is None:
        missing.append("realtime_dialogue_ledger")
    if not realtime_turn_events:
        missing.append("realtime_turn_recorded_or_routed")
    if active_provider_backed_sessions and not provider_backed_turn_events:
        missing.append(f"provider_backed_realtime_turn:{selected_realtime}")
    return CockpitWalkthroughStep(
        step_id="realtime-provider-smoke",
        title="Realtime provider smoke proof",
        status="ready" if not missing else "blocked",
        evidence=[
            f"default_realtime_provider={selected_realtime}",
            f"realtime_sessions={len(realtime_sessions)}",
            f"provider_backed_sessions={len(provider_backed_sessions)}",
            f"active_provider_backed_sessions={len(active_provider_backed_sessions)}",
            f"rehearsal_sessions={len(rehearsal_sessions)}",
            f"provider_backed_turn_events={len(provider_backed_turn_events)}",
        ],
        missing_evidence=missing,
        next_actions=[
            "Configure the selected realtime provider, create a realtime session, route one voice turn, and build the realtime dialogue ledger."
        ]
        if missing
        else ["Review turn-taking and interruption state in the realtime dialogue ledger."],
        linked_artifact_ids=[ledger.artifact_id] if ledger else [],
        linked_event_types=[
            event_type
            for event_type in [
                "realtime_session_created",
                "realtime_rehearsal_session_created",
                "realtime_turn_recorded",
                "realtime_turn_routed",
            ]
            if event_type in event_types
        ],
    )


def _provider_observability_step(
    *, artifacts: list[ArtifactRecord], events
) -> CockpitWalkthroughStep:
    model_routing = _latest_artifact(artifacts, ArtifactType.MODEL_ROUTING_LEDGER)
    provider_ops = _latest_artifact(artifacts, ArtifactType.PROVIDER_OPERATIONS_LEDGER)
    event_types = {event.event_type for event in events}
    missing = []
    if model_routing is None:
        missing.append("model_routing_ledger")
    if provider_ops is None:
        missing.append("provider_operations_ledger")
    fallback_count = sum(1 for event in events if event.event_type == "provider_fallback")
    if fallback_count:
        missing.append(f"provider_fallback_count={fallback_count}")
    return CockpitWalkthroughStep(
        step_id="provider-observability",
        title="Model routing and provider operations proof",
        status="ready" if not missing else "needs_review",
        evidence=[
            f"provider_fallback_count={fallback_count}",
            f"event_types={sorted(event_types & {'agent_model_use_approved', 'provider_fallback', 'provider_operations_ledger_built', 'model_routing_ledger_built'})}",
        ],
        missing_evidence=missing,
        next_actions=[
            "Build model routing and provider operations ledgers after provider-backed runs."
        ]
        if missing
        else ["Use provider operations ledger to confirm no provider fallback occurred."],
        linked_artifact_ids=[
            artifact.artifact_id
            for artifact in [model_routing, provider_ops]
            if artifact is not None
        ],
        linked_event_types=[
            event_type
            for event_type in ["model_routing_ledger_built", "provider_operations_ledger_built"]
            if event_type in event_types
        ],
    )


def _feedback_loop_step(*, feedback_items, events) -> CockpitWalkthroughStep:
    event_types = {event.event_type for event in events}
    status_counts = Counter(
        getattr(feedback.status, "value", feedback.status) for feedback in feedback_items
    )
    unresolved_items = [
        feedback
        for feedback in feedback_items
        if getattr(feedback.status, "value", feedback.status) in {"open", "routed"}
    ]
    return CockpitWalkthroughStep(
        step_id="feedback-loop",
        title="Human feedback loop proof",
        status="needs_review" if unresolved_items else "ready",
        evidence=[
            f"feedback_items={len(feedback_items)}",
            f"open_feedback_items={status_counts['open']}",
            f"routed_feedback_items={status_counts['routed']}",
            f"unresolved_feedback_items={len(unresolved_items)}",
        ],
        missing_evidence=["unresolved_feedback_items"] if unresolved_items else [],
        next_actions=[
            "Resolve or explicitly keep open feedback gates before publishing."
        ]
        if unresolved_items
        else ["Feedback loop has no open items for this run."],
        linked_event_types=[
            event_type
            for event_type in ["human_feedback_gate_opened", "feedback_routed", "feedback_resolved"]
            if event_type in event_types
        ],
    )


def _is_active_unexpired_realtime_session(session) -> bool:
    return (
        session.status == RealtimeSessionStatus.ACTIVE
        and not _is_expired_realtime_session(session)
    )


def _is_expired_realtime_session(session) -> bool:
    expires_at_unix = getattr(session, "expires_at_unix", None)
    if expires_at_unix is None:
        return False
    return expires_at_unix <= int(datetime.now(timezone.utc).timestamp())


def _latest_artifact(
    artifacts: list[ArtifactRecord], artifact_type: ArtifactType
) -> ArtifactRecord | None:
    matches = [
        artifact for artifact in artifacts if artifact.artifact_type == artifact_type
    ]
    return matches[-1] if matches else None


def _runtime_status(status: RuntimeHealthStatus) -> str:
    if status == RuntimeHealthStatus.READY:
        return "ready"
    if status == RuntimeHealthStatus.BLOCKED:
        return "blocked"
    return "needs_review"


def _overall_status(status_counts: Counter[str]) -> str:
    if status_counts["blocked"]:
        return "blocked"
    if status_counts["needs_review"]:
        return "needs_review"
    return "ready"
