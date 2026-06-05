from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from all_about_llms.contracts import (
    A2ACollaborationGraphRequest,
    AgentMessage,
    AgentTaskStatus,
    AgentWorkerRunRequest,
    AgentWorkerCycleRequest,
    ArtifactRecord,
    ArtifactType,
    AutonomousStudioPassRequest,
    AutonomousStudioPassResult,
    DistributionPackageRequest,
    FeedbackResolutionLedgerRequest,
    FeedbackStatus,
    FoundationAuditRequest,
    GuardrailAuditRequest,
    InteractiveRunNoteRequest,
    MediaProductionRequest,
    MemorySearchResult,
    ModelRoutingLedgerRequest,
    ProviderOperationsLedgerRequest,
    ProviderSmokeRunRequest,
    ProjectMemoryRetrievalRequest,
    PublishReadinessRequest,
    RealtimeDialogueLedgerRequest,
    ResearchFreshnessLedgerRequest,
    ResearchFreshnessStatus,
    RetrievalQualityLedgerRequest,
    RetrievalQualityStatus,
    RunCheckpointCreate,
    RunEvent,
    RunReplayLedgerRequest,
    RuntimeHealthLedgerRequest,
    RuntimeHealthStatus,
    RunSyncPulseRequest,
    RunWorkPlanRequest,
    SkillUsageLedgerRequest,
    SourceLedgerSnapshotRequest,
)
from all_about_llms.config import Settings
from all_about_llms.orchestration.a2a_projection import (
    public_a2a_message_event_payload,
)
from all_about_llms.orchestration.a2a_graph import A2ACollaborationGraphWorkflow
from all_about_llms.orchestration.agent_worker import AgentWorker
from all_about_llms.orchestration.context_engineering import (
    build_context_engineering_payload,
)
from all_about_llms.orchestration.foundation_audit import FoundationAuditWorkflow
from all_about_llms.orchestration.feedback_resolution import (
    FeedbackResolutionLedgerWorkflow,
)
from all_about_llms.orchestration.guardrail_audit import (
    GuardrailAuditWorkflow,
    NoArtifactsToAuditError,
)
from all_about_llms.orchestration.distribution_package import (
    DistributionPackageWorkflow,
    NoArtifactsForDistributionPackageError,
)
from all_about_llms.orchestration.interactive_notes import InteractiveRunNoteWorkflow
from all_about_llms.orchestration.media_production import (
    MediaProductionWorkflow,
    NoArtifactsForMediaProductionError,
)
from all_about_llms.orchestration.model_routing_ledger import (
    ModelRoutingLedgerWorkflow,
)
from all_about_llms.orchestration.publish_readiness import PublishReadinessWorkflow
from all_about_llms.orchestration.provider_ops import ProviderOperationsLedgerWorkflow
from all_about_llms.orchestration.provider_smoke import ProviderSmokeWorkflow
from all_about_llms.orchestration.project_memory_retrieval import (
    ProjectMemoryRetrievalWorkflow,
    project_memory_retrieval_digest,
)
from all_about_llms.orchestration.realtime_dialogue import (
    RealtimeDialogueLedgerWorkflow,
)
from all_about_llms.orchestration.research_freshness import (
    ResearchFreshnessLedgerWorkflow,
)
from all_about_llms.orchestration.retrieval_quality import (
    RetrievalQualityLedgerWorkflow,
)
from all_about_llms.orchestration.run_replay import RunReplayLedgerWorkflow
from all_about_llms.orchestration.run_resume import RunResumeWorkflow
from all_about_llms.orchestration.runtime_health import RuntimeHealthLedgerWorkflow
from all_about_llms.orchestration.services import ContentWorkflowServices
from all_about_llms.orchestration.source_ledger import SourceLedgerWorkflow
from all_about_llms.orchestration.skill_usage import SkillUsageLedgerWorkflow
from all_about_llms.orchestration.sync_pulse import RunSyncPulseWorkflow
from all_about_llms.orchestration.work_plan import RunWorkPlanWorkflow


class AutonomousStudioPassError(RuntimeError):
    """Base error for bounded autonomous studio passes."""


class AutonomousStudioPassRunNotFoundError(AutonomousStudioPassError):
    """Raised when a studio pass targets a missing run."""


SOURCE_CONTENT_TYPES = {
    ArtifactType.POST,
    ArtifactType.REEL_SCRIPT,
    ArtifactType.SUBSTACK_ARTICLE,
}

MEDIA_PLAN_TYPES = {
    ArtifactType.IMAGE,
    ArtifactType.AUDIO,
    ArtifactType.VIDEO,
}

MULTIMODAL_FOLLOWUP_WORKER_AGENT_IDS = [
    "context-engineering-agent",
    "product-manager",
    "interactive-note-taking-agent",
    "realtime-conversation-host",
    "image-generation-agent",
    "audio-producer",
    "video-reel-producer",
    "script-doctor",
    "content-strategist",
    "web-research-agent",
]


