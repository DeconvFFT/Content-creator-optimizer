import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import NAMESPACE_URL, UUID, uuid5

from all_about_llms.agents import (
    AGENT_ROSTER,
    SKILL_CARDS,
    get_agent_card,
    skill_cards_for_agent,
)
from all_about_llms.contracts import (
    AgentMessage,
    AgentTaskStatus,
    ArtifactRecord,
    ArtifactType,
    AgentWorkerCycleRequest,
    AgentWorkerCycleResult,
    AgentWorkerRunRequest,
    AgentWorkerRunResult,
    AgentWorkerTaskResult,
    AutonomousStudioPassRequest,
    ClaimRecord,
    ClaimSupportStatus,
    DistributionPackageRequest,
    FeedbackItem,
    FeedbackResolutionLedgerRequest,
    FeedbackStatus,
    GuardrailAuditStatus,
    GuardrailAuditRequest,
    InteractiveRunNoteRequest,
    MemorySearchResult,
    ObsidianMemoryPromotionRequest,
    ObsidianReviewNoteRequest,
    ProjectMemoryRecordRequest,
    ProjectMemoryRetrievalRequest,
    RealtimeDialogueLedgerRequest,
    ResearchFreshnessLedgerRequest,
    RetrievalQualityLedgerRequest,
    ReviewDecision,
    ReviewDecisionStatus,
    RunEvent,
    RunResumePlanRequest,
    RuntimeHealthLedgerRequest,
    SourceFreshnessStatus,
    SourceQualityStatus,
    SourceLedgerSnapshotRequest,
    RunStatus,
    RunSyncPulseRequest,
    RunWorkPlanRequest,
    SourceRecord,
    WorkerProfileHeartbeatResult,
    WorkerProfileExecutionMode,
    WorkerProfileStatus,
    WorkerSchedulerRunRequest,
    WorkerSchedulerRunResult,
)
from all_about_llms.orchestration.services import ContentWorkflowServices
from all_about_llms.orchestration.distribution_package import (
    DistributionPackageWorkflow,
    NoArtifactsForDistributionPackageError,
)
from all_about_llms.orchestration.interactive_notes import InteractiveRunNoteWorkflow
from all_about_llms.orchestration.obsidian_memory import (
    ObsidianMemoryPromotionWorkflow,
)
from all_about_llms.orchestration.obsidian_notes import ObsidianReviewNoteWorkflow
from all_about_llms.orchestration.project_memory import ProjectMemoryWorkflow
from all_about_llms.orchestration.project_memory_retrieval import (
    ProjectMemoryRetrievalWorkflow,
    project_memory_retrieval_digest,
)
from all_about_llms.orchestration.run_resume import RunResumeWorkflow
from all_about_llms.orchestration.runtime_health import RuntimeHealthLedgerWorkflow
from all_about_llms.orchestration.research_freshness import (
    ResearchFreshnessLedgerWorkflow,
)
from all_about_llms.orchestration.retrieval_evidence import (
    accepted_retrieval_evidence_by_source,
    latest_retrieval_quality_ledger,
    retrieval_evidence_payload,
    retrieval_evidence_payloads_for_source_ids,
)
from all_about_llms.orchestration.retrieval_quality import (
    RetrievalQualityLedgerWorkflow,
)
from all_about_llms.orchestration.source_ledger import SourceLedgerWorkflow
from all_about_llms.orchestration.context_engineering import (
    build_context_engineering_payload,
)
from all_about_llms.orchestration.a2a_projection import (
    public_a2a_context_packet_event_payload,
    public_a2a_dependency_waiting_event_payload,
    public_a2a_message_event_payload,
    public_a2a_recovered_event_payload,
    public_a2a_retry_exhausted_event_payload,
    public_a2a_skill_invocation_event_payload,
    public_a2a_status_event_payload,
)
from all_about_llms.orchestration.a2a_trace import append_handoff_trace
from all_about_llms.orchestration.feedback_routing import (
    FOCUS_AGENT_MAP,
    KEYWORD_AGENT_MAP,
)
from all_about_llms.orchestration.source_quality import evaluate_source_quality
from all_about_llms.orchestration.tool_policy import (
    require_model_allowed,
    require_tool_allowed,
)
from all_about_llms.orchestration.sync_pulse import RunSyncPulseWorkflow
from all_about_llms.orchestration.work_plan import RunWorkPlanWorkflow
from all_about_llms.providers.interfaces import (
    GemmaRequest,
    ProviderConfigurationError,
    RerankCandidate,
    RerankRequest,
    RerankResult,
    SearchRequest,
    SearchResult,
)
from all_about_llms.providers.rerank import DeterministicRerankerProvider
from all_about_llms.orchestration.feedback_resolution import (
    FeedbackResolutionLedgerWorkflow,
)
from all_about_llms.orchestration.realtime_dialogue import (
    RealtimeDialogueLedgerWorkflow,
)


class AgentWorkerError(RuntimeError):
    """Base error for durable agent worker execution."""


class AgentWorkerRunNotFoundError(AgentWorkerError):
    """Raised when a worker is pointed at a missing run."""


class AgentWorkerAgentNotFoundError(AgentWorkerError):
    """Raised when a worker is pointed at an unknown agent."""


class WorkerProfileNotFoundError(AgentWorkerError):
    """Raised when a saved worker profile is missing."""


DEFAULT_WORKER_AGENT_IDS = [
    "realtime-conversation-host",
    "web-research-agent",
    "retrieval-intelligence-agent",
    "knowledge-graph-curator-agent",
    "source-ledger-agent",
    "context-engineering-agent",
    "agent-harness-engineer",
    "forward-deployed-engineer",
    "principal-software-engineer",
    "backend-platform-engineer",
    "frontend-experience-engineer",
    "scalability-reliability-engineer",
    "inference-systems-engineer",
    "claim-verification-agent",
    "a2a-protocol-agent",
    "intent-router",
    "content-strategist",
    "data-analyst-agent",
    "eli5-short-form-writer",
    "substack-essay-writer",
    "script-doctor",
    "platform-optimization-agent",
    "influencer-strategy-agent",
    "outreach-agent",
    "guardrails-agent",
    "lead-ui-ux-designer",
    "interactive-systems-designer",
    "visual-director",
    "image-generation-agent",
    "audio-producer",
    "video-reel-producer",
    "editor-in-chief",
    "critic-reviewer-agent",
    "artifact-librarian",
    "interactive-note-taking-agent",
    "product-manager",
    "sprint-progress-agent",
    "observability-agent",
]

CONCRETE_WORKER_EXECUTOR_AGENT_IDS = {
    "realtime-conversation-host",
    "web-research-agent",
    "retrieval-intelligence-agent",
    "knowledge-graph-curator-agent",
    "source-ledger-agent",
    "context-engineering-agent",
    "agent-harness-engineer",
    "forward-deployed-engineer",
    "principal-software-engineer",
    "backend-platform-engineer",
    "frontend-experience-engineer",
    "scalability-reliability-engineer",
    "inference-systems-engineer",
    "claim-verification-agent",
    "a2a-protocol-agent",
    "intent-router",
    "content-strategist",
    "data-analyst-agent",
    "eli5-short-form-writer",
    "substack-essay-writer",
    "script-doctor",
    "platform-optimization-agent",
    "influencer-strategy-agent",
    "outreach-agent",
    "guardrails-agent",
    "lead-ui-ux-designer",
    "interactive-systems-designer",
    "visual-director",
    "image-generation-agent",
    "audio-producer",
    "video-reel-producer",
    "editor-in-chief",
    "critic-reviewer-agent",
    "artifact-librarian",
    "interactive-note-taking-agent",
    "product-manager",
    "sprint-progress-agent",
    "observability-agent",
}

CLAIM_VERIFICATION_TASK_TYPES = {
    "verify_content_claims",
    "verify_conversation_claims",
    "verify_source_refresh_claims",
}
MAX_WEB_RESEARCH_SEARCH_QUERIES = 5

PROJECT_MEMORY_CONFIRMATION_GATE_STATUSES = {
    "graph_only_review",
    "needs_precision_review",
    "needs_recall_repair",
    "regressed",
}

PROJECT_MEMORY_CONFIRMATION_GATE = "project_memory_policy_confirmation"

ARCHITECTURE_REVIEW_AGENT_PROFILES: dict[str, dict[str, Any]] = {
    "principal-software-engineer": {
        "title": "Principal architecture review",
        "workflow": "principal_architecture_review_worker_v1",
        "generation_mode": "principal_architecture_review_worker",
        "deterministic_generation_mode": "deterministic_architecture_review",
        "summary_label": "architecture review",
        "focus": [
            "service boundaries",
            "durability",
            "worker coverage",
            "provider boundaries",
            "feedback gates",
        ],
        "revision_note": (
            "Reviewed architecture boundaries, durability, worker coverage, "
            "provider boundaries, feedback gates, and engineering next actions."
        ),
    },
    "backend-platform-engineer": {
        "title": "Backend platform review",
        "workflow": "backend_platform_review_worker_v1",
        "generation_mode": "backend_platform_review_worker",
        "deterministic_generation_mode": "deterministic_backend_platform_review",
        "summary_label": "backend platform review",
        "focus": [
            "FastAPI service contracts",
            "Postgres and pgvector writes",
            "migrations",
            "async APIs",
            "data consistency",
        ],
        "revision_note": (
            "Reviewed FastAPI service contracts, Postgres/pgvector durability, "
            "migration boundaries, async API behavior, and backend consistency."
        ),
    },
    "scalability-reliability-engineer": {
        "title": "Scalability and reliability review",
        "workflow": "scalability_reliability_review_worker_v1",
        "generation_mode": "scalability_reliability_review_worker",
        "deterministic_generation_mode": "deterministic_scalability_reliability_review",
        "summary_label": "scalability/reliability review",
        "focus": [
            "SLOs",
            "capacity",
            "backpressure",
            "worker scheduling",
            "graceful degradation",
            "always-on safety",
        ],
        "revision_note": (
            "Reviewed SLOs, capacity, backpressure, worker scheduling, "
            "graceful degradation, and always-on safety gates."
        ),
    },
    "inference-systems-engineer": {
        "title": "Inference systems review",
        "workflow": "inference_systems_review_worker_v1",
        "generation_mode": "inference_systems_review_worker",
        "deterministic_generation_mode": "deterministic_inference_systems_review",
        "summary_label": "inference systems review",
        "focus": [
            "OpenRouter/LiveKit/Kokoro realtime boundaries",
            "legacy native-Gemma/HF context",
            "realtime audio boundaries",
            "model routing",
            "latency and cost budgets",
            "fallback policy",
            "provider smoke proof",
        ],
        "revision_note": (
            "Reviewed OpenRouter/LiveKit/Kokoro realtime provider boundaries, "
            "legacy native-Gemma/HF context, model "
            "routing, latency/cost budgets, fallback policy, and provider smoke proof."
        ),
    },
}

UX_REVIEW_AGENT_PROFILES: dict[str, dict[str, str]] = {
    "lead-ui-ux-designer": {
        "title": "Lead UI/UX review",
        "workflow": "lead_ui_ux_review_worker_v1",
        "generation_mode": "lead_ui_ux_review_worker",
        "deterministic_generation_mode": "deterministic_ux_review",
        "summary_label": "UX review",
    },
    "frontend-experience-engineer": {
        "title": "Frontend experience review",
        "workflow": "frontend_experience_review_worker_v1",
        "generation_mode": "frontend_experience_review_worker",
        "deterministic_generation_mode": "deterministic_frontend_experience_review",
        "summary_label": "frontend experience review",
    },
}


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


SOURCE_CONTENT_TYPES = {
    ArtifactType.POST,
    ArtifactType.REEL_SCRIPT,
    ArtifactType.SUBSTACK_ARTICLE,
}

SOURCE_REPAIR_ARTIFACT_TYPES = {
    ArtifactType.POST,
    ArtifactType.REEL_SCRIPT,
    ArtifactType.SUBSTACK_ARTICLE,
    ArtifactType.SOCIAL_PACKAGE,
    ArtifactType.GROWTH_STRATEGY,
    ArtifactType.VISUAL_BRIEF,
    ArtifactType.IMAGE,
    ArtifactType.AUDIO,
    ArtifactType.VIDEO,
}

SOURCE_DEPENDENT_ARTIFACT_TYPES = {
    ArtifactType.POST,
    ArtifactType.REEL_SCRIPT,
    ArtifactType.SUBSTACK_ARTICLE,
    ArtifactType.SOCIAL_PACKAGE,
    ArtifactType.GROWTH_STRATEGY,
    ArtifactType.DATA_BRIEF,
    ArtifactType.VISUAL_BRIEF,
    ArtifactType.IMAGE,
    ArtifactType.AUDIO,
    ArtifactType.VIDEO,
}

TARGETABLE_MULTIMODAL_CONTEXT_TYPES = {
    ArtifactType.MULTIMODAL_REVIEW,
    ArtifactType.VISUAL_BRIEF,
    ArtifactType.IMAGE,
    ArtifactType.AUDIO,
    ArtifactType.VIDEO,
    ArtifactType.CONTEXT_PACKET,
}

GROWTH_DISTRIBUTION_AGENTS = {
    "platform-optimization-agent",
    "influencer-strategy-agent",
    "outreach-agent",
}

CONTENT_WRITER_AGENTS = {
    "eli5-short-form-writer",
    "substack-essay-writer",
}


def _heartbeat_processed_tasks(*, cycle_result, autonomous_pass_result) -> int:
    processed_tasks = cycle_result.total_processed_tasks if cycle_result else 0
    if autonomous_pass_result is None:
        return processed_tasks
    if autonomous_pass_result.research_refresh_cycle is not None:
        processed_tasks += len(
            autonomous_pass_result.research_refresh_cycle.processed_tasks
        )
    if autonomous_pass_result.multimodal_followup_cycle is not None:
        processed_tasks += (
            autonomous_pass_result.multimodal_followup_cycle.total_processed_tasks
        )
    return processed_tasks


def _heartbeat_cycle_summary(cycle_result) -> dict[str, Any] | None:
    if cycle_result is None:
        return None
    return {
        "agent_ids": cycle_result.agent_ids,
        "rounds_completed": cycle_result.rounds_completed,
        "total_processed_tasks": cycle_result.total_processed_tasks,
        "idle": cycle_result.idle,
    }


def _heartbeat_autonomous_pass_summary(autonomous_pass_result) -> dict[str, Any] | None:
    if autonomous_pass_result is None:
        return None
    return {
        "event_id": autonomous_pass_result.event_id,
        "skipped_steps": autonomous_pass_result.skipped_steps,
        "runtime_health_status": (
            autonomous_pass_result.runtime_health.status
            if autonomous_pass_result.runtime_health
            else None
        ),
        "research_freshness_status": (
            autonomous_pass_result.research_freshness.status
            if autonomous_pass_result.research_freshness
            else None
        ),
        "publish_readiness_status": (
            autonomous_pass_result.publish_readiness.status
            if autonomous_pass_result.publish_readiness
            else None
        ),
        "retrieval_quality_status": (
            autonomous_pass_result.retrieval_quality.status
            if autonomous_pass_result.retrieval_quality
            else None
        ),
        "obsidian_memory_summary_artifact_id": (
            str(autonomous_pass_result.obsidian_memory_summary.artifact_id)
            if autonomous_pass_result.obsidian_memory_summary
            else None
        ),
        "artifact_index_processed_tasks": (
            len(autonomous_pass_result.artifact_index.processed_tasks)
            if autonomous_pass_result.artifact_index
            else None
        ),
    }


def _heartbeat_metrics_summary(
    *,
    autonomous_pass_result,
    context_packet_artifact,
) -> dict[str, Any]:
    return {
        "retrieval_quality": _heartbeat_retrieval_quality_metrics(
            autonomous_pass_result
        ),
        "memory_health": _heartbeat_memory_health_metrics(context_packet_artifact),
        "project_memory_retrieval": _heartbeat_project_memory_retrieval_metrics(
            context_packet_artifact
        ),
    }


def _heartbeat_retrieval_quality_metrics(autonomous_pass_result) -> dict[str, Any]:
    retrieval_quality = (
        autonomous_pass_result.retrieval_quality
        if autonomous_pass_result
        else None
    )
    skipped_steps = (
        autonomous_pass_result.skipped_steps if autonomous_pass_result else []
    )
    if retrieval_quality is None:
        return {
            "status": None,
            "candidate_count": 0,
            "accepted_candidate_count": 0,
            "accepted_candidate_ratio": None,
            "precision_risk_count": 0,
            "recall_gap_count": 0,
            "coverage_gap_count": 0,
            "graph_node_count": 0,
            "recommended_query_count": 0,
            "gate_blocked_pass": (
                "retrieval_quality_blocked_autonomous_pass" in skipped_steps
            ),
        }
    accepted_ratio = None
    if retrieval_quality.candidate_count:
        accepted_ratio = (
            retrieval_quality.accepted_candidate_count
            / retrieval_quality.candidate_count
        )
    return {
        "status": retrieval_quality.status.value,
        "candidate_count": retrieval_quality.candidate_count,
        "accepted_candidate_count": retrieval_quality.accepted_candidate_count,
        "accepted_candidate_ratio": accepted_ratio,
        "precision_risk_count": retrieval_quality.precision_risk_count,
        "recall_gap_count": retrieval_quality.recall_gap_count,
        "coverage_gap_count": retrieval_quality.coverage_gap_count,
        "graph_node_count": retrieval_quality.graph_node_count,
        "recommended_query_count": len(retrieval_quality.recommended_queries),
        "gate_blocked_pass": (
            "retrieval_quality_blocked_autonomous_pass" in skipped_steps
        ),
    }


def _heartbeat_memory_health_metrics(context_packet_artifact) -> dict[str, Any]:
    if context_packet_artifact is None:
        return {
            "memory_count": 0,
            "project_memory_count": 0,
            "stale_memory_count": 0,
            "low_confidence_memory_count": 0,
            "conflict_count": 0,
            "context_risk_count": 0,
        }
    summary = context_packet_artifact.content.get("summary") or {}
    memory_health = summary.get("memory_health") or {}
    return {
        "memory_count": memory_health.get("memory_count", 0),
        "project_memory_count": memory_health.get("project_memory_count", 0),
        "stale_memory_count": memory_health.get("stale_memory_count", 0),
        "low_confidence_memory_count": memory_health.get(
            "low_confidence_memory_count",
            0,
        ),
        "conflict_count": memory_health.get("conflict_count", 0),
        "context_risk_count": summary.get("context_risk_count", 0),
    }


def _heartbeat_project_memory_retrieval_metrics(context_packet_artifact) -> dict[str, Any]:
    if context_packet_artifact is None:
        return {
            "memory_count": 0,
            "seed_memory_count": 0,
            "related_memory_count": 0,
            "graph_edge_count": 0,
            "precision": None,
            "recall": None,
            "precision_risk_count": 0,
            "recall_gap_count": 0,
            "repeated_query_count": 0,
            "trend": None,
            "policy_status": "not_available",
        }
    summary = context_packet_artifact.content.get("summary") or {}
    retrieval = summary.get("project_memory_retrieval") or {}
    evaluation = retrieval.get("evaluation") or {}
    return {
        "memory_count": retrieval.get("memory_count", 0),
        "seed_memory_count": retrieval.get("seed_memory_count", 0),
        "related_memory_count": retrieval.get("related_memory_count", 0),
        "graph_edge_count": retrieval.get("graph_edge_count", 0),
        "precision": evaluation.get("precision"),
        "recall": evaluation.get("recall"),
        "precision_risk_count": evaluation.get("precision_risk_count", 0),
        "recall_gap_count": evaluation.get("recall_gap_count", 0),
        "repeated_query_count": evaluation.get("repeated_query_count", 0),
        "trend": evaluation.get("trend"),
        "policy_status": _project_memory_policy_status_from_digest(retrieval),
    }


def _scheduler_metrics_summary(heartbeat_results) -> dict[str, Any]:
    profile_metrics = [
        result.heartbeat_ledger_artifact.content.get("metrics", {})
        for result in heartbeat_results
        if result.heartbeat_ledger_artifact is not None
    ]
    retrieval_metrics = [
        metrics.get("retrieval_quality", {}) for metrics in profile_metrics
    ]
    memory_metrics = [metrics.get("memory_health", {}) for metrics in profile_metrics]
    project_memory_metrics = [
        metrics.get("project_memory_retrieval", {}) for metrics in profile_metrics
    ]
    return {
        "profile_metrics": profile_metrics,
        "retrieval_quality_blocked_profile_count": sum(
            1 for metrics in retrieval_metrics if metrics.get("status") == "blocked"
        ),
        "retrieval_quality_gate_blocked_profile_count": sum(
            1 for metrics in retrieval_metrics if metrics.get("gate_blocked_pass")
        ),
        "retrieval_quality_recall_gap_count": sum(
            int(metrics.get("recall_gap_count") or 0)
            for metrics in retrieval_metrics
        ),
        "retrieval_quality_coverage_gap_count": sum(
            int(metrics.get("coverage_gap_count") or 0)
            for metrics in retrieval_metrics
        ),
        "memory_stale_profile_count": sum(
            1
            for metrics in memory_metrics
            if int(metrics.get("stale_memory_count") or 0) > 0
        ),
        "memory_low_confidence_profile_count": sum(
            1
            for metrics in memory_metrics
            if int(metrics.get("low_confidence_memory_count") or 0) > 0
        ),
        "memory_conflict_profile_count": sum(
            1
            for metrics in memory_metrics
            if int(metrics.get("conflict_count") or 0) > 0
        ),
        "project_memory_retrieval_precision_risk_profile_count": sum(
            1
            for metrics in project_memory_metrics
            if int(metrics.get("precision_risk_count") or 0) > 0
        ),
        "project_memory_retrieval_recall_gap_profile_count": sum(
            1
            for metrics in project_memory_metrics
            if int(metrics.get("recall_gap_count") or 0) > 0
        ),
        "project_memory_retrieval_regressed_profile_count": sum(
            1
            for metrics in project_memory_metrics
            if metrics.get("trend") == "regressed"
        ),
        "project_memory_retrieval_no_seed_profile_count": sum(
            1
            for metrics in project_memory_metrics
            if int(metrics.get("memory_count") or 0) > 0
            and int(metrics.get("seed_memory_count") or 0) == 0
        ),
    }


def _project_memory_policy_status_from_digest(
    retrieval: dict[str, Any] | None,
) -> str:
    if not retrieval:
        return "not_available"
    if not retrieval.get("memory_count"):
        return "no_memory"
    evaluation = retrieval.get("evaluation") or {}
    if evaluation.get("trend") == "regressed":
        return "regressed"
    if int(evaluation.get("precision_risk_count") or 0) > 0:
        return "needs_precision_review"
    if int(retrieval.get("seed_memory_count") or 0) == 0:
        return "graph_only_review"
    if int(evaluation.get("recall_gap_count") or 0) > 0:
        return "needs_recall_repair"
    return "ready"


def _project_memory_policy_from_digest(
    retrieval: dict[str, Any] | None,
) -> dict[str, Any]:
    status = _project_memory_policy_status_from_digest(retrieval)
    evaluation = (retrieval or {}).get("evaluation") or {}
    instructions = []
    if status == "ready":
        instructions.append(
            "Use seed project memories as durable context for this agent task."
        )
    elif status == "no_memory":
        instructions.append(
            "Do not infer project policy from memory; retrieve source notes or ask for confirmation."
        )
    elif status == "graph_only_review":
        instructions.append(
            "Treat graph-neighbor memories as weak context until a seed memory is confirmed."
        )
    elif status == "needs_precision_review":
        instructions.append(
            "Review false-positive or graph-neighbor memories before applying them as policy."
        )
    elif status == "needs_recall_repair":
        instructions.append(
            "Treat retrieved memories as incomplete and inspect missing expected memories before final decisions."
        )
    elif status == "regressed":
        instructions.append(
            "Compare against the prior retrieval ledger before depending on this memory set."
        )
    return {
        "status": status,
        "apply_seed_memories_as_policy": status in {"ready", "needs_recall_repair"},
        "graph_neighbors_require_review": (
            int((retrieval or {}).get("related_memory_count") or 0) > 0
            or status in {"graph_only_review", "needs_precision_review"}
        ),
        "precision": evaluation.get("precision"),
        "recall": evaluation.get("recall"),
        "precision_risk_count": evaluation.get("precision_risk_count", 0),
        "recall_gap_count": evaluation.get("recall_gap_count", 0),
        "trend": evaluation.get("trend"),
        "repeated_query_count": evaluation.get("repeated_query_count", 0),
        "instructions": instructions,
        "recommended_actions": (retrieval or {}).get("recommended_actions", []),
    }


def _project_memory_policy_requires_confirmation(policy: dict[str, Any]) -> bool:
    return str(policy.get("status") or "") in PROJECT_MEMORY_CONFIRMATION_GATE_STATUSES


def _project_memory_policy_blocked_reasons(policy: dict[str, Any]) -> list[str]:
    status = str(policy.get("status") or "unknown")
    return [
        "project_memory_policy_confirmation_required",
        f"project_memory_policy_{status}",
    ]


def _project_memory_query_for_message(message: AgentMessage) -> str:
    payload = message.payload if isinstance(message.payload, dict) else {}
    for key in ("query", "topic", "title", "goal", "content"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return _redact_provider_failure_text(value.strip())
    safe_payload = _safe_provider_failure_metadata(payload)
    return f"{message.task_type} {json.dumps(safe_payload, sort_keys=True)[:500]}"


def _agent_memory_system_instruction(context_summary: dict[str, Any]) -> str:
    policy = context_summary.get("project_memory_policy") or {}
    status = policy.get("status")
    instructions = policy.get("instructions") or []
    if not status:
        return ""
    return (
        "Project-memory policy status is "
        f"{status}. {' '.join(instructions)} "
    )


def _worker_profile_policy_summary(profile, autonomous_pass_result=None) -> dict[str, Any]:
    skipped_steps = (
        autonomous_pass_result.skipped_steps if autonomous_pass_result else []
    )
    research_refresh_cycle = (
        autonomous_pass_result.research_refresh_cycle
        if autonomous_pass_result
        else None
    )
    return {
        "execution_mode": profile.execution_mode.value,
        "memory_context": {
            "include_global_memories": profile.include_global_memories,
            "memory_limit": profile.memory_limit,
        },
        "autonomous": {
            "applied": (
                profile.execution_mode
                == WorkerProfileExecutionMode.AUTONOMOUS_PASS
            ),
            "auto_refresh_research_sources": (
                profile.autonomous_auto_refresh_research_sources
            ),
            "block_on_research_freshness_blocked": (
                profile.autonomous_block_on_research_freshness_blocked
            ),
            "block_on_retrieval_quality_blocked": (
                profile.autonomous_block_on_retrieval_quality_blocked
            ),
            "export_memory_summary_to_obsidian": (
                profile.autonomous_export_memory_summary_to_obsidian
            ),
            "memory_summary_agent_id": profile.autonomous_memory_summary_agent_id,
            "memory_summary_limit": profile.autonomous_memory_summary_limit,
            "observed": {
                "research_refresh_cycle_ran": research_refresh_cycle is not None,
                "research_refresh_processed_tasks": (
                    len(research_refresh_cycle.processed_tasks)
                    if research_refresh_cycle
                    else 0
                ),
                "research_refresh_disabled": (
                    "research_source_refresh_disabled" in skipped_steps
                ),
                "research_refresh_unconfigured": (
                    "research_source_refresh_unconfigured" in skipped_steps
                ),
                "research_freshness_gate_blocked_pass": (
                    "research_freshness_blocked_autonomous_pass" in skipped_steps
                ),
                "retrieval_quality_gate_blocked_pass": (
                    "retrieval_quality_blocked_autonomous_pass" in skipped_steps
                ),
                "obsidian_memory_summary_exported": bool(
                    autonomous_pass_result
                    and autonomous_pass_result.obsidian_memory_summary
                ),
            },
        },
    }


def _heartbeat_work_plan_summary(work_plan) -> dict[str, Any] | None:
    if work_plan is None:
        return None
    return {
        "artifact_id": str(work_plan.artifact_id) if work_plan.artifact_id else None,
        "plan_item_count": len(work_plan.plan_items),
        "pending_task_count": work_plan.pending_task_count,
        "blocked_item_count": work_plan.blocked_item_count,
        "recommended_agent_ids": work_plan.recommended_agent_ids,
        "created_task_message_ids": [
            str(message_id) for message_id in work_plan.created_task_message_ids
        ],
    }

SCRIPT_DOCTOR_AGENT_ID = "script-doctor"

EDITORIAL_REVIEW_AGENTS = {
    "editor-in-chief",
    "critic-reviewer-agent",
}

EDITORIAL_REVIEW_ARTIFACT_TYPES = {
    ArtifactType.POST,
    ArtifactType.REEL_SCRIPT,
    ArtifactType.SUBSTACK_ARTICLE,
    ArtifactType.SOCIAL_PACKAGE,
}

INTENT_ROUTER_MAX_TARGETS = 10

INTENT_ROUTE_TASK_TYPES = {
    "content-strategist": "plan_from_conversation_turn",
    "web-research-agent": "research_conversation_request",
    "source-ledger-agent": "refresh_sources_for_conversation",
    "claim-verification-agent": "verify_conversation_claims",
    "data-analyst-agent": "analyze_conversation_data_request",
    "forward-deployed-engineer": "translate_conversation_feedback",
    "principal-software-engineer": "review_conversation_architecture_request",
    "backend-platform-engineer": "review_backend_platform_request",
    "frontend-experience-engineer": "review_frontend_experience_request",
    "scalability-reliability-engineer": "review_scalability_reliability_request",
    "inference-systems-engineer": "review_inference_systems_request",
    "agent-harness-engineer": "plan_conversation_resume_or_checkpoint",
    "context-engineering-agent": "build_context_from_conversation_turn",
    "product-manager": "coordinate_conversation_request",
    "interactive-note-taking-agent": "record_conversation_note",
    "visual-director": "plan_visual_system_from_turn",
    "image-generation-agent": "plan_imagegen_assets_from_turn",
    "audio-producer": "plan_audio_from_turn",
    "video-reel-producer": "plan_video_from_turn",
    "platform-optimization-agent": "adapt_platforms_from_turn",
    "influencer-strategy-agent": "plan_keywords_and_hashtags_from_turn",
    "outreach-agent": "plan_outreach_from_turn",
    "lead-ui-ux-designer": "review_interface_request_from_turn",
    "interactive-systems-designer": "review_planning_surface_request_from_turn",
    "editor-in-chief": "review_conversation_requested_edits",
    "critic-reviewer-agent": "critique_conversation_requested_edits",
}

DEDUPED_MULTIMODAL_FOLLOWUP_STATUSES = {
    AgentTaskStatus.ACCEPTED,
    AgentTaskStatus.CLAIMED,
    AgentTaskStatus.IN_PROGRESS,
    AgentTaskStatus.WAITING_FOR_HUMAN,
    AgentTaskStatus.BLOCKED,
    AgentTaskStatus.COMPLETED,
}

STALE_RECOVERABLE_AGENT_TASK_STATUSES = {
    AgentTaskStatus.CLAIMED,
    AgentTaskStatus.IN_PROGRESS,
}


class AgentWorker:
    """Process durable A2A tasks for one specialist agent.

    This is the first local worker loop. It is intentionally conservative: each
    task is claimed, moved in progress, given a context packet, and then marked
    completed or failed with a persisted result. Real provider execution is used
    when configured; otherwise the worker records deterministic local output.
    """

    def __init__(
        self,
        store,
        services: ContentWorkflowServices | None = None,
        artifacts_root: Path | None = None,
        obsidian_vault_path: Path | None = None,
    ):
        self._store = store
        self._services = services or ContentWorkflowServices()
        self._artifacts_root = artifacts_root or Path("artifacts")
        self._obsidian_vault_path = obsidian_vault_path or Path("social_media_optimiser")

    async def run(
        self,
        agent_id: str,
        request: AgentWorkerRunRequest,
    ) -> AgentWorkerRunResult:
        run = await self._store.get_run(request.run_id)
        if run is None:
            raise AgentWorkerRunNotFoundError(f"Run not found: {request.run_id}")

        agent = get_agent_card(agent_id)
        if agent is None:
            raise AgentWorkerAgentNotFoundError(f"Agent not found: {agent_id}")

        targeted_message_ids = _dedupe_message_ids(request.message_ids)
        recovered_stale_messages = []
        if request.recover_stale_tasks and not targeted_message_ids:
            recovered_stale_messages = await self._recover_stale_messages(
                run_id=request.run_id,
                agent_id=agent_id,
                stale_after_seconds=request.stale_task_after_seconds,
                limit=request.max_tasks,
            )
        blocked_exhausted_messages = []
        if not targeted_message_ids:
            blocked_exhausted_messages = await self._block_exhausted_messages(
                run_id=request.run_id,
                agent_id=agent_id,
                limit=request.max_tasks,
            )

        if targeted_message_ids:
            messages = await self._targeted_accepted_messages(
                run_id=request.run_id,
                agent_id=agent_id,
                message_ids=targeted_message_ids,
                limit=request.max_tasks,
            )
        else:
            messages = await self._store.list_agent_messages(
                request.run_id,
                agent_id=agent_id,
                direction="inbox",
                status=AgentTaskStatus.ACCEPTED,
                limit=request.max_tasks,
            )
        if not messages:
            task_scope = "targeted accepted tasks" if targeted_message_ids else "accepted tasks"
            return AgentWorkerRunResult(
                run_id=request.run_id,
                agent_id=agent_id,
                recovered_stale_tasks=len(recovered_stale_messages),
                blocked_exhausted_tasks=len(blocked_exhausted_messages),
                dependency_blocked_tasks=0,
                idle=True,
                summary=(
                    f"No {task_scope} waiting for {agent.name}. "
                    f"Recovered {len(recovered_stale_messages)} stale task(s); "
                    f"blocked {len(blocked_exhausted_messages)} exhausted task(s)."
                ),
            )

        task_results = []
        dependency_blocked_messages = []
        messages_by_id = {
            existing.message_id: existing
            for existing in await self._store.list_agent_messages(
                request.run_id,
                limit=1000,
            )
        }
        for message in messages:
            unmet_dependency_ids = _unmet_dependency_message_ids(
                message,
                messages_by_id,
            )
            if unmet_dependency_ids:
                dependency_blocked_messages.append(message)
                dependency_waiting_notes = (
                    "Task remains accepted until upstream A2A dependencies "
                    "complete."
                )
                append_handoff_trace(
                    message,
                    actor="agent-harness-engineer",
                    action="dependency_waiting",
                    status=message.status,
                    notes=dependency_waiting_notes,
                    metadata={
                        "worker_agent_id": agent_id,
                        "unmet_dependency_message_ids": [
                            str(dependency_id)
                            for dependency_id in unmet_dependency_ids
                        ],
                    },
                )
                message.updated_at = datetime.now(timezone.utc)
                await self._store.record_agent_message(message)
                await self._store.append_event(
                    RunEvent(
                        run_id=request.run_id,
                        event_type="agent_message_dependency_waiting",
                        actor="agent-harness-engineer",
                        payload=public_a2a_dependency_waiting_event_payload(
                            message=message,
                            worker_agent_id=agent_id,
                            unmet_dependency_message_ids=unmet_dependency_ids,
                            notes=dependency_waiting_notes,
                        ),
                    )
                )
                continue
            claimed_message = await self._claim_message(
                message=message,
                agent_id=agent_id,
            )
            if claimed_message is None:
                continue
            task_results.append(
                await self._process_message(
                    message=claimed_message,
                    agent_id=agent_id,
                    request=request,
                )
            )

        if not task_results:
            return AgentWorkerRunResult(
                run_id=request.run_id,
                agent_id=agent_id,
                recovered_stale_tasks=len(recovered_stale_messages),
                blocked_exhausted_tasks=len(blocked_exhausted_messages),
                dependency_blocked_tasks=len(dependency_blocked_messages),
                idle=True,
                summary=(
                    f"No claimable accepted tasks waiting for {agent.name}; "
                    f"{len(dependency_blocked_messages)} task(s) are waiting "
                    "for upstream dependencies and remaining candidates were "
                    "already claimed or moved."
                ),
            )

        completed = sum(
            1 for task in task_results if task.status == AgentTaskStatus.COMPLETED
        )
        failed = sum(1 for task in task_results if task.status == AgentTaskStatus.FAILED)
        return AgentWorkerRunResult(
            run_id=request.run_id,
            agent_id=agent_id,
            processed_tasks=task_results,
            recovered_stale_tasks=len(recovered_stale_messages),
            blocked_exhausted_tasks=len(blocked_exhausted_messages),
            dependency_blocked_tasks=len(dependency_blocked_messages),
            idle=False,
            summary=(
                f"{agent.name} processed {len(task_results)} task(s): "
                f"{completed} completed, {failed} failed; "
                f"{len(recovered_stale_messages)} stale task(s) recovered; "
                f"{len(blocked_exhausted_messages)} exhausted task(s) blocked; "
                f"{len(dependency_blocked_messages)} dependency-waiting task(s)."
            ),
        )

    async def _targeted_accepted_messages(
        self,
        *,
        run_id,
        agent_id: str,
        message_ids: list[UUID],
        limit: int,
    ) -> list[AgentMessage]:
        messages: list[AgentMessage] = []
        for message_id in message_ids:
            if len(messages) >= limit:
                break
            message = await self._store.get_agent_message(message_id)
            if (
                message is None
                or message.run_id != run_id
                or message.recipient_agent_id != agent_id
                or message.status != AgentTaskStatus.ACCEPTED
            ):
                continue
            messages.append(message)
        return messages

    async def _target_agents_for_messages(
        self,
        run_id,
        message_ids: list[UUID],
    ) -> list[str]:
        agent_ids: list[str] = []
        for message_id in message_ids:
            message = await self._store.get_agent_message(message_id)
            if message is None or message.run_id != run_id:
                continue
            if message.recipient_agent_id not in agent_ids:
                agent_ids.append(message.recipient_agent_id)
        return agent_ids

    async def _accepted_child_message_ids(
        self,
        run_id,
        parent_message_ids: list[UUID],
    ) -> list[UUID]:
        parent_ids = {str(message_id) for message_id in parent_message_ids}
        if not parent_ids:
            return []
        child_message_ids: list[UUID] = []
        messages = await self._store.list_agent_messages(run_id, limit=1000)
        for message in messages:
            if (
                message.status == AgentTaskStatus.ACCEPTED
                and message.payload.get("parent_message_id") in parent_ids
            ):
                child_message_ids.append(message.message_id)
        return _dedupe_message_ids(child_message_ids)

    async def run_cycle(
        self,
        request: AgentWorkerCycleRequest,
    ) -> AgentWorkerCycleResult:
        run = await self._store.get_run(request.run_id)
        if run is None:
            raise AgentWorkerRunNotFoundError(f"Run not found: {request.run_id}")

        target_message_ids = _dedupe_message_ids(request.message_ids)
        target_agent_ids = (
            await self._target_agents_for_messages(
                request.run_id,
                target_message_ids,
            )
            if target_message_ids
            else []
        )
        if request.agent_ids:
            agent_ids = request.agent_ids
        elif target_message_ids:
            agent_ids = (
                _dedupe_preserve_order([*target_agent_ids, *DEFAULT_WORKER_AGENT_IDS])
                if request.continue_message_lineage and target_agent_ids
                else target_agent_ids
            )
        else:
            agent_ids = DEFAULT_WORKER_AGENT_IDS
        for agent_id in agent_ids:
            if get_agent_card(agent_id) is None:
                raise AgentWorkerAgentNotFoundError(f"Agent not found: {agent_id}")

        worker_results: list[AgentWorkerRunResult] = []
        rounds_completed = 0
        active_message_ids = target_message_ids
        lineaged_target_mode = bool(
            target_message_ids and request.continue_message_lineage
        )
        for _ in range(request.max_rounds):
            rounds_completed += 1
            round_results = []
            for agent_id in agent_ids:
                result = await self.run(
                    agent_id,
                    AgentWorkerRunRequest(
                        run_id=request.run_id,
                        max_tasks=request.max_tasks_per_agent,
                        message_ids=active_message_ids,
                        include_global_memories=request.include_global_memories,
                        memory_limit=request.memory_limit,
                        use_gemma=request.use_gemma,
                        fail_on_provider_error=request.fail_on_provider_error,
                        recover_stale_tasks=request.recover_stale_tasks,
                        stale_task_after_seconds=request.stale_task_after_seconds,
                    ),
                )
                worker_results.append(result)
                round_results.append(result)
                if lineaged_target_mode and result.processed_tasks:
                    child_message_ids = await self._accepted_child_message_ids(
                        request.run_id,
                        [task.message_id for task in result.processed_tasks],
                    )
                    if child_message_ids:
                        active_message_ids = _dedupe_message_ids(
                            [*active_message_ids, *child_message_ids]
                        )
            if all(result.idle for result in round_results):
                break

        total_processed_tasks = sum(
            len(result.processed_tasks) for result in worker_results
        )
        await self._store.append_event(
            RunEvent(
                run_id=request.run_id,
                event_type="agent_worker_cycle_completed",
                actor="agent-harness-engineer",
                payload={
                    "agent_ids": agent_ids,
                    "message_ids": [
                        str(message_id)
                        for message_id in target_message_ids
                    ],
                    "continue_message_lineage": lineaged_target_mode,
                    "rounds_completed": rounds_completed,
                    "total_processed_tasks": total_processed_tasks,
                    "idle": total_processed_tasks == 0,
                },
            )
        )
        return AgentWorkerCycleResult(
            run_id=request.run_id,
            agent_ids=agent_ids,
            rounds_completed=rounds_completed,
            worker_results=worker_results,
            total_processed_tasks=total_processed_tasks,
            idle=total_processed_tasks == 0,
            summary=(
                f"Worker cycle ran {rounds_completed} round(s) across "
                f"{len(agent_ids)} agent(s) and processed "
                f"{total_processed_tasks} task(s)."
            ),
        )

    async def run_profile_heartbeat(
        self,
        profile_id,
    ) -> WorkerProfileHeartbeatResult:
        profile = await self._store.get_worker_profile(profile_id)
        if profile is None:
            raise WorkerProfileNotFoundError(f"Worker profile not found: {profile_id}")
        if profile.status != WorkerProfileStatus.ACTIVE:
            return WorkerProfileHeartbeatResult(
                profile=profile,
                skipped=True,
                skipped_reason=f"profile_{profile.status.value}",
                summary=(
                    f"Worker profile '{profile.name}' is {profile.status.value}; "
                    "heartbeat skipped."
                ),
            )

        claimed_profile = await self._store.try_claim_worker_profile_heartbeat(
            profile.profile_id,
            claimed_by="agent-harness-engineer",
            lease_seconds=max(profile.poll_interval_seconds * 2, 60.0),
        )
        if claimed_profile is None:
            latest_profile = await self._store.get_worker_profile(profile.profile_id)
            return WorkerProfileHeartbeatResult(
                profile=latest_profile or profile,
                skipped=True,
                skipped_reason="heartbeat_already_running",
                summary=(
                    f"Worker profile '{profile.name}' already has an active "
                    "heartbeat lease; heartbeat skipped."
                ),
            )
        profile = claimed_profile

        resume_request = RunResumePlanRequest(
            agent_id="agent-harness-engineer",
            create_checkpoint=True,
            checkpoint_kind="worker_profile_heartbeat",
            include_global_memories=profile.include_global_memories,
            memory_limit=profile.memory_limit,
            notes=f"Heartbeat preflight for worker profile '{profile.name}'.",
        )
        resume_plan = await RunResumeWorkflow(self._store).build_resume_plan(
            profile.run_id,
            resume_request,
        )
        heartbeat_blocked_reasons = [
            reason
            for reason in resume_plan.blocked_reasons
            if reason != "run_completed"
        ]
        if heartbeat_blocked_reasons:
            return await self._record_blocked_profile_heartbeat(
                profile_id=profile_id,
                profile=profile,
                resume_plan=resume_plan,
                blocked_reasons=heartbeat_blocked_reasons,
                skipped_reason="resume_plan_blocked",
            )

        project_memory_policy = _project_memory_policy_from_digest(
            resume_plan.context_summary.get("project_memory_retrieval")
        )
        if _project_memory_policy_requires_confirmation(project_memory_policy):
            await self._ensure_project_memory_policy_feedback_gate(
                profile=profile,
                resume_plan=resume_plan,
                project_memory_policy=project_memory_policy,
            )
            gated_resume_plan = await RunResumeWorkflow(self._store).build_resume_plan(
                profile.run_id,
                resume_request.model_copy(
                    update={
                        "checkpoint_kind": "worker_profile_policy_gate",
                        "notes": (
                            "Heartbeat blocked until project-memory policy "
                            f"status '{project_memory_policy['status']}' is "
                            "confirmed by a human."
                        ),
                    }
                ),
            )
            return await self._record_blocked_profile_heartbeat(
                profile_id=profile_id,
                profile=profile,
                resume_plan=gated_resume_plan,
                blocked_reasons=_project_memory_policy_blocked_reasons(
                    project_memory_policy
                ),
                skipped_reason="project_memory_policy_confirmation_required",
            )

        cycle_result = None
        autonomous_pass_result = None
        if profile.execution_mode == WorkerProfileExecutionMode.AUTONOMOUS_PASS:
            from all_about_llms.orchestration.autonomous_pass import (
                AutonomousStudioPassWorkflow,
            )

            autonomous_pass_result = await AutonomousStudioPassWorkflow(
                self._store,
                self._artifacts_root,
                self._services,
                obsidian_vault_path=self._obsidian_vault_path,
            ).run(
                profile.run_id,
                AutonomousStudioPassRequest(
                    agent_ids=profile.agent_ids,
                    max_tasks_per_agent=profile.max_tasks_per_agent,
                    max_worker_rounds=profile.max_rounds,
                    auto_refresh_research_sources=(
                        profile.autonomous_auto_refresh_research_sources
                    ),
                    block_on_research_freshness_blocked=(
                        profile.autonomous_block_on_research_freshness_blocked
                    ),
                    block_on_retrieval_quality_blocked=(
                        profile.autonomous_block_on_retrieval_quality_blocked
                    ),
                    export_memory_summary_to_obsidian=(
                        profile.autonomous_export_memory_summary_to_obsidian
                    ),
                    memory_summary_agent_id=(
                        profile.autonomous_memory_summary_agent_id
                    ),
                    memory_summary_limit=profile.autonomous_memory_summary_limit,
                    use_gemma=profile.use_gemma,
                    fail_on_provider_error=profile.fail_on_provider_error,
                ),
            )
            cycle_result = autonomous_pass_result.worker_cycle
        else:
            cycle_result = await self.run_cycle(
                AgentWorkerCycleRequest(
                    run_id=profile.run_id,
                    agent_ids=profile.agent_ids,
                    max_tasks_per_agent=profile.max_tasks_per_agent,
                    max_rounds=profile.max_rounds,
                    include_global_memories=profile.include_global_memories,
                    memory_limit=profile.memory_limit,
                    use_gemma=profile.use_gemma,
                    fail_on_provider_error=profile.fail_on_provider_error,
                )
            )
        updated_profile = await self._store.record_worker_profile_heartbeat(profile_id)
        if updated_profile is None:
            raise WorkerProfileNotFoundError(f"Worker profile not found: {profile_id}")
        context_packet_artifact = None
        realtime_dialogue_ledger = None
        feedback_resolution_ledger = None
        if autonomous_pass_result is not None:
            work_plan = autonomous_pass_result.work_plan
            context_packet_artifact = autonomous_pass_result.context_packet_artifact
            realtime_dialogue_ledger = autonomous_pass_result.realtime_dialogue_ledger
            feedback_resolution_ledger = autonomous_pass_result.feedback_resolution_ledger
        else:
            work_plan = await RunWorkPlanWorkflow(self._store).build(
                updated_profile.run_id,
                RunWorkPlanRequest(
                    record_artifact=True,
                    create_followup_tasks=True,
                ),
            )
            realtime_dialogue_ledger = await RealtimeDialogueLedgerWorkflow(
                self._store
            ).build(
                updated_profile.run_id,
                RealtimeDialogueLedgerRequest(
                    record_artifact=True,
                    event_limit=500,
                    turn_limit=200,
                    include_transcript_preview=True,
                ),
            )
            feedback_resolution_ledger = await FeedbackResolutionLedgerWorkflow(
                self._store
            ).build(
                updated_profile.run_id,
                FeedbackResolutionLedgerRequest(
                    record_artifact=True,
                    max_feedback_items=200,
                    max_messages=1000,
                ),
            )
            context_packet_artifact = await self._build_worker_profile_context_packet(
                profile=updated_profile,
                resume_plan=resume_plan,
                blocked_reasons=[],
            )
        processed_tasks = _heartbeat_processed_tasks(
            cycle_result=cycle_result,
            autonomous_pass_result=autonomous_pass_result,
        )
        heartbeat_ledger_artifact = await self._record_worker_profile_heartbeat_ledger(
            profile=updated_profile,
            resume_plan=resume_plan,
            cycle_result=cycle_result,
            autonomous_pass_result=autonomous_pass_result,
            work_plan=work_plan,
            context_packet_artifact=context_packet_artifact,
            realtime_dialogue_ledger=realtime_dialogue_ledger,
            feedback_resolution_ledger=feedback_resolution_ledger,
            skipped=False,
            skipped_reason=None,
            blocked_reasons=[],
            processed_tasks=processed_tasks,
        )
        profile_policy = _worker_profile_policy_summary(
            updated_profile,
            autonomous_pass_result,
        )
        heartbeat_metrics = heartbeat_ledger_artifact.content.get("metrics", {})
        await self._store.append_event(
            RunEvent(
                run_id=updated_profile.run_id,
                event_type="worker_profile_heartbeat",
                actor="agent-harness-engineer",
                payload={
                    "profile_id": str(updated_profile.profile_id),
                    "name": updated_profile.name,
                    "execution_mode": updated_profile.execution_mode.value,
                    "status": updated_profile.status.value,
                    "policy": profile_policy,
                    "metrics": heartbeat_metrics,
                    "total_processed_tasks": processed_tasks,
                    "rounds_completed": (
                        cycle_result.rounds_completed if cycle_result else 0
                    ),
                    "idle": processed_tasks == 0,
                    "autonomous_pass_event_id": (
                        autonomous_pass_result.event_id
                        if autonomous_pass_result
                        else None
                    ),
                    "autonomous_pass_skipped_steps": (
                        autonomous_pass_result.skipped_steps
                        if autonomous_pass_result
                        else []
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
                    "work_plan_created_task_message_ids": (
                        [
                            str(message_id)
                            for message_id in work_plan.created_task_message_ids
                        ]
                        if work_plan
                        else []
                    ),
                    "context_packet_artifact_id": (
                        str(context_packet_artifact.artifact_id)
                        if context_packet_artifact
                        and context_packet_artifact.artifact_id
                        else None
                    ),
                    "heartbeat_ledger_artifact_id": (
                        str(heartbeat_ledger_artifact.artifact_id)
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
                },
            )
        )
        return WorkerProfileHeartbeatResult(
            profile=updated_profile,
            resume_plan=resume_plan,
            cycle_result=cycle_result,
            autonomous_pass_result=autonomous_pass_result,
            work_plan=work_plan,
            heartbeat_ledger_artifact=heartbeat_ledger_artifact,
            context_packet_artifact=context_packet_artifact,
            realtime_dialogue_ledger=realtime_dialogue_ledger,
            feedback_resolution_ledger=feedback_resolution_ledger,
            skipped=False,
            summary=(
                f"Worker profile '{updated_profile.name}' heartbeat processed "
                f"{processed_tasks} task(s) in "
                f"{updated_profile.execution_mode.value} mode and built "
                f"{len(work_plan.plan_items) if work_plan else 0} "
                "work-plan item(s)."
            ),
        )

    async def run_due_profile_scheduler(
        self,
        request: WorkerSchedulerRunRequest,
    ) -> WorkerSchedulerRunResult:
        requested_run_id = str(request.run_id) if request.run_id is not None else None
        requested_execution_mode = (
            request.execution_mode.value if request.execution_mode is not None else None
        )
        profiles = await self._store.list_due_worker_profiles(
            limit=request.max_profiles,
            run_id=request.run_id,
            execution_mode=request.execution_mode,
        )
        heartbeat_results = []
        for profile in profiles:
            heartbeat_results.append(
                await self.run_profile_heartbeat(profile.profile_id)
            )
        total_processed_tasks = sum(
            _heartbeat_processed_tasks(
                cycle_result=result.cycle_result,
                autonomous_pass_result=result.autonomous_pass_result,
            )
            for result in heartbeat_results
            if not result.skipped
        )
        touched_run_ids = []
        for profile in profiles:
            if profile.run_id not in touched_run_ids:
                touched_run_ids.append(profile.run_id)
        for run_id in touched_run_ids:
            run_results = [
                result
                for result in heartbeat_results
                if result.profile.run_id == run_id
            ]
            scheduler_metrics = _scheduler_metrics_summary(run_results)
            profile_policies = [
                _worker_profile_policy_summary(
                    result.profile,
                    result.autonomous_pass_result,
                )
                for result in run_results
            ]
            run_processed_tasks = sum(
                _heartbeat_processed_tasks(
                    cycle_result=result.cycle_result,
                    autonomous_pass_result=result.autonomous_pass_result,
                )
                for result in run_results
                if not result.skipped
            )
            run_work_plans = [
                result.work_plan for result in run_results if result.work_plan is not None
            ]
            await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="worker_scheduler_pass_completed",
                    actor="agent-harness-engineer",
                    payload={
                        "requested_run_id": requested_run_id,
                        "requested_execution_mode": requested_execution_mode,
                        "checked_profiles": len(run_results),
                        "scheduler_checked_profiles": len(profiles),
                        "heartbeat_count": len(run_results),
                        "total_processed_tasks": run_processed_tasks,
                        "idle": run_processed_tasks == 0,
                        "profile_ids": [
                            str(result.profile.profile_id) for result in run_results
                        ],
                        "execution_modes": [
                            result.profile.execution_mode.value
                            for result in run_results
                        ],
                        "profile_policies": profile_policies,
                        "profile_metrics": scheduler_metrics["profile_metrics"],
                        "retrieval_quality_blocked_profile_count": (
                            scheduler_metrics[
                                "retrieval_quality_blocked_profile_count"
                            ]
                        ),
                        "retrieval_quality_gate_blocked_profile_count": (
                            scheduler_metrics[
                                "retrieval_quality_gate_blocked_profile_count"
                            ]
                        ),
                        "retrieval_quality_recall_gap_count": (
                            scheduler_metrics[
                                "retrieval_quality_recall_gap_count"
                            ]
                        ),
                        "retrieval_quality_coverage_gap_count": (
                            scheduler_metrics[
                                "retrieval_quality_coverage_gap_count"
                            ]
                        ),
                        "memory_stale_profile_count": (
                            scheduler_metrics["memory_stale_profile_count"]
                        ),
                        "memory_low_confidence_profile_count": (
                            scheduler_metrics[
                                "memory_low_confidence_profile_count"
                            ]
                        ),
                        "memory_conflict_profile_count": (
                            scheduler_metrics["memory_conflict_profile_count"]
                        ),
                        "project_memory_retrieval_precision_risk_profile_count": (
                            scheduler_metrics[
                                "project_memory_retrieval_precision_risk_profile_count"
                            ]
                        ),
                        "project_memory_retrieval_recall_gap_profile_count": (
                            scheduler_metrics[
                                "project_memory_retrieval_recall_gap_profile_count"
                            ]
                        ),
                        "project_memory_retrieval_regressed_profile_count": (
                            scheduler_metrics[
                                "project_memory_retrieval_regressed_profile_count"
                            ]
                        ),
                        "project_memory_retrieval_no_seed_profile_count": (
                            scheduler_metrics[
                                "project_memory_retrieval_no_seed_profile_count"
                            ]
                        ),
                        "autonomous_memory_summary_exported_profile_count": sum(
                            1
                            for policy in profile_policies
                            if policy["autonomous"]["observed"][
                                "obsidian_memory_summary_exported"
                            ]
                        ),
                        "research_refresh_cycle_profile_count": sum(
                            1
                            for policy in profile_policies
                            if policy["autonomous"]["observed"][
                                "research_refresh_cycle_ran"
                            ]
                        ),
                        "autonomous_pass_event_ids": [
                            result.autonomous_pass_result.event_id
                            for result in run_results
                            if result.autonomous_pass_result
                            and result.autonomous_pass_result.event_id
                        ],
                        "work_plan_artifact_ids": [
                            str(work_plan.artifact_id)
                            for work_plan in run_work_plans
                            if work_plan.artifact_id
                        ],
                        "realtime_dialogue_artifact_ids": [
                            str(result.realtime_dialogue_ledger.ledger_artifact_id)
                            for result in run_results
                            if result.realtime_dialogue_ledger
                            and result.realtime_dialogue_ledger.ledger_artifact_id
                        ],
                        "feedback_resolution_artifact_ids": [
                            str(result.feedback_resolution_ledger.ledger_artifact_id)
                            for result in run_results
                            if result.feedback_resolution_ledger
                            and result.feedback_resolution_ledger.ledger_artifact_id
                        ],
                        "context_packet_artifact_ids": [
                            str(result.context_packet_artifact.artifact_id)
                            for result in run_results
                            if result.context_packet_artifact
                            and result.context_packet_artifact.artifact_id
                        ],
                        "heartbeat_ledger_artifact_ids": [
                            str(result.heartbeat_ledger_artifact.artifact_id)
                            for result in run_results
                            if result.heartbeat_ledger_artifact
                            and result.heartbeat_ledger_artifact.artifact_id
                        ],
                        "work_plan_blocked_item_count": sum(
                            work_plan.blocked_item_count
                            for work_plan in run_work_plans
                        ),
                        "work_plan_created_task_message_ids": [
                            str(message_id)
                            for work_plan in run_work_plans
                            for message_id in work_plan.created_task_message_ids
                        ],
                    },
                )
            )
        if request.run_id is not None and not touched_run_ids:
            scheduler_metrics = _scheduler_metrics_summary([])
            await self._store.append_event(
                RunEvent(
                    run_id=request.run_id,
                    event_type="worker_scheduler_pass_completed",
                    actor="agent-harness-engineer",
                    payload={
                        "requested_run_id": requested_run_id,
                        "requested_execution_mode": requested_execution_mode,
                        "checked_profiles": 0,
                        "scheduler_checked_profiles": 0,
                        "heartbeat_count": 0,
                        "total_processed_tasks": 0,
                        "idle": True,
                        "idle_reason": "no_due_profiles",
                        "profile_ids": [],
                        "execution_modes": [],
                        "profile_policies": [],
                        "profile_metrics": scheduler_metrics["profile_metrics"],
                        "retrieval_quality_blocked_profile_count": (
                            scheduler_metrics[
                                "retrieval_quality_blocked_profile_count"
                            ]
                        ),
                        "retrieval_quality_gate_blocked_profile_count": (
                            scheduler_metrics[
                                "retrieval_quality_gate_blocked_profile_count"
                            ]
                        ),
                        "retrieval_quality_recall_gap_count": (
                            scheduler_metrics["retrieval_quality_recall_gap_count"]
                        ),
                        "retrieval_quality_coverage_gap_count": (
                            scheduler_metrics[
                                "retrieval_quality_coverage_gap_count"
                            ]
                        ),
                        "memory_stale_profile_count": (
                            scheduler_metrics["memory_stale_profile_count"]
                        ),
                        "memory_low_confidence_profile_count": (
                            scheduler_metrics[
                                "memory_low_confidence_profile_count"
                            ]
                        ),
                        "memory_conflict_profile_count": (
                            scheduler_metrics["memory_conflict_profile_count"]
                        ),
                        "project_memory_retrieval_precision_risk_profile_count": (
                            scheduler_metrics[
                                "project_memory_retrieval_precision_risk_profile_count"
                            ]
                        ),
                        "project_memory_retrieval_recall_gap_profile_count": (
                            scheduler_metrics[
                                "project_memory_retrieval_recall_gap_profile_count"
                            ]
                        ),
                        "project_memory_retrieval_regressed_profile_count": (
                            scheduler_metrics[
                                "project_memory_retrieval_regressed_profile_count"
                            ]
                        ),
                        "project_memory_retrieval_no_seed_profile_count": (
                            scheduler_metrics[
                                "project_memory_retrieval_no_seed_profile_count"
                            ]
                        ),
                        "autonomous_memory_summary_exported_profile_count": 0,
                        "research_refresh_cycle_profile_count": 0,
                        "autonomous_pass_event_ids": [],
                        "work_plan_artifact_ids": [],
                        "realtime_dialogue_artifact_ids": [],
                        "feedback_resolution_artifact_ids": [],
                        "context_packet_artifact_ids": [],
                        "heartbeat_ledger_artifact_ids": [],
                        "work_plan_blocked_item_count": 0,
                        "work_plan_created_task_message_ids": [],
                    },
                )
            )
        return WorkerSchedulerRunResult(
            checked_profiles=len(profiles),
            heartbeat_results=heartbeat_results,
            total_processed_tasks=total_processed_tasks,
            idle=total_processed_tasks == 0,
            summary=(
                f"Scheduler checked {len(profiles)} due profile(s) and "
            f"processed {total_processed_tasks} task(s)."
            ),
        )

    async def _ensure_project_memory_policy_feedback_gate(
        self,
        *,
        profile,
        resume_plan,
        project_memory_policy: dict[str, Any],
    ) -> FeedbackItem:
        existing_gate = await self._existing_project_memory_policy_feedback_gate(
            profile=profile,
            project_memory_policy=project_memory_policy,
            retrieval=resume_plan.context_summary.get("project_memory_retrieval"),
        )
        if existing_gate is not None:
            await self._store.update_run_status(
                profile.run_id,
                RunStatus.WAITING_FOR_HUMAN,
            )
            return existing_gate

        retrieval = resume_plan.context_summary.get("project_memory_retrieval") or {}
        evaluation = retrieval.get("evaluation") or {}
        policy_status = project_memory_policy["status"]
        feedback = FeedbackItem(
            run_id=profile.run_id,
            author="system",
            target_agent_id="forward-deployed-engineer",
            feedback_text=(
                "Confirm or correct project-memory retrieval before this "
                f"always-on profile continues. Policy status: {policy_status}."
            ),
            metadata={
                "gate": PROJECT_MEMORY_CONFIRMATION_GATE,
                "source": "worker_profile_heartbeat",
                "profile_id": str(profile.profile_id),
                "profile_name": profile.name,
                "execution_mode": profile.execution_mode.value,
                "project_memory_policy_status": policy_status,
                "project_memory_query": retrieval.get("query"),
                "memory_count": retrieval.get("memory_count", 0),
                "seed_memory_count": retrieval.get("seed_memory_count", 0),
                "related_memory_count": retrieval.get("related_memory_count", 0),
                "graph_edge_count": retrieval.get("graph_edge_count", 0),
                "precision": evaluation.get("precision"),
                "recall": evaluation.get("recall"),
                "precision_risk_count": evaluation.get("precision_risk_count", 0),
                "recall_gap_count": evaluation.get("recall_gap_count", 0),
                "trend": evaluation.get("trend"),
                "recommended_actions": project_memory_policy.get(
                    "recommended_actions",
                    [],
                ),
                "resume_plan_event_id": resume_plan.event_id,
            },
        )
        await self._store.record_feedback(feedback)
        await self._store.update_run_status(
            profile.run_id,
            RunStatus.WAITING_FOR_HUMAN,
        )
        await self._store.append_event(
            RunEvent(
                run_id=profile.run_id,
                event_type="human_feedback_gate_opened",
                actor="forward-deployed-engineer",
                payload={
                    "feedback_id": str(feedback.feedback_id),
                    "gate": PROJECT_MEMORY_CONFIRMATION_GATE,
                    "profile_id": str(profile.profile_id),
                    "project_memory_policy_status": policy_status,
                    "project_memory_query": retrieval.get("query"),
                    "precision": evaluation.get("precision"),
                    "recall": evaluation.get("recall"),
                    "precision_risk_count": evaluation.get(
                        "precision_risk_count",
                        0,
                    ),
                    "recall_gap_count": evaluation.get("recall_gap_count", 0),
                    "trend": evaluation.get("trend"),
                },
            )
        )
        return feedback

    async def _existing_project_memory_policy_feedback_gate(
        self,
        *,
        profile,
        project_memory_policy: dict[str, Any],
        retrieval: dict[str, Any] | None,
    ) -> FeedbackItem | None:
        retrieval = retrieval or {}
        open_or_routed_feedback = [
            feedback
            for feedback in await self._store.list_feedback(profile.run_id)
            if feedback.status in {FeedbackStatus.OPEN, FeedbackStatus.ROUTED}
        ]
        policy_status = project_memory_policy.get("status")
        query = retrieval.get("query")
        for feedback in open_or_routed_feedback:
            metadata = feedback.metadata or {}
            if metadata.get("gate") != PROJECT_MEMORY_CONFIRMATION_GATE:
                continue
            if metadata.get("profile_id") != str(profile.profile_id):
                continue
            if metadata.get("project_memory_policy_status") != policy_status:
                continue
            if metadata.get("project_memory_query") != query:
                continue
            return feedback
        return None

    async def _record_blocked_profile_heartbeat(
        self,
        *,
        profile_id,
        profile,
        resume_plan,
        blocked_reasons: list[str],
        skipped_reason: str,
    ) -> WorkerProfileHeartbeatResult:
        updated_profile = await self._store.record_worker_profile_heartbeat(
            profile_id
        )
        if updated_profile is None:
            raise WorkerProfileNotFoundError(f"Worker profile not found: {profile_id}")
        work_plan = await RunWorkPlanWorkflow(self._store).build(
            updated_profile.run_id,
            RunWorkPlanRequest(
                record_artifact=True,
                create_followup_tasks=False,
            ),
        )
        realtime_dialogue_ledger = await RealtimeDialogueLedgerWorkflow(
            self._store
        ).build(
            updated_profile.run_id,
            RealtimeDialogueLedgerRequest(
                record_artifact=True,
                event_limit=500,
                turn_limit=200,
                include_transcript_preview=True,
            ),
        )
        feedback_resolution_ledger = await FeedbackResolutionLedgerWorkflow(
            self._store
        ).build(
            updated_profile.run_id,
            FeedbackResolutionLedgerRequest(
                record_artifact=True,
                max_feedback_items=200,
                max_messages=1000,
            ),
        )
        context_packet_artifact = await self._build_worker_profile_context_packet(
            profile=updated_profile,
            resume_plan=resume_plan,
            blocked_reasons=blocked_reasons,
        )
        heartbeat_ledger_artifact = await self._record_worker_profile_heartbeat_ledger(
            profile=updated_profile,
            resume_plan=resume_plan,
            cycle_result=None,
            autonomous_pass_result=None,
            work_plan=work_plan,
            context_packet_artifact=context_packet_artifact,
            realtime_dialogue_ledger=realtime_dialogue_ledger,
            feedback_resolution_ledger=feedback_resolution_ledger,
            skipped=True,
            skipped_reason=skipped_reason,
            blocked_reasons=blocked_reasons,
            processed_tasks=0,
        )
        profile_policy = _worker_profile_policy_summary(updated_profile)
        heartbeat_metrics = heartbeat_ledger_artifact.content.get("metrics", {})
        project_memory_metrics = heartbeat_metrics.get("project_memory_retrieval") or {}
        await self._store.append_event(
            RunEvent(
                run_id=updated_profile.run_id,
                event_type="worker_profile_heartbeat_blocked",
                actor="agent-harness-engineer",
                payload={
                    "profile_id": str(updated_profile.profile_id),
                    "name": updated_profile.name,
                    "execution_mode": updated_profile.execution_mode.value,
                    "policy": profile_policy,
                    "metrics": heartbeat_metrics,
                    "skipped_reason": skipped_reason,
                    "blocked_reasons": blocked_reasons,
                    "resume_plan_blocked_reasons": resume_plan.blocked_reasons,
                    "recommended_next_actions": resume_plan.recommended_next_actions,
                    "project_memory_policy_status": (
                        project_memory_metrics.get("policy_status")
                    ),
                    "checkpoint_id": (
                        str(resume_plan.checkpoint.checkpoint_id)
                        if resume_plan.checkpoint
                        else None
                    ),
                    "work_plan_artifact_id": (
                        str(work_plan.artifact_id)
                        if work_plan and work_plan.artifact_id
                        else None
                    ),
                    "work_plan_blocked_item_count": (
                        work_plan.blocked_item_count if work_plan else None
                    ),
                    "realtime_dialogue_artifact_id": (
                        str(realtime_dialogue_ledger.ledger_artifact_id)
                        if realtime_dialogue_ledger.ledger_artifact_id
                        else None
                    ),
                    "realtime_dialogue_status": realtime_dialogue_ledger.status,
                    "feedback_resolution_artifact_id": (
                        str(feedback_resolution_ledger.ledger_artifact_id)
                        if feedback_resolution_ledger.ledger_artifact_id
                        else None
                    ),
                    "feedback_resolution_status": feedback_resolution_ledger.status,
                    "feedback_resolution_open_count": (
                        feedback_resolution_ledger.open_feedback_count
                    ),
                    "context_packet_artifact_id": (
                        str(context_packet_artifact.artifact_id)
                        if context_packet_artifact.artifact_id
                        else None
                    ),
                    "heartbeat_ledger_artifact_id": str(
                        heartbeat_ledger_artifact.artifact_id
                    ),
                    "context_packet_manifest_items": (
                        context_packet_artifact.content["summary"][
                            "context_manifest_items"
                        ]
                    ),
                    "context_packet_risk_count": (
                        context_packet_artifact.content["summary"][
                            "context_risk_count"
                        ]
                    ),
                },
            )
        )
        return WorkerProfileHeartbeatResult(
            profile=updated_profile,
            resume_plan=resume_plan,
            work_plan=work_plan,
            heartbeat_ledger_artifact=heartbeat_ledger_artifact,
            context_packet_artifact=context_packet_artifact,
            realtime_dialogue_ledger=realtime_dialogue_ledger,
            feedback_resolution_ledger=feedback_resolution_ledger,
            skipped=True,
            skipped_reason=skipped_reason,
            summary=(
                f"Worker profile '{updated_profile.name}' heartbeat blocked by "
                f"{', '.join(blocked_reasons) or 'resume gate'}."
            ),
        )

    async def _build_worker_profile_context_packet(
        self,
        *,
        profile,
        resume_plan,
        blocked_reasons: list[str],
    ) -> ArtifactRecord:
        target_agent_id = "agent-harness-engineer"
        blocked = bool(blocked_reasons)
        source_workflow = (
            "worker_profile_heartbeat_blocked_v1"
            if blocked
            else "worker_profile_heartbeat_v1"
        )
        workflow = (
            "worker_profile_blocked_context_packet_v1"
            if blocked
            else "worker_profile_context_packet_v1"
        )
        memory_results = await self._store.search_memories(
            agent_id=target_agent_id,
            run_id=profile.run_id,
            include_global_memories=profile.include_global_memories,
            query_embedding=None,
            limit=profile.memory_limit,
        )
        recent_events = await self._store.list_events(profile.run_id, limit=75)
        run = await self._store.get_run(profile.run_id)
        if run is None:
            raise AgentWorkerRunNotFoundError(f"Run not found: {profile.run_id}")
        project_memory_retrieval = await ProjectMemoryRetrievalWorkflow(
            self._store
        ).retrieve(
            profile.run_id,
            ProjectMemoryRetrievalRequest(
                query=run.goal,
                agent_id=target_agent_id,
                include_global_memories=profile.include_global_memories,
                seed_limit=min(5, profile.memory_limit),
                memory_limit=max(profile.memory_limit, 10),
                graph_depth=1,
                record_artifact=False,
            ),
        )
        payload = build_context_engineering_payload(
            run=run,
            conversation_turns=await self._store.list_conversation_turns(profile.run_id),
            agent_messages=await self._store.list_agent_messages(
                profile.run_id,
                agent_id=target_agent_id,
            ),
            recent_events=recent_events,
            sources=await self._store.list_sources(profile.run_id),
            claims=await self._store.list_claims(profile.run_id),
            artifacts=await self._store.list_artifacts(profile.run_id),
            guardrail_audits=await self._store.list_guardrail_audits(profile.run_id),
            feedback_items=await self._store.list_feedback(profile.run_id),
            memories=[
                MemorySearchResult(memory=memory, distance=distance)
                for memory, distance in memory_results
            ],
            agent_id=target_agent_id,
            max_manifest_items=60,
            max_context_tokens=16000,
            project_memory_retrieval=project_memory_retrieval_digest(
                project_memory_retrieval
            ),
        )
        artifact = ArtifactRecord(
            run_id=profile.run_id,
            artifact_type=ArtifactType.CONTEXT_PACKET,
            title=(
                f"Blocked heartbeat context packet: {profile.name}"
                if blocked
                else f"Worker profile heartbeat context packet: {profile.name}"
            ),
            uri=(
                f"artifact://runs/{profile.run_id}/worker-profiles/"
                f"{profile.profile_id}/"
                f"{'blocked-context' if blocked else 'heartbeat-context'}"
            ),
            content={
                "target_agent_id": target_agent_id,
                "source_workflow": source_workflow,
                "profile_id": str(profile.profile_id),
                "profile_name": profile.name,
                "execution_mode": profile.execution_mode.value,
                "heartbeat_state": "blocked" if blocked else "completed",
                "blocked_reasons": blocked_reasons,
                "resume_plan_event_id": resume_plan.event_id,
                "checkpoint_id": (
                    str(resume_plan.checkpoint.checkpoint_id)
                    if resume_plan.checkpoint
                    else None
                ),
                "summary": payload["summary"],
                "context_manifest": [
                    item.model_dump(mode="json")
                    for item in payload["context_manifest"]
                ],
                "context_risks": [
                    risk.model_dump(mode="json") for risk in payload["context_risks"]
                ],
                "recommended_fetches": payload["recommended_fetches"],
                "source_evidence": payload["source_evidence"],
                "recent_events": [
                    event.model_dump(mode="json") for event in recent_events
                ],
            },
            provenance={
                "workflow": workflow,
                "agent_id": "context-engineering-agent",
                "target_agent_id": target_agent_id,
                "profile_id": str(profile.profile_id),
                "source_workflow": source_workflow,
                "generation_mode": "deterministic_context_engineering",
            },
            revision_history=[
                {
                    "actor": "context-engineering-agent",
                    "workflow": workflow,
                    "note": (
                        "Created a post-ledger context packet for a blocked "
                        "always-on profile heartbeat."
                        if blocked
                        else "Created a post-cycle context packet for an always-on profile heartbeat."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(artifact)
        await self._store.append_event(
            RunEvent(
                run_id=profile.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=artifact.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=profile.run_id,
                event_type="context_packet_artifact_created",
                actor="context-engineering-agent",
                payload={
                    "artifact_id": str(artifact.artifact_id),
                    "target_agent_id": target_agent_id,
                    "source_workflow": source_workflow,
                    "profile_id": str(profile.profile_id),
                    "heartbeat_state": "blocked" if blocked else "completed",
                    "blocked_reasons": blocked_reasons,
                    "context_manifest_items": payload["summary"][
                        "context_manifest_items"
                    ],
                    "context_risk_count": payload["summary"]["context_risk_count"],
                    "recommended_fetches": payload["summary"]["recommended_fetches"],
                },
            )
        )
        return artifact

    async def _record_worker_profile_heartbeat_ledger(
        self,
        *,
        profile,
        resume_plan,
        cycle_result,
        autonomous_pass_result,
        work_plan,
        context_packet_artifact,
        realtime_dialogue_ledger,
        feedback_resolution_ledger,
        skipped: bool,
        skipped_reason: str | None,
        blocked_reasons: list[str],
        processed_tasks: int,
    ) -> ArtifactRecord:
        heartbeat_state = "blocked" if blocked_reasons else "completed"
        content = {
            "format": "worker_profile_heartbeat_ledger",
            "profile": {
                "profile_id": str(profile.profile_id),
                "name": profile.name,
                "status": profile.status.value,
                "execution_mode": profile.execution_mode.value,
                "agent_ids": profile.agent_ids,
                "poll_interval_seconds": profile.poll_interval_seconds,
                "last_heartbeat_at": (
                    profile.last_heartbeat_at.isoformat()
                    if profile.last_heartbeat_at
                    else None
                ),
            },
            "heartbeat_state": heartbeat_state,
            "skipped": skipped,
            "skipped_reason": skipped_reason,
            "blocked_reasons": blocked_reasons,
            "processed_tasks": processed_tasks,
            "idle": processed_tasks == 0,
            "resume_gate": {
                "resume_allowed": resume_plan.resume_allowed,
                "blocked_reasons": resume_plan.blocked_reasons,
                "recommended_next_actions": resume_plan.recommended_next_actions,
                "event_id": resume_plan.event_id,
                "checkpoint_id": (
                    str(resume_plan.checkpoint.checkpoint_id)
                    if resume_plan.checkpoint
                    else None
                ),
            },
            "worker_cycle": _heartbeat_cycle_summary(cycle_result),
            "autonomous_pass": _heartbeat_autonomous_pass_summary(
                autonomous_pass_result
            ),
            "policy": _worker_profile_policy_summary(
                profile,
                autonomous_pass_result,
            ),
            "metrics": _heartbeat_metrics_summary(
                autonomous_pass_result=autonomous_pass_result,
                context_packet_artifact=context_packet_artifact,
            ),
            "work_plan": _heartbeat_work_plan_summary(work_plan),
            "linked_artifacts": {
                "work_plan_artifact_id": (
                    str(work_plan.artifact_id)
                    if work_plan and work_plan.artifact_id
                    else None
                ),
                "context_packet_artifact_id": (
                    str(context_packet_artifact.artifact_id)
                    if context_packet_artifact
                    and context_packet_artifact.artifact_id
                    else None
                ),
                "realtime_dialogue_artifact_id": (
                    str(realtime_dialogue_ledger.ledger_artifact_id)
                    if realtime_dialogue_ledger
                    and realtime_dialogue_ledger.ledger_artifact_id
                    else None
                ),
                "feedback_resolution_artifact_id": (
                    str(feedback_resolution_ledger.ledger_artifact_id)
                    if feedback_resolution_ledger
                    and feedback_resolution_ledger.ledger_artifact_id
                    else None
                ),
            },
            "loop_ledgers": {
                "realtime_dialogue_status": (
                    realtime_dialogue_ledger.status
                    if realtime_dialogue_ledger
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
            },
        }
        workflow = (
            "worker_profile_heartbeat_blocked_ledger_v1"
            if blocked_reasons
            else "worker_profile_heartbeat_ledger_v1"
        )
        artifact = ArtifactRecord(
            run_id=profile.run_id,
            artifact_type=ArtifactType.WORKER_PROFILE_HEARTBEAT_LEDGER,
            title=(
                f"Blocked worker profile heartbeat ledger: {profile.name}"
                if blocked_reasons
                else f"Worker profile heartbeat ledger: {profile.name}"
            ),
            uri=(
                f"artifact://runs/{profile.run_id}/worker-profiles/"
                f"{profile.profile_id}/heartbeat-ledger"
            ),
            content=content,
            provenance={
                "workflow": workflow,
                "agent_id": "agent-harness-engineer",
                "profile_id": str(profile.profile_id),
                "execution_mode": profile.execution_mode.value,
                "generation_mode": "deterministic_heartbeat_ledger",
            },
            revision_history=[
                {
                    "actor": "agent-harness-engineer",
                    "workflow": workflow,
                    "note": (
                        "Recorded a compact durable heartbeat ledger for an "
                        "always-on worker profile."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(artifact)
        await self._store.append_event(
            RunEvent(
                run_id=profile.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=artifact.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=profile.run_id,
                event_type="worker_profile_heartbeat_ledger_recorded",
                actor="agent-harness-engineer",
                payload={
                    "artifact_id": str(artifact.artifact_id),
                    "profile_id": str(profile.profile_id),
                    "execution_mode": profile.execution_mode.value,
                    "heartbeat_state": heartbeat_state,
                    "policy": content["policy"],
                    "metrics": content["metrics"],
                    "skipped": skipped,
                    "skipped_reason": skipped_reason,
                    "blocked_reasons": blocked_reasons,
                    "processed_tasks": processed_tasks,
                    "idle": processed_tasks == 0,
                    "context_packet_artifact_id": content["linked_artifacts"][
                        "context_packet_artifact_id"
                    ],
                    "realtime_dialogue_artifact_id": content["linked_artifacts"][
                        "realtime_dialogue_artifact_id"
                    ],
                    "feedback_resolution_artifact_id": content["linked_artifacts"][
                        "feedback_resolution_artifact_id"
                    ],
                },
            )
        )
        return artifact

    async def _recover_stale_messages(
        self,
        *,
        run_id: UUID,
        agent_id: str,
        stale_after_seconds: float,
        limit: int,
    ) -> list[AgentMessage]:
        if not hasattr(self._store, "recover_stale_agent_messages"):
            return []
        stale_before = datetime.now(timezone.utc) - timedelta(
            seconds=stale_after_seconds
        )
        recovered = await self._store.recover_stale_agent_messages(
            run_id,
            stale_before=stale_before,
            statuses=list(STALE_RECOVERABLE_AGENT_TASK_STATUSES),
            agent_id=agent_id,
            limit=limit,
            recovery_actor="agent-harness-engineer",
        )
        recovered_messages = []
        for item in recovered:
            message = item["message"]
            recovered_messages.append(message)
            previous_updated_at = item.get("previous_updated_at")
            recovery_notes = (
                "Recovered stale claimed/in-progress task for "
                "atomic reprocessing."
            )
            await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="agent_message_recovered",
                    actor="agent-harness-engineer",
                    payload=public_a2a_recovered_event_payload(
                        message=message,
                        from_status=item["from_status"],
                        to_status=AgentTaskStatus.ACCEPTED,
                        previous_claimed_by_agent_id=item.get(
                            "previous_claimed_by_agent_id"
                        ),
                        previous_updated_at=previous_updated_at,
                        worker_agent_id=agent_id,
                        stale_after_seconds=stale_after_seconds,
                        notes=recovery_notes,
                    ),
                )
            )
        return recovered_messages

    async def _block_exhausted_messages(
        self,
        *,
        run_id: UUID,
        agent_id: str,
        limit: int,
    ) -> list[AgentMessage]:
        if not hasattr(self._store, "block_exhausted_agent_messages"):
            return []
        blocked_messages = await self._store.block_exhausted_agent_messages(
            run_id,
            agent_id=agent_id,
            limit=limit,
            recovery_actor="agent-harness-engineer",
        )
        if blocked_messages:
            await self._store.update_run_status(run_id, RunStatus.WAITING_FOR_HUMAN)
        for message in blocked_messages:
            await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="agent_message_retry_exhausted",
                    actor="agent-harness-engineer",
                    payload=public_a2a_retry_exhausted_event_payload(
                        message=message,
                        worker_agent_id=agent_id,
                        notes=(
                            "Blocked A2A task after retry attempts were exhausted; "
                            "human review is required before another retry."
                        ),
                    ),
                )
            )
        return blocked_messages

    async def _claim_message(
        self,
        *,
        message: AgentMessage,
        agent_id: str,
    ) -> AgentMessage | None:
        claimed = await self._store.try_claim_agent_message(
            message.message_id,
            agent_id=agent_id,
        )
        if claimed is None:
            return None
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="agent_message_status_updated",
                actor=agent_id,
                payload=public_a2a_status_event_payload(
                    message=message,
                    from_status=AgentTaskStatus.ACCEPTED,
                    to_status=AgentTaskStatus.CLAIMED,
                    notes="Worker atomically claimed task for durable execution.",
                    has_result=False,
                    has_error=False,
                ),
            )
        )
        return claimed

    async def _process_message(
        self,
        *,
        message: AgentMessage,
        agent_id: str,
        request: AgentWorkerRunRequest,
    ) -> AgentWorkerTaskResult:
        in_progress_message = await self._set_status(
            message=message,
            agent_id=agent_id,
            status=AgentTaskStatus.IN_PROGRESS,
            result={},
            notes="Worker started task execution.",
        )

        context_summary: dict[str, Any] = {}
        skill_usage: dict[str, Any] = {}
        try:
            context_summary = await self._build_context_summary(
                message=in_progress_message,
                agent_id=agent_id,
                request=request,
            )
            skill_usage = _skill_usage_payload(
                message=in_progress_message,
                agent_id=agent_id,
                context_summary=context_summary,
            )
            skill_invocation_event = await self._record_skill_invocation(
                message=in_progress_message,
                agent_id=agent_id,
                skill_usage=skill_usage,
            )
            skill_usage["invocation_event_id"] = skill_invocation_event.event_id
            result = await self._execute_specialist_step(
                message=in_progress_message,
                agent_id=agent_id,
                context_summary=context_summary,
                request=request,
            )
            result.setdefault("skill_ids", skill_usage["skill_ids"])
            result["skill_usage"] = {
                **skill_usage,
                "status": AgentTaskStatus.COMPLETED.value,
            }
            completed_message = await self._set_status(
                message=in_progress_message,
                agent_id=agent_id,
                status=AgentTaskStatus.COMPLETED,
                result=result,
                notes=result["summary"],
            )
            return AgentWorkerTaskResult(
                message_id=completed_message.message_id,
                task_type=completed_message.task_type,
                status=completed_message.status,
                generation_mode=result["generation_mode"],
                summary=result["summary"],
            )
        except Exception as exc:
            failed_result = {"generation_mode": "worker_error"}
            if skill_usage:
                failed_result["skill_usage"] = {
                    **skill_usage,
                    "status": AgentTaskStatus.FAILED.value,
                }
            failed_message = await self._set_status(
                message=in_progress_message,
                agent_id=agent_id,
                status=AgentTaskStatus.FAILED,
                result=failed_result,
                error=str(exc),
                notes="Worker task failed.",
            )
            return AgentWorkerTaskResult(
                message_id=failed_message.message_id,
                task_type=failed_message.task_type,
                status=failed_message.status,
                generation_mode="worker_error",
                summary=str(exc),
            )

    async def _record_skill_invocation(
        self,
        *,
        message: AgentMessage,
        agent_id: str,
        skill_usage: dict[str, Any],
    ) -> RunEvent:
        return await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="agent_skill_invocation_recorded",
                actor=agent_id,
                payload=public_a2a_skill_invocation_event_payload(
                    skill_usage=skill_usage,
                    status=AgentTaskStatus.IN_PROGRESS,
                    notes=(
                        "Worker attached active project skill cards before "
                        "executing the specialist task."
                    ),
                ),
            )
        )

    async def _build_context_summary(
        self,
        *,
        message: AgentMessage,
        agent_id: str,
        request: AgentWorkerRunRequest,
    ) -> dict[str, Any]:
        memories = await self._store.search_memories(
            agent_id=agent_id,
            run_id=request.run_id,
            include_global_memories=request.include_global_memories,
            limit=request.memory_limit,
        )
        project_memory_retrieval = await ProjectMemoryRetrievalWorkflow(
            self._store
        ).retrieve(
            request.run_id,
            ProjectMemoryRetrievalRequest(
                query=_project_memory_query_for_message(message),
                agent_id=agent_id,
                include_global_memories=request.include_global_memories,
                seed_limit=min(5, request.memory_limit),
                memory_limit=max(request.memory_limit, 10),
                graph_depth=1,
                record_artifact=False,
            ),
        )
        project_memory_retrieval_summary = project_memory_retrieval_digest(
            project_memory_retrieval
        )
        skill_cards = skill_cards_for_agent(agent_id)
        summary = {
            "run_id": str(request.run_id),
            "agent_id": agent_id,
            "message_id": str(message.message_id),
            "task_type": message.task_type,
            "skill_ids": [skill.id for skill in skill_cards],
            "skill_count": len(skill_cards),
            "conversation_turns": len(
                await self._store.list_conversation_turns(request.run_id)
            ),
            "agent_messages": len(
                await self._store.list_agent_messages(
                    request.run_id,
                    agent_id=agent_id,
                    direction="all",
                )
            ),
            "sources": len(await self._store.list_sources(request.run_id)),
            "claims": len(await self._store.list_claims(request.run_id)),
            "artifacts": len(await self._store.list_artifacts(request.run_id)),
            "guardrail_audits": len(
                await self._store.list_guardrail_audits(request.run_id)
            ),
            "feedback_items": len(await self._store.list_feedback(request.run_id)),
            "memories": len(memories),
            "project_memory_retrieval": project_memory_retrieval_summary,
            "project_memory_policy": _project_memory_policy_from_digest(
                project_memory_retrieval_summary
            ),
        }
        await self._store.append_event(
            RunEvent(
                run_id=request.run_id,
                event_type="context_packet_built",
                actor=agent_id,
                payload=public_a2a_context_packet_event_payload(summary),
            )
        )
        return summary

    async def _execute_specialist_step(
        self,
        *,
        message: AgentMessage,
        agent_id: str,
        context_summary: dict[str, Any],
        request: AgentWorkerRunRequest,
    ) -> dict[str, Any]:
        if message.task_type == "review_multimodal_intake":
            return await self._execute_multimodal_intake_review(
                message=message,
                agent_id=agent_id,
                context_summary=context_summary,
                request=request,
            )
        if agent_id == "web-research-agent":
            return await self._execute_web_research(
                message=message,
                context_summary=context_summary,
                request=request,
            )
        if agent_id == "realtime-conversation-host":
            return await self._execute_realtime_conversation_brief(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "source-ledger-agent":
            return await self._execute_source_ledger_snapshot(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "context-engineering-agent":
            if message.task_type == "record_project_memory":
                return await self._execute_project_memory_record(
                    message=message,
                    context_summary=context_summary,
                )
            if message.task_type == "retrieve_project_memory":
                return await self._execute_project_memory_retrieval(
                    message=message,
                    context_summary=context_summary,
                )
            return await self._execute_context_engineering_packet(
                message=message,
                context_summary=context_summary,
            )
        if (
            message.task_type == "review_provider_configuration_blockers"
            and agent_id in {"inference-systems-engineer", "agent-harness-engineer"}
        ):
            return await self._execute_provider_configuration_blocker_review(
                message=message,
                agent_id=agent_id,
                context_summary=context_summary,
            )
        if agent_id == "agent-harness-engineer":
            return await self._execute_harness_resume_plan(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "forward-deployed-engineer":
            return await self._execute_forward_deployed_feedback(
                message=message,
                context_summary=context_summary,
            )
        if (
            agent_id == "inference-systems-engineer"
            and message.task_type == "review_realtime_provider_failure"
        ):
            return await self._execute_realtime_provider_failure_review(
                message=message,
                context_summary=context_summary,
            )
        if agent_id in ARCHITECTURE_REVIEW_AGENT_PROFILES:
            return await self._execute_principal_architecture_review(
                message=message,
                agent_id=agent_id,
                context_summary=context_summary,
            )
        if agent_id == "claim-verification-agent":
            return await self._execute_claim_verification(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "a2a-protocol-agent":
            return await self._execute_a2a_protocol_audit(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "retrieval-intelligence-agent":
            return await self._execute_retrieval_intelligence_review(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "knowledge-graph-curator-agent":
            if message.task_type == "retrieve_project_memory":
                return await self._execute_project_memory_retrieval(
                    message=message,
                    context_summary=context_summary,
                )
            return await self._execute_knowledge_graph_curator_review(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "intent-router":
            return await self._execute_intent_route_plan(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "data-analyst-agent":
            return await self._execute_data_analysis(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "content-strategist":
            return await self._execute_content_strategy(
                message=message,
                context_summary=context_summary,
                request=request,
            )
        if agent_id in CONTENT_WRITER_AGENTS:
            return await self._execute_content_writer(
                message=message,
                agent_id=agent_id,
                context_summary=context_summary,
            )
        if agent_id == SCRIPT_DOCTOR_AGENT_ID:
            return await self._execute_script_doctor(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "guardrails-agent":
            return await self._execute_guardrail_review(
                message=message,
                context_summary=context_summary,
            )
        if agent_id in UX_REVIEW_AGENT_PROFILES:
            return await self._execute_ux_review(
                message=message,
                agent_id=agent_id,
                context_summary=context_summary,
            )
        if agent_id == "interactive-systems-designer":
            return await self._execute_interactive_systems_review(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "visual-director":
            return await self._execute_visual_direction_brief(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "image-generation-agent":
            return await self._execute_image_generation_prompt_pack(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "audio-producer":
            return await self._execute_audio_production_brief(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "video-reel-producer":
            return await self._execute_video_reel_storyboard(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "platform-optimization-agent":
            return await self._execute_distribution_packaging(
                message=message,
                agent_id=agent_id,
                context_summary=context_summary,
                request=request,
            )
        if agent_id == "influencer-strategy-agent":
            return await self._execute_influencer_strategy(
                message=message,
                context_summary=context_summary,
                request=request,
            )
        if agent_id == "outreach-agent":
            return await self._execute_outreach_strategy(
                message=message,
                context_summary=context_summary,
                request=request,
            )
        if agent_id in EDITORIAL_REVIEW_AGENTS:
            return await self._execute_editorial_review(
                message=message,
                agent_id=agent_id,
                context_summary=context_summary,
            )
        if agent_id == "artifact-librarian":
            return await self._execute_artifact_librarian_index(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "product-manager":
            if message.task_type == "record_project_memory":
                return await self._execute_project_memory_record(
                    message=message,
                    context_summary=context_summary,
                )
            if message.task_type == "retrieve_project_memory":
                return await self._execute_project_memory_retrieval(
                    message=message,
                    context_summary=context_summary,
                )
            return await self._execute_product_manager_sync(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "sprint-progress-agent":
            return await self._execute_sprint_work_plan(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "interactive-note-taking-agent":
            if message.task_type == "record_project_memory":
                return await self._execute_project_memory_record(
                    message=message,
                    context_summary=context_summary,
                )
            if message.task_type == "generate_obsidian_memory_promotion":
                return await self._execute_obsidian_memory_promotion_worker(
                    message=message,
                    context_summary=context_summary,
                )
            if message.task_type == "generate_obsidian_review_note":
                return await self._execute_obsidian_review_note_worker(
                    message=message,
                    context_summary=context_summary,
                )
            return await self._execute_interactive_note_worker(
                message=message,
                context_summary=context_summary,
            )
        if agent_id == "observability-agent":
            if message.task_type == "build_runtime_health_ledger":
                return await self._execute_runtime_health_ledger(
                    message=message,
                    context_summary=context_summary,
                )
            return await self._execute_observability_report(
                message=message,
                context_summary=context_summary,
            )
        if agent_id in {
            "visual-director",
            "audio-producer",
            "video-reel-producer",
        }:
            return await self._execute_media_planning(
                message=message,
                agent_id=agent_id,
                context_summary=context_summary,
                request=request,
            )
        return await self._execute_gemma_or_deterministic(
            message=message,
            agent_id=agent_id,
            context_summary=context_summary,
            request=request,
        )

    async def _execute_gemma_or_deterministic(
        self,
        *,
        message: AgentMessage,
        agent_id: str,
        context_summary: dict[str, Any],
        request: AgentWorkerRunRequest,
    ) -> dict[str, Any]:
        agent = get_agent_card(agent_id)
        if request.use_gemma and self._services.gemma_provider and agent is not None:
            model_id = _gemma_model_id(agent.allowed_models)
            await require_model_allowed(
                self._store,
                run_id=message.run_id,
                agent_id=agent_id,
                model_id=model_id,
                reason="agent_worker_gemma_completion",
                message_id=message.message_id,
                metadata={"task_type": message.task_type},
            )
            try:
                response = await self._services.gemma_provider.complete(
                    GemmaRequest(
                        model_id=model_id,
                        agent_id=agent_id,
                        system_context=(
                            f"You are {agent.name}. Complete the assigned A2A "
                            "task using only the supplied durable context. "
                            f"{_agent_memory_system_instruction(context_summary)}"
                            "Return concise structured work product text."
                        ),
                        user_input=json.dumps(
                            {
                                "task_type": message.task_type,
                                "payload": message.payload,
                                "context_summary": context_summary,
                                "active_skills": [
                                    skill.model_dump()
                                    for skill in skill_cards_for_agent(agent_id)
                                ],
                            },
                            indent=2,
                        ),
                        metadata={"workflow": "agent_worker_v1"},
                    )
                )
                await self._store.append_event(
                    RunEvent(
                        run_id=message.run_id,
                        event_type="gemma_worker_completed",
                        actor=agent_id,
                        payload={
                            "message_id": str(message.message_id),
                            "model_id": response.model_id,
                            "usage": response.usage,
                        },
                    )
                )
                return {
                    "generation_mode": "gemma_provider",
                    "summary": f"{agent.name} completed {message.task_type}.",
                    "content": response.content,
                    "model_id": response.model_id,
                    "usage": response.usage,
                    "context_summary": context_summary,
                    "skill_ids": context_summary.get("skill_ids", []),
                }
            except ProviderConfigurationError as exc:
                await self._store.append_event(
                    RunEvent(
                        run_id=message.run_id,
                        event_type="provider_fallback",
                        actor=agent_id,
                        payload={"provider": "gemma", "reason": str(exc)},
                    )
                )
                if request.fail_on_provider_error:
                    raise

        return _deterministic_task_result(
            agent_id=agent_id,
            task_type=message.task_type,
            payload=message.payload,
            context_summary=context_summary,
        )

    async def _execute_realtime_conversation_brief(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        run = await self._store.get_run(message.run_id)
        if run is None:
            raise AgentWorkerRunNotFoundError(f"Run not found: {message.run_id}")
        turns = await self._store.list_conversation_turns(message.run_id)
        realtime_sessions = await self._store.list_realtime_sessions(message.run_id)
        messages = await self._store.list_agent_messages(message.run_id)
        feedback_items = await self._store.list_feedback(message.run_id)
        events = await self._store.list_events(message.run_id, limit=200)
        brief_content = _realtime_conversation_brief_content(
            run=run,
            message=message,
            context_summary=context_summary,
            turns=turns,
            realtime_sessions=realtime_sessions,
            messages=messages,
            feedback_items=feedback_items,
            events=events,
        )
        topic = _topic_from_payload(message.payload)
        if topic == "the current user goal":
            topic = run.goal
        brief = ArtifactRecord(
            run_id=message.run_id,
            artifact_type=ArtifactType.REALTIME_CONVERSATION_BRIEF,
            title=f"Realtime conversation brief: {topic}",
            uri=(
                f"artifact://runs/{message.run_id}/realtime-conversation-briefs/"
                f"{message.message_id}"
            ),
            content=brief_content,
            provenance={
                "workflow": "realtime_conversation_host_worker_v1",
                "agent_id": "realtime-conversation-host",
                "message_id": str(message.message_id),
                "generation_mode": "deterministic_realtime_conversation_brief",
                "realtime_session_ids": [
                    str(session.realtime_session_id) for session in realtime_sessions
                ],
            },
            revision_history=[
                {
                    "actor": "realtime-conversation-host",
                    "workflow": "realtime_conversation_host_worker_v1",
                    "message_id": str(message.message_id),
                    "note": (
                        "Summarized realtime session state, turn-taking risks, "
                        "voice feedback, and specialist handoff recommendations."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(brief)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=brief.model_dump(mode="json"),
            )
        )
        created_handoffs, skipped_duplicate_handoff_count = (
            await self._create_realtime_conversation_handoff_tasks(
                message=message,
                brief=brief,
                brief_content=brief_content,
                topic=topic,
                context_summary=context_summary,
            )
        )
        brief.content["created_task_message_ids"] = [
            str(child.message_id) for child in created_handoffs
        ]
        brief.content["created_target_agent_ids"] = [
            child.recipient_agent_id for child in created_handoffs
        ]
        brief.content["skipped_duplicate_handoff_task_count"] = (
            skipped_duplicate_handoff_count
        )
        brief.revision_history.append(
            {
                "actor": "realtime-conversation-host",
                "workflow": "realtime_conversation_host_worker_v1",
                "message_id": str(message.message_id),
                "note": (
                    f"Materialized {len(created_handoffs)} downstream A2A "
                    "handoff task(s) from the realtime conversation brief."
                ),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        await self._store.update_artifact(brief)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="realtime_conversation_brief_created",
                actor="realtime-conversation-host",
                payload={
                    "message_id": str(message.message_id),
                    "brief_artifact_id": str(brief.artifact_id),
                    "realtime_session_count": len(realtime_sessions),
                    "turn_count": len(turns),
                    "voice_feedback_count": brief_content["voice_feedback_count"],
                    "recommended_handoff_agent_ids": [
                        item["target_agent_id"]
                        for item in brief_content["recommended_handoffs"]
                    ],
                    "created_task_message_ids": [
                        str(child.message_id) for child in created_handoffs
                    ],
                    "created_target_agent_ids": [
                        child.recipient_agent_id for child in created_handoffs
                    ],
                    "skipped_duplicate_handoff_task_count": (
                        skipped_duplicate_handoff_count
                    ),
                },
            )
        )
        return {
            "generation_mode": "realtime_conversation_host_worker",
            "summary": (
                "realtime-conversation-host recorded a realtime conversation "
                f"brief across {len(realtime_sessions)} session(s) and "
                f"{len(turns)} turn(s)."
            ),
            "brief_artifact_id": str(brief.artifact_id),
            "realtime_session_count": len(realtime_sessions),
            "turn_count": len(turns),
            "voice_feedback_count": brief_content["voice_feedback_count"],
            "created_task_message_ids": [
                str(child.message_id) for child in created_handoffs
            ],
            "created_target_agent_ids": [
                child.recipient_agent_id for child in created_handoffs
            ],
            "skipped_duplicate_handoff_task_count": skipped_duplicate_handoff_count,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _create_realtime_conversation_handoff_tasks(
        self,
        *,
        message: AgentMessage,
        brief: ArtifactRecord,
        brief_content: dict[str, Any],
        topic: str,
        context_summary: dict[str, Any],
    ) -> tuple[list[AgentMessage], int]:
        created: list[AgentMessage] = []
        skipped_duplicate_count = 0
        for handoff in brief_content["recommended_handoffs"]:
            target_agent_id = handoff["target_agent_id"]
            if target_agent_id == "realtime-conversation-host":
                continue
            child = AgentMessage(
                message_id=_realtime_handoff_message_id(
                    message=message,
                    target_agent_id=target_agent_id,
                    task_type=handoff["task_type"],
                ),
                run_id=message.run_id,
                sender_agent_id="realtime-conversation-host",
                recipient_agent_id=target_agent_id,
                task_type=handoff["task_type"],
                payload={
                    "workflow": "realtime_conversation_handoff_v1",
                    "topic": topic,
                    "parent_message_id": str(message.message_id),
                    "brief_artifact_id": str(brief.artifact_id),
                    "source_task_type": message.task_type,
                    "handoff_reason": handoff["reason"],
                    "recommended_handoff": handoff,
                    "realtime_session_inventory": brief_content["session_inventory"],
                    "turn_inventory": brief_content["turn_inventory"],
                    "control_event_inventory": brief_content[
                        "control_event_inventory"
                    ],
                    "voice_feedback_count": brief_content["voice_feedback_count"],
                    "transcript": _realtime_brief_transcript_excerpt(brief_content),
                    "requested_intent": message.payload.get("requested_intent", "auto"),
                    "routed_intent": message.payload.get("routed_intent", "route_task"),
                    "target_formats": message.payload.get("target_formats", []),
                    "context_summary": context_summary,
                },
            )
            recorded_child = await self._record_agent_message_if_absent(child)
            if recorded_child is None:
                skipped_duplicate_count += 1
                continue
            created.append(recorded_child)
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="agent_message_accepted",
                    actor="realtime-conversation-host",
                    payload=public_a2a_message_event_payload(recorded_child),
                )
            )
        return created, skipped_duplicate_count

    async def _record_agent_message_if_absent(
        self,
        message: AgentMessage,
    ) -> AgentMessage | None:
        recorder = getattr(self._store, "record_agent_message_if_absent", None)
        if callable(recorder):
            return await recorder(message)
        raise RuntimeError(
            "Realtime handoff task creation requires "
            "store.record_agent_message_if_absent for idempotent writes."
        )

    async def _record_artifact_if_absent(
        self,
        artifact: ArtifactRecord,
    ) -> ArtifactRecord | None:
        recorder = getattr(self._store, "record_artifact_if_absent", None)
        if callable(recorder):
            return await recorder(artifact)
        raise RuntimeError(
            "Agent worker artifact creation requires store.record_artifact_if_absent "
            "for idempotent writes."
        )

    async def _execute_retrieval_intelligence_review(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        payload = message.payload if isinstance(message.payload, dict) else {}
        topic = _topic_from_payload(payload)
        ledger = await RetrievalQualityLedgerWorkflow(
            self._store,
            _SourceRefreshRetrievalRerankerFallback(
                store=self._store,
                run_id=message.run_id,
                primary_reranker=self._services.reranker_provider,
                actor="retrieval-intelligence-agent",
            )
            if self._services.reranker_provider
            else None,
        ).build(
            message.run_id,
            RetrievalQualityLedgerRequest(
                record_artifact=bool(payload.get("record_artifact", True)),
                topic=topic,
                candidate_window=_bounded_int(
                    payload.get("candidate_window"),
                    default=30,
                    minimum=5,
                    maximum=200,
                ),
                min_accepted_sources=_bounded_int(
                    payload.get("min_accepted_sources"),
                    default=2,
                    minimum=1,
                    maximum=25,
                ),
                require_reranking=bool(payload.get("require_reranking", True)),
                require_graph_coverage=bool(
                    payload.get("require_graph_coverage", True)
                ),
            ),
        )
        followups = await self._create_retrieval_quality_research_followups(
            message=message,
            sender_agent_id="retrieval-intelligence-agent",
            topic=topic,
            ledger=ledger,
            enabled=bool(payload.get("create_research_followups", True)),
            max_followups=_bounded_int(
                payload.get("max_research_followups"),
                default=2,
                minimum=0,
                maximum=5,
            ),
        )
        return {
            "generation_mode": "retrieval_intelligence_worker",
            "summary": (
                f"retrieval-intelligence-agent built retrieval quality ledger "
                f"for {topic}: {ledger.status.value}, "
                f"{ledger.accepted_candidate_count}/{ledger.candidate_count} "
                "accepted candidate(s)."
            ),
            "topic": topic,
            "retrieval_quality_ledger": _retrieval_quality_result_summary(ledger),
            "recommended_queries": ledger.recommended_queries,
            "candidate_ids": [candidate.candidate_id for candidate in ledger.candidates],
            "accepted_source_ids": [
                str(candidate.source_id)
                for candidate in ledger.candidates
                if candidate.source_id and candidate.accepted_for_context
            ],
            "research_followups": followups,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_knowledge_graph_curator_review(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        payload = message.payload if isinstance(message.payload, dict) else {}
        topic = _topic_from_payload(payload)
        ledger = await RetrievalQualityLedgerWorkflow(
            self._store,
            _SourceRefreshRetrievalRerankerFallback(
                store=self._store,
                run_id=message.run_id,
                primary_reranker=self._services.reranker_provider,
                actor="knowledge-graph-curator-agent",
            )
            if self._services.reranker_provider
            else None,
        ).build(
            message.run_id,
            RetrievalQualityLedgerRequest(
                record_artifact=bool(payload.get("record_artifact", True)),
                topic=topic,
                candidate_window=_bounded_int(
                    payload.get("candidate_window"),
                    default=30,
                    minimum=5,
                    maximum=200,
                ),
                min_accepted_sources=_bounded_int(
                    payload.get("min_accepted_sources"),
                    default=2,
                    minimum=1,
                    maximum=25,
                ),
                require_reranking=bool(payload.get("require_reranking", True)),
                require_graph_coverage=True,
            ),
        )
        graph = _knowledge_graph_worker_summary(ledger.graph_coverage)
        followups = await self._create_retrieval_quality_research_followups(
            message=message,
            sender_agent_id="knowledge-graph-curator-agent",
            topic=topic,
            ledger=ledger,
            enabled=bool(payload.get("create_research_followups", False)),
            max_followups=_bounded_int(
                payload.get("max_research_followups"),
                default=2,
                minimum=0,
                maximum=5,
            ),
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="knowledge_graph_curated",
                actor="knowledge-graph-curator-agent",
                payload={
                    "topic": topic,
                    "message_id": str(message.message_id),
                    "retrieval_quality_ledger_artifact_id": (
                        str(ledger.ledger_artifact_id)
                        if ledger.ledger_artifact_id
                        else None
                    ),
                    "node_count": graph["node_count"],
                    "edge_count": len(graph["traversal_edges"]),
                    "coverage_gap_count": graph["coverage_gap_count"],
                    "node_type_counts": graph["node_type_counts"],
                    "coverage_status_counts": graph["coverage_status_counts"],
                },
            )
        )
        return {
            "generation_mode": "knowledge_graph_curator_worker",
            "summary": (
                "knowledge-graph-curator-agent recorded "
                f"{graph['node_count']} graph node(s), "
                f"{len(graph['traversal_edges'])} traversal edge(s), and "
                f"{graph['coverage_gap_count']} coverage gap(s) for {topic}."
            ),
            "topic": topic,
            "knowledge_graph": graph,
            "retrieval_quality_ledger": _retrieval_quality_result_summary(ledger),
            "research_followups": followups,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _create_retrieval_quality_research_followups(
        self,
        *,
        message: AgentMessage,
        sender_agent_id: str,
        topic: str,
        ledger,
        enabled: bool,
        max_followups: int,
    ) -> dict[str, Any]:
        if not enabled or max_followups <= 0 or ledger.status.value == "ready":
            return {
                "enabled": enabled,
                "created_count": 0,
                "skipped_duplicate_count": 0,
                "created_message_ids": [],
                "recommended_queries": ledger.recommended_queries,
            }
        created: list[AgentMessage] = []
        skipped_duplicate_count = 0
        for index, query in enumerate(ledger.recommended_queries[:max_followups], start=1):
            task_type = f"research_retrieval_quality_gap_{index}"
            child = AgentMessage(
                message_id=_agent_worker_child_message_id(
                    run_id=message.run_id,
                    parent_message_id=message.message_id,
                    sender_agent_id=sender_agent_id,
                    recipient_agent_id="web-research-agent",
                    task_type=task_type,
                ),
                run_id=message.run_id,
                sender_agent_id=sender_agent_id,
                recipient_agent_id="web-research-agent",
                task_type=task_type,
                payload={
                    "workflow": "retrieval_quality_gap_handoff_v1",
                    "topic": topic,
                    "search_queries": [query],
                    "parent_message_id": str(message.message_id),
                    "retrieval_quality_status": ledger.status.value,
                    "retrieval_quality_ledger_artifact_id": (
                        str(ledger.ledger_artifact_id)
                        if ledger.ledger_artifact_id
                        else None
                    ),
                    "accepted_candidate_count": ledger.accepted_candidate_count,
                    "candidate_count": ledger.candidate_count,
                    "precision_risk_count": ledger.precision_risk_count,
                    "recall_gap_count": ledger.recall_gap_count,
                    "coverage_gap_count": ledger.coverage_gap_count,
                    "handoff_reason": (
                        "Retrieval quality found recall, precision, or graph "
                        "coverage gaps that need provider-backed research."
                    ),
                },
            )
            recorded_child = await self._record_agent_message_if_absent(child)
            if recorded_child is None:
                skipped_duplicate_count += 1
                continue
            created.append(recorded_child)
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="agent_message_accepted",
                    actor=sender_agent_id,
                    payload=public_a2a_message_event_payload(recorded_child),
                )
            )
        return {
            "enabled": enabled,
            "created_count": len(created),
            "skipped_duplicate_count": skipped_duplicate_count,
            "created_message_ids": [str(child.message_id) for child in created],
            "recommended_queries": ledger.recommended_queries,
        }

    async def _execute_web_research(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
        request: AgentWorkerRunRequest,
    ) -> dict[str, Any]:
        topic = _topic_from_payload(message.payload)
        search_queries, skipped_search_query_count = _search_queries_from_payload(
            message.payload, fallback_topic=topic
        )
        if self._services.search_provider:
            await require_tool_allowed(
                self._store,
                run_id=message.run_id,
                agent_id="web-research-agent",
                tool_name="web_search",
                reason="worker_web_research_provider_search",
                message_id=message.message_id,
                metadata={
                    "topic": topic,
                    "search_queries": search_queries,
                    "skipped_search_query_count": skipped_search_query_count,
                },
            )
            try:
                provider_results: list[tuple[str, int, SearchResult]] = []
                provider_result_count = 0
                for query in search_queries:
                    query_results = await self._services.search_provider.search(
                        SearchRequest(query=query, freshness="current", max_results=5)
                    )
                    provider_result_count += len(query_results)
                    provider_results.extend(
                        (query, index, result)
                        for index, result in enumerate(query_results, start=1)
                    )
            except ProviderConfigurationError as exc:
                safe_reason = _redact_provider_failure_text(str(exc))
                await self._store.append_event(
                    RunEvent(
                        run_id=message.run_id,
                        event_type="provider_fallback",
                        actor="web-research-agent",
                        payload={"provider": "web_search", "reason": safe_reason},
                    )
                )
                if not request.use_gemma:
                    return await self._web_research_blocked_result(
                        message=message,
                        topic=topic,
                        context_summary=context_summary,
                        reason=safe_reason,
                        blocker="web_search_provider_configuration",
                    )
            else:
                source_ids = []
                recorded_sources = []
                ranked_results, rerank_metadata = await _rank_provider_search_results(
                    topic=topic,
                    provider_results=provider_results,
                    reranker_provider=self._services.reranker_provider,
                )
                if rerank_metadata.get("reranker_fallback_reason"):
                    await self._store.append_event(
                        RunEvent(
                            run_id=message.run_id,
                            event_type="provider_fallback",
                            actor="web-research-agent",
                            payload={
                                "provider": "retrieval_reranker",
                                "reason": rerank_metadata[
                                    "reranker_fallback_reason"
                                ],
                            },
                        )
                    )
                citation_number = _next_citation_number(
                    await self._store.list_sources(message.run_id)
                )
                for query, query_rank, result, rerank_result in ranked_results:
                    published_at = _parse_provider_datetime(result.published_at)
                    retrieved_at = _parse_provider_datetime(result.retrieved_at)
                    source = SourceRecord(
                        run_id=message.run_id,
                        citation_id=f"S{citation_number + len(recorded_sources)}",
                        title=result.title,
                        url=result.url,
                        publisher=result.publisher,
                        retrieved_at=retrieved_at or datetime.now(timezone.utc),
                        published_at=published_at,
                        metadata={
                            "source_type": "worker_web_search_result",
                            "snippet": result.snippet,
                            "published_at": result.published_at,
                            "retrieved_at": result.retrieved_at,
                            "search_query": query,
                            "retriever": "web_search",
                            "search_rank": query_rank,
                            "rerank_rank": rerank_result.rank_after,
                            "rerank_rank_before": rerank_result.rank_before,
                            "rerank_score": rerank_result.relevance_score,
                            "reranker": rerank_metadata.get("reranker"),
                            "rerank_reason": rerank_result.reason,
                            "freshness": "current",
                            "max_results": 5,
                            "agent_id": "web-research-agent",
                            "message_id": str(message.message_id),
                        },
                    )
                    await self._store.record_source(source)
                    await self._store.append_event(
                        RunEvent(
                            run_id=message.run_id,
                            event_type="source_recorded",
                            actor="source-ledger-agent",
                            payload=source.model_dump(mode="json"),
                        )
                    )
                    source_ids.append(str(source.source_id))
                    recorded_sources.append(source)
                web_research_event = await self._store.append_event(
                    RunEvent(
                        run_id=message.run_id,
                        event_type="web_research_completed",
                        actor="web-research-agent",
                        payload={
                            "query": topic,
                            "queries": search_queries,
                            "provider_query_count": len(search_queries),
                            "skipped_query_count": skipped_search_query_count,
                            "freshness": "current",
                            "max_results": 5,
                            "provider_result_count": provider_result_count,
                            "accepted_source_count": len(recorded_sources),
                            "deduplicated_result_count": (
                                provider_result_count - len(recorded_sources)
                            ),
                            "reranker": rerank_metadata.get("reranker"),
                            "reranked_result_count": len(ranked_results),
                            "reranker_fallback_reason": rerank_metadata.get(
                                "reranker_fallback_reason"
                            ),
                            "source_ids": source_ids,
                            "citation_ids": [
                                source.citation_id for source in recorded_sources
                            ],
                            "source_titles": [
                                source.title for source in recorded_sources
                            ],
                            "message_id": str(message.message_id),
                        },
                    )
                )
                source_repair = await self._repair_source_dependencies(
                    run_id=message.run_id,
                    replacement_sources=recorded_sources,
                )
                freshness_ledger = await ResearchFreshnessLedgerWorkflow(
                    self._store
                ).build(message.run_id, ResearchFreshnessLedgerRequest(topic=topic))
                retrieval_quality_ledger = await self._build_source_refresh_retrieval_quality(
                    run_id=message.run_id,
                    topic=topic,
                    reranker_provider=None
                    if rerank_metadata.get("reranker_fallback_reason")
                    else self._services.reranker_provider,
                )
                claim_followup = await self._create_source_refresh_claim_followup(
                    message=message,
                    topic=topic,
                    replacement_sources=recorded_sources,
                    source_repair=source_repair,
                    freshness_ledger=freshness_ledger,
                    retrieval_quality_ledger=retrieval_quality_ledger,
                )
                return {
                    "generation_mode": "web_search_provider",
                    "summary": (
                        f"web-research-agent recorded {len(source_ids)} "
                        f"source(s) for {topic} and repaired "
                        f"{source_repair['claim_count']} claim(s), "
                        f"{source_repair['artifact_count']} artifact(s); "
                        f"freshness status is {freshness_ledger.status.value}; "
                        f"claim verification follow-up is {claim_followup['status']}; "
                        f"skipped {skipped_search_query_count} capped search query(ies)."
                    ),
                    "source_ids": source_ids,
                    "web_research": {
                        "event_id": web_research_event.event_id,
                        "provider_result_count": provider_result_count,
                        "accepted_source_count": len(recorded_sources),
                        "deduplicated_result_count": (
                            provider_result_count - len(recorded_sources)
                        ),
                        "reranker": rerank_metadata.get("reranker"),
                        "reranked_result_count": len(ranked_results),
                        "reranker_fallback_reason": rerank_metadata.get(
                            "reranker_fallback_reason"
                        ),
                        "queries": search_queries,
                        "provider_query_count": len(search_queries),
                        "skipped_query_count": skipped_search_query_count,
                        "citation_ids": [
                            source.citation_id for source in recorded_sources
                        ],
                    },
                    "source_repair": source_repair,
                    "claim_verification_followup": claim_followup,
                    "research_freshness_ledger": {
                        "status": freshness_ledger.status.value,
                        "ledger_artifact_id": (
                            str(freshness_ledger.ledger_artifact_id)
                            if freshness_ledger.ledger_artifact_id
                            else None
                        ),
                        "accepted_source_count": (
                            freshness_ledger.accepted_source_count
                        ),
                        "seed_source_count": freshness_ledger.seed_source_count,
                        "needs_review_source_count": (
                            freshness_ledger.needs_review_source_count
                        ),
                    },
                    "retrieval_quality_ledger": _retrieval_quality_result_summary(
                        retrieval_quality_ledger
                    ),
                    "topic": topic,
                    "context_summary": context_summary,
                    "skill_ids": context_summary.get("skill_ids", []),
                }

        if not request.use_gemma:
            return await self._web_research_blocked_result(
                message=message,
                topic=topic,
                context_summary=context_summary,
                reason="No provider-backed web search provider is configured.",
                blocker="web_search_provider_missing",
            )

        return await self._execute_gemma_or_deterministic(
            message=message,
            agent_id="web-research-agent",
            context_summary=context_summary,
            request=request,
        )

    async def _build_source_refresh_retrieval_quality(
        self,
        *,
        run_id: UUID,
        topic: str,
        reranker_provider,
    ):
        fallback_reranker = (
            _SourceRefreshRetrievalRerankerFallback(
                store=self._store,
                run_id=run_id,
                primary_reranker=reranker_provider,
                actor="web-research-agent",
            )
            if reranker_provider
            else None
        )
        return await RetrievalQualityLedgerWorkflow(
            self._store,
            fallback_reranker,
        ).build(run_id, RetrievalQualityLedgerRequest(topic=topic))

    async def _web_research_blocked_result(
        self,
        *,
        message: AgentMessage,
        topic: str,
        context_summary: dict[str, Any],
        reason: str,
        blocker: str,
    ) -> dict[str, Any]:
        safe_reason = _redact_provider_failure_text(reason)
        freshness_ledger = await ResearchFreshnessLedgerWorkflow(self._store).build(
            message.run_id,
            ResearchFreshnessLedgerRequest(topic=topic),
        )
        blocked_event = await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="web_research_blocked",
                actor="web-research-agent",
                payload={
                    "query": topic,
                    "blocker": blocker,
                    "reason": safe_reason,
                    "message_id": str(message.message_id),
                    "freshness_status": freshness_ledger.status.value,
                    "seed_source_count": freshness_ledger.seed_source_count,
                    "accepted_source_count": freshness_ledger.accepted_source_count,
                    "ledger_artifact_id": (
                        str(freshness_ledger.ledger_artifact_id)
                        if freshness_ledger.ledger_artifact_id
                        else None
                    ),
                },
            )
        )
        return {
            "generation_mode": "web_search_provider_blocked",
            "summary": (
                f"Provider-backed web research is blocked for {topic}: {safe_reason}"
            ),
            "source_ids": [],
            "web_research": {
                "status": "blocked",
                "blocker": blocker,
                "reason": safe_reason,
                "event_id": blocked_event.event_id,
                "accepted_source_count": 0,
            },
            "research_freshness_ledger": {
                "status": freshness_ledger.status.value,
                "ledger_artifact_id": (
                    str(freshness_ledger.ledger_artifact_id)
                    if freshness_ledger.ledger_artifact_id
                    else None
                ),
                "accepted_source_count": freshness_ledger.accepted_source_count,
                "seed_source_count": freshness_ledger.seed_source_count,
                "needs_review_source_count": (
                    freshness_ledger.needs_review_source_count
                ),
            },
            "topic": topic,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _create_source_refresh_claim_followup(
        self,
        *,
        message: AgentMessage,
        topic: str,
        replacement_sources: list[SourceRecord],
        source_repair: dict[str, Any],
        freshness_ledger,
        retrieval_quality_ledger,
    ) -> dict[str, Any]:
        claim_ids = list(source_repair.get("claim_ids", []))
        source_ids = [str(source.source_id) for source in replacement_sources]
        if not claim_ids:
            return {
                "status": "not_needed",
                "reason": "no_repaired_claims",
                "message_id": None,
                "skipped_existing_task_count": 0,
            }

        existing_messages = await self._store.list_agent_messages(
            message.run_id,
            agent_id="claim-verification-agent",
            direction="inbox",
            limit=500,
        )
        active_claim_tasks = [
            existing
            for existing in existing_messages
            if existing.status
            in {
                AgentTaskStatus.ACCEPTED,
                AgentTaskStatus.CLAIMED,
                AgentTaskStatus.IN_PROGRESS,
            }
            and existing.task_type in CLAIM_VERIFICATION_TASK_TYPES
        ]
        if active_claim_tasks:
            return {
                "status": "existing_runnable_task",
                "reason": "claim_verification_already_queued",
                "message_id": str(active_claim_tasks[0].message_id),
                "skipped_existing_task_count": len(active_claim_tasks),
            }

        child = AgentMessage(
            message_id=_agent_worker_child_message_id(
                run_id=message.run_id,
                parent_message_id=message.message_id,
                sender_agent_id="web-research-agent",
                recipient_agent_id="claim-verification-agent",
                task_type="verify_source_refresh_claims",
            ),
            run_id=message.run_id,
            sender_agent_id="web-research-agent",
            recipient_agent_id="claim-verification-agent",
            task_type="verify_source_refresh_claims",
            depends_on_message_ids=[message.message_id],
            payload={
                "workflow": "source_refresh_claim_verification_handoff_v1",
                "topic": topic,
                "parent_message_id": str(message.message_id),
                "source_ids": source_ids,
                "claim_ids": claim_ids,
                "source_repair": source_repair,
                "freshness_status": freshness_ledger.status.value,
                "freshness_ledger_artifact_id": (
                    str(freshness_ledger.ledger_artifact_id)
                    if freshness_ledger.ledger_artifact_id
                    else None
                ),
                "retrieval_quality_status": retrieval_quality_ledger.status.value,
                "retrieval_quality_ledger_artifact_id": (
                    str(retrieval_quality_ledger.ledger_artifact_id)
                    if retrieval_quality_ledger.ledger_artifact_id
                    else None
                ),
                "accepted_retrieval_source_count": (
                    retrieval_quality_ledger.accepted_candidate_count
                ),
                "handoff_reason": (
                    "Provider-backed web research replaced weak or search-seed "
                    "source dependencies; claims must be re-verified before "
                    "drafts are treated as publishable."
                ),
            },
        )
        recorded_child = await self._record_agent_message_if_absent(child)
        if recorded_child is None:
            return {
                "status": "duplicate_suppressed",
                "reason": "claim_verification_followup_already_exists",
                "message_id": str(child.message_id),
                "skipped_existing_task_count": 1,
            }
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="agent_message_accepted",
                actor="web-research-agent",
                payload=public_a2a_message_event_payload(recorded_child),
            )
        )
        return {
            "status": "created",
            "reason": "repaired_claims_need_verification",
            "message_id": str(recorded_child.message_id),
            "skipped_existing_task_count": 0,
        }

    async def _repair_source_dependencies(
        self,
        *,
        run_id,
        replacement_sources: list[SourceRecord],
    ) -> dict[str, Any]:
        current_sources = await self._store.list_sources(run_id)
        source_by_id = {source.source_id: source for source in current_sources}
        weak_source_ids = {
            source.source_id
            for source in current_sources
            if evaluate_source_quality(source).quality_status == SourceQualityStatus.WEAK
        }
        replacement_source_ids = [
            source.source_id
            for source in replacement_sources
            if evaluate_source_quality(source).quality_status != SourceQualityStatus.WEAK
        ]
        if not replacement_source_ids:
            return {
                "claim_count": 0,
                "artifact_count": 0,
                "claim_ids": [],
                "artifact_ids": [],
                "replacement_source_ids": [],
                "weak_source_ids": [str(source_id) for source_id in weak_source_ids],
            }

        repaired_claim_ids = []
        for claim in await self._store.list_claims(run_id):
            if not _source_ids_need_repair(
                claim.source_ids,
                source_by_id=source_by_id,
                weak_source_ids=weak_source_ids,
            ):
                continue
            original_source_ids = list(claim.source_ids)
            claim.source_ids = _repaired_source_ids(
                claim.source_ids,
                replacement_source_ids=replacement_source_ids,
                source_by_id=source_by_id,
                weak_source_ids=weak_source_ids,
            )
            claim.support_status = ClaimSupportStatus.NEEDS_REVIEW
            claim.reviewer_agent_id = "source-ledger-agent"
            claim.notes = (
                "Source grounding repair replaced missing or weak source "
                f"dependencies {', '.join(str(source_id) for source_id in original_source_ids) or 'none'}; "
                "claim verification must re-evaluate support status."
            )
            await self._store.update_claim(claim)
            repaired_claim_ids.append(str(claim.claim_id))

        repaired_artifact_ids = []
        for artifact in await self._store.list_artifacts(run_id):
            if artifact.artifact_type not in SOURCE_REPAIR_ARTIFACT_TYPES:
                continue
            if not _source_ids_need_repair(
                artifact.source_ids,
                source_by_id=source_by_id,
                weak_source_ids=weak_source_ids,
            ):
                continue
            original_source_ids = list(artifact.source_ids)
            artifact.source_ids = _repaired_source_ids(
                artifact.source_ids,
                replacement_source_ids=replacement_source_ids,
                source_by_id=source_by_id,
                weak_source_ids=weak_source_ids,
            )
            artifact.provenance["source_ids"] = [
                str(source_id) for source_id in artifact.source_ids
            ]
            artifact.content["source_ids"] = [
                str(source_id) for source_id in artifact.source_ids
            ]
            if "source_dependencies" in artifact.content:
                artifact.content["source_dependencies"] = (
                    _source_dependency_snapshots(
                        source_ids=artifact.source_ids,
                        source_by_id=source_by_id,
                    )
                )
            artifact.provenance.setdefault("source_grounding_repairs", []).append(
                {
                    "actor": "source-ledger-agent",
                    "original_source_ids": [
                        str(source_id) for source_id in original_source_ids
                    ],
                    "replacement_source_ids": [
                        str(source_id) for source_id in replacement_source_ids
                    ],
                    "reason": "replace_missing_or_weak_source_dependencies",
                }
            )
            artifact.revision_history.append(
                {
                    "actor": "source-ledger-agent",
                    "note": "Repaired weak or missing source dependencies after web research.",
                }
            )
            await self._store.update_artifact(artifact)
            repaired_artifact_ids.append(str(artifact.artifact_id))

        if repaired_claim_ids or repaired_artifact_ids:
            await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="source_grounding_repaired",
                    actor="source-ledger-agent",
                    payload={
                        "claim_ids": repaired_claim_ids,
                        "artifact_ids": repaired_artifact_ids,
                        "replacement_source_ids": [
                            str(source_id) for source_id in replacement_source_ids
                        ],
                        "weak_source_ids": [
                            str(source_id) for source_id in weak_source_ids
                        ],
                    },
                )
            )

        return {
            "claim_count": len(repaired_claim_ids),
            "artifact_count": len(repaired_artifact_ids),
            "claim_ids": repaired_claim_ids,
            "artifact_ids": repaired_artifact_ids,
            "replacement_source_ids": [
                str(source_id) for source_id in replacement_source_ids
            ],
            "weak_source_ids": [str(source_id) for source_id in weak_source_ids],
        }

    async def _execute_claim_verification(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        await require_tool_allowed(
            self._store,
            run_id=message.run_id,
            agent_id="claim-verification-agent",
            tool_name="source_ledger",
            reason="claim_verification_reads_source_ledger",
            message_id=message.message_id,
        )
        claims = await self._store.list_claims(message.run_id)
        sources = await self._store.list_sources(message.run_id)
        artifacts = await self._store.list_artifacts(message.run_id)
        source_by_id = {source.source_id: source for source in sources}
        retrieval_evidence_by_source_id = accepted_retrieval_evidence_by_source(
            artifacts
        )
        retrieval_ledger = latest_retrieval_quality_ledger(artifacts)
        enforce_retrieval_evidence = retrieval_ledger is not None
        supported = []
        needs_review = []
        unsupported = []
        missing_sources = []
        accepted_retrieval_claims = []
        missing_accepted_retrieval_claims = []
        updated_claim_ids = []
        reviewed_claims_by_id = {}
        for claim in claims:
            reviewed_claim = _review_claim_support(
                claim,
                source_by_id,
                retrieval_evidence_by_source_id=retrieval_evidence_by_source_id,
                enforce_retrieval_evidence=enforce_retrieval_evidence,
            )
            reviewed_claims_by_id[claim.claim_id] = reviewed_claim
            if reviewed_claim["missing_source_ids"]:
                missing_sources.append(str(claim.claim_id))
            if reviewed_claim["accepted_retrieval_source_ids"]:
                accepted_retrieval_claims.append(str(claim.claim_id))
            if reviewed_claim["missing_accepted_retrieval_evidence"]:
                missing_accepted_retrieval_claims.append(str(claim.claim_id))
            if reviewed_claim["status"] == ClaimSupportStatus.SUPPORTED:
                supported.append(str(claim.claim_id))
            elif reviewed_claim["status"] == ClaimSupportStatus.UNSUPPORTED:
                unsupported.append(str(claim.claim_id))
            else:
                needs_review.append(str(claim.claim_id))
            if _claim_needs_update(
                claim=claim,
                status=reviewed_claim["status"],
                notes=reviewed_claim["notes"],
            ):
                claim.support_status = reviewed_claim["status"]
                claim.reviewer_agent_id = "claim-verification-agent"
                claim.notes = reviewed_claim["notes"]
                await self._store.update_claim(claim)
                updated_claim_ids.append(str(claim.claim_id))
        claim_revision_plan_artifact = await self._record_claim_revision_plan_if_needed(
            message=message,
            claims=claims,
            artifacts=artifacts,
            source_by_id=source_by_id,
            reviewed_claims_by_id=reviewed_claims_by_id,
            retrieval_evidence_by_source_id=retrieval_evidence_by_source_id,
            retrieval_ledger=retrieval_ledger,
        )
        created_revision_followups, skipped_revision_followups = (
            await self._materialize_claim_revision_followups(
                message=message,
                claim_revision_plan_artifact=claim_revision_plan_artifact,
                artifacts=artifacts,
                retrieval_ledger=retrieval_ledger,
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="claim_verification_completed",
                actor="claim-verification-agent",
                payload={
                    "message_id": str(message.message_id),
                    "supported": len(supported),
                    "needs_review": len(needs_review),
                    "unsupported": len(unsupported),
                    "missing_sources": len(missing_sources),
                    "accepted_retrieval_claims": len(accepted_retrieval_claims),
                    "missing_accepted_retrieval_claims": len(
                        missing_accepted_retrieval_claims
                    ),
                    "retrieval_evidence_required": enforce_retrieval_evidence,
                    "retrieval_ledger_artifact_id": (
                        str(retrieval_ledger.artifact_id)
                        if retrieval_ledger
                        else None
                    ),
                    "claim_revision_plan_artifact_id": (
                        str(claim_revision_plan_artifact.artifact_id)
                        if claim_revision_plan_artifact
                        else None
                    ),
                    "created_followup_message_ids": [
                        str(followup.message_id)
                        for followup in created_revision_followups
                    ],
                    "created_followup_count": len(created_revision_followups),
                    "skipped_duplicate_followups": skipped_revision_followups,
                    "updated_claim_ids": updated_claim_ids,
                },
            )
        )
        return {
            "generation_mode": "claim_verification_worker",
            "summary": (
                f"claim-verification-agent reviewed {len(claims)} claim(s): "
                f"{len(supported)} supported, {len(needs_review)} need review, "
                f"{len(unsupported)} unsupported."
            ),
            "supported_claim_ids": supported,
            "needs_review_claim_ids": needs_review,
            "unsupported_claim_ids": unsupported,
            "missing_source_claim_ids": missing_sources,
            "accepted_retrieval_claim_ids": accepted_retrieval_claims,
            "missing_accepted_retrieval_claim_ids": (
                missing_accepted_retrieval_claims
            ),
            "retrieval_evidence_required": enforce_retrieval_evidence,
            "claim_revision_plan_artifact_id": (
                str(claim_revision_plan_artifact.artifact_id)
                if claim_revision_plan_artifact
                else None
            ),
            "created_followup_message_ids": [
                str(followup.message_id) for followup in created_revision_followups
            ],
            "skipped_duplicate_followups": skipped_revision_followups,
            "updated_claim_ids": updated_claim_ids,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _record_claim_revision_plan_if_needed(
        self,
        *,
        message: AgentMessage,
        claims: list[ClaimRecord],
        artifacts: list[ArtifactRecord],
        source_by_id: dict[UUID, SourceRecord],
        reviewed_claims_by_id: dict[UUID, dict[str, Any]],
        retrieval_evidence_by_source_id: dict[UUID, Any],
        retrieval_ledger: ArtifactRecord | None,
    ) -> ArtifactRecord | None:
        plan = _claim_revision_plan_content(
            claims=claims,
            source_by_id=source_by_id,
            reviewed_claims_by_id=reviewed_claims_by_id,
            retrieval_evidence_by_source_id=retrieval_evidence_by_source_id,
            retrieval_ledger=retrieval_ledger,
        )
        if not plan["held_claims"]:
            return None
        target_artifacts = _claim_revision_target_artifacts(
            artifacts,
            [UUID(item["claim_id"]) for item in plan["held_claims"]],
        )
        plan["target_artifact_ids"] = [
            str(artifact.artifact_id) for artifact in target_artifacts
        ]
        plan["target_artifact_types"] = [
            artifact.artifact_type.value for artifact in target_artifacts
        ]
        claim_ids = [UUID(item["claim_id"]) for item in plan["held_claims"]]
        source_ids = [
            UUID(item["source_id"])
            for item in plan["accepted_source_alternatives"]
        ]
        artifact = ArtifactRecord(
            run_id=message.run_id,
            artifact_type=ArtifactType.CLAIM_REVISION_PLAN,
            title="Claim rewrite and hold plan",
            uri=(
                f"artifact://runs/{message.run_id}/claim-revision-plan/"
                f"{message.message_id}"
            ),
            content=plan,
            provenance={
                "workflow": "claim_revision_plan_v1",
                "agent_id": "claim-verification-agent",
                "message_id": str(message.message_id),
                "claim_ids": [str(claim_id) for claim_id in claim_ids],
                "source_ids": [str(source_id) for source_id in source_ids],
                "retrieval_ledger_artifact_id": (
                    str(retrieval_ledger.artifact_id)
                    if retrieval_ledger
                    else None
                ),
                "generation_mode": "deterministic_claim_revision_plan",
            },
            source_ids=source_ids,
            revision_history=[
                {
                    "actor": "claim-verification-agent",
                    "workflow": "claim_revision_plan_v1",
                    "note": (
                        "Created writer-facing rewrite and hold guidance for "
                        "claims that are unsupported, need review, or lack "
                        "accepted retrieval evidence."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(artifact)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=artifact.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="claim_revision_plan_created",
                actor="claim-verification-agent",
                payload={
                    "message_id": str(message.message_id),
                    "artifact_id": str(artifact.artifact_id),
                    "held_claim_count": len(plan["held_claims"]),
                    "accepted_source_alternative_count": len(
                        plan["accepted_source_alternatives"]
                    ),
                    "retrieval_ledger_artifact_id": (
                        str(retrieval_ledger.artifact_id)
                        if retrieval_ledger
                        else None
                    ),
                },
            )
        )
        return artifact

    async def _materialize_claim_revision_followups(
        self,
        *,
        message: AgentMessage,
        claim_revision_plan_artifact: ArtifactRecord | None,
        artifacts: list[ArtifactRecord],
        retrieval_ledger: ArtifactRecord | None,
    ) -> tuple[list[AgentMessage], int]:
        if claim_revision_plan_artifact is None:
            return [], 0
        followup_plan = _claim_revision_followup_specs(
            claim_revision_plan_artifact,
            artifacts,
        )
        if not followup_plan:
            return [], 0
        if message.requires_human_feedback:
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="claim_revision_followups_gated",
                    actor="claim-verification-agent",
                    payload={
                        "message_id": str(message.message_id),
                        "claim_revision_plan_artifact_id": str(
                            claim_revision_plan_artifact.artifact_id
                        ),
                        "reason": "human_feedback_required",
                        "planned_followup_count": len(followup_plan),
                    },
                )
            )
            return [], 0
        if not bool(message.payload.get("create_followup_tasks", True)):
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="claim_revision_followups_gated",
                    actor="claim-verification-agent",
                    payload={
                        "message_id": str(message.message_id),
                        "claim_revision_plan_artifact_id": str(
                            claim_revision_plan_artifact.artifact_id
                        ),
                        "reason": "create_followup_tasks_false",
                        "planned_followup_count": len(followup_plan),
                    },
                )
            )
            return [], 0

        existing_messages = await self._store.list_agent_messages(message.run_id)
        existing_by_signature = {
            str(existing.payload.get("claim_revision_followup_signature")): existing
            for existing in existing_messages
            if existing.payload.get("claim_revision_followup_signature")
            and existing.status in DEDUPED_MULTIMODAL_FOLLOWUP_STATUSES
        }
        created: list[AgentMessage] = []
        created_writer_message_ids: list[UUID] = []
        skipped_duplicates = 0
        for spec in followup_plan:
            signature = _claim_revision_followup_signature(
                claim_revision_plan_artifact=claim_revision_plan_artifact,
                retrieval_ledger=retrieval_ledger,
                recipient_agent_id=spec["recipient_agent_id"],
                task_type=spec["task_type"],
                target_artifact_ids=spec["target_artifact_ids"],
            )
            if signature in existing_by_signature:
                skipped_duplicates += 1
                continue
            depends_on_message_ids = (
                list(created_writer_message_ids)
                if spec["recipient_agent_id"] == "editor-in-chief"
                else []
            )
            followup = AgentMessage(
                run_id=message.run_id,
                sender_agent_id="claim-verification-agent",
                recipient_agent_id=spec["recipient_agent_id"],
                task_type=spec["task_type"],
                payload={
                    "workflow": "claim_revision_followup_v1",
                    "source_workflow": "claim_revision_plan_v1",
                    "source_message_id": str(message.message_id),
                    "claim_revision_plan_artifact_id": str(
                        claim_revision_plan_artifact.artifact_id
                    ),
                    "claim_revision_followup_signature": signature,
                    "held_claim_ids": [
                        claim["claim_id"]
                        for claim in claim_revision_plan_artifact.content.get(
                            "held_claims",
                            [],
                        )
                    ],
                    "accepted_source_alternative_ids": [
                        source["source_id"]
                        for source in claim_revision_plan_artifact.content.get(
                            "accepted_source_alternatives",
                            [],
                        )
                    ],
                    "target_artifact_ids": spec["target_artifact_ids"],
                    "target_artifact_types": spec["target_artifact_types"],
                    "handoff_reason": spec["reason"],
                    "topic": _topic_from_payload(message.payload),
                    "create_followup_tasks": False,
                },
                depends_on_message_ids=depends_on_message_ids,
            )
            await self._store.record_agent_message(followup)
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="agent_message_accepted",
                    actor="claim-verification-agent",
                    payload=public_a2a_message_event_payload(followup),
                )
            )
            created.append(followup)
            existing_by_signature[signature] = followup
            if spec["recipient_agent_id"] != "editor-in-chief":
                created_writer_message_ids.append(followup.message_id)

        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="claim_revision_followups_materialized",
                actor="claim-verification-agent",
                payload={
                    "message_id": str(message.message_id),
                    "claim_revision_plan_artifact_id": str(
                        claim_revision_plan_artifact.artifact_id
                    ),
                    "planned_followup_count": len(followup_plan),
                    "created_followup_message_ids": [
                        str(followup.message_id) for followup in created
                    ],
                    "created_followup_count": len(created),
                    "skipped_duplicate_followups": skipped_duplicates,
                    "recipient_agent_ids": [
                        followup.recipient_agent_id for followup in created
                    ],
                },
            )
        )
        return created, skipped_duplicates

    async def _execute_source_ledger_snapshot(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        snapshot = await SourceLedgerWorkflow(self._store).build(
            message.run_id,
            SourceLedgerSnapshotRequest(
                record_artifact=True,
                include_artifact_content=bool(
                    message.payload.get("include_artifact_content", False)
                ),
            ),
        )
        return {
            "generation_mode": "source_ledger_worker",
            "summary": snapshot.summary,
            "ledger_artifact_id": (
                str(snapshot.ledger_artifact_id)
                if snapshot.ledger_artifact_id
                else None
            ),
            "source_count": snapshot.source_count,
            "claim_count": snapshot.claim_count,
            "artifact_count": snapshot.artifact_count,
            "supported_claim_count": snapshot.supported_claim_count,
            "needs_review_claim_count": snapshot.needs_review_claim_count,
            "unsupported_claim_count": snapshot.unsupported_claim_count,
            "weak_source_ids": [
                str(source_id) for source_id in snapshot.weak_source_ids
            ],
            "stale_source_ids": [
                str(source_id) for source_id in snapshot.stale_source_ids
            ],
            "artifacts_missing_claims": [
                str(artifact_id)
                for artifact_id in snapshot.artifacts_missing_claims
            ],
            "artifacts_missing_sources": [
                str(artifact_id)
                for artifact_id in snapshot.artifacts_missing_sources
            ],
            "event_id": snapshot.event_id,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_context_engineering_packet(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        run = await self._store.get_run(message.run_id)
        if run is None:
            raise AgentWorkerRunNotFoundError(f"Run not found: {message.run_id}")
        target_agent_id = _target_agent_from_payload(message.payload)
        memories = await self._store.search_memories(
            agent_id=target_agent_id,
            run_id=message.run_id,
            include_global_memories=bool(
                message.payload.get("include_global_memories", True)
            ),
            query_embedding=message.payload.get("query_embedding"),
            limit=int(message.payload.get("memory_limit", 10)),
        )
        recent_events = await self._store.list_events(
            message.run_id,
            limit=int(message.payload.get("event_limit", 25)),
        )
        payload = build_context_engineering_payload(
            run=run,
            conversation_turns=await self._store.list_conversation_turns(message.run_id),
            agent_messages=await self._store.list_agent_messages(
                message.run_id,
                agent_id=target_agent_id,
            ),
            recent_events=recent_events,
            sources=await self._store.list_sources(message.run_id),
            claims=await self._store.list_claims(message.run_id),
            artifacts=await self._store.list_artifacts(message.run_id),
            guardrail_audits=await self._store.list_guardrail_audits(message.run_id),
            feedback_items=await self._store.list_feedback(message.run_id),
            memories=[
                MemorySearchResult(memory=memory, distance=distance)
                for memory, distance in memories
            ],
            agent_id=target_agent_id,
            max_manifest_items=int(message.payload.get("max_manifest_items", 40)),
            max_context_tokens=int(message.payload.get("max_context_tokens", 12000)),
        )
        artifact = ArtifactRecord(
            run_id=message.run_id,
            artifact_type=ArtifactType.CONTEXT_PACKET,
            title=(
                "Context packet"
                if target_agent_id is None
                else f"Context packet: {target_agent_id}"
            ),
            uri=(
                f"artifact://runs/{message.run_id}/context-packets/"
                f"{message.message_id}"
            ),
            content={
                "target_agent_id": target_agent_id,
                "source_multimodal_review_artifact_id": message.payload.get(
                    "source_multimodal_review_artifact_id"
                ),
                "target_artifact_ids": message.payload.get("target_artifact_ids", []),
                "source_workflow": message.payload.get("workflow"),
                "summary": payload["summary"],
                "context_manifest": [
                    item.model_dump(mode="json")
                    for item in payload["context_manifest"]
                ],
                "context_risks": [
                    risk.model_dump(mode="json") for risk in payload["context_risks"]
                ],
                "recommended_fetches": payload["recommended_fetches"],
                "source_evidence": payload["source_evidence"],
                "recent_events": [
                    event.model_dump(mode="json") for event in recent_events
                ],
            },
            provenance={
                "workflow": "context_engineering_worker_v1",
                "agent_id": "context-engineering-agent",
                "message_id": str(message.message_id),
                "target_agent_id": target_agent_id,
                "source_multimodal_review_artifact_id": message.payload.get(
                    "source_multimodal_review_artifact_id"
                ),
                "target_artifact_ids": message.payload.get("target_artifact_ids", []),
                "generation_mode": "deterministic_context_engineering",
            },
            revision_history=[
                {
                    "actor": "context-engineering-agent",
                    "workflow": "context_engineering_worker_v1",
                    "message_id": str(message.message_id),
                    "note": (
                        "Created a budgeted context packet artifact for a "
                        "long-running or resumed agent task."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(artifact)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=artifact.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="context_packet_artifact_created",
                actor="context-engineering-agent",
                payload={
                    "message_id": str(message.message_id),
                    "artifact_id": str(artifact.artifact_id),
                    "target_agent_id": target_agent_id,
                    "context_manifest_items": payload["summary"][
                        "context_manifest_items"
                    ],
                    "context_risk_count": payload["summary"]["context_risk_count"],
                    "recommended_fetches": payload["summary"]["recommended_fetches"],
                },
            )
        )
        return {
            "generation_mode": "context_engineering_worker",
            "summary": (
                "context-engineering-agent created a context packet artifact "
                f"with {payload['summary']['context_manifest_items']} manifest "
                f"item(s), {payload['summary']['context_risk_count']} risk(s), "
                f"and {payload['summary']['recommended_fetches']} recommended "
                "fetch(es)."
            ),
            "context_packet_artifact_id": str(artifact.artifact_id),
            "target_agent_id": target_agent_id,
            "context_manifest_items": payload["summary"]["context_manifest_items"],
            "context_risk_count": payload["summary"]["context_risk_count"],
            "recommended_fetches": payload["summary"]["recommended_fetches"],
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_harness_resume_plan(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        target_agent_id = _target_agent_from_payload(message.payload)
        plan = await RunResumeWorkflow(self._store).build_resume_plan(
            message.run_id,
            RunResumePlanRequest(
                agent_id=target_agent_id,
                include_global_memories=bool(
                    message.payload.get("include_global_memories", True)
                ),
                memory_limit=int(message.payload.get("memory_limit", 6)),
                create_checkpoint=bool(message.payload.get("create_checkpoint", True)),
                checkpoint_kind=str(
                    message.payload.get("checkpoint_kind") or "harness_worker"
                ),
                notes=message.payload.get("notes")
                or "Agent Harness worker prepared resume context.",
            ),
        )
        content = {
            "format": "run_resume_plan",
            "target_agent_id": target_agent_id,
            "resume_allowed": plan.resume_allowed,
            "blocked_reasons": plan.blocked_reasons,
            "recommended_next_actions": plan.recommended_next_actions,
            "latest_event_id": plan.latest_event_id,
            "event_stream_after_id": plan.event_stream_after_id,
            "summary": plan.summary,
            "context_summary": plan.context_summary,
            "checkpoint": (
                {
                    "checkpoint_id": str(plan.checkpoint.checkpoint_id),
                    "checkpoint_kind": plan.checkpoint.checkpoint_kind,
                    "event_cursor": plan.checkpoint.event_cursor,
                    "state_digest": plan.checkpoint.state_digest,
                    "created_by": plan.checkpoint.created_by,
                    "notes": plan.checkpoint.notes,
                    "created_at": plan.checkpoint.created_at.isoformat(),
                }
                if plan.checkpoint
                else None
            ),
            "pending_agent_messages": [
                {
                    "message_id": str(agent_message.message_id),
                    "sender_agent_id": agent_message.sender_agent_id,
                    "recipient_agent_id": agent_message.recipient_agent_id,
                    "task_type": agent_message.task_type,
                    "status": agent_message.status.value,
                    "requires_human_feedback": agent_message.requires_human_feedback,
                    "created_at": agent_message.created_at.isoformat(),
                }
                for agent_message in plan.pending_agent_messages
            ],
            "open_feedback_items": [
                {
                    "feedback_id": str(feedback.feedback_id),
                    "target_agent_id": feedback.target_agent_id,
                    "status": feedback.status.value,
                    "feedback_text": feedback.feedback_text,
                    "created_at": feedback.created_at.isoformat(),
                }
                for feedback in plan.open_feedback_items
            ],
            "active_worker_profiles": [
                {
                    "profile_id": str(profile.profile_id),
                    "name": profile.name,
                    "status": profile.status.value,
                    "agent_ids": profile.agent_ids,
                    "max_tasks_per_agent": profile.max_tasks_per_agent,
                    "max_rounds": profile.max_rounds,
                    "poll_interval_seconds": profile.poll_interval_seconds,
                    "last_heartbeat_at": (
                        profile.last_heartbeat_at.isoformat()
                        if profile.last_heartbeat_at
                        else None
                    ),
                }
                for profile in plan.active_worker_profiles
            ],
        }
        record_artifact = bool(message.payload.get("record_artifact", True))
        artifact_id = None
        if record_artifact:
            artifact = ArtifactRecord(
                run_id=message.run_id,
                artifact_type=ArtifactType.RUN_RESUME_PLAN,
                title=(
                    "Run resume plan"
                    if target_agent_id is None
                    else f"Run resume plan: {target_agent_id}"
                ),
                uri=(
                    f"artifact://runs/{message.run_id}/resume-plans/"
                    f"{message.message_id}"
                ),
                content=content,
                provenance={
                    "workflow": "agent_harness_resume_plan_worker_v1",
                    "agent_id": "agent-harness-engineer",
                    "message_id": str(message.message_id),
                    "target_agent_id": target_agent_id,
                    "checkpoint_id": (
                        str(plan.checkpoint.checkpoint_id)
                        if plan.checkpoint
                        else None
                    ),
                    "generation_mode": "deterministic_harness_resume_plan",
                },
                revision_history=[
                    {
                        "actor": "agent-harness-engineer",
                        "workflow": "agent_harness_resume_plan_worker_v1",
                        "message_id": str(message.message_id),
                        "note": (
                            "Created a checkpointed resume plan for durable "
                            "long-running agent work."
                        ),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            )
            await self._store.record_artifact(artifact)
            artifact_id = artifact.artifact_id
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="artifact_recorded",
                    actor="artifact-librarian",
                    payload=artifact.model_dump(mode="json"),
                )
            )

        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="agent_harness_resume_plan_recorded",
                actor="agent-harness-engineer",
                payload={
                    "message_id": str(message.message_id),
                    "artifact_id": str(artifact_id) if artifact_id else None,
                    "checkpoint_id": (
                        str(plan.checkpoint.checkpoint_id)
                        if plan.checkpoint
                        else None
                    ),
                    "target_agent_id": target_agent_id,
                    "resume_allowed": plan.resume_allowed,
                    "blocked_reasons": plan.blocked_reasons,
                    "pending_agent_messages": len(plan.pending_agent_messages),
                    "open_feedback_items": len(plan.open_feedback_items),
                    "active_worker_profiles": len(plan.active_worker_profiles),
                    "event_stream_after_id": plan.event_stream_after_id,
                },
            )
        )
        return {
            "generation_mode": "agent_harness_resume_plan_worker",
            "summary": (
                "agent-harness-engineer recorded a resume plan with "
                f"{len(plan.pending_agent_messages)} pending task(s), "
                f"{len(plan.open_feedback_items)} open feedback item(s), "
                f"{len(plan.active_worker_profiles)} active worker profile(s), "
                f"resume_allowed={plan.resume_allowed}."
            ),
            "resume_plan_artifact_id": str(artifact_id) if artifact_id else None,
            "checkpoint_id": (
                str(plan.checkpoint.checkpoint_id) if plan.checkpoint else None
            ),
            "target_agent_id": target_agent_id,
            "resume_allowed": plan.resume_allowed,
            "blocked_reasons": plan.blocked_reasons,
            "recommended_next_actions": plan.recommended_next_actions,
            "latest_event_id": plan.latest_event_id,
            "event_stream_after_id": plan.event_stream_after_id,
            "pending_agent_messages": len(plan.pending_agent_messages),
            "open_feedback_items": len(plan.open_feedback_items),
            "active_worker_profiles": len(plan.active_worker_profiles),
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_forward_deployed_feedback(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        feedback_items = await self._selected_feedback_items(message)
        requirements_content = _forward_deployed_requirements_content(
            message=message,
            feedback_items=feedback_items,
            context_summary=context_summary,
        )
        artifact = ArtifactRecord(
            run_id=message.run_id,
            artifact_type=ArtifactType.FEEDBACK_REQUIREMENTS,
            title="Forward deployed feedback requirements",
            uri=(
                f"artifact://runs/{message.run_id}/feedback-requirements/"
                f"{message.message_id}"
            ),
            content=requirements_content,
            provenance={
                "workflow": "forward_deployed_feedback_worker_v1",
                "agent_id": "forward-deployed-engineer",
                "message_id": str(message.message_id),
                "source_feedback_ids": [
                    str(feedback.feedback_id) for feedback in feedback_items
                ],
                "generation_mode": "deterministic_feedback_requirements",
            },
            revision_history=[
                {
                    "actor": "forward-deployed-engineer",
                    "workflow": "forward_deployed_feedback_worker_v1",
                    "message_id": str(message.message_id),
                    "note": (
                        "Converted human feedback and handoff context into "
                        "acceptance criteria and specialist follow-up tasks."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(artifact)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=artifact.model_dump(mode="json"),
            )
        )

        created_messages = await self._create_feedback_requirement_tasks(
            message=message,
            requirements=requirements_content["requirements"],
            requirements_artifact_id=artifact.artifact_id,
        )
        artifact.content["created_task_message_ids"] = [
            str(created.message_id) for created in created_messages
        ]
        artifact.content["handoff_count"] = len(created_messages)
        await self._store.update_artifact(artifact)

        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="feedback_requirements_recorded",
                actor="forward-deployed-engineer",
                payload={
                    "message_id": str(message.message_id),
                    "requirements_artifact_id": str(artifact.artifact_id),
                    "source_feedback_ids": [
                        str(feedback.feedback_id) for feedback in feedback_items
                    ],
                    "requirement_count": len(requirements_content["requirements"]),
                    "open_question_count": len(requirements_content["open_questions"]),
                    "created_task_message_ids": [
                        str(created.message_id) for created in created_messages
                    ],
                    "owner_agent_ids": requirements_content["owner_agent_ids"],
                },
            )
        )
        return {
            "generation_mode": "forward_deployed_feedback_worker",
            "summary": (
                "forward-deployed-engineer captured "
                f"{len(requirements_content['requirements'])} requirement(s), "
                f"{len(requirements_content['open_questions'])} open question(s), "
                f"and created {len(created_messages)} follow-up task(s)."
            ),
            "requirements_artifact_id": str(artifact.artifact_id),
            "source_feedback_ids": [
                str(feedback.feedback_id) for feedback in feedback_items
            ],
            "requirement_count": len(requirements_content["requirements"]),
            "open_question_count": len(requirements_content["open_questions"]),
            "created_task_message_ids": [
                str(created.message_id) for created in created_messages
            ],
            "owner_agent_ids": requirements_content["owner_agent_ids"],
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _selected_feedback_items(
        self,
        message: AgentMessage,
    ) -> list[FeedbackItem]:
        requested_ids = _feedback_ids_from_payload(message.payload)
        feedback_items = await self._store.list_feedback(message.run_id)
        if requested_ids:
            selected = [
                feedback
                for feedback in feedback_items
                if str(feedback.feedback_id) in requested_ids
            ]
            if selected:
                return selected
        selected = [
            feedback
            for feedback in feedback_items
            if feedback.status in {FeedbackStatus.OPEN, FeedbackStatus.ROUTED}
            and (
                feedback.target_agent_id in {None, "forward-deployed-engineer"}
                or feedback.metadata.get("routed_by") == "forward-deployed-engineer"
                or feedback.metadata.get("focus") == "feedback"
            )
        ]
        if selected:
            return selected
        feedback_text = _payload_text(
            message.payload,
            "feedback_text",
            "Clarify the requested change before the next specialist pass.",
        )
        return [
            FeedbackItem(
                run_id=message.run_id,
                author=str(message.payload.get("author") or message.sender_agent_id),
                target_agent_id="forward-deployed-engineer",
                feedback_text=feedback_text,
                status=FeedbackStatus.ROUTED,
                metadata={
                    "source": "forward_deployed_worker_message",
                    "source_message_id": str(message.message_id),
                    "task_type": message.task_type,
                    **(
                        message.payload.get("feedback_metadata")
                        if isinstance(message.payload.get("feedback_metadata"), dict)
                        else {}
                    ),
                },
            )
        ]

    async def _create_feedback_requirement_tasks(
        self,
        *,
        message: AgentMessage,
        requirements: list[dict[str, Any]],
        requirements_artifact_id: UUID,
    ) -> list[AgentMessage]:
        existing = {
            (
                existing_message.recipient_agent_id,
                existing_message.task_type,
                existing_message.payload.get("parent_message_id"),
                existing_message.payload.get("requirement_id"),
            )
            for existing_message in await self._store.list_agent_messages(message.run_id)
        }
        created: list[AgentMessage] = []
        for requirement in requirements:
            owner_agent_id = requirement["owner_agent_id"]
            if owner_agent_id == "forward-deployed-engineer":
                continue
            key = (
                owner_agent_id,
                "incorporate_feedback_requirement",
                str(message.message_id),
                requirement["requirement_id"],
            )
            if key in existing:
                continue
            created.append(
                await self._record_feedback_requirement_task(
                    message=message,
                    recipient_agent_id=owner_agent_id,
                    task_type="incorporate_feedback_requirement",
                    requirement=requirement,
                    requirements_artifact_id=requirements_artifact_id,
                )
            )

        for recipient_agent_id, task_type in [
            ("interactive-note-taking-agent", "record_feedback_requirements_note"),
            ("sprint-progress-agent", "plan_feedback_requirements"),
        ]:
            key = (recipient_agent_id, task_type, str(message.message_id), None)
            if key in existing:
                continue
            created.append(
                await self._record_feedback_requirement_task(
                    message=message,
                    recipient_agent_id=recipient_agent_id,
                    task_type=task_type,
                    requirement=None,
                    requirements_artifact_id=requirements_artifact_id,
                )
            )
        return created

    async def _record_feedback_requirement_task(
        self,
        *,
        message: AgentMessage,
        recipient_agent_id: str,
        task_type: str,
        requirement: dict[str, Any] | None,
        requirements_artifact_id: UUID,
    ) -> AgentMessage:
        task = AgentMessage(
            run_id=message.run_id,
            sender_agent_id="forward-deployed-engineer",
            recipient_agent_id=recipient_agent_id,
            task_type=task_type,
            payload={
                "parent_message_id": str(message.message_id),
                "requirements_artifact_id": str(requirements_artifact_id),
                "requirement_id": (
                    requirement["requirement_id"] if requirement else None
                ),
                "requirement": requirement,
                "instruction": (
                    "Use the structured feedback requirement and acceptance "
                    "criteria as the source of truth for the next pass."
                ),
            },
        )
        await self._store.record_agent_message(task)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="agent_message_accepted",
                actor="forward-deployed-engineer",
                payload=public_a2a_message_event_payload(task),
            )
        )
        return task

    async def _execute_provider_configuration_blocker_review(
        self,
        *,
        message: AgentMessage,
        agent_id: str,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        safe_payload = _safe_provider_failure_metadata(message.payload)
        blocked_steps = _provider_configuration_blocked_steps(safe_payload)
        recovery_checks = _provider_configuration_recovery_checks(blocked_steps)
        required_actions = _provider_configuration_required_actions(blocked_steps)
        content = {
            "format": "provider_configuration_recovery",
            "status": "blocked_until_provider_configuration_recheck",
            "review_agent_id": agent_id,
            "source_task_type": message.task_type,
            "provider_smoke_status": _payload_text(
                safe_payload,
                "provider_smoke_status",
                "blocked",
            ),
            "provider_smoke_ledger_artifact_id": _payload_optional_text(
                safe_payload,
                "ledger_artifact_id",
            ),
            "blocked_step_count": len(blocked_steps),
            "blocked_steps": blocked_steps,
            "recovery_checks": recovery_checks,
            "required_actions": required_actions,
            "fallback_policy": {
                "allowed": [
                    "retry_provider_smoke_after_configuration_recheck",
                    "use_provider_free_rehearsal_for_local_dialogue_only",
                    "switch_optional_provider_after_human_confirmation",
                ],
                "blocked": [
                    "persist_provider_secret_values",
                    "count_provider_free_rehearsal_as_provider_backed_smoke",
                    "fallback_to_paid_realtime_provider_without_human_confirmation",
                ],
            },
            "context_summary": context_summary,
        }
        artifact = ArtifactRecord(
            artifact_id=_agent_worker_artifact_id(
                run_id=message.run_id,
                message_id=message.message_id,
                workflow="provider_configuration_recovery_worker_v1",
                artifact_type=ArtifactType.PROVIDER_OPERATIONS_LEDGER,
            ),
            run_id=message.run_id,
            artifact_type=ArtifactType.PROVIDER_OPERATIONS_LEDGER,
            title="Provider configuration recovery plan",
            uri=(
                f"artifact://runs/{message.run_id}/provider-configuration-recovery/"
                f"{message.message_id}"
            ),
            content=content,
            provenance={
                "workflow": "provider_configuration_recovery_worker_v1",
                "agent_id": agent_id,
                "message_id": str(message.message_id),
                "generation_mode": (
                    "deterministic_provider_configuration_recovery"
                ),
                "provider_smoke_ledger_artifact_id": content[
                    "provider_smoke_ledger_artifact_id"
                ],
            },
            reviewer_decisions=[
                {
                    "reviewer_agent_id": agent_id,
                    "decision": ReviewDecisionStatus.BLOCKED.value,
                    "notes": (
                        "Provider-backed operation remains blocked until "
                        "configuration is repaired and provider smoke is rerun."
                    ),
                }
            ],
            revision_history=[
                {
                    "actor": agent_id,
                    "workflow": "provider_configuration_recovery_worker_v1",
                    "message_id": str(message.message_id),
                    "note": (
                        "Converted provider-smoke configuration blockers into "
                        "operator-grade recovery checks and follow-up tasks."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        recorded_artifact = await self._record_artifact_if_absent(artifact)
        if recorded_artifact is not None:
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="artifact_recorded",
                    actor="artifact-librarian",
                    payload=recorded_artifact.model_dump(mode="json"),
                )
            )

        created_followups, skipped_duplicate_followups = (
            await self._create_provider_configuration_followups(
                message=message,
                actor_agent_id=agent_id,
                review_artifact=artifact,
                content=content,
            )
        )
        await _append_agent_worker_event_if_absent(
            self._store,
            RunEvent(
                run_id=message.run_id,
                event_type="provider_configuration_review_recorded",
                actor=agent_id,
                payload={
                    "message_id": str(message.message_id),
                    "provider_configuration_review_artifact_id": str(
                        artifact.artifact_id
                    ),
                    "status": content["status"],
                    "blocked_step_count": len(blocked_steps),
                    "created_followup_message_ids": [
                        str(followup.message_id) for followup in created_followups
                    ],
                    "skipped_duplicate_followup_count": skipped_duplicate_followups,
                },
            ),
            idempotency_key=_agent_worker_event_idempotency_key(
                run_id=message.run_id,
                event_type="provider_configuration_review_recorded",
                message_id=message.message_id,
            ),
        )
        return {
            "generation_mode": "provider_configuration_recovery_worker",
            "summary": (
                f"{agent_id} recorded provider configuration recovery for "
                f"{len(blocked_steps)} blocked provider-smoke step(s); created "
                f"{len(created_followups)} follow-up task(s)."
            ),
            "provider_configuration_review_artifact_id": str(artifact.artifact_id),
            "status": content["status"],
            "blocked_step_count": len(blocked_steps),
            "created_followup_message_ids": [
                str(followup.message_id) for followup in created_followups
            ],
            "skipped_duplicate_followup_count": skipped_duplicate_followups,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _create_provider_configuration_followups(
        self,
        *,
        message: AgentMessage,
        actor_agent_id: str,
        review_artifact: ArtifactRecord,
        content: dict[str, Any],
    ) -> tuple[list[AgentMessage], int]:
        base_payload = {
            "workflow": "provider_configuration_recovery_followup_v1",
            "parent_message_id": str(message.message_id),
            "provider_configuration_review_artifact_id": str(
                review_artifact.artifact_id
            ),
            "provider_smoke_ledger_artifact_id": content[
                "provider_smoke_ledger_artifact_id"
            ],
            "blocked_steps": content["blocked_steps"],
            "required_actions": content["required_actions"],
        }
        specs = [
            (
                "observability-agent",
                "build_runtime_health_ledger",
                {
                    **base_payload,
                    "record_artifact": True,
                    "include_static_checks": True,
                    "include_run_evidence": True,
                    "record_live_store_evidence": True,
                    "event_limit": 250,
                    "handoff_reason": (
                        "Provider configuration recovery needs durable runtime "
                        "and smoke evidence before retry."
                    ),
                },
            ),
            (
                "agent-harness-engineer",
                "plan_provider_configuration_recovery_checkpoint",
                {
                    **base_payload,
                    "checkpoint_scope": "provider_configuration_recovery",
                    "handoff_reason": (
                        "The run needs a resumable checkpoint after provider-smoke "
                        "configuration blockers."
                    ),
                },
            ),
        ]
        created: list[AgentMessage] = []
        skipped_duplicate_count = 0
        for recipient_agent_id, task_type, payload in specs:
            child = AgentMessage(
                message_id=_agent_worker_child_message_id(
                    run_id=message.run_id,
                    parent_message_id=message.message_id,
                    sender_agent_id=actor_agent_id,
                    recipient_agent_id=recipient_agent_id,
                    task_type=task_type,
                ),
                run_id=message.run_id,
                sender_agent_id=actor_agent_id,
                recipient_agent_id=recipient_agent_id,
                task_type=task_type,
                payload=payload,
            )
            recorded_child = await self._record_agent_message_if_absent(child)
            if recorded_child is None:
                skipped_duplicate_count += 1
                continue
            created.append(recorded_child)
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="agent_message_accepted",
                    actor=actor_agent_id,
                    payload=public_a2a_message_event_payload(recorded_child),
                )
            )
        return created, skipped_duplicate_count

    async def _execute_realtime_provider_failure_review(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        safe_payload = _safe_provider_failure_metadata(message.payload)
        failure_stage = _payload_text(safe_payload, "failure_stage", "unknown")
        failure_reason = _payload_text(
            safe_payload,
            "failure_reason",
            "Unknown Gemma/Kokoro realtime provider failure.",
        )
        failed_component = _realtime_provider_failure_component(
            stage=failure_stage,
            reason=failure_reason,
        )
        recovery_checks = _realtime_provider_failure_recovery_checks(
            failed_component=failed_component,
            payload=safe_payload,
        )
        content = {
            "format": "realtime_provider_failure_recovery",
            "status": "blocked_until_realtime_provider_recheck",
            "review_agent_id": "inference-systems-engineer",
            "source_task_type": message.task_type,
            "provider": _payload_text(safe_payload, "provider", "gemma4_realtime"),
            "transport_framework": _payload_text(
                safe_payload,
                "transport_framework",
                "livekit",
            ),
            "realtime_session_id": _payload_optional_text(
                safe_payload,
                "realtime_session_id",
            ),
            "provider_session_id": _payload_optional_text(
                safe_payload,
                "provider_session_id",
            ),
            "room_name": _payload_optional_text(safe_payload, "room_name"),
            "voice": _payload_optional_text(safe_payload, "voice"),
            "failure": {
                "stage": failure_stage,
                "reason": failure_reason,
                "component": failed_component,
                "turn_id": _payload_optional_text(safe_payload, "turn_id"),
                "response_id": _payload_optional_text(safe_payload, "response_id"),
                "voice_agent_event_id": safe_payload.get("voice_agent_event_id"),
                "voice_agent_event_type": _payload_optional_text(
                    safe_payload,
                    "voice_agent_event_type",
                ),
                "assistant_text_chars": safe_payload.get("assistant_text_chars", 0),
                "audio_chunk_count": safe_payload.get("audio_chunk_count", 0),
            },
            "recovery_checks": recovery_checks,
            "required_actions": [
                "Run Runtime preflight before allowing another provider-backed voice turn.",
                "Run session-bound provider smoke with live calls only after the operator confirms external endpoint usage.",
                "Build the realtime voice timing ledger and confirm LiveKit, Gemma TTFT, Kokoro first-audio, and interruption stages.",
                "Keep the user turn durable, but do not materialize an assistant turn until speech was actually produced.",
            ],
            "fallback_policy": {
                "allowed": [
                    "retry_same_route_after_readiness_passes",
                    "switch_kokoro_route_when_tts_component_failed",
                    "fall_back_to_text_response_only_after_human_confirmation",
                ],
                "blocked": [
                    "openai_realtime_fallback",
                    "fake_assistant_voice_turns",
                    "provider_free_rehearsal_counted_as_live_voice",
                ],
            },
            "context_summary": context_summary,
        }
        artifact = ArtifactRecord(
            artifact_id=_agent_worker_artifact_id(
                run_id=message.run_id,
                message_id=message.message_id,
                workflow="realtime_provider_failure_recovery_worker_v1",
                artifact_type=ArtifactType.PROVIDER_OPERATIONS_LEDGER,
            ),
            run_id=message.run_id,
            artifact_type=ArtifactType.PROVIDER_OPERATIONS_LEDGER,
            title="Realtime provider failure recovery plan",
            uri=(
                f"artifact://runs/{message.run_id}/provider-failure-recovery/"
                f"{message.message_id}"
            ),
            content=content,
            provenance={
                "workflow": "realtime_provider_failure_recovery_worker_v1",
                "agent_id": "inference-systems-engineer",
                "message_id": str(message.message_id),
                "generation_mode": "deterministic_realtime_provider_failure_recovery",
                "source_voice_agent_event_id": safe_payload.get(
                    "voice_agent_event_id"
                ),
                "source_voice_agent_event_type": safe_payload.get(
                    "voice_agent_event_type"
                ),
            },
            reviewer_decisions=[
                {
                    "reviewer_agent_id": "inference-systems-engineer",
                    "decision": ReviewDecisionStatus.BLOCKED.value,
                    "notes": (
                        "Provider-backed realtime voice remains blocked until "
                        "readiness, provider smoke, and timing proof are refreshed."
                    ),
                }
            ],
            revision_history=[
                {
                    "actor": "inference-systems-engineer",
                    "workflow": "realtime_provider_failure_recovery_worker_v1",
                    "message_id": str(message.message_id),
                    "note": (
                        "Converted a failed Gemma/Kokoro voice event into an "
                        "operator-grade recovery plan and follow-up tasks."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        recorded_artifact = await self._record_artifact_if_absent(artifact)
        if recorded_artifact is not None:
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="artifact_recorded",
                    actor="artifact-librarian",
                    payload=recorded_artifact.model_dump(mode="json"),
                )
            )

        created_followups, skipped_duplicate_followups = (
            await self._create_realtime_provider_failure_followups(
                message=message,
                review_artifact=artifact,
                content=content,
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="realtime_provider_failure_review_recorded",
                actor="inference-systems-engineer",
                payload={
                    "message_id": str(message.message_id),
                    "provider_failure_review_artifact_id": str(artifact.artifact_id),
                    "status": content["status"],
                    "failed_component": failed_component,
                    "failure_stage": failure_stage,
                    "created_followup_message_ids": [
                        str(followup.message_id) for followup in created_followups
                    ],
                    "skipped_duplicate_followup_count": skipped_duplicate_followups,
                },
            )
        )
        return {
            "generation_mode": "realtime_provider_failure_recovery_worker",
            "summary": (
                "inference-systems-engineer recorded realtime provider failure "
                f"recovery for {failed_component}; created "
                f"{len(created_followups)} follow-up task(s)."
            ),
            "provider_failure_review_artifact_id": str(artifact.artifact_id),
            "status": content["status"],
            "failed_component": failed_component,
            "failure_stage": failure_stage,
            "created_followup_message_ids": [
                str(followup.message_id) for followup in created_followups
            ],
            "skipped_duplicate_followup_count": skipped_duplicate_followups,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _create_realtime_provider_failure_followups(
        self,
        *,
        message: AgentMessage,
        review_artifact: ArtifactRecord,
        content: dict[str, Any],
    ) -> tuple[list[AgentMessage], int]:
        base_payload = {
            "workflow": "realtime_provider_failure_recovery_followup_v1",
            "parent_message_id": str(message.message_id),
            "provider_failure_review_artifact_id": str(review_artifact.artifact_id),
            "provider": content["provider"],
            "transport_framework": content["transport_framework"],
            "realtime_session_id": content["realtime_session_id"],
            "failure": content["failure"],
            "required_actions": content["required_actions"],
        }
        specs = [
            (
                "observability-agent",
                "build_runtime_health_ledger",
                {
                    **base_payload,
                    "record_artifact": True,
                    "include_static_checks": True,
                    "include_run_evidence": True,
                    "record_live_store_evidence": True,
                    "event_limit": 250,
                    "handoff_reason": (
                        "Provider failure recovery needs durable runtime health "
                        "evidence before another live voice attempt."
                    ),
                },
            ),
            (
                "agent-harness-engineer",
                "plan_realtime_provider_recovery_checkpoint",
                {
                    **base_payload,
                    "checkpoint_scope": "realtime_provider_failure_recovery",
                    "handoff_reason": (
                        "The run needs a resumable checkpoint after a failed "
                        "provider-backed voice turn."
                    ),
                },
            ),
        ]
        created: list[AgentMessage] = []
        skipped_duplicate_count = 0
        for recipient_agent_id, task_type, payload in specs:
            child = AgentMessage(
                message_id=_agent_worker_child_message_id(
                    run_id=message.run_id,
                    parent_message_id=message.message_id,
                    sender_agent_id="inference-systems-engineer",
                    recipient_agent_id=recipient_agent_id,
                    task_type=task_type,
                ),
                run_id=message.run_id,
                sender_agent_id="inference-systems-engineer",
                recipient_agent_id=recipient_agent_id,
                task_type=task_type,
                payload=payload,
            )
            recorded_child = await self._record_agent_message_if_absent(child)
            if recorded_child is None:
                skipped_duplicate_count += 1
                continue
            created.append(recorded_child)
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="agent_message_accepted",
                    actor="inference-systems-engineer",
                    payload=public_a2a_message_event_payload(recorded_child),
                )
            )
        return created, skipped_duplicate_count

    async def _execute_principal_architecture_review(
        self,
        *,
        message: AgentMessage,
        agent_id: str = "principal-software-engineer",
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        profile = ARCHITECTURE_REVIEW_AGENT_PROFILES[agent_id]
        run = await self._store.get_run(message.run_id)
        if run is None:
            raise AgentWorkerRunNotFoundError(f"Run not found: {message.run_id}")
        messages = await self._store.list_agent_messages(message.run_id)
        events = await self._store.list_events(
            message.run_id,
            limit=int(message.payload.get("event_limit", 250)),
        )
        artifacts = await self._store.list_artifacts(message.run_id)
        sources = await self._store.list_sources(message.run_id)
        claims = await self._store.list_claims(message.run_id)
        feedback_items = await self._store.list_feedback(message.run_id)
        guardrail_audits = await self._store.list_guardrail_audits(message.run_id)
        checkpoints = await self._store.list_run_checkpoints(message.run_id)
        worker_profiles = await self._store.list_worker_profiles(message.run_id)
        realtime_sessions = await self._store.list_realtime_sessions(message.run_id)
        review_content = _principal_architecture_review_content(
            run=run,
            messages=messages,
            events=events,
            artifacts=artifacts,
            sources=sources,
            claims=claims,
            feedback_items=feedback_items,
            guardrail_audits=guardrail_audits,
            checkpoints=checkpoints,
            worker_profiles=worker_profiles,
            realtime_sessions=realtime_sessions,
            context_summary=context_summary,
            scope=_payload_text(
                message.payload,
                "scope",
                "local-first realtime multi-agent content studio",
            ),
            review_agent_id=agent_id,
            review_profile=profile,
        )
        review = ArtifactRecord(
            run_id=message.run_id,
            artifact_type=ArtifactType.ARCHITECTURE_REVIEW,
            title=profile["title"],
            uri=(
                f"artifact://runs/{message.run_id}/architecture-reviews/"
                f"{message.message_id}"
            ),
            content=review_content,
            provenance={
                "workflow": profile["workflow"],
                "agent_id": agent_id,
                "message_id": str(message.message_id),
                "source_event_count": len(events),
                "source_artifact_count": len(artifacts),
                "generation_mode": profile["deterministic_generation_mode"],
            },
            revision_history=[
                {
                    "actor": agent_id,
                    "workflow": profile["workflow"],
                    "message_id": str(message.message_id),
                    "note": profile["revision_note"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(review)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=review.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="architecture_review_recorded",
                actor=agent_id,
                payload={
                    "message_id": str(message.message_id),
                    "agent_id": agent_id,
                    "architecture_review_artifact_id": str(review.artifact_id),
                    "health_status": review_content["health_status"],
                    "finding_count": len(review_content["findings"]),
                    "risk_count": len(review_content["risk_register"]),
                    "recommended_next_actions": review_content[
                        "recommended_next_actions"
                    ],
                },
            )
        )
        return {
            "generation_mode": profile["generation_mode"],
            "summary": (
                f"{agent_id} recorded {profile['summary_label']} "
                f"status={review_content['health_status']} with "
                f"{len(review_content['findings'])} finding(s), "
                f"{len(review_content['risk_register'])} risk(s), and "
                f"{len(review_content['recommended_next_actions'])} next action(s)."
            ),
            "architecture_review_artifact_id": str(review.artifact_id),
            "health_status": review_content["health_status"],
            "finding_count": len(review_content["findings"]),
            "risk_count": len(review_content["risk_register"]),
            "recommended_next_actions": review_content["recommended_next_actions"],
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_ux_review(
        self,
        *,
        message: AgentMessage,
        agent_id: str = "lead-ui-ux-designer",
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        profile = UX_REVIEW_AGENT_PROFILES[agent_id]
        run = await self._store.get_run(message.run_id)
        if run is None:
            raise AgentWorkerRunNotFoundError(f"Run not found: {message.run_id}")
        events = await self._store.list_events(
            message.run_id,
            limit=int(message.payload.get("event_limit", 250)),
        )
        artifacts = await self._store.list_artifacts(message.run_id)
        feedback_items = await self._store.list_feedback(message.run_id)
        messages = await self._store.list_agent_messages(message.run_id)
        realtime_sessions = await self._store.list_realtime_sessions(message.run_id)
        review_content = _ux_review_content(
            run=run,
            message=message,
            events=events,
            artifacts=artifacts,
            feedback_items=feedback_items,
            messages=messages,
            realtime_sessions=realtime_sessions,
            context_summary=context_summary,
            review_agent_id=agent_id,
            review_profile=profile,
        )
        review = ArtifactRecord(
            run_id=message.run_id,
            artifact_type=ArtifactType.UX_REVIEW,
            title=profile["title"],
            uri=(
                f"artifact://runs/{message.run_id}/ux-reviews/"
                f"{message.message_id}"
            ),
            content=review_content,
            provenance={
                "workflow": profile["workflow"],
                "agent_id": agent_id,
                "message_id": str(message.message_id),
                "surface_scope": review_content["surface_scope"],
                "generation_mode": profile["deterministic_generation_mode"],
            },
            revision_history=[
                {
                    "actor": agent_id,
                    "workflow": profile["workflow"],
                    "message_id": str(message.message_id),
                    "note": (
                        "Reviewed cockpit, planning surface boundary, realtime "
                        "interaction controls, feedback affordances, and "
                        "source/artifact visibility."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(review)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=review.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="ux_review_recorded",
                actor=agent_id,
                payload={
                    "message_id": str(message.message_id),
                    "agent_id": agent_id,
                    "ux_review_artifact_id": str(review.artifact_id),
                    "surface_scope": review_content["surface_scope"],
                    "finding_count": len(review_content["findings"]),
                    "risk_count": len(review_content["ux_risks"]),
                    "recommended_next_actions": review_content[
                        "recommended_next_actions"
                    ],
                },
            )
        )
        return {
            "generation_mode": profile["generation_mode"],
            "summary": (
                f"{agent_id} recorded {profile['summary_label']} for "
                f"{review_content['surface_scope']} with "
                f"{len(review_content['findings'])} finding(s), "
                f"{len(review_content['ux_risks'])} risk(s), and "
                f"{len(review_content['recommended_next_actions'])} next action(s)."
            ),
            "ux_review_artifact_id": str(review.artifact_id),
            "surface_scope": review_content["surface_scope"],
            "finding_count": len(review_content["findings"]),
            "risk_count": len(review_content["ux_risks"]),
            "recommended_next_actions": review_content["recommended_next_actions"],
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_interactive_systems_review(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        events = await self._store.list_events(
            message.run_id,
            limit=int(message.payload.get("event_limit", 250)),
        )
        artifacts = await self._store.list_artifacts(message.run_id)
        feedback_items = await self._store.list_feedback(message.run_id)
        surface_path = Path(
            str(
                message.payload.get("surface_path")
                or "planning/foundation-system-design.html"
            )
        )
        review_content = _interactive_systems_review_content(
            surface_path=surface_path,
            events=events,
            artifacts=artifacts,
            feedback_items=feedback_items,
            context_summary=context_summary,
        )
        review = ArtifactRecord(
            run_id=message.run_id,
            artifact_type=ArtifactType.PLANNING_SURFACE_REVIEW,
            title="Interactive planning surface review",
            uri=(
                f"artifact://runs/{message.run_id}/planning-surface-reviews/"
                f"{message.message_id}"
            ),
            content=review_content,
            provenance={
                "workflow": "interactive_systems_review_worker_v1",
                "agent_id": "interactive-systems-designer",
                "message_id": str(message.message_id),
                "surface_path": str(surface_path),
                "generation_mode": "deterministic_planning_surface_review",
            },
            revision_history=[
                {
                    "actor": "interactive-systems-designer",
                    "workflow": "interactive_systems_review_worker_v1",
                    "message_id": str(message.message_id),
                    "note": (
                        "Reviewed the separate animated planning workspace, "
                        "embedded JSON state, local progress tracker, "
                        "suggestion capture, and export affordances."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(review)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=review.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="interactive_systems_review_recorded",
                actor="interactive-systems-designer",
                payload={
                    "message_id": str(message.message_id),
                    "planning_surface_review_artifact_id": str(review.artifact_id),
                    "surface_path": str(surface_path),
                    "data_section_count": len(
                        review_content["embedded_state"]["section_keys"]
                    ),
                    "interactive_control_count": review_content[
                        "interaction_inventory"
                    ]["interactive_control_count"],
                    "finding_count": len(review_content["findings"]),
                    "risk_count": len(review_content["risks"]),
                    "recommended_next_actions": review_content[
                        "recommended_next_actions"
                    ],
                },
            )
        )
        return {
            "generation_mode": "interactive_systems_review_worker",
            "summary": (
                "interactive-systems-designer recorded planning surface review "
                f"with {len(review_content['findings'])} finding(s), "
                f"{len(review_content['risks'])} risk(s), and "
                f"{len(review_content['recommended_next_actions'])} next action(s)."
            ),
            "planning_surface_review_artifact_id": str(review.artifact_id),
            "surface_path": str(surface_path),
            "finding_count": len(review_content["findings"]),
            "risk_count": len(review_content["risks"]),
            "recommended_next_actions": review_content["recommended_next_actions"],
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_a2a_protocol_audit(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        messages = await self._store.list_agent_messages(message.run_id)
        feedback_items = await self._store.list_feedback(message.run_id)
        artifacts = await self._store.list_artifacts(message.run_id)
        events = await self._store.list_events(message.run_id, limit=200)
        audit_content = _a2a_protocol_audit_content(
            messages=messages,
            feedback_items=feedback_items,
            artifacts=artifacts,
            events=events,
        )
        audit_artifact = ArtifactRecord(
            run_id=message.run_id,
            artifact_type=ArtifactType.A2A_CONTRACT_AUDIT,
            title="A2A protocol contract audit",
            uri=(
                f"artifact://runs/{message.run_id}/a2a-contract-audits/"
                f"{message.message_id}"
            ),
            content=audit_content,
            provenance={
                "workflow": "a2a_protocol_audit_worker_v1",
                "agent_id": "a2a-protocol-agent",
                "message_id": str(message.message_id),
                "agent_ids": [agent.id for agent in AGENT_ROSTER],
                "skill_ids": [skill.id for skill in SKILL_CARDS],
                "source_message_ids": [
                    str(agent_message.message_id) for agent_message in messages
                ],
                "generation_mode": "deterministic_protocol_audit",
            },
            revision_history=[
                {
                    "actor": "a2a-protocol-agent",
                    "workflow": "a2a_protocol_audit_worker_v1",
                    "message_id": str(message.message_id),
                    "note": (
                        "Audited agent cards, skill coverage, message handoffs, "
                        "and model/tool boundaries for the current run."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(audit_artifact)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=audit_artifact.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="a2a_protocol_audit_recorded",
                actor="a2a-protocol-agent",
                payload={
                    "message_id": str(message.message_id),
                    "audit_artifact_id": str(audit_artifact.artifact_id),
                    "status": audit_content["status"],
                    "agent_count": audit_content["agent_count"],
                    "skill_count": audit_content["skill_count"],
                    "message_count": audit_content["message_count"],
                    "finding_count": audit_content["finding_count"],
                },
            )
        )
        return {
            "generation_mode": "a2a_protocol_audit_worker",
            "summary": (
                "a2a-protocol-agent recorded a contract audit with "
                f"{audit_content['agent_count']} agent card(s), "
                f"{audit_content['skill_count']} skill card(s), "
                f"{audit_content['message_count']} message handoff(s), and "
                f"{audit_content['finding_count']} finding(s)."
            ),
            "audit_artifact_id": str(audit_artifact.artifact_id),
            "status": audit_content["status"],
            "finding_count": audit_content["finding_count"],
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_content_strategy(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
        request: AgentWorkerRunRequest,
    ) -> dict[str, Any]:
        strategy = await self._execute_gemma_or_deterministic(
            message=message,
            agent_id="content-strategist",
            context_summary=context_summary,
            request=request,
        )
        topic = _topic_from_payload(message.payload)
        feedback_context = _feedback_context_from_payload(message.payload)
        seed_artifacts = await self._ensure_content_strategy_seed_artifacts(
            message=message,
            topic=topic,
        )
        seed_artifact_ids = [str(artifact.artifact_id) for artifact in seed_artifacts]
        target_context = await self._content_strategy_child_target_context(
            message=message,
            seed_artifact_ids=seed_artifact_ids,
            feedback_context=feedback_context,
        )
        child_specs = [
            ("data-analyst-agent", "build_data_brief"),
            ("eli5-short-form-writer", "write_eli5_short_form"),
            ("substack-essay-writer", "write_substack_essay"),
            ("script-doctor", "revise_hook_and_pacing"),
            ("visual-director", "plan_visual_system"),
            ("image-generation-agent", "plan_imagegen_assets"),
            ("audio-producer", "plan_realtime_audio_brief"),
            ("video-reel-producer", "plan_reel_storyboard"),
            ("platform-optimization-agent", "adapt_platform_variants"),
            ("influencer-strategy-agent", "plan_keywords_and_hashtags"),
            ("outreach-agent", "plan_outreach_angles"),
            ("editor-in-chief", "editorial_review_current_artifacts"),
            ("critic-reviewer-agent", "critical_review_current_artifacts"),
            ("artifact-librarian", "build_artifact_index"),
        ]
        child_message_ids = []
        existing_children = {
            (
                existing.recipient_agent_id,
                existing.task_type,
                existing.payload.get("parent_message_id"),
            )
            for existing in await self._store.list_agent_messages(message.run_id)
        }
        for recipient_agent_id, task_type in child_specs:
            key = (recipient_agent_id, task_type, str(message.message_id))
            if key in existing_children:
                continue
            child = AgentMessage(
                message_id=_agent_worker_child_message_id(
                    run_id=message.run_id,
                    parent_message_id=message.message_id,
                    sender_agent_id="content-strategist",
                    recipient_agent_id=recipient_agent_id,
                    task_type=task_type,
                ),
                run_id=message.run_id,
                sender_agent_id="content-strategist",
                recipient_agent_id=recipient_agent_id,
                task_type=task_type,
                payload={
                    "topic": topic,
                    "parent_message_id": str(message.message_id),
                    "strategy_summary": strategy["summary"],
                    "context_summary": context_summary,
                    **feedback_context,
                    **target_context,
                },
            )
            recorded_child = await self._record_agent_message_if_absent(child)
            if recorded_child is None:
                continue
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="agent_message_accepted",
                    actor="content-strategist",
                    payload=public_a2a_message_event_payload(recorded_child),
                )
            )
            child_message_ids.append(str(recorded_child.message_id))
        return {
            **strategy,
            "generation_mode": "content_strategy_worker",
            "summary": (
                f"content-strategist created {len(child_message_ids)} "
                f"downstream task(s) for {topic}."
            ),
            "seed_artifact_ids": seed_artifact_ids,
            "child_message_ids": child_message_ids,
        }

    async def _ensure_content_strategy_seed_artifacts(
        self,
        *,
        message: AgentMessage,
        topic: str,
    ) -> list[ArtifactRecord]:
        existing_artifacts = await self._store.list_artifacts(message.run_id)
        requested_types = _content_strategy_requested_artifact_types(message.payload)
        if not _content_strategy_requires_seed_artifacts(
            payload=message.payload,
            existing_artifacts=existing_artifacts,
        ):
            return []
        existing_seed_artifacts = _content_strategy_seed_artifacts_for_message(
            existing_artifacts,
            message=message,
            requested_types=requested_types,
        )
        existing_seed_types = {
            artifact.artifact_type for artifact in existing_seed_artifacts
        }
        missing_types = [
            artifact_type
            for artifact_type in requested_types
            if artifact_type not in existing_seed_types
        ]
        if not missing_types:
            return existing_seed_artifacts

        all_sources = await self._store.list_sources(message.run_id)
        all_claims = await self._store.list_claims(message.run_id)
        sources, claims = _content_strategy_seed_source_context(
            payload=message.payload,
            artifacts=existing_artifacts,
            sources=all_sources,
            claims=all_claims,
        )
        created: list[ArtifactRecord] = []
        for artifact_type in missing_types:
            artifact = ArtifactRecord(
                artifact_id=_agent_worker_artifact_id(
                    run_id=message.run_id,
                    message_id=message.message_id,
                    workflow="content_strategy_seed_artifact_v1",
                    artifact_type=artifact_type,
                ),
                run_id=message.run_id,
                artifact_type=artifact_type,
                title=_content_strategy_seed_title(artifact_type, topic),
                uri=(
                    f"artifact://runs/{message.run_id}/content-strategy-seeds/"
                    f"{message.message_id}/{artifact_type.value}"
                ),
                content=_content_strategy_seed_content(
                    artifact_type=artifact_type,
                    topic=topic,
                    message=message,
                    sources=sources,
                    claims=claims,
                ),
                provenance={
                    "workflow": "content_strategy_seed_artifact_v1",
                    "agent_id": "content-strategist",
                    "message_id": str(message.message_id),
                    "parent_message_id": message.payload.get("parent_message_id"),
                    "source_message_workflow": message.payload.get("workflow"),
                    "generation_mode": "deterministic_content_strategy_seed",
                    "source_ids": [str(source.source_id) for source in sources],
                    "claim_ids": [str(claim.claim_id) for claim in claims],
                },
                source_ids=[source.source_id for source in sources],
                revision_history=[
                    {
                        "actor": "content-strategist",
                        "workflow": "content_strategy_seed_artifact_v1",
                        "message_id": str(message.message_id),
                        "note": (
                            "Created a durable seed draft from a voice or "
                            "conversation-originated content strategy task."
                        ),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            )
            recorded = await self._record_artifact_if_absent(artifact)
            if recorded is None:
                continue
            created.append(recorded)
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="artifact_recorded",
                    actor="artifact-librarian",
                    payload=recorded.model_dump(mode="json"),
                )
            )

        if created:
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="content_strategy_seed_artifacts_created",
                    actor="content-strategist",
                    payload={
                        "message_id": str(message.message_id),
                        "artifact_ids": [
                            str(artifact.artifact_id) for artifact in created
                        ],
                        "artifact_types": [
                            artifact.artifact_type.value for artifact in created
                        ],
                        "source_count": len(sources),
                        "claim_count": len(claims),
                    },
                )
            )
        refreshed_artifacts = await self._store.list_artifacts(message.run_id)
        final_seed_artifacts = _content_strategy_seed_artifacts_for_message(
            refreshed_artifacts,
            message=message,
            requested_types=requested_types,
        )
        final_seed_types = {artifact.artifact_type for artifact in final_seed_artifacts}
        missing_final_types = [
            artifact_type.value
            for artifact_type in requested_types
            if artifact_type not in final_seed_types
        ]
        if missing_final_types:
            raise RuntimeError(
                "Content strategy seed artifact creation did not materialize "
                f"all requested types: {missing_final_types}."
            )
        return final_seed_artifacts

    async def _content_strategy_child_target_context(
        self,
        *,
        message: AgentMessage,
        seed_artifact_ids: list[str],
        feedback_context: dict[str, Any],
    ) -> dict[str, Any]:
        if feedback_context.get("target_artifact_ids"):
            return {
                "target_artifact_ids": feedback_context["target_artifact_ids"],
                "target_artifact_selection": feedback_context.get(
                    "target_artifact_selection",
                    "explicit_target_artifacts",
                ),
            }
        if seed_artifact_ids:
            return {
                "target_artifact_ids": seed_artifact_ids,
                "target_artifact_selection": "content_strategy_seed_artifacts",
            }
        artifacts = await self._store.list_artifacts(message.run_id)
        requested_types = set(_content_strategy_requested_artifact_types(message.payload))
        existing_source_artifacts = [
            artifact
            for artifact in _leaf_source_content_artifacts(artifacts)
            if artifact.artifact_type in requested_types
        ]
        existing_source_artifacts_by_type: dict[ArtifactType, list[ArtifactRecord]] = {}
        for artifact in existing_source_artifacts:
            existing_source_artifacts_by_type.setdefault(
                artifact.artifact_type,
                [],
            ).append(artifact)
        ambiguous_artifact_ids = {
            artifact_type.value: [
                str(artifact.artifact_id) for artifact in matching_artifacts
            ]
            for artifact_type, matching_artifacts in existing_source_artifacts_by_type.items()
            if len(matching_artifacts) > 1
        }
        if ambiguous_artifact_ids:
            raise RuntimeError(
                "Content strategy task has ambiguous existing source artifacts; "
                "provide explicit target_artifact_ids. "
                f"ambiguous_artifact_ids={ambiguous_artifact_ids}"
            )
        existing_source_artifact_ids = [
            str(artifact.artifact_id) for artifact in existing_source_artifacts
        ]
        if not existing_source_artifact_ids:
            return {}
        return {
            "target_artifact_ids": existing_source_artifact_ids,
            "target_artifact_selection": "existing_source_content_artifacts",
        }

    async def _execute_intent_route_plan(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        run = await self._store.get_run(message.run_id)
        if run is None:
            raise AgentWorkerRunNotFoundError(f"Run not found: {message.run_id}")

        messages = await self._store.list_agent_messages(message.run_id)
        turns = await self._store.list_conversation_turns(message.run_id)
        artifacts = await self._store.list_artifacts(message.run_id)
        sources = await self._store.list_sources(message.run_id)
        feedback_items = await self._store.list_feedback(message.run_id)
        target_agent_ids = _select_intent_route_targets(message.payload)
        planned_handoffs = [
            {
                "target_agent_id": target_agent_id,
                "target_agent_name": _agent_name(target_agent_id),
                "task_type": _intent_router_task_type(target_agent_id),
                "reason": _intent_route_target_reason(
                    target_agent_id=target_agent_id,
                    payload=message.payload,
                ),
            }
            for target_agent_id in target_agent_ids
        ]
        plan_content = _intent_route_plan_content(
            run=run,
            message=message,
            context_summary=context_summary,
            target_agent_ids=target_agent_ids,
            planned_handoffs=planned_handoffs,
            turns=turns,
            messages=messages,
            artifacts=artifacts,
            sources=sources,
            feedback_items=feedback_items,
        )
        topic = plan_content["topic"]
        route_plan = _existing_worker_artifact(
            artifacts,
            artifact_type=ArtifactType.INTENT_ROUTE_PLAN,
            workflow="intent_router_worker_v1",
            message_id=message.message_id,
        )
        route_plan_created = route_plan is None
        if route_plan is None:
            route_plan = ArtifactRecord(
                artifact_id=_agent_worker_artifact_id(
                    run_id=message.run_id,
                    message_id=message.message_id,
                    workflow="intent_router_worker_v1",
                    artifact_type=ArtifactType.INTENT_ROUTE_PLAN,
                ),
                run_id=message.run_id,
                artifact_type=ArtifactType.INTENT_ROUTE_PLAN,
                title=f"Intent route plan: {topic}",
                uri=(
                    f"artifact://runs/{message.run_id}/intent-route-plans/"
                    f"{message.message_id}"
                ),
                content=plan_content,
                provenance={
                    "workflow": "intent_router_worker_v1",
                    "agent_id": "intent-router",
                    "message_id": str(message.message_id),
                    "turn_id": message.payload.get("turn_id"),
                    "target_agent_ids": target_agent_ids,
                    "generation_mode": "deterministic_intent_route_plan",
                },
                revision_history=[
                    {
                        "actor": "intent-router",
                        "workflow": "intent_router_worker_v1",
                        "message_id": str(message.message_id),
                        "note": (
                            "Converted a live dialogue handoff into a durable "
                            "route plan and specialist A2A task set."
                        ),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            )
            recorded_route_plan = await self._record_artifact_if_absent(route_plan)
            if recorded_route_plan is None:
                refreshed_artifacts = await self._store.list_artifacts(message.run_id)
                route_plan = _existing_worker_artifact(
                    refreshed_artifacts,
                    artifact_type=ArtifactType.INTENT_ROUTE_PLAN,
                    workflow="intent_router_worker_v1",
                    message_id=message.message_id,
                )
                route_plan_created = False
                if route_plan is None:
                    raise RuntimeError(
                        "Intent route plan insert was skipped but no existing "
                        "route plan artifact could be loaded."
                    )
            else:
                route_plan = recorded_route_plan
                await self._store.append_event(
                    RunEvent(
                        run_id=message.run_id,
                        event_type="artifact_recorded",
                        actor="artifact-librarian",
                        payload=route_plan.model_dump(mode="json"),
                    )
                )

        existing_children = {
            (
                existing.recipient_agent_id,
                existing.task_type,
                existing.payload.get("parent_message_id"),
            )
            for existing in messages
            if existing.payload.get("parent_message_id")
        }
        created_task_message_ids = []
        created_target_agent_ids = []
        for handoff in planned_handoffs:
            key = (
                handoff["target_agent_id"],
                handoff["task_type"],
                str(message.message_id),
            )
            if key in existing_children:
                continue
            child = AgentMessage(
                message_id=_agent_worker_child_message_id(
                    run_id=message.run_id,
                    parent_message_id=message.message_id,
                    sender_agent_id="intent-router",
                    recipient_agent_id=handoff["target_agent_id"],
                    task_type=handoff["task_type"],
                ),
                run_id=message.run_id,
                sender_agent_id="intent-router",
                recipient_agent_id=handoff["target_agent_id"],
                task_type=handoff["task_type"],
                payload={
                    "topic": topic,
                    "turn_id": message.payload.get("turn_id"),
                    "transcript": message.payload.get("transcript"),
                    "target_formats": message.payload.get("target_formats", []),
                    "requested_intent": message.payload.get("requested_intent"),
                    "routed_intent": message.payload.get("routed_intent"),
                    "route_reason": handoff["reason"],
                    "route_plan_artifact_id": str(route_plan.artifact_id),
                    "parent_message_id": str(message.message_id),
                    "context_summary": context_summary,
                },
            )
            recorded_child = await self._record_agent_message_if_absent(child)
            if recorded_child is None:
                continue
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="agent_message_accepted",
                    actor="intent-router",
                    payload=public_a2a_message_event_payload(recorded_child),
                )
            )
            created_task_message_ids.append(str(recorded_child.message_id))
            created_target_agent_ids.append(recorded_child.recipient_agent_id)

        if route_plan_created or created_task_message_ids:
            prior_created_task_ids = [
                str(task_id)
                for task_id in route_plan.content.get("created_task_message_ids", [])
            ]
            prior_created_target_ids = [
                str(agent_id)
                for agent_id in route_plan.content.get("created_target_agent_ids", [])
            ]
            route_plan.content["created_task_message_ids"] = _dedupe_preserve_order(
                [*prior_created_task_ids, *created_task_message_ids]
            )
            route_plan.content["created_target_agent_ids"] = _dedupe_preserve_order(
                [*prior_created_target_ids, *created_target_agent_ids]
            )
            route_plan.revision_history.append(
                {
                    "actor": "intent-router",
                    "workflow": "intent_router_worker_v1",
                    "message_id": str(message.message_id),
                    "note": (
                        f"Materialized {len(created_task_message_ids)} downstream "
                        "specialist A2A task(s) from the route plan."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            updated_route_plan = await self._store.update_artifact(route_plan)
            if updated_route_plan is None:
                raise RuntimeError(
                    "Intent route plan artifact disappeared before update."
                )
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="intent_route_plan_created",
                    actor="intent-router",
                    payload={
                        "message_id": str(message.message_id),
                        "route_plan_artifact_id": str(route_plan.artifact_id),
                        "target_agent_ids": target_agent_ids,
                        "created_task_message_ids": created_task_message_ids,
                        "requested_intent": message.payload.get("requested_intent"),
                        "routed_intent": message.payload.get("routed_intent"),
                        "reused_existing_artifact": not route_plan_created,
                    },
                )
            )
        return {
            "generation_mode": "intent_router_worker",
            "summary": (
                "intent-router created an intent route plan and "
                f"{len(created_task_message_ids)} downstream task(s) for {topic}."
            ),
            "route_plan_artifact_id": str(route_plan.artifact_id),
            "target_agent_ids": target_agent_ids,
            "created_task_message_ids": created_task_message_ids,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_data_analysis(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        await require_tool_allowed(
            self._store,
            run_id=message.run_id,
            agent_id="data-analyst-agent",
            tool_name="source_ledger",
            reason="data_analysis_reads_sources_claims_and_artifacts",
            message_id=message.message_id,
        )
        run = await self._store.get_run(message.run_id)
        sources = await self._store.list_sources(message.run_id)
        claims = await self._store.list_claims(message.run_id)
        artifacts = await self._store.list_artifacts(message.run_id)
        topic = _topic_from_payload(message.payload)
        data_brief = ArtifactRecord(
            run_id=message.run_id,
            artifact_type=ArtifactType.DATA_BRIEF,
            title=f"Data brief: {topic}",
            uri=(
                f"artifact://runs/{message.run_id}/data-brief/"
                f"{message.message_id}"
            ),
            content=_data_brief_content_for(
                topic=topic,
                run_goal=run.goal if run else None,
                sources=sources,
                claims=claims,
                artifacts=artifacts,
            ),
            provenance={
                "workflow": "data_analysis_worker_v1",
                "agent_id": "data-analyst-agent",
                "message_id": str(message.message_id),
                "source_ids": [str(source.source_id) for source in sources],
                "claim_ids": [str(claim.claim_id) for claim in claims],
                "generation_mode": "deterministic_data_analysis",
            },
            source_ids=[source.source_id for source in sources],
            revision_history=[
                {
                    "actor": "data-analyst-agent",
                    "workflow": "data_analysis_worker_v1",
                    "message_id": str(message.message_id),
                    "note": (
                        "Created a source-backed data brief from current sources, "
                        "claims, and artifact dependencies."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(data_brief)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=data_brief.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="data_analysis_artifact_created",
                actor="data-analyst-agent",
                payload={
                    "message_id": str(message.message_id),
                    "data_artifact_id": str(data_brief.artifact_id),
                    "source_count": len(sources),
                    "claim_count": len(claims),
                    "artifact_count": len(artifacts),
                    "source_ids": [str(source.source_id) for source in sources],
                    "claim_ids": [str(claim.claim_id) for claim in claims],
                },
            )
        )
        return {
            "generation_mode": "data_analysis_worker",
            "summary": (
                "data-analyst-agent created a source-backed data brief with "
                f"{len(sources)} source(s), {len(claims)} claim(s), and "
                f"{len(artifacts)} artifact dependency row(s)."
            ),
            "data_artifact_id": str(data_brief.artifact_id),
            "source_count": len(sources),
            "claim_count": len(claims),
            "artifact_count": len(artifacts),
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_content_writer(
        self,
        *,
        message: AgentMessage,
        agent_id: str,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        all_artifacts = await self._store.list_artifacts(message.run_id)
        feedback_context = _feedback_context_from_payload(message.payload)
        source_artifacts = _writer_source_artifacts(
            all_artifacts,
            agent_id,
            target_artifact_ids=feedback_context.get("target_artifact_ids", []),
        )
        retrieval_evidence_by_source_id = accepted_retrieval_evidence_by_source(
            all_artifacts
        )
        claim_revision_plan = _latest_claim_revision_plan(all_artifacts)
        topic = _topic_from_payload(message.payload)
        created_artifact_ids = []
        source_artifact_ids = []
        retrieval_acceptance_statuses = []
        claim_revision_context_statuses = []
        for artifact in source_artifacts:
            writer_source_ids, retrieval_acceptance_status = (
                _writer_source_ids_for_retrieval(
                    artifact,
                    retrieval_evidence_by_source_id,
                )
            )
            retrieval_context = {
                "acceptance_status": retrieval_acceptance_status,
                "accepted_source_count": sum(
                    1
                    for source_id in writer_source_ids
                    if source_id in retrieval_evidence_by_source_id
                ),
                "accepted_sources": retrieval_evidence_payloads_for_source_ids(
                    writer_source_ids,
                    retrieval_evidence_by_source_id,
                ),
            }
            claim_revision_context = _writer_claim_revision_context(
                claim_revision_plan,
                _extract_artifact_claim_ids(artifact),
            )
            writer_artifact = ArtifactRecord(
                run_id=message.run_id,
                artifact_type=artifact.artifact_type,
                title=_writer_artifact_title(artifact, agent_id),
                uri=(
                    f"artifact://runs/{message.run_id}/writer-drafts/"
                    f"{message.message_id}/{artifact.artifact_id}"
                ),
                content=_writer_content_for(
                    artifact=artifact,
                    topic=topic,
                    agent_id=agent_id,
                    source_ids=writer_source_ids,
                    retrieval_context=retrieval_context,
                    claim_revision_context=claim_revision_context,
                    feedback_context=feedback_context,
                ),
                provenance={
                    "workflow": "content_writer_worker_v1",
                    "parent_artifact_id": str(artifact.artifact_id),
                    "parent_message_id": str(message.message_id),
                    "agent_id": agent_id,
                    "source_ids": [str(source_id) for source_id in writer_source_ids],
                    "retrieval_acceptance_status": retrieval_acceptance_status,
                    "accepted_retrieval_source_ids": [
                        str(source_id)
                        for source_id in writer_source_ids
                        if source_id in retrieval_evidence_by_source_id
                    ],
                    "accepted_retrieval_sources": (
                        retrieval_context["accepted_sources"]
                    ),
                    "claim_revision_plan_artifact_id": (
                        claim_revision_context.get("artifact_id")
                    ),
                    "claim_revision_status": claim_revision_context.get("status"),
                    "held_claim_ids": claim_revision_context.get(
                        "held_claim_ids",
                        [],
                    ),
                    "claim_ids": [
                        str(claim_id) for claim_id in _extract_artifact_claim_ids(artifact)
                    ],
                    "generation_mode": "deterministic_writer",
                    "parent_provenance": artifact.provenance,
                    **_feedback_provenance_fields(feedback_context),
                },
                revision_history=[
                    *artifact.revision_history,
                    {
                        "actor": agent_id,
                        "workflow": "content_writer_worker_v1",
                        "parent_artifact_id": str(artifact.artifact_id),
                        "message_id": str(message.message_id),
                        "feedback_id": feedback_context.get("feedback_id"),
                        "note": (
                            "Created specialist writer version from the targeted "
                            "source-backed artifact."
                        ),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                ],
                source_ids=writer_source_ids,
            )
            await self._store.record_artifact(writer_artifact)
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="artifact_recorded",
                    actor="artifact-librarian",
                    payload=writer_artifact.model_dump(mode="json"),
                )
            )
            created_artifact_ids.append(str(writer_artifact.artifact_id))
            source_artifact_ids.append(str(artifact.artifact_id))
            retrieval_acceptance_statuses.append(retrieval_acceptance_status)
            claim_revision_context_statuses.append(
                claim_revision_context.get("status")
            )

        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="content_writer_artifacts_created",
                actor=agent_id,
                payload={
                    "message_id": str(message.message_id),
                    "source_artifact_ids": source_artifact_ids,
                    "created_artifact_ids": created_artifact_ids,
                    "artifact_count": len(created_artifact_ids),
                    "retrieval_acceptance_statuses": retrieval_acceptance_statuses,
                    "claim_revision_context_statuses": (
                        claim_revision_context_statuses
                    ),
                },
            )
        )
        return {
            "generation_mode": "content_writer_worker",
            "summary": (
                f"{agent_id} created {len(created_artifact_ids)} "
                "source-backed writer artifact version(s)."
            ),
            "source_artifact_ids": source_artifact_ids,
            "created_artifact_ids": created_artifact_ids,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_script_doctor(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        all_artifacts = await self._store.list_artifacts(message.run_id)
        feedback_context = _feedback_context_from_payload(message.payload)
        source_artifacts = _script_doctor_source_artifacts(
            all_artifacts,
            target_artifact_ids=feedback_context.get("target_artifact_ids", []),
        )
        topic = _topic_from_payload(message.payload)
        created_artifact_ids = []
        source_artifact_ids = []
        for artifact in source_artifacts:
            doctored_artifact = ArtifactRecord(
                run_id=message.run_id,
                artifact_type=ArtifactType.REEL_SCRIPT,
                title=f"Script Doctor version: {artifact.title}",
                uri=(
                    f"artifact://runs/{message.run_id}/script-doctor/"
                    f"{message.message_id}/{artifact.artifact_id}"
                ),
                content=_script_doctor_content_for(
                    artifact=artifact,
                    topic=topic,
                    feedback_context=feedback_context,
                ),
                provenance={
                    "workflow": "script_doctor_worker_v1",
                    "parent_artifact_id": str(artifact.artifact_id),
                    "parent_message_id": str(message.message_id),
                    "agent_id": SCRIPT_DOCTOR_AGENT_ID,
                    "source_ids": [str(source_id) for source_id in artifact.source_ids],
                    "claim_ids": [
                        str(claim_id) for claim_id in _extract_artifact_claim_ids(artifact)
                    ],
                    "generation_mode": "deterministic_script_doctor",
                    "parent_provenance": artifact.provenance,
                    **_feedback_provenance_fields(feedback_context),
                },
                source_ids=artifact.source_ids,
                revision_history=[
                    *artifact.revision_history,
                    {
                        "actor": SCRIPT_DOCTOR_AGENT_ID,
                        "workflow": "script_doctor_worker_v1",
                        "parent_artifact_id": str(artifact.artifact_id),
                        "message_id": str(message.message_id),
                        "feedback_id": feedback_context.get("feedback_id"),
                        "note": (
                            "Created hook, pacing, and retention-optimized reel "
                            "script version from targeted feedback."
                        ),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                ],
            )
            await self._store.record_artifact(doctored_artifact)
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="artifact_recorded",
                    actor="artifact-librarian",
                    payload=doctored_artifact.model_dump(mode="json"),
                )
            )
            created_artifact_ids.append(str(doctored_artifact.artifact_id))
            source_artifact_ids.append(str(artifact.artifact_id))

        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="script_doctor_artifacts_created",
                actor=SCRIPT_DOCTOR_AGENT_ID,
                payload={
                    "message_id": str(message.message_id),
                    "source_artifact_ids": source_artifact_ids,
                    "created_artifact_ids": created_artifact_ids,
                    "artifact_count": len(created_artifact_ids),
                },
            )
        )
        return {
            "generation_mode": "script_doctor_worker",
            "summary": (
                "script-doctor created "
                f"{len(created_artifact_ids)} hook/pacing artifact version(s)."
            ),
            "source_artifact_ids": source_artifact_ids,
            "created_artifact_ids": created_artifact_ids,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_editorial_review(
        self,
        *,
        message: AgentMessage,
        agent_id: str,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        all_artifacts = await self._store.list_artifacts(message.run_id)
        artifacts = _leaf_editorial_artifacts(all_artifacts)
        claims = await self._store.list_claims(message.run_id)
        claim_by_id = {claim.claim_id: claim for claim in claims}
        retrieval_evidence_by_source_id = accepted_retrieval_evidence_by_source(
            all_artifacts
        )
        retrieval_ledger = latest_retrieval_quality_ledger(all_artifacts)
        reviewed_artifact_ids = []
        skipped_artifact_ids = []
        decisions = []
        for artifact in artifacts:
            if _has_current_review(artifact, agent_id):
                skipped_artifact_ids.append(str(artifact.artifact_id))
                continue
            decision = _editorial_decision_for(
                artifact=artifact,
                reviewer_agent_id=agent_id,
                claim_by_id=claim_by_id,
                retrieval_evidence_by_source_id=retrieval_evidence_by_source_id,
                retrieval_ledger_available=retrieval_ledger is not None,
            )
            accepted_retrieval_source_ids = [
                str(source_id)
                for source_id in artifact.source_ids
                if source_id in retrieval_evidence_by_source_id
            ]
            decision_payload = {
                **decision.model_dump(mode="json"),
                "workflow": "editorial_review_worker_v1",
                "message_id": str(message.message_id),
                "accepted_retrieval_source_ids": accepted_retrieval_source_ids,
                "retrieval_ledger_artifact_id": (
                    str(retrieval_ledger.artifact_id)
                    if retrieval_ledger
                    else None
                ),
            }
            artifact.reviewer_decisions.append(decision_payload)
            artifact.revision_history.append(
                {
                    "actor": agent_id,
                    "workflow": "editorial_review_worker_v1",
                    "note": decision.notes,
                    "status": decision.status.value,
                    "blocking_issues": decision.blocking_issues,
                    "accepted_retrieval_source_ids": accepted_retrieval_source_ids,
                }
            )
            await self._store.update_artifact(artifact)
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="review_decision_recorded",
                    actor=agent_id,
                    payload={
                        "artifact_id": str(artifact.artifact_id),
                        "message_id": str(message.message_id),
                        "decision": decision_payload,
                    },
                )
            )
            reviewed_artifact_ids.append(str(artifact.artifact_id))
            decisions.append(decision)

        status_counts = {
            status.value: sum(1 for decision in decisions if decision.status == status)
            for status in ReviewDecisionStatus
        }
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="editorial_review_completed",
                actor=agent_id,
                payload={
                    "message_id": str(message.message_id),
                    "reviewed_artifact_ids": reviewed_artifact_ids,
                    "skipped_artifact_ids": skipped_artifact_ids,
                    "status_counts": status_counts,
                },
            )
        )
        return {
            "generation_mode": "editorial_review_worker",
            "summary": (
                f"{agent_id} reviewed {len(reviewed_artifact_ids)} artifact(s) "
                f"and skipped {len(skipped_artifact_ids)} already-reviewed artifact(s)."
            ),
            "reviewed_artifact_ids": reviewed_artifact_ids,
            "skipped_artifact_ids": skipped_artifact_ids,
            "status_counts": status_counts,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_product_manager_sync(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        pulse = await RunSyncPulseWorkflow(self._store).build(
            message.run_id,
            RunSyncPulseRequest(
                record_artifact=True,
                build_work_plan=True,
                create_followup_tasks=bool(
                    message.payload.get("create_followup_tasks", False)
                ),
                include_completed_tasks=bool(
                    message.payload.get("include_completed_tasks", False)
                ),
                max_work_items=int(message.payload.get("max_work_items", 25)),
                include_all_active_agents=bool(
                    message.payload.get("include_all_active_agents", True)
                ),
                notes=_payload_text(
                    message.payload,
                    "notes",
                    f"Product Manager worker processed {message.task_type}.",
                ),
            ),
        )
        return {
            "generation_mode": "management_sync_worker",
            "summary": (
                "product-manager recorded a multi-agent sync pulse with "
                f"{len(pulse.agent_states)} agent state(s), "
                f"{len(pulse.blockers)} blocker(s), and "
                f"{len(pulse.recommended_agent_ids)} recommended agent(s)."
            ),
            "sync_pulse_artifact_id": (
                str(pulse.artifact_id) if pulse.artifact_id else None
            ),
            "work_plan_artifact_id": (
                str(pulse.work_plan.artifact_id)
                if pulse.work_plan and pulse.work_plan.artifact_id
                else None
            ),
            "work_plan_item_count": (
                len(pulse.work_plan.plan_items) if pulse.work_plan else 0
            ),
            "created_task_message_ids": (
                [
                    str(message_id)
                    for message_id in pulse.work_plan.created_task_message_ids
                ]
                if pulse.work_plan
                else []
            ),
            "recommended_agent_ids": pulse.recommended_agent_ids,
            "blockers": pulse.blockers,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_sprint_work_plan(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        work_plan = await RunWorkPlanWorkflow(self._store).build(
            message.run_id,
            RunWorkPlanRequest(
                record_artifact=True,
                include_completed_tasks=bool(
                    message.payload.get("include_completed_tasks", False)
                ),
                create_followup_tasks=bool(
                    message.payload.get("create_followup_tasks", False)
                ),
                max_items=int(message.payload.get("max_items", 25)),
            ),
        )
        return {
            "generation_mode": "sprint_work_plan_worker",
            "summary": (
                "sprint-progress-agent built a durable next-pass work plan with "
                f"{len(work_plan.plan_items)} item(s), "
                f"{work_plan.pending_task_count} pending task(s), and "
                f"{len(work_plan.created_task_message_ids)} created follow-up task(s)."
            ),
            "work_plan_artifact_id": (
                str(work_plan.artifact_id) if work_plan.artifact_id else None
            ),
            "plan_item_count": len(work_plan.plan_items),
            "pending_task_count": work_plan.pending_task_count,
            "blocked_item_count": work_plan.blocked_item_count,
            "created_task_message_ids": [
                str(message_id) for message_id in work_plan.created_task_message_ids
            ],
            "recommended_agent_ids": work_plan.recommended_agent_ids,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_interactive_note_worker(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        note_result = await InteractiveRunNoteWorkflow(
            self._store,
            artifacts_root=self._artifacts_root,
        ).generate(
            message.run_id,
            InteractiveRunNoteRequest(
                title=_payload_text(
                    message.payload,
                    "title",
                    "Interactive run note",
                ),
                include_event_payloads=bool(
                    message.payload.get("include_event_payloads", False)
                ),
            ),
        )
        return {
            "generation_mode": "interactive_note_worker",
            "summary": note_result.summary,
            "artifact_id": str(note_result.artifact_id),
            "uri": note_result.uri,
            "file_path": note_result.file_path,
            "event_id": note_result.event_id,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_obsidian_review_note_worker(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        note_result = await ObsidianReviewNoteWorkflow(
            self._store,
            vault_path=self._obsidian_vault_path,
        ).generate(
            message.run_id,
            ObsidianReviewNoteRequest(
                title=_payload_text(
                    message.payload,
                    "title",
                    "Obsidian run review",
                ),
                note_kind=_payload_text(
                    message.payload,
                    "note_kind",
                    "run_review",
                ),
                include_event_tail=bool(
                    message.payload.get("include_event_tail", True)
                ),
                event_limit=int(message.payload.get("event_limit", 25)),
            ),
        )
        return {
            "generation_mode": "obsidian_review_note_worker",
            "summary": note_result.summary,
            "artifact_id": str(note_result.artifact_id),
            "uri": note_result.uri,
            "file_path": note_result.file_path,
            "note_kind": note_result.note_kind,
            "event_id": note_result.event_id,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_obsidian_memory_promotion_worker(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        promotion_result = await ObsidianMemoryPromotionWorkflow(
            self._store,
            vault_path=self._obsidian_vault_path,
        ).generate(
            message.run_id,
            ObsidianMemoryPromotionRequest(
                title=_payload_text(
                    message.payload,
                    "title",
                    "Obsidian memory promotion",
                ),
                promotion_kind=_payload_text(
                    message.payload,
                    "promotion_kind",
                    "run_memory_promotion",
                ),
                target_wiki_notes=_payload_text_list(
                    message.payload,
                    "target_wiki_notes",
                    [
                        "wiki/product/agent-studio-memory-layer.md",
                        "wiki/ops/codex-obsidian-working-memory.md",
                    ],
                ),
                include_review_note_links=bool(
                    message.payload.get("include_review_note_links", True)
                ),
                event_limit=int(message.payload.get("event_limit", 50)),
            ),
        )
        return {
            "generation_mode": "obsidian_memory_promotion_worker",
            "summary": promotion_result.summary,
            "artifact_id": str(promotion_result.artifact_id),
            "uri": promotion_result.uri,
            "file_path": promotion_result.file_path,
            "promotion_kind": promotion_result.promotion_kind,
            "target_wiki_notes": promotion_result.target_wiki_notes,
            "promoted_item_count": promotion_result.promoted_item_count,
            "event_id": promotion_result.event_id,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_project_memory_record(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        memory_result = await ProjectMemoryWorkflow(self._store).record(
            message.run_id,
            ProjectMemoryRecordRequest(
                memory_kind=_payload_text(
                    message.payload,
                    "memory_kind",
                    "user_preference",
                ),
                content=_payload_text(
                    message.payload,
                    "content",
                    "No project memory content provided.",
                ),
                agent_id=_payload_optional_text(message.payload, "agent_id")
                or message.recipient_agent_id,
                scope=_payload_text(message.payload, "scope", "global"),
                embedding=message.payload.get("embedding")
                if isinstance(message.payload.get("embedding"), list)
                else None,
                confidence=_payload_text(message.payload, "confidence", "medium"),
                tags=_payload_text_list(message.payload, "tags", []),
                source_artifact_ids=_payload_text_list(
                    message.payload,
                    "source_artifact_ids",
                    [],
                ),
                target_wiki_notes=_payload_text_list(
                    message.payload,
                    "target_wiki_notes",
                    [],
                ),
                metadata=dict(message.payload.get("metadata", {}))
                if isinstance(message.payload.get("metadata"), dict)
                else {},
            ),
        )
        return {
            "generation_mode": "project_memory_record_worker",
            "summary": memory_result.summary,
            "memory_id": str(memory_result.memory.memory_id),
            "memory_kind": memory_result.memory.memory_kind,
            "memory_scope": memory_result.memory_scope.value,
            "agent_id": memory_result.memory.agent_id,
            "event_id": memory_result.event_id,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_project_memory_retrieval(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        retrieval_result = await ProjectMemoryRetrievalWorkflow(self._store).retrieve(
            message.run_id,
            ProjectMemoryRetrievalRequest(
                query=_payload_text(
                    message.payload,
                    "query",
                    _payload_text(message.payload, "topic", "project memory"),
                ),
                agent_id=_payload_optional_text(message.payload, "agent_id"),
                query_embedding=message.payload.get("query_embedding")
                if isinstance(message.payload.get("query_embedding"), list)
                else None,
                include_global_memories=bool(
                    message.payload.get("include_global_memories", True)
                ),
                memory_kinds=_payload_text_list(
                    message.payload,
                    "memory_kinds",
                    [],
                ),
                tags=_payload_text_list(message.payload, "tags", []),
                target_wiki_notes=_payload_text_list(
                    message.payload,
                    "target_wiki_notes",
                    [],
                ),
                seed_limit=int(message.payload.get("seed_limit", 10)),
                memory_limit=int(message.payload.get("memory_limit", 20)),
                graph_memory_limit=int(
                    message.payload.get("graph_memory_limit", 80)
                ),
                graph_depth=int(message.payload.get("graph_depth", 1)),
                record_artifact=bool(message.payload.get("record_artifact", True)),
            ),
        )
        return {
            "generation_mode": "project_memory_retrieval_worker",
            "summary": retrieval_result.summary,
            "artifact_id": (
                str(retrieval_result.artifact_id)
                if retrieval_result.artifact_id
                else None
            ),
            "event_id": retrieval_result.event_id,
            "query": retrieval_result.query,
            "agent_id": retrieval_result.agent_id,
            "memory_count": retrieval_result.memory_count,
            "seed_memory_count": retrieval_result.seed_memory_count,
            "related_memory_count": retrieval_result.related_memory_count,
            "graph_node_count": retrieval_result.graph_node_count,
            "graph_edge_count": retrieval_result.graph_edge_count,
            "recommended_actions": retrieval_result.recommended_actions,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_runtime_health_ledger(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        ledger = await RuntimeHealthLedgerWorkflow(self._store).build(
            message.run_id,
            RuntimeHealthLedgerRequest(
                record_artifact=bool(message.payload.get("record_artifact", True)),
                event_limit=int(message.payload.get("event_limit", 250)),
                include_static_checks=bool(
                    message.payload.get("include_static_checks", True)
                ),
                include_run_evidence=bool(
                    message.payload.get("include_run_evidence", True)
                ),
                record_live_store_evidence=bool(
                    message.payload.get("record_live_store_evidence", True)
                ),
            ),
        )
        return {
            "generation_mode": "runtime_health_ledger_worker",
            "summary": ledger.summary,
            "ledger_artifact_id": (
                str(ledger.ledger_artifact_id) if ledger.ledger_artifact_id else None
            ),
            "status": ledger.status.value,
            "check_count": ledger.check_count,
            "ready_count": ledger.ready_count,
            "degraded_count": ledger.degraded_count,
            "blocked_count": ledger.blocked_count,
            "unknown_count": ledger.unknown_count,
            "event_id": ledger.event_id,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_observability_report(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        run = await self._store.get_run(message.run_id)
        if run is None:
            raise AgentWorkerRunNotFoundError(f"Run not found: {message.run_id}")
        messages = await self._store.list_agent_messages(message.run_id)
        events = await self._store.list_events(
            message.run_id,
            limit=int(message.payload.get("event_limit", 250)),
        )
        artifacts = await self._store.list_artifacts(message.run_id)
        sources = await self._store.list_sources(message.run_id)
        claims = await self._store.list_claims(message.run_id)
        feedback_items = await self._store.list_feedback(message.run_id)
        guardrail_audits = await self._store.list_guardrail_audits(message.run_id)
        worker_profiles = await self._store.list_worker_profiles(message.run_id)
        report_content = _observability_report_content(
            run=run,
            messages=messages,
            events=events,
            artifacts=artifacts,
            sources=sources,
            claims=claims,
            feedback_items=feedback_items,
            guardrail_audits=guardrail_audits,
            worker_profiles=worker_profiles,
        )
        report = ArtifactRecord(
            run_id=message.run_id,
            artifact_type=ArtifactType.RUN_HEALTH_REPORT,
            title="Run health report",
            uri=(
                f"artifact://runs/{message.run_id}/observability/"
                f"{message.message_id}"
            ),
            content=report_content,
            provenance={
                "workflow": "observability_report_worker_v1",
                "agent_id": "observability-agent",
                "message_id": str(message.message_id),
                "source_event_count": len(events),
                "source_message_count": len(messages),
                "generation_mode": "deterministic_observability_report",
            },
            revision_history=[
                {
                    "actor": "observability-agent",
                    "workflow": "observability_report_worker_v1",
                    "message_id": str(message.message_id),
                    "note": (
                        "Created a run health report from events, tasks, "
                        "artifacts, feedback, guardrails, sources, claims, "
                        "and worker profiles."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(report)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=report.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="observability_report_recorded",
                actor="observability-agent",
                payload={
                    "message_id": str(message.message_id),
                    "report_artifact_id": str(report.artifact_id),
                    "health_status": report_content["health_status"],
                    "risk_count": report_content["risk_count"],
                    "event_count": report_content["event_count"],
                    "message_count": report_content["message_count"],
                    "artifact_count": report_content["artifact_count"],
                },
            )
        )
        return {
            "generation_mode": "observability_worker",
            "summary": (
                "observability-agent recorded a run health report with "
                f"{report_content['event_count']} event(s), "
                f"{report_content['message_count']} message(s), "
                f"{report_content['artifact_count']} artifact(s), and "
                f"{report_content['risk_count']} risk item(s)."
            ),
            "report_artifact_id": str(report.artifact_id),
            "health_status": report_content["health_status"],
            "risk_count": report_content["risk_count"],
            "event_count": report_content["event_count"],
            "message_count": report_content["message_count"],
            "artifact_count": report_content["artifact_count"],
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_artifact_librarian_index(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        sources = await self._store.list_sources(message.run_id)
        claims = await self._store.list_claims(message.run_id)
        artifacts = [
            artifact
            for artifact in await self._store.list_artifacts(message.run_id)
            if artifact.artifact_type != ArtifactType.ARTIFACT_INDEX
        ]
        events = await self._store.list_events(
            message.run_id,
            limit=int(message.payload.get("event_limit", 200)),
        )
        messages = await self._store.list_agent_messages(message.run_id)
        feedback_items = await self._store.list_feedback(message.run_id)
        guardrail_audits = await self._store.list_guardrail_audits(message.run_id)
        claim_revision_ledger = await self._record_claim_revision_ledger_if_needed(
            message=message,
            artifacts=artifacts,
            claims=claims,
            messages=messages,
        )
        if claim_revision_ledger is not None:
            artifacts.append(claim_revision_ledger)
        index_content = _artifact_librarian_index_content(
            artifacts=artifacts,
            sources=sources,
            claims=claims,
            events=events,
            messages=messages,
            feedback_items=feedback_items,
            guardrail_audits=guardrail_audits,
        )
        source_ids = []
        for artifact in artifacts:
            for source_id in artifact.source_ids:
                if source_id not in source_ids:
                    source_ids.append(source_id)
        index = ArtifactRecord(
            run_id=message.run_id,
            artifact_type=ArtifactType.ARTIFACT_INDEX,
            title="Artifact index",
            uri=(
                f"artifact://runs/{message.run_id}/artifact-index/"
                f"{message.message_id}"
            ),
            content=index_content,
            provenance={
                "workflow": "artifact_librarian_index_worker_v1",
                "agent_id": "artifact-librarian",
                "message_id": str(message.message_id),
                "source_artifact_ids": [
                    str(artifact.artifact_id) for artifact in artifacts
                ],
                "generation_mode": "deterministic_artifact_index",
            },
            source_ids=source_ids,
            revision_history=[
                {
                    "actor": "artifact-librarian",
                    "workflow": "artifact_librarian_index_worker_v1",
                    "message_id": str(message.message_id),
                    "note": (
                        "Indexed artifact provenance, source dependencies, "
                        "claim links, revision edges, and retrieval facets."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(index)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=index.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_index_recorded",
                actor="artifact-librarian",
                payload={
                    "message_id": str(message.message_id),
                    "artifact_index_id": str(index.artifact_id),
                    "indexed_artifact_count": index_content["artifact_count"],
                    "dependency_edge_count": len(index_content["dependency_edges"]),
                    "provenance_gap_count": len(index_content["provenance_gaps"]),
                    "source_linked_artifact_count": index_content[
                        "source_linked_artifact_count"
                    ],
                    "publishable_artifact_count": index_content[
                        "publishing_handoff"
                    ]["publishable_artifact_count"],
                    "publishing_handoff_status": index_content[
                        "publishing_handoff"
                    ]["status"],
                    "claim_revision_ledger_artifact_id": (
                        str(claim_revision_ledger.artifact_id)
                        if claim_revision_ledger
                        else None
                    ),
                    "claim_revision_status": index_content[
                        "publishing_handoff"
                    ].get("claim_revision", {}).get("status"),
                },
            )
        )
        return {
            "generation_mode": "artifact_librarian_worker",
            "summary": (
                "artifact-librarian indexed "
                f"{index_content['artifact_count']} artifact(s), "
                f"{len(index_content['dependency_edges'])} dependency edge(s), "
                f"and {len(index_content['provenance_gaps'])} provenance gap(s)."
            ),
            "artifact_index_id": str(index.artifact_id),
            "indexed_artifact_count": index_content["artifact_count"],
            "dependency_edge_count": len(index_content["dependency_edges"]),
            "provenance_gap_count": len(index_content["provenance_gaps"]),
            "source_linked_artifact_count": index_content[
                "source_linked_artifact_count"
            ],
            "publishing_handoff_status": index_content["publishing_handoff"][
                "status"
            ],
            "publishable_artifact_count": index_content["publishing_handoff"][
                "publishable_artifact_count"
            ],
            "claim_revision_ledger_artifact_id": (
                str(claim_revision_ledger.artifact_id)
                if claim_revision_ledger
                else None
            ),
            "claim_revision_status": index_content["publishing_handoff"]
            .get("claim_revision", {})
            .get("status"),
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _record_claim_revision_ledger_if_needed(
        self,
        *,
        message: AgentMessage,
        artifacts: list[ArtifactRecord],
        claims: list[ClaimRecord],
        messages: list[AgentMessage],
    ) -> ArtifactRecord | None:
        content = _claim_revision_closure_ledger_content(
            artifacts=artifacts,
            claims=claims,
            messages=messages,
        )
        if content["status"] == "no_claim_revision_plan":
            return None
        source_ids = []
        for source in content.get("accepted_source_alternatives", []):
            try:
                source_id = UUID(str(source.get("source_id")))
            except (TypeError, ValueError):
                continue
            if source_id not in source_ids:
                source_ids.append(source_id)
        ledger = ArtifactRecord(
            run_id=message.run_id,
            artifact_type=ArtifactType.CLAIM_REVISION_LEDGER,
            title="Claim revision closure ledger",
            uri=(
                f"artifact://runs/{message.run_id}/claim-revision-ledger/"
                f"{message.message_id}"
            ),
            content=content,
            provenance={
                "workflow": "claim_revision_closure_ledger_v1",
                "agent_id": "artifact-librarian",
                "message_id": str(message.message_id),
                "claim_revision_plan_artifact_id": content.get(
                    "claim_revision_plan_artifact_id"
                ),
                "generation_mode": "deterministic_claim_revision_closure",
            },
            source_ids=source_ids,
            revision_history=[
                {
                    "actor": "artifact-librarian",
                    "workflow": "claim_revision_closure_ledger_v1",
                    "message_id": str(message.message_id),
                    "note": (
                        "Recorded closure status for held claims, claim-revision "
                        "follow-up A2A tasks, revised artifacts, and editor review."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(ledger)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=ledger.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="claim_revision_ledger_recorded",
                actor="artifact-librarian",
                payload={
                    "message_id": str(message.message_id),
                    "ledger_artifact_id": str(ledger.artifact_id),
                    "claim_revision_plan_artifact_id": content.get(
                        "claim_revision_plan_artifact_id"
                    ),
                    "status": content["status"],
                    "held_claim_count": content["held_claim_count"],
                    "open_held_claim_count": content["open_held_claim_count"],
                    "pending_followup_count": content["pending_followup_count"],
                    "completed_followup_count": content["completed_followup_count"],
                    "blocked_followup_count": content["blocked_followup_count"],
                    "revised_artifact_count": content["revised_artifact_count"],
                },
            )
        )
        return ledger

    async def _execute_distribution_packaging(
        self,
        *,
        message: AgentMessage,
        agent_id: str,
        context_summary: dict[str, Any],
        request: AgentWorkerRunRequest,
    ) -> dict[str, Any]:
        artifacts = await self._store.list_artifacts(message.run_id)
        source_artifacts = _leaf_source_content_artifacts(artifacts)
        if not source_artifacts:
            raise NoArtifactsForDistributionPackageError(
                "No content artifacts are available for distribution packaging."
            )

        current_package = _current_distribution_package(
            artifacts=artifacts,
            source_artifacts=source_artifacts,
        )
        if current_package is not None:
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="distribution_package_reused",
                    actor=agent_id,
                    payload={
                        "message_id": str(message.message_id),
                        "distribution_artifact_id": str(current_package.artifact_id),
                        "source_artifact_ids": [
                            str(artifact.artifact_id)
                            for artifact in source_artifacts
                        ],
                        "platforms": current_package.provenance.get("platforms", []),
                    },
                )
            )
            return {
                "generation_mode": "distribution_package_worker",
                "summary": (
                    f"{agent_id} reused the current distribution package "
                    f"{current_package.artifact_id}."
                ),
                "distribution_artifact_id": str(current_package.artifact_id),
                "source_artifact_ids": [
                    str(artifact.artifact_id) for artifact in source_artifacts
                ],
                "platforms": current_package.provenance.get("platforms", []),
                "reused_existing": True,
                "context_summary": context_summary,
                "skill_ids": context_summary.get("skill_ids", []),
            }

        growth_strategy = await self._execute_gemma_or_deterministic(
            message=message,
            agent_id=agent_id,
            context_summary=context_summary,
            request=request,
        )
        package = await DistributionPackageWorkflow(self._store).run(
            message.run_id,
            DistributionPackageRequest(
                target_artifact_ids=[
                    artifact.artifact_id for artifact in source_artifacts
                ],
                platforms=_platforms_from_payload(message.payload),
                audience=_payload_text(
                    message.payload,
                    "audience",
                    "AI-curious builders, creators, and operators",
                ),
                campaign_goal=_payload_text(
                    message.payload,
                    "campaign_goal",
                    "educate with source-backed, ELI5 content",
                ),
                include_outreach=bool(message.payload.get("include_outreach", True)),
                created_by_agent_id=agent_id,
            ),
        )
        return {
            "generation_mode": "distribution_package_worker",
            "summary": (
                f"{agent_id} built distribution package "
                f"{package.distribution_artifact_id} for "
                f"{len(package.platforms)} platform(s)."
            ),
            "distribution_artifact_id": str(package.distribution_artifact_id),
            "source_artifact_ids": [
                str(artifact_id) for artifact_id in package.source_artifact_ids
            ],
            "platforms": package.platforms,
            "reused_existing": False,
            "growth_strategy": growth_strategy,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_influencer_strategy(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
        request: AgentWorkerRunRequest,
    ) -> dict[str, Any]:
        strategy_context = await self._execute_gemma_or_deterministic(
            message=message,
            agent_id="influencer-strategy-agent",
            context_summary=context_summary,
            request=request,
        )
        package, source_artifacts = await self._ensure_growth_distribution_package(
            message=message,
            initiated_by_agent_id="influencer-strategy-agent",
        )
        artifact = _build_influencer_strategy_artifact(
            message=message,
            package=package,
            source_artifacts=source_artifacts,
            strategy_context=strategy_context,
        )
        recorded_artifact = await self._record_artifact_if_absent(artifact)
        if recorded_artifact is not None:
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="artifact_recorded",
                    actor="artifact-librarian",
                    payload=recorded_artifact.model_dump(mode="json"),
                )
            )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type=(
                    "influencer_strategy_recorded"
                    if recorded_artifact is not None
                    else "influencer_strategy_reused"
                ),
                actor="influencer-strategy-agent",
                payload={
                    "message_id": str(message.message_id),
                    "strategy_artifact_id": str(artifact.artifact_id),
                    "distribution_artifact_id": str(package.artifact_id),
                    "source_artifact_ids": [
                        str(source_artifact.artifact_id)
                        for source_artifact in source_artifacts
                    ],
                    "reused_existing": recorded_artifact is None,
                },
            )
        )
        return {
            "generation_mode": "influencer_strategy_worker",
            "summary": (
                "influencer-strategy-agent recorded audience, keyword, hashtag, "
                f"and creator packaging strategy for {package.artifact_id}."
            ),
            "strategy_artifact_id": str(artifact.artifact_id),
            "distribution_artifact_id": str(package.artifact_id),
            "source_artifact_ids": [
                str(source_artifact.artifact_id) for source_artifact in source_artifacts
            ],
            "reused_existing": recorded_artifact is None,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_outreach_strategy(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
        request: AgentWorkerRunRequest,
    ) -> dict[str, Any]:
        strategy_context = await self._execute_gemma_or_deterministic(
            message=message,
            agent_id="outreach-agent",
            context_summary=context_summary,
            request=request,
        )
        package, source_artifacts = await self._ensure_growth_distribution_package(
            message=message,
            initiated_by_agent_id="outreach-agent",
        )
        artifact = _build_outreach_strategy_artifact(
            message=message,
            package=package,
            source_artifacts=source_artifacts,
            strategy_context=strategy_context,
        )
        recorded_artifact = await self._record_artifact_if_absent(artifact)
        if recorded_artifact is not None:
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="artifact_recorded",
                    actor="artifact-librarian",
                    payload=recorded_artifact.model_dump(mode="json"),
                )
            )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type=(
                    "outreach_strategy_recorded"
                    if recorded_artifact is not None
                    else "outreach_strategy_reused"
                ),
                actor="outreach-agent",
                payload={
                    "message_id": str(message.message_id),
                    "strategy_artifact_id": str(artifact.artifact_id),
                    "distribution_artifact_id": str(package.artifact_id),
                    "source_artifact_ids": [
                        str(source_artifact.artifact_id)
                        for source_artifact in source_artifacts
                    ],
                    "reused_existing": recorded_artifact is None,
                },
            )
        )
        return {
            "generation_mode": "outreach_strategy_worker",
            "summary": (
                "outreach-agent recorded community, partnership, and engagement "
                f"strategy for {package.artifact_id}."
            ),
            "strategy_artifact_id": str(artifact.artifact_id),
            "distribution_artifact_id": str(package.artifact_id),
            "source_artifact_ids": [
                str(source_artifact.artifact_id) for source_artifact in source_artifacts
            ],
            "reused_existing": recorded_artifact is None,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _ensure_growth_distribution_package(
        self,
        *,
        message: AgentMessage,
        initiated_by_agent_id: str,
    ) -> tuple[ArtifactRecord, list[ArtifactRecord]]:
        artifacts = await self._store.list_artifacts(message.run_id)
        source_artifacts = _leaf_source_content_artifacts(artifacts)
        if not source_artifacts:
            raise NoArtifactsForDistributionPackageError(
                "No content artifacts are available for growth strategy."
            )
        current_package = _current_distribution_package(
            artifacts=artifacts,
            source_artifacts=source_artifacts,
        )
        if current_package is not None:
            return current_package, source_artifacts

        package_result = await DistributionPackageWorkflow(self._store).run(
            message.run_id,
            DistributionPackageRequest(
                target_artifact_ids=[
                    artifact.artifact_id for artifact in source_artifacts
                ],
                platforms=_platforms_from_payload(message.payload),
                audience=_payload_text(
                    message.payload,
                    "audience",
                    "AI-curious builders, creators, and operators",
                ),
                campaign_goal=_payload_text(
                    message.payload,
                    "campaign_goal",
                    "educate with source-backed, ELI5 content",
                ),
                include_outreach=True,
                created_by_agent_id="platform-optimization-agent",
                initiated_by_agent_id=initiated_by_agent_id,
            ),
        )
        refreshed_artifacts = await self._store.list_artifacts(message.run_id)
        for artifact in reversed(refreshed_artifacts):
            if artifact.artifact_id == package_result.distribution_artifact_id:
                return artifact, source_artifacts
        raise NoArtifactsForDistributionPackageError(
            "Distribution package could not be loaded after creation."
        )

    async def _execute_guardrail_review(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        await require_tool_allowed(
            self._store,
            run_id=message.run_id,
            agent_id="guardrails-agent",
            tool_name="source_ledger",
            reason="guardrail_audit_reads_source_and_claim_ledger",
            message_id=message.message_id,
        )
        from all_about_llms.orchestration.guardrail_audit import (
            GuardrailAuditWorkflow,
            NoArtifactsToAuditError,
        )

        try:
            audit_result = await GuardrailAuditWorkflow(self._store).run(
                message.run_id,
                GuardrailAuditRequest(open_feedback_gate=message.requires_human_feedback),
            )
        except NoArtifactsToAuditError:
            return {
                "generation_mode": "guardrail_worker",
                "summary": "guardrails-agent found no artifacts to audit.",
                "status": "blocked",
                "context_summary": context_summary,
                "skill_ids": context_summary.get("skill_ids", []),
            }
        return {
            "generation_mode": "guardrail_worker",
            "summary": audit_result.summary,
            "status": audit_result.status.value,
            "audit_ids": [str(audit.audit_id) for audit in audit_result.audits],
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_visual_direction_brief(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        artifacts = await self._store.list_artifacts(message.run_id)
        source_artifacts = _targeted_source_artifacts(
            artifacts=artifacts,
            target_artifact_ids=message.payload.get("target_artifact_ids", []) or [],
            include_explicit_target_artifact_types=TARGETABLE_MULTIMODAL_CONTEXT_TYPES,
        )
        if not source_artifacts:
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="visual_direction_brief_blocked",
                    actor="visual-director",
                    payload={
                        "message_id": str(message.message_id),
                        "reason": "no_source_content_artifacts",
                    },
                )
            )
            return {
                "generation_mode": "visual_direction_worker",
                "summary": (
                    "visual-director found no source-backed content artifacts "
                    "for visual direction planning."
                ),
                "status": "blocked",
                "visual_brief_artifact_id": None,
                "source_artifact_ids": [],
                "context_summary": context_summary,
                "skill_ids": context_summary.get("skill_ids", []),
            }

        run = await self._store.get_run(message.run_id)
        feedback_items = await self._store.list_feedback(message.run_id)
        topic = _topic_from_payload(message.payload)
        if topic == "the requested topic":
            topic = _topic_from_artifacts(source_artifacts, run.goal if run else topic)
        source_ids = _unique_source_ids_from_artifacts(source_artifacts)
        claim_ids = _unique_claim_ids_from_artifacts(source_artifacts)
        visual_brief = ArtifactRecord(
            run_id=message.run_id,
            artifact_type=ArtifactType.VISUAL_BRIEF,
            title=f"Visual brief: {topic}",
            uri=(
                f"artifact://runs/{message.run_id}/visual-briefs/"
                f"{message.message_id}"
            ),
            content=_visual_direction_brief_content(
                topic=topic,
                source_artifacts=source_artifacts,
                source_ids=source_ids,
                claim_ids=claim_ids,
                feedback_items=feedback_items,
                platform=_payload_text(
                    message.payload,
                    "platform",
                    "instagram_reel",
                ),
            ),
            provenance={
                "workflow": "visual_direction_worker_v1",
                "agent_id": "visual-director",
                "message_id": str(message.message_id),
                "source_artifact_ids": [
                    str(artifact.artifact_id) for artifact in source_artifacts
                ],
                "source_ids": [str(source_id) for source_id in source_ids],
                "claim_ids": [str(claim_id) for claim_id in claim_ids],
                "generation_mode": "deterministic_visual_brief",
            },
            source_ids=source_ids,
            revision_history=[
                {
                    "actor": "visual-director",
                    "workflow": "visual_direction_worker_v1",
                    "message_id": str(message.message_id),
                    "note": (
                        "Created a source-linked visual system brief for image, "
                        "carousel, thumbnail, diagram, and reel storyboard work."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(visual_brief)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=visual_brief.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="visual_direction_brief_created",
                actor="visual-director",
                payload={
                    "message_id": str(message.message_id),
                    "visual_brief_artifact_id": str(visual_brief.artifact_id),
                    "source_artifact_ids": [
                        str(artifact.artifact_id) for artifact in source_artifacts
                    ],
                    "source_count": len(source_ids),
                    "claim_count": len(claim_ids),
                    "frame_count": len(visual_brief.content["frame_plan"]),
                },
            )
        )
        return {
            "generation_mode": "visual_direction_worker",
            "summary": (
                "visual-director created a source-linked visual brief "
                f"from {len(source_artifacts)} content artifact(s)."
            ),
            "visual_brief_artifact_id": str(visual_brief.artifact_id),
            "source_artifact_ids": [
                str(artifact.artifact_id) for artifact in source_artifacts
            ],
            "source_count": len(source_ids),
            "claim_count": len(claim_ids),
            "frame_count": len(visual_brief.content["frame_plan"]),
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_multimodal_intake_review(
        self,
        *,
        message: AgentMessage,
        agent_id: str,
        context_summary: dict[str, Any],
        request: AgentWorkerRunRequest,
    ) -> dict[str, Any]:
        assets = list(message.payload.get("assets", []) or [])
        if not assets:
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="multimodal_intake_review_blocked",
                    actor=agent_id,
                    payload={
                        "message_id": str(message.message_id),
                        "reason": "no_multimodal_assets",
                    },
                )
            )
            return {
                "generation_mode": "multimodal_intake_review_worker",
                "summary": f"{agent_id} found no multimodal assets to review.",
                "status": "blocked",
                "multimodal_review_artifact_id": None,
                "context_summary": context_summary,
                "skill_ids": context_summary.get("skill_ids", []),
            }

        agent = get_agent_card(agent_id)
        focus = _multimodal_review_focus(agent_id)
        modality_counts = _value_counts(
            str(asset.get("modality") or "unknown") for asset in assets
        )
        gemma_response = None
        gemma_generation_mode = "deterministic_multimodal_review"
        if (
            request.use_gemma
            and self._services.gemma_provider
            and agent is not None
            and _agent_allows_gemma(agent.allowed_models)
        ):
            model_id = _gemma_model_id(agent.allowed_models)
            await require_model_allowed(
                self._store,
                run_id=message.run_id,
                agent_id=agent_id,
                model_id=model_id,
                reason="multimodal_intake_review_gemma",
                message_id=message.message_id,
                metadata={
                    "task_type": message.task_type,
                    "asset_count": len(assets),
                    "modalities": sorted(modality_counts),
                    "review_focus": focus,
                },
            )
            try:
                gemma_response = await self._services.gemma_provider.complete(
                    GemmaRequest(
                        model_id=model_id,
                        agent_id=agent_id,
                        system_context=(
                            f"You are {agent.name}. Review multimodal intake "
                            "references for your specialist focus. Use asset "
                            "URIs, descriptions, modality flags, and provider "
                            "boundaries as the available input contract. Do not "
                            "claim binary file analysis unless the endpoint "
                            "received the file directly."
                        ),
                        user_input=json.dumps(
                            {
                                "task_type": message.task_type,
                                "review_focus": focus,
                                "run_goal": message.payload.get("run_goal"),
                                "notes": message.payload.get("notes"),
                                "assets": assets,
                                "all_asset_ids": message.payload.get(
                                    "all_asset_ids", []
                                ),
                                "modality_counts": modality_counts,
                                "provider_boundaries": message.payload.get(
                                    "provider_boundaries", {}
                                ),
                                "context_summary": context_summary,
                            },
                            indent=2,
                        ),
                        attachments=[
                            {
                                "asset_id": asset.get("asset_id"),
                                "asset_uri": asset.get("asset_uri"),
                                "modality": asset.get("modality"),
                                "description": asset.get("description"),
                                "analysis_boundary": asset.get(
                                    "analysis_boundary"
                                ),
                                "generation_boundary": asset.get(
                                    "generation_boundary"
                                ),
                                "metadata": asset.get("metadata", {}),
                            }
                            for asset in assets
                        ],
                        metadata={
                            "workflow": "multimodal_intake_review_worker_v1",
                            "source_workflow": message.payload.get("workflow"),
                            "asset_count": len(assets),
                            "modalities": sorted(modality_counts),
                            "review_focus": focus,
                            "input_contract": "asset_reference_payload",
                        },
                    )
                )
                gemma_generation_mode = "gemma_multimodal_review"
                await self._store.append_event(
                    RunEvent(
                        run_id=message.run_id,
                        event_type="gemma_worker_completed",
                        actor=agent_id,
                        payload={
                            "message_id": str(message.message_id),
                            "model_id": gemma_response.model_id,
                            "usage": gemma_response.usage,
                            "workflow": "multimodal_intake_review_worker_v1",
                            "asset_count": len(assets),
                            "modalities": sorted(modality_counts),
                        },
                    )
                )
                await self._store.append_event(
                    RunEvent(
                        run_id=message.run_id,
                        event_type="gemma_multimodal_review_completed",
                        actor=agent_id,
                        payload={
                            "message_id": str(message.message_id),
                            "model_id": gemma_response.model_id,
                            "usage": gemma_response.usage,
                            "asset_count": len(assets),
                            "modality_counts": modality_counts,
                            "review_focus": focus,
                        },
                    )
                )
            except ProviderConfigurationError as exc:
                await self._store.append_event(
                    RunEvent(
                        run_id=message.run_id,
                        event_type="provider_fallback",
                        actor=agent_id,
                        payload={
                            "provider": "gemma",
                            "reason": str(exc),
                            "workflow": "multimodal_intake_review_worker_v1",
                            "message_id": str(message.message_id),
                            "asset_count": len(assets),
                            "modalities": sorted(modality_counts),
                        },
                    )
                )
                if request.fail_on_provider_error:
                    raise
        asset_reviews = [
            _multimodal_asset_review(
                asset=asset,
                agent_id=agent_id,
                focus=focus,
            )
            for asset in assets
        ]
        content = {
            "format": "multimodal_intake_review",
            "agent_id": agent_id,
            "task_message_id": str(message.message_id),
            "review_focus": focus,
            "asset_count": len(assets),
            "modality_counts": modality_counts,
            "assets": asset_reviews,
            "all_asset_ids": message.payload.get("all_asset_ids", []),
            "provider_boundaries": message.payload.get("provider_boundaries", {}),
            "run_goal": message.payload.get("run_goal"),
            "notes": message.payload.get("notes"),
            "requires_human_feedback": message.requires_human_feedback,
            "recommended_next_actions": _multimodal_review_next_actions(
                agent_id=agent_id,
                assets=assets,
            ),
            "generation_mode": gemma_generation_mode,
        }
        provenance = {
            "workflow": "multimodal_intake_review_worker_v1",
            "agent_id": agent_id,
            "message_id": str(message.message_id),
            "source_workflow": message.payload.get("workflow"),
            "asset_count": len(assets),
            "modalities": sorted(modality_counts),
            "generation_mode": gemma_generation_mode,
        }
        revision_note = (
            "Reviewed multimodal intake assets without invoking external "
            "generation or live provider calls."
        )
        if gemma_response is not None:
            content["gemma_review"] = gemma_response.content
            content["model_id"] = gemma_response.model_id
            content["usage"] = gemma_response.usage
            content["provider_input_contract"] = (
                "Gemma received asset references, modality metadata, and "
                "provider boundaries. Direct binary upload remains an adapter "
                "capability for endpoints that support it."
            )
            provenance["model_provider"] = "huggingface"
            provenance["model_id"] = gemma_response.model_id
            provenance["provider_usage"] = gemma_response.usage
            revision_note = (
                "Reviewed multimodal intake assets with a Gemma HF expert "
                "provider using asset references and provider-boundary metadata."
            )
        followup_plan = _multimodal_review_followup_specs(
            agent_id=agent_id,
            assets=assets,
        )
        content["followup_plan"] = followup_plan
        content["followup_creation_policy"] = {
            "create_followup_tasks": bool(
                message.payload.get("create_followup_tasks", True)
            ),
            "requires_human_feedback": message.requires_human_feedback,
            "idempotency_key": str(message.message_id),
        }
        artifact = ArtifactRecord(
            run_id=message.run_id,
            artifact_type=ArtifactType.MULTIMODAL_REVIEW,
            title=f"Multimodal review: {agent.name if agent else agent_id}",
            uri=(
                f"artifact://runs/{message.run_id}/multimodal-reviews/"
                f"{message.message_id}/{agent_id}"
            ),
            content=content,
            provenance=provenance,
            revision_history=[
                {
                    "actor": agent_id,
                    "workflow": "multimodal_intake_review_worker_v1",
                    "message_id": str(message.message_id),
                    "note": revision_note,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(artifact)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=artifact.model_dump(mode="json"),
            )
        )
        created_followups, skipped_followups = (
            await self._materialize_multimodal_review_followups(
                message=message,
                agent_id=agent_id,
                artifact=artifact,
                assets=assets,
                focus=focus,
                modality_counts=modality_counts,
                followup_plan=followup_plan,
                recommended_next_actions=content["recommended_next_actions"],
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="multimodal_intake_review_recorded",
                actor=agent_id,
                payload={
                    "message_id": str(message.message_id),
                    "multimodal_review_artifact_id": str(artifact.artifact_id),
                    "asset_count": len(assets),
                    "modality_counts": modality_counts,
                    "review_focus": focus,
                    "created_followup_message_ids": [
                        str(followup.message_id) for followup in created_followups
                    ],
                    "skipped_duplicate_followups": skipped_followups,
                },
            )
        )
        return {
            "generation_mode": "multimodal_intake_review_worker",
            "summary": (
                f"{agent_id} reviewed {len(assets)} multimodal intake asset(s) "
                f"for {focus}."
            ),
            "multimodal_review_artifact_id": str(artifact.artifact_id),
            "asset_count": len(assets),
            "modality_counts": modality_counts,
            "review_focus": focus,
            "provider_generation_mode": gemma_generation_mode,
            "model_id": gemma_response.model_id if gemma_response else None,
            "created_followup_message_ids": [
                str(followup.message_id) for followup in created_followups
            ],
            "skipped_duplicate_followups": skipped_followups,
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _materialize_multimodal_review_followups(
        self,
        *,
        message: AgentMessage,
        agent_id: str,
        artifact: ArtifactRecord,
        assets: list[dict[str, Any]],
        focus: str,
        modality_counts: dict[str, int],
        followup_plan: list[dict[str, str]],
        recommended_next_actions: list[str],
    ) -> tuple[list[AgentMessage], int]:
        if not followup_plan:
            return [], 0
        if message.requires_human_feedback:
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="multimodal_review_followups_gated",
                    actor=agent_id,
                    payload={
                        "message_id": str(message.message_id),
                        "multimodal_review_artifact_id": str(artifact.artifact_id),
                        "reason": "human_feedback_required",
                        "planned_followup_count": len(followup_plan),
                    },
                )
            )
            return [], 0
        if not bool(message.payload.get("create_followup_tasks", True)):
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="multimodal_review_followups_gated",
                    actor=agent_id,
                    payload={
                        "message_id": str(message.message_id),
                        "multimodal_review_artifact_id": str(artifact.artifact_id),
                        "reason": "create_followup_tasks_false",
                        "planned_followup_count": len(followup_plan),
                    },
                )
            )
            return [], 0

        existing_messages = await self._store.list_agent_messages(message.run_id)
        signatures = {
            str(existing.payload.get("multimodal_review_signature"))
            for existing in existing_messages
            if existing.payload.get("multimodal_review_signature")
            and existing.status in DEDUPED_MULTIMODAL_FOLLOWUP_STATUSES
        }
        created: list[AgentMessage] = []
        skipped_duplicates = 0
        for spec in followup_plan:
            signature = _multimodal_review_followup_signature(
                source_message_id=message.message_id,
                artifact_id=artifact.artifact_id,
                recipient_agent_id=spec["recipient_agent_id"],
                task_type=spec["task_type"],
            )
            if signature in signatures:
                skipped_duplicates += 1
                continue
            followup = AgentMessage(
                run_id=message.run_id,
                sender_agent_id=agent_id,
                recipient_agent_id=spec["recipient_agent_id"],
                task_type=spec["task_type"],
                payload={
                    "workflow": "multimodal_review_followup_v1",
                    "source_workflow": "multimodal_intake_review_worker_v1",
                    "source_review_agent_id": agent_id,
                    "source_message_id": str(message.message_id),
                    "source_multimodal_review_artifact_id": str(artifact.artifact_id),
                    "multimodal_review_signature": signature,
                    "review_focus": focus,
                    "asset_count": len(assets),
                    "asset_ids": [
                        str(asset.get("asset_id"))
                        for asset in assets
                        if asset.get("asset_id")
                    ],
                    "assets": assets,
                    "modality_counts": modality_counts,
                    "provider_boundaries": message.payload.get(
                        "provider_boundaries", {}
                    ),
                    "recommended_next_actions": recommended_next_actions,
                    "handoff_reason": spec["reason"],
                    "target_artifact_ids": [str(artifact.artifact_id)],
                    "target_agent_id": (
                        agent_id
                        if spec["recipient_agent_id"] == "context-engineering-agent"
                        else None
                    ),
                    "topic": message.payload.get("run_goal")
                    or _topic_from_payload(message.payload),
                    "requires_asset_reference_only": True,
                    "create_followup_tasks": False,
                },
            )
            await self._store.record_agent_message(followup)
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="agent_message_accepted",
                    actor=agent_id,
                    payload=public_a2a_message_event_payload(followup),
                )
            )
            created.append(followup)
            signatures.add(signature)

        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="multimodal_review_followups_materialized",
                actor=agent_id,
                payload={
                    "message_id": str(message.message_id),
                    "multimodal_review_artifact_id": str(artifact.artifact_id),
                    "planned_followup_count": len(followup_plan),
                    "created_followup_message_ids": [
                        str(followup.message_id) for followup in created
                    ],
                    "created_followup_count": len(created),
                    "skipped_duplicate_followups": skipped_duplicates,
                    "recipient_agent_ids": [
                        followup.recipient_agent_id for followup in created
                    ],
                },
            )
        )
        return created, skipped_duplicates

    async def _execute_image_generation_prompt_pack(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        await require_tool_allowed(
            self._store,
            run_id=message.run_id,
            agent_id="image-generation-agent",
            tool_name="imagegen",
            reason="image_generation_worker_prepares_raster_prompt_pack",
            message_id=message.message_id,
            metadata={"task_type": message.task_type},
        )
        artifacts = await self._store.list_artifacts(message.run_id)
        source_artifacts = _targeted_source_artifacts(
            artifacts=artifacts,
            target_artifact_ids=message.payload.get("target_artifact_ids", []) or [],
            include_explicit_target_artifact_types=TARGETABLE_MULTIMODAL_CONTEXT_TYPES,
        )
        if not source_artifacts:
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="image_generation_prompt_pack_blocked",
                    actor="image-generation-agent",
                    payload={
                        "message_id": str(message.message_id),
                        "reason": "no_source_content_artifacts",
                    },
                )
            )
            return {
                "generation_mode": "image_generation_worker",
                "summary": (
                    "image-generation-agent found no source-backed content "
                    "artifacts for imagegen prompt planning."
                ),
                "status": "blocked",
                "image_artifact_id": None,
                "source_artifact_ids": [],
                "context_summary": context_summary,
                "skill_ids": context_summary.get("skill_ids", []),
            }

        feedback_items = await self._store.list_feedback(message.run_id)
        topic = _topic_from_payload(message.payload)
        if topic == "the requested topic":
            run = await self._store.get_run(message.run_id)
            topic = _topic_from_artifacts(source_artifacts, run.goal if run else topic)
        source_ids = _unique_source_ids_from_artifacts(source_artifacts)
        claim_ids = _unique_claim_ids_from_artifacts(source_artifacts)
        prompt_pack = ArtifactRecord(
            run_id=message.run_id,
            artifact_type=ArtifactType.IMAGE,
            title=f"Imagegen prompt pack: {topic}",
            uri=(
                f"artifact://runs/{message.run_id}/imagegen-prompt-packs/"
                f"{message.message_id}"
            ),
            content=_imagegen_prompt_pack_content(
                topic=topic,
                source_artifacts=source_artifacts,
                source_ids=source_ids,
                claim_ids=claim_ids,
                feedback_items=feedback_items,
                image_style=_payload_text(
                    message.payload,
                    "image_style",
                    "clean educational social visual",
                ),
                platform=_payload_text(
                    message.payload,
                    "platform",
                    "instagram_reel",
                ),
            ),
            provenance={
                "workflow": "image_generation_worker_v1",
                "agent_id": "image-generation-agent",
                "message_id": str(message.message_id),
                "source_artifact_ids": [
                    str(artifact.artifact_id) for artifact in source_artifacts
                ],
                "source_ids": [str(source_id) for source_id in source_ids],
                "claim_ids": [str(claim_id) for claim_id in claim_ids],
                "tool_boundary": "imagegen",
                "generation_mode": "deterministic_imagegen_prompt_pack",
            },
            source_ids=source_ids,
            revision_history=[
                {
                    "actor": "image-generation-agent",
                    "workflow": "image_generation_worker_v1",
                    "message_id": str(message.message_id),
                    "note": (
                        "Created source-linked imagegen prompt pack without "
                        "invoking raster generation."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(prompt_pack)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=prompt_pack.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="image_generation_prompt_pack_created",
                actor="image-generation-agent",
                payload={
                    "message_id": str(message.message_id),
                    "image_artifact_id": str(prompt_pack.artifact_id),
                    "source_artifact_ids": [
                        str(artifact.artifact_id) for artifact in source_artifacts
                    ],
                    "source_count": len(source_ids),
                    "claim_count": len(claim_ids),
                    "tool_boundary": "imagegen",
                },
            )
        )
        return {
            "generation_mode": "image_generation_worker",
            "summary": (
                "image-generation-agent created a source-linked imagegen prompt "
                f"pack from {len(source_artifacts)} content artifact(s)."
            ),
            "image_artifact_id": str(prompt_pack.artifact_id),
            "source_artifact_ids": [
                str(artifact.artifact_id) for artifact in source_artifacts
            ],
            "source_count": len(source_ids),
            "claim_count": len(claim_ids),
            "tool_boundary": "imagegen",
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_audio_production_brief(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        await require_tool_allowed(
            self._store,
            run_id=message.run_id,
            agent_id="audio-producer",
            tool_name="realtime_audio_provider",
            reason="audio_worker_plans_realtime_voice_boundary",
            message_id=message.message_id,
            metadata={"task_type": message.task_type},
        )
        await require_tool_allowed(
            self._store,
            run_id=message.run_id,
            agent_id="audio-producer",
            tool_name="tts_provider",
            reason="audio_worker_plans_tts_output_boundary",
            message_id=message.message_id,
            metadata={"task_type": message.task_type},
        )
        artifacts = await self._store.list_artifacts(message.run_id)
        source_artifacts = _targeted_source_artifacts(
            artifacts=artifacts,
            target_artifact_ids=message.payload.get("target_artifact_ids", []) or [],
            include_explicit_target_artifact_types=TARGETABLE_MULTIMODAL_CONTEXT_TYPES,
        )
        if not source_artifacts:
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="audio_production_brief_blocked",
                    actor="audio-producer",
                    payload={
                        "message_id": str(message.message_id),
                        "reason": "no_source_content_artifacts",
                    },
                )
            )
            return {
                "generation_mode": "audio_production_worker",
                "summary": (
                    "audio-producer found no source-backed content artifacts "
                    "for realtime audio planning."
                ),
                "status": "blocked",
                "audio_artifact_id": None,
                "source_artifact_ids": [],
                "context_summary": context_summary,
                "skill_ids": context_summary.get("skill_ids", []),
            }

        run = await self._store.get_run(message.run_id)
        realtime_sessions = await self._store.list_realtime_sessions(message.run_id)
        feedback_items = await self._store.list_feedback(message.run_id)
        topic = _topic_from_payload(message.payload)
        if topic == "the requested topic":
            topic = _topic_from_artifacts(source_artifacts, run.goal if run else topic)
        source_ids = _unique_source_ids_from_artifacts(source_artifacts)
        claim_ids = _unique_claim_ids_from_artifacts(source_artifacts)
        audio_brief = ArtifactRecord(
            run_id=message.run_id,
            artifact_type=ArtifactType.AUDIO,
            title=f"Realtime audio brief: {topic}",
            uri=(
                f"artifact://runs/{message.run_id}/audio-briefs/"
                f"{message.message_id}"
            ),
            content=_audio_production_brief_content(
                topic=topic,
                source_artifacts=source_artifacts,
                source_ids=source_ids,
                claim_ids=claim_ids,
                feedback_items=feedback_items,
                realtime_sessions=realtime_sessions,
                voice_style=_payload_text(
                    message.payload,
                    "voice_style",
                    "natural, warm, interruptible, ELI5",
                ),
                platform=_payload_text(
                    message.payload,
                    "platform",
                    "instagram_reel",
                ),
            ),
            provenance={
                "workflow": "audio_production_worker_v1",
                "agent_id": "audio-producer",
                "message_id": str(message.message_id),
                "source_artifact_ids": [
                    str(artifact.artifact_id) for artifact in source_artifacts
                ],
                "source_ids": [str(source_id) for source_id in source_ids],
                "claim_ids": [str(claim_id) for claim_id in claim_ids],
                "realtime_session_ids": [
                    str(session.realtime_session_id) for session in realtime_sessions
                ],
                "tool_boundaries": ["realtime_audio_provider", "tts_provider"],
                "generation_mode": "deterministic_audio_brief",
            },
            source_ids=source_ids,
            revision_history=[
                {
                    "actor": "audio-producer",
                    "workflow": "audio_production_worker_v1",
                    "message_id": str(message.message_id),
                    "note": (
                        "Created a source-linked realtime/TTS audio brief "
                        "without invoking external audio providers."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(audio_brief)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=audio_brief.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="audio_production_brief_created",
                actor="audio-producer",
                payload={
                    "message_id": str(message.message_id),
                    "audio_artifact_id": str(audio_brief.artifact_id),
                    "source_artifact_ids": [
                        str(artifact.artifact_id) for artifact in source_artifacts
                    ],
                    "source_count": len(source_ids),
                    "claim_count": len(claim_ids),
                    "realtime_session_count": len(realtime_sessions),
                    "tool_boundaries": ["realtime_audio_provider", "tts_provider"],
                },
            )
        )
        return {
            "generation_mode": "audio_production_worker",
            "summary": (
                "audio-producer created a source-linked realtime audio brief "
                f"from {len(source_artifacts)} content artifact(s)."
            ),
            "audio_artifact_id": str(audio_brief.artifact_id),
            "source_artifact_ids": [
                str(artifact.artifact_id) for artifact in source_artifacts
            ],
            "source_count": len(source_ids),
            "claim_count": len(claim_ids),
            "realtime_session_count": len(realtime_sessions),
            "tool_boundaries": ["realtime_audio_provider", "tts_provider"],
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_video_reel_storyboard(
        self,
        *,
        message: AgentMessage,
        context_summary: dict[str, Any],
    ) -> dict[str, Any]:
        artifacts = await self._store.list_artifacts(message.run_id)
        source_artifacts = _targeted_source_artifacts(
            artifacts=artifacts,
            target_artifact_ids=message.payload.get("target_artifact_ids", []) or [],
            include_explicit_target_artifact_types=TARGETABLE_MULTIMODAL_CONTEXT_TYPES,
        )
        if not source_artifacts:
            await self._store.append_event(
                RunEvent(
                    run_id=message.run_id,
                    event_type="video_reel_storyboard_blocked",
                    actor="video-reel-producer",
                    payload={
                        "message_id": str(message.message_id),
                        "reason": "no_source_content_artifacts",
                    },
                )
            )
            return {
                "generation_mode": "video_reel_worker",
                "summary": (
                    "video-reel-producer found no source-backed content "
                    "artifacts for reel storyboard planning."
                ),
                "status": "blocked",
                "video_artifact_id": None,
                "source_artifact_ids": [],
                "context_summary": context_summary,
                "skill_ids": context_summary.get("skill_ids", []),
            }

        run = await self._store.get_run(message.run_id)
        feedback_items = await self._store.list_feedback(message.run_id)
        media_dependencies = _media_dependency_artifacts(artifacts)
        topic = _topic_from_payload(message.payload)
        if topic == "the requested topic":
            topic = _topic_from_artifacts(source_artifacts, run.goal if run else topic)
        source_ids = _unique_source_ids_from_artifacts(source_artifacts)
        claim_ids = _unique_claim_ids_from_artifacts(source_artifacts)
        storyboard = ArtifactRecord(
            run_id=message.run_id,
            artifact_type=ArtifactType.VIDEO,
            title=f"Reel storyboard: {topic}",
            uri=(
                f"artifact://runs/{message.run_id}/reel-storyboards/"
                f"{message.message_id}"
            ),
            content=_video_reel_storyboard_content(
                topic=topic,
                source_artifacts=source_artifacts,
                media_dependencies=media_dependencies,
                source_ids=source_ids,
                claim_ids=claim_ids,
                feedback_items=feedback_items,
                platform=_payload_text(
                    message.payload,
                    "platform",
                    "instagram_reel",
                ),
                duration_seconds=int(message.payload.get("duration_seconds", 35)),
            ),
            provenance={
                "workflow": "video_reel_worker_v1",
                "agent_id": "video-reel-producer",
                "message_id": str(message.message_id),
                "source_artifact_ids": [
                    str(artifact.artifact_id) for artifact in source_artifacts
                ],
                "media_dependency_artifact_ids": [
                    str(artifact.artifact_id) for artifact in media_dependencies
                ],
                "source_ids": [str(source_id) for source_id in source_ids],
                "claim_ids": [str(claim_id) for claim_id in claim_ids],
                "generation_mode": "deterministic_reel_storyboard",
            },
            source_ids=source_ids,
            revision_history=[
                {
                    "actor": "video-reel-producer",
                    "workflow": "video_reel_worker_v1",
                    "message_id": str(message.message_id),
                    "note": (
                        "Created a source-linked reel storyboard with scene "
                        "timing, subtitle rules, media dependencies, and QA checks."
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        await self._store.record_artifact(storyboard)
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=storyboard.model_dump(mode="json"),
            )
        )
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="video_reel_storyboard_created",
                actor="video-reel-producer",
                payload={
                    "message_id": str(message.message_id),
                    "video_artifact_id": str(storyboard.artifact_id),
                    "source_artifact_ids": [
                        str(artifact.artifact_id) for artifact in source_artifacts
                    ],
                    "media_dependency_artifact_ids": [
                        str(artifact.artifact_id) for artifact in media_dependencies
                    ],
                    "source_count": len(source_ids),
                    "claim_count": len(claim_ids),
                    "scene_count": len(storyboard.content["scenes"]),
                },
            )
        )
        return {
            "generation_mode": "video_reel_worker",
            "summary": (
                "video-reel-producer created a source-linked reel storyboard "
                f"from {len(source_artifacts)} content artifact(s)."
            ),
            "video_artifact_id": str(storyboard.artifact_id),
            "source_artifact_ids": [
                str(artifact.artifact_id) for artifact in source_artifacts
            ],
            "media_dependency_artifact_ids": [
                str(artifact.artifact_id) for artifact in media_dependencies
            ],
            "source_count": len(source_ids),
            "claim_count": len(claim_ids),
            "scene_count": len(storyboard.content["scenes"]),
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _execute_media_planning(
        self,
        *,
        message: AgentMessage,
        agent_id: str,
        context_summary: dict[str, Any],
        request: AgentWorkerRunRequest,
    ) -> dict[str, Any]:
        media_plan = await self._execute_gemma_or_deterministic(
            message=message,
            agent_id=agent_id,
            context_summary=context_summary,
            request=request,
        )
        return {
            **media_plan,
            "generation_mode": "media_planning_worker",
            "summary": f"{agent_id} produced a media planning result.",
            "media_plan": {
                "visuals": "Use source-backed diagrams and imagegen only for raster assets.",
                "audio": "Keep voice natural, interruptible, and matched to realtime settings.",
                "video": "Create concise reel beats with subtitle-safe phrasing.",
            },
            "skill_ids": context_summary.get("skill_ids", []),
        }

    async def _set_status(
        self,
        *,
        message: AgentMessage,
        agent_id: str,
        status: AgentTaskStatus,
        result: dict[str, Any],
        notes: str | None = None,
        error: str | None = None,
    ) -> AgentMessage:
        current = await self._store.get_agent_message(message.message_id)
        if current is None:
            current = message
        from_status = current.status
        updated = await self._store.update_agent_message_status(
            message_id=message.message_id,
            status=status,
            agent_id=agent_id,
            result=result,
            notes=notes,
            error=error,
        )
        if updated is None:
            raise AgentWorkerError(f"Agent message not found: {message.message_id}")
        await self._store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="agent_message_status_updated",
                actor=agent_id,
                payload=public_a2a_status_event_payload(
                    message=message,
                    from_status=from_status,
                    to_status=status,
                    notes=notes,
                    has_result=bool(result),
                    has_error=error is not None,
                    skill_ids=[skill.id for skill in skill_cards_for_agent(agent_id)],
                ),
            )
        )
        return updated


def _gemma_model_id(allowed_models: list[str]) -> str:
    for model in allowed_models:
        if model.startswith("google/"):
            return model
        if model.startswith("gemma-4"):
            return f"google/{model}"
    return "google/gemma-4-31b-it"


def _agent_allows_gemma(allowed_models: list[str]) -> bool:
    return any(
        model.startswith("google/gemma-4") or model.startswith("gemma-4")
        for model in allowed_models
    )


def _skill_usage_payload(
    *,
    message: AgentMessage,
    agent_id: str,
    context_summary: dict[str, Any],
) -> dict[str, Any]:
    skill_cards = skill_cards_for_agent(agent_id)
    return {
        "workflow": "agent_worker_skill_usage_v1",
        "agent_id": agent_id,
        "message_id": str(message.message_id),
        "task_type": message.task_type,
        "skill_ids": [skill.id for skill in skill_cards],
        "skill_source_paths": {
            skill.id: skill.source_path for skill in skill_cards
        },
        "skill_outputs": {skill.id: skill.outputs for skill in skill_cards},
        "skill_guardrails": {skill.id: skill.guardrails for skill in skill_cards},
        "context_summary": {
            "run_id": context_summary.get("run_id"),
            "agent_id": context_summary.get("agent_id"),
            "message_id": context_summary.get("message_id"),
            "task_type": context_summary.get("task_type"),
            "conversation_turns": context_summary.get("conversation_turns", 0),
            "agent_messages": context_summary.get("agent_messages", 0),
            "sources": context_summary.get("sources", 0),
            "claims": context_summary.get("claims", 0),
            "artifacts": context_summary.get("artifacts", 0),
            "feedback_items": context_summary.get("feedback_items", 0),
            "memories": context_summary.get("memories", 0),
        },
    }


def _deterministic_task_result(
    *,
    agent_id: str,
    task_type: str,
    payload: dict[str, Any],
    context_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "generation_mode": "deterministic_worker",
        "summary": f"{agent_id} completed {task_type} with local deterministic logic.",
        "content": {
            "task_type": task_type,
            "payload_keys": sorted(payload.keys()),
            "context_summary": context_summary,
            "skill_ids": context_summary.get("skill_ids", []),
        },
        "context_summary": context_summary,
        "skill_ids": context_summary.get("skill_ids", []),
    }


def _multimodal_review_focus(agent_id: str) -> str:
    focus_by_agent = {
        "lead-ui-ux-designer": "product_ui_and_accessibility",
        "interactive-systems-designer": "interactive_planning_surface",
        "visual-director": "visual_storytelling_and_composition",
        "audio-producer": "voice_transcription_pacing_and_tts",
        "realtime-conversation-host": "turn_taking_interruptions_and_voice_context",
        "video-reel-producer": "reel_frames_subtitles_and_scene_sequence",
        "context-engineering-agent": "context_extraction_and_retrieval",
        "content-strategist": "content_angle_and_audience_fit",
        "intent-router": "specialist_handoff_selection",
    }
    return focus_by_agent.get(agent_id, "specialist_multimodal_review")


def _multimodal_asset_review(
    *,
    asset: dict[str, Any],
    agent_id: str,
    focus: str,
) -> dict[str, Any]:
    modality = str(asset.get("modality") or "unknown")
    asset_uri = str(asset.get("asset_uri") or "")
    description = asset.get("description")
    return {
        "asset_id": asset.get("asset_id"),
        "asset_uri": asset_uri,
        "modality": modality,
        "description": description,
        "source": asset.get("source"),
        "agent_focus": focus,
        "analysis_boundary": asset.get("analysis_boundary"),
        "generation_boundary": asset.get("generation_boundary"),
        "requires_transcription": bool(asset.get("requires_transcription")),
        "requires_visual_analysis": bool(asset.get("requires_visual_analysis")),
        "metadata": asset.get("metadata", {}),
        "review_decision": _multimodal_review_decision(agent_id, modality),
    }


def _multimodal_review_decision(agent_id: str, modality: str) -> str:
    if agent_id in {"lead-ui-ux-designer", "interactive-systems-designer"}:
        return (
            "Use the asset to inspect layout, interaction affordances, and "
            "planning/product boundary risks before proposing UI changes."
        )
    if agent_id == "visual-director":
        return (
            "Use the asset as visual reference for composition, hierarchy, "
            "story beats, and imagegen prompt requirements."
        )
    if agent_id in {"audio-producer", "realtime-conversation-host"}:
        return (
            "Use transcript, voice metadata, interruptions, and timing as "
            "inputs to voice style, TTS, and realtime turn-taking decisions."
        )
    if agent_id == "video-reel-producer":
        return (
            "Use the asset to identify frames, captions, pacing, and scene "
            "dependencies for reel planning."
        )
    if modality in {"document", "text"}:
        return "Extract durable context before writers or researchers depend on it."
    return "Keep the asset attached to the run until the right specialist consumes it."


def _multimodal_review_next_actions(
    *, agent_id: str, assets: list[dict[str, Any]]
) -> list[str]:
    modalities = {str(asset.get("modality") or "unknown") for asset in assets}
    actions_by_agent = {
        "lead-ui-ux-designer": [
            "Check screenshot hierarchy, spacing, contrast, and interaction state.",
            "Route product-app issues separately from planning HTML suggestions.",
        ],
        "interactive-systems-designer": [
            "Map planning-surface suggestions into structured feedback items.",
            "Preserve embedded JSON state for future planning iterations.",
        ],
        "visual-director": [
            "Convert useful visual references into source-aware visual direction.",
            "Only request imagegen after a prompt pack and provenance are ready.",
        ],
        "audio-producer": [
            "Request transcription when the audio asset lacks a text transcript.",
            "Turn voice notes into pacing, pronunciation, and TTS QA guidance.",
        ],
        "realtime-conversation-host": [
            "Keep interruption and turn-taking metadata attached to the next reply.",
            "Route semantic work without blocking the live conversation.",
        ],
        "video-reel-producer": [
            "Extract storyboard beats, subtitle needs, and frame dependencies.",
            "Keep reference video separate from generated final assets.",
        ],
        "context-engineering-agent": [
            "Summarize the asset into a context packet before long-running work.",
            "Add retrieval tags for future specialist handoffs.",
        ],
        "content-strategist": [
            "Use asset context to refine audience, angle, and content format.",
            "Keep factual claims source-backed before drafting.",
        ],
    }
    actions = list(actions_by_agent.get(agent_id, []))
    if "audio" in modalities or "voice" in modalities:
        actions.append("Do not treat audio as verified text until transcript context exists.")
    if modalities & {"image", "screenshot", "screen", "video", "reel"}:
        actions.append("Use Gemma 4 multimodal review for analysis when configured.")
    if not actions:
        actions.append("Route the asset to the next specialist with modality and boundary context.")
    return actions


def _multimodal_review_followup_specs(
    *, agent_id: str, assets: list[dict[str, Any]]
) -> list[dict[str, str]]:
    modalities = {str(asset.get("modality") or "unknown") for asset in assets}
    specs_by_agent = {
        "lead-ui-ux-designer": [
            (
                "context-engineering-agent",
                "build_context_from_multimodal_review",
                "Convert UI screenshot findings into durable context for later product and planning work.",
            ),
            (
                "product-manager",
                "coordinate_multimodal_ui_review",
                "Prioritize product-app versus planning-surface follow-up from the UI review.",
            ),
        ],
        "interactive-systems-designer": [
            (
                "interactive-note-taking-agent",
                "record_planning_surface_multimodal_review",
                "Capture planning-surface findings as durable interactive notes and feedback history.",
            ),
            (
                "product-manager",
                "coordinate_planning_surface_multimodal_review",
                "Keep planning-surface changes separate from product cockpit work.",
            ),
        ],
        "visual-director": [
            (
                "context-engineering-agent",
                "build_visual_context_from_multimodal_review",
                "Preserve visual references, composition notes, and generation boundaries for downstream media work.",
            ),
            (
                "image-generation-agent",
                "prepare_imagegen_prompt_pack_from_multimodal_review",
                "Turn reviewed visual references into imagegen-ready prompt-pack requirements before generation.",
            ),
        ],
        "audio-producer": [
            (
                "context-engineering-agent",
                "build_audio_context_from_multimodal_review",
                "Preserve transcript, timing, voice, and provider-boundary context before narration decisions.",
            ),
            (
                "realtime-conversation-host",
                "apply_voice_context_from_multimodal_review",
                "Carry voice-note context into the next realtime dialogue turn without making Gemma own speech transport.",
            ),
        ],
        "realtime-conversation-host": [
            (
                "intent-router",
                "route_voice_context_from_multimodal_review",
                "Route voice-turn context to semantic specialists while keeping the conversation responsive.",
            )
        ],
        "video-reel-producer": [
            (
                "context-engineering-agent",
                "build_reel_context_from_multimodal_review",
                "Extract durable scene, subtitle, pacing, and frame-reference context from reviewed reel/video assets.",
            ),
            (
                "script-doctor",
                "adapt_script_from_multimodal_reel_review",
                "Use reviewed reel pacing and scene evidence to improve hooks, spoken flow, and retention.",
            ),
        ],
        "context-engineering-agent": [
            (
                "content-strategist",
                "apply_multimodal_context_to_content_strategy",
                "Use extracted document or text context to refine audience, angle, and content format.",
            )
        ],
        "content-strategist": [
            (
                "web-research-agent",
                "research_multimodal_context_claims",
                "Ground any content claims implied by the user-provided asset before drafting.",
            )
        ],
        "intent-router": [
            (
                "context-engineering-agent",
                "build_context_from_routed_multimodal_text",
                "Classify text asset context before other specialists depend on it.",
            )
        ],
    }
    specs = list(specs_by_agent.get(agent_id, []))
    if (
        agent_id == "visual-director"
        and not modalities & {"image", "screenshot", "screen"}
    ):
        specs = [
            spec
            for spec in specs
            if spec[0] != "image-generation-agent"
        ]
    if agent_id == "audio-producer" and not modalities & {"audio", "voice"}:
        specs = [
            spec
            for spec in specs
            if spec[0] != "realtime-conversation-host"
        ]
    if agent_id == "video-reel-producer" and not modalities & {"video", "reel"}:
        specs = [
            spec
            for spec in specs
            if spec[0] != "script-doctor"
        ]
    if not specs:
        specs = [
            (
                "product-manager",
                "coordinate_multimodal_review_followup",
                "Decide the next specialist handoff from the multimodal review artifact.",
            )
        ]
    return [
        {
            "recipient_agent_id": recipient_agent_id,
            "task_type": task_type,
            "reason": reason,
        }
        for recipient_agent_id, task_type, reason in specs
        if recipient_agent_id != agent_id
    ]


def _multimodal_review_followup_signature(
    *,
    source_message_id: UUID,
    artifact_id: UUID,
    recipient_agent_id: str,
    task_type: str,
) -> str:
    return ":".join(
        [
            "multimodal-review-followup",
            str(source_message_id),
            str(artifact_id),
            recipient_agent_id,
            task_type,
        ]
    )


def _review_claim_support(
    claim: ClaimRecord,
    source_by_id: dict[UUID, SourceRecord],
    *,
    retrieval_evidence_by_source_id: dict[UUID, Any] | None = None,
    enforce_retrieval_evidence: bool = False,
) -> dict[str, Any]:
    retrieval_evidence_by_source_id = retrieval_evidence_by_source_id or {}
    missing_source_ids = [
        source_id for source_id in claim.source_ids if source_id not in source_by_id
    ]
    if not claim.source_ids or missing_source_ids:
        return {
            "status": ClaimSupportStatus.UNSUPPORTED,
            "missing_source_ids": missing_source_ids or claim.source_ids,
            "accepted_retrieval_source_ids": [],
            "missing_accepted_retrieval_evidence": False,
            "notes": (
                "Claim verification marked this unsupported because it has no "
                "valid SourceRecord dependencies."
            ),
        }

    accepted_retrieval_source_ids = [
        source_id
        for source_id in claim.source_ids
        if source_id in retrieval_evidence_by_source_id
    ]
    if enforce_retrieval_evidence and not accepted_retrieval_source_ids:
        return {
            "status": ClaimSupportStatus.UNSUPPORTED,
            "missing_source_ids": [],
            "accepted_retrieval_source_ids": [],
            "missing_accepted_retrieval_evidence": True,
            "notes": (
                "Claim verification marked this unsupported because none of its "
                "source dependencies are accepted retrieval evidence from the "
                "latest retrieval quality ledger."
            ),
        }

    source_entries = [
        evaluate_source_quality(source_by_id[source_id])
        for source_id in claim.source_ids
        if source_id in source_by_id
    ]
    weak_or_review_sources = [
        entry
        for entry in source_entries
        if entry.quality_status
        in {SourceQualityStatus.WEAK, SourceQualityStatus.NEEDS_REVIEW}
    ]
    freshness_review_sources = [
        entry
        for entry in source_entries
        if entry.freshness_status
        in {SourceFreshnessStatus.UNKNOWN, SourceFreshnessStatus.STALE}
    ]
    if weak_or_review_sources or freshness_review_sources:
        return {
            "status": ClaimSupportStatus.NEEDS_REVIEW,
            "missing_source_ids": [],
            "accepted_retrieval_source_ids": accepted_retrieval_source_ids,
            "missing_accepted_retrieval_evidence": False,
            "notes": (
                "Claim verification found source records, but at least one "
                "source still needs quality or freshness review."
            ),
        }

    return {
        "status": ClaimSupportStatus.SUPPORTED,
        "missing_source_ids": [],
        "accepted_retrieval_source_ids": accepted_retrieval_source_ids,
        "missing_accepted_retrieval_evidence": False,
        "notes": (
            "Claim verification found valid source records with acceptable "
            "quality and freshness signals"
            + (
                " and accepted retrieval evidence."
                if accepted_retrieval_source_ids
                else "."
            )
        ),
    }


def _claim_revision_plan_content(
    *,
    claims: list[ClaimRecord],
    source_by_id: dict[UUID, SourceRecord],
    reviewed_claims_by_id: dict[UUID, dict[str, Any]],
    retrieval_evidence_by_source_id: dict[UUID, Any],
    retrieval_ledger: ArtifactRecord | None,
) -> dict[str, Any]:
    held_claims = []
    for claim in claims:
        reviewed_claim = reviewed_claims_by_id.get(claim.claim_id)
        if reviewed_claim is None:
            continue
        status = reviewed_claim["status"]
        if status == ClaimSupportStatus.SUPPORTED:
            continue
        held_claims.append(
            {
                "claim_id": str(claim.claim_id),
                "claim_text": claim.claim_text,
                "support_status": status.value,
                "source_ids": [str(source_id) for source_id in claim.source_ids],
                "source_citation_ids": [
                    source_by_id[source_id].citation_id
                    for source_id in claim.source_ids
                    if source_id in source_by_id
                ],
                "accepted_retrieval_source_ids": [
                    str(source_id)
                    for source_id in reviewed_claim.get(
                        "accepted_retrieval_source_ids",
                        [],
                    )
                ],
                "missing_source_ids": [
                    str(source_id)
                    for source_id in reviewed_claim.get("missing_source_ids", [])
                ],
                "missing_accepted_retrieval_evidence": bool(
                    reviewed_claim.get("missing_accepted_retrieval_evidence")
                ),
                "reason": reviewed_claim.get("notes"),
                "rewrite_action": _claim_rewrite_action(reviewed_claim, status),
            }
        )

    accepted_source_alternatives = [
        retrieval_evidence_payload(evidence)
        for evidence in retrieval_evidence_by_source_id.values()
    ]
    status = "ready" if not held_claims else "revision_required"
    return {
        "status": status,
        "format": "claim_revision_plan",
        "held_claim_count": len(held_claims),
        "held_claims": held_claims,
        "accepted_source_alternatives": accepted_source_alternatives,
        "retrieval_ledger_artifact_id": (
            str(retrieval_ledger.artifact_id) if retrieval_ledger else None
        ),
        "retrieval_evidence_required": bool(
            retrieval_ledger and retrieval_evidence_by_source_id
        ),
        "target_writer_agent_ids": [
            "eli5-short-form-writer",
            "substack-essay-writer",
            "script-doctor",
        ],
        "writer_instructions": _claim_revision_writer_instructions(
            held_claims,
            accepted_source_alternatives,
        ),
    }


def _claim_rewrite_action(
    reviewed_claim: dict[str, Any],
    status: ClaimSupportStatus,
) -> str:
    if reviewed_claim.get("missing_source_ids"):
        return "hold_until_source_recorded"
    if reviewed_claim.get("missing_accepted_retrieval_evidence"):
        return "rewrite_against_accepted_retrieval_evidence_or_hold"
    if status == ClaimSupportStatus.UNSUPPORTED:
        return "remove_or_rewrite_as_unsupported_caveat"
    return "verify_source_quality_or_replace_source"


def _claim_revision_writer_instructions(
    held_claims: list[dict[str, Any]],
    accepted_source_alternatives: list[dict[str, Any]],
) -> list[str]:
    if not held_claims:
        return []
    instructions = [
        "Do not present held claims as factual until Claim Verification supports them.",
        "If a held claim lacks accepted retrieval evidence, either rewrite it using accepted source alternatives or remove it from the draft.",
        "Keep unsupported claims as caveats, open questions, or omit them from publishable copy.",
    ]
    if accepted_source_alternatives:
        instructions.append(
            "Prefer accepted retrieval source alternatives before raw source dependencies."
        )
    else:
        instructions.append(
            "Request research repair before drafting factual replacements."
        )
    return instructions


def _claim_revision_target_artifacts(
    artifacts: list[ArtifactRecord],
    held_claim_ids: list[UUID],
) -> list[ArtifactRecord]:
    held_claim_id_set = set(held_claim_ids)
    target_artifacts = [
        artifact
        for artifact in _leaf_source_content_artifacts(artifacts)
        if held_claim_id_set & set(_extract_artifact_claim_ids(artifact))
    ]
    if target_artifacts:
        return target_artifacts
    return _leaf_source_content_artifacts(artifacts)


def _claim_revision_followup_specs(
    claim_revision_plan_artifact: ArtifactRecord,
    artifacts: list[ArtifactRecord],
) -> list[dict[str, Any]]:
    held_claim_ids = [
        UUID(str(claim["claim_id"]))
        for claim in claim_revision_plan_artifact.content.get("held_claims", [])
        if claim.get("claim_id")
    ]
    target_artifacts = _claim_revision_target_artifacts(artifacts, held_claim_ids)
    artifacts_by_type = {
        artifact_type: [
            artifact for artifact in target_artifacts if artifact.artifact_type == artifact_type
        ]
        for artifact_type in SOURCE_CONTENT_TYPES
    }
    specs: list[dict[str, Any]] = []
    short_form_artifacts = [
        *artifacts_by_type.get(ArtifactType.POST, []),
        *artifacts_by_type.get(ArtifactType.REEL_SCRIPT, []),
    ]
    if short_form_artifacts:
        specs.append(
            _claim_revision_followup_spec(
                recipient_agent_id="eli5-short-form-writer",
                task_type="rewrite_short_form_from_claim_revision_plan",
                artifacts=short_form_artifacts,
                reason=(
                    "Rewrite ELI5 post/reel copy so held claims are removed, "
                    "caveated, or replaced with accepted retrieval evidence."
                ),
            )
        )
    substack_artifacts = artifacts_by_type.get(ArtifactType.SUBSTACK_ARTICLE, [])
    if substack_artifacts:
        specs.append(
            _claim_revision_followup_spec(
                recipient_agent_id="substack-essay-writer",
                task_type="rewrite_substack_from_claim_revision_plan",
                artifacts=substack_artifacts,
                reason=(
                    "Rewrite long-form sections so held claims are replaced with "
                    "accepted evidence or clearly held for research."
                ),
            )
        )
    reel_artifacts = artifacts_by_type.get(ArtifactType.REEL_SCRIPT, [])
    if reel_artifacts:
        specs.append(
            _claim_revision_followup_spec(
                recipient_agent_id="script-doctor",
                task_type="repair_script_claims_from_revision_plan",
                artifacts=reel_artifacts,
                reason=(
                    "Adjust hook, beats, and caveats around held claims before "
                    "the reel script returns to editorial review."
                ),
            )
        )
    if target_artifacts:
        specs.append(
            _claim_revision_followup_spec(
                recipient_agent_id="editor-in-chief",
                task_type="review_claim_revision_closure",
                artifacts=target_artifacts,
                reason=(
                    "Review revised artifacts after writer follow-ups resolve "
                    "the claim revision plan."
                ),
            )
        )
    return specs


def _claim_revision_followup_spec(
    *,
    recipient_agent_id: str,
    task_type: str,
    artifacts: list[ArtifactRecord],
    reason: str,
) -> dict[str, Any]:
    return {
        "recipient_agent_id": recipient_agent_id,
        "task_type": task_type,
        "target_artifact_ids": [str(artifact.artifact_id) for artifact in artifacts],
        "target_artifact_types": [
            artifact.artifact_type.value for artifact in artifacts
        ],
        "reason": reason,
    }


def _claim_revision_followup_signature(
    *,
    claim_revision_plan_artifact: ArtifactRecord,
    retrieval_ledger: ArtifactRecord | None,
    recipient_agent_id: str,
    task_type: str,
    target_artifact_ids: list[str],
) -> str:
    held_claim_ids = sorted(
        str(claim.get("claim_id"))
        for claim in claim_revision_plan_artifact.content.get("held_claims", [])
        if claim.get("claim_id")
    )
    target_ids = sorted(str(artifact_id) for artifact_id in target_artifact_ids)
    retrieval_ledger_id = (
        str(retrieval_ledger.artifact_id)
        if retrieval_ledger
        else str(
            claim_revision_plan_artifact.content.get(
                "retrieval_ledger_artifact_id",
                "none",
            )
        )
    )
    return ":".join(
        [
            "claim-revision-followup",
            retrieval_ledger_id,
            recipient_agent_id,
            task_type,
            ",".join(held_claim_ids),
            ",".join(target_ids),
        ]
    )


def _claim_revision_closure_ledger_content(
    *,
    artifacts: list[ArtifactRecord],
    claims: list[ClaimRecord],
    messages: list[AgentMessage],
) -> dict[str, Any]:
    plan_artifacts = [
        artifact
        for artifact in artifacts
        if artifact.artifact_type == ArtifactType.CLAIM_REVISION_PLAN
    ]
    if not plan_artifacts:
        return {
            "format": "claim_revision_ledger",
            "status": "no_claim_revision_plan",
            "plan_count": 0,
            "held_claim_count": 0,
            "open_held_claim_count": 0,
            "pending_followup_count": 0,
            "completed_followup_count": 0,
            "blocked_followup_count": 0,
            "revised_artifact_count": 0,
            "summary": "No claim revision plan has been recorded for this run.",
        }
    latest_plan = max(plan_artifacts, key=lambda artifact: artifact.created_at)
    held_claims = [
        claim
        for claim in latest_plan.content.get("held_claims", [])
        if isinstance(claim, dict)
    ]
    held_claim_ids = [
        str(claim.get("claim_id")) for claim in held_claims if claim.get("claim_id")
    ]
    claim_by_id = {str(claim.claim_id): claim for claim in claims}
    held_claim_statuses = {
        claim_id: (
            claim_by_id[claim_id].support_status.value
            if claim_id in claim_by_id
            else "missing_claim_record"
        )
        for claim_id in held_claim_ids
    }
    open_held_claim_ids = [
        claim_id
        for claim_id, status in held_claim_statuses.items()
        if status != ClaimSupportStatus.SUPPORTED.value
    ]
    followups = [
        message
        for message in messages
        if message.payload.get("workflow") == "claim_revision_followup_v1"
        and message.payload.get("claim_revision_plan_artifact_id")
        == str(latest_plan.artifact_id)
    ]
    followup_entries = [
        {
            "message_id": str(message.message_id),
            "recipient_agent_id": message.recipient_agent_id,
            "task_type": message.task_type,
            "status": message.status.value,
            "target_artifact_ids": message.payload.get("target_artifact_ids", []),
            "depends_on_message_ids": [
                str(message_id) for message_id in message.depends_on_message_ids
            ],
        }
        for message in followups
    ]
    pending_followups = [
        message
        for message in followups
        if message.status
        in {
            AgentTaskStatus.ACCEPTED,
            AgentTaskStatus.CLAIMED,
            AgentTaskStatus.IN_PROGRESS,
        }
    ]
    blocked_followups = [
        message
        for message in followups
        if message.status
        in {
            AgentTaskStatus.WAITING_FOR_HUMAN,
            AgentTaskStatus.BLOCKED,
            AgentTaskStatus.FAILED,
        }
    ]
    completed_followups = [
        message for message in followups if message.status == AgentTaskStatus.COMPLETED
    ]
    revised_artifacts = [
        artifact
        for artifact in artifacts
        if artifact.provenance.get("claim_revision_plan_artifact_id")
        == str(latest_plan.artifact_id)
        and artifact.artifact_type != ArtifactType.CLAIM_REVISION_LEDGER
    ]
    editor_followups = [
        message
        for message in followups
        if message.recipient_agent_id == "editor-in-chief"
    ]
    status = _claim_revision_closure_status(
        held_claim_count=len(held_claims),
        open_held_claim_count=len(open_held_claim_ids),
        followup_count=len(followups),
        pending_followup_count=len(pending_followups),
        blocked_followup_count=len(blocked_followups),
        completed_followup_count=len(completed_followups),
        revised_artifact_count=len(revised_artifacts),
        editor_followups=editor_followups,
    )
    return {
        "format": "claim_revision_ledger",
        "status": status,
        "plan_count": len(plan_artifacts),
        "claim_revision_plan_artifact_id": str(latest_plan.artifact_id),
        "held_claim_count": len(held_claims),
        "open_held_claim_count": len(open_held_claim_ids),
        "closed_held_claim_count": len(held_claims) - len(open_held_claim_ids),
        "held_claim_ids": held_claim_ids,
        "open_held_claim_ids": open_held_claim_ids,
        "held_claim_statuses": held_claim_statuses,
        "accepted_source_alternatives": latest_plan.content.get(
            "accepted_source_alternatives",
            [],
        ),
        "followup_count": len(followups),
        "pending_followup_count": len(pending_followups),
        "completed_followup_count": len(completed_followups),
        "blocked_followup_count": len(blocked_followups),
        "followup_status_counts": _value_counts(
            entry["status"] for entry in followup_entries
        ),
        "followups": followup_entries,
        "revised_artifact_count": len(revised_artifacts),
        "revised_artifact_ids": [
            str(artifact.artifact_id) for artifact in revised_artifacts
        ],
        "editor_followup_message_ids": [
            str(message.message_id) for message in editor_followups
        ],
        "recommended_next_actions": _claim_revision_closure_actions(
            status,
            open_held_claim_count=len(open_held_claim_ids),
            pending_followup_count=len(pending_followups),
            blocked_followup_count=len(blocked_followups),
            revised_artifact_count=len(revised_artifacts),
        ),
        "summary": _claim_revision_closure_summary(
            status=status,
            held_claim_count=len(held_claims),
            open_held_claim_count=len(open_held_claim_ids),
            followup_count=len(followups),
            revised_artifact_count=len(revised_artifacts),
        ),
    }


def _claim_revision_closure_status(
    *,
    held_claim_count: int,
    open_held_claim_count: int,
    followup_count: int,
    pending_followup_count: int,
    blocked_followup_count: int,
    completed_followup_count: int,
    revised_artifact_count: int,
    editor_followups: list[AgentMessage],
) -> str:
    if held_claim_count == 0:
        return "no_open_claim_revision"
    if blocked_followup_count:
        return "blocked"
    if followup_count == 0:
        return "no_followups_created"
    if pending_followup_count:
        return "followups_pending"
    if revised_artifact_count == 0:
        return "awaiting_revised_artifacts"
    if open_held_claim_count:
        return "needs_claim_reverification"
    if editor_followups and not all(
        message.status == AgentTaskStatus.COMPLETED for message in editor_followups
    ):
        return "needs_editor_review"
    if completed_followup_count == followup_count:
        return "closed"
    return "in_progress"


def _claim_revision_closure_actions(
    status: str,
    *,
    open_held_claim_count: int,
    pending_followup_count: int,
    blocked_followup_count: int,
    revised_artifact_count: int,
) -> list[str]:
    if status == "closed":
        return ["Claim revision loop is closed; proceed to publish-readiness review."]
    if status == "no_open_claim_revision":
        return ["No held claims remain in the latest claim revision plan."]
    if status == "no_followups_created":
        return ["Materialize claim revision follow-up tasks for writers and editor."]
    if blocked_followup_count:
        return ["Resolve blocked claim revision follow-up tasks."]
    if pending_followup_count:
        return ["Run pending claim revision writer/editor follow-up tasks."]
    if revised_artifact_count == 0:
        return ["Run writer follow-ups so revised artifacts carry the claim plan."]
    if open_held_claim_count:
        return ["Run Claim Verification again after revised artifacts are available."]
    return ["Review the claim revision closure ledger before publish readiness."]


def _claim_revision_closure_summary(
    *,
    status: str,
    held_claim_count: int,
    open_held_claim_count: int,
    followup_count: int,
    revised_artifact_count: int,
) -> str:
    return (
        f"Claim revision closure is {status}: {open_held_claim_count}/"
        f"{held_claim_count} held claim(s) remain open, {followup_count} "
        f"follow-up task(s) are tracked, and {revised_artifact_count} revised "
        "artifact(s) reference the latest plan."
    )


def _claim_needs_update(
    *,
    claim: ClaimRecord,
    status: ClaimSupportStatus,
    notes: str,
) -> bool:
    return (
        claim.support_status != status
        or claim.reviewer_agent_id != "claim-verification-agent"
        or claim.notes != notes
    )


def _source_ids_need_repair(
    source_ids: list[UUID],
    *,
    source_by_id: dict[UUID, SourceRecord],
    weak_source_ids: set[UUID],
) -> bool:
    return (
        not source_ids
        or any(source_id not in source_by_id for source_id in source_ids)
        or any(source_id in weak_source_ids for source_id in source_ids)
    )


def _repaired_source_ids(
    source_ids: list[UUID],
    *,
    replacement_source_ids: list[UUID],
    source_by_id: dict[UUID, SourceRecord],
    weak_source_ids: set[UUID],
) -> list[UUID]:
    retained_source_ids = [
        source_id
        for source_id in source_ids
        if source_id in source_by_id and source_id not in weak_source_ids
    ]
    repaired_source_ids: list[UUID] = []
    for source_id in [*retained_source_ids, *replacement_source_ids]:
        if source_id not in repaired_source_ids:
            repaired_source_ids.append(source_id)
    return repaired_source_ids


def _source_dependency_snapshots(
    *,
    source_ids: list[UUID],
    source_by_id: dict[UUID, SourceRecord],
) -> list[dict[str, Any]]:
    dependencies = []
    for source_id in source_ids:
        source = source_by_id.get(source_id)
        if source is None:
            continue
        dependencies.append(
            {
                "source_id": str(source.source_id),
                "citation_id": source.citation_id,
                "title": source.title,
                "url": str(source.url),
                "publisher": source.publisher,
                "published_at": (
                    source.published_at.isoformat() if source.published_at else None
                ),
            }
        )
    return dependencies


def _agent_name(agent_id: str) -> str:
    agent = get_agent_card(agent_id)
    return agent.name if agent else agent_id


def _realtime_conversation_brief_content(
    *,
    run,
    message: AgentMessage,
    context_summary: dict[str, Any],
    turns,
    realtime_sessions,
    messages: list[AgentMessage],
    feedback_items,
    events: list[RunEvent],
) -> dict[str, Any]:
    voice_feedback = [
        feedback
        for feedback in feedback_items
        if (
            feedback.target_agent_id == "realtime-conversation-host"
            or str(feedback.metadata.get("focus", "")).lower()
            in {"voice", "realtime", "conversation", "audio"}
            or _contains_any(
                feedback.feedback_text.lower(),
                [
                    "voice",
                    "audio",
                    "realtime",
                    "speech",
                    "interrupt",
                    "spoken",
                    "conversation",
                ],
            )
        )
    ]
    event_type_counts = _value_counts(event.event_type for event in events)
    task_status_counts = _value_counts(message.status.value for message in messages)
    control_events = _realtime_control_event_inventory(events, turns)
    interrupted_turns = [
        turn
        for turn in turns
        if bool(turn.metadata.get("interrupted"))
        or str(turn.metadata.get("interrupted", "")).lower() == "true"
    ]
    routed_voice_turns = [
        turn
        for turn in turns
        if turn.modality == "voice" and turn.speaker == "user"
    ]
    latest_turns = [
        {
            "turn_id": str(turn.turn_id),
            "speaker": turn.speaker,
            "modality": turn.modality,
            "transcript": turn.transcript,
            "metadata": turn.metadata,
        }
        for turn in turns[-6:]
    ]
    return {
        "format": "realtime_conversation_brief",
        "run_goal": run.goal,
        "task_type": message.task_type,
        "task_payload": message.payload,
        "provider_boundary": (
            "Realtime providers own speech transport, turn-taking, interruptions, "
            "and spoken output. Gemma 4 specialist agents own reasoning, writing, "
            "critique, visual analysis, and source-backed synthesis."
        ),
        "session_inventory": _realtime_session_inventory(realtime_sessions),
        "turn_inventory": {
            "turn_count": len(turns),
            "voice_user_turn_count": len(routed_voice_turns),
            "interrupted_turn_count": len(interrupted_turns),
            "latest_turns": latest_turns,
        },
        "handoff_state": {
            "accepted_task_count": task_status_counts.get(AgentTaskStatus.ACCEPTED.value, 0),
            "in_progress_task_count": task_status_counts.get(
                AgentTaskStatus.IN_PROGRESS.value, 0
            ),
            "completed_task_count": task_status_counts.get(
                AgentTaskStatus.COMPLETED.value, 0
            ),
            "failed_task_count": task_status_counts.get(AgentTaskStatus.FAILED.value, 0),
            "event_type_counts": event_type_counts,
        },
        "control_event_inventory": control_events,
        "voice_feedback_count": len(voice_feedback),
        "voice_feedback": [
            {
                "feedback_id": str(feedback.feedback_id),
                "status": feedback.status.value,
                "feedback_text": feedback.feedback_text,
                "metadata": feedback.metadata,
            }
            for feedback in voice_feedback
        ],
        "recommended_handoffs": _realtime_recommended_handoffs(
            voice_feedback=voice_feedback,
            realtime_sessions=realtime_sessions,
            turns=turns,
            control_events=control_events,
            event_type_counts=event_type_counts,
        ),
        "host_operating_rules": [
            "A user interruption must stop or supersede pending speech before another spoken reply starts.",
            "Durable realtime control events must be resolved by an explicit resume, stop-output acknowledgement, or the next routed voice turn before another long spoken reply.",
            "Every routed voice turn keeps the run id, realtime session id, provider, interruption flag, and response turn id in durable state.",
            "Provider secrets stay out of event payloads and artifacts.",
            "When background specialists continue after a voice turn, the host should speak a short status summary instead of pretending work is finished.",
            "If speech confidence, user intent, or output approval is ambiguous, open a human feedback gate before publishing.",
        ],
        "context_summary": context_summary,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _realtime_handoff_message_id(
    *,
    message: AgentMessage,
    target_agent_id: str,
    task_type: str,
) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        (
            "all-about-llms:realtime_conversation_handoff:"
            f"{message.run_id}:{message.message_id}:{target_agent_id}:{task_type}"
        ),
    )


def _agent_worker_child_message_id(
    *,
    run_id: UUID,
    parent_message_id: UUID,
    sender_agent_id: str,
    recipient_agent_id: str,
    task_type: str,
) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        (
            "all-about-llms:agent_worker_child:"
            f"{run_id}:{parent_message_id}:{sender_agent_id}:"
            f"{recipient_agent_id}:{task_type}"
        ),
    )


def _agent_worker_event_idempotency_key(
    *,
    run_id: UUID,
    event_type: str,
    message_id: UUID,
) -> str:
    return f"agent_worker_v1:{run_id}:{event_type}:{message_id}"


async def _append_agent_worker_event_if_absent(
    store,
    event: RunEvent,
    *,
    idempotency_key: str,
) -> RunEvent | None:
    appender = getattr(store, "append_event_if_absent", None)
    if callable(appender):
        return await appender(event, idempotency_key=idempotency_key)
    event.payload = {
        **event.payload,
        "event_idempotency_key": idempotency_key,
    }
    return await store.append_event(event)


def _agent_worker_artifact_id(
    *,
    run_id: UUID,
    message_id: UUID,
    workflow: str,
    artifact_type: ArtifactType,
) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        (
            "all-about-llms:agent_worker_artifact:"
            f"{run_id}:{message_id}:{workflow}:{artifact_type.value}"
        ),
    )


def _content_strategy_requested_artifact_types(
    payload: dict[str, Any],
) -> list[ArtifactType]:
    target_formats = {
        str(target_format).lower().strip()
        for target_format in payload.get("target_formats", [])
        if isinstance(target_format, str) and target_format.strip()
    }
    search_text = _intent_route_search_text(payload)
    requested: list[ArtifactType] = []

    def add(artifact_type: ArtifactType) -> None:
        if artifact_type not in requested:
            requested.append(artifact_type)

    if "post" in target_formats or _contains_any(
        search_text,
        ["post", "caption", "carousel", "instagram", "linkedin"],
    ):
        add(ArtifactType.POST)
    if "reel" in target_formats or _contains_any(
        search_text,
        ["reel", "short", "video", "script", "tiktok", "youtube"],
    ):
        add(ArtifactType.REEL_SCRIPT)
    if "substack" in target_formats or _contains_any(
        search_text,
        ["substack", "article", "essay", "newsletter", "long-form", "longform"],
    ):
        add(ArtifactType.SUBSTACK_ARTICLE)
    if requested:
        return requested
    return [
        ArtifactType.POST,
        ArtifactType.REEL_SCRIPT,
        ArtifactType.SUBSTACK_ARTICLE,
    ]


def _content_strategy_requires_seed_artifacts(
    *,
    payload: dict[str, Any],
    existing_artifacts: list[ArtifactRecord],
) -> bool:
    if payload.get("route_plan_artifact_id"):
        return True
    if payload.get("transcript") or payload.get("turn_id") or payload.get(
        "realtime_session_id"
    ):
        return True
    workflow = str(payload.get("workflow") or "").lower()
    if any(token in workflow for token in ("realtime", "conversation", "voice")):
        return True
    if payload.get("target_artifact_ids"):
        return False
    return not any(
        artifact.artifact_type in SOURCE_CONTENT_TYPES for artifact in existing_artifacts
    )


def _content_strategy_seed_artifacts_for_message(
    artifacts: list[ArtifactRecord],
    *,
    message: AgentMessage,
    requested_types: list[ArtifactType],
) -> list[ArtifactRecord]:
    seed_by_type = {
        artifact.artifact_type: artifact
        for artifact in artifacts
        if artifact.artifact_type in SOURCE_CONTENT_TYPES
        and artifact.provenance.get("workflow")
        == "content_strategy_seed_artifact_v1"
        and artifact.provenance.get("message_id") == str(message.message_id)
    }
    return [
        seed_by_type[artifact_type]
        for artifact_type in requested_types
        if artifact_type in seed_by_type
    ]


def _content_strategy_seed_source_context(
    *,
    payload: dict[str, Any],
    artifacts: list[ArtifactRecord],
    sources: list[SourceRecord],
    claims: list[ClaimRecord],
) -> tuple[list[SourceRecord], list[ClaimRecord]]:
    source_ids = _uuid_set_from_payload(
        payload,
        (
            "source_ids",
            "target_source_ids",
            "target_artifact_source_ids",
        ),
    )
    claim_ids = _uuid_set_from_payload(
        payload,
        (
            "claim_ids",
            "target_claim_ids",
            "target_artifact_claim_ids",
        ),
    )
    target_artifact_ids = _uuid_set_from_payload(payload, ("target_artifact_ids",))
    if target_artifact_ids:
        for artifact in artifacts:
            if artifact.artifact_id not in target_artifact_ids:
                continue
            source_ids.update(artifact.source_ids)
            claim_ids.update(_extract_artifact_claim_ids(artifact))
    source_id_set = set(source_ids)
    claim_id_set = set(claim_ids)
    return (
        [source for source in sources if source.source_id in source_id_set],
        [claim for claim in claims if claim.claim_id in claim_id_set],
    )


def _uuid_set_from_payload(
    payload: dict[str, Any],
    keys: tuple[str, ...],
) -> set[UUID]:
    ids: set[UUID] = set()

    def collect(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, UUID):
            ids.add(value)
            return
        if isinstance(value, str):
            try:
                ids.add(UUID(value))
            except ValueError:
                return
            return
        if isinstance(value, dict):
            for nested_key in (
                "id",
                "source_id",
                "claim_id",
                "artifact_id",
            ):
                collect(value.get(nested_key))
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                collect(item)

    for key in keys:
        collect(payload.get(key))
    return ids


def _content_strategy_seed_title(artifact_type: ArtifactType, topic: str) -> str:
    if artifact_type == ArtifactType.POST:
        return f"Voice-originated social post seed: {topic}"
    if artifact_type == ArtifactType.REEL_SCRIPT:
        return f"Voice-originated reel seed: {topic}"
    if artifact_type == ArtifactType.SUBSTACK_ARTICLE:
        return f"Voice-originated Substack seed: {topic}"
    return f"Voice-originated content seed: {topic}"


def _content_strategy_seed_content(
    *,
    artifact_type: ArtifactType,
    topic: str,
    message: AgentMessage,
    sources: list[SourceRecord],
    claims: list[ClaimRecord],
) -> dict[str, Any]:
    transcript = str(message.payload.get("transcript") or "").strip()
    evidence_note = (
        "source_context_available_needs_review"
        if sources
        else "needs_web_research_before_publish"
    )
    base = {
        "format": "content_strategy_seed",
        "topic": topic,
        "source": "voice_or_conversation_handoff",
        "transcript": transcript,
        "evidence_status": evidence_note,
        "source_ids": [str(source.source_id) for source in sources],
        "claim_ids": [str(claim.claim_id) for claim in claims],
        "review_required": True,
        "publishable": False,
        "source_caveat": (
            "Use linked source ids for claims before publishing."
            if sources
            else "Run web research and source-ledger review before publishing."
        ),
    }
    if artifact_type == ArtifactType.POST:
        base.update(
            {
                "hook": f"ELI5 take on {topic}",
                "body": (
                    transcript
                    or f"Explain {topic} in simple, source-backed language."
                ),
                "cta": "Save this before you build your own agent stack.",
            }
        )
    elif artifact_type == ArtifactType.REEL_SCRIPT:
        base.update(
            {
                "hook": f"Here is {topic} in plain English.",
                "script": [
                    f"Start with the simple problem: {topic}.",
                    transcript
                    or "Explain the concept with one concrete example.",
                    "End with the source trail and a clear next step.",
                ],
                "caption": f"ELI5 source-backed reel seed for {topic}.",
            }
        )
    elif artifact_type == ArtifactType.SUBSTACK_ARTICLE:
        base.update(
            {
                "headline": f"{topic}: an ELI5 but detailed guide",
                "lede": transcript
                or f"A plain-language, source-backed breakdown of {topic}.",
                "sections": [
                    "What this means in simple terms",
                    "Why it matters in real systems",
                    "Source-backed claims to verify",
                    "Practical implications",
                ],
            }
        )
    return base


def _existing_worker_artifact(
    artifacts: list[ArtifactRecord],
    *,
    artifact_type: ArtifactType,
    workflow: str,
    message_id: UUID,
) -> ArtifactRecord | None:
    for artifact in reversed(artifacts):
        if artifact.artifact_type != artifact_type:
            continue
        provenance = artifact.provenance or {}
        if provenance.get("workflow") != workflow:
            continue
        if provenance.get("message_id") == str(message_id):
            return artifact
    return None


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _dedupe_message_ids(message_ids: list[UUID]) -> list[UUID]:
    seen = set()
    deduped = []
    for message_id in message_ids:
        if message_id in seen:
            continue
        seen.add(message_id)
        deduped.append(message_id)
    return deduped


def _realtime_brief_transcript_excerpt(brief_content: dict[str, Any]) -> str:
    latest_turns = brief_content.get("turn_inventory", {}).get("latest_turns", [])
    if not isinstance(latest_turns, list):
        return ""
    excerpts = []
    for turn in latest_turns[-4:]:
        if not isinstance(turn, dict):
            continue
        transcript = str(turn.get("transcript") or "").strip()
        if not transcript:
            continue
        speaker = str(turn.get("speaker") or "unknown").strip() or "unknown"
        excerpts.append(f"{speaker}: {transcript}")
    return "\n".join(excerpts)[:1000]


def _realtime_recommended_handoffs(
    *,
    voice_feedback,
    realtime_sessions,
    turns,
    control_events: dict[str, Any],
    event_type_counts: dict[str, int],
) -> list[dict[str, str]]:
    handoffs = []

    def add(target_agent_id: str, task_type: str, reason: str) -> None:
        if not any(
            item["target_agent_id"] == target_agent_id
            and item["task_type"] == task_type
            for item in handoffs
        ):
            handoffs.append(
                {
                    "target_agent_id": target_agent_id,
                    "target_agent_name": _agent_name(target_agent_id),
                    "task_type": task_type,
                    "reason": reason,
                }
            )

    if voice_feedback:
        add(
            "forward-deployed-engineer",
            "translate_voice_feedback",
            "Voice or realtime feedback needs requirements and acceptance criteria.",
        )
    if not realtime_sessions:
        add(
            "audio-producer",
            "plan_realtime_session",
            "No realtime session is recorded for this run yet.",
        )
    if event_type_counts.get("realtime_session_configuration_failed", 0):
        add(
            "observability-agent",
            "review_realtime_provider_failure",
            "Realtime provider setup has failed and should be visible in run health.",
        )
    if any(turn.metadata.get("interrupted") for turn in turns):
        add(
            "audio-producer",
            "review_interruption_and_resume",
            "Interrupted voice turns need explicit resume and spoken-status behavior.",
        )
    if control_events["unresolved_control_event_ids"]:
        add(
            "product-manager",
            "coordinate_realtime_control_resolution",
            "Durable realtime controls are unresolved and need an explicit next conversational state.",
        )
        add(
            "audio-producer",
            "review_realtime_control_audio_state",
            "Realtime interrupt/resume/stop-output controls affect spoken output timing and voiceover behavior.",
        )
    if turns:
        add(
            "intent-router",
            "route_latest_voice_context",
            "Recent voice/text context may need specialist background work.",
        )
    if not handoffs:
        add(
            "product-manager",
            "coordinate_realtime_next_step",
            "No realtime blocker is visible; keep the next conversational action explicit.",
        )
    return handoffs


def _realtime_control_event_inventory(
    events: list[RunEvent], turns
) -> dict[str, Any]:
    resolved_event_ids = {
        int(str(event_id))
        for turn in turns
        for event_id in [turn.metadata.get("interruption_control_event_id")]
        if _int_like(event_id)
    }
    controls = []
    action_counts: dict[str, int] = {}
    for event in events:
        if event.event_type != "realtime_session_control_recorded":
            continue
        payload = event.payload or {}
        action = str(payload.get("action") or "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1
        controls.append(
            {
                "event_id": event.event_id,
                "realtime_session_id": payload.get("realtime_session_id"),
                "action": action,
                "reason": payload.get("reason"),
                "followup_task_message_id": payload.get("followup_task_message_id"),
                "resolved": event.event_id in resolved_event_ids
                if event.event_id is not None
                else False,
                "created_at": event.created_at.isoformat(),
            }
        )
    unresolved_ids = [
        item["event_id"]
        for item in controls
        if item["action"] == "interrupt"
        and not item["resolved"]
        and item["event_id"] is not None
    ]
    return {
        "control_event_count": len(controls),
        "control_action_counts": action_counts,
        "unresolved_control_event_ids": unresolved_ids,
        "recent_controls": controls[-8:],
    }


def _int_like(value) -> bool:
    try:
        int(str(value))
    except (TypeError, ValueError):
        return False
    return True


def _select_intent_route_targets(payload: dict[str, Any]) -> list[str]:
    routed_intent = str(payload.get("routed_intent") or "").lower()
    requested_intent = str(payload.get("requested_intent") or "").lower()
    text = _intent_route_search_text(payload)
    target_formats = {
        str(target_format).lower()
        for target_format in payload.get("target_formats", [])
        if isinstance(target_format, str)
    }
    targets: list[str] = []

    def add(agent_id: str) -> None:
        if len(targets) >= INTENT_ROUTER_MAX_TARGETS:
            return
        if agent_id in {
            "intent-router",
            "realtime-conversation-host",
        }:
            return
        if get_agent_card(agent_id) is None:
            return
        if agent_id not in targets:
            targets.append(agent_id)

    if "record_only" in {routed_intent, requested_intent}:
        add("interactive-note-taking-agent")
        return targets

    if "revise_content" in {routed_intent, requested_intent} or _contains_any(
        text,
        [
            "revise",
            "revision",
            "feedback",
            "change",
            "improve",
            "fix",
            "update",
            "incorporate",
        ],
    ):
        add("forward-deployed-engineer")
        add("editor-in-chief")
        add("critic-reviewer-agent")

    if "create_content" in {routed_intent, requested_intent} or target_formats:
        add("content-strategist")

    if _contains_any(
        text,
        [
            "post",
            "reel",
            "substack",
            "article",
            "draft",
            "write",
            "create",
            "generate",
            "caption",
            "carousel",
            "script",
        ],
    ):
        add("content-strategist")

    if "reel" in target_formats or _contains_any(
        text,
        ["reel", "short", "storyboard", "shot list", "subtitle", "video"],
    ):
        add("video-reel-producer")

    if _contains_any(
        text,
        [
            "source",
            "sources",
            "research",
            "fresh",
            "freshness",
            "latest",
            "web",
            "citation",
            "cite",
        ],
    ):
        add("web-research-agent")
        add("source-ledger-agent")

    if _contains_any(
        text,
        ["claim", "fact", "verify", "verification", "evidence", "unsupported"],
    ):
        add("claim-verification-agent")
        add("source-ledger-agent")

    if _contains_any(
        text,
        ["data", "chart", "metric", "benchmark", "table", "stats", "compare"],
    ):
        add("data-analyst-agent")

    if _contains_any(
        text,
        [
            "visual",
            "image",
            "thumbnail",
            "diagram",
            "frame",
            "frames",
            "design",
            "asset",
        ],
    ):
        add("visual-director")
        add("image-generation-agent")

    if _contains_any(
        text,
        [
            "audio",
            "voice",
            "voiceover",
            "tts",
            "speech",
            "realtime",
            "spoken",
            "interrupt",
        ],
    ):
        add("audio-producer")

    if _contains_any(
        text,
        [
            "hashtag",
            "keyword",
            "platform",
            "instagram",
            "linkedin",
            "tiktok",
            "youtube",
            "distribution",
        ],
    ):
        add("platform-optimization-agent")
        add("influencer-strategy-agent")

    if _contains_any(text, ["outreach", "collab", "community", "partner"]):
        add("outreach-agent")

    if _contains_any(
        text,
        ["ui", "ux", "cockpit", "interface", "screen", "button", "layout"],
    ):
        add("lead-ui-ux-designer")
        add("frontend-experience-engineer")

    if _contains_any(
        text,
        ["planning html", "planning surface", "system diagram", "architecture map"],
    ):
        add("interactive-systems-designer")

    if _contains_any(
        text,
        [
            "architecture",
            "orchestration",
            "checkpoint",
            "resume",
            "durable",
            "context",
            "memory",
            "agent harness",
        ],
    ):
        add("principal-software-engineer")
        add("agent-harness-engineer")
        add("context-engineering-agent")

    if _contains_any(
        text,
        [
            "backend",
            "fastapi",
            "api",
            "postgres",
            "pgvector",
            "migration",
            "database",
            "schema",
        ],
    ):
        add("backend-platform-engineer")

    if _contains_any(
        text,
        [
            "scale",
            "scalability",
            "reliability",
            "slo",
            "capacity",
            "backpressure",
            "scheduler",
            "heartbeat",
            "always-on",
            "degradation",
        ],
    ):
        add("scalability-reliability-engineer")

    if _contains_any(
        text,
        [
            "inference",
            "provider",
            "hf",
            "hugging face",
            "gemma",
            "latency",
            "cost",
            "fallback",
            "smoke",
            "model routing",
        ],
    ):
        add("inference-systems-engineer")

    if not targets:
        add("product-manager")
        add("content-strategist")
    return targets


def _intent_route_search_text(payload: dict[str, Any]) -> str:
    text_parts = [
        payload.get("transcript"),
        payload.get("topic"),
        payload.get("instruction"),
        payload.get("requested_intent"),
        payload.get("routed_intent"),
    ]
    target_formats = payload.get("target_formats")
    if isinstance(target_formats, list):
        text_parts.extend(str(target_format) for target_format in target_formats)
    return " ".join(str(part) for part in text_parts if part).lower()


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def _intent_router_task_type(agent_id: str) -> str:
    return INTENT_ROUTE_TASK_TYPES.get(agent_id, "handle_conversation_turn")


def _intent_route_target_reason(
    *,
    target_agent_id: str,
    payload: dict[str, Any],
) -> str:
    reason_by_agent = {
        "content-strategist": "The turn asks for content planning or content creation.",
        "web-research-agent": "The turn needs current source discovery or freshness checks.",
        "source-ledger-agent": "The turn asks for citation/source coverage to be maintained.",
        "claim-verification-agent": "The turn needs claims mapped to evidence before publishing.",
        "data-analyst-agent": "The turn asks for real-world data, comparisons, or chart-ready structure.",
        "forward-deployed-engineer": "The turn contains feedback or requested changes that need requirements.",
        "principal-software-engineer": "The turn affects system architecture or durability decisions.",
        "backend-platform-engineer": "The turn affects FastAPI, Postgres/pgvector, migrations, async APIs, or backend consistency.",
        "frontend-experience-engineer": "The turn affects cockpit implementation, browser voice controls, frontend state, or accessibility.",
        "scalability-reliability-engineer": "The turn affects scale, SLOs, capacity, backpressure, scheduler behavior, or degradation policy.",
        "inference-systems-engineer": "The turn affects OpenRouter/LiveKit/Kokoro realtime providers, legacy native-Gemma/HF context, model routing, latency, cost, fallback, or smoke proof.",
        "agent-harness-engineer": "The turn affects checkpointing, resume behavior, or worker execution.",
        "context-engineering-agent": "The turn affects reusable context, memory, or retrieval policy.",
        "product-manager": "The turn needs coordination across product scope and next actions.",
        "interactive-note-taking-agent": "The turn should be preserved as structured interactive notes.",
        "visual-director": "The turn asks for visual direction, thumbnails, diagrams, or frames.",
        "image-generation-agent": "The turn needs imagegen-ready raster asset prompts.",
        "audio-producer": "The turn asks for voice, TTS, speech, or realtime audio planning.",
        "video-reel-producer": "The turn asks for reels, video structure, subtitles, or storyboards.",
        "platform-optimization-agent": "The turn needs channel-specific packaging.",
        "influencer-strategy-agent": "The turn asks for keywords, hashtags, audience targeting, or creator packaging.",
        "outreach-agent": "The turn asks for community, partnership, or outreach angles.",
        "lead-ui-ux-designer": "The turn asks for product cockpit UI/UX feedback.",
        "interactive-systems-designer": "The turn asks for the separate planning HTML surface.",
        "editor-in-chief": "The turn asks for editorial judgment on requested changes.",
        "critic-reviewer-agent": "The turn needs a skeptical critique before the next revision.",
    }
    target_formats = payload.get("target_formats", [])
    if target_formats and target_agent_id == "content-strategist":
        return (
            reason_by_agent[target_agent_id]
            + f" Requested formats: {', '.join(str(item) for item in target_formats)}."
        )
    return reason_by_agent.get(
        target_agent_id,
        "The turn matched this specialist's durable A2A responsibility.",
    )


def _intent_route_plan_content(
    *,
    run,
    message: AgentMessage,
    context_summary: dict[str, Any],
    target_agent_ids: list[str],
    planned_handoffs: list[dict[str, Any]],
    turns,
    messages: list[AgentMessage],
    artifacts: list[ArtifactRecord],
    sources: list[SourceRecord],
    feedback_items,
) -> dict[str, Any]:
    topic = _topic_from_payload(message.payload)
    if topic == "the current user goal" and run.goal:
        topic = run.goal
    routed_intent = message.payload.get("routed_intent") or "route_task"
    requested_intent = message.payload.get("requested_intent") or "auto"
    return {
        "format": "intent_route_plan",
        "topic": topic,
        "turn_id": message.payload.get("turn_id"),
        "parent_message_id": str(message.message_id),
        "requested_intent": requested_intent,
        "routed_intent": routed_intent,
        "transcript": message.payload.get("transcript", ""),
        "target_formats": message.payload.get("target_formats", []),
        "target_agent_ids": target_agent_ids,
        "planned_handoffs": planned_handoffs,
        "conversation_context": {
            "run_goal": run.goal,
            "turn_count": len(turns),
            "recent_turns": [
                {
                    "turn_id": str(turn.turn_id),
                    "speaker": turn.speaker,
                    "modality": turn.modality,
                    "transcript": turn.transcript,
                }
                for turn in turns[-4:]
            ],
        },
        "run_state": {
            "agent_message_count": len(messages),
            "artifact_count": len(artifacts),
            "source_count": len(sources),
            "feedback_count": len(feedback_items),
            "open_feedback_count": sum(
                1
                for feedback in feedback_items
                if feedback.status in {FeedbackStatus.OPEN, FeedbackStatus.ROUTED}
            ),
        },
        "routing_policy": [
            "Do not block live dialogue while specialist workers continue in the background.",
            "Route source-backed content requests through research, source ledger, and verification specialists when freshness or evidence is requested.",
            "Keep voice transport with realtime providers; route audio planning to Audio Producer only when spoken output or voice direction is requested.",
            "Preserve user feedback as structured downstream tasks instead of free-form notes.",
        ],
        "context_summary": context_summary,
        "created_task_message_ids": [],
        "created_target_agent_ids": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _topic_from_payload(payload: dict[str, Any]) -> str:
    topic = payload.get("topic") or payload.get("query") or payload.get("title")
    if isinstance(topic, str) and topic.strip():
        return topic.strip()
    return "the current user goal"


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _search_queries_from_payload(
    payload: dict[str, Any], *, fallback_topic: str
) -> tuple[list[str], int]:
    raw_queries = payload.get("search_queries")
    if isinstance(raw_queries, str):
        raw_queries = [raw_queries]
    if not isinstance(raw_queries, list):
        raw_queries = []
    queries = [
        str(query).strip()
        for query in raw_queries
        if isinstance(query, str) and query.strip()
    ]
    deduped_queries = list(dict.fromkeys(queries))
    if deduped_queries:
        return (
            deduped_queries[:MAX_WEB_RESEARCH_SEARCH_QUERIES],
            max(0, len(deduped_queries) - MAX_WEB_RESEARCH_SEARCH_QUERIES),
        )
    if fallback_topic.strip():
        return [fallback_topic.strip()], 0
    return ["the current user goal"], 0


def _retrieval_quality_result_summary(result) -> dict[str, Any]:
    return {
        "status": result.status.value,
        "topic": result.topic,
        "ledger_artifact_id": (
            str(result.ledger_artifact_id) if result.ledger_artifact_id else None
        ),
        "event_id": result.event_id,
        "candidate_count": result.candidate_count,
        "accepted_candidate_count": result.accepted_candidate_count,
        "precision_risk_count": result.precision_risk_count,
        "recall_gap_count": result.recall_gap_count,
        "coverage_gap_count": result.coverage_gap_count,
        "summary": result.summary,
    }


def _knowledge_graph_worker_summary(entries) -> dict[str, Any]:
    traversal_edges = []
    for entry in entries:
        if entry.node_type != "claim":
            continue
        for source_id in entry.source_ids:
            supported = entry.coverage_status == "covered"
            traversal_edges.append(
                {
                    "from_node_id": entry.node_id,
                    "to_node_id": f"source:{source_id}",
                    "relationship": (
                        "supported_by" if supported else "candidate_evidence"
                    ),
                    "confidence": 1.0 if supported else 0.35,
                    "source_ids": [str(source_id)],
                }
            )
    return {
        "node_count": len(entries),
        "node_type_counts": _value_counts(
            sorted(entry.node_type for entry in entries)
        ),
        "coverage_status_counts": _value_counts(
            sorted(entry.coverage_status for entry in entries)
        ),
        "coverage_gap_count": sum(
            1 for entry in entries if entry.coverage_status != "covered"
        ),
        "covered_node_ids": [
            entry.node_id for entry in entries if entry.coverage_status == "covered"
        ],
        "gap_node_ids": [
            entry.node_id for entry in entries if entry.coverage_status != "covered"
        ],
        "traversal_edges": traversal_edges,
        "graph_coverage": [
            entry.model_dump(mode="json") if hasattr(entry, "model_dump") else entry
            for entry in entries
        ],
    }


class _SourceRefreshRetrievalRerankerFallback:
    provider_id = "source_refresh_retrieval_reranker_with_fallback"

    def __init__(
        self,
        *,
        store,
        run_id: UUID,
        primary_reranker,
        actor: str,
    ) -> None:
        self._store = store
        self._run_id = run_id
        self._primary_reranker = primary_reranker
        self._actor = actor
        self._fallback_reranker = DeterministicRerankerProvider()

    async def rerank(self, request: RerankRequest) -> list[RerankResult]:
        try:
            return await self._primary_reranker.rerank(request)
        except Exception as exc:
            safe_reason = _redact_provider_failure_text(
                f"{type(exc).__name__}: {exc}"
            )
            await self._store.append_event(
                RunEvent(
                    run_id=self._run_id,
                    event_type="provider_fallback",
                    actor=self._actor,
                    payload={
                        "provider": "retrieval_quality_reranker",
                        "reason": safe_reason,
                    },
                )
            )
            return await self._fallback_reranker.rerank(request)


TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
}


def _canonical_source_url(value: Any) -> str:
    raw = str(value).strip()
    if not raw:
        return raw
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return raw.rstrip("/")
    filtered_query = urlencode(
        [
            (key, item_value)
            for key, item_value in parse_qsl(
                parsed.query,
                keep_blank_values=True,
            )
            if not key.lower().startswith("utm_")
            and key.lower() not in TRACKING_QUERY_KEYS
        ],
        doseq=True,
    )
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            filtered_query,
            "",
        )
    )


async def _rank_provider_search_results(
    *,
    topic: str,
    provider_results: list[tuple[str, int, SearchResult]],
    reranker_provider,
) -> tuple[
    list[tuple[str, int, SearchResult, RerankResult]],
    dict[str, Any],
]:
    candidates: list[RerankCandidate] = []
    candidate_payloads: dict[str, tuple[str, int, SearchResult]] = {}
    seen_urls: set[str] = set()
    for provider_order, (query, query_rank, result) in enumerate(
        provider_results,
        start=1,
    ):
        normalized_url = _canonical_source_url(result.url)
        if normalized_url in seen_urls:
            continue
        seen_urls.add(normalized_url)
        candidate_id = f"provider-result:{provider_order}"
        candidate_payloads[candidate_id] = (query, query_rank, result)
        quality = _search_result_quality(
            query=query,
            query_rank=query_rank,
            result=result,
        )
        candidates.append(
            RerankCandidate(
                candidate_id=candidate_id,
                title=result.title,
                url=str(result.url),
                snippet=result.snippet,
                query=query,
                retrievers=["web_search"],
                rank=provider_order,
                metadata={
                    "search_query": query,
                    "search_rank": query_rank,
                    "provider_order": provider_order,
                    "source_type": "worker_web_search_result",
                    "quality_status": quality.quality_status.value,
                    "freshness_status": quality.freshness_status.value,
                    "has_published_at": result.published_at is not None,
                    "publisher": result.publisher,
                },
            )
        )

    if not candidates:
        return [], {
            "reranker": None,
            "reranked_result_count": 0,
            "reranker_fallback_reason": None,
        }

    active_reranker = reranker_provider or DeterministicRerankerProvider()
    fallback_reason = None
    try:
        rerank_results = await active_reranker.rerank(
            RerankRequest(
                query=topic,
                candidates=candidates,
                top_k=len(candidates),
                metadata={"workflow": "worker_web_research_source_refresh_v1"},
            )
        )
    except Exception as exc:
        fallback_reason = _redact_provider_failure_text(
            f"{type(exc).__name__}: {exc}"
        )
        active_reranker = DeterministicRerankerProvider()
        rerank_results = await active_reranker.rerank(
            RerankRequest(
                query=topic,
                candidates=candidates,
                top_k=len(candidates),
                metadata={
                    "workflow": "worker_web_research_source_refresh_v1",
                    "fallback_reason": fallback_reason,
                },
            )
        )

    rerank_by_id = {
        result.candidate_id: result
        for result in rerank_results
        if result.candidate_id in candidate_payloads
    }
    missing_candidates = [
        candidate
        for candidate in candidates
        if candidate.candidate_id not in rerank_by_id
    ]
    missing_results = [
        _unranked_candidate_result(
            candidate,
            rank_after=len(rerank_by_id) + index,
            provider_id=_reranker_provider_id(active_reranker, rerank_results),
        )
        for index, candidate in enumerate(missing_candidates, start=1)
    ]
    for result in missing_results:
        rerank_by_id[result.candidate_id] = result

    ordered = [
        (
            candidate_payloads[result.candidate_id][0],
            candidate_payloads[result.candidate_id][1],
            candidate_payloads[result.candidate_id][2],
            result,
        )
        for result in sorted(
            rerank_by_id.values(),
            key=lambda item: (
                item.rank_after,
                -item.relevance_score,
                item.candidate_id,
            ),
        )
    ]
    return ordered, {
        "reranker": _reranker_provider_id(active_reranker, rerank_results),
        "reranked_result_count": len(ordered),
        "reranker_fallback_reason": fallback_reason,
    }


def _search_result_quality(
    *,
    query: str,
    query_rank: int,
    result: SearchResult,
):
    published_at = _parse_provider_datetime(result.published_at)
    retrieved_at = _parse_provider_datetime(result.retrieved_at)
    source = SourceRecord(
        run_id=UUID(int=0),
        citation_id="candidate",
        title=result.title,
        url=result.url,
        publisher=result.publisher,
        retrieved_at=retrieved_at or datetime.now(timezone.utc),
        published_at=published_at,
        metadata={
            "source_type": "worker_web_search_result",
            "snippet": result.snippet,
            "published_at": result.published_at,
            "retrieved_at": result.retrieved_at,
            "search_query": query,
            "search_rank": query_rank,
            "freshness": "current",
        },
    )
    return evaluate_source_quality(source)


def _reranker_provider_id(reranker_provider, rerank_results: list[RerankResult]) -> str:
    for result in rerank_results:
        provider_id = result.metadata.get("provider_id")
        if isinstance(provider_id, str) and provider_id.strip():
            return provider_id.strip()
    provider_id = getattr(reranker_provider, "provider_id", None)
    if isinstance(provider_id, str) and provider_id.strip():
        return provider_id.strip()
    return type(reranker_provider).__name__


def _unranked_candidate_result(
    candidate: RerankCandidate,
    *,
    rank_after: int,
    provider_id: str,
) -> RerankResult:
    return RerankResult(
        candidate_id=candidate.candidate_id,
        rank_before=candidate.rank,
        rank_after=rank_after,
        relevance_score=0.0,
        reason="candidate was not returned by reranker",
        metadata={"provider_id": provider_id, "missing_from_reranker": True},
    )


def _target_agent_from_payload(payload: dict[str, Any]) -> str | None:
    raw_agent_id = payload.get("target_agent_id") or payload.get("agent_id")
    if isinstance(raw_agent_id, str) and raw_agent_id.strip():
        agent_id = raw_agent_id.strip()
        if get_agent_card(agent_id) is not None:
            return agent_id
    return None


def _feedback_ids_from_payload(payload: dict[str, Any]) -> set[str]:
    raw_feedback_ids = payload.get("feedback_ids")
    if raw_feedback_ids is None:
        raw_feedback_ids = payload.get("feedback_id")
    if raw_feedback_ids is None:
        return set()
    if isinstance(raw_feedback_ids, str):
        raw_feedback_ids = [raw_feedback_ids]
    if not isinstance(raw_feedback_ids, list):
        return set()
    return {
        str(feedback_id)
        for feedback_id in raw_feedback_ids
        if str(feedback_id).strip()
    }


FEEDBACK_CONTEXT_PAYLOAD_KEYS = (
    "feedback_id",
    "feedback_text",
    "author",
    "route_reason",
    "feedback_metadata",
    "target_artifact_selection",
    "target_artifact_count",
    "target_artifact_ids",
    "target_artifacts",
    "target_artifact_titles",
    "target_artifact_types",
    "target_artifact_source_ids",
    "target_artifact_claim_ids",
    "target_source_ids",
    "target_claim_ids",
)


def _feedback_context_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: payload[key]
        for key in FEEDBACK_CONTEXT_PAYLOAD_KEYS
        if key in payload and payload[key] not in (None, [], {})
    }


def _feedback_provenance_fields(feedback_context: dict[str, Any]) -> dict[str, Any]:
    if not feedback_context:
        return {}
    return {
        "feedback_id": feedback_context.get("feedback_id"),
        "feedback_text": feedback_context.get("feedback_text"),
        "feedback_metadata": feedback_context.get("feedback_metadata", {}),
        "target_artifact_selection": feedback_context.get(
            "target_artifact_selection"
        ),
        "target_artifact_ids": feedback_context.get("target_artifact_ids", []),
        "target_source_ids": feedback_context.get("target_source_ids", []),
        "target_claim_ids": feedback_context.get("target_claim_ids", []),
    }


def _forward_deployed_requirements_content(
    *,
    message: AgentMessage,
    feedback_items: list[FeedbackItem],
    context_summary: dict[str, Any],
) -> dict[str, Any]:
    requirements = []
    open_questions = []
    for index, feedback in enumerate(feedback_items, start=1):
        owner_agent_id = _feedback_requirement_owner(feedback)
        requirement = {
            "requirement_id": f"FDR-{index}",
            "source_feedback_id": str(feedback.feedback_id),
            "source_message_id": str(message.message_id),
            "author": feedback.author,
            "feedback_text": feedback.feedback_text,
            "owner_agent_id": owner_agent_id,
            "priority": _feedback_priority(feedback),
            "route_reason": _feedback_requirement_route_reason(feedback, owner_agent_id),
            "acceptance_criteria": _feedback_acceptance_criteria(
                feedback=feedback,
                owner_agent_id=owner_agent_id,
            ),
            "status": "ready_for_specialist",
            "metadata": feedback.metadata,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        requirements.append(requirement)
        if _feedback_needs_clarification(feedback.feedback_text):
            open_questions.append(
                {
                    "requirement_id": requirement["requirement_id"],
                    "question": (
                        "What exact before/after change should the specialist "
                        "optimize for?"
                    ),
                    "routed_to": "forward-deployed-engineer",
                }
            )

    owner_agent_ids = []
    for requirement in requirements:
        if requirement["owner_agent_id"] not in owner_agent_ids:
            owner_agent_ids.append(requirement["owner_agent_id"])
    return {
        "format": "feedback_requirements",
        "source_message_id": str(message.message_id),
        "task_type": message.task_type,
        "feedback_count": len(feedback_items),
        "requirements": requirements,
        "owner_agent_ids": owner_agent_ids,
        "open_questions": open_questions,
        "handoff_policy": {
            "specialist_tasks": "One task per requirement owner.",
            "note_task": "Interactive Note-Taking Agent receives the requirements artifact.",
            "progress_task": "Sprint/Progress Agent receives the requirements artifact.",
        },
        "context_summary": context_summary,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _feedback_requirement_owner(feedback: FeedbackItem) -> str:
    explicit = _feedback_metadata_string(
        feedback.metadata,
        "target_agent_id",
        "route_to",
        "agent_id",
    )
    if explicit and explicit != "forward-deployed-engineer":
        agent_id = explicit.strip()
        if get_agent_card(agent_id) is not None:
            return agent_id
    if feedback.target_agent_id and feedback.target_agent_id != "forward-deployed-engineer":
        if get_agent_card(feedback.target_agent_id) is not None:
            return feedback.target_agent_id

    focus = _feedback_metadata_string(feedback.metadata, "focus", "category", "area")
    if focus:
        focus_key = focus.lower().strip()
        if focus_key in FOCUS_AGENT_MAP:
            return FOCUS_AGENT_MAP[focus_key]
        for keyword, agent_id in FOCUS_AGENT_MAP.items():
            if keyword in focus_key:
                return agent_id

    searchable_text = _feedback_searchable_text(feedback)
    for keywords, agent_id in KEYWORD_AGENT_MAP:
        if any(keyword in searchable_text for keyword in keywords):
            return agent_id
    return "product-manager"


def _feedback_requirement_route_reason(
    feedback: FeedbackItem,
    owner_agent_id: str,
) -> str:
    focus = _feedback_metadata_string(feedback.metadata, "focus", "category", "area")
    if focus:
        return f"feedback_focus:{focus}"
    searchable_text = _feedback_searchable_text(feedback)
    for keywords, agent_id in KEYWORD_AGENT_MAP:
        if agent_id != owner_agent_id:
            continue
        for keyword in keywords:
            if keyword in searchable_text:
                return f"feedback_keyword:{keyword}"
    if feedback.target_agent_id and feedback.target_agent_id == owner_agent_id:
        return "feedback_target_agent"
    return "feedback_default_owner"


def _feedback_priority(feedback: FeedbackItem) -> str:
    priority = _feedback_metadata_string(feedback.metadata, "priority", "severity")
    if priority:
        priority_key = priority.lower().strip()
        if priority_key in {"low", "medium", "high", "critical"}:
            return priority_key
    text = feedback.feedback_text.lower()
    if any(term in text for term in ["blocked", "broken", "cannot", "urgent"]):
        return "high"
    if any(term in text for term in ["nice to have", "later", "minor"]):
        return "low"
    return "medium"


def _feedback_acceptance_criteria(
    *,
    feedback: FeedbackItem,
    owner_agent_id: str,
) -> list[str]:
    agent = get_agent_card(owner_agent_id)
    owner_name = agent.name if agent else owner_agent_id
    return [
        f"{owner_name} has a concrete next-pass task linked to this feedback.",
        "The feedback text is preserved verbatim in durable run state.",
        "The resulting artifact, event, or reviewer decision references the requirement id.",
        "If the request is ambiguous, an open question is recorded before autonomous continuation.",
    ]


def _feedback_needs_clarification(feedback_text: str) -> bool:
    text = feedback_text.strip().lower()
    if len(text) < 32:
        return True
    vague_terms = {"better", "improve", "polish", "nice", "good", "bad"}
    specific_terms = {"because", "so that", "with", "without", "instead", "must"}
    return any(term in text for term in vague_terms) and not any(
        term in text for term in specific_terms
    )


def _feedback_metadata_string(metadata: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _feedback_searchable_text(feedback: FeedbackItem) -> str:
    metadata_values = [
        str(value)
        for value in feedback.metadata.values()
        if isinstance(value, str)
    ]
    return " ".join([feedback.feedback_text, *metadata_values]).lower()


def _principal_architecture_review_content(
    *,
    run,
    messages: list[AgentMessage],
    events: list[RunEvent],
    artifacts: list[ArtifactRecord],
    sources: list[SourceRecord],
    claims: list[ClaimRecord],
    feedback_items,
    guardrail_audits,
    checkpoints,
    worker_profiles,
    realtime_sessions,
    context_summary: dict[str, Any],
    scope: str,
    review_agent_id: str = "principal-software-engineer",
    review_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = review_profile or ARCHITECTURE_REVIEW_AGENT_PROFILES[
        "principal-software-engineer"
    ]
    artifact_type_counts = _value_counts(
        artifact.artifact_type.value for artifact in artifacts
    )
    event_type_counts = _value_counts(event.event_type for event in events)
    task_status_counts = _value_counts(message.status.value for message in messages)
    open_feedback = [
        feedback
        for feedback in feedback_items
        if feedback.status in {FeedbackStatus.OPEN, FeedbackStatus.ROUTED}
    ]
    blocked_messages = [
        message
        for message in messages
        if message.status in {AgentTaskStatus.BLOCKED, AgentTaskStatus.FAILED}
    ]
    publishable_artifacts = [
        artifact
        for artifact in artifacts
        if artifact.artifact_type in EDITORIAL_REVIEW_ARTIFACT_TYPES
    ]
    architecture_artifacts = {
        "source_ledger": artifact_type_counts.get(ArtifactType.SOURCE_LEDGER.value, 0),
        "context_packet": artifact_type_counts.get(ArtifactType.CONTEXT_PACKET.value, 0),
        "run_resume_plan": artifact_type_counts.get(
            ArtifactType.RUN_RESUME_PLAN.value, 0
        ),
        "artifact_index": artifact_type_counts.get(ArtifactType.ARTIFACT_INDEX.value, 0),
        "feedback_requirements": artifact_type_counts.get(
            ArtifactType.FEEDBACK_REQUIREMENTS.value, 0
        ),
        "run_health_report": artifact_type_counts.get(
            ArtifactType.RUN_HEALTH_REPORT.value, 0
        ),
    }
    concrete_worker_ids = list(DEFAULT_WORKER_AGENT_IDS)
    concrete_worker_executor_ids = sorted(CONCRETE_WORKER_EXECUTOR_AGENT_IDS)
    roster_agent_ids = [agent.id for agent in AGENT_ROSTER]
    non_worker_agent_ids = [
        agent_id for agent_id in roster_agent_ids if agent_id not in concrete_worker_ids
    ]
    generic_fallback_only_agent_ids = [
        agent_id
        for agent_id in roster_agent_ids
        if agent_id not in CONCRETE_WORKER_EXECUTOR_AGENT_IDS
    ]
    expected_non_worker_boundaries = {
        "realtime-conversation-host": "realtime_surface_api",
        "intent-router": "conversation_routing_api",
        "image-generation-agent": "imagegen_tool_boundary",
    }
    remaining_worker_gaps = [
        agent_id
        for agent_id in sorted(set(non_worker_agent_ids + generic_fallback_only_agent_ids))
        if agent_id not in expected_non_worker_boundaries
    ]

    risk_register = []
    _append_architecture_risk(
        risk_register,
        condition=not checkpoints,
        severity="high",
        risk_type="missing_checkpoint",
        detail="No durable run checkpoint has been recorded for restart recovery.",
        owner_agent_id="agent-harness-engineer",
    )
    _append_architecture_risk(
        risk_register,
        condition=not worker_profiles,
        severity="medium",
        risk_type="no_worker_profile",
        detail="No saved worker profile exists for always-on local execution.",
        owner_agent_id="agent-harness-engineer",
    )
    _append_architecture_risk(
        risk_register,
        condition=bool(open_feedback),
        severity="high",
        risk_type="open_feedback_gate",
        detail="Open or routed human feedback must be resolved or converted into requirements before autonomous publishing.",
        owner_agent_id="forward-deployed-engineer",
        metadata={"feedback_ids": [str(feedback.feedback_id) for feedback in open_feedback]},
    )
    _append_architecture_risk(
        risk_register,
        condition=bool(blocked_messages),
        severity="high",
        risk_type="blocked_agent_tasks",
        detail="Failed or blocked A2A messages need triage before the run is considered healthy.",
        owner_agent_id="observability-agent",
        metadata={
            "message_ids": [str(message.message_id) for message in blocked_messages]
        },
    )
    _append_architecture_risk(
        risk_register,
        condition=publishable_artifacts and not guardrail_audits,
        severity="high",
        risk_type="missing_guardrail_audit",
        detail="Publishable artifacts exist without a guardrail audit.",
        owner_agent_id="guardrails-agent",
    )
    _append_architecture_risk(
        risk_register,
        condition=publishable_artifacts and not architecture_artifacts["source_ledger"],
        severity="medium",
        risk_type="missing_source_ledger_snapshot",
        detail="Publishable artifacts should have a current source ledger snapshot.",
        owner_agent_id="source-ledger-agent",
    )
    _append_architecture_risk(
        risk_register,
        condition=not architecture_artifacts["context_packet"],
        severity="medium",
        risk_type="missing_context_packet",
        detail="No reusable context packet is available for resumed specialist work.",
        owner_agent_id="context-engineering-agent",
    )
    _append_architecture_risk(
        risk_register,
        condition=not architecture_artifacts["artifact_index"],
        severity="medium",
        risk_type="missing_artifact_index",
        detail="No artifact index exists for retrieval facets and provenance graph inspection.",
        owner_agent_id="artifact-librarian",
    )
    _append_architecture_risk(
        risk_register,
        condition=not realtime_sessions,
        severity="medium",
        risk_type="no_realtime_session",
        detail="No realtime session has been recorded for voice dialogue verification.",
        owner_agent_id="realtime-conversation-host",
    )
    _append_architecture_risk(
        risk_register,
        condition=bool(remaining_worker_gaps),
        severity="medium",
        risk_type="remaining_worker_gaps",
        detail="Some named specialist agents still need concrete durable worker execution.",
        owner_agent_id="principal-software-engineer",
        metadata={"agent_ids": remaining_worker_gaps},
    )
    _append_architecture_risk(
        risk_register,
        condition=event_type_counts.get("provider_fallback", 0) > 0,
        severity="medium",
        risk_type="provider_fallbacks",
        detail="Provider fallback events should be reviewed before assuming live model/tool readiness.",
        owner_agent_id="observability-agent",
        metadata={"provider_fallback_count": event_type_counts.get("provider_fallback", 0)},
    )

    findings = _principal_architecture_findings(
        risk_register=risk_register,
        architecture_artifacts=architecture_artifacts,
        concrete_worker_ids=concrete_worker_ids,
        realtime_sessions=realtime_sessions,
    )
    health_status = _principal_architecture_health_status(risk_register)
    return {
        "format": "architecture_review",
        "review_agent_id": review_agent_id,
        "review_profile": profile["summary_label"],
        "specialist_focus": profile["focus"],
        "scope": scope,
        "health_status": health_status,
        "locked_decisions": [
            {
                "decision": "Postgres plus pgvector is the only durable local store.",
                "status": "locked",
            },
            {
                "decision": "LangGraph-style checkpoints and event logs are required for resumable long-running work.",
                "status": "locked",
            },
            {
                "decision": "Realtime providers own voice transport while Gemma 4/HF cloud owns specialist reasoning.",
                "status": "locked",
            },
            {
                "decision": "imagegen is a raster asset tool boundary, not a hidden backend network provider.",
                "status": "locked",
            },
            {
                "decision": "Planning HTML remains separate from the product cockpit.",
                "status": "locked",
            },
        ],
        "run_inventory": {
            "run_id": str(run.run_id),
            "status": run.status.value,
            "sources": len(sources),
            "claims": len(claims),
            "artifacts": len(artifacts),
            "events": len(events),
            "agent_messages": len(messages),
            "feedback_items": len(feedback_items),
            "guardrail_audits": len(guardrail_audits),
            "checkpoints": len(checkpoints),
            "worker_profiles": len(worker_profiles),
            "realtime_sessions": len(realtime_sessions),
        },
        "agent_coverage": {
            "roster_agent_count": len(AGENT_ROSTER),
            "default_worker_agent_count": len(concrete_worker_ids),
            "default_worker_agent_ids": concrete_worker_ids,
            "concrete_worker_executor_count": len(concrete_worker_executor_ids),
            "concrete_worker_executor_agent_ids": concrete_worker_executor_ids,
            "generic_fallback_only_agent_ids": generic_fallback_only_agent_ids,
            "non_worker_agent_ids": non_worker_agent_ids,
            "expected_non_worker_boundaries": expected_non_worker_boundaries,
            "remaining_worker_gaps": remaining_worker_gaps,
            "skill_count": len(SKILL_CARDS),
        },
        "provider_boundaries": {
            "gemma_reasoning_agents": [
                agent.id
                for agent in AGENT_ROSTER
                if any(model.startswith("gemma-4") for model in agent.allowed_models)
            ],
            "realtime_audio_agents": [
                agent.id
                for agent in AGENT_ROSTER
                if "realtime-audio-provider" in agent.allowed_models
            ],
            "imagegen_tool_agents": [
                agent.id for agent in AGENT_ROSTER if "imagegen" in agent.allowed_tools
            ],
        },
        "architecture_artifacts": architecture_artifacts,
        "event_type_counts": event_type_counts,
        "task_status_counts": task_status_counts,
        "artifact_type_counts": artifact_type_counts,
        "findings": findings,
        "risk_register": risk_register,
        "recommended_next_actions": _principal_architecture_next_actions(risk_register),
        "context_summary": context_summary,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }


def _append_architecture_risk(
    risks: list[dict[str, Any]],
    *,
    condition: bool,
    severity: str,
    risk_type: str,
    detail: str,
    owner_agent_id: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    if not condition:
        return
    risks.append(
        {
            "risk_type": risk_type,
            "severity": severity,
            "detail": detail,
            "owner_agent_id": owner_agent_id,
            "metadata": metadata or {},
        }
    )


def _principal_architecture_findings(
    *,
    risk_register: list[dict[str, Any]],
    architecture_artifacts: dict[str, int],
    concrete_worker_ids: list[str],
    realtime_sessions,
) -> list[dict[str, Any]]:
    return [
        {
            "finding_type": "durable_worker_coverage",
            "status": "needs_review"
            if any(risk["risk_type"] == "remaining_worker_gaps" for risk in risk_register)
            else "healthy",
            "detail": (
                f"{len(concrete_worker_ids)} specialist agents are in the default "
                "worker cycle."
            ),
        },
        {
            "finding_type": "context_and_resume_harness",
            "status": (
                "healthy"
                if architecture_artifacts["context_packet"]
                and architecture_artifacts["run_resume_plan"]
                else "needs_review"
            ),
            "detail": "Context packet and resume-plan artifacts are the core restart path.",
        },
        {
            "finding_type": "artifact_retrieval",
            "status": "healthy"
            if architecture_artifacts["artifact_index"]
            else "needs_review",
            "detail": "Artifact index gives long-running agents retrieval and provenance facets.",
        },
        {
            "finding_type": "voice_surface",
            "status": "healthy" if realtime_sessions else "needs_review",
            "detail": "Realtime sessions prove the voice/text dialogue surface is exercised.",
        },
    ]


def _principal_architecture_health_status(
    risk_register: list[dict[str, Any]],
) -> str:
    severities = {risk["severity"] for risk in risk_register}
    if "high" in severities:
        return "blocked"
    if risk_register:
        return "needs_attention"
    return "healthy"


def _principal_architecture_next_actions(
    risk_register: list[dict[str, Any]],
) -> list[str]:
    if not risk_register:
        return ["Continue autonomous worker passes and refresh architecture review after each major slice."]
    action_by_risk_type = {
        "missing_checkpoint": "Ask Agent Harness Engineer to record a checkpointed resume plan.",
        "no_worker_profile": "Create and start a worker profile for the run.",
        "open_feedback_gate": "Ask Forward Deployed Engineer to convert open feedback into requirements or resolve the gate.",
        "blocked_agent_tasks": "Ask Observability Agent to triage blocked or failed A2A messages.",
        "missing_guardrail_audit": "Run Guardrails Agent before publish readiness.",
        "missing_source_ledger_snapshot": "Run Source Ledger Agent snapshot.",
        "missing_context_packet": "Run Context Engineering Agent for a reusable context packet.",
        "missing_artifact_index": "Run Artifact Librarian index worker.",
        "no_realtime_session": "Start a realtime voice/text session and record at least one turn.",
        "remaining_worker_gaps": "Implement concrete workers for remaining named specialist agents.",
        "provider_fallbacks": "Review provider readiness and configure missing live providers.",
    }
    actions = []
    for risk in risk_register:
        action = action_by_risk_type.get(risk["risk_type"])
        if action and action not in actions:
            actions.append(action)
    return actions


def _ux_review_content(
    *,
    run,
    message: AgentMessage,
    events: list[RunEvent],
    artifacts: list[ArtifactRecord],
    feedback_items,
    messages: list[AgentMessage],
    realtime_sessions,
    context_summary: dict[str, Any],
    review_agent_id: str = "lead-ui-ux-designer",
    review_profile: dict[str, str] | None = None,
) -> dict[str, Any]:
    profile = review_profile or UX_REVIEW_AGENT_PROFILES["lead-ui-ux-designer"]
    surface_scope = str(message.payload.get("surface_scope") or "cockpit_and_planning")
    event_type_counts = _value_counts(event.event_type for event in events)
    artifact_type_counts = _value_counts(
        artifact.artifact_type.value for artifact in artifacts
    )
    open_feedback = [
        feedback
        for feedback in feedback_items
        if feedback.status in {FeedbackStatus.OPEN, FeedbackStatus.ROUTED}
    ]
    ux_feedback = [
        feedback
        for feedback in feedback_items
        if (
            feedback.target_agent_id == "lead-ui-ux-designer"
            or str(feedback.metadata.get("focus", "")).lower() in {"ui", "ux", "design"}
            or any(
                keyword in feedback.feedback_text.lower()
                for keyword in ["ui", "ux", "cockpit", "layout", "interface"]
            )
        )
    ]
    findings = [
        {
            "finding_type": "surface_boundary",
            "status": "healthy",
            "detail": (
                "Product cockpit and animated planning HTML remain separate "
                "surfaces in the run contract."
            ),
        },
        {
            "finding_type": "realtime_controls",
            "status": "healthy" if realtime_sessions else "needs_review",
            "detail": (
                "Realtime session state is visible for voice controls."
                if realtime_sessions
                else "No realtime session is present; voice controls need a live-session check."
            ),
        },
        {
            "finding_type": "source_and_artifact_visibility",
            "status": (
                "healthy"
                if artifacts and artifact_type_counts.get(ArtifactType.SOURCE_LEDGER.value, 0)
                else "needs_review"
            ),
            "detail": (
                "Source ledger and artifacts are available for review."
                if artifacts and artifact_type_counts.get(ArtifactType.SOURCE_LEDGER.value, 0)
                else "The cockpit should make missing source-ledger context obvious."
            ),
        },
        {
            "finding_type": "feedback_affordance",
            "status": "needs_review" if open_feedback else "healthy",
            "detail": (
                f"{len(open_feedback)} open/routed feedback item(s) need clear status."
                if open_feedback
                else "No unresolved feedback is blocking the current UX flow."
            ),
        },
    ]
    ux_risks = []
    _append_ux_risk(
        ux_risks,
        condition=not realtime_sessions,
        risk_type="unverified_voice_controls",
        severity="medium",
        detail="Voice controls have not been exercised in a realtime session for this run.",
        owner_agent_id="realtime-conversation-host",
    )
    _append_ux_risk(
        ux_risks,
        condition=bool(open_feedback),
        risk_type="unclear_feedback_state",
        severity="medium",
        detail="Open or routed feedback needs visible ownership and next action.",
        owner_agent_id="forward-deployed-engineer",
        metadata={"feedback_ids": [str(feedback.feedback_id) for feedback in open_feedback]},
    )
    _append_ux_risk(
        ux_risks,
        condition=not artifact_type_counts.get(ArtifactType.SOURCE_LEDGER.value, 0),
        risk_type="source_context_not_visible",
        severity="medium",
        detail="No source ledger artifact exists for cockpit source visibility.",
        owner_agent_id="source-ledger-agent",
    )
    _append_ux_risk(
        ux_risks,
        condition=not artifact_type_counts.get(ArtifactType.ARTIFACT_INDEX.value, 0),
        risk_type="artifact_navigation_not_indexed",
        severity="low",
        detail="No artifact index exists to power scan-friendly artifact navigation.",
        owner_agent_id="artifact-librarian",
    )
    _append_ux_risk(
        ux_risks,
        condition=not ux_feedback and message.task_type == "incorporate_feedback_requirement",
        risk_type="missing_specific_ux_feedback",
        severity="low",
        detail="UX review was requested without explicit UI/UX feedback text.",
        owner_agent_id="lead-ui-ux-designer",
    )
    return {
        "format": "ux_review",
        "review_agent_id": review_agent_id,
        "review_profile": profile["summary_label"],
        "surface_scope": surface_scope,
        "run_id": str(run.run_id),
        "run_status": run.status.value,
        "surface_inventory": {
            "product_cockpit": "frontend/cockpit/index.html",
            "planning_workspace": "planning/foundation-system-design.html",
            "boundary": "Planning HTML is separate from the product cockpit.",
        },
        "interaction_inventory": {
            "conversation_events": event_type_counts.get("conversation_turn_recorded", 0),
            "voice_turn_events": event_type_counts.get("realtime_turn_recorded", 0),
            "realtime_sessions": len(realtime_sessions),
            "agent_messages": len(messages),
            "open_feedback": len(open_feedback),
        },
        "artifact_visibility": {
            "artifact_count": len(artifacts),
            "artifact_type_counts": artifact_type_counts,
            "has_source_ledger": bool(
                artifact_type_counts.get(ArtifactType.SOURCE_LEDGER.value, 0)
            ),
            "has_artifact_index": bool(
                artifact_type_counts.get(ArtifactType.ARTIFACT_INDEX.value, 0)
            ),
            "has_feedback_requirements": bool(
                artifact_type_counts.get(ArtifactType.FEEDBACK_REQUIREMENTS.value, 0)
            ),
        },
        "findings": findings,
        "ux_risks": ux_risks,
        "feedback_inputs": [
            {
                "feedback_id": str(feedback.feedback_id),
                "status": feedback.status.value,
                "target_agent_id": feedback.target_agent_id,
                "feedback_text": feedback.feedback_text,
                "metadata": feedback.metadata,
            }
            for feedback in ux_feedback
        ],
        "recommended_next_actions": _ux_review_next_actions(ux_risks),
        "context_summary": context_summary,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }


def _append_ux_risk(
    risks: list[dict[str, Any]],
    *,
    condition: bool,
    risk_type: str,
    severity: str,
    detail: str,
    owner_agent_id: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    if not condition:
        return
    risks.append(
        {
            "risk_type": risk_type,
            "severity": severity,
            "detail": detail,
            "owner_agent_id": owner_agent_id,
            "metadata": metadata or {},
        }
    )


def _ux_review_next_actions(ux_risks: list[dict[str, Any]]) -> list[str]:
    if not ux_risks:
        return ["Keep cockpit interactions stable and refresh UX review after the next surface change."]
    action_by_risk = {
        "unverified_voice_controls": "Start a realtime session and verify voice turn controls in the cockpit.",
        "unclear_feedback_state": "Show feedback owner, status, and next action in the cockpit timeline.",
        "source_context_not_visible": "Run Source Ledger Agent so source coverage is visible beside drafts.",
        "artifact_navigation_not_indexed": "Run Artifact Librarian so artifact browsing can use retrieval facets.",
        "missing_specific_ux_feedback": "Ask the user for concrete UI/UX before/after feedback.",
    }
    actions = []
    for risk in ux_risks:
        action = action_by_risk.get(risk["risk_type"])
        if action and action not in actions:
            actions.append(action)
    return actions


def _interactive_systems_review_content(
    *,
    surface_path: Path,
    events: list[RunEvent],
    artifacts: list[ArtifactRecord],
    feedback_items,
    context_summary: dict[str, Any],
) -> dict[str, Any]:
    inventory = _planning_surface_inventory(surface_path)
    embedded_state = {
        "has_foundation_data": inventory["has_foundation_data"],
        "section_keys": inventory["data_keys"],
        "agent_count": inventory["agent_count"],
        "worker_executor_count": inventory["worker_executor_count"],
        "planning_progress_item_count": inventory["planning_progress_item_count"],
        "decision_count": inventory["data_counts"].get("decisions", 0),
        "data_counts": inventory["data_counts"],
        "parse_error": inventory["parse_error"],
    }
    interaction_inventory = {
        "suggestion_capture": inventory["feature_flags"]["suggestion_capture"],
        "progress_tracker": inventory["feature_flags"]["progress_tracker"],
        "drag_drop": inventory["feature_flags"]["drag_progress"],
        "export_packet": inventory["feature_flags"]["export_packet"],
        "animation": inventory["feature_flags"]["animation"],
    }
    interaction_inventory["interactive_control_count"] = sum(
        1 for value in interaction_inventory.values() if value is True
    )
    boundary_checks = _planning_surface_boundary_checks(inventory)
    event_type_counts = _value_counts(event.event_type for event in events)
    artifact_type_counts = _value_counts(
        artifact.artifact_type.value for artifact in artifacts
    )
    planning_feedback = [
        feedback
        for feedback in feedback_items
        if (
            feedback.target_agent_id == "interactive-systems-designer"
            or str(feedback.metadata.get("focus", "")).lower() == "planning"
            or "planning html" in feedback.feedback_text.lower()
            or "system design" in feedback.feedback_text.lower()
        )
    ]
    findings = [
        {
            "finding_type": "surface_boundary",
            "status": (
                "healthy"
                if inventory["exists"]
                and _boundary_status(boundary_checks, "product_app_separation")
                == "healthy"
                else "blocked"
            ),
            "detail": (
                "Planning HTML exists as a standalone artifact outside the product app."
                if inventory["exists"]
                else "Planning HTML file is missing."
            ),
        },
        {
            "finding_type": "embedded_state",
            "status": "healthy" if inventory["has_foundation_data"] else "blocked",
            "detail": (
                "Embedded foundation-data JSON is available for agent reuse."
                if inventory["has_foundation_data"]
                else "Embedded foundation-data JSON could not be parsed."
            ),
        },
        {
            "finding_type": "progress_surface",
            "status": (
                "healthy"
                if inventory["data_counts"].get("planningProgressItems", 0) > 0
                else "needs_review"
            ),
            "detail": "Planning progress tracker exists and exports structured state.",
        },
        {
            "finding_type": "suggestion_capture",
            "status": (
                "healthy"
                if inventory["feature_flags"]["suggestion_capture"]
                else "needs_review"
            ),
            "detail": "Planning suggestions can be captured locally and exported.",
        },
        {
            "finding_type": "worker_executor_map",
            "status": (
                "healthy"
                if inventory["data_counts"].get("workerExecutors", 0) >= 20
                else "needs_review"
            ),
            "detail": "Worker executor map reflects the durable agent harness slices.",
        },
    ]
    risks = []
    _append_interactive_system_risk(
        risks,
        condition=not inventory["exists"],
        risk_type="planning_surface_missing",
        severity="high",
        detail="The standalone planning HTML artifact is missing.",
    )
    _append_interactive_system_risk(
        risks,
        condition=not inventory["has_foundation_data"],
        risk_type="embedded_state_missing",
        severity="high",
        detail="The planning surface lacks parseable embedded JSON state.",
    )
    _append_interactive_system_risk(
        risks,
        condition=not inventory["feature_flags"]["drag_progress"],
        risk_type="progress_drag_not_detected",
        severity="medium",
        detail="The local planning progress tracker drag affordance was not detected.",
    )
    _append_interactive_system_risk(
        risks,
        condition=not inventory["feature_flags"]["export_packet"],
        risk_type="export_packet_missing",
        severity="medium",
        detail="The planning surface export packet affordance was not detected.",
    )
    _append_interactive_system_risk(
        risks,
        condition=(
            _boundary_status(boundary_checks, "product_app_separation") != "healthy"
        ),
        risk_type="product_boundary_unclear",
        severity="high",
        detail="The planning surface does not clearly state that it is separate from the product app.",
    )
    _append_interactive_system_risk(
        risks,
        condition=(
            _boundary_status(boundary_checks, "durable_store_decision") != "healthy"
        ),
        risk_type="durability_decision_unclear",
        severity="medium",
        detail="The planning surface does not clearly preserve the Postgres plus pgvector durability decision.",
    )
    _append_interactive_system_risk(
        risks,
        condition=bool(planning_feedback),
        risk_type="open_planning_feedback",
        severity="medium",
        detail="Planning feedback is present and should be reflected in the next surface revision.",
        metadata={
            "feedback_ids": [
                str(feedback.feedback_id) for feedback in planning_feedback
            ]
        },
    )
    return {
        "format": "planning_surface_review",
        "surface_scope": "separate_planning_html",
        "surface_path": str(surface_path),
        "surface_inventory": inventory,
        "embedded_state": embedded_state,
        "interaction_inventory": interaction_inventory,
        "boundary_checks": boundary_checks,
        "run_state_links": {
            "event_count": len(events),
            "artifact_count": len(artifacts),
            "planning_feedback_count": len(planning_feedback),
            "event_type_counts": event_type_counts,
            "artifact_type_counts": artifact_type_counts,
        },
        "findings": findings,
        "risks": risks,
        "planning_risks": risks,
        "planning_feedback": [
            {
                "feedback_id": str(feedback.feedback_id),
                "status": feedback.status.value,
                "feedback_text": feedback.feedback_text,
                "metadata": feedback.metadata,
            }
            for feedback in planning_feedback
        ],
        "recommended_next_actions": _interactive_system_next_actions(risks),
        "context_summary": context_summary,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }


def _planning_surface_inventory(surface_path: Path) -> dict[str, Any]:
    html = ""
    exists = surface_path.exists()
    if exists:
        html = surface_path.read_text(encoding="utf-8")
    data = {}
    parse_error = None
    marker = '<script id="foundation-data" type="application/json">'
    if marker in html:
        try:
            data_blob = html.split(marker, 1)[1].split("</script>", 1)[0]
            data = json.loads(data_blob)
        except (IndexError, json.JSONDecodeError) as exc:
            parse_error = str(exc)
    feature_flags = {
        "suggestion_capture": "planning-feedback-form" in html
        or "planning-feedback-export" in html,
        "progress_tracker": "planning-progress-board" in html,
        "drag_progress": "draggable = true" in html and "dataTransfer.setData" in html,
        "export_packet": "planning-progress-export" in html
        and "agent-studio-planning-progress-v1" in html,
        "animation": "@keyframes" in html or "Animated foundation map" in html,
        "animated_diagram": "Animated foundation map" in html,
        "product_boundary_text": (
            "separate planning workspace" in html
            and "not part of the product app" in html
        ),
        "durable_store_decision": "No SQLite" in html and "pgvector" in html,
    }
    data_counts = {
        key: len(value)
        for key, value in data.items()
        if isinstance(value, list)
    }
    return {
        "planning_artifact_path": str(surface_path),
        "product_cockpit_path": "frontend/cockpit/index.html",
        "boundary": "Planning workspace is separate from product cockpit.",
        "exists": exists,
        "html_bytes": len(html.encode("utf-8")),
        "has_foundation_data": bool(data),
        "parse_error": parse_error,
        "data_keys": sorted(data.keys()),
        "data_counts": data_counts,
        "decision_titles": [
            item.get("title")
            for item in data.get("decisions", [])
            if isinstance(item, dict)
        ],
        "agent_count": len(data.get("agents", [])),
        "worker_executor_count": len(data.get("workerExecutors", [])),
        "planning_progress_item_count": len(data.get("planningProgressItems", [])),
        "feature_flags": feature_flags,
    }


def _planning_surface_boundary_checks(
    inventory: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        {
            "check_type": "product_app_separation",
            "status": (
                "healthy"
                if inventory["exists"]
                and inventory["feature_flags"]["product_boundary_text"]
                else "needs_review"
            ),
            "detail": "Planning workspace is explicitly separate from the product app.",
        },
        {
            "check_type": "durable_store_decision",
            "status": (
                "healthy"
                if inventory["feature_flags"]["durable_store_decision"]
                else "needs_review"
            ),
            "detail": "Postgres plus pgvector remains the locked durability baseline.",
        },
        {
            "check_type": "embedded_state_available",
            "status": "healthy" if inventory["has_foundation_data"] else "blocked",
            "detail": "Embedded foundation-data JSON is available for future planning iterations.",
        },
    ]


def _boundary_status(
    boundary_checks: list[dict[str, str]],
    check_type: str,
) -> str | None:
    for check in boundary_checks:
        if check["check_type"] == check_type:
            return check["status"]
    return None


def _append_interactive_system_risk(
    risks: list[dict[str, Any]],
    *,
    condition: bool,
    risk_type: str,
    severity: str,
    detail: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    if not condition:
        return
    risks.append(
        {
            "risk_type": risk_type,
            "severity": severity,
            "detail": detail,
            "owner_agent_id": "interactive-systems-designer",
            "metadata": metadata or {},
        }
    )


def _interactive_system_next_actions(risks: list[dict[str, Any]]) -> list[str]:
    if not risks:
        return ["Refresh the planning surface after the next durable worker slice lands."]
    action_by_risk = {
        "planning_surface_missing": "Recreate the standalone planning HTML artifact.",
        "embedded_state_missing": "Restore parseable embedded foundation-data JSON.",
        "progress_drag_not_detected": "Restore local drag/drop progress movement in the planning surface.",
        "export_packet_missing": "Restore structured planning export packets for agent handoff.",
        "product_boundary_unclear": "Clarify that the planning workspace is not part of the product app.",
        "durability_decision_unclear": "Restore the Postgres plus pgvector durability decision in the planning state.",
        "open_planning_feedback": "Incorporate planning feedback into the next planning HTML revision.",
    }
    actions = []
    for risk in risks:
        action = action_by_risk.get(risk["risk_type"])
        if action and action not in actions:
            actions.append(action)
    return actions


def _artifact_librarian_index_content(
    *,
    artifacts: list[ArtifactRecord],
    sources: list[SourceRecord],
    claims: list[ClaimRecord],
    events: list[RunEvent],
    messages: list[AgentMessage],
    feedback_items,
    guardrail_audits,
) -> dict[str, Any]:
    source_by_id = {source.source_id: source for source in sources}
    claim_by_id = {claim.claim_id: claim for claim in claims}
    artifact_ids = {str(artifact.artifact_id) for artifact in artifacts}
    entries = []
    dependency_edges = []
    provenance_gaps = []
    latest_artifact = max(
        artifacts,
        key=lambda artifact: artifact.created_at,
        default=None,
    )

    for artifact in artifacts:
        claim_ids = _extract_artifact_claim_ids(artifact)
        workflow = artifact.provenance.get("workflow")
        agent_id = artifact.provenance.get("agent_id")
        parent_artifact_id = artifact.provenance.get("parent_artifact_id")
        missing_source_ids = [
            source_id for source_id in artifact.source_ids if source_id not in source_by_id
        ]
        missing_claim_ids = [
            claim_id for claim_id in claim_ids if claim_id not in claim_by_id
        ]
        source_citation_ids = [
            source_by_id[source_id].citation_id
            for source_id in artifact.source_ids
            if source_id in source_by_id
        ]
        entry = {
            "artifact_id": str(artifact.artifact_id),
            "artifact_type": artifact.artifact_type.value,
            "title": artifact.title,
            "uri": artifact.uri,
            "workflow": workflow or "unknown",
            "agent_id": agent_id or "unknown",
            "generation_mode": artifact.provenance.get("generation_mode", "unknown"),
            "parent_artifact_id": str(parent_artifact_id) if parent_artifact_id else None,
            "source_ids": [str(source_id) for source_id in artifact.source_ids],
            "source_citation_ids": source_citation_ids,
            "claim_ids": [str(claim_id) for claim_id in claim_ids],
            "missing_source_ids": [str(source_id) for source_id in missing_source_ids],
            "missing_claim_ids": [str(claim_id) for claim_id in missing_claim_ids],
            "reviewer_decision_count": len(artifact.reviewer_decisions),
            "revision_count": len(artifact.revision_history),
            "content_keys": sorted(str(key) for key in artifact.content.keys()),
            "created_at": artifact.created_at.isoformat(),
        }
        entries.append(entry)

        for source_id in artifact.source_ids:
            dependency_edges.append(
                {
                    "edge_type": "artifact_source",
                    "from_artifact_id": str(artifact.artifact_id),
                    "to_source_id": str(source_id),
                    "status": "linked" if source_id in source_by_id else "missing",
                }
            )
        for claim_id in claim_ids:
            dependency_edges.append(
                {
                    "edge_type": "artifact_claim",
                    "from_artifact_id": str(artifact.artifact_id),
                    "to_claim_id": str(claim_id),
                    "status": "linked" if claim_id in claim_by_id else "missing",
                }
            )
        if parent_artifact_id:
            dependency_edges.append(
                {
                    "edge_type": "artifact_revision_parent",
                    "from_artifact_id": str(artifact.artifact_id),
                    "to_artifact_id": str(parent_artifact_id),
                    "status": (
                        "linked"
                        if str(parent_artifact_id) in artifact_ids
                        else "missing"
                    ),
                }
            )
        for decision in artifact.reviewer_decisions:
            reviewer_agent_id = (
                decision.get("reviewer_agent_id")
                or decision.get("agent_id")
                or decision.get("reviewer")
            )
            if reviewer_agent_id:
                dependency_edges.append(
                    {
                        "edge_type": "artifact_reviewer",
                        "from_artifact_id": str(artifact.artifact_id),
                        "to_agent_id": str(reviewer_agent_id),
                        "status": decision.get("status", "recorded"),
                    }
                )

        if not workflow:
            provenance_gaps.append(
                _artifact_provenance_gap(
                    artifact,
                    "missing_workflow",
                    "Artifact provenance does not name the generating workflow.",
                )
            )
        if not agent_id:
            provenance_gaps.append(
                _artifact_provenance_gap(
                    artifact,
                    "missing_agent_id",
                    "Artifact provenance does not name the responsible agent.",
                )
            )
        if missing_source_ids:
            provenance_gaps.append(
                _artifact_provenance_gap(
                    artifact,
                    "missing_source_record",
                    "Artifact references source ids that are not in the current ledger.",
                )
            )
        if missing_claim_ids:
            provenance_gaps.append(
                _artifact_provenance_gap(
                    artifact,
                    "missing_claim_record",
                    "Artifact references claim ids that are not in the current claim table.",
                )
            )
        if artifact.artifact_type in SOURCE_DEPENDENT_ARTIFACT_TYPES and not artifact.source_ids:
            provenance_gaps.append(
                _artifact_provenance_gap(
                    artifact,
                    "missing_source_dependencies",
                    "Source-dependent artifact has no source dependencies.",
                )
            )
        if artifact.artifact_type in SOURCE_CONTENT_TYPES and not claim_ids:
            provenance_gaps.append(
                _artifact_provenance_gap(
                    artifact,
                    "missing_claim_dependencies",
                    "Publishable draft has no claim dependencies.",
                )
            )
        if parent_artifact_id and str(parent_artifact_id) not in artifact_ids:
            provenance_gaps.append(
                _artifact_provenance_gap(
                    artifact,
                    "missing_parent_artifact",
                    "Artifact revision points to a parent artifact that is not indexed.",
                )
            )

    source_linked_artifact_count = sum(1 for entry in entries if entry["source_ids"])
    claim_linked_artifact_count = sum(1 for entry in entries if entry["claim_ids"])
    reviewed_artifact_count = sum(
        1 for entry in entries if entry["reviewer_decision_count"] > 0
    )
    recommended_actions = _artifact_librarian_recommended_actions(
        artifact_count=len(entries),
        provenance_gaps=provenance_gaps,
        entries=entries,
    )
    publishing_handoff = _artifact_librarian_publishing_handoff(
        artifacts=artifacts,
        sources=sources,
        claims=claims,
        events=events,
        feedback_items=feedback_items,
        guardrail_audits=guardrail_audits,
    )
    return {
        "format": "artifact_index",
        "artifact_count": len(entries),
        "source_count": len(sources),
        "claim_count": len(claims),
        "event_count": len(events),
        "message_count": len(messages),
        "source_linked_artifact_count": source_linked_artifact_count,
        "claim_linked_artifact_count": claim_linked_artifact_count,
        "reviewed_artifact_count": reviewed_artifact_count,
        "artifact_type_counts": _value_counts(
            entry["artifact_type"] for entry in entries
        ),
        "workflow_counts": _value_counts(entry["workflow"] for entry in entries),
        "agent_counts": _value_counts(entry["agent_id"] for entry in entries),
        "latest_artifact": (
            {
                "artifact_id": str(latest_artifact.artifact_id),
                "artifact_type": latest_artifact.artifact_type.value,
                "title": latest_artifact.title,
                "created_at": latest_artifact.created_at.isoformat(),
            }
            if latest_artifact
            else None
        ),
        "entries": entries,
        "dependency_edges": dependency_edges,
        "provenance_gaps": provenance_gaps,
        "retrieval_facets": {
            "by_type": _group_entry_ids(entries, "artifact_type"),
            "by_agent": _group_entry_ids(entries, "agent_id"),
            "by_workflow": _group_entry_ids(entries, "workflow"),
        },
        "recent_event_ids": _event_ids(events[-25:]),
        "pending_message_ids": [
            str(message.message_id)
            for message in messages
            if message.status
            in {
                AgentTaskStatus.ACCEPTED,
                AgentTaskStatus.CLAIMED,
                AgentTaskStatus.IN_PROGRESS,
                AgentTaskStatus.WAITING_FOR_HUMAN,
                AgentTaskStatus.BLOCKED,
            }
        ],
        "publishing_handoff": publishing_handoff,
        "recommended_actions": recommended_actions,
    }


def _artifact_librarian_publishing_handoff(
    *,
    artifacts: list[ArtifactRecord],
    sources: list[SourceRecord],
    claims: list[ClaimRecord],
    events: list[RunEvent],
    feedback_items,
    guardrail_audits,
) -> dict[str, Any]:
    publishable_artifacts = [
        artifact
        for artifact in artifacts
        if artifact.artifact_type in SOURCE_CONTENT_TYPES
        or artifact.artifact_type == ArtifactType.SOCIAL_PACKAGE
    ]
    source_drafts = [
        artifact
        for artifact in artifacts
        if artifact.artifact_type in SOURCE_CONTENT_TYPES
    ]
    distribution_packages = [
        artifact
        for artifact in artifacts
        if artifact.artifact_type == ArtifactType.SOCIAL_PACKAGE
    ]
    media_artifacts = [
        artifact
        for artifact in artifacts
        if artifact.artifact_type
        in {ArtifactType.IMAGE, ArtifactType.AUDIO, ArtifactType.VIDEO}
    ]
    source_ledger_artifacts = [
        artifact
        for artifact in artifacts
        if artifact.artifact_type == ArtifactType.SOURCE_LEDGER
    ]
    claim_revision_ledgers = [
        artifact
        for artifact in artifacts
        if artifact.artifact_type == ArtifactType.CLAIM_REVISION_LEDGER
    ]
    latest_claim_revision_ledger = (
        max(claim_revision_ledgers, key=lambda artifact: artifact.created_at)
        if claim_revision_ledgers
        else None
    )
    claim_revision_summary = _claim_revision_handoff_summary(
        latest_claim_revision_ledger,
    )
    source_by_id = {source.source_id: source for source in sources}
    publishable_artifact_ids = {artifact.artifact_id for artifact in publishable_artifacts}
    claim_status_counts = _value_counts(claim.support_status.value for claim in claims)
    source_quality_entries = [evaluate_source_quality(source) for source in sources]
    source_quality_counts = _value_counts(
        entry.quality_status.value for entry in source_quality_entries
    )
    source_freshness_counts = _value_counts(
        entry.freshness_status.value for entry in source_quality_entries
    )
    open_feedback = [
        feedback
        for feedback in feedback_items
        if feedback.status in {FeedbackStatus.OPEN, FeedbackStatus.ROUTED}
    ]
    latest_publish_readiness = _latest_event_summary(
        events,
        "publish_readiness_checked",
        fields=(
            "status",
            "ready",
            "artifact_ids",
            "blocking_issues",
            "recommended_next_actions",
            "feedback_gate_opened",
            "feedback_id",
            "summary",
        ),
    )
    source_ledger_events = [
        event for event in events if event.event_type == "source_ledger_snapshot_built"
    ]
    latest_source_ledger_event = _latest_event_summary(
        events,
        "source_ledger_snapshot_built",
        fields=(
            "source_count",
            "claim_count",
            "artifact_count",
            "unsupported_claim_count",
            "weak_source_count",
            "stale_source_count",
            "ledger_artifact_id",
        ),
    )
    audits_for_publishable = [
        audit
        for audit in guardrail_audits
        if audit.artifact_id in publishable_artifact_ids
    ]
    audited_artifact_ids = {audit.artifact_id for audit in audits_for_publishable}
    non_approved_audits = [
        audit
        for audit in audits_for_publishable
        if audit.status != GuardrailAuditStatus.APPROVED
    ]
    missing_guardrail_artifact_ids = [
        str(artifact.artifact_id)
        for artifact in publishable_artifacts
        if artifact.artifact_id not in audited_artifact_ids
    ]
    source_dependency_ids = []
    claim_dependency_ids = []
    for artifact in publishable_artifacts:
        for source_id in artifact.source_ids:
            if str(source_id) not in source_dependency_ids:
                source_dependency_ids.append(str(source_id))
        for claim_id in _extract_artifact_claim_ids(artifact):
            if str(claim_id) not in claim_dependency_ids:
                claim_dependency_ids.append(str(claim_id))
    missing_source_ids = [
        source_id
        for source_id in source_dependency_ids
        if UUID(source_id) not in source_by_id
    ]
    unsupported_claim_ids = [
        str(claim.claim_id)
        for claim in claims
        if claim.support_status == ClaimSupportStatus.UNSUPPORTED
    ]
    needs_review_claim_ids = [
        str(claim.claim_id)
        for claim in claims
        if claim.support_status == ClaimSupportStatus.NEEDS_REVIEW
    ]
    latest_publish_status = (
        str(latest_publish_readiness.get("status"))
        if latest_publish_readiness and latest_publish_readiness.get("status")
        else None
    )
    status = _publishing_handoff_status(
        publishable_artifact_count=len(publishable_artifacts),
        source_count=len(sources),
        source_ledger_count=len(source_ledger_artifacts),
        source_ledger_event_count=len(source_ledger_events),
        distribution_package_count=len(distribution_packages),
        guardrail_audit_count=len(audits_for_publishable),
        missing_guardrail_artifact_ids=missing_guardrail_artifact_ids,
        non_approved_audit_count=len(non_approved_audits),
        open_feedback_count=len(open_feedback),
        unsupported_claim_count=len(unsupported_claim_ids),
        needs_review_claim_count=len(needs_review_claim_ids),
        missing_source_count=len(missing_source_ids),
        latest_publish_readiness_status=latest_publish_status,
        claim_revision_status=claim_revision_summary.get("status"),
    )
    recommended_actions = _publishing_handoff_recommended_actions(
        status=status,
        has_source_drafts=bool(source_drafts),
        has_distribution_package=bool(distribution_packages),
        has_media_artifacts=bool(media_artifacts),
        has_source_ledger=bool(source_ledger_artifacts or source_ledger_events),
        has_guardrail_audits=bool(audits_for_publishable),
        has_publish_readiness=latest_publish_readiness is not None,
        open_feedback_count=len(open_feedback),
        unsupported_claim_count=len(unsupported_claim_ids),
        needs_review_claim_count=len(needs_review_claim_ids),
        missing_source_count=len(missing_source_ids),
        non_approved_audit_count=len(non_approved_audits),
        claim_revision_status=claim_revision_summary.get("status"),
    )
    return {
        "format": "publishing_handoff",
        "status": status,
        "publishable_artifact_count": len(publishable_artifacts),
        "source_draft_count": len(source_drafts),
        "distribution_package_count": len(distribution_packages),
        "media_artifact_count": len(media_artifacts),
        "source_dependency_count": len(source_dependency_ids),
        "claim_dependency_count": len(claim_dependency_ids),
        "source_count": len(sources),
        "claim_count": len(claims),
        "publishable_artifacts": [
            _publishing_handoff_artifact_entry(artifact)
            for artifact in publishable_artifacts
        ],
        "distribution_package_artifact_ids": [
            str(artifact.artifact_id) for artifact in distribution_packages
        ],
        "media_artifact_ids": [str(artifact.artifact_id) for artifact in media_artifacts],
        "source_ledger": {
            "artifact_ids": [
                str(artifact.artifact_id) for artifact in source_ledger_artifacts
            ],
            "snapshot_event_ids": _event_ids(source_ledger_events),
            "latest_snapshot": latest_source_ledger_event,
        },
        "claim_revision": claim_revision_summary,
        "claim_support_counts": claim_status_counts,
        "unsupported_claim_ids": unsupported_claim_ids,
        "needs_review_claim_ids": needs_review_claim_ids,
        "missing_source_ids": missing_source_ids,
        "source_quality_counts": source_quality_counts,
        "source_freshness_counts": source_freshness_counts,
        "guardrail": {
            "audit_count": len(audits_for_publishable),
            "status_counts": _value_counts(
                audit.status.value for audit in audits_for_publishable
            ),
            "missing_guardrail_artifact_ids": missing_guardrail_artifact_ids,
            "non_approved_audit_ids": [
                str(audit.audit_id) for audit in non_approved_audits
            ],
        },
        "feedback_gates": {
            "open_or_routed_count": len(open_feedback),
            "feedback_ids": [str(feedback.feedback_id) for feedback in open_feedback],
            "target_agent_ids": sorted(
                {
                    feedback.target_agent_id
                    for feedback in open_feedback
                    if feedback.target_agent_id
                }
            ),
        },
        "latest_publish_readiness": latest_publish_readiness,
        "source_artifact_ids": [str(artifact.artifact_id) for artifact in source_drafts],
        "recommended_next_actions": recommended_actions,
    }


def _publishing_handoff_artifact_entry(artifact: ArtifactRecord) -> dict[str, Any]:
    reviewer_statuses = [
        str(decision.get("status") or "recorded")
        for decision in artifact.reviewer_decisions
    ]
    return {
        "artifact_id": str(artifact.artifact_id),
        "artifact_type": artifact.artifact_type.value,
        "title": artifact.title,
        "uri": artifact.uri,
        "source_ids": [str(source_id) for source_id in artifact.source_ids],
        "claim_ids": [
            str(claim_id) for claim_id in _extract_artifact_claim_ids(artifact)
        ],
        "workflow": artifact.provenance.get("workflow", "unknown"),
        "agent_id": artifact.provenance.get(
            "agent_id",
            artifact.provenance.get("created_by_agent_id", "unknown"),
        ),
        "generation_mode": artifact.provenance.get("generation_mode", "unknown"),
        "reviewer_decision_count": len(artifact.reviewer_decisions),
        "reviewer_statuses": reviewer_statuses,
        "created_at": artifact.created_at.isoformat(),
    }


def _claim_revision_handoff_summary(
    ledger_artifact: ArtifactRecord | None,
) -> dict[str, Any]:
    if ledger_artifact is None:
        return {
            "status": "no_claim_revision_ledger",
            "artifact_id": None,
            "held_claim_count": 0,
            "open_held_claim_count": 0,
            "pending_followup_count": 0,
            "blocked_followup_count": 0,
            "completed_followup_count": 0,
            "revised_artifact_count": 0,
            "recommended_next_actions": [],
        }
    content = ledger_artifact.content or {}
    return {
        "status": content.get("status"),
        "artifact_id": str(ledger_artifact.artifact_id),
        "claim_revision_plan_artifact_id": content.get(
            "claim_revision_plan_artifact_id"
        ),
        "held_claim_count": content.get("held_claim_count", 0),
        "open_held_claim_count": content.get("open_held_claim_count", 0),
        "pending_followup_count": content.get("pending_followup_count", 0),
        "blocked_followup_count": content.get("blocked_followup_count", 0),
        "completed_followup_count": content.get("completed_followup_count", 0),
        "revised_artifact_count": content.get("revised_artifact_count", 0),
        "open_held_claim_ids": content.get("open_held_claim_ids", []),
        "recommended_next_actions": content.get("recommended_next_actions", []),
        "summary": content.get("summary"),
    }


def _latest_event_summary(
    events: list[RunEvent],
    event_type: str,
    *,
    fields: tuple[str, ...],
) -> dict[str, Any] | None:
    matches = [event for event in events if event.event_type == event_type]
    if not matches:
        return None
    event = matches[-1]
    payload = event.payload or {}
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "actor": event.actor,
        "created_at": event.created_at.isoformat(),
        **{field: payload.get(field) for field in fields if field in payload},
    }


def _publishing_handoff_status(
    *,
    publishable_artifact_count: int,
    source_count: int,
    source_ledger_count: int,
    source_ledger_event_count: int,
    distribution_package_count: int,
    guardrail_audit_count: int,
    missing_guardrail_artifact_ids: list[str],
    non_approved_audit_count: int,
    open_feedback_count: int,
    unsupported_claim_count: int,
    needs_review_claim_count: int,
    missing_source_count: int,
    latest_publish_readiness_status: str | None,
    claim_revision_status: str | None,
) -> str:
    if publishable_artifact_count == 0:
        return "no_publishable_content"
    if open_feedback_count:
        return "blocked_by_feedback"
    if claim_revision_status in {
        "blocked",
        "no_followups_created",
        "followups_pending",
        "awaiting_revised_artifacts",
        "needs_claim_reverification",
        "needs_editor_review",
        "in_progress",
    }:
        return "blocked_by_claim_revision"
    if latest_publish_readiness_status == "ready":
        return "ready"
    if latest_publish_readiness_status == "blocked":
        return "blocked_by_publish_readiness"
    if unsupported_claim_count or missing_source_count:
        return "blocked_by_evidence"
    if latest_publish_readiness_status == "needs_review":
        return "needs_publish_readiness_review"
    if needs_review_claim_count:
        return "needs_claim_review"
    if source_count == 0:
        return "needs_web_research"
    if source_ledger_count == 0 and source_ledger_event_count == 0:
        return "needs_source_ledger_snapshot"
    if distribution_package_count == 0:
        return "needs_distribution_package"
    if guardrail_audit_count == 0 or missing_guardrail_artifact_ids:
        return "needs_guardrail_audit"
    if non_approved_audit_count:
        return "needs_guardrail_revision"
    return "ready_for_publish_readiness"


def _publishing_handoff_recommended_actions(
    *,
    status: str,
    has_source_drafts: bool,
    has_distribution_package: bool,
    has_media_artifacts: bool,
    has_source_ledger: bool,
    has_guardrail_audits: bool,
    has_publish_readiness: bool,
    open_feedback_count: int,
    unsupported_claim_count: int,
    needs_review_claim_count: int,
    missing_source_count: int,
    non_approved_audit_count: int,
    claim_revision_status: str | None,
) -> list[str]:
    actions = []
    if status == "no_publishable_content" or not has_source_drafts:
        actions.append("Generate source-backed post, reel, and Substack drafts.")
    if missing_source_count:
        actions.append("Repair missing source records before any publish check.")
    if unsupported_claim_count or needs_review_claim_count:
        actions.append(
            "Run claim verification and rewrite unsupported or needs-review claims."
        )
    if claim_revision_status in {
        "blocked",
        "no_followups_created",
        "followups_pending",
        "awaiting_revised_artifacts",
        "needs_claim_reverification",
        "needs_editor_review",
        "in_progress",
    }:
        actions.append(
            "Close the claim revision ledger before publish-readiness handoff."
        )
    if not has_source_ledger:
        actions.append("Build a source ledger snapshot for the current artifacts.")
    if not has_distribution_package:
        actions.append(
            "Build the distribution package for platform hooks, keywords, and hashtags."
        )
    if not has_media_artifacts:
        actions.append(
            "Run media production for imagegen prompts, audio brief, and reel storyboard."
        )
    if not has_guardrail_audits:
        actions.append("Run the guardrail audit loop on publishable artifacts.")
    if non_approved_audit_count:
        actions.append("Resolve guardrail audit findings before publish readiness.")
    if open_feedback_count:
        actions.append("Resolve or route open human feedback before publishing.")
    if not has_publish_readiness:
        actions.append(
            "Run publish readiness after source, package, and guardrail evidence is current."
        )
    if not actions:
        actions.append("Use this publishing handoff for final editor and human approval.")
    return actions


def _artifact_provenance_gap(
    artifact: ArtifactRecord,
    gap_type: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "artifact_id": str(artifact.artifact_id),
        "artifact_type": artifact.artifact_type.value,
        "title": artifact.title,
        "gap_type": gap_type,
        "detail": detail,
    }


def _group_entry_ids(entries: list[dict[str, Any]], key: str) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for entry in entries:
        grouped.setdefault(str(entry.get(key) or "unknown"), []).append(
            entry["artifact_id"]
        )
    return grouped


def _artifact_librarian_recommended_actions(
    *,
    artifact_count: int,
    provenance_gaps: list[dict[str, Any]],
    entries: list[dict[str, Any]],
) -> list[str]:
    if artifact_count == 0:
        return ["Generate or import the first artifact before indexing retrieval facets."]
    gap_types = {gap["gap_type"] for gap in provenance_gaps}
    actions = []
    if "missing_source_dependencies" in gap_types or "missing_source_record" in gap_types:
        actions.append("Run web research and source-ledger repair before publish checks.")
    if "missing_claim_dependencies" in gap_types or "missing_claim_record" in gap_types:
        actions.append("Run claim verification so publishable artifacts have claim links.")
    if "missing_workflow" in gap_types or "missing_agent_id" in gap_types:
        actions.append("Route provenance gaps back to the producing specialist agent.")
    unreviewed_publishable = [
        entry
        for entry in entries
        if entry["artifact_type"]
        in {
            ArtifactType.POST.value,
            ArtifactType.REEL_SCRIPT.value,
            ArtifactType.SUBSTACK_ARTICLE.value,
            ArtifactType.SOCIAL_PACKAGE.value,
        }
        and entry["reviewer_decision_count"] == 0
    ]
    if unreviewed_publishable:
        actions.append("Run editorial and guardrail review for unreviewed publishable artifacts.")
    if not actions:
        actions.append("Use this artifact index as retrieval context for the next specialist handoff.")
    return actions


def _observability_report_content(
    *,
    run,
    messages: list[AgentMessage],
    events: list[RunEvent],
    artifacts: list[ArtifactRecord],
    sources: list[SourceRecord],
    claims: list[ClaimRecord],
    feedback_items,
    guardrail_audits,
    worker_profiles,
) -> dict[str, Any]:
    event_type_counts = _value_counts(event.event_type for event in events)
    task_status_counts = _value_counts(message.status.value for message in messages)
    artifact_type_counts = _value_counts(
        artifact.artifact_type.value for artifact in artifacts
    )
    worker_profile_status_counts = _value_counts(
        profile.status.value for profile in worker_profiles
    )
    provider_fallback_events = [
        event for event in events if event.event_type == "provider_fallback"
    ]
    policy_denial_events = [
        event
        for event in events
        if event.event_type in {"agent_tool_use_denied", "agent_model_use_denied"}
    ]
    failed_messages = [
        message
        for message in messages
        if message.status == AgentTaskStatus.FAILED or message.error is not None
    ]
    blocked_messages = [
        message
        for message in messages
        if message.status
        in {AgentTaskStatus.BLOCKED, AgentTaskStatus.WAITING_FOR_HUMAN}
    ]
    open_feedback = [
        feedback
        for feedback in feedback_items
        if feedback.status in {FeedbackStatus.OPEN, FeedbackStatus.ROUTED}
    ]
    non_approved_audits = [
        audit
        for audit in guardrail_audits
        if audit.status != GuardrailAuditStatus.APPROVED
    ]
    unsupported_claims = [
        claim for claim in claims if claim.support_status == ClaimSupportStatus.UNSUPPORTED
    ]
    needs_review_claims = [
        claim
        for claim in claims
        if claim.support_status == ClaimSupportStatus.NEEDS_REVIEW
    ]
    weak_or_stale_sources = []
    for source in sources:
        quality = evaluate_source_quality(source)
        if (
            quality.quality_status
            in {SourceQualityStatus.WEAK, SourceQualityStatus.NEEDS_REVIEW}
            or quality.freshness_status
            in {SourceFreshnessStatus.STALE, SourceFreshnessStatus.UNKNOWN}
        ):
            weak_or_stale_sources.append(
                {
                    "source_id": str(source.source_id),
                    "citation_id": source.citation_id,
                    "quality_status": quality.quality_status.value,
                    "freshness_status": quality.freshness_status.value,
                    "flags": quality.flags,
                }
            )

    risk_items = []
    if failed_messages:
        risk_items.append(
            {
                "risk_type": "failed_agent_tasks",
                "severity": "high",
                "count": len(failed_messages),
                "message_ids": [
                    str(message.message_id) for message in failed_messages
                ],
            }
        )
    if blocked_messages:
        risk_items.append(
            {
                "risk_type": "blocked_or_human_waiting_tasks",
                "severity": "high",
                "count": len(blocked_messages),
                "message_ids": [
                    str(message.message_id) for message in blocked_messages
                ],
            }
        )
    if policy_denial_events:
        risk_items.append(
            {
                "risk_type": "tool_or_model_policy_denials",
                "severity": "high",
                "count": len(policy_denial_events),
                "event_ids": _event_ids(policy_denial_events),
            }
        )
    if provider_fallback_events:
        risk_items.append(
            {
                "risk_type": "provider_fallbacks",
                "severity": "medium",
                "count": len(provider_fallback_events),
                "event_ids": _event_ids(provider_fallback_events),
            }
        )
    if open_feedback:
        risk_items.append(
            {
                "risk_type": "open_or_routed_feedback",
                "severity": "high",
                "count": len(open_feedback),
                "feedback_ids": [
                    str(feedback.feedback_id) for feedback in open_feedback
                ],
            }
        )
    if non_approved_audits:
        risk_items.append(
            {
                "risk_type": "guardrail_audits_not_approved",
                "severity": "high",
                "count": len(non_approved_audits),
                "audit_ids": [str(audit.audit_id) for audit in non_approved_audits],
            }
        )
    if unsupported_claims:
        risk_items.append(
            {
                "risk_type": "unsupported_claims",
                "severity": "high",
                "count": len(unsupported_claims),
                "claim_ids": [str(claim.claim_id) for claim in unsupported_claims],
            }
        )
    if needs_review_claims:
        risk_items.append(
            {
                "risk_type": "claims_need_review",
                "severity": "medium",
                "count": len(needs_review_claims),
                "claim_ids": [
                    str(claim.claim_id) for claim in needs_review_claims
                ],
            }
        )
    if weak_or_stale_sources:
        risk_items.append(
            {
                "risk_type": "source_quality_or_freshness_review",
                "severity": "medium",
                "count": len(weak_or_stale_sources),
                "sources": weak_or_stale_sources,
            }
        )

    health_status = "healthy"
    if any(risk["severity"] == "high" for risk in risk_items):
        health_status = "needs_attention"
    elif risk_items:
        health_status = "watch"

    return {
        "generation_mode": "deterministic_observability_report",
        "format": "run_health_report",
        "run_id": str(run.run_id),
        "run_status": run.status.value,
        "health_status": health_status,
        "risk_count": len(risk_items),
        "risk_items": risk_items,
        "event_count": len(events),
        "message_count": len(messages),
        "artifact_count": len(artifacts),
        "source_count": len(sources),
        "claim_count": len(claims),
        "feedback_count": len(feedback_items),
        "guardrail_audit_count": len(guardrail_audits),
        "worker_profile_count": len(worker_profiles),
        "event_type_counts": event_type_counts,
        "task_status_counts": task_status_counts,
        "artifact_type_counts": artifact_type_counts,
        "worker_profile_status_counts": worker_profile_status_counts,
        "provider_fallback_count": len(provider_fallback_events),
        "policy_denial_count": len(policy_denial_events),
        "failed_task_count": len(failed_messages),
        "blocked_task_count": len(blocked_messages),
        "open_feedback_count": len(open_feedback),
        "unsupported_claim_count": len(unsupported_claims),
        "claims_need_review_count": len(needs_review_claims),
        "weak_or_stale_source_count": len(weak_or_stale_sources),
        "recent_events": [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "actor": event.actor,
                "created_at": event.created_at.isoformat(),
            }
            for event in events[-15:]
        ],
        "recommended_actions": _observability_recommended_actions(risk_items),
    }


def _value_counts(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return counts


def _event_ids(events: list[RunEvent]) -> list[int]:
    return [event.event_id for event in events if event.event_id is not None]


def _observability_recommended_actions(
    risk_items: list[dict[str, Any]],
) -> list[str]:
    if not risk_items:
        return ["Continue the current autonomous worker cycle."]
    actions = []
    risk_types = {risk["risk_type"] for risk in risk_items}
    if "failed_agent_tasks" in risk_types:
        actions.append("Run or inspect the failed specialist worker tasks.")
    if "blocked_or_human_waiting_tasks" in risk_types:
        actions.append("Resolve blocked or human-waiting A2A tasks before resuming.")
    if "tool_or_model_policy_denials" in risk_types:
        actions.append("Review agent-card model/tool permissions before retrying.")
    if "provider_fallbacks" in risk_types:
        actions.append("Check provider configuration for fallback-producing services.")
    if "open_or_routed_feedback" in risk_types:
        actions.append("Route or resolve user feedback gates before publishing.")
    if "guardrail_audits_not_approved" in risk_types:
        actions.append("Run guardrail fixes and publish-readiness checks.")
    if "unsupported_claims" in risk_types or "claims_need_review" in risk_types:
        actions.append("Run claim verification and source ledger repair.")
    if "source_quality_or_freshness_review" in risk_types:
        actions.append("Run web research and source freshness review.")
    return actions


def _a2a_protocol_audit_content(
    *,
    messages: list[AgentMessage],
    feedback_items: list[Any],
    artifacts: list[ArtifactRecord],
    events: list[RunEvent],
) -> dict[str, Any]:
    agent_ids = {agent.id for agent in AGENT_ROSTER}
    skill_ids = {skill.id for skill in SKILL_CARDS}
    required_card_fields = {
        "id",
        "name",
        "role",
        "capabilities",
        "allowed_models",
        "allowed_tools",
        "inputs",
        "outputs",
        "handoff_rules",
        "guardrails",
        "skill_ids",
    }
    required_non_empty_fields = required_card_fields - {"allowed_tools"}

    agent_card_checks = []
    missing_required_fields = []
    missing_skill_ids = []
    for agent in AGENT_ROSTER:
        payload = agent.model_dump()
        empty_or_missing = [
            field
            for field in required_non_empty_fields
            if field not in payload or not payload[field]
        ]
        unknown_skills = [
            skill_id for skill_id in agent.skill_ids if skill_id not in skill_ids
        ]
        if empty_or_missing:
            missing_required_fields.append(
                {"agent_id": agent.id, "fields": empty_or_missing}
            )
        if unknown_skills:
            missing_skill_ids.append(
                {"agent_id": agent.id, "skill_ids": unknown_skills}
            )
        agent_card_checks.append(
            {
                "agent_id": agent.id,
                "name": agent.name,
                "role": agent.role,
                "capabilities": agent.capabilities,
                "allowed_models": agent.allowed_models,
                "allowed_tools": agent.allowed_tools,
                "skill_ids": agent.skill_ids,
                "handoff_rules": agent.handoff_rules,
                "guardrail_count": len(agent.guardrails),
                "outputs": agent.outputs,
                "complete": not empty_or_missing and not unknown_skills,
            }
        )

    skill_unknown_agents = []
    skill_cards = []
    for skill in SKILL_CARDS:
        unknown_agent_ids = [
            agent_id
            for agent_id in skill.applies_to_agents
            if agent_id not in agent_ids
        ]
        if unknown_agent_ids:
            skill_unknown_agents.append(
                {"skill_id": skill.id, "agent_ids": unknown_agent_ids}
            )
        skill_cards.append(
            {
                "skill_id": skill.id,
                "name": skill.name,
                "agent_count": len(skill.applies_to_agents),
                "source_path": skill.source_path,
                "outputs": skill.outputs,
                "guardrails": skill.guardrails,
            }
        )

    covered_agent_ids = {
        agent_id for skill in SKILL_CARDS for agent_id in skill.applies_to_agents
    }
    skill_coverage_missing_agent_ids = sorted(agent_ids - covered_agent_ids)

    unknown_message_agents = []
    handoff_matrix = []
    for message in messages:
        unknowns = []
        if message.sender_agent_id not in agent_ids:
            unknowns.append(message.sender_agent_id)
        if message.recipient_agent_id not in agent_ids:
            unknowns.append(message.recipient_agent_id)
        if unknowns:
            unknown_message_agents.append(
                {
                    "message_id": str(message.message_id),
                    "unknown_agent_ids": unknowns,
                }
            )
        handoff_matrix.append(
            {
                "message_id": str(message.message_id),
                "sender_agent_id": message.sender_agent_id,
                "recipient_agent_id": message.recipient_agent_id,
                "task_type": message.task_type,
                "status": message.status.value,
                "requires_human_feedback": message.requires_human_feedback,
                "has_result": bool(message.result),
                "has_error": message.error is not None,
            }
        )

    findings = []
    if missing_required_fields:
        findings.append(
            {
                "finding_type": "agent_card_required_field_gap",
                "severity": "high",
                "items": missing_required_fields,
            }
        )
    if missing_skill_ids:
        findings.append(
            {
                "finding_type": "unknown_agent_skill_ids",
                "severity": "high",
                "items": missing_skill_ids,
            }
        )
    if skill_unknown_agents:
        findings.append(
            {
                "finding_type": "skill_references_unknown_agents",
                "severity": "high",
                "items": skill_unknown_agents,
            }
        )
    if skill_coverage_missing_agent_ids:
        findings.append(
            {
                "finding_type": "agents_without_skill_coverage",
                "severity": "medium",
                "agent_ids": skill_coverage_missing_agent_ids,
            }
        )
    if unknown_message_agents:
        findings.append(
            {
                "finding_type": "messages_reference_unknown_agents",
                "severity": "high",
                "items": unknown_message_agents,
            }
        )

    event_type_counts = {}
    for event in events:
        event_type_counts[event.event_type] = (
            event_type_counts.get(event.event_type, 0) + 1
        )

    return {
        "generation_mode": "deterministic_protocol_audit",
        "protocol": "a2a-style-agent-cards",
        "status": "passed" if not findings else "needs_review",
        "agent_count": len(AGENT_ROSTER),
        "skill_count": len(SKILL_CARDS),
        "message_count": len(messages),
        "feedback_count": len(feedback_items),
        "artifact_count": len(artifacts),
        "event_count": len(events),
        "finding_count": len(findings),
        "findings": findings,
        "agent_card_checks": agent_card_checks,
        "skill_cards": skill_cards,
        "skill_coverage_missing_agent_ids": skill_coverage_missing_agent_ids,
        "missing_required_fields": missing_required_fields,
        "missing_skill_ids": missing_skill_ids,
        "skill_unknown_agents": skill_unknown_agents,
        "unknown_message_agents": unknown_message_agents,
        "handoff_matrix": handoff_matrix,
        "model_boundary_summary": {
            "gemma_agents": sorted(
                agent.id
                for agent in AGENT_ROSTER
                if any(model.startswith("gemma-4") for model in agent.allowed_models)
            ),
            "realtime_agents": sorted(
                agent.id
                for agent in AGENT_ROSTER
                if "realtime-audio-provider" in agent.allowed_models
            ),
            "deterministic_agents": sorted(
                agent.id
                for agent in AGENT_ROSTER
                if "deterministic-tools" in agent.allowed_models
            ),
        },
        "tool_boundary_summary": {
            agent.id: agent.allowed_tools
            for agent in AGENT_ROSTER
            if agent.allowed_tools
        },
        "event_type_counts": event_type_counts,
        "protocol_decisions": [
            "Every specialist exposes an A2A-style AgentCard.",
            "Every durable handoff is an AgentMessage with sender, recipient, task type, payload, status, and optional human gate.",
            "Tool and model use must be allowed by the recipient agent card before provider execution.",
            "Human feedback must remain structured FeedbackItem state and route back into AgentMessage work.",
        ],
    }


def _leaf_source_content_artifacts(
    artifacts: list[ArtifactRecord],
) -> list[ArtifactRecord]:
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


def _targeted_source_artifacts(
    *,
    artifacts: list[ArtifactRecord],
    target_artifact_ids: list[Any],
    include_explicit_target_artifact_types: set[ArtifactType] | None = None,
) -> list[ArtifactRecord]:
    source_artifacts = _leaf_source_content_artifacts(artifacts)
    artifact_by_id = {artifact.artifact_id: artifact for artifact in artifacts}
    target_ids = set()
    for raw_id in target_artifact_ids:
        try:
            target_ids.add(UUID(str(raw_id)))
        except (TypeError, ValueError):
            continue
    if not target_ids:
        return source_artifacts
    targeted_artifacts = [
        artifact
        for artifact in source_artifacts
        if _artifact_matches_target_or_descendant(
            artifact,
            target_ids=target_ids,
            artifact_by_id=artifact_by_id,
        )
    ]
    if include_explicit_target_artifact_types:
        for artifact in artifacts:
            if (
                artifact.artifact_id in target_ids
                and artifact.artifact_type in include_explicit_target_artifact_types
                and artifact.artifact_id
                not in {existing.artifact_id for existing in targeted_artifacts}
            ):
                targeted_artifacts.append(artifact)
    return targeted_artifacts


def _artifact_matches_target_or_descendant(
    artifact: ArtifactRecord,
    *,
    target_ids: set[UUID],
    artifact_by_id: dict[UUID, ArtifactRecord],
) -> bool:
    current: ArtifactRecord | None = artifact
    seen: set[UUID] = set()
    while current is not None and current.artifact_id not in seen:
        if current.artifact_id in target_ids:
            return True
        seen.add(current.artifact_id)
        parent_id = current.provenance.get("parent_artifact_id")
        if parent_id is None:
            return False
        try:
            current = artifact_by_id.get(UUID(str(parent_id)))
        except (TypeError, ValueError):
            return False
    return False


def _unique_source_ids_from_artifacts(
    artifacts: list[ArtifactRecord],
) -> list[UUID]:
    source_ids = []
    for artifact in artifacts:
        for source_id in artifact.source_ids:
            if source_id not in source_ids:
                source_ids.append(source_id)
    return source_ids


def _unique_claim_ids_from_artifacts(
    artifacts: list[ArtifactRecord],
) -> list[UUID]:
    claim_ids = []
    for artifact in artifacts:
        for claim_id in _extract_artifact_claim_ids(artifact):
            if claim_id not in claim_ids:
                claim_ids.append(claim_id)
    return claim_ids


def _media_dependency_artifacts(
    artifacts: list[ArtifactRecord],
) -> list[ArtifactRecord]:
    return [
        artifact
        for artifact in artifacts
        if artifact.artifact_type
        in {ArtifactType.VISUAL_BRIEF, ArtifactType.IMAGE, ArtifactType.AUDIO}
    ]


def _topic_from_artifacts(
    artifacts: list[ArtifactRecord],
    fallback: str,
) -> str:
    for artifact in artifacts:
        topic = artifact.content.get("topic")
        if isinstance(topic, str) and topic.strip():
            return topic.strip()
    for artifact in artifacts:
        if artifact.title.strip():
            return artifact.title.strip()
    return fallback.replace("Create source-backed content about ", "").strip()


def _visual_direction_brief_content(
    *,
    topic: str,
    source_artifacts: list[ArtifactRecord],
    source_ids: list[UUID],
    claim_ids: list[UUID],
    feedback_items: list[FeedbackItem],
    platform: str,
) -> dict[str, Any]:
    visual_feedback = [
        feedback
        for feedback in feedback_items
        if (
            feedback.target_agent_id == "visual-director"
            or str(feedback.metadata.get("focus", "")).lower()
            in {"visual", "image", "thumbnail", "diagram"}
            or "visual" in feedback.feedback_text.lower()
            or "thumbnail" in feedback.feedback_text.lower()
            or "diagram" in feedback.feedback_text.lower()
        )
    ]
    source_summaries = [
        {
            "artifact_id": str(artifact.artifact_id),
            "artifact_type": artifact.artifact_type.value,
            "title": artifact.title,
            "format": artifact.content.get("format"),
            "source_ids": [str(source_id) for source_id in artifact.source_ids],
            "claim_ids": [
                str(claim_id) for claim_id in _extract_artifact_claim_ids(artifact)
            ],
        }
        for artifact in source_artifacts
    ]
    return {
        "format": "visual_brief",
        "topic": topic,
        "platform": platform,
        "source_artifact_count": len(source_artifacts),
        "source_artifact_ids": [
            str(artifact.artifact_id) for artifact in source_artifacts
        ],
        "source_ids": [str(source_id) for source_id in source_ids],
        "claim_ids": [str(claim_id) for claim_id in claim_ids],
        "source_summaries": source_summaries,
        "visual_system": {
            "intent": "Make the source trail and agent collaboration visible without decorative clutter.",
            "tone": "clear, modern, educational, and ELI5-first",
            "layout": "dense but readable mobile-first frames with one focal idea per screen",
            "color_strategy": "restrained contrast palette with source and claim states visually distinct",
            "typography": "large labels, short captions, no tiny factual text",
        },
        "frame_plan": [
            {
                "frame": "hook",
                "purpose": "Stop scroll with one concrete question.",
                "visual": f"One bold question about {topic} with a visible source-trail hint.",
                "handoff": "thumbnail_prompt",
            },
            {
                "frame": "agent_map",
                "purpose": "Explain collaboration in one glance.",
                "visual": "Research, writing, review, visual, audio, and video agents connected by A2A handoffs.",
                "handoff": "reel_scene",
            },
            {
                "frame": "evidence_path",
                "purpose": "Show source-backed content generation.",
                "visual": "Source records flow into claims, then into post, reel, and article artifacts.",
                "handoff": "carousel_frame",
            },
            {
                "frame": "review_gate",
                "purpose": "Make guardrails and human feedback visible.",
                "visual": "Unsupported claims and open feedback stop the publish gate.",
                "handoff": "publish_readiness_visual",
            },
        ],
        "asset_prompts": {
            "thumbnail": (
                f"Create a mobile-safe thumbnail for {topic}: one ELI5 hook, "
                "a source trail motif, strong contrast, and no unsupported labels."
            ),
            "diagram": (
                "Create an educational diagram showing agent-to-agent handoffs, "
                "source ledger, feedback gate, and final artifacts."
            ),
            "carousel": (
                "Create a four-frame carousel using hook, agent map, evidence path, "
                "and review gate frames with consistent typography."
            ),
        },
        "handoff_contracts": [
            {
                "target_agent_id": "image-generation-agent",
                "handoff": "Use asset_prompts and visual_system when creating imagegen prompt packs.",
            },
            {
                "target_agent_id": "video-reel-producer",
                "handoff": "Use frame_plan and visual_system when sequencing reel scenes.",
            },
            {
                "target_agent_id": "lead-ui-ux-designer",
                "handoff": "Use boundary and readability checks when visual assets influence cockpit previews.",
            },
        ],
        "guardrails": [
            "Every visible factual label must map to a source or claim id.",
            "Do not present generated visuals as real screenshots or product state.",
            "Keep product cockpit visuals separate from the planning HTML surface.",
            "Avoid decorative elements that hide the actual concept.",
        ],
        "qa_checks": [
            "Text fits on mobile without overlap.",
            "Frame hierarchy makes the source trail scannable.",
            "Visual states distinguish draft, review, blocked, and ready.",
            "Image and video workers can reuse the brief without losing provenance.",
        ],
        "feedback_inputs": [
            {
                "feedback_id": str(feedback.feedback_id),
                "status": feedback.status.value,
                "feedback_text": feedback.feedback_text,
                "metadata": feedback.metadata,
            }
            for feedback in visual_feedback
        ],
    }


def _imagegen_prompt_pack_content(
    *,
    topic: str,
    source_artifacts: list[ArtifactRecord],
    source_ids: list[UUID],
    claim_ids: list[UUID],
    feedback_items: list[FeedbackItem],
    image_style: str,
    platform: str,
) -> dict[str, Any]:
    image_feedback = [
        feedback
        for feedback in feedback_items
        if (
            feedback.target_agent_id == "image-generation-agent"
            or str(feedback.metadata.get("focus", "")).lower() in {"image", "visual"}
            or "image" in feedback.feedback_text.lower()
            or "thumbnail" in feedback.feedback_text.lower()
        )
    ]
    source_summaries = [
        {
            "artifact_id": str(artifact.artifact_id),
            "artifact_type": artifact.artifact_type.value,
            "title": artifact.title,
            "format": artifact.content.get("format"),
            "source_ids": [str(source_id) for source_id in artifact.source_ids],
            "claim_ids": [
                str(claim_id) for claim_id in _extract_artifact_claim_ids(artifact)
            ],
        }
        for artifact in source_artifacts
    ]
    return {
        "format": "imagegen_prompt_pack",
        "topic": topic,
        "platform": platform,
        "provider_boundary": (
            "Use imagegen only for raster image generation or editing; this "
            "artifact is the source-linked prompt and QA contract."
        ),
        "source_artifact_count": len(source_artifacts),
        "source_artifact_ids": [
            str(artifact.artifact_id) for artifact in source_artifacts
        ],
        "source_ids": [str(source_id) for source_id in source_ids],
        "claim_ids": [str(claim_id) for claim_id in claim_ids],
        "source_summaries": source_summaries,
        "primary_prompt": (
            f"Create a crisp educational social visual about {topic}. "
            f"Style: {image_style}. Use ELI5 composition, clear hierarchy, "
            "source-backed labels only, and one obvious focal point."
        ),
        "thumbnail_prompt": (
            f"Create a vertical reel thumbnail for {topic}. Use one readable "
            "mobile-safe hook, high contrast, and room for platform overlays."
        ),
        "carousel_frame_prompts": [
            (
                f"Frame 1: Hook visual for {topic} with a single ELI5 question "
                "and no unsupported numbers."
            ),
            (
                "Frame 2: Show the source trail as a simple evidence path from "
                "source to claim to draft."
            ),
            (
                "Frame 3: Show the review gate blocking weak claims before the "
                "content is published."
            ),
        ],
        "style_controls": {
            "aspect_ratios": ["9:16", "1:1", "4:5"],
            "typography": "large, short, mobile-safe text",
            "composition": "dense but uncluttered educational layout",
            "accessibility": "strong contrast and no tiny factual labels",
        },
        "negative_constraints": [
            "Do not add factual labels that are not in the source or claim ids.",
            "Do not render charts unless the data table exists in the run.",
            "Do not use decorative clutter that hides the actual concept.",
            "Do not imply a generated bitmap is a real screenshot or product UI.",
        ],
        "qa_checks": [
            "Every visible claim maps to a source or claim id.",
            "Longest text fits on mobile without overlap.",
            "Prompt can be regenerated without losing provenance.",
            "Raster generation happens only through the imagegen boundary.",
        ],
        "feedback_inputs": [
            {
                "feedback_id": str(feedback.feedback_id),
                "status": feedback.status.value,
                "feedback_text": feedback.feedback_text,
                "metadata": feedback.metadata,
            }
            for feedback in image_feedback
        ],
    }


def _audio_production_brief_content(
    *,
    topic: str,
    source_artifacts: list[ArtifactRecord],
    source_ids: list[UUID],
    claim_ids: list[UUID],
    feedback_items: list[FeedbackItem],
    realtime_sessions: list[Any],
    voice_style: str,
    platform: str,
) -> dict[str, Any]:
    audio_feedback = [
        feedback
        for feedback in feedback_items
        if (
            feedback.target_agent_id == "audio-producer"
            or str(feedback.metadata.get("focus", "")).lower()
            in {"audio", "voice", "tts"}
            or "audio" in feedback.feedback_text.lower()
            or "voice" in feedback.feedback_text.lower()
            or "pacing" in feedback.feedback_text.lower()
        )
    ]
    return {
        "format": "audio_brief",
        "topic": topic,
        "platform": platform,
        "voice_style": voice_style,
        "provider_boundary": (
            "OpenRouter deepseek/deepseek-v4-flash handles text-turn live dialogue "
            "reasoning, Kokoro handles TTS, and LiveKit handles realtime transport; "
            "raw microphone PCM is not sent to OpenRouter. Legacy native-Gemma/HF "
            "audio understanding is non-default context. Pipecat processors and "
            "proprietary voice providers are optional fallback routes, not the default."
        ),
        "source_artifact_count": len(source_artifacts),
        "source_artifact_ids": [
            str(artifact.artifact_id) for artifact in source_artifacts
        ],
        "source_ids": [str(source_id) for source_id in source_ids],
        "claim_ids": [str(claim_id) for claim_id in claim_ids],
        "voiceover_script": _audio_script_from_artifacts(source_artifacts),
        "provider_plan": [
            {
                "provider": "openrouter_livekit",
                "role": "OpenRouter deepseek/deepseek-v4-flash text-turn reasoning with Kokoro speech output over LiveKit.",
                "use_when": "default live back-and-forth studio sessions need provider-backed reasoning, turn-taking, context pruning, and barge-in.",
            },
            {
                "provider": "livekit_transport",
                "role": "WebRTC media transport, turn lifecycle, device handling, and interruption plumbing.",
                "use_when": "browser or mobile clients need production-grade realtime audio.",
            },
            {
                "provider": "rust_vad_edge",
                "role": "low-latency VAD, outbound audio buffer control, and cancellation signals to Python/OpenRouter/Kokoro.",
                "use_when": "barge-in must stop speech instantly and keep long-running sessions stable.",
            },
            {
                "provider": "elevenlabs",
                "role": "optional high-quality proprietary TTS voice output for polished narration",
                "use_when": "a user explicitly chooses a paid external narration provider.",
            },
            {
                "provider": "cartesia",
                "role": "optional proprietary low-latency TTS output",
                "use_when": "a user explicitly chooses a paid external realtime TTS provider.",
            },
        ],
        "session_inventory": _realtime_session_inventory(realtime_sessions),
        "pacing_plan": [
            "One idea per breath.",
            "Pause before source-backed caveats.",
            "Keep the ELI5 hook under four seconds for short-form video.",
            "Use short spoken sentences even when the written artifact is detailed.",
        ],
        "pronunciation_notes": [
            "Say OpenRouter as open router.",
            "Say pgvector as P-G vector.",
            "Say A2A as agent-to-agent unless the audience already knows the acronym.",
            "Expand HF as Hugging Face on first spoken mention.",
        ],
        "interruption_and_resume_checks": [
            "A user interruption must preserve the current run id and latest spoken turn.",
            "Resumed speech must summarize the current agent state before continuing.",
            "Provider session secrets or signed URLs must not be stored in events.",
        ],
        "qa_checks": [
            "No unsupported factual claims in spoken copy.",
            "Every statistic or named provider claim remains source traceable.",
            "Caveats are spoken clearly, not hidden in captions.",
            "Voice style matches the chosen platform and user feedback.",
        ],
        "feedback_inputs": [
            {
                "feedback_id": str(feedback.feedback_id),
                "status": feedback.status.value,
                "feedback_text": feedback.feedback_text,
                "metadata": feedback.metadata,
            }
            for feedback in audio_feedback
        ],
    }


def _audio_script_from_artifacts(artifacts: list[ArtifactRecord]) -> str:
    for artifact in artifacts:
        if artifact.artifact_type == ArtifactType.REEL_SCRIPT:
            script = artifact.content.get("script")
            if isinstance(script, list) and script:
                return " ".join(str(line) for line in script)
            hook = artifact.content.get("hook")
            body = artifact.content.get("body")
            if hook or body:
                return " ".join(str(part) for part in [hook, body] if part)
    for artifact in artifacts:
        summary = artifact.content.get("body") or artifact.content.get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
    return (
        "Explain the idea in ELI5 language, name the source trail, and end by "
        "inviting the user to review the draft before publishing."
    )


def _realtime_session_inventory(realtime_sessions: list[Any]) -> dict[str, Any]:
    return {
        "session_count": len(realtime_sessions),
        "active_session_count": sum(
            1 for session in realtime_sessions if session.status.value == "active"
        ),
        "providers": sorted({session.provider for session in realtime_sessions}),
        "voices": sorted(
            {session.voice for session in realtime_sessions if session.voice}
        ),
        "sessions": [
            {
                "realtime_session_id": str(session.realtime_session_id),
                "provider": session.provider,
                "voice": session.voice,
                "audio_mode": session.audio_mode,
                "status": session.status.value,
                "has_client_secret": session.has_client_secret,
                "has_websocket_url": session.has_websocket_url,
            }
            for session in realtime_sessions
        ],
    }


def _video_reel_storyboard_content(
    *,
    topic: str,
    source_artifacts: list[ArtifactRecord],
    media_dependencies: list[ArtifactRecord],
    source_ids: list[UUID],
    claim_ids: list[UUID],
    feedback_items: list[FeedbackItem],
    platform: str,
    duration_seconds: int,
) -> dict[str, Any]:
    video_feedback = [
        feedback
        for feedback in feedback_items
        if (
            feedback.target_agent_id == "video-reel-producer"
            or str(feedback.metadata.get("focus", "")).lower()
            in {"video", "reel", "storyboard"}
            or "video" in feedback.feedback_text.lower()
            or "reel" in feedback.feedback_text.lower()
            or "subtitle" in feedback.feedback_text.lower()
        )
    ]
    return {
        "format": "reel_storyboard",
        "topic": topic,
        "platform": platform,
        "duration_seconds": duration_seconds,
        "source_artifact_count": len(source_artifacts),
        "source_artifact_ids": [
            str(artifact.artifact_id) for artifact in source_artifacts
        ],
        "source_ids": [str(source_id) for source_id in source_ids],
        "claim_ids": [str(claim_id) for claim_id in claim_ids],
        "media_dependencies": [
            {
                "artifact_id": str(artifact.artifact_id),
                "artifact_type": artifact.artifact_type.value,
                "title": artifact.title,
                "format": artifact.content.get("format"),
                "agent_id": artifact.provenance.get("agent_id"),
            }
            for artifact in media_dependencies
        ],
        "narration_reference": _audio_script_from_artifacts(source_artifacts),
        "scenes": [
            {
                "time": "0-4s",
                "visual": f"Hook frame for {topic} with one concrete question.",
                "caption": "Why should you trust this AI draft?",
                "source_rule": "No data labels unless backed by linked claim ids.",
            },
            {
                "time": "4-12s",
                "visual": "Show researcher, writer, and guardrail agents working in sequence.",
                "caption": "One agent writes. Another checks. A third blocks weak claims.",
                "source_rule": "Keep agent roles as system behavior, not factual market claims.",
            },
            {
                "time": "12-24s",
                "visual": "Animate source records linking to claims and then into the draft.",
                "caption": "Every big claim gets a visible source trail.",
                "source_rule": "Visible claims must map to source_ids or claim_ids.",
            },
            {
                "time": "24-32s",
                "visual": "Show voice, image, and storyboard artifacts joining the run timeline.",
                "caption": "The studio plans visuals, voice, and edits before publishing.",
                "source_rule": "Do not imply generated assets are final unless reviewed.",
            },
            {
                "time": f"32-{duration_seconds}s",
                "visual": "Publish gate moves from needs review to ready after fixes.",
                "caption": "Review first. Publish after the evidence checks out.",
                "source_rule": "End with a review call, not an unsupported performance promise.",
            },
        ],
        "shot_list": [
            "Mobile-safe hook frame",
            "Agent handoff sequence",
            "Source ledger close-up",
            "Artifact stack for image, audio, and video",
            "Human feedback gate and publish readiness state",
        ],
        "subtitle_rules": [
            "Maximum two lines per frame.",
            "Keep ELI5 wording for reels and short posts.",
            "Do not hide caveats or source uncertainty.",
            "Use captions that can stand alone with muted playback.",
        ],
        "asset_requirements": [
            "Use imagegen prompt packs for raster visuals.",
            "Use audio briefs for voiceover pacing and pronunciation.",
            "Keep all on-screen factual text source traceable.",
            "Reserve safe space for platform controls and captions.",
        ],
        "qa_checks": [
            "No unsupported claims appear in captions or on-screen labels.",
            "Text fits on mobile without overlap.",
            "Scene timing leaves time for natural spoken pauses.",
            "Every media dependency keeps provenance to its source artifacts.",
        ],
        "feedback_inputs": [
            {
                "feedback_id": str(feedback.feedback_id),
                "status": feedback.status.value,
                "feedback_text": feedback.feedback_text,
                "metadata": feedback.metadata,
            }
            for feedback in video_feedback
        ],
    }


def _writer_source_artifacts(
    artifacts: list[ArtifactRecord],
    agent_id: str,
    *,
    target_artifact_ids: list[Any] | None = None,
) -> list[ArtifactRecord]:
    source_artifacts = _targeted_source_artifacts(
        artifacts=artifacts,
        target_artifact_ids=target_artifact_ids or [],
    )
    if agent_id == "eli5-short-form-writer":
        return [
            artifact
            for artifact in source_artifacts
            if artifact.artifact_type in {ArtifactType.POST, ArtifactType.REEL_SCRIPT}
        ]
    if agent_id == "substack-essay-writer":
        return [
            artifact
            for artifact in source_artifacts
            if artifact.artifact_type == ArtifactType.SUBSTACK_ARTICLE
        ]
    return []


def _writer_source_ids_for_retrieval(
    artifact: ArtifactRecord,
    evidence_by_source_id: dict[UUID, Any],
) -> tuple[list[UUID], str]:
    parent_source_ids = list(dict.fromkeys(artifact.source_ids))
    if not evidence_by_source_id:
        return parent_source_ids, "retrieval_quality_not_available"
    accepted_source_ids = [
        source_id
        for source_id in evidence_by_source_id
        if source_id in set(parent_source_ids)
    ]
    if accepted_source_ids:
        return accepted_source_ids, "accepted_retrieval_evidence"
    return parent_source_ids, "no_accepted_retrieval_overlap"


def _latest_claim_revision_plan(
    artifacts: list[ArtifactRecord],
) -> ArtifactRecord | None:
    plans = [
        artifact
        for artifact in artifacts
        if artifact.artifact_type == ArtifactType.CLAIM_REVISION_PLAN
    ]
    if not plans:
        return None
    return max(plans, key=lambda artifact: artifact.created_at)


def _writer_claim_revision_context(
    claim_revision_plan: ArtifactRecord | None,
    artifact_claim_ids: list[UUID],
) -> dict[str, Any]:
    if claim_revision_plan is None:
        return {
            "status": "no_claim_revision_plan",
            "held_claim_ids": [],
            "instructions": [],
        }
    artifact_claim_id_set = {str(claim_id) for claim_id in artifact_claim_ids}
    held_claims = [
        claim
        for claim in claim_revision_plan.content.get("held_claims", [])
        if str(claim.get("claim_id")) in artifact_claim_id_set
    ]
    if not held_claims:
        return {
            "status": "claim_revision_plan_not_applicable",
            "artifact_id": str(claim_revision_plan.artifact_id),
            "held_claim_ids": [],
            "instructions": [],
        }
    return {
        "status": "claim_revision_required",
        "artifact_id": str(claim_revision_plan.artifact_id),
        "held_claim_ids": [str(claim.get("claim_id")) for claim in held_claims],
        "instructions": claim_revision_plan.content.get("writer_instructions", []),
        "held_claims": held_claims,
        "accepted_source_alternatives": claim_revision_plan.content.get(
            "accepted_source_alternatives",
            [],
        ),
    }


def _script_doctor_source_artifacts(
    artifacts: list[ArtifactRecord],
    *,
    target_artifact_ids: list[Any] | None = None,
) -> list[ArtifactRecord]:
    return [
        artifact
        for artifact in _targeted_source_artifacts(
            artifacts=artifacts,
            target_artifact_ids=target_artifact_ids or [],
        )
        if artifact.artifact_type == ArtifactType.REEL_SCRIPT
    ]


def _data_brief_content_for(
    *,
    topic: str,
    run_goal: str | None,
    sources: list[SourceRecord],
    claims: list[ClaimRecord],
    artifacts: list[ArtifactRecord],
) -> dict[str, Any]:
    source_by_id = {source.source_id: source for source in sources}
    source_table = []
    for source in sources:
        source_quality = evaluate_source_quality(source)
        source_table.append(
            {
                "source_id": str(source.source_id),
                "citation_id": source.citation_id,
                "title": source.title,
                "publisher": source.publisher,
                "url": str(source.url),
                "source_type": source.metadata.get("source_type", "unknown"),
                "published_at": _datetime_or_none(source.published_at),
                "retrieved_at": source.retrieved_at.isoformat(),
                "quality_status": source_quality.quality_status.value,
                "freshness_status": source_quality.freshness_status.value,
            }
        )

    claim_table = []
    for claim in claims:
        claim_table.append(
            {
                "claim_id": str(claim.claim_id),
                "claim_text": claim.claim_text,
                "support_status": claim.support_status.value,
                "source_ids": [str(source_id) for source_id in claim.source_ids],
                "source_citation_ids": [
                    source_by_id[source_id].citation_id
                    for source_id in claim.source_ids
                    if source_id in source_by_id
                ],
                "missing_source_ids": [
                    str(source_id)
                    for source_id in claim.source_ids
                    if source_id not in source_by_id
                ],
                "reviewer_agent_id": claim.reviewer_agent_id,
                "notes": claim.notes,
            }
        )

    artifact_dependency_table = []
    for artifact in artifacts:
        claim_ids = _extract_artifact_claim_ids(artifact)
        artifact_dependency_table.append(
            {
                "artifact_id": str(artifact.artifact_id),
                "artifact_type": artifact.artifact_type.value,
                "title": artifact.title,
                "source_ids": [str(source_id) for source_id in artifact.source_ids],
                "source_citation_ids": [
                    source_by_id[source_id].citation_id
                    for source_id in artifact.source_ids
                    if source_id in source_by_id
                ],
                "claim_ids": [str(claim_id) for claim_id in claim_ids],
                "missing_source_ids": [
                    str(source_id)
                    for source_id in artifact.source_ids
                    if source_id not in source_by_id
                ],
                "missing_claim_dependencies": not claim_ids,
                "workflow": artifact.provenance.get("workflow", "unknown"),
            }
        )

    unsupported_claims = [
        row
        for row in claim_table
        if row["support_status"] == ClaimSupportStatus.UNSUPPORTED.value
    ]
    claims_needing_review = [
        row
        for row in claim_table
        if row["support_status"] == ClaimSupportStatus.NEEDS_REVIEW.value
    ]
    claims_missing_sources = [
        row for row in claim_table if not row["source_ids"] or row["missing_source_ids"]
    ]
    artifacts_missing_sources = [
        row
        for row in artifact_dependency_table
        if not row["source_ids"] or row["missing_source_ids"]
    ]
    artifacts_missing_claims = [
        row for row in artifact_dependency_table if row["missing_claim_dependencies"]
    ]
    publish_risks = []
    if unsupported_claims:
        publish_risks.append(
            {
                "risk_type": "unsupported_claims",
                "count": len(unsupported_claims),
                "claim_ids": [row["claim_id"] for row in unsupported_claims],
            }
        )
    if claims_needing_review:
        publish_risks.append(
            {
                "risk_type": "claims_need_review",
                "count": len(claims_needing_review),
                "claim_ids": [row["claim_id"] for row in claims_needing_review],
            }
        )
    if claims_missing_sources or artifacts_missing_sources:
        publish_risks.append(
            {
                "risk_type": "missing_source_dependencies",
                "claim_ids": [row["claim_id"] for row in claims_missing_sources],
                "artifact_ids": [
                    row["artifact_id"] for row in artifacts_missing_sources
                ],
            }
        )
    if artifacts_missing_claims:
        publish_risks.append(
            {
                "risk_type": "missing_claim_dependencies",
                "artifact_ids": [row["artifact_id"] for row in artifacts_missing_claims],
            }
        )

    return {
        "generation_mode": "deterministic_data_analysis",
        "format": "source_backed_data_brief",
        "topic": topic,
        "run_goal": run_goal,
        "source_count": len(sources),
        "claim_count": len(claims),
        "artifact_count": len(artifacts),
        "source_table": source_table,
        "claim_table": claim_table,
        "artifact_dependency_table": artifact_dependency_table,
        "support_mix": {
            status.value: sum(
                1 for claim in claims if claim.support_status == status
            )
            for status in ClaimSupportStatus
        },
        "content_angles": [
            {
                "angle": "ELI5 mechanism",
                "use": (
                    "Explain how the source ledger works like receipts attached "
                    "to each major claim."
                ),
            },
            {
                "angle": "Real-world proof",
                "use": (
                    "Use source titles and citation IDs as visible proof points "
                    "before examples or platform claims."
                ),
            },
            {
                "angle": "Caveat framing",
                "use": (
                    "Turn needs-review and unsupported claims into explicit caveats "
                    "instead of publishable facts."
                ),
            },
        ],
        "chart_suggestions": [
            "Source freshness mix by citation ID",
            "Claim support mix across supported, needs_review, and unsupported",
            "Artifact dependency map from drafts to sources and claims",
        ],
        "publish_risks": publish_risks,
    }


def _script_doctor_content_for(
    *,
    artifact: ArtifactRecord,
    topic: str,
    feedback_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    claim_ids = [str(claim_id) for claim_id in _extract_artifact_claim_ids(artifact)]
    source_ids = [str(source_id) for source_id in artifact.source_ids]
    source_caveat = "Ask for the source ledger before treating the draft as final."
    feedback_context = feedback_context or {}
    return {
        "generation_mode": "deterministic_script_doctor",
        "format": "script_doctor_reel_script",
        "topic": topic,
        "hook_options": [
            f"POV: {topic} is not one AI voice. It is a studio with specialists.",
            f"ELI5: {topic} works because every agent gets one clear job.",
            "Before this becomes a reel, every big claim needs a receipt.",
        ],
        "recommended_hook": (
            f"ELI5: {topic} is a live studio where one agent talks, one "
            "researches, and one checks the claims."
        ),
        "spoken_script": [
            "Start with the problem in one short sentence.",
            "Name the agent team in plain language.",
            "Show the source-backed claim before the takeaway.",
            source_caveat,
        ],
        "timing_seconds": [
            {"start": 0, "end": 3, "beat": "hook"},
            {"start": 3, "end": 9, "beat": "simple analogy"},
            {"start": 9, "end": 18, "beat": "source-backed mechanism"},
            {"start": 18, "end": 24, "beat": "caveat and CTA"},
        ],
        "retention_notes": [
            "Keep the first line under eight seconds when spoken.",
            "Use one concrete noun per sentence.",
            "Put the caveat before the CTA, not after it.",
            "Avoid benchmark or access claims that are not in the source ledger.",
        ],
        "subtitle_safe_lines": [
            "One agent talks.",
            "One agent researches.",
            "One agent checks claims.",
            "Sources before publishing.",
        ],
        "claim_ids": claim_ids,
        "source_ids": source_ids,
        "parent_artifact_id": str(artifact.artifact_id),
        "feedback_context": feedback_context,
    }


def _datetime_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _parse_provider_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _writer_artifact_title(artifact: ArtifactRecord, agent_id: str) -> str:
    if agent_id == "eli5-short-form-writer":
        return f"ELI5 writer version: {artifact.title}"
    if agent_id == "substack-essay-writer":
        return f"Substack writer version: {artifact.title}"
    return f"Writer version: {artifact.title}"


def _writer_content_for(
    *,
    artifact: ArtifactRecord,
    topic: str,
    agent_id: str,
    source_ids: list[UUID] | None = None,
    retrieval_context: dict[str, Any] | None = None,
    claim_revision_context: dict[str, Any] | None = None,
    feedback_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    claim_ids = [str(claim_id) for claim_id in _extract_artifact_claim_ids(artifact)]
    source_ids = [str(source_id) for source_id in (source_ids or artifact.source_ids)]
    feedback_context = feedback_context or {}
    retrieval_context = retrieval_context or {
        "acceptance_status": "retrieval_quality_not_available",
        "accepted_source_count": 0,
        "accepted_sources": [],
    }
    claim_revision_context = claim_revision_context or {
        "status": "no_claim_revision_plan",
        "held_claim_ids": [],
        "instructions": [],
    }
    if agent_id == "eli5-short-form-writer":
        if artifact.artifact_type == ArtifactType.REEL_SCRIPT:
            return {
                "generation_mode": "deterministic_writer",
                "format": "eli5_reel_script",
                "hook": f"ELI5: {topic} is a team of specialists, not one magic model.",
                "beats": [
                    "Name the everyday analogy in the first sentence.",
                    "Show the source-backed claim before the punchline.",
                    "Explain what Gemma 4 handles and what realtime audio handles.",
                    "End with the caveat: claims still need the source ledger.",
                ],
                "subtitle_safe_lines": [
                    "One agent talks.",
                    "One agent researches.",
                    "One agent checks the claim.",
                    "Nothing ships without sources.",
                ],
                "claim_ids": claim_ids,
                "source_ids": source_ids,
                "retrieval_context": retrieval_context,
                "claim_revision_context": claim_revision_context,
                "parent_artifact_id": str(artifact.artifact_id),
                "feedback_context": feedback_context,
            }
        return {
            "generation_mode": "deterministic_writer",
            "format": "eli5_social_post",
            "hook": f"ELI5: {topic} works best when each agent has one job.",
            "body": (
                "Think of the studio like a live conversation backed by a research "
                "desk: voice handles the back-and-forth, Gemma 4 specialists draft "
                "and critique, and the source ledger keeps claims honest."
            ),
            "cta": "Ask for the source ledger before treating any draft as final.",
            "hashtags": ["#AI", "#LLMs", "#AIAgents", "#SourceBacked"],
            "claim_ids": claim_ids,
            "source_ids": source_ids,
            "retrieval_context": retrieval_context,
            "claim_revision_context": claim_revision_context,
            "parent_artifact_id": str(artifact.artifact_id),
            "feedback_context": feedback_context,
        }

    return {
        "generation_mode": "deterministic_writer",
        "format": "substack_article",
        "title": f"{topic}: ELI5 first, architecture second",
        "sections": [
            {
                "heading": "ELI5 summary",
                "body": (
                    "The system should feel like talking to one studio, while "
                    "specialist agents quietly research, draft, critique, and check "
                    "sources in the background."
                ),
            },
            {
                "heading": "What each layer does",
                "body": (
                    "Realtime audio owns natural dialogue. Gemma 4 expert agents "
                    "handle reasoning and writing. Postgres keeps runs, events, "
                    "sources, feedback, memories, and artifacts durable."
                ),
            },
            {
                "heading": "Why sources matter",
                "body": (
                    "Every important claim must map to a source record or stay "
                    "marked as unsupported until research and claim verification "
                    "resolve it."
                ),
            },
            {
                "heading": "What still needs review",
                "body": (
                    "Publishing still needs human judgment, guardrail audits, and "
                    "platform-specific editorial review before external use."
                ),
            },
        ],
        "claim_ids": claim_ids,
        "source_ids": source_ids,
        "retrieval_context": retrieval_context,
        "claim_revision_context": claim_revision_context,
        "parent_artifact_id": str(artifact.artifact_id),
        "feedback_context": feedback_context,
    }


def _leaf_editorial_artifacts(
    artifacts: list[ArtifactRecord],
) -> list[ArtifactRecord]:
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
        if artifact.artifact_type in EDITORIAL_REVIEW_ARTIFACT_TYPES
        and artifact.artifact_id not in parent_ids
    ]


def _has_current_review(artifact: ArtifactRecord, reviewer_agent_id: str) -> bool:
    return any(
        decision.get("reviewer_agent_id") == reviewer_agent_id
        and decision.get("workflow") == "editorial_review_worker_v1"
        for decision in artifact.reviewer_decisions
        if isinstance(decision, dict)
    )


def _editorial_decision_for(
    *,
    artifact: ArtifactRecord,
    reviewer_agent_id: str,
    claim_by_id: dict[UUID, ClaimRecord] | None = None,
    retrieval_evidence_by_source_id: dict[UUID, Any] | None = None,
    retrieval_ledger_available: bool = False,
) -> ReviewDecision:
    claim_by_id = claim_by_id or {}
    retrieval_evidence_by_source_id = retrieval_evidence_by_source_id or {}
    strict_evidence_gate = reviewer_agent_id == "editor-in-chief"
    blocking_issues: list[str] = []
    notes = []
    artifact_claim_ids = _extract_artifact_claim_ids(artifact)
    if not artifact.source_ids:
        blocking_issues.append("missing_source_dependencies")
        notes.append("Artifact has no source dependencies.")
    if (
        strict_evidence_gate
        and retrieval_ledger_available
        and not retrieval_evidence_by_source_id
    ):
        blocking_issues.append("no_accepted_retrieval_evidence")
        notes.append("Latest retrieval quality ledger has no accepted source evidence.")
    elif (
        strict_evidence_gate
        and retrieval_evidence_by_source_id
        and artifact.source_ids
    ):
        accepted_source_ids = {
            source_id
            for source_id in artifact.source_ids
            if source_id in retrieval_evidence_by_source_id
        }
        if not accepted_source_ids:
            blocking_issues.append("artifact_missing_accepted_retrieval_evidence")
            notes.append(
                "Artifact source dependencies do not overlap accepted retrieval evidence."
            )
    if not artifact_claim_ids:
        blocking_issues.append("missing_claim_dependencies")
        notes.append("Artifact has no claim dependencies.")
    elif strict_evidence_gate:
        linked_claims = [
            claim_by_id[claim_id]
            for claim_id in artifact_claim_ids
            if claim_id in claim_by_id
        ]
        unsupported_claims = [
            claim
            for claim in linked_claims
            if claim.support_status == ClaimSupportStatus.UNSUPPORTED
        ]
        needs_review_claims = [
            claim
            for claim in linked_claims
            if claim.support_status == ClaimSupportStatus.NEEDS_REVIEW
        ]
        if unsupported_claims:
            blocking_issues.append("unsupported_claim_dependencies")
            notes.append(
                f"{len(unsupported_claims)} linked claim(s) are unsupported."
            )
        if needs_review_claims:
            blocking_issues.append("claim_dependencies_need_review")
            notes.append(
                f"{len(needs_review_claims)} linked claim(s) still need review."
            )
        if retrieval_evidence_by_source_id:
            claims_without_accepted_evidence = [
                claim
                for claim in linked_claims
                if claim.source_ids
                and not any(
                    source_id in retrieval_evidence_by_source_id
                    for source_id in claim.source_ids
                )
            ]
            if claims_without_accepted_evidence:
                blocking_issues.append("claim_missing_accepted_retrieval_evidence")
                notes.append(
                    f"{len(claims_without_accepted_evidence)} linked claim(s) "
                    "have no accepted retrieval evidence."
                )
    if artifact.artifact_type == ArtifactType.SOCIAL_PACKAGE:
        if not artifact.content.get("platform_variants"):
            blocking_issues.append("missing_platform_variants")
        if not artifact.content.get("outreach"):
            blocking_issues.append("missing_outreach_brief")
    elif not _has_eli5_or_source_signal(artifact):
        notes.append(
            "Artifact should make the ELI5 framing or source caveat more visible."
        )

    if blocking_issues:
        status = ReviewDecisionStatus.NEEDS_REVISION
    elif notes:
        status = ReviewDecisionStatus.APPROVED_WITH_NOTES
    else:
        status = ReviewDecisionStatus.APPROVED

    reviewer_note = (
        "Editorial review found blocking issues before publish readiness."
        if blocking_issues
        else "Editorial review approved the artifact with source-aware quality checks."
    )
    if reviewer_agent_id == "critic-reviewer-agent" and not blocking_issues:
        status = ReviewDecisionStatus.APPROVED_WITH_NOTES
        notes.append(
            "Critic review still recommends a final human read for hook strength and audience fit."
        )

    return ReviewDecision(
        reviewer_agent_id=reviewer_agent_id,
        status=status,
        notes=" ".join([reviewer_note, *notes]).strip(),
        blocking_issues=blocking_issues,
    )


def _extract_artifact_claim_ids(artifact: ArtifactRecord) -> list[UUID]:
    raw_claim_ids = [
        *artifact.provenance.get("claim_ids", []),
        *artifact.content.get("claim_ids", []),
    ]
    claim_ids = []
    for raw_claim_id in raw_claim_ids:
        try:
            claim_id = UUID(str(raw_claim_id))
        except (TypeError, ValueError):
            continue
        if claim_id not in claim_ids:
            claim_ids.append(claim_id)
    return claim_ids


def _has_eli5_or_source_signal(artifact: ArtifactRecord) -> bool:
    text = json.dumps(artifact.content, default=str).lower()
    return any(
        marker in text
        for marker in {
            "eli5",
            "source",
            "claim",
            "caveat",
            "explain",
            "simply",
        }
    )


def _current_distribution_package(
    *,
    artifacts: list[ArtifactRecord],
    source_artifacts: list[ArtifactRecord],
) -> ArtifactRecord | None:
    source_artifact_ids = {
        str(artifact.artifact_id) for artifact in source_artifacts
    }
    for artifact in reversed(artifacts):
        if (
            artifact.artifact_type == ArtifactType.SOCIAL_PACKAGE
            and artifact.provenance.get("workflow") == "distribution_package_v1"
            and set(artifact.provenance.get("source_artifact_ids", []))
            == source_artifact_ids
        ):
            return artifact
    return None


def _build_influencer_strategy_artifact(
    *,
    message: AgentMessage,
    package: ArtifactRecord,
    source_artifacts: list[ArtifactRecord],
    strategy_context: dict[str, Any],
) -> ArtifactRecord:
    topic = _growth_package_topic(package)
    source_ids = _growth_package_source_ids(package, source_artifacts)
    claim_ids = _growth_package_claim_ids(package, source_artifacts)
    platforms = _growth_package_platforms(package)
    hashtags = _growth_package_terms(package, "hashtags")
    keywords = _growth_package_terms(package, "keywords")
    hook_angles = [
        {
            "platform": variant.get("platform"),
            "hook": variant.get("hook"),
            "cta": variant.get("cta"),
        }
        for variant in platforms
        if isinstance(variant, dict)
    ]
    content = {
        "workflow": "influencer_strategy_v1",
        "topic": topic,
        "distribution_artifact_id": str(package.artifact_id),
        "source_artifact_ids": [
            str(source_artifact.artifact_id) for source_artifact in source_artifacts
        ],
        "source_ids": [str(source_id) for source_id in source_ids],
        "claim_ids": [str(claim_id) for claim_id in claim_ids],
        "audience_segments": [
            {
                "segment": "AI-curious beginners",
                "promise": f"Explain {topic} without jargon.",
                "best_channels": ["instagram_post", "instagram_reel"],
            },
            {
                "segment": "builders and operators",
                "promise": "Show the workflow, sources, and caveats plainly.",
                "best_channels": ["linkedin", "x_thread"],
            },
            {
                "segment": "deep readers",
                "promise": "Connect the ELI5 explanation to the source ledger.",
                "best_channels": ["substack"],
            },
        ],
        "hashtag_strategy": {
            "primary": hashtags
            or ["#AI", "#LLMs", "#AIAgents", "#SourceBacked"],
            "rotation_rules": [
                "Use broad discovery tags only when the post has a source ledger.",
                "Pair one topic tag with one audience tag and one build-in-public tag.",
                "Remove tags that imply certainty beyond the claim review state.",
            ],
        },
        "keyword_strategy": {
            "primary": keywords
            or ["source-backed AI", "AI agents", "content studio"],
            "search_intent": [
                "ELI5 explainer",
                "practical implementation",
                "source-backed workflow",
            ],
        },
        "creator_packaging": {
            "hook_angles": hook_angles,
            "signature_phrases": [
                "ELI5 first, sources second.",
                "Here is what is proven and what still needs checking.",
                "Save the source trail, not just the hot take.",
            ],
            "caption_rhythm": [
                "Short hook.",
                "Plain-language mechanism.",
                "Source or caveat.",
                "Audience question.",
            ],
        },
        "do_not_say": [
            "Do not imply claims are proven when review status is needs_review.",
            "Do not use hype words that are absent from the source ledger.",
            "Do not target a broad audience before naming the useful segment.",
        ],
        "review_checklist": [
            "Confirm hashtags match the platform variant and not only the topic.",
            "Check every audience promise against source-backed content.",
            "Keep short-form copy ELI5 and reserve nuance for Substack.",
        ],
        "source_dependencies": package.content.get("source_dependencies", []),
        "distribution_claim_review_state": package.content.get(
            "claim_review_state", {}
        ),
        "strategy_context_summary": strategy_context.get("summary"),
    }
    artifact = ArtifactRecord(
        artifact_id=_agent_worker_artifact_id(
            run_id=message.run_id,
            message_id=message.message_id,
            workflow="influencer_strategy_v1",
            artifact_type=ArtifactType.GROWTH_STRATEGY,
        ),
        run_id=message.run_id,
        artifact_type=ArtifactType.GROWTH_STRATEGY,
        title=f"Influencer strategy: {topic}",
        uri="",
        content=content,
        provenance={
            "workflow": "influencer_strategy_v1",
            "created_by_agent_id": "influencer-strategy-agent",
            "message_id": str(message.message_id),
            "distribution_artifact_id": str(package.artifact_id),
            "source_artifact_ids": content["source_artifact_ids"],
            "source_ids": content["source_ids"],
            "claim_ids": content["claim_ids"],
            "generation_mode": "deterministic_growth_strategy",
        },
        source_ids=source_ids,
        reviewer_decisions=[
            {
                "reviewer_agent_id": "editor-in-chief",
                "status": ReviewDecisionStatus.NEEDS_REVISION.value,
                "notes": (
                    "Influencer strategy needs source, guardrail, and human review "
                    "before external publication."
                ),
                "blocking_issues": ["requires_growth_review"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
        revision_history=[
            {
                "actor": "influencer-strategy-agent",
                "workflow": "influencer_strategy_v1",
                "message_id": str(message.message_id),
                "note": (
                    "Created durable influencer strategy from current distribution "
                    "package and source-backed content artifacts."
                ),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
    )
    artifact.uri = (
        f"artifact://runs/{message.run_id}/growth-strategies/{artifact.artifact_id}"
    )
    return artifact


def _build_outreach_strategy_artifact(
    *,
    message: AgentMessage,
    package: ArtifactRecord,
    source_artifacts: list[ArtifactRecord],
    strategy_context: dict[str, Any],
) -> ArtifactRecord:
    topic = _growth_package_topic(package)
    source_ids = _growth_package_source_ids(package, source_artifacts)
    claim_ids = _growth_package_claim_ids(package, source_artifacts)
    outreach = package.content.get("outreach")
    outreach_brief = outreach if isinstance(outreach, dict) else {}
    base_pitch = str(
        outreach_brief.get("collaboration_pitch")
        or f"Would your audience want a source-backed ELI5 breakdown of {topic}?"
    )
    content = {
        "workflow": "outreach_strategy_v1",
        "topic": topic,
        "distribution_artifact_id": str(package.artifact_id),
        "source_artifact_ids": [
            str(source_artifact.artifact_id) for source_artifact in source_artifacts
        ],
        "source_ids": [str(source_id) for source_id in source_ids],
        "claim_ids": [str(claim_id) for claim_id in claim_ids],
        "community_targets": [
            {
                "community": "AI builders and applied engineering groups",
                "why": "They care about implementation detail and source quality.",
                "first_touch": "Share the ELI5 hook plus one caveat.",
            },
            {
                "community": "creator/operator communities",
                "why": "They care about reusable content workflows.",
                "first_touch": "Ask which claim they want stress-tested.",
            },
            {
                "community": "newsletter and Substack readers",
                "why": "They are a fit for the detailed source trail.",
                "first_touch": "Offer the long-form evidence path.",
            },
        ],
        "collaboration_pitches": [
            {
                "persona": "technical creator",
                "pitch": base_pitch,
            },
            {
                "persona": "operator community lead",
                "pitch": (
                    f"I can turn {topic} into a short ELI5 post, reel, and deeper "
                    "source-backed article for your audience."
                ),
            },
            {
                "persona": "newsletter writer",
                "pitch": (
                    "I can contribute a version that separates simple explanation, "
                    "evidence, caveats, and open questions."
                ),
            },
        ],
        "engagement_prompts": [
            "Which claim should be checked next?",
            "What would make this explanation more useful in your workflow?",
            "Do you want the source ledger or the ELI5 version first?",
        ],
        "risk_checks": [
            "Do not cold-pitch unsupported claims.",
            "Do not promise benchmarks, timelines, or capabilities missing from sources.",
            "Route skeptical replies into claim verification before responding publicly.",
        ],
        "do_not_say": [
            "Do not describe outreach as guaranteed growth.",
            "Do not imply endorsement from any source or community.",
            "Do not ask for shares before giving useful evidence.",
        ],
        "source_dependencies": package.content.get("source_dependencies", []),
        "distribution_claim_review_state": package.content.get(
            "claim_review_state", {}
        ),
        "strategy_context_summary": strategy_context.get("summary"),
    }
    artifact = ArtifactRecord(
        artifact_id=_agent_worker_artifact_id(
            run_id=message.run_id,
            message_id=message.message_id,
            workflow="outreach_strategy_v1",
            artifact_type=ArtifactType.GROWTH_STRATEGY,
        ),
        run_id=message.run_id,
        artifact_type=ArtifactType.GROWTH_STRATEGY,
        title=f"Outreach strategy: {topic}",
        uri="",
        content=content,
        provenance={
            "workflow": "outreach_strategy_v1",
            "created_by_agent_id": "outreach-agent",
            "message_id": str(message.message_id),
            "distribution_artifact_id": str(package.artifact_id),
            "source_artifact_ids": content["source_artifact_ids"],
            "source_ids": content["source_ids"],
            "claim_ids": content["claim_ids"],
            "generation_mode": "deterministic_growth_strategy",
        },
        source_ids=source_ids,
        reviewer_decisions=[
            {
                "reviewer_agent_id": "editor-in-chief",
                "status": ReviewDecisionStatus.NEEDS_REVISION.value,
                "notes": (
                    "Outreach strategy needs source, guardrail, and human review "
                    "before external publication."
                ),
                "blocking_issues": ["requires_outreach_review"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
        revision_history=[
            {
                "actor": "outreach-agent",
                "workflow": "outreach_strategy_v1",
                "message_id": str(message.message_id),
                "note": (
                    "Created durable outreach strategy from current distribution "
                    "package and source-backed content artifacts."
                ),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
    )
    artifact.uri = (
        f"artifact://runs/{message.run_id}/growth-strategies/{artifact.artifact_id}"
    )
    return artifact


def _growth_package_topic(package: ArtifactRecord) -> str:
    topic = package.content.get("topic")
    if isinstance(topic, str) and topic.strip():
        return topic.strip()
    return "source-backed AI content"


def _growth_package_platforms(package: ArtifactRecord) -> list[dict[str, Any]]:
    platforms = package.content.get("platforms")
    if not isinstance(platforms, list):
        return []
    return [platform for platform in platforms if isinstance(platform, dict)]


def _growth_package_terms(package: ArtifactRecord, key: str) -> list[str]:
    terms: list[str] = []
    for platform in _growth_package_platforms(package):
        values = platform.get(key)
        if isinstance(values, list):
            terms.extend(str(value) for value in values if str(value).strip())
    return _dedupe_preserve_order(terms)


def _growth_package_source_ids(
    package: ArtifactRecord,
    source_artifacts: list[ArtifactRecord],
) -> list[UUID]:
    source_ids = _unique_source_ids_from_artifacts(source_artifacts)
    for source_id in _uuid_list_from_values(
        [
            package.provenance.get("source_ids", []),
            package.content.get("source_ids", []),
        ]
    ):
        if source_id not in source_ids:
            source_ids.append(source_id)
    return source_ids


def _growth_package_claim_ids(
    package: ArtifactRecord,
    source_artifacts: list[ArtifactRecord],
) -> list[UUID]:
    claim_ids = _unique_claim_ids_from_artifacts(source_artifacts)
    for claim_id in _uuid_list_from_values(
        [
            package.provenance.get("claim_ids", []),
            package.content.get("claim_ids", []),
        ]
    ):
        if claim_id not in claim_ids:
            claim_ids.append(claim_id)
    return claim_ids


def _uuid_list_from_values(values: list[Any]) -> list[UUID]:
    ids: list[UUID] = []

    def collect(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, UUID):
            if value not in ids:
                ids.append(value)
            return
        if isinstance(value, str):
            try:
                item_id = UUID(value)
            except ValueError:
                return
            if item_id not in ids:
                ids.append(item_id)
            return
        if isinstance(value, dict):
            for nested_key in ("id", "source_id", "claim_id", "artifact_id"):
                collect(value.get(nested_key))
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                collect(item)

    for value in values:
        collect(value)
    return ids


def _platforms_from_payload(payload: dict[str, Any]) -> list[str]:
    platforms = payload.get("platforms")
    if isinstance(platforms, list):
        return [str(platform) for platform in platforms]
    platform = payload.get("platform")
    if isinstance(platform, str) and platform.strip():
        return [platform.strip()]
    return [
        "instagram_post",
        "instagram_reel",
        "linkedin",
        "x_thread",
        "substack",
    ]


def _provider_configuration_blocked_steps(
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    raw_steps = payload.get("blocked_steps")
    steps: list[dict[str, Any]] = []
    if isinstance(raw_steps, list):
        for index, raw_step in enumerate(raw_steps, start=1):
            if not isinstance(raw_step, dict):
                continue
            step_id = _payload_text(
                raw_step,
                "step_id",
                f"provider-configuration-step-{index}",
            )
            steps.append(
                {
                    "step_id": step_id,
                    "provider_id": _payload_text(
                        raw_step,
                        "provider_id",
                        "unknown-provider",
                    ),
                    "provider_type": _payload_text(
                        raw_step,
                        "provider_type",
                        "unknown",
                    ),
                    "title": _payload_text(
                        raw_step,
                        "title",
                        "Provider configuration blocker",
                    ),
                    "blockers": _payload_text_list(
                        raw_step,
                        "blockers",
                        ["Provider configuration is blocked."],
                    ),
                    "missing_env": _payload_text_list(raw_step, "missing_env", []),
                    "required_env": _payload_text_list(raw_step, "required_env", []),
                    "secret_files": _provider_configuration_secret_files(
                        raw_step.get("secret_files")
                    ),
                    "next_actions": _payload_text_list(
                        raw_step,
                        "next_actions",
                        [],
                    ),
                    "details": _safe_provider_failure_metadata(
                        raw_step.get("details", {})
                        if isinstance(raw_step.get("details"), dict)
                        else {}
                    ),
                }
            )
    if steps:
        return steps
    return [
        {
            "step_id": "provider-configuration",
            "provider_id": "unknown-provider",
            "provider_type": "unknown",
            "title": "Provider configuration blocker",
            "blockers": [
                _payload_text(
                    payload,
                    "required_action",
                    "Provider configuration is blocked.",
                )
            ],
            "missing_env": [],
            "required_env": [],
            "secret_files": [],
            "next_actions": [],
            "details": {},
        }
    ]


def _provider_configuration_secret_files(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    secret_files: list[dict[str, Any]] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        secret_files.append(
            {
                "env_name": _payload_text(raw, "env_name", "UNKNOWN_ENV"),
                "file_env_name": _payload_text(raw, "file_env_name", "UNKNOWN_FILE"),
                "status": _payload_text(raw, "status", "unknown"),
                "configured": bool(raw.get("configured")),
                "path": _payload_optional_text(raw, "path"),
                "detail": _payload_text(raw, "detail", "Secret-file state unknown."),
            }
        )
    return secret_files


def _provider_configuration_recovery_checks(
    blocked_steps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for step in blocked_steps:
        step_id = str(step["step_id"])
        provider_type = str(step["provider_type"])
        missing_env = step.get("missing_env") or []
        checks.append(
            {
                "id": f"{step_id}_configuration",
                "status": "blocked",
                "owner_agent_id": _provider_configuration_owner(provider_type),
                "provider_id": step["provider_id"],
                "provider_type": provider_type,
                "missing_env": missing_env,
                "detail": (
                    "Repair non-secret provider configuration and rerun provider "
                    "readiness before live provider smoke."
                ),
            }
        )
        if step.get("secret_files"):
            checks.append(
                {
                    "id": f"{step_id}_secret_files",
                    "status": "blocked",
                    "owner_agent_id": "agent-harness-engineer",
                    "provider_id": step["provider_id"],
                    "provider_type": provider_type,
                    "secret_files": step["secret_files"],
                    "detail": (
                        "Verify secret-file path, presence, permissions, and empty-file "
                        "state without reading or echoing secret values."
                    ),
                }
            )
        if provider_type == "web_search":
            checks.append(
                {
                    "id": f"{step_id}_source_grounding_recheck",
                    "status": "required_after_configuration",
                    "owner_agent_id": "web-research-agent",
                    "provider_id": step["provider_id"],
                    "provider_type": provider_type,
                    "detail": (
                        "After search provider configuration is ready, run a "
                        "source-backed research smoke before claiming grounded content."
                    ),
                }
            )
    return checks


def _provider_configuration_owner(provider_type: str) -> str:
    if provider_type in {"gemma4_hf_endpoint", "realtime_audio", "reranker"}:
        return "inference-systems-engineer"
    if provider_type == "web_search":
        return "agent-harness-engineer"
    return "agent-harness-engineer"


def _provider_configuration_required_actions(
    blocked_steps: list[dict[str, Any]],
) -> list[str]:
    actions = [
        "Do not request, echo, or persist provider secret values; use only env names, secret-file statuses, and readiness metadata.",
        "Repair missing provider configuration outside durable artifacts, then rerun provider readiness.",
        "Rerun provider smoke after configuration is repaired and attach the new ledger before unblocking voice or source-backed content.",
    ]
    for step in blocked_steps:
        for action in step.get("next_actions") or []:
            if action not in actions:
                actions.append(str(action))
    if any(step.get("provider_type") == "web_search" for step in blocked_steps):
        actions.append(
            "After web-search configuration is ready, rebuild retrieval quality and source ledgers before trusting generated claims."
        )
    return actions


def _safe_provider_failure_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _safe_provider_failure_metadata_value(value)
        for key, value in metadata.items()
        if not _provider_metadata_key_is_sensitive(key)
    }


def _provider_metadata_key_is_sensitive(key: Any) -> bool:
    if not isinstance(key, str) or not key.strip():
        return False
    normalized = _normalize_provider_metadata_key(key)
    compact = normalized.replace("_", "")
    sensitive_exact = {
        "access_token",
        "api_key",
        "api_secret",
        "authorization",
        "client_secret",
        "private_key",
        "raw_request",
        "raw_response",
        "refresh_token",
        "session_token",
        "signed_url",
        "token",
        "websocket_url",
    }
    sensitive_compact = {item.replace("_", "") for item in sensitive_exact}
    if normalized in sensitive_exact or compact in sensitive_compact:
        return True
    if (
        "credential" in compact
        or "bearer" in compact
        or "authorization" in compact
    ):
        return True
    return normalized.endswith(("_key", "_secret", "_token", "_password"))


def _normalize_provider_metadata_key(key: str) -> str:
    camel_split = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key.strip())
    return re.sub(r"[^a-z0-9]+", "_", camel_split.lower()).strip("_")


def _safe_provider_failure_metadata_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _safe_provider_failure_metadata(value)
    if isinstance(value, list):
        return [_safe_provider_failure_metadata_value(item) for item in value]
    if isinstance(value, str):
        return _redact_provider_failure_text(value)
    return value


def _redact_provider_failure_text(value: str) -> str:
    redacted = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [redacted]", value)
    redacted = re.sub(r"hf_[A-Za-z0-9]{20,}", "hf_[redacted]", redacted)
    redacted = re.sub(r"tvly-[A-Za-z0-9-]{20,}", "tvly-[redacted]", redacted)
    return redacted


def _realtime_provider_failure_component(*, stage: str, reason: str) -> str:
    search_text = f"{stage} {reason}".lower()
    if "kokoro" in search_text or "tts" in search_text:
        return "kokoro_tts"
    if "gemma" in search_text or "generation" in search_text or "hf" in search_text:
        return "gemma_audio_reasoner"
    if "livekit" in search_text or "room" in search_text or "participant" in search_text:
        return "livekit_transport"
    if "voice-edge" in search_text or "vad" in search_text or "barge" in search_text:
        return "rust_voice_edge"
    return "gemma_kokoro_voice_runtime"


def _realtime_provider_failure_recovery_checks(
    *,
    failed_component: str,
    payload: dict[str, Any],
) -> list[dict[str, str]]:
    checks = [
        {
            "id": "runtime_preflight",
            "owner_agent_id": "observability-agent",
            "status": "required",
            "detail": (
                "Refresh LiveKit, Gemma/HF, Kokoro, Rust voice edge, and "
                "context-pruning readiness before retrying provider-backed voice."
            ),
        },
        {
            "id": "session_bound_provider_smoke",
            "owner_agent_id": "inference-systems-engineer",
            "status": "required",
            "detail": (
                "Run Gemma/Kokoro session-bound provider smoke with live calls only "
                "after operator confirmation."
            ),
        },
        {
            "id": "voice_timing_ledger",
            "owner_agent_id": "observability-agent",
            "status": "required",
            "detail": (
                "Build realtime voice timing proof for LiveKit, Gemma first token, "
                "Kokoro first audio, cancellation, and output-clear stages."
            ),
        },
        {
            "id": "conversation_history_integrity",
            "owner_agent_id": "agent-harness-engineer",
            "status": "required",
            "detail": (
                "Verify the failed turn preserved user context without creating an "
                "assistant message that was never spoken."
            ),
        },
    ]
    if failed_component == "gemma_audio_reasoner":
        checks.append(
            {
                "id": "gemma_streaming_route",
                "owner_agent_id": "inference-systems-engineer",
                "status": "required",
                "detail": (
                    "Verify Gemma 4 E4B HF endpoint/router configuration, streaming "
                    "payload shape, token redaction, and TTFT before retry."
                ),
            }
        )
    if failed_component == "kokoro_tts":
        checks.append(
            {
                "id": "kokoro_audio_route",
                "owner_agent_id": "inference-systems-engineer",
                "status": "required",
                "detail": (
                    "Verify hosted or local Kokoro route, first-audio latency, base64 "
                    "decode, and non-empty PCM chunks before retry."
                ),
            }
        )
    if payload.get("realtime_session_id"):
        checks.append(
            {
                "id": "participant_presence",
                "owner_agent_id": "observability-agent",
                "status": "required",
                "detail": (
                    "Confirm a fresh Gemma/Kokoro LiveKit participant ready event for "
                    "the same realtime session."
                ),
            }
        )
    return checks


def _payload_text(
    payload: dict[str, Any],
    key: str,
    default: str,
) -> str:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _payload_optional_text(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _payload_text_list(
    payload: dict[str, Any],
    key: str,
    default: list[str],
) -> list[str]:
    value = payload.get(key)
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items or default
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return default


def _next_citation_number(sources: list[SourceRecord]) -> int:
    current = 0
    for source in sources:
        citation_id = source.citation_id.strip().upper()
        if citation_id.startswith("S") and citation_id[1:].isdigit():
            current = max(current, int(citation_id[1:]))
    return current + 1