class AutonomousStudioPassWorkflow:
    """Run a bounded, resumable multi-agent pass over an existing content run."""

    def __init__(
        self,
        store,
        artifacts_root: Path,
        services: ContentWorkflowServices | None = None,
        obsidian_vault_path: Path | None = None,
        settings: Settings | None = None,
        realtime_provider_factory=None,
    ):
        self._store = store
        self._artifacts_root = artifacts_root
        self._services = services or ContentWorkflowServices()
        self._obsidian_vault_path = obsidian_vault_path
        self._settings = settings or Settings()
        self._realtime_provider_factory = realtime_provider_factory

    async def run(
        self,
        run_id: UUID,
        request: AutonomousStudioPassRequest,
    ) -> AutonomousStudioPassResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise AutonomousStudioPassRunNotFoundError(f"Run not found: {run_id}")

        skipped_steps: list[str] = []
        await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="autonomous_studio_pass_started",
                actor="agent-harness-engineer",
                payload={
                    "agent_ids": request.agent_ids,
                    "max_tasks_per_agent": request.max_tasks_per_agent,
                    "max_worker_rounds": request.max_worker_rounds,
                    "run_runtime_health_check": request.run_runtime_health_check,
                    "block_on_runtime_health_blocked": (
                        request.block_on_runtime_health_blocked
                    ),
                    "build_research_freshness_ledger": (
                        request.build_research_freshness_ledger
                    ),
                    "auto_refresh_research_sources": (
                        request.auto_refresh_research_sources
                    ),
                    "block_on_research_freshness_blocked": (
                        request.block_on_research_freshness_blocked
                    ),
                    "build_retrieval_quality_ledger": (
                        request.build_retrieval_quality_ledger
                    ),
                    "block_on_retrieval_quality_blocked": (
                        request.block_on_retrieval_quality_blocked
                    ),
                    "retrieval_quality_candidate_window": (
                        request.retrieval_quality_candidate_window
                    ),
                    "retrieval_quality_min_accepted_sources": (
                        request.retrieval_quality_min_accepted_sources
                    ),
                    "build_a2a_collaboration_graph": (
                        request.build_a2a_collaboration_graph
                    ),
                    "block_on_a2a_graph_blocked": (
                        request.block_on_a2a_graph_blocked
                    ),
                    "block_on_open_feedback": request.block_on_open_feedback,
                    "run_worker_cycle": request.run_worker_cycle,
                    "continue_multimodal_followups": (
                        request.continue_multimodal_followups
                    ),
                    "multimodal_followup_rounds": request.multimodal_followup_rounds,
                    "build_missing_media_plans": request.build_missing_media_plans,
                    "build_distribution_package": request.build_distribution_package,
                    "refresh_source_ledger": request.refresh_source_ledger,
                    "run_guardrail_audit": request.run_guardrail_audit,
                    "check_publish_readiness": request.check_publish_readiness,
                    "build_work_plan": request.build_work_plan,
                    "record_sync_pulse": request.record_sync_pulse,
                    "build_context_packet": request.build_context_packet,
                    "context_packet_agent_id": request.context_packet_agent_id,
                    "context_packet_event_limit": request.context_packet_event_limit,
                    "context_packet_max_manifest_items": (
                        request.context_packet_max_manifest_items
                    ),
                    "context_packet_max_context_tokens": (
                        request.context_packet_max_context_tokens
                    ),
                    "export_memory_summary_to_obsidian": (
                        request.export_memory_summary_to_obsidian
                    ),
                    "memory_summary_agent_id": request.memory_summary_agent_id,
                    "memory_summary_limit": request.memory_summary_limit,
                    "build_skill_usage_ledger": request.build_skill_usage_ledger,
                    "build_model_routing_ledger": (
                        request.build_model_routing_ledger
                    ),
                    "build_provider_smoke_ledger": (
                        request.build_provider_smoke_ledger
                    ),
                    "provider_smoke_execute_live_calls": (
                        request.provider_smoke_execute_live_calls
                    ),
                    "provider_smoke_realtime_provider": (
                        request.provider_smoke_realtime_provider
                    ),
                    "build_provider_ops_ledger": request.build_provider_ops_ledger,
                    "build_foundation_audit": request.build_foundation_audit,
                    "foundation_audit_event_limit": (
                        request.foundation_audit_event_limit
                    ),
                    "build_run_replay_ledger": request.build_run_replay_ledger,
                    "generate_interactive_note": request.generate_interactive_note,
                    "open_feedback_gate": request.open_feedback_gate,
                    "notes": request.notes,
                },
            )
        )

        checkpoint = None
        if request.create_checkpoint:
            checkpoint_result = await RunResumeWorkflow(self._store).create_checkpoint(
                run_id,
                RunCheckpointCreate(
                    checkpoint_kind="autonomous_studio_pass_start",
                    created_by="agent-harness-engineer",
                    notes=request.notes,
                ),
            )
            checkpoint = checkpoint_result.checkpoint
        else:
            skipped_steps.append("checkpoint_disabled")

        runtime_health = None
        runtime_health_blocked = False
        if request.run_runtime_health_check:
            runtime_health = await RuntimeHealthLedgerWorkflow(self._store).build(
                run_id,
                RuntimeHealthLedgerRequest(
                    record_artifact=True,
                    event_limit=250,
                    include_static_checks=True,
                    include_run_evidence=True,
                    record_live_store_evidence=True,
                ),
            )
            runtime_health_blocked = (
                runtime_health.status == RuntimeHealthStatus.BLOCKED
                and request.block_on_runtime_health_blocked
            )
            if runtime_health_blocked:
                skipped_steps.append("runtime_health_blocked_autonomous_pass")
        else:
            skipped_steps.append("runtime_health_check_disabled")

        a2a_collaboration_graph = None
        a2a_graph_blocked = False
        if runtime_health_blocked:
            skipped_steps.append("a2a_graph_blocked_by_runtime_health")
        elif request.build_a2a_collaboration_graph:
            a2a_collaboration_graph = await A2ACollaborationGraphWorkflow(
                self._store
            ).build(
                run_id,
                A2ACollaborationGraphRequest(
                    record_artifact=True,
                    include_completed_tasks=True,
                    max_messages=500,
                ),
            )
            a2a_graph_blocked = (
                request.block_on_a2a_graph_blocked
                and (
                    bool(a2a_collaboration_graph.dependency_cycle_message_ids)
                    or bool(a2a_collaboration_graph.retry_exhausted_task_ids)
                )
            )
            if a2a_graph_blocked:
                skipped_steps.append("a2a_graph_blocked_autonomous_pass")
        else:
            skipped_steps.append("a2a_graph_check_disabled")

        open_feedback_items = await self._store.list_feedback(
            run_id,
            status=FeedbackStatus.OPEN,
        )
        open_feedback_blocked = (
            bool(open_feedback_items) and request.block_on_open_feedback
        )
        if open_feedback_blocked:
            skipped_steps.append("open_feedback_blocked_autonomous_pass")

        worker_cycle = None
        if runtime_health_blocked:
            skipped_steps.append("worker_cycle_blocked_by_runtime_health")
        elif a2a_graph_blocked:
            skipped_steps.append("worker_cycle_blocked_by_a2a_graph")
        elif open_feedback_blocked:
            skipped_steps.append("worker_cycle_blocked_by_open_feedback")
        elif request.run_worker_cycle:
            worker_cycle = await AgentWorker(
                self._store,
                self._services,
                artifacts_root=self._artifacts_root,
            ).run_cycle(
                AgentWorkerCycleRequest(
                    run_id=run_id,
                    agent_ids=request.agent_ids,
                    max_tasks_per_agent=request.max_tasks_per_agent,
                    max_rounds=request.max_worker_rounds,
                    use_gemma=request.use_gemma,
                    fail_on_provider_error=request.fail_on_provider_error,
                )
            )
        else:
            skipped_steps.append("worker_cycle_disabled")

        multimodal_followup_cycle = None
        if runtime_health_blocked:
            skipped_steps.append("multimodal_followup_cycle_blocked_by_runtime_health")
        elif a2a_graph_blocked:
            skipped_steps.append("multimodal_followup_cycle_blocked_by_a2a_graph")
        elif open_feedback_blocked:
            skipped_steps.append("multimodal_followup_cycle_blocked_by_open_feedback")
        elif request.continue_multimodal_followups:
            pending_multimodal_followups = await self._pending_multimodal_followups(
                run_id
            )
            if pending_multimodal_followups:
                multimodal_followup_cycle = await AgentWorker(
                    self._store,
                    self._services,
                    artifacts_root=self._artifacts_root,
                ).run_cycle(
                    AgentWorkerCycleRequest(
                        run_id=run_id,
                        agent_ids=MULTIMODAL_FOLLOWUP_WORKER_AGENT_IDS,
                        max_tasks_per_agent=request.max_tasks_per_agent,
                        max_rounds=request.multimodal_followup_rounds,
                        use_gemma=request.use_gemma,
                        fail_on_provider_error=request.fail_on_provider_error,
                    )
                )
                await self._store.append_event(
                    RunEvent(
                        run_id=run_id,
                        event_type="autonomous_multimodal_followups_continued",
                        actor="agent-harness-engineer",
                        payload={
                            "initial_pending_followup_count": len(
                                pending_multimodal_followups
                            ),
                            "processed_task_count": (
                                multimodal_followup_cycle.total_processed_tasks
                            ),
                            "rounds_completed": (
                                multimodal_followup_cycle.rounds_completed
                            ),
                            "agent_ids": MULTIMODAL_FOLLOWUP_WORKER_AGENT_IDS,
                        },
                    )
                )
        else:
            skipped_steps.append("multimodal_followup_cycle_disabled")

        research_freshness = None
        research_refresh_cycle = None
        research_freshness_blocked = False
        if runtime_health_blocked:
            skipped_steps.append("research_freshness_blocked_by_runtime_health")
        elif open_feedback_blocked:
            skipped_steps.append("research_freshness_blocked_by_open_feedback")
        elif request.build_research_freshness_ledger:
            research_freshness = await ResearchFreshnessLedgerWorkflow(
                self._store
            ).build(
                run_id,
                ResearchFreshnessLedgerRequest(
                    record_artifact=True,
                    freshness_required=True,
                ),
            )
            if (
                request.auto_refresh_research_sources
                and research_freshness.status == ResearchFreshnessStatus.BLOCKED
                and _search_provider_is_configured(self._services.search_provider)
            ):
                research_refresh_cycle = await self._refresh_research_sources(
                    run_id=run_id,
                    topic=research_freshness.topic,
                    request=request,
                )
                research_freshness = await ResearchFreshnessLedgerWorkflow(
                    self._store
                ).build(
                    run_id,
                    ResearchFreshnessLedgerRequest(
                        topic=research_freshness.topic,
                        record_artifact=True,
                        freshness_required=True,
                    ),
                )
                await self._store.append_event(
                    RunEvent(
                        run_id=run_id,
                        event_type="autonomous_research_sources_refreshed",
                        actor="agent-harness-engineer",
                        payload={
                            "topic": research_freshness.topic,
                            "processed_task_count": len(
                                research_refresh_cycle.processed_tasks
                            ),
                            "idle": research_refresh_cycle.idle,
                            "final_freshness_status": (
                                research_freshness.status.value
                            ),
                            "ledger_artifact_id": (
                                str(research_freshness.ledger_artifact_id)
                                if research_freshness.ledger_artifact_id
                                else None
                            ),
                        },
                    )
                )
            elif (
                request.auto_refresh_research_sources
                and research_freshness.status == ResearchFreshnessStatus.BLOCKED
            ):
                skipped_steps.append("research_source_refresh_unconfigured")
            elif not request.auto_refresh_research_sources:
                skipped_steps.append("research_source_refresh_disabled")
            research_freshness_blocked = (
                research_freshness.status == ResearchFreshnessStatus.BLOCKED
                and request.block_on_research_freshness_blocked
            )
            if research_freshness_blocked:
                skipped_steps.append("research_freshness_blocked_autonomous_pass")
        else:
            skipped_steps.append("research_freshness_disabled")

        retrieval_quality = None
        retrieval_quality_blocked = False
        if runtime_health_blocked:
            skipped_steps.append("retrieval_quality_blocked_by_runtime_health")
        elif open_feedback_blocked:
            skipped_steps.append("retrieval_quality_blocked_by_open_feedback")
        elif request.build_retrieval_quality_ledger:
            retrieval_quality = await RetrievalQualityLedgerWorkflow(
                self._store,
                self._services.reranker_provider,
            ).build(
                run_id,
                RetrievalQualityLedgerRequest(
                    record_artifact=True,
                    candidate_window=request.retrieval_quality_candidate_window,
                    min_accepted_sources=(
                        request.retrieval_quality_min_accepted_sources
                    ),
                    require_reranking=True,
                    require_graph_coverage=True,
                ),
            )
            retrieval_quality_blocked = (
                retrieval_quality.status != RetrievalQualityStatus.READY
                and request.block_on_retrieval_quality_blocked
            )
            if retrieval_quality_blocked:
                skipped_steps.append("retrieval_quality_blocked_autonomous_pass")
        else:
            skipped_steps.append("retrieval_quality_disabled")

        media_production = None
        if runtime_health_blocked:
            skipped_steps.append("media_plan_blocked_by_runtime_health")
        elif a2a_graph_blocked:
            skipped_steps.append("media_plan_blocked_by_a2a_graph")
        elif open_feedback_blocked:
            skipped_steps.append("media_plan_blocked_by_open_feedback")
        elif not request.build_missing_media_plans:
            skipped_steps.append("media_plan_disabled")
        elif research_freshness_blocked:
            skipped_steps.append("media_plan_blocked_by_research_freshness")
        elif retrieval_quality_blocked:
            skipped_steps.append("media_plan_blocked_by_retrieval_quality")
        else:
            media_request, media_skip_reason = await self._media_request_for_current_content(
                run_id
            )
            if media_request is None:
                skipped_steps.append(media_skip_reason or "media_plan_not_needed")
            else:
                try:
                    media_production = await MediaProductionWorkflow(self._store).run(
                        run_id,
                        media_request,
                    )
                except NoArtifactsForMediaProductionError:
                    skipped_steps.append("no_content_artifacts_for_media_plan")

        distribution_package = None
        if runtime_health_blocked:
            skipped_steps.append("distribution_package_blocked_by_runtime_health")
        elif a2a_graph_blocked:
            skipped_steps.append("distribution_package_blocked_by_a2a_graph")
        elif open_feedback_blocked:
            skipped_steps.append("distribution_package_blocked_by_open_feedback")
        elif not request.build_distribution_package:
            skipped_steps.append("distribution_package_disabled")
        elif research_freshness_blocked:
            skipped_steps.append("distribution_package_blocked_by_research_freshness")
        elif retrieval_quality_blocked:
            skipped_steps.append("distribution_package_blocked_by_retrieval_quality")
        else:
            (
                distribution_request,
                distribution_skip_reason,
            ) = await self._distribution_request_for_current_content(run_id)
            if distribution_request is None:
                skipped_steps.append(
                    distribution_skip_reason or "distribution_package_not_needed"
                )
            else:
                try:
                    distribution_package = await DistributionPackageWorkflow(
                        self._store
                    ).run(run_id, distribution_request)
                except NoArtifactsForDistributionPackageError:
                    skipped_steps.append("no_content_artifacts_for_distribution")

        source_ledger = None
        if runtime_health_blocked:
            skipped_steps.append("source_ledger_blocked_by_runtime_health")
        elif open_feedback_blocked:
            skipped_steps.append("source_ledger_blocked_by_open_feedback")
        elif request.refresh_source_ledger:
            source_ledger = await SourceLedgerWorkflow(self._store).build(
                run_id,
                SourceLedgerSnapshotRequest(
                    record_artifact=True,
                    include_artifact_content=False,
                ),
            )
        else:
            skipped_steps.append("source_ledger_disabled")

        guardrail_audit = None
        if runtime_health_blocked:
            skipped_steps.append("guardrail_audit_blocked_by_runtime_health")
        elif open_feedback_blocked:
            skipped_steps.append("guardrail_audit_blocked_by_open_feedback")
        elif not request.run_guardrail_audit:
            skipped_steps.append("guardrail_audit_disabled")
        elif research_freshness_blocked:
            skipped_steps.append("guardrail_audit_blocked_by_research_freshness")
        elif retrieval_quality_blocked:
            skipped_steps.append("guardrail_audit_blocked_by_retrieval_quality")
        else:
            try:
                guardrail_audit = await GuardrailAuditWorkflow(self._store).run(
                    run_id,
                    GuardrailAuditRequest(open_feedback_gate=request.open_feedback_gate),
                )
            except NoArtifactsToAuditError:
                skipped_steps.append("no_artifacts_for_guardrail_audit")

        publish_readiness = None
        if runtime_health_blocked:
            skipped_steps.append("publish_readiness_blocked_by_runtime_health")
        elif open_feedback_blocked:
            skipped_steps.append("publish_readiness_blocked_by_open_feedback")
        elif not request.check_publish_readiness:
            skipped_steps.append("publish_readiness_disabled")
        elif research_freshness_blocked:
            skipped_steps.append("publish_readiness_blocked_by_research_freshness")
        elif retrieval_quality_blocked:
            skipped_steps.append("publish_readiness_blocked_by_retrieval_quality")
        else:
            publish_readiness = await PublishReadinessWorkflow(
                self._store,
                credential_env_values=(
                    self._settings.publication_credential_env_values()
                ),
            ).run(
                run_id,
                PublishReadinessRequest(
                    open_feedback_gate=request.open_feedback_gate,
                    mark_run_completed_if_ready=False,
                    check_publish_channel_readiness=True,
                    acknowledge_publish_channel_policy=(
                        request.acknowledge_publish_channel_policy
                    ),
                ),
            )

        artifact_index = None
        if runtime_health_blocked:
            skipped_steps.append("artifact_index_blocked_by_runtime_health")
        elif request.build_artifact_index:
            artifact_index = await self._build_artifact_index(run_id)
        else:
            skipped_steps.append("artifact_index_disabled")

        work_plan = None
        if runtime_health_blocked:
            skipped_steps.append("work_plan_blocked_by_runtime_health")
        elif request.build_work_plan:
            work_plan = await RunWorkPlanWorkflow(self._store).build(
                run_id,
                RunWorkPlanRequest(
                    record_artifact=True,
                    create_followup_tasks=not open_feedback_blocked,
                ),
            )
        else:
            skipped_steps.append("work_plan_disabled")

        sync_pulse = None
        if runtime_health_blocked:
            skipped_steps.append("sync_pulse_blocked_by_runtime_health")
        elif request.record_sync_pulse:
            sync_pulse = await RunSyncPulseWorkflow(self._store).build(
                run_id,
                RunSyncPulseRequest(
                    record_artifact=True,
                    build_work_plan=False,
                    notes="Autonomous studio pass coordination pulse.",
                ),
            )
        else:
            skipped_steps.append("sync_pulse_disabled")

        skill_usage_ledger = None
        if runtime_health_blocked:
            skipped_steps.append("skill_usage_ledger_blocked_by_runtime_health")
        elif request.build_skill_usage_ledger:
            skill_usage_ledger = await SkillUsageLedgerWorkflow(self._store).build(
                run_id,
                SkillUsageLedgerRequest(
                    record_artifact=True,
                    include_pending_tasks=True,
                    max_messages=500,
                    max_events=2000,
                ),
            )
        else:
            skipped_steps.append("skill_usage_ledger_disabled")

        model_routing_ledger = None
        if runtime_health_blocked:
            skipped_steps.append("model_routing_ledger_blocked_by_runtime_health")
        elif request.build_model_routing_ledger:
            model_routing_ledger = await ModelRoutingLedgerWorkflow(
                self._store
            ).build(
                run_id,
                ModelRoutingLedgerRequest(
                    record_artifact=True,
                    event_limit=1000,
                    include_agent_matrix=True,
                    include_artifact_provenance=True,
                ),
            )
        else:
            skipped_steps.append("model_routing_ledger_disabled")

        provider_smoke_ledger = None
        if runtime_health_blocked:
            skipped_steps.append("provider_smoke_ledger_blocked_by_runtime_health")
        elif request.build_provider_smoke_ledger:
            provider_smoke_ledger = await ProviderSmokeWorkflow(
                self._store,
                self._settings,
                self._services,
                realtime_provider_factory=self._realtime_provider_factory,
            ).build(
                run_id,
                ProviderSmokeRunRequest(
                    record_artifact=True,
                    execute_live_calls=request.provider_smoke_execute_live_calls,
                    topic=run.goal,
                    realtime_provider=request.provider_smoke_realtime_provider,
                    voice=request.provider_smoke_voice,
                    search_query=request.provider_smoke_search_query,
                    event_limit=1000,
                    include_gemma=request.use_gemma,
                    include_realtime=True,
                    include_web_search=True,
                    include_reranker=True,
                    include_imagegen_boundary=True,
                ),
            )
        else:
            skipped_steps.append("provider_smoke_ledger_disabled")

        provider_operations_ledger = None
        if runtime_health_blocked:
            skipped_steps.append("provider_ops_ledger_blocked_by_runtime_health")
        elif request.build_provider_ops_ledger:
            provider_operations_ledger = await ProviderOperationsLedgerWorkflow(
                self._store
            ).build(
                run_id,
                ProviderOperationsLedgerRequest(
                    record_artifact=True,
                    event_limit=1000,
                    include_artifact_provenance=True,
                ),
            )
        else:
            skipped_steps.append("provider_ops_ledger_disabled")

        realtime_dialogue_ledger = None
        if runtime_health_blocked:
            skipped_steps.append("realtime_dialogue_ledger_blocked_by_runtime_health")
        elif request.build_realtime_dialogue_ledger:
            realtime_dialogue_ledger = await RealtimeDialogueLedgerWorkflow(
                self._store
            ).build(
                run_id,
                RealtimeDialogueLedgerRequest(
                    record_artifact=True,
                    event_limit=1000,
                    turn_limit=200,
                    include_transcript_preview=True,
                ),
            )
        else:
            skipped_steps.append("realtime_dialogue_ledger_disabled")

        feedback_resolution_ledger = None
        if runtime_health_blocked:
            skipped_steps.append("feedback_resolution_ledger_blocked_by_runtime_health")
        elif request.build_feedback_resolution_ledger:
            feedback_resolution_ledger = await FeedbackResolutionLedgerWorkflow(
                self._store
            ).build(
                run_id,
                FeedbackResolutionLedgerRequest(
                    record_artifact=True,
                    max_feedback_items=200,
                    max_messages=1000,
                ),
            )
        else:
            skipped_steps.append("feedback_resolution_ledger_disabled")

        context_packet_artifact = None
        if runtime_health_blocked:
            skipped_steps.append("context_packet_blocked_by_runtime_health")
        elif request.build_context_packet:
            context_packet_artifact = await self._build_context_packet_artifact(
                run=run,
                request=request,
            )
        else:
            skipped_steps.append("context_packet_disabled")

        interactive_note = None
        if runtime_health_blocked:
            skipped_steps.append("interactive_note_blocked_by_runtime_health")
        elif request.generate_interactive_note:
            interactive_note = await InteractiveRunNoteWorkflow(
                self._store,
                self._artifacts_root,
            ).generate(
                run_id,
                InteractiveRunNoteRequest(
                    title="Autonomous studio pass note",
                    include_event_payloads=request.include_note_event_payloads,
                ),
            )
        else:
            skipped_steps.append("interactive_note_disabled")

        foundation_audit = None
        if request.build_foundation_audit:
            foundation_audit = await FoundationAuditWorkflow(self._store).build(
                run_id,
                FoundationAuditRequest(
                    record_artifact=True,
                    event_limit=request.foundation_audit_event_limit,
                    include_static_surface_checks=True,
                ),
            )
            if not runtime_health_blocked and request.build_work_plan:
                work_plan = await RunWorkPlanWorkflow(self._store).build(
                    run_id,
                    RunWorkPlanRequest(
                        record_artifact=True,
                        create_followup_tasks=not open_feedback_blocked,
                        refresh_reason="foundation_audit_completed",
                    ),
                )
            if not runtime_health_blocked and request.record_sync_pulse:
                sync_pulse = await RunSyncPulseWorkflow(self._store).build(
                    run_id,
                    RunSyncPulseRequest(
                        record_artifact=True,
                        build_work_plan=False,
                        notes=(
                            "Post-audit manager sync pulse with same-pass "
                            "foundation remediation routed."
                        ),
                        refresh_reason="foundation_audit_completed",
                    ),
                )
            if (
                context_packet_artifact is not None
                and not runtime_health_blocked
                and request.build_context_packet
            ):
                context_packet_artifact = await self._build_context_packet_artifact(
                    run=run,
                    request=request,
                    refresh_reason="foundation_audit_completed",
                )
        else:
            skipped_steps.append("foundation_audit_disabled")

        run_replay_ledger = None
        if runtime_health_blocked:
            skipped_steps.append("run_replay_ledger_blocked_by_runtime_health")
        elif request.build_run_replay_ledger:
            run_replay_ledger = await RunReplayLedgerWorkflow(self._store).build(
                run_id,
                RunReplayLedgerRequest(
                    record_artifact=True,
                    checkpoint_id=checkpoint.checkpoint_id if checkpoint else None,
                    event_limit=1000,
                    include_event_payloads=request.include_replay_event_payloads,
                ),
            )
        else:
            skipped_steps.append("run_replay_ledger_disabled")

        obsidian_memory_summary = None
        if request.export_memory_summary_to_obsidian:
            if runtime_health_blocked:
                skipped_steps.append(
                    "obsidian_memory_summary_blocked_by_runtime_health"
                )
            elif self._obsidian_vault_path is None:
                skipped_steps.append("obsidian_memory_summary_missing_vault")
            elif context_packet_artifact is None:
                skipped_steps.append("obsidian_memory_summary_missing_context_packet")
            else:
                obsidian_memory_summary = (
                    await self._export_memory_summary_to_obsidian(
                        run=run,
                        request=request,
                        context_packet_artifact=context_packet_artifact,
                    )
                )

        context_packet_summary = (
            context_packet_artifact.content.get("summary", {})
            if context_packet_artifact
            else {}
        )
        context_packet_memory_health = context_packet_summary.get("memory_health") or {}
        context_packet_publishing_handoff = (
            context_packet_summary.get("latest_publishing_handoff") or {}
        )
        context_packet_foundation_audit = (
            context_packet_summary.get("latest_foundation_audit") or {}
        )
        context_packet_retrieval_quality = (
            context_packet_summary.get("latest_retrieval_quality") or {}
        )
        artifact_index_payload = await self._latest_artifact_index_payload(run_id)
        completed = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="autonomous_studio_pass_completed",
                actor="product-manager",
                payload={
                    "checkpoint_id": (
                        str(checkpoint.checkpoint_id) if checkpoint else None
                    ),
                    "worker_total_processed_tasks": (
                        worker_cycle.total_processed_tasks if worker_cycle else None
                    ),
                    "runtime_health_status": (
                        runtime_health.status.value if runtime_health else None
                    ),
                    "runtime_health_artifact_id": (
                        str(runtime_health.ledger_artifact_id)
                        if runtime_health and runtime_health.ledger_artifact_id
                        else None
                    ),
                    "runtime_health_blocked": runtime_health_blocked,
                    "research_freshness_status": (
                        research_freshness.status.value
                        if research_freshness
                        else None
                    ),
                    "research_freshness_artifact_id": (
                        str(research_freshness.ledger_artifact_id)
                        if research_freshness
                        and research_freshness.ledger_artifact_id
                        else None
                    ),
                    "research_refresh_processed_tasks": (
                        len(research_refresh_cycle.processed_tasks)
                        if research_refresh_cycle
                        else 0
                    ),
                    "research_refresh_idle": (
                        research_refresh_cycle.idle
                        if research_refresh_cycle
                        else None
                    ),
                    "research_freshness_blocked": research_freshness_blocked,
                    "retrieval_quality_status": (
                        retrieval_quality.status.value
                        if retrieval_quality
                        else None
                    ),
                    "retrieval_quality_artifact_id": (
                        str(retrieval_quality.ledger_artifact_id)
                        if retrieval_quality
                        and retrieval_quality.ledger_artifact_id
                        else None
                    ),
                    "retrieval_quality_blocked": retrieval_quality_blocked,
                    "retrieval_quality_candidate_count": (
                        retrieval_quality.candidate_count
                        if retrieval_quality
                        else None
                    ),
                    "retrieval_quality_accepted_candidate_count": (
                        retrieval_quality.accepted_candidate_count
                        if retrieval_quality
                        else None
                    ),
                    "retrieval_quality_precision_risk_count": (
                        retrieval_quality.precision_risk_count
                        if retrieval_quality
                        else None
                    ),
                    "retrieval_quality_recall_gap_count": (
                        retrieval_quality.recall_gap_count
                        if retrieval_quality
                        else None
                    ),
                    "retrieval_quality_coverage_gap_count": (
                        retrieval_quality.coverage_gap_count
                        if retrieval_quality
                        else None
                    ),
                    "a2a_graph_artifact_id": (
                        str(a2a_collaboration_graph.artifact_id)
                        if a2a_collaboration_graph
                        and a2a_collaboration_graph.artifact_id
                        else None
                    ),
                    "a2a_graph_event_id": (
                        a2a_collaboration_graph.event_id
                        if a2a_collaboration_graph
                        else None
                    ),
                    "a2a_graph_blocked": a2a_graph_blocked,
                    "a2a_graph_ready_task_count": (
                        len(a2a_collaboration_graph.ready_task_ids)
                        if a2a_collaboration_graph
                        else None
                    ),
                    "a2a_graph_dependency_cycle_message_count": (
                        len(a2a_collaboration_graph.dependency_cycle_message_ids)
                        if a2a_collaboration_graph
                        else None
                    ),
                    "a2a_graph_retry_exhausted_task_count": (
                        len(a2a_collaboration_graph.retry_exhausted_task_ids)
                        if a2a_collaboration_graph
                        else None
                    ),
                    "open_feedback_blocked": open_feedback_blocked,
                    "open_feedback_count": len(open_feedback_items),
                    "open_feedback_item_ids": [
                        str(feedback.feedback_id) for feedback in open_feedback_items
                    ],
                    "multimodal_followup_processed_tasks": (
                        multimodal_followup_cycle.total_processed_tasks
                        if multimodal_followup_cycle
                        else 0
                    ),
                    "multimodal_followup_rounds_completed": (
                        multimodal_followup_cycle.rounds_completed
                        if multimodal_followup_cycle
                        else 0
                    ),
                    "media_artifact_ids": (
                        [
                            str(artifact_id)
                            for artifact_id in media_production.media_artifact_ids
                        ]
                        if media_production
                        else []
                    ),
                    "distribution_artifact_id": (
                        str(distribution_package.distribution_artifact_id)
                        if distribution_package
                        else None
                    ),
                    "distribution_platforms": (
                        distribution_package.platforms if distribution_package else []
                    ),
                    "source_ledger_artifact_id": (
                        str(source_ledger.ledger_artifact_id)
                        if source_ledger and source_ledger.ledger_artifact_id
                        else None
                    ),
                    "guardrail_status": (
                        guardrail_audit.status.value if guardrail_audit else None
                    ),
                    "publish_readiness_status": (
                        publish_readiness.status.value
                        if publish_readiness
                        else None
                    ),
                    "artifact_index_processed_tasks": (
                        len(artifact_index.processed_tasks)
                        if artifact_index
                        else None
                    ),
                    "artifact_index_idle": (
                        artifact_index.idle if artifact_index else None
                    ),
                    "artifact_index_artifact_id": artifact_index_payload.get(
                        "artifact_index_artifact_id"
                    ),
                    "artifact_index_publishing_handoff_status": (
                        artifact_index_payload.get("publishing_handoff_status")
                    ),
                    "artifact_index_publishable_artifact_count": (
                        artifact_index_payload.get("publishable_artifact_count")
                    ),
                    "work_plan_artifact_id": (
                        str(work_plan.artifact_id)
                        if work_plan and work_plan.artifact_id
                        else None
                    ),
                    "work_plan_blocked_item_count": (
                        work_plan.blocked_item_count if work_plan else None
                    ),
                    "work_plan_recommended_agent_ids": (
                        work_plan.recommended_agent_ids if work_plan else []
                    ),
                    "work_plan_refresh_reason": (
                        work_plan.refresh_reason if work_plan else None
                    ),
                    "work_plan_foundation_audit_remediation_count": (
                        len(
                            [
                                item
                                for item in work_plan.plan_items
                                if item.item_type
                                == "foundation_audit_remediation"
                            ]
                        )
                        if work_plan
                        else None
                    ),
                    "sync_pulse_artifact_id": (
                        str(sync_pulse.artifact_id)
                        if sync_pulse and sync_pulse.artifact_id
                        else None
                    ),
                    "sync_pulse_blockers": sync_pulse.blockers if sync_pulse else [],
                    "sync_pulse_refresh_reason": (
                        sync_pulse.refresh_reason if sync_pulse else None
                    ),
                    "sync_pulse_recommended_agent_ids": (
                        sync_pulse.recommended_agent_ids if sync_pulse else []
                    ),
                    "context_packet_artifact_id": (
                        str(context_packet_artifact.artifact_id)
                        if context_packet_artifact
                        else None
                    ),
                    "context_packet_target_agent_id": (
                        context_packet_artifact.content.get("target_agent_id")
                        if context_packet_artifact
                        else None
                    ),
                    "context_packet_manifest_items": (
                        context_packet_artifact.content["summary"][
                            "context_manifest_items"
                        ]
                        if context_packet_artifact
                        else None
                    ),
                    "context_packet_risk_count": (
                        context_packet_artifact.content["summary"][
                            "context_risk_count"
                        ]
                        if context_packet_artifact
                        else None
                    ),
                    "context_packet_refresh_reason": (
                        context_packet_artifact.content.get("refresh_reason")
                        if context_packet_artifact
                        else None
                    ),
                    "context_packet_latest_publishing_handoff_artifact_id": (
                        context_packet_publishing_handoff.get("artifact_id")
                    ),
                    "context_packet_latest_publishing_handoff_status": (
                        context_packet_publishing_handoff.get("status")
                    ),
                    "context_packet_latest_publishing_handoff_open_feedback_count": (
                        context_packet_publishing_handoff.get("open_feedback_count")
                    ),
                    "context_packet_latest_foundation_audit_artifact_id": (
                        context_packet_foundation_audit.get("artifact_id")
                    ),
                    "context_packet_foundation_audit_remediation_count": (
                        context_packet_foundation_audit.get("remediation_count")
                    ),
                    "context_packet_latest_retrieval_quality_artifact_id": (
                        context_packet_retrieval_quality.get("artifact_id")
                    ),
                    "context_packet_latest_retrieval_quality_status": (
                        context_packet_retrieval_quality.get("status")
                    ),
                    "context_packet_retrieval_quality_recall_gap_count": (
                        context_packet_retrieval_quality.get("recall_gap_count")
                    ),
                    "context_packet_retrieval_quality_coverage_gap_count": (
                        context_packet_retrieval_quality.get("coverage_gap_count")
                    ),
                    "context_packet_memory_health_stale_count": (
                        context_packet_memory_health.get("stale_memory_count")
                    ),
                    "context_packet_memory_health_low_confidence_count": (
                        context_packet_memory_health.get(
                            "low_confidence_memory_count"
                        )
                    ),
                    "context_packet_memory_health_conflict_count": (
                        context_packet_memory_health.get("conflict_count")
                    ),
                    "obsidian_memory_summary_artifact_id": (
                        str(obsidian_memory_summary.artifact_id)
                        if obsidian_memory_summary
                        else None
                    ),
                    "obsidian_memory_summary_uri": (
                        obsidian_memory_summary.uri
                        if obsidian_memory_summary
                        else None
                    ),
                    "obsidian_memory_summary_memory_count": (
                        obsidian_memory_summary.content.get("memory_count")
                        if obsidian_memory_summary
                        else None
                    ),
                    "skill_usage_artifact_id": (
                        str(skill_usage_ledger.artifact_id)
                        if skill_usage_ledger and skill_usage_ledger.artifact_id
                        else None
                    ),
                    "skill_usage_missing_count": (
                        len(skill_usage_ledger.missing_skill_usage_message_ids)
                        if skill_usage_ledger
                        else None
                    ),
                    "skill_usage_invocation_count": (
                        skill_usage_ledger.skill_invocation_count
                        if skill_usage_ledger
                        else None
                    ),
                    "skill_source_contract_issue_count": (
                        skill_usage_ledger.skill_source_contract_issue_count
                        if skill_usage_ledger
                        else None
                    ),
                    "model_routing_artifact_id": (
                        str(model_routing_ledger.ledger_artifact_id)
                        if model_routing_ledger
                        and model_routing_ledger.ledger_artifact_id
                        else None
                    ),
                    "model_routing_boundary_violation_count": (
                        model_routing_ledger.boundary_violation_count
                        if model_routing_ledger
                        else None
                    ),
                    "model_routing_gemma_agent_count": (
                        model_routing_ledger.gemma_capable_agent_count
                        if model_routing_ledger
                        else None
                    ),
                    "provider_ops_artifact_id": (
                        str(provider_operations_ledger.ledger_artifact_id)
                        if provider_operations_ledger
                        and provider_operations_ledger.ledger_artifact_id
                        else None
                    ),
                    "provider_smoke_artifact_id": (
                        str(provider_smoke_ledger.ledger_artifact_id)
                        if provider_smoke_ledger
                        and provider_smoke_ledger.ledger_artifact_id
                        else None
                    ),
                    "provider_smoke_status": (
                        provider_smoke_ledger.status if provider_smoke_ledger else None
                    ),
                    "provider_smoke_blocked_count": (
                        provider_smoke_ledger.blocked_count
                        if provider_smoke_ledger
                        else None
                    ),
                    "provider_smoke_failed_count": (
                        provider_smoke_ledger.failed_count
                        if provider_smoke_ledger
                        else None
                    ),
                    "provider_smoke_not_run_count": (
                        provider_smoke_ledger.not_run_count
                        if provider_smoke_ledger
                        else None
                    ),
                    "provider_operation_count": (
                        provider_operations_ledger.provider_operation_count
                        if provider_operations_ledger
                        else None
                    ),
                    "provider_fallback_count": (
                        provider_operations_ledger.provider_fallback_count
                        if provider_operations_ledger
                        else None
                    ),
                    "provider_policy_denial_count": (
                        provider_operations_ledger.policy_denial_count
                        if provider_operations_ledger
                        else None
                    ),
                    "realtime_dialogue_artifact_id": (
                        str(realtime_dialogue_ledger.ledger_artifact_id)
                        if realtime_dialogue_ledger
                        and realtime_dialogue_ledger.ledger_artifact_id
                        else None
                    ),
                    "realtime_dialogue_status": (
                        realtime_dialogue_ledger.status
                        if realtime_dialogue_ledger
                        else None
                    ),
                    "realtime_dialogue_turn_count": (
                        realtime_dialogue_ledger.turn_count
                        if realtime_dialogue_ledger
                        else None
                    ),
                    "realtime_dialogue_pending_followup_count": (
                        len(realtime_dialogue_ledger.pending_followup_task_ids)
                        if realtime_dialogue_ledger
                        else None
                    ),
                    "realtime_dialogue_unacknowledged_interruption_count": (
                        len(
                            realtime_dialogue_ledger.unacknowledged_interruption_turn_ids
                        )
                        if realtime_dialogue_ledger
                        else None
                    ),
                    "feedback_resolution_artifact_id": (
                        str(feedback_resolution_ledger.ledger_artifact_id)
                        if feedback_resolution_ledger
                        and feedback_resolution_ledger.ledger_artifact_id
                        else None
                    ),
                    "feedback_resolution_status": (
                        feedback_resolution_ledger.status
                        if feedback_resolution_ledger
                        else None
                    ),
                    "feedback_resolution_open_count": (
                        feedback_resolution_ledger.open_feedback_count
                        if feedback_resolution_ledger
                        else None
                    ),
                    "feedback_resolution_pending_task_count": (
                        feedback_resolution_ledger.pending_linked_task_count
                        if feedback_resolution_ledger
                        else None
                    ),
                    "foundation_audit_status": (
                        foundation_audit.status.value if foundation_audit else None
                    ),
                    "foundation_audit_artifact_id": (
                        str(foundation_audit.audit_artifact_id)
                        if foundation_audit and foundation_audit.audit_artifact_id
                        else None
                    ),
                    "foundation_audit_completion_score": (
                        foundation_audit.completion_score
                        if foundation_audit
                        else None
                    ),
                    "foundation_audit_fail_count": (
                        foundation_audit.fail_count if foundation_audit else None
                    ),
                    "foundation_audit_needs_attention_count": (
                        foundation_audit.needs_attention_count
                        if foundation_audit
                        else None
                    ),
                    "foundation_audit_remediation_count": (
                        foundation_audit.remediation_count
                        if foundation_audit
                        else None
                    ),
                    "foundation_audit_blocking_remediation_count": (
                        foundation_audit.blocking_remediation_count
                        if foundation_audit
                        else None
                    ),
                    "run_replay_artifact_id": (
                        str(run_replay_ledger.replay_artifact_id)
                        if run_replay_ledger and run_replay_ledger.replay_artifact_id
                        else None
                    ),
                    "run_replay_event_count": (
                        run_replay_ledger.replay_event_count
                        if run_replay_ledger
                        else None
                    ),
                    "run_replay_latest_event_id": (
                        run_replay_ledger.latest_event_id
                        if run_replay_ledger
                        else None
                    ),
                    "interactive_note_uri": (
                        interactive_note.uri if interactive_note else None
                    ),
                    "skipped_steps": skipped_steps,
                },
            )
        )

        completed_steps = [
            name
            for name, value in {
                "checkpoint": checkpoint,
                "runtime_health": runtime_health,
                "research_freshness": research_freshness,
                "retrieval_quality": retrieval_quality,
                "a2a_collaboration_graph": a2a_collaboration_graph,
                "open_feedback": open_feedback_items if open_feedback_items else None,
                "research_refresh_cycle": research_refresh_cycle,
                "worker_cycle": worker_cycle,
                "multimodal_followup_cycle": multimodal_followup_cycle,
                "media_production": media_production,
                "distribution_package": distribution_package,
                "source_ledger": source_ledger,
                "guardrail_audit": guardrail_audit,
                "publish_readiness": publish_readiness,
                "artifact_index": artifact_index,
                "work_plan": work_plan,
                "sync_pulse": sync_pulse,
                "context_packet_artifact": context_packet_artifact,
                "skill_usage_ledger": skill_usage_ledger,
                "model_routing_ledger": model_routing_ledger,
                "provider_smoke_ledger": provider_smoke_ledger,
                "provider_operations_ledger": provider_operations_ledger,
                "realtime_dialogue_ledger": realtime_dialogue_ledger,
                "feedback_resolution_ledger": feedback_resolution_ledger,
                "foundation_audit": foundation_audit,
                "run_replay_ledger": run_replay_ledger,
                "obsidian_memory_summary": obsidian_memory_summary,
                "interactive_note": interactive_note,
            }.items()
            if value is not None
        ]
        return AutonomousStudioPassResult(
            run_id=run_id,
            checkpoint=checkpoint,
            runtime_health=runtime_health,
            research_freshness=research_freshness,
            retrieval_quality=retrieval_quality,
            a2a_collaboration_graph=a2a_collaboration_graph,
            open_feedback_count=len(open_feedback_items),
            open_feedback_item_ids=[
                feedback.feedback_id for feedback in open_feedback_items
            ],
            research_refresh_cycle=research_refresh_cycle,
            worker_cycle=worker_cycle,
            multimodal_followup_cycle=multimodal_followup_cycle,
            media_production=media_production,
            distribution_package=distribution_package,
            source_ledger=source_ledger,
            guardrail_audit=guardrail_audit,
            publish_readiness=publish_readiness,
            artifact_index=artifact_index,
            work_plan=work_plan,
            sync_pulse=sync_pulse,
            context_packet_artifact=context_packet_artifact,
            skill_usage_ledger=skill_usage_ledger,
            model_routing_ledger=model_routing_ledger,
            provider_smoke_ledger=provider_smoke_ledger,
            provider_operations_ledger=provider_operations_ledger,
            realtime_dialogue_ledger=realtime_dialogue_ledger,
            feedback_resolution_ledger=feedback_resolution_ledger,
            foundation_audit=foundation_audit,
            run_replay_ledger=run_replay_ledger,
            obsidian_memory_summary=obsidian_memory_summary,
            interactive_note=interactive_note,
            skipped_steps=skipped_steps,
            event_id=completed.event_id,
            summary=(
                f"Autonomous studio pass completed {len(completed_steps)} "
                f"step(s): {', '.join(completed_steps) or 'none'}."
            ),
        )

    async def _build_context_packet_artifact(
        self,
        *,
        run,
        request: AutonomousStudioPassRequest,
        refresh_reason: str | None = None,
    ) -> ArtifactRecord:
        target_agent_id = request.context_packet_agent_id
        memory_results = await self._store.search_memories(
            agent_id=target_agent_id,
            run_id=run.run_id,
            include_global_memories=True,
            query_embedding=None,
            limit=10,
        )
        recent_events = await self._store.list_events(
            run.run_id,
            limit=request.context_packet_event_limit,
        )
        project_memory_retrieval = await ProjectMemoryRetrievalWorkflow(
            self._store
        ).retrieve(
            run.run_id,
            ProjectMemoryRetrievalRequest(
                query=run.goal,
                agent_id=target_agent_id,
                include_global_memories=True,
                seed_limit=5,
                memory_limit=10,
                graph_depth=1,
                record_artifact=False,
            ),
        )
        context_payload = build_context_engineering_payload(
            run=run,
            conversation_turns=await self._store.list_conversation_turns(run.run_id),
            agent_messages=await self._store.list_agent_messages(
                run.run_id,
                agent_id=target_agent_id,
            ),
            recent_events=recent_events,
            sources=await self._store.list_sources(run.run_id),
            claims=await self._store.list_claims(run.run_id),
            artifacts=await self._store.list_artifacts(run.run_id),
            guardrail_audits=await self._store.list_guardrail_audits(run.run_id),
            feedback_items=await self._store.list_feedback(run.run_id),
            memories=[
                MemorySearchResult(memory=memory, distance=distance)
                for memory, distance in memory_results
            ],
            agent_id=target_agent_id,
            max_manifest_items=request.context_packet_max_manifest_items,
            max_context_tokens=request.context_packet_max_context_tokens,
            project_memory_retrieval=project_memory_retrieval_digest(
                project_memory_retrieval
            ),
        )
        artifact_id = uuid4()
        artifact = ArtifactRecord(
            artifact_id=artifact_id,
            run_id=run.run_id,
            artifact_type=ArtifactType.CONTEXT_PACKET,
            title=(
                "Autonomous pass context packet"
                if target_agent_id is None
                else f"Autonomous pass context packet: {target_agent_id}"
            ),
            uri=(
                f"artifact://runs/{run.run_id}/context-packets/"
                f"{artifact_id}"
            ),
            content={
                "target_agent_id": target_agent_id,
                "source_workflow": "autonomous_studio_pass_v1",
                "refresh_reason": refresh_reason,
                "summary": context_payload["summary"],
                "context_manifest": [
                    item.model_dump(mode="json")
                    for item in context_payload["context_manifest"]
                ],
                "context_risks": [
                    risk.model_dump(mode="json")
                    for risk in context_payload["context_risks"]
                ],
                "recommended_fetches": context_payload["recommended_fetches"],
                "source_evidence": context_payload["source_evidence"],
                "recent_events": [
                    event.model_dump(mode="json") for event in recent_events
                ],
            },
            provenance={
                "workflow": "autonomous_context_packet_v1",
                "agent_id": "context-engineering-agent",
                "target_agent_id": target_agent_id,
                "generation_mode": "deterministic_context_engineering",
                "source_workflow": "autonomous_studio_pass_v1",
            },
            revision_history=[
                {
                    "actor": "context-engineering-agent",
                    "workflow": "autonomous_context_packet_v1",
                    "note": (
                        "Created a budgeted context packet during an autonomous "
                        "studio pass so resumed agents have a compact handoff."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(artifact)
        await self._store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=artifact.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="context_packet_artifact_created",
                actor="context-engineering-agent",
                payload={
                    "artifact_id": str(artifact.artifact_id),
                    "target_agent_id": target_agent_id,
                    "source_workflow": "autonomous_studio_pass_v1",
                    "refresh_reason": refresh_reason,
                    "context_manifest_items": context_payload["summary"][
                        "context_manifest_items"
                    ],
                    "context_risk_count": context_payload["summary"][
                        "context_risk_count"
                    ],
                    "recommended_fetches": context_payload["summary"][
                        "recommended_fetches"
                    ],
                },
            )
        )
        return artifact

    async def _export_memory_summary_to_obsidian(
        self,
        *,
        run,
        request: AutonomousStudioPassRequest,
        context_packet_artifact: ArtifactRecord,
    ) -> ArtifactRecord:
        if self._obsidian_vault_path is None:
            raise AutonomousStudioPassError("Obsidian vault path is not configured.")

        target_agent_id = (
            request.memory_summary_agent_id
            or request.context_packet_agent_id
            or "context-engineering-agent"
        )
        memory_results = await self._store.search_memories(
            agent_id=target_agent_id,
            run_id=run.run_id,
            include_global_memories=True,
            query_embedding=None,
            limit=request.memory_summary_limit,
        )
        context_summary = context_packet_artifact.content.get("summary") or {}
        memory_health = context_summary.get("memory_health") or {}
        context_risks = context_packet_artifact.content.get("context_risks") or []
        memory_risks = [
            risk
            for risk in context_risks
            if risk.get("risk_type")
            in {
                "stale_project_memories",
                "low_confidence_project_memories",
                "conflicting_project_memories",
            }
        ]
        recommended_fetches = context_packet_artifact.content.get(
            "recommended_fetches",
            [],
        )
        memory_rows = _memory_summary_rows(memory_results, memory_health)

        note_dir = (
            self._obsidian_vault_path
            / "output"
            / "reports"
            / "autonomous-memory-summaries"
            / str(run.run_id)
        )
        note_dir.mkdir(parents=True, exist_ok=True)
        note_path = note_dir / "memory-summary.md"
        note_path.write_text(
            _render_autonomous_memory_summary_note(
                run=run,
                target_agent_id=target_agent_id,
                context_packet_artifact=context_packet_artifact,
                memory_rows=memory_rows,
                memory_health=memory_health,
                memory_risks=memory_risks,
                recommended_fetches=recommended_fetches,
            ),
            encoding="utf-8",
        )

        relative_note_path = note_path.relative_to(self._obsidian_vault_path)
        uri = f"obsidian://agent-studio/{relative_note_path.as_posix()}"
        artifact = ArtifactRecord(
            run_id=run.run_id,
            artifact_type=ArtifactType.OBSIDIAN_NOTE,
            title="Autonomous memory summary",
            uri=uri,
            content={
                "format": "obsidian_autonomous_memory_summary",
                "note_kind": "autonomous_memory_summary",
                "vault_path": str(self._obsidian_vault_path),
                "relative_path": relative_note_path.as_posix(),
                "target_agent_id": target_agent_id,
                "memory_count": len(memory_rows),
                "memory_health": memory_health,
                "risk_types": [
                    risk.get("risk_type")
                    for risk in memory_risks
                    if risk.get("risk_type")
                ],
                "source_context_packet_artifact_id": str(
                    context_packet_artifact.artifact_id
                ),
            },
            provenance={
                "workflow": "autonomous_memory_summary_export_v1",
                "agent_id": "interactive-note-taking-agent",
                "target_agent_id": target_agent_id,
                "source_workflow": "autonomous_studio_pass_v1",
                "source_context_packet_artifact_id": str(
                    context_packet_artifact.artifact_id
                ),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            revision_history=[
                {
                    "actor": "interactive-note-taking-agent",
                    "workflow": "autonomous_memory_summary_export_v1",
                    "note": (
                        "Exported a compact memory summary from an autonomous "
                        "pass context packet and selected project memories."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(artifact)
        await self._store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=artifact.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="obsidian_memory_summary_exported",
                actor="interactive-note-taking-agent",
                payload={
                    "artifact_id": str(artifact.artifact_id),
                    "uri": uri,
                    "file_path": str(note_path),
                    "target_agent_id": target_agent_id,
                    "memory_count": len(memory_rows),
                    "memory_health": memory_health,
                    "risk_types": artifact.content["risk_types"],
                    "source_context_packet_artifact_id": str(
                        context_packet_artifact.artifact_id
                    ),
                },
            )
        )
        return artifact

    async def _build_artifact_index(self, run_id: UUID):
        message = AgentMessage(
            run_id=run_id,
            sender_agent_id="product-manager",
            recipient_agent_id="artifact-librarian",
            task_type="build_artifact_index",
            payload={
                "event_limit": 1000,
                "refresh_reason": "autonomous_quality_gates_completed",
            },
        )
        await self._store.record_agent_message(message)
        return await AgentWorker(
            self._store,
            artifacts_root=self._artifacts_root,
        ).run(
            "artifact-librarian",
            AgentWorkerRunRequest(
                run_id=run_id,
                max_tasks=25,
                use_gemma=False,
                fail_on_provider_error=False,
            ),
        )

    async def _latest_artifact_index_payload(self, run_id: UUID) -> dict[str, object]:
        artifacts = await self._store.list_artifacts(run_id)
        for artifact in reversed(artifacts):
            if artifact.artifact_type != ArtifactType.ARTIFACT_INDEX:
                continue
            handoff = artifact.content.get("publishing_handoff") or {}
            if not isinstance(handoff, dict):
                handoff = {}
            return {
                "artifact_index_artifact_id": str(artifact.artifact_id),
                "publishing_handoff_status": handoff.get("status"),
                "publishable_artifact_count": handoff.get(
                    "publishable_artifact_count"
                ),
            }
        return {}

    async def _pending_multimodal_followups(self, run_id: UUID):
        return [
            message
            for message in await self._store.list_agent_messages(run_id)
            if message.status == AgentTaskStatus.ACCEPTED
            and message.payload.get("workflow") == "multimodal_review_followup_v1"
        ]

    async def _refresh_research_sources(
        self,
        *,
        run_id: UUID,
        topic: str,
        request: AutonomousStudioPassRequest,
    ):
        message = AgentMessage(
            run_id=run_id,
            sender_agent_id="agent-harness-engineer",
            recipient_agent_id="web-research-agent",
            task_type="autonomous_research_source_refresh",
            payload={
                "topic": topic,
                "freshness": "current",
                "workflow": "autonomous_research_source_refresh_v1",
            },
        )
        await self._store.record_agent_message(message)
        await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="agent_message_accepted",
                actor=message.sender_agent_id,
                payload=public_a2a_message_event_payload(message),
            )
        )
        return await AgentWorker(
            self._store,
            self._services,
            artifacts_root=self._artifacts_root,
        ).run(
            "web-research-agent",
            AgentWorkerRunRequest(
                run_id=run_id,
                max_tasks=1,
                use_gemma=request.use_gemma,
                fail_on_provider_error=request.fail_on_provider_error,
            ),
        )

    async def _media_request_for_current_content(
        self, run_id: UUID
    ) -> tuple[MediaProductionRequest | None, str | None]:
        artifacts = await self._store.list_artifacts(run_id)
        current_content = _leaf_content_artifacts(artifacts)
        if not current_content:
            return None, "no_current_content_artifacts"

        content_ids = {str(artifact.artifact_id) for artifact in current_content}
        current_media_types = {
            artifact.artifact_type
            for artifact in artifacts
            if artifact.artifact_type in MEDIA_PLAN_TYPES
            and artifact.provenance.get("workflow") == "media_production_v1"
            and set(artifact.provenance.get("source_artifact_ids", [])) == content_ids
        }
        missing_types = MEDIA_PLAN_TYPES - current_media_types
        if not missing_types:
            return None, "media_plans_already_current"

        return (
            MediaProductionRequest(
                target_artifact_ids=[artifact.artifact_id for artifact in current_content],
                include_image_prompt=ArtifactType.IMAGE in missing_types,
                include_audio_brief=ArtifactType.AUDIO in missing_types,
                include_video_storyboard=ArtifactType.VIDEO in missing_types,
            ),
            None,
        )

    async def _distribution_request_for_current_content(
        self, run_id: UUID
    ) -> tuple[DistributionPackageRequest | None, str | None]:
        artifacts = await self._store.list_artifacts(run_id)
        current_content = _leaf_content_artifacts(artifacts)
        if not current_content:
            return None, "no_current_content_artifacts_for_distribution"

        content_ids = {str(artifact.artifact_id) for artifact in current_content}
        for artifact in artifacts:
            if (
                artifact.artifact_type == ArtifactType.SOCIAL_PACKAGE
                and artifact.provenance.get("workflow") == "distribution_package_v1"
                and set(artifact.provenance.get("source_artifact_ids", []))
                == content_ids
            ):
                return None, "distribution_package_already_current"

        return (
            DistributionPackageRequest(
                target_artifact_ids=[artifact.artifact_id for artifact in current_content]
            ),
            None,
        )


def _leaf_content_artifacts(artifacts: list[ArtifactRecord]) -> list[ArtifactRecord]:
    parent_ids = set()
    for artifact in artifacts:
        parent_id = artifact.provenance.get("parent_artifact_id")
        if isinstance(parent_id, str):
            try:
                parent_ids.add(UUID(parent_id))
            except ValueError:
                continue
    return [
        artifact
        for artifact in artifacts
        if artifact.artifact_type in SOURCE_CONTENT_TYPES
        and artifact.artifact_id not in parent_ids
    ]


def _search_provider_is_configured(search_provider) -> bool:
    if search_provider is None:
        return False
    api_key = getattr(search_provider, "_api_key", ...)
    if api_key is None:
        return False
    return True


def _memory_summary_rows(memory_results, memory_health: dict[str, object]):
    stale_ids = {str(memory_id) for memory_id in memory_health.get("stale_memory_ids", [])}
    low_confidence_ids = {
        str(memory_id)
        for memory_id in memory_health.get("low_confidence_memory_ids", [])
    }
    conflict_ids = {
        str(memory_id)
        for pair in memory_health.get("conflict_pairs", [])
        for memory_id in pair.get("memory_ids", [])
    }
    rows = []
    for memory, distance in memory_results:
        metadata = memory.metadata or {}
        memory_id = str(memory.memory_id)
        rows.append(
            {
                "memory_id": memory_id,
                "agent_id": memory.agent_id,
                "memory_kind": str(
                    metadata.get("project_memory_kind") or memory.memory_kind
                ),
                "memory_scope": str(
                    metadata.get("memory_scope")
                    or ("run" if memory.run_id else "global")
                ),
                "confidence": str(metadata.get("confidence") or "medium"),
                "created_at": memory.created_at.isoformat(),
                "distance": distance,
                "flags": _memory_summary_flags(
                    memory_id,
                    stale_ids=stale_ids,
                    low_confidence_ids=low_confidence_ids,
                    conflict_ids=conflict_ids,
                ),
                "tags": [
                    str(tag)
                    for tag in metadata.get("tags", [])
                    if str(tag).strip()
                ],
                "target_wiki_notes": [
                    str(note)
                    for note in metadata.get("target_wiki_notes", [])
                    if str(note).strip()
                ],
                "content": memory.content,
            }
        )
    return rows


def _memory_summary_flags(
    memory_id: str,
    *,
    stale_ids: set[str],
    low_confidence_ids: set[str],
    conflict_ids: set[str],
) -> list[str]:
    flags = []
    if memory_id in stale_ids:
        flags.append("stale")
    if memory_id in low_confidence_ids:
        flags.append("low-confidence")
    if memory_id in conflict_ids:
        flags.append("conflict")
    return flags


def _render_autonomous_memory_summary_note(
    *,
    run,
    target_agent_id: str,
    context_packet_artifact: ArtifactRecord,
    memory_rows: list[dict[str, object]],
    memory_health: dict[str, object],
    memory_risks: list[dict[str, object]],
    recommended_fetches: list[str],
) -> str:
    updated = datetime.now(timezone.utc).date().isoformat()
    lines = [
        "---",
        "type: autonomous-memory-summary",
        "project: agent-studio",
        "status: generated",
        f"updated: {updated}",
        f"run_id: {run.run_id}",
        f"target_agent_id: {target_agent_id}",
        f"source_context_packet_artifact_id: {context_packet_artifact.artifact_id}",
        "owners:",
        "  - interactive-note-taking-agent",
        "  - context-engineering-agent",
        "---",
        "",
        "# Autonomous Memory Summary",
        "",
        "## Source Run",
        "",
        f"- Run: `{run.run_id}`",
        f"- Goal: {_markdown_inline(run.goal)}",
        f"- Target agent: `{target_agent_id}`",
        f"- Context packet artifact: `{context_packet_artifact.artifact_id}`",
        "",
        "## Memory Health",
        "",
        f"- Retrieved memories: {len(memory_rows)}",
        f"- Project memories: {memory_health.get('project_memory_count', 0)}",
        f"- Stale memories: {memory_health.get('stale_memory_count', 0)}",
        (
            "- Low-confidence memories: "
            f"{memory_health.get('low_confidence_memory_count', 0)}"
        ),
        f"- Conflicting memory pairs: {memory_health.get('conflict_count', 0)}",
        "",
        "## Selected Memories",
        "",
    ]
    if memory_rows:
        lines.extend(
            [
                "| Kind | Scope | Confidence | Flags | Excerpt |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for row in memory_rows:
            flags = ", ".join(row["flags"]) if row["flags"] else "clear"
            lines.append(
                "| "
                + " | ".join(
                    [
                        _markdown_table_cell(str(row["memory_kind"])),
                        _markdown_table_cell(str(row["memory_scope"])),
                        _markdown_table_cell(str(row["confidence"])),
                        _markdown_table_cell(flags),
                        _markdown_table_cell(_excerpt(str(row["content"]), 180)),
                    ]
                )
                + " |"
            )
    else:
        lines.append("No project memories were retrieved for this target agent.")

    lines.extend(["", "## Memory Risks", ""])
    if memory_risks:
        for risk in memory_risks:
            lines.append(
                "- "
                + _markdown_inline(str(risk.get("risk_type", "memory_risk")))
                + ": "
                + _markdown_inline(str(risk.get("reason", "Review before use.")))
            )
    else:
        lines.append("No memory health risks were reported in the context packet.")

    lines.extend(["", "## Recommended Follow-up", ""])
    if recommended_fetches:
        for fetch in recommended_fetches:
            lines.append(f"- {_markdown_inline(fetch)}")
    else:
        lines.append("No follow-up fetches were recorded.")

    lines.extend(
        [
            "",
            "## Policy",
            "",
            (
                "This output is a compact run handoff. It can inform future work, "
                "but it does not rewrite canonical wiki notes by itself."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _markdown_table_cell(value: str) -> str:
    return _markdown_inline(value).replace("|", "\\|")


def _markdown_inline(value: str) -> str:
    return " ".join(value.replace("\n", " ").split())


def _excerpt(value: str, max_chars: int) -> str:
    normalized = _markdown_inline(value)
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."
