from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from all_about_llms.local_provider_config import LocalProviderConfigEnvName


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    WAITING_FOR_HUMAN = "waiting_for_human"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class ClaimSupportStatus(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    NEEDS_REVIEW = "needs_review"


class SourceQualityStatus(StrEnum):
    STRONG = "strong"
    ACCEPTABLE = "acceptable"
    NEEDS_REVIEW = "needs_review"
    WEAK = "weak"


class SourceFreshnessStatus(StrEnum):
    CURRENT = "current"
    ACCEPTABLE = "acceptable"
    EVERGREEN = "evergreen"
    UNKNOWN = "unknown"
    STALE = "stale"


class ReviewDecisionStatus(StrEnum):
    APPROVED = "approved"
    APPROVED_WITH_NOTES = "approved_with_notes"
    NEEDS_REVISION = "needs_revision"
    BLOCKED = "blocked"


class GuardrailAuditStatus(StrEnum):
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    BLOCKED = "blocked"


class PublishReadinessStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class ProviderReadinessStatus(StrEnum):
    READY = "ready"
    MISSING_CONFIG = "missing_config"
    TOOL_BOUNDARY = "tool_boundary"


class ProviderSmokeStepStatus(StrEnum):
    PASSED = "passed"
    BLOCKED = "blocked"
    FAILED = "failed"
    NOT_RUN = "not_run"
    TOOL_BOUNDARY = "tool_boundary"


class ProviderSmokeRunStatus(StrEnum):
    PASSED = "passed"
    BLOCKED = "blocked"
    FAILED = "failed"
    NEEDS_LIVE_SMOKE = "needs_live_smoke"
    NEEDS_REVIEW = "needs_review"


class FoundationAuditStatus(StrEnum):
    PASS = "pass"
    NEEDS_ATTENTION = "needs_attention"
    FAIL = "fail"


class RuntimeHealthStatus(StrEnum):
    READY = "ready"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class VoiceAgentPresenceStatus(StrEnum):
    READY = "ready"
    STALE = "stale"
    MISSING = "missing"


class VoiceAgentProcessStatus(StrEnum):
    DISABLED = "disabled"
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    EXITED = "exited"
    FAILED = "failed"


class LocalLiveKitProcessMode(StrEnum):
    NATIVE = "native"
    COMPOSE = "compose"


class ResearchFreshnessStatus(StrEnum):
    READY = "ready"
    NEEDS_REFRESH = "needs_refresh"
    BLOCKED = "blocked"


class RetrievalQualityStatus(StrEnum):
    READY = "ready"
    NEEDS_RERANK = "needs_rerank"
    NEEDS_MORE_RECALL = "needs_more_recall"
    BLOCKED = "blocked"


class RealtimeSessionStatus(StrEnum):
    ACTIVE = "active"
    ENDED = "ended"
    FAILED = "failed"


class RealtimeControlAction(StrEnum):
    INTERRUPT = "interrupt"
    RESUME = "resume"
    STOP_OUTPUT = "stop_output"


class AgentTaskStatus(StrEnum):
    ACCEPTED = "accepted"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_HUMAN = "waiting_for_human"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELED = "canceled"


class WorkerProfileStatus(StrEnum):
    PAUSED = "paused"
    ACTIVE = "active"
    STOPPED = "stopped"


class WorkerProfileExecutionMode(StrEnum):
    WORKER_CYCLE = "worker_cycle"
    AUTONOMOUS_PASS = "autonomous_pass"


class FeedbackStatus(StrEnum):
    OPEN = "open"
    ROUTED = "routed"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class ConversationRouteIntent(StrEnum):
    AUTO = "auto"
    CREATE_CONTENT = "create_content"
    REVISE_CONTENT = "revise_content"
    ROUTE_TASK = "route_task"
    RECORD_ONLY = "record_only"


class ArtifactType(StrEnum):
    REALTIME_CONVERSATION_BRIEF = "realtime_conversation_brief"
    REALTIME_DIALOGUE_LEDGER = "realtime_dialogue_ledger"
    REALTIME_VOICE_TIMING_LEDGER = "realtime_voice_timing_ledger"
    VOICE_SETUP_PROOF = "voice_setup_proof"
    CONVERSATION_HANDOFF = "conversation_handoff"
    INTENT_ROUTE_PLAN = "intent_route_plan"
    POST = "post"
    REEL_SCRIPT = "reel_script"
    SUBSTACK_ARTICLE = "substack_article"
    SOCIAL_PACKAGE = "social_package"
    GROWTH_STRATEGY = "growth_strategy"
    DATA_BRIEF = "data_brief"
    CLAIM_REVISION_PLAN = "claim_revision_plan"
    CLAIM_REVISION_LEDGER = "claim_revision_ledger"
    A2A_CONTRACT_AUDIT = "a2a_contract_audit"
    A2A_COLLABORATION_GRAPH = "a2a_collaboration_graph"
    SKILL_USAGE_LEDGER = "skill_usage_ledger"
    CONTEXT_PACKET = "context_packet"
    RUN_RESUME_PLAN = "run_resume_plan"
    RUN_REPLAY_LEDGER = "run_replay_ledger"
    RUN_HEALTH_REPORT = "run_health_report"
    WORKER_PROFILE_HEARTBEAT_LEDGER = "worker_profile_heartbeat_ledger"
    AUTOPILOT_LAUNCH_LEDGER = "autopilot_launch_ledger"
    COCKPIT_WALKTHROUGH_LEDGER = "cockpit_walkthrough_ledger"
    RUNTIME_HEALTH_LEDGER = "runtime_health_ledger"
    MODEL_ROUTING_LEDGER = "model_routing_ledger"
    PROVIDER_OPERATIONS_LEDGER = "provider_operations_ledger"
    PROVIDER_SMOKE_LEDGER = "provider_smoke_ledger"
    FOUNDATION_AUDIT = "foundation_audit"
    RESEARCH_FRESHNESS_LEDGER = "research_freshness_ledger"
    RETRIEVAL_QUALITY_LEDGER = "retrieval_quality_ledger"
    MULTIMODAL_INTAKE_LEDGER = "multimodal_intake_ledger"
    MULTIMODAL_REVIEW = "multimodal_review"
    ARTIFACT_INDEX = "artifact_index"
    FEEDBACK_REQUIREMENTS = "feedback_requirements"
    FEEDBACK_RESOLUTION_LEDGER = "feedback_resolution_ledger"
    ARCHITECTURE_REVIEW = "architecture_review"
    UX_REVIEW = "ux_review"
    PLANNING_SURFACE_REVIEW = "planning_surface_review"
    VISUAL_BRIEF = "visual_brief"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    HTML_NOTE = "html_note"
    OBSIDIAN_NOTE = "obsidian_note"
    OBSIDIAN_MEMORY_PROMOTION = "obsidian_memory_promotion"
    PROJECT_MEMORY_RETRIEVAL_LEDGER = "project_memory_retrieval_ledger"
    SYSTEM_PLAN = "system_plan"
    SOURCE_LEDGER = "source_ledger"


DEFAULT_TARGET_FORMATS = ["post", "reel", "substack"]


class AgentCard(BaseModel):
    """A2A-style public contract for a specialist agent."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    role: str
    capabilities: list[str]
    allowed_models: list[str]
    allowed_tools: list[str]
    inputs: list[str]
    outputs: list[str]
    handoff_rules: list[str]
    guardrails: list[str]
    skill_ids: list[str] = Field(default_factory=list)


class AgentSkillCard(BaseModel):
    """Reusable project-owned workflow contract for one or more agents."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    description: str
    applies_to_agents: list[str]
    capabilities: list[str]
    workflow_steps: list[str]
    required_inputs: list[str]
    outputs: list[str]
    guardrails: list[str]
    source_path: str


class RunCreateRequest(BaseModel):
    goal: str = Field(min_length=1)
    input_mode: str = "text"
    initial_context: dict[str, Any] = Field(default_factory=dict)


class ConversationTurn(BaseModel):
    turn_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    speaker: str
    modality: str
    transcript: str = Field(min_length=1)
    audio_uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationTurnCreate(BaseModel):
    speaker: str = "user"
    modality: str = "text"
    transcript: str = Field(min_length=1)
    audio_uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrchestrationRequest(BaseModel):
    transcript: str = Field(min_length=1)
    modality: str = "text"
    speaker: str = "user"
    audio_uri: str | None = None
    topic: str | None = None
    target_formats: list[str] = Field(
        default_factory=lambda: list(DEFAULT_TARGET_FORMATS)
    )
    require_human_feedback: bool = True


class OrchestrationResult(BaseModel):
    run_id: UUID
    turn_id: UUID
    task_message_ids: list[UUID]
    source_ids: list[UUID]
    claim_ids: list[UUID]
    artifact_ids: list[UUID]
    feedback_gate_opened: bool
    summary: str


class RealtimeSessionCreateRequest(BaseModel):
    provider: str | None = None
    voice: str | None = None
    instructions: str | None = None
    transport_framework: str | None = None
    room_name: str | None = None
    participant_identity: str | None = None
    agent_participant_identity: str | None = None
    context_window_turns: int = Field(default=4, ge=1, le=12)
    summarize_after_turns: int = Field(default=3, ge=1, le=12)
    dry_run: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class RealtimeTransportGrant(BaseModel):
    framework: str = "livekit"
    url: str | None = None
    room_name: str | None = None
    participant_identity: str | None = None
    agent_identity: str | None = None
    token: str | None = None
    has_token: bool = False
    token_persisted: bool = False
    expires_at_unix: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RealtimeSessionCreateResult(BaseModel):
    run_id: UUID
    realtime_session_id: UUID
    provider: str
    session_id: str
    client_secret: str | None = None
    websocket_url: str | None = None
    transport: RealtimeTransportGrant | None = None
    expires_at_unix: int | None = None
    event_id: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RealtimeSessionRecord(BaseModel):
    realtime_session_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    provider: str
    provider_session_id: str
    voice: str | None = None
    audio_mode: str = "speech_to_speech"
    instructions: str
    has_client_secret: bool = False
    has_websocket_url: bool = False
    transport_framework: str | None = None
    room_name: str | None = None
    participant_identity: str | None = None
    agent_participant_identity: str | None = None
    has_transport_token: bool = False
    context_window_turns: int = 4
    summarize_after_turns: int = 3
    expires_at_unix: int | None = None
    status: RealtimeSessionStatus = RealtimeSessionStatus.ACTIVE
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MultimodalAssetInput(BaseModel):
    asset_uri: str = Field(min_length=1)
    modality: str = Field(min_length=1)
    description: str | None = None
    source: str = "user_input"
    metadata: dict[str, Any] = Field(default_factory=dict)


class RealtimeTurnCreate(BaseModel):
    speaker: str = "user"
    transcript: str | None = Field(default=None, min_length=1)
    modality: str = "voice"
    audio_uri: str | None = None
    assets: list[MultimodalAssetInput] = Field(default_factory=list)
    record_multimodal_intake: bool = True
    interrupted: bool = False
    route_turn: bool = True
    create_realtime_brief_task: bool = True
    topic: str | None = None
    target_formats: list[str] = Field(
        default_factory=lambda: list(DEFAULT_TARGET_FORMATS)
    )
    intent: ConversationRouteIntent = ConversationRouteIntent.AUTO
    require_human_feedback: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class RealtimeSpokenResponsePlan(BaseModel):
    realtime_session_id: UUID
    provider: str
    provider_session_id: str
    response_id: UUID = Field(default_factory=uuid4)
    voice: str | None = None
    audio_mode: str
    output_channel: str
    source_turn_id: UUID
    response_turn_id: UUID | None = None
    text: str = Field(min_length=1)
    interrupt_previous: bool = False
    gemma_generation_id: str | None = None
    kokoro_buffer_id: str | None = None
    audio_track_id: str | None = None
    audio_chunk_count: int = 0
    canceled_at: datetime | None = None
    cancellation_reason: str | None = None
    provider_payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RealtimeTurnResult(BaseModel):
    realtime_session: RealtimeSessionRecord
    conversation_turn: ConversationTurn | None = None
    routed_result: "ConversationRouteResult | None" = None
    spoken_response: RealtimeSpokenResponsePlan | None = None
    brief_task_message_id: UUID | None = None
    event_id: int | None = None
    summary: str


class RealtimeSessionControlRequest(BaseModel):
    action: RealtimeControlAction
    reason: str | None = None
    cancel_gemma: bool | None = None
    clear_kokoro_buffers: bool | None = None
    stop_livekit_audio: bool | None = None
    interrupted_response_id: str | None = None
    client_audio_timestamp_ms: int | None = Field(default=None, ge=0)
    create_followup_task: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class RealtimeSessionControlResult(BaseModel):
    run_id: UUID
    realtime_session_id: UUID
    action: RealtimeControlAction
    event_id: int | None = None
    followup_task_message_id: UUID | None = None
    summary: str


class RealtimeDialogueLedgerRequest(BaseModel):
    record_artifact: bool = True
    event_limit: int = Field(default=250, ge=1, le=1000)
    turn_limit: int = Field(default=100, ge=1, le=500)
    include_transcript_preview: bool = True


class RealtimeDialogueSessionEntry(BaseModel):
    realtime_session_id: UUID
    provider: str
    status: RealtimeSessionStatus
    voice: str | None = None
    audio_mode: str
    has_client_secret: bool
    has_websocket_url: bool
    transport_framework: str | None = None
    room_name: str | None = None
    participant_identity: str | None = None
    agent_participant_identity: str | None = None
    has_transport_token: bool = False
    context_window_turns: int = 4
    summarize_after_turns: int = 3
    turn_count: int = 0
    voice_turn_count: int = 0
    interrupted_turn_count: int = 0
    assistant_response_turn_count: int = 0
    last_turn_at: datetime | None = None


class RealtimeDialogueTurnEntry(BaseModel):
    turn_id: UUID
    speaker: str
    modality: str
    realtime_session_id: UUID | None = None
    transcript_preview: str | None = None
    interrupted: bool = False
    has_audio: bool = False
    responds_to_turn_id: UUID | None = None
    response_turn_id: UUID | None = None
    created_at: datetime
    metadata_keys: list[str] = Field(default_factory=list)


class RealtimeDialogueFollowupEntry(BaseModel):
    message_id: UUID
    sender_agent_id: str
    recipient_agent_id: str
    task_type: str
    status: AgentTaskStatus
    requires_human_feedback: bool
    source_turn_id: UUID | None = None
    response_turn_id: UUID | None = None
    interrupted: bool = False


class RealtimeDialogueControlEntry(BaseModel):
    event_id: int | None = None
    realtime_session_id: UUID
    action: RealtimeControlAction
    reason: str | None = None
    followup_task_message_id: UUID | None = None
    resolved_by_turn_id: UUID | None = None
    created_at: datetime


class RealtimeDialogueSpokenResponseEntry(BaseModel):
    event_id: int | None = None
    realtime_session_id: UUID
    provider: str
    voice: str | None = None
    output_channel: str
    source_turn_id: UUID
    response_turn_id: UUID | None = None
    text_preview: str | None = None
    interrupt_previous: bool = False
    created_at: datetime


class RealtimeDialogueLedgerResult(BaseModel):
    run_id: UUID
    status: str
    session_count: int
    active_session_count: int
    turn_count: int
    user_turn_count: int
    assistant_turn_count: int
    voice_turn_count: int
    interrupted_turn_count: int
    assistant_response_turn_count: int
    unanswered_user_turn_ids: list[UUID] = Field(default_factory=list)
    unacknowledged_interruption_turn_ids: list[UUID] = Field(default_factory=list)
    pending_followup_task_ids: list[UUID] = Field(default_factory=list)
    open_feedback_count: int = 0
    control_event_count: int = 0
    unresolved_control_event_ids: list[int] = Field(default_factory=list)
    control_action_counts: dict[str, int] = Field(default_factory=dict)
    spoken_response_plan_count: int = 0
    sessions: list[RealtimeDialogueSessionEntry] = Field(default_factory=list)
    turns: list[RealtimeDialogueTurnEntry] = Field(default_factory=list)
    followup_tasks: list[RealtimeDialogueFollowupEntry] = Field(default_factory=list)
    control_events: list[RealtimeDialogueControlEntry] = Field(default_factory=list)
    spoken_responses: list[RealtimeDialogueSpokenResponseEntry] = Field(
        default_factory=list
    )
    recommended_next_actions: list[str] = Field(default_factory=list)
    ledger_artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str


class RealtimeVoiceAgentEventCreate(BaseModel):
    event_type: str = Field(min_length=1)
    voice_agent_event_uid: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    agent_created_at: datetime | None = None
    source: str = "livekit_data_channel"


class RealtimeVoiceAgentEventRecordResult(BaseModel):
    run_id: UUID
    realtime_session_id: UUID
    event_id: int
    event_type: str
    materialized_turn_id: UUID | None = None
    materialized_speaker: str | None = None
    followup_task_message_id: UUID | None = None
    followup_kind: str | None = None
    followup_worker_agent_ids: list[str] = Field(default_factory=list)
    followup_worker_use_gemma: bool | None = None
    summary: str


class VoiceAgentPresenceResult(BaseModel):
    run_id: UUID
    realtime_session_id: UUID | None = None
    status: VoiceAgentPresenceStatus
    observed: bool = False
    stale: bool = False
    stale_after_seconds: int
    event_age_seconds: float | None = Field(default=None, ge=0)
    latest_event_id: int | None = None
    latest_event_type: str | None = None
    latest_event_created_at: datetime | None = None
    provider: str | None = None
    provider_session_id: str | None = None
    transport_framework: str | None = None
    room_name: str | None = None
    agent_participant_identity: str | None = None
    livekit_sender_identity: str | None = None
    probe_id: str | None = None
    audio_input_model: str | None = None
    reasoning_model: str | None = None
    audio_output_model: str | None = None
    evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    summary: str


class VoiceAgentProcessStartRequest(BaseModel):
    dev: bool = False
    unregistered: bool = False
    force_restart: bool = False


class VoiceAgentProcessStatusResult(BaseModel):
    enabled: bool
    status: VoiceAgentProcessStatus
    running: bool = False
    pid: int | None = None
    returncode: int | None = None
    last_error: str | None = None
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    command: list[str] = Field(default_factory=list)
    log_tail: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    summary: str


class LocalLiveKitProcessStartRequest(BaseModel):
    mode: LocalLiveKitProcessMode = LocalLiveKitProcessMode.NATIVE
    force_restart: bool = False


class LocalLiveKitProcessStatusResult(BaseModel):
    enabled: bool
    mode: LocalLiveKitProcessMode
    status: VoiceAgentProcessStatus
    running: bool = False
    pid: int | None = None
    returncode: int | None = None
    last_error: str | None = None
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    command: list[str] = Field(default_factory=list)
    log_tail: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    summary: str


class WorkerSchedulerProcessStartRequest(BaseModel):
    run_id: UUID
    execution_mode: WorkerProfileExecutionMode = WorkerProfileExecutionMode.AUTONOMOUS_PASS
    max_profiles: int = Field(default=25, ge=1, le=250)
    poll_interval_seconds: float = Field(default=5.0, ge=0.25, le=3600.0)
    force_restart: bool = False


class WorkerSchedulerProcessStatusResult(BaseModel):
    enabled: bool
    status: VoiceAgentProcessStatus
    running: bool = False
    pid: int | None = None
    returncode: int | None = None
    last_error: str | None = None
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    run_id: UUID | None = None
    execution_mode: WorkerProfileExecutionMode = WorkerProfileExecutionMode.AUTONOMOUS_PASS
    max_profiles: int = Field(default=25, ge=1, le=250)
    poll_interval_seconds: float = Field(default=5.0, ge=0.25, le=3600.0)
    command: list[str] = Field(default_factory=list)
    log_tail: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    summary: str


class RealtimeVoiceTimingLedgerRequest(BaseModel):
    record_artifact: bool = True
    event_limit: int = Field(default=500, ge=1, le=2000)


class RealtimeVoiceTimingStageEntry(BaseModel):
    stage_id: str
    title: str
    status: str
    latency_ms: float | None = Field(default=None, ge=0)
    evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    event_ids: list[int] = Field(default_factory=list)


class RealtimeVoiceTimingTurnEntry(BaseModel):
    turn_id: str | None = None
    response_id: str | None = None
    realtime_session_id: UUID | None = None
    speech_start_to_turn_commit_ms: float | None = Field(default=None, ge=0)
    turn_commit_to_agent_turn_ms: float | None = Field(default=None, ge=0)
    speech_start_to_turn_start_ms: float | None = Field(default=None, ge=0)
    turn_start_to_gemma_start_ms: float | None = Field(default=None, ge=0)
    gemma_start_to_first_text_ms: float | None = Field(default=None, ge=0)
    gemma_start_to_first_audio_ms: float | None = Field(default=None, ge=0)
    turn_start_to_first_audio_ms: float | None = Field(default=None, ge=0)
    barge_in_to_cancelled_ms: float | None = Field(default=None, ge=0)
    failure_stage: str | None = None
    failure_reason: str | None = None
    failed_at_ms: float | None = Field(default=None, ge=0)
    event_ids: list[int] = Field(default_factory=list)


class RealtimeVoiceTimingLedgerResult(BaseModel):
    run_id: UUID
    status: str
    session_count: int
    event_count: int
    measured_stage_count: int
    missing_stage_count: int
    stages: list[RealtimeVoiceTimingStageEntry] = Field(default_factory=list)
    turns: list[RealtimeVoiceTimingTurnEntry] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)
    ledger_artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str


class VoiceSetupProofStep(BaseModel):
    id: str
    label: str
    status: str
    detail: str
    next_action: str | None = None
    required: bool = True


class VoiceSetupProofRequest(BaseModel):
    action: str = Field(min_length=1)
    status: str = Field(min_length=1)
    trigger: str = "voice_panel"
    provider: str | None = None
    realtime_session_id: UUID | None = None
    transport_framework: str | None = None
    readiness_status: str | None = None
    livekit_process_status: str | None = None
    voice_agent_process_status: str | None = None
    primary_blocker: VoiceSetupProofStep | None = None
    steps: list[VoiceSetupProofStep] = Field(default_factory=list, max_length=20)
    event_summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    record_artifact: bool = True


class VoiceSetupProofResult(BaseModel):
    run_id: UUID
    status: str
    action: str
    artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str
    artifact: "ArtifactRecord | None" = None


class RealtimeSessionStatusUpdate(BaseModel):
    status: RealtimeSessionStatus = RealtimeSessionStatus.ENDED
    reason: str | None = None


class ProviderSecretFileStatus(BaseModel):
    env_name: str
    file_env_name: str
    status: str
    configured: bool = False
    path: str | None = None
    detail: str


class LocalSecretFileEnvName(StrEnum):
    HF_TOKEN = "HF_TOKEN"
    LIVEKIT_API_KEY = "LIVEKIT_API_KEY"
    LIVEKIT_API_SECRET = "LIVEKIT_API_SECRET"
    TAVILY_API_KEY = "TAVILY_API_KEY"
    INSTAGRAM_ACCESS_TOKEN = "INSTAGRAM_ACCESS_TOKEN"
    LINKEDIN_ACCESS_TOKEN = "LINKEDIN_ACCESS_TOKEN"
    X_ACCESS_TOKEN = "X_ACCESS_TOKEN"
    X_API_KEY = "X_API_KEY"
    SUBSTACK_API_TOKEN = "SUBSTACK_API_TOKEN"


class LocalSecretFileWriteRequest(BaseModel):
    env_name: LocalSecretFileEnvName
    secret_value: str = Field(min_length=1, max_length=16_384)


class LocalSecretFileWriteResult(BaseModel):
    env_name: LocalSecretFileEnvName
    file_env_name: str
    status: str
    configured: bool
    path: str
    detail: str


class LocalProviderConfigWriteRequest(BaseModel):
    env_name: LocalProviderConfigEnvName
    config_value: str = Field(min_length=1, max_length=4096)


class LocalProviderConfigWriteResult(BaseModel):
    env_name: LocalProviderConfigEnvName
    status: str
    configured: bool
    config_file_env_name: str
    path: str
    detail: str


class LocalLiveKitDevConfigResult(BaseModel):
    status: str
    configured: bool
    configured_env: list[str]
    config_file_env_name: str
    secret_file_env_names: list[str]
    paths: dict[str, str]
    detail: str


class ProviderReadinessItem(BaseModel):
    provider_id: str
    provider_type: str
    display_name: str
    status: ProviderReadinessStatus
    selected: bool = False
    required_env: list[str] = Field(default_factory=list)
    configured_env: list[str] = Field(default_factory=list)
    missing_env: list[str] = Field(default_factory=list)
    model_ids: list[str] = Field(default_factory=list)
    endpoint_configured: bool | None = None
    capabilities: list[str] = Field(default_factory=list)
    boundary: str
    notes: str
    documentation_url: str | None = None
    next_actions: list[str] = Field(default_factory=list)
    secret_files: list[ProviderSecretFileStatus] = Field(default_factory=list)


class ProviderSmokeTestStep(BaseModel):
    step_id: str
    provider_id: str
    provider_type: str
    title: str
    status: str
    required: bool = True
    live_call: bool = False
    cockpit_action: str | None = None
    api_path: str | None = None
    documentation_url: str | None = None
    required_env: list[str] = Field(default_factory=list)
    missing_env: list[str] = Field(default_factory=list)
    expected_evidence: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class ProviderReadinessResult(BaseModel):
    default_realtime_provider: str
    selected_web_search_provider: str
    providers: list[ProviderReadinessItem]
    ready_provider_ids: list[str] = Field(default_factory=list)
    missing_provider_ids: list[str] = Field(default_factory=list)
    tool_boundary_provider_ids: list[str] = Field(default_factory=list)
    missing_required_env: list[str] = Field(default_factory=list)
    provider_backed_smoke_ready: bool = False
    smoke_test_plan: list[ProviderSmokeTestStep] = Field(default_factory=list)
    demo_walkthrough: list[str] = Field(default_factory=list)
    summary: str


class VoiceRuntimeReadinessCheck(BaseModel):
    check_id: str
    label: str
    status: RuntimeHealthStatus
    required: bool = True
    evidence: list[str] = Field(default_factory=list)
    missing_env: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VoiceRuntimeReadinessResult(BaseModel):
    status: RuntimeHealthStatus
    selected_provider: str
    transport_framework: str
    audio_input_model: str
    reasoning_model: str
    audio_output_model: str
    preflight_livekit: bool = False
    preflight_edge: bool = False
    preflight_agent: bool = False
    preflight_gemma: bool = False
    preflight_tts: bool = False
    checks: list[VoiceRuntimeReadinessCheck] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    summary: str


class ProviderOperationsLedgerRequest(BaseModel):
    record_artifact: bool = True
    event_limit: int = Field(default=250, ge=1, le=1000)
    include_artifact_provenance: bool = True


class ProviderOperationEntry(BaseModel):
    operation_type: str
    provider: str | None = None
    agent_id: str | None = None
    model_id: str | None = None
    tool_name: str | None = None
    latency_class: str | None = None
    end_to_end_latency_ms: float | None = Field(default=None, ge=0)
    provider_latency_ms: float | None = Field(default=None, ge=0)
    fallback_reason: str | None = None
    smoke_proof_status: str | None = None
    status: str
    source_event_id: int | None = None
    source_artifact_id: UUID | None = None
    source_session_id: UUID | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ProviderOperationsLedgerResult(BaseModel):
    run_id: UUID
    event_count: int
    realtime_session_count: int
    provider_operation_count: int
    model_operation_count: int
    tool_operation_count: int
    provider_fallback_count: int
    policy_denial_count: int
    provider_counts: dict[str, int] = Field(default_factory=dict)
    operation_type_counts: dict[str, int] = Field(default_factory=dict)
    operations: list[ProviderOperationEntry] = Field(default_factory=list)
    ledger_artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str


class ProviderSmokeRunRequest(BaseModel):
    record_artifact: bool = True
    execute_live_calls: bool = False
    topic: str = "provider smoke test for OpenRouter LiveKit content studio"
    realtime_provider: str | None = None
    realtime_session_id: UUID | None = None
    require_voice_agent_presence: bool = False
    voice_agent_presence_stale_after_seconds: int = Field(default=60, ge=5, le=3600)
    max_voice_audio_artifact_age_seconds: int = Field(default=120, ge=5, le=3600)
    voice: str | None = None
    search_query: str | None = None
    event_limit: int = Field(default=250, ge=1, le=1000)
    include_gemma: bool = False
    include_realtime: bool = True
    include_web_search: bool = True
    include_reranker: bool = True
    include_imagegen_boundary: bool = True


class ProviderSmokeStepResult(BaseModel):
    step_id: str
    provider_id: str
    provider_type: str
    title: str
    status: ProviderSmokeStepStatus
    required: bool = True
    live_call: bool = False
    latency_class: str | None = None
    end_to_end_latency_ms: float | None = Field(default=None, ge=0)
    provider_latency_ms: float | None = Field(default=None, ge=0)
    smoke_proof_status: str | None = None
    evidence: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    source_ids: list[UUID] = Field(default_factory=list)
    realtime_session_ids: list[UUID] = Field(default_factory=list)
    event_ids: list[int] = Field(default_factory=list)
    error: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ProviderSmokeRunResult(BaseModel):
    run_id: UUID
    status: ProviderSmokeRunStatus
    execute_live_calls: bool
    provider_readiness: ProviderReadinessResult
    step_count: int
    passed_count: int
    blocked_count: int
    failed_count: int
    not_run_count: int
    tool_boundary_count: int
    source_ids: list[UUID] = Field(default_factory=list)
    realtime_session_ids: list[UUID] = Field(default_factory=list)
    provider_configuration_followup_message_ids: list[UUID] = Field(
        default_factory=list
    )
    steps: list[ProviderSmokeStepResult] = Field(default_factory=list)
    ledger_artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str


class ModelRoutingLedgerRequest(BaseModel):
    record_artifact: bool = True
    event_limit: int = Field(default=250, ge=1, le=1000)
    include_agent_matrix: bool = True
    include_artifact_provenance: bool = True


class ModelRoutingBoundaryCheck(BaseModel):
    check_id: str
    status: str
    owner_agent_id: str
    requirement: str
    evidence: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)


class ModelRoutingLedgerEntry(BaseModel):
    entry_type: str
    route_task: str | None = None
    agent_id: str | None = None
    provider: str | None = None
    model_id: str | None = None
    tool_name: str | None = None
    status: str
    source_event_id: int | None = None
    source_artifact_id: UUID | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ModelRoutingLedgerResult(BaseModel):
    run_id: UUID
    route_count: int
    agent_count: int
    gemma_capable_agent_count: int
    realtime_agent_count: int
    imagegen_tool_agent_count: int
    policy_event_count: int
    gemma_generation_event_count: int
    artifact_model_provenance_count: int
    boundary_violation_count: int
    entries: list[ModelRoutingLedgerEntry] = Field(default_factory=list)
    boundary_checks: list[ModelRoutingBoundaryCheck] = Field(default_factory=list)
    ledger_artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str


class FoundationAuditRequest(BaseModel):
    record_artifact: bool = True
    event_limit: int = Field(default=250, ge=1, le=1000)
    include_static_surface_checks: bool = True


class FoundationAuditCheck(BaseModel):
    check_id: str
    title: str
    status: FoundationAuditStatus
    owner_agent_id: str
    requirement: str
    evidence: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    severity: str = "foundation"


class FoundationAuditResult(BaseModel):
    run_id: UUID
    status: FoundationAuditStatus
    check_count: int
    pass_count: int
    needs_attention_count: int
    fail_count: int
    completion_score: float = Field(ge=0.0, le=1.0)
    checks: list[FoundationAuditCheck] = Field(default_factory=list)
    remediation_items: list[dict[str, Any]] = Field(default_factory=list)
    remediation_count: int = 0
    blocking_remediation_count: int = 0
    audit_artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str


class RuntimeHealthLedgerRequest(BaseModel):
    record_artifact: bool = True
    event_limit: int = Field(default=250, ge=1, le=1000)
    include_static_checks: bool = True
    include_run_evidence: bool = True
    record_live_store_evidence: bool = True
    include_voice_edge_benchmark: bool = True


class RuntimeHealthCheck(BaseModel):
    check_id: str
    title: str
    status: RuntimeHealthStatus
    component: str
    requirement: str
    evidence: list[str] = Field(default_factory=list)
    recommended_action: str
    severity: str = "runtime"


class RuntimeHealthLedgerResult(BaseModel):
    run_id: UUID
    status: RuntimeHealthStatus
    check_count: int
    ready_count: int
    degraded_count: int
    blocked_count: int
    unknown_count: int
    checks: list[RuntimeHealthCheck] = Field(default_factory=list)
    ledger_artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str


class CockpitWalkthroughLedgerRequest(BaseModel):
    record_artifact: bool = True
    event_limit: int = Field(default=250, ge=1, le=1000)
    include_runtime_health: bool = True
    include_static_runtime_checks: bool = True
    record_live_store_evidence: bool = True


class CockpitWalkthroughStep(BaseModel):
    step_id: str
    title: str
    status: str
    required: bool = True
    evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    linked_artifact_ids: list[UUID] = Field(default_factory=list)
    linked_event_types: list[str] = Field(default_factory=list)


class CockpitWalkthroughLedgerResult(BaseModel):
    run_id: UUID
    status: str
    required_step_count: int
    ready_required_count: int
    needs_review_required_count: int
    blocked_required_count: int
    optional_ready_count: int = 0
    steps: list[CockpitWalkthroughStep] = Field(default_factory=list)
    runtime_health: RuntimeHealthLedgerResult | None = None
    provider_readiness: ProviderReadinessResult
    ledger_artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str


class ResearchFreshnessLedgerRequest(BaseModel):
    record_artifact: bool = True
    topic: str | None = None
    freshness_required: bool = True


class ResearchFreshnessQueryEntry(BaseModel):
    query: str
    freshness: str = "current"
    source_count: int = 0
    accepted_source_count: int = 0
    seed_source_count: int = 0
    needs_review_source_count: int = 0
    status: ResearchFreshnessStatus
    notes: str


class ResearchFreshnessSourceEntry(BaseModel):
    source_id: UUID
    citation_id: str
    title: str
    url: HttpUrl
    publisher: str | None = None
    source_type: str
    search_query: str | None = None
    requires_web_search: bool = False
    accepted_for_drafting: bool
    quality_status: SourceQualityStatus
    freshness_status: SourceFreshnessStatus
    flags: list[str] = Field(default_factory=list)
    notes: str


class ResearchFreshnessLedgerResult(BaseModel):
    run_id: UUID
    topic: str
    status: ResearchFreshnessStatus
    source_count: int
    accepted_source_count: int
    seed_source_count: int
    weak_source_count: int
    stale_source_count: int
    unknown_freshness_source_count: int
    needs_review_source_count: int
    query_entries: list[ResearchFreshnessQueryEntry] = Field(default_factory=list)
    source_entries: list[ResearchFreshnessSourceEntry] = Field(default_factory=list)
    ledger_artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str


class RetrievalQualityLedgerRequest(BaseModel):
    record_artifact: bool = True
    topic: str | None = None
    candidate_window: int = Field(default=30, ge=5, le=200)
    min_accepted_sources: int = Field(default=2, ge=1, le=25)
    require_reranking: bool = True
    require_graph_coverage: bool = True


class RetrievalCandidateEntry(BaseModel):
    candidate_id: str
    source_id: UUID | None = None
    citation_id: str | None = None
    title: str
    url: str | None = None
    retrievers: list[str] = Field(default_factory=list)
    query: str | None = None
    source_type: str = "unknown"
    fused_rank: int
    rerank_score: float = Field(ge=0.0, le=1.0)
    reranker: str = "deterministic_source_quality_v1"
    rerank_reason: str | None = None
    accepted_for_context: bool
    quality_status: SourceQualityStatus | None = None
    freshness_status: SourceFreshnessStatus | None = None
    precision_risks: list[str] = Field(default_factory=list)
    recall_risks: list[str] = Field(default_factory=list)
    coverage_topics: list[str] = Field(default_factory=list)


class KnowledgeGraphCoverageEntry(BaseModel):
    node_id: str
    node_type: str
    label: str
    source_ids: list[UUID] = Field(default_factory=list)
    claim_ids: list[UUID] = Field(default_factory=list)
    traversal_role: str
    coverage_status: str
    notes: str


class RetrievalQualityLedgerResult(BaseModel):
    run_id: UUID
    topic: str
    status: RetrievalQualityStatus
    candidate_count: int
    accepted_candidate_count: int
    reranked_candidate_count: int
    graph_node_count: int
    precision_risk_count: int
    recall_gap_count: int
    coverage_gap_count: int
    recommended_queries: list[str] = Field(default_factory=list)
    candidates: list[RetrievalCandidateEntry] = Field(default_factory=list)
    graph_coverage: list[KnowledgeGraphCoverageEntry] = Field(default_factory=list)
    ledger_artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str


class FoundationReference(BaseModel):
    reference_id: str
    title: str
    publisher: str
    url: str
    reference_type: str
    applies_to: list[str] = Field(default_factory=list)
    architecture_decisions: list[str] = Field(default_factory=list)
    agent_implications: list[str] = Field(default_factory=list)
    freshness_policy: str
    last_verified: str


class FoundationReferenceResult(BaseModel):
    references: list[FoundationReference]
    required_publishers: list[str]
    covered_decisions: list[str]
    summary: str


class RevisionRequest(BaseModel):
    feedback_text: str = Field(min_length=1)
    author: str = "user"
    target_artifact_ids: list[UUID] = Field(default_factory=list)
    require_human_feedback: bool = True


class ReviewDecision(BaseModel):
    reviewer_agent_id: str
    status: ReviewDecisionStatus
    notes: str
    blocking_issues: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RevisionResult(BaseModel):
    run_id: UUID
    feedback_id: UUID
    task_message_ids: list[UUID]
    revised_artifact_ids: list[UUID]
    review_decisions: list[ReviewDecision]
    feedback_gate_opened: bool
    summary: str


class MediaProductionRequest(BaseModel):
    target_artifact_ids: list[UUID] = Field(default_factory=list)
    include_image_prompt: bool = True
    include_audio_brief: bool = True
    include_video_storyboard: bool = True
    image_style: str = "clean educational social visual"
    voice_style: str = "natural, warm, interruptible, ELI5"
    platform: str = "instagram_reel"


class MediaProductionResult(BaseModel):
    run_id: UUID
    source_artifact_ids: list[UUID]
    media_artifact_ids: list[UUID]
    image_artifact_id: UUID | None = None
    audio_artifact_id: UUID | None = None
    video_artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str


class MultimodalIntakeRequest(BaseModel):
    assets: list[MultimodalAssetInput] = Field(min_length=1)
    record_artifact: bool = True
    create_agent_tasks: bool = True
    require_human_feedback: bool = False
    notes: str | None = None


class MultimodalAssetEntry(BaseModel):
    asset_id: UUID = Field(default_factory=uuid4)
    asset_uri: str
    modality: str
    source: str
    description: str | None = None
    recommended_agent_ids: list[str] = Field(default_factory=list)
    analysis_boundary: str
    generation_boundary: str
    requires_transcription: bool = False
    requires_visual_analysis: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class MultimodalIntakeResult(BaseModel):
    run_id: UUID
    asset_count: int
    modality_counts: dict[str, int] = Field(default_factory=dict)
    recommended_agent_ids: list[str] = Field(default_factory=list)
    task_message_ids: list[UUID] = Field(default_factory=list)
    intake_artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str
    assets: list[MultimodalAssetEntry] = Field(default_factory=list)


class DistributionPackageRequest(BaseModel):
    target_artifact_ids: list[UUID] = Field(default_factory=list)
    platforms: list[str] = Field(
        default_factory=lambda: [
            "instagram_post",
            "instagram_reel",
            "linkedin",
            "x_thread",
            "substack",
        ]
    )
    audience: str = "AI-curious builders, creators, and operators"
    campaign_goal: str = "educate with source-backed, ELI5 content"
    include_outreach: bool = True
    created_by_agent_id: str = "platform-optimization-agent"
    initiated_by_agent_id: str | None = None


class DistributionPlatformVariant(BaseModel):
    platform: str
    hook: str
    primary_copy: str
    cta: str
    hashtags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    format_notes: list[str] = Field(default_factory=list)
    source_citation_ids: list[str] = Field(default_factory=list)
    claim_ids: list[UUID] = Field(default_factory=list)


class DistributionPackageResult(BaseModel):
    run_id: UUID
    source_artifact_ids: list[UUID]
    distribution_artifact_id: UUID
    platforms: list[str]
    event_id: int | None = None
    summary: str


class GrowthPackageResult(BaseModel):
    run_id: UUID
    source_artifact_ids: list[UUID]
    distribution_artifact_id: UUID
    platforms: list[str]
    influencer_strategy_artifact_id: UUID
    outreach_strategy_artifact_id: UUID
    strategy_artifact_ids: list[UUID]
    agent_message_ids: list[UUID]
    event_id: int | None = None
    summary: str


class AutonomousStudioPassRequest(BaseModel):
    agent_ids: list[str] = Field(default_factory=list)
    max_tasks_per_agent: int = Field(default=1, ge=1, le=25)
    max_worker_rounds: int = Field(default=1, ge=1, le=25)
    run_runtime_health_check: bool = True
    block_on_runtime_health_blocked: bool = True
    build_research_freshness_ledger: bool = True
    auto_refresh_research_sources: bool = True
    block_on_research_freshness_blocked: bool = True
    build_retrieval_quality_ledger: bool = True
    block_on_retrieval_quality_blocked: bool = True
    retrieval_quality_candidate_window: int = Field(default=30, ge=5, le=200)
    retrieval_quality_min_accepted_sources: int = Field(default=2, ge=1, le=25)
    build_a2a_collaboration_graph: bool = True
    block_on_a2a_graph_blocked: bool = True
    block_on_open_feedback: bool = True
    run_worker_cycle: bool = True
    continue_multimodal_followups: bool = True
    multimodal_followup_rounds: int = Field(default=1, ge=1, le=10)
    build_missing_media_plans: bool = True
    build_distribution_package: bool = True
    refresh_source_ledger: bool = True
    run_guardrail_audit: bool = True
    check_publish_readiness: bool = True
    check_publish_channel_readiness: bool = True
    acknowledge_publish_channel_policy: bool = False
    build_artifact_index: bool = True
    build_work_plan: bool = True
    record_sync_pulse: bool = True
    build_context_packet: bool = True
    context_packet_agent_id: str | None = "agent-harness-engineer"
    context_packet_event_limit: int = Field(default=75, ge=0, le=500)
    context_packet_max_manifest_items: int = Field(default=60, ge=5, le=200)
    context_packet_max_context_tokens: int = Field(default=16000, ge=1000, le=200000)
    export_memory_summary_to_obsidian: bool = False
    memory_summary_agent_id: str | None = None
    memory_summary_limit: int = Field(default=8, ge=1, le=50)
    build_skill_usage_ledger: bool = True
    build_model_routing_ledger: bool = True
    build_provider_smoke_ledger: bool = True
    provider_smoke_execute_live_calls: bool = False
    provider_smoke_realtime_provider: str | None = None
    provider_smoke_voice: str | None = None
    provider_smoke_search_query: str | None = None
    build_provider_ops_ledger: bool = True
    build_realtime_dialogue_ledger: bool = True
    build_feedback_resolution_ledger: bool = True
    build_foundation_audit: bool = True
    foundation_audit_event_limit: int = Field(default=500, ge=1, le=1000)
    build_run_replay_ledger: bool = True
    generate_interactive_note: bool = False
    create_checkpoint: bool = True
    open_feedback_gate: bool = True
    use_gemma: bool = False
    fail_on_provider_error: bool = False
    include_note_event_payloads: bool = False
    include_replay_event_payloads: bool = False
    notes: str | None = None


class AutonomousStudioPassResult(BaseModel):
    run_id: UUID
    checkpoint: "RunCheckpoint | None" = None
    runtime_health: RuntimeHealthLedgerResult | None = None
    research_freshness: ResearchFreshnessLedgerResult | None = None
    retrieval_quality: RetrievalQualityLedgerResult | None = None
    a2a_collaboration_graph: "A2ACollaborationGraphResult | None" = None
    open_feedback_count: int = 0
    open_feedback_item_ids: list[UUID] = Field(default_factory=list)
    research_refresh_cycle: "AgentWorkerRunResult | None" = None
    worker_cycle: "AgentWorkerCycleResult | None" = None
    multimodal_followup_cycle: "AgentWorkerCycleResult | None" = None
    media_production: MediaProductionResult | None = None
    distribution_package: DistributionPackageResult | None = None
    source_ledger: "SourceLedgerSnapshotResult | None" = None
    guardrail_audit: "GuardrailAuditResult | None" = None
    publish_readiness: "PublishReadinessResult | None" = None
    artifact_index: "AgentWorkerRunResult | None" = None
    work_plan: "RunWorkPlanResult | None" = None
    sync_pulse: "RunSyncPulseResult | None" = None
    context_packet_artifact: "ArtifactRecord | None" = None
    obsidian_memory_summary: "ArtifactRecord | None" = None
    skill_usage_ledger: "SkillUsageLedgerResult | None" = None
    model_routing_ledger: ModelRoutingLedgerResult | None = None
    provider_smoke_ledger: ProviderSmokeRunResult | None = None
    provider_operations_ledger: ProviderOperationsLedgerResult | None = None
    realtime_dialogue_ledger: RealtimeDialogueLedgerResult | None = None
    feedback_resolution_ledger: "FeedbackResolutionLedgerResult | None" = None
    foundation_audit: FoundationAuditResult | None = None
    run_replay_ledger: "RunReplayLedgerResult | None" = None
    interactive_note: "InteractiveRunNoteResult | None" = None
    skipped_steps: list[str] = Field(default_factory=list)
    event_id: int | None = None
    summary: str


class ConversationRouteRequest(BaseModel):
    run_id: UUID | None = None
    transcript: str = Field(min_length=1)
    modality: str = "text"
    speaker: str = "user"
    audio_uri: str | None = None
    assets: list[MultimodalAssetInput] = Field(default_factory=list)
    record_multimodal_intake: bool = True
    topic: str | None = None
    target_artifact_ids: list[UUID] = Field(default_factory=list)
    target_formats: list[str] = Field(
        default_factory=lambda: list(DEFAULT_TARGET_FORMATS)
    )
    intent: ConversationRouteIntent = ConversationRouteIntent.AUTO
    require_human_feedback: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationRouteResult(BaseModel):
    run_id: UUID
    turn_id: UUID
    response_turn_id: UUID | None = None
    routed_intent: ConversationRouteIntent
    response_text: str
    created_run: bool
    task_message_ids: list[UUID] = Field(default_factory=list)
    artifact_ids: list[UUID] = Field(default_factory=list)
    target_artifact_ids: list[UUID] = Field(default_factory=list)
    multimodal_intake: MultimodalIntakeResult | None = None
    feedback_id: UUID | None = None
    feedback_gate_opened: bool
    orchestration_result: OrchestrationResult | None = None
    revision_result: RevisionResult | None = None
    summary: str


class GuardrailAuditRequest(BaseModel):
    target_artifact_ids: list[UUID] = Field(default_factory=list)
    open_feedback_gate: bool = True


class GuardrailAuditRecord(BaseModel):
    audit_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    artifact_id: UUID
    status: GuardrailAuditStatus
    source_coverage: float = Field(ge=0.0, le=1.0)
    claim_count: int = 0
    supported_claim_ids: list[UUID] = Field(default_factory=list)
    needs_review_claim_ids: list[UUID] = Field(default_factory=list)
    unsupported_claim_ids: list[UUID] = Field(default_factory=list)
    missing_source_claim_ids: list[UUID] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    reviewer_agent_id: str = "guardrails-agent"
    notes: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GuardrailAuditResult(BaseModel):
    run_id: UUID
    audits: list[GuardrailAuditRecord]
    status: GuardrailAuditStatus
    feedback_gate_opened: bool
    summary: str


class PublishReadinessRequest(BaseModel):
    target_artifact_ids: list[UUID] = Field(default_factory=list)
    open_feedback_gate: bool = True
    mark_run_completed_if_ready: bool = False
    check_publish_channel_readiness: bool = False
    acknowledge_publish_channel_policy: bool = False


class PublishChannelCheck(BaseModel):
    platform: str
    credential_envs: list[str] = Field(default_factory=list)
    credential_status: str
    policy_status: str
    blocking_issues: list[str] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)


class PublishReadinessResult(BaseModel):
    run_id: UUID
    status: PublishReadinessStatus
    ready: bool
    artifact_ids: list[UUID]
    source_count: int
    claim_count: int
    audit_count: int
    open_feedback_count: int
    blocking_issues: list[str] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)
    publish_channel_checks: list[PublishChannelCheck] = Field(default_factory=list)
    feedback_gate_opened: bool = False
    feedback_id: UUID | None = None
    summary: str


class RunCheckpoint(BaseModel):
    checkpoint_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    checkpoint_kind: str = "manual"
    status: RunStatus
    conversation_state: dict[str, Any] = Field(default_factory=dict)
    active_agents: list[str] = Field(default_factory=list)
    source_record_ids: list[UUID] = Field(default_factory=list)
    artifact_ids: list[UUID] = Field(default_factory=list)
    feedback_item_ids: list[UUID] = Field(default_factory=list)
    event_cursor: int | None = None
    state_digest: dict[str, Any] = Field(default_factory=dict)
    created_by: str = "agent-harness-engineer"
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RunCheckpointCreate(BaseModel):
    checkpoint_kind: str = "manual"
    created_by: str = "agent-harness-engineer"
    notes: str | None = None


class RunCheckpointResult(BaseModel):
    checkpoint: RunCheckpoint
    event_id: int | None = None
    summary: str


class RunResumePlanRequest(BaseModel):
    agent_id: str | None = None
    include_global_memories: bool = True
    memory_limit: int = Field(default=6, ge=1, le=25)
    include_project_memory_retrieval: bool = True
    project_memory_query: str | None = None
    project_memory_query_embedding: list[float] | None = None
    project_memory_seed_limit: int = Field(default=5, ge=1, le=25)
    project_memory_retrieval_limit: int = Field(default=12, ge=1, le=50)
    project_memory_graph_depth: int = Field(default=1, ge=0, le=2)
    create_checkpoint: bool = True
    checkpoint_kind: str = "resume_plan"
    notes: str | None = None


class RunResumeRequest(BaseModel):
    agent_id: str | None = None
    agent_ids: list[str] = Field(default_factory=list)
    include_global_memories: bool = True
    memory_limit: int = Field(default=6, ge=1, le=25)
    create_checkpoint: bool = True
    checkpoint_kind: str = "resume_execution"
    notes: str | None = None
    build_work_plan: bool = True
    create_followup_tasks: bool = True
    heartbeat_active_profiles: bool = True
    run_worker_cycle: bool = True
    max_tasks_per_agent: int = Field(default=1, ge=1, le=25)
    max_worker_rounds: int = Field(default=1, ge=1, le=25)
    use_gemma: bool = False
    fail_on_provider_error: bool = False


class RunResumeResult(BaseModel):
    run_id: UUID
    resumed: bool
    resume_plan: "RunResumePlan"
    status_before: RunStatus
    status_after: RunStatus
    work_plan: "RunWorkPlanResult | None" = None
    worker_cycle: "AgentWorkerCycleResult | None" = None
    profile_heartbeats: list["WorkerProfileHeartbeatResult"] = Field(
        default_factory=list
    )
    event_id: int | None = None
    summary: str


class RunReplayLedgerRequest(BaseModel):
    record_artifact: bool = True
    checkpoint_id: UUID | None = None
    after_event_id: int | None = None
    event_limit: int = Field(default=500, ge=1, le=5000)
    include_event_payloads: bool = False


class RunReplayEventEntry(BaseModel):
    event_id: int
    event_type: str
    actor: str
    created_at: datetime
    payload_preview: dict[str, Any] = Field(default_factory=dict)


class RunReplayStateDelta(BaseModel):
    key: str
    checkpoint_value: int | None = None
    current_value: int | None = None
    delta: int | None = None


class RunReplayLedgerResult(BaseModel):
    run_id: UUID
    checkpoint_id: UUID | None = None
    replay_after_event_id: int | None = None
    latest_event_id: int | None = None
    replay_event_count: int
    event_type_counts: dict[str, int] = Field(default_factory=dict)
    actor_counts: dict[str, int] = Field(default_factory=dict)
    state_deltas: list[RunReplayStateDelta] = Field(default_factory=list)
    events: list[RunReplayEventEntry] = Field(default_factory=list)
    replay_artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str


class RunState(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    goal: str
    status: RunStatus = RunStatus.CREATED
    conversation_state: dict[str, Any] = Field(default_factory=dict)
    active_agents: list[str] = Field(default_factory=list)
    source_record_ids: list[UUID] = Field(default_factory=list)
    artifact_ids: list[UUID] = Field(default_factory=list)
    feedback_item_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RunEvent(BaseModel):
    event_id: int | None = None
    run_id: UUID
    event_type: str
    actor: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentMessage(BaseModel):
    message_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    sender_agent_id: str
    recipient_agent_id: str
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    depends_on_message_ids: list[UUID] = Field(default_factory=list)
    requires_human_feedback: bool = False
    status: AgentTaskStatus = AgentTaskStatus.ACCEPTED
    claimed_by_agent_id: str | None = None
    attempt_count: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1, le=25)
    result: dict[str, Any] = Field(default_factory=dict)
    handoff_trace: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentMessageResponse(BaseModel):
    message_id: UUID
    run_id: UUID
    accepted: bool
    recipient_agent_id: str
    event_id: int | None = None
    status: str


class AgentMessageStatusUpdate(BaseModel):
    agent_id: str
    status: AgentTaskStatus
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    notes: str | None = None


class AgentMessageStatusResponse(BaseModel):
    message: AgentMessage
    event_id: int | None = None


class AgentMessagePublicProjection(BaseModel):
    message_id: UUID
    run_id: UUID
    sender_agent_id: str
    recipient_agent_id: str
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    depends_on_message_ids: list[UUID] = Field(default_factory=list)
    requires_human_feedback: bool = False
    status: AgentTaskStatus
    claimed_by_agent_id: str | None = None
    attempt_count: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1, le=25)
    result: dict[str, Any] = Field(default_factory=dict)
    handoff_trace: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    redaction: dict[str, Any] = Field(default_factory=dict)


class AgentMessageDetailResponse(BaseModel):
    message: AgentMessage | AgentMessagePublicProjection
    projection: str = "private"


class AgentMessageRetryRequest(BaseModel):
    agent_id: str
    reason: str = Field(min_length=1)
    reset_attempt_count: bool = True
    max_attempts: int | None = Field(default=None, ge=1, le=25)


class AgentMessageRetryResponse(BaseModel):
    message: AgentMessage
    event_id: int | None = None
    summary: str


class AgentMessageDependencyRepairRequest(BaseModel):
    agent_id: str
    remove_dependency_message_ids: list[UUID] = Field(min_length=1)
    reason: str = Field(min_length=1)


class AgentMessageDependencyRepairResponse(BaseModel):
    message: AgentMessage
    removed_dependency_message_ids: list[UUID]
    remaining_dependency_message_ids: list[UUID]
    event_id: int | None = None
    summary: str


class AgentWorkerRunRequest(BaseModel):
    run_id: UUID
    max_tasks: int = Field(default=1, ge=1, le=25)
    message_ids: list[UUID] = Field(default_factory=list)
    include_global_memories: bool = True
    memory_limit: int = Field(default=6, ge=1, le=25)
    use_gemma: bool = False
    fail_on_provider_error: bool = False
    recover_stale_tasks: bool = True
    stale_task_after_seconds: float = Field(default=3600.0, ge=1.0, le=86400.0)


class AgentWorkerTaskResult(BaseModel):
    message_id: UUID
    task_type: str
    status: AgentTaskStatus
    generation_mode: str
    summary: str


class AgentWorkerRunResult(BaseModel):
    run_id: UUID
    agent_id: str
    processed_tasks: list[AgentWorkerTaskResult] = Field(default_factory=list)
    recovered_stale_tasks: int = 0
    blocked_exhausted_tasks: int = 0
    dependency_blocked_tasks: int = 0
    idle: bool
    summary: str


class AgentWorkerCycleRequest(BaseModel):
    run_id: UUID
    agent_ids: list[str] = Field(default_factory=list)
    message_ids: list[UUID] = Field(default_factory=list, max_length=100)
    continue_message_lineage: bool = False
    max_tasks_per_agent: int = Field(default=1, ge=1, le=25)
    max_rounds: int = Field(default=1, ge=1, le=50)
    include_global_memories: bool = True
    memory_limit: int = Field(default=6, ge=1, le=25)
    use_gemma: bool = False
    fail_on_provider_error: bool = False
    recover_stale_tasks: bool = True
    stale_task_after_seconds: float = Field(default=3600.0, ge=1.0, le=86400.0)


class AgentWorkerCycleResult(BaseModel):
    run_id: UUID
    agent_ids: list[str]
    rounds_completed: int
    worker_results: list[AgentWorkerRunResult] = Field(default_factory=list)
    total_processed_tasks: int
    idle: bool
    summary: str


class WorkerProfile(BaseModel):
    profile_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    name: str = Field(min_length=1)
    execution_mode: WorkerProfileExecutionMode = WorkerProfileExecutionMode.WORKER_CYCLE
    agent_ids: list[str] = Field(default_factory=list)
    max_tasks_per_agent: int = Field(default=1, ge=1, le=25)
    max_rounds: int = Field(default=1, ge=1, le=50)
    poll_interval_seconds: float = Field(default=5.0, ge=0.25, le=3600.0)
    include_global_memories: bool = True
    memory_limit: int = Field(default=6, ge=1, le=25)
    autonomous_auto_refresh_research_sources: bool = True
    autonomous_block_on_research_freshness_blocked: bool = True
    autonomous_block_on_retrieval_quality_blocked: bool = True
    autonomous_export_memory_summary_to_obsidian: bool = False
    autonomous_memory_summary_agent_id: str | None = None
    autonomous_memory_summary_limit: int = Field(default=8, ge=1, le=50)
    use_gemma: bool = False
    fail_on_provider_error: bool = False
    status: WorkerProfileStatus = WorkerProfileStatus.PAUSED
    last_heartbeat_at: datetime | None = None
    heartbeat_claimed_at: datetime | None = None
    heartbeat_claimed_by: str | None = None
    heartbeat_lease_until: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkerProfileCreate(BaseModel):
    name: str = Field(min_length=1)
    execution_mode: WorkerProfileExecutionMode = WorkerProfileExecutionMode.WORKER_CYCLE
    agent_ids: list[str] = Field(default_factory=list)
    max_tasks_per_agent: int = Field(default=1, ge=1, le=25)
    max_rounds: int = Field(default=1, ge=1, le=50)
    poll_interval_seconds: float = Field(default=5.0, ge=0.25, le=3600.0)
    include_global_memories: bool = True
    memory_limit: int = Field(default=6, ge=1, le=25)
    autonomous_auto_refresh_research_sources: bool = True
    autonomous_block_on_research_freshness_blocked: bool = True
    autonomous_block_on_retrieval_quality_blocked: bool = True
    autonomous_export_memory_summary_to_obsidian: bool = False
    autonomous_memory_summary_agent_id: str | None = None
    autonomous_memory_summary_limit: int = Field(default=8, ge=1, le=50)
    use_gemma: bool = False
    fail_on_provider_error: bool = False
    status: WorkerProfileStatus = WorkerProfileStatus.PAUSED


class WorkerProfileStatusUpdate(BaseModel):
    status: WorkerProfileStatus


class WorkerProfileHeartbeatResult(BaseModel):
    profile: WorkerProfile
    resume_plan: "RunResumePlan | None" = None
    cycle_result: AgentWorkerCycleResult | None = None
    autonomous_pass_result: AutonomousStudioPassResult | None = None
    heartbeat_ledger_artifact: "ArtifactRecord | None" = None
    context_packet_artifact: "ArtifactRecord | None" = None
    realtime_dialogue_ledger: "RealtimeDialogueLedgerResult | None" = None
    feedback_resolution_ledger: "FeedbackResolutionLedgerResult | None" = None
    work_plan: "RunWorkPlanResult | None" = None
    skipped: bool
    skipped_reason: str | None = None
    summary: str


class AutopilotLaunchRequest(BaseModel):
    profile_name: str = "Autonomous studio profile"
    agent_ids: list[str] = Field(default_factory=list)
    max_tasks_per_agent: int = Field(default=1, ge=1, le=25)
    max_rounds: int = Field(default=2, ge=1, le=50)
    poll_interval_seconds: float = Field(default=5.0, ge=0.25, le=3600.0)
    include_global_memories: bool = True
    memory_limit: int = Field(default=6, ge=1, le=25)
    autonomous_auto_refresh_research_sources: bool = True
    autonomous_block_on_research_freshness_blocked: bool = True
    autonomous_block_on_retrieval_quality_blocked: bool = True
    autonomous_export_memory_summary_to_obsidian: bool = False
    autonomous_memory_summary_agent_id: str | None = None
    autonomous_memory_summary_limit: int = Field(default=8, ge=1, le=50)
    use_gemma: bool = False
    fail_on_provider_error: bool = False
    reuse_existing_profile: bool = True
    run_first_heartbeat: bool = True
    record_artifact: bool = True


class AutopilotLaunchResult(BaseModel):
    run_id: UUID
    profile: WorkerProfile
    created_profile: bool
    reused_profile: bool
    started_profile: bool
    heartbeat_result: WorkerProfileHeartbeatResult | None = None
    launch_ledger_artifact: "ArtifactRecord | None" = None
    event_id: int | None = None
    summary: str


class WorkerSchedulerRunRequest(BaseModel):
    max_profiles: int = Field(default=25, ge=1, le=250)
    run_id: UUID | None = None
    execution_mode: WorkerProfileExecutionMode | None = None


class WorkerSchedulerRunResult(BaseModel):
    checked_profiles: int
    heartbeat_results: list[WorkerProfileHeartbeatResult] = Field(default_factory=list)
    total_processed_tasks: int
    idle: bool
    summary: str


class SourceRecord(BaseModel):
    source_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    citation_id: str
    title: str
    url: HttpUrl
    publisher: str | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    published_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceRecordCreate(BaseModel):
    citation_id: str
    title: str
    url: HttpUrl
    publisher: str | None = None
    published_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceLedgerSnapshotRequest(BaseModel):
    record_artifact: bool = True
    include_artifact_content: bool = False


class SourceLedgerClaimEntry(BaseModel):
    claim_id: UUID
    claim_text: str
    support_status: ClaimSupportStatus
    source_ids: list[UUID] = Field(default_factory=list)
    source_citation_ids: list[str] = Field(default_factory=list)
    missing_source_ids: list[UUID] = Field(default_factory=list)
    reviewer_agent_id: str | None = None
    notes: str | None = None


class SourceLedgerSourceEntry(BaseModel):
    source_id: UUID
    citation_id: str
    title: str
    url: HttpUrl
    publisher: str | None = None
    source_type: str
    quality_status: SourceQualityStatus
    freshness_status: SourceFreshnessStatus
    quality_score: float = Field(ge=0.0, le=1.0)
    freshness_score: float = Field(ge=0.0, le=1.0)
    published_at: datetime | None = None
    retrieved_at: datetime
    flags: list[str] = Field(default_factory=list)
    notes: str
    accepted_for_context: bool = False
    retrieval_candidate_id: str | None = None
    retrieval_rank: int | None = None
    retrieval_rerank_score: float | None = Field(default=None, ge=0.0, le=1.0)
    retrieval_reranker: str | None = None
    retrieval_rerank_reason: str | None = None
    retrieval_precision_risks: list[str] = Field(default_factory=list)
    retrieval_recall_risks: list[str] = Field(default_factory=list)
    retrieval_coverage_topics: list[str] = Field(default_factory=list)
    retrieval_ledger_artifact_id: UUID | None = None
    retrieval_ledger_status: str | None = None


class SourceLedgerClaimSourceMatrixEntry(BaseModel):
    claim_id: UUID
    claim_text: str
    support_status: ClaimSupportStatus
    source_ids: list[UUID] = Field(default_factory=list)
    source_citation_ids: list[str] = Field(default_factory=list)
    missing_source_ids: list[UUID] = Field(default_factory=list)
    source_quality_statuses: dict[str, SourceQualityStatus] = Field(
        default_factory=dict
    )
    source_freshness_statuses: dict[str, SourceFreshnessStatus] = Field(
        default_factory=dict
    )
    verdict: str


class SourceLedgerArtifactEntry(BaseModel):
    artifact_id: UUID
    artifact_type: ArtifactType
    title: str
    uri: str
    source_ids: list[UUID] = Field(default_factory=list)
    source_citation_ids: list[str] = Field(default_factory=list)
    claim_ids: list[UUID] = Field(default_factory=list)
    missing_source_ids: list[UUID] = Field(default_factory=list)
    missing_claim_ids: list[UUID] = Field(default_factory=list)
    claim_source_matrix: list[SourceLedgerClaimSourceMatrixEntry] = Field(
        default_factory=list
    )
    coverage_status: str
    content_preview: dict[str, Any] = Field(default_factory=dict)


class SourceLedgerSnapshotResult(BaseModel):
    run_id: UUID
    source_count: int
    claim_count: int
    artifact_count: int
    supported_claim_count: int
    needs_review_claim_count: int
    unsupported_claim_count: int
    missing_source_claim_ids: list[UUID] = Field(default_factory=list)
    unsupported_claim_ids: list[UUID] = Field(default_factory=list)
    weak_source_ids: list[UUID] = Field(default_factory=list)
    stale_source_ids: list[UUID] = Field(default_factory=list)
    unknown_freshness_source_ids: list[UUID] = Field(default_factory=list)
    accepted_retrieval_source_count: int = 0
    retrieval_evidence_status: str = "missing_retrieval_quality_ledger"
    retrieval_ledger_artifact_id: UUID | None = None
    artifacts_missing_claims: list[UUID] = Field(default_factory=list)
    artifacts_missing_sources: list[UUID] = Field(default_factory=list)
    claim_source_matrix_count: int = 0
    claim_source_verdict_counts: dict[str, int] = Field(default_factory=dict)
    source_entries: list[SourceLedgerSourceEntry] = Field(default_factory=list)
    claim_entries: list[SourceLedgerClaimEntry] = Field(default_factory=list)
    artifact_entries: list[SourceLedgerArtifactEntry] = Field(default_factory=list)
    ledger_artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str


class ClaimRecord(BaseModel):
    claim_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    claim_text: str
    support_status: ClaimSupportStatus = ClaimSupportStatus.NEEDS_REVIEW
    source_ids: list[UUID] = Field(default_factory=list)
    reviewer_agent_id: str | None = None
    notes: str | None = None


class ClaimRecordCreate(BaseModel):
    claim_text: str = Field(min_length=1)
    support_status: ClaimSupportStatus = ClaimSupportStatus.NEEDS_REVIEW
    source_ids: list[UUID] = Field(default_factory=list)
    reviewer_agent_id: str | None = None
    notes: str | None = None


class FeedbackItem(BaseModel):
    feedback_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    author: str = "user"
    target_agent_id: str | None = None
    feedback_text: str = Field(min_length=1)
    status: FeedbackStatus = FeedbackStatus.OPEN
    metadata: dict[str, Any] = Field(default_factory=dict)
    resolution_notes: str | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FeedbackResolutionRequest(BaseModel):
    status: FeedbackStatus = FeedbackStatus.RESOLVED
    resolver: str = "user"
    resolution_notes: str | None = None
    run_status: RunStatus | None = None
    build_resolution_ledger: bool = True


class FeedbackResolutionResult(BaseModel):
    feedback: FeedbackItem
    run_status: RunStatus
    open_feedback_count: int
    resolution_ledger: "FeedbackResolutionLedgerResult | None" = None
    event_id: int | None = None
    summary: str


class FeedbackResolutionLedgerRequest(BaseModel):
    record_artifact: bool = True
    max_feedback_items: int = Field(default=100, ge=1, le=500)
    max_messages: int = Field(default=500, ge=1, le=2000)


class FeedbackResolutionFeedbackEntry(BaseModel):
    feedback_id: UUID
    status: FeedbackStatus
    outcome: str = "held"
    target_agent_id: str | None = None
    author: str
    route_reason: str | None = None
    priority: str | None = None
    target_artifact_ids: list[UUID] = Field(default_factory=list)
    target_artifact_titles: list[str] = Field(default_factory=list)
    target_artifact_types: list[str] = Field(default_factory=list)
    target_source_ids: list[UUID] = Field(default_factory=list)
    target_claim_ids: list[UUID] = Field(default_factory=list)
    target_artifact_selection: str | None = None
    linked_message_ids: list[UUID] = Field(default_factory=list)
    resolution_notes: str | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None


class FeedbackResolutionTaskEntry(BaseModel):
    message_id: UUID
    feedback_id: UUID | None = None
    recipient_agent_id: str
    task_type: str
    status: AgentTaskStatus
    requires_human_feedback: bool = False
    blocking: bool = False


class FeedbackResolutionLedgerResult(BaseModel):
    run_id: UUID
    status: str
    feedback_count: int
    open_feedback_count: int
    routed_feedback_count: int
    accepted_feedback_count: int = 0
    revised_feedback_count: int = 0
    held_feedback_count: int = 0
    resolved_feedback_count: int
    rejected_feedback_count: int
    feedback_outcomes: dict[str, int] = Field(default_factory=dict)
    targeted_feedback_count: int = 0
    targeted_artifact_count: int = 0
    targeted_source_count: int = 0
    targeted_claim_count: int = 0
    linked_task_count: int
    pending_linked_task_count: int
    blocked_linked_task_count: int
    failed_linked_task_count: int = 0
    open_feedback_ids: list[UUID] = Field(default_factory=list)
    routed_feedback_ids: list[UUID] = Field(default_factory=list)
    recently_resolved_feedback_ids: list[UUID] = Field(default_factory=list)
    pending_task_ids: list[UUID] = Field(default_factory=list)
    failed_task_ids: list[UUID] = Field(default_factory=list)
    feedback_entries: list[FeedbackResolutionFeedbackEntry] = Field(default_factory=list)
    task_entries: list[FeedbackResolutionTaskEntry] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)
    ledger_artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str


class FeedbackRoutingResult(BaseModel):
    feedback: FeedbackItem
    routed_agent_id: str
    route_reason: str
    task_message_id: UUID
    support_task_message_ids: list[UUID] = Field(default_factory=list)
    memory_ids: list[UUID] = Field(default_factory=list)
    event_ids: list[int] = Field(default_factory=list)
    summary: str


class PlanningFeedbackSuggestion(BaseModel):
    """One suggestion captured from the separate planning HTML surface."""

    id: str | None = None
    focus: str = "planning-html"
    priority: str = "medium"
    route_to: str = "forward-deployed-engineer"
    suggestion: str = Field(min_length=1)
    summary: str | None = None
    created_at: str | None = None


class PlanningFeedbackIngestRequest(BaseModel):
    """Durably route planning-surface suggestions into the agent loop."""

    run_id: UUID
    author: str = "user"
    artifact: str = "planning/foundation-system-design.html"
    items: list[PlanningFeedbackSuggestion] = Field(min_length=1)


class PlanningFeedbackRoutedItem(BaseModel):
    input_id: str | None = None
    feedback_id: UUID
    routed_agent_id: str
    route_reason: str
    task_message_id: UUID
    support_task_message_ids: list[UUID] = Field(default_factory=list)
    status: FeedbackStatus


class PlanningFeedbackIngestResult(BaseModel):
    run_id: UUID
    artifact: str
    routed_count: int
    routed_items: list[PlanningFeedbackRoutedItem] = Field(default_factory=list)
    event_id: int | None = None
    summary: str


class ArtifactRecord(BaseModel):
    artifact_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    artifact_type: ArtifactType
    title: str
    uri: str
    content: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    source_ids: list[UUID] = Field(default_factory=list)
    reviewer_decisions: list[dict[str, Any]] = Field(default_factory=list)
    revision_history: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ArtifactRecordCreate(BaseModel):
    artifact_type: ArtifactType
    title: str = Field(min_length=1)
    uri: str = Field(min_length=1)
    content: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    source_ids: list[UUID] = Field(default_factory=list)
    reviewer_decisions: list[dict[str, Any]] = Field(default_factory=list)
    revision_history: list[dict[str, Any]] = Field(default_factory=list)


class InteractiveRunNoteRequest(BaseModel):
    title: str | None = None
    include_event_payloads: bool = False


class InteractiveRunNoteResult(BaseModel):
    run_id: UUID
    artifact_id: UUID
    uri: str
    file_path: str
    event_id: int | None = None
    summary: str


class ObsidianReviewNoteRequest(BaseModel):
    title: str | None = None
    note_kind: str = "run_review"
    include_event_tail: bool = True
    event_limit: int = Field(default=25, ge=0, le=200)


class ObsidianReviewNoteResult(BaseModel):
    run_id: UUID
    artifact_id: UUID
    uri: str
    file_path: str
    note_kind: str
    event_id: int | None = None
    summary: str


class ObsidianMemoryPromotionRequest(BaseModel):
    title: str | None = None
    promotion_kind: str = "run_memory_promotion"
    target_wiki_notes: list[str] = Field(
        default_factory=lambda: [
            "wiki/product/agent-studio-memory-layer.md",
            "wiki/ops/codex-obsidian-working-memory.md",
        ]
    )
    include_review_note_links: bool = True
    event_limit: int = Field(default=50, ge=0, le=250)


class ObsidianMemoryPromotionResult(BaseModel):
    run_id: UUID
    artifact_id: UUID
    uri: str
    file_path: str
    promotion_kind: str
    target_wiki_notes: list[str]
    promoted_item_count: int
    event_id: int | None = None
    summary: str


class ProjectMemoryKind(StrEnum):
    USER_PREFERENCE = "user_preference"
    PROJECT_DECISION = "project_decision"


class ProjectMemoryScope(StrEnum):
    GLOBAL = "global"
    RUN = "run"


class ProjectMemoryRecordRequest(BaseModel):
    memory_kind: ProjectMemoryKind
    content: str = Field(min_length=1)
    agent_id: str | None = None
    scope: ProjectMemoryScope = ProjectMemoryScope.GLOBAL
    embedding: list[float] | None = None
    confidence: str = "medium"
    tags: list[str] = Field(default_factory=list)
    source_artifact_ids: list[UUID] = Field(default_factory=list)
    target_wiki_notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectMemoryRecordResult(BaseModel):
    run_id: UUID
    memory: "AgentMemory"
    memory_scope: ProjectMemoryScope
    event_id: int | None = None
    summary: str


class ProjectMemoryRetrievalRequest(BaseModel):
    query: str = Field(min_length=1)
    agent_id: str | None = None
    query_embedding: list[float] | None = None
    include_global_memories: bool = True
    memory_kinds: list[ProjectMemoryKind] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    target_wiki_notes: list[str] = Field(default_factory=list)
    relevant_memory_ids: list[UUID] = Field(default_factory=list)
    relevant_tags: list[str] = Field(default_factory=list)
    relevant_target_wiki_notes: list[str] = Field(default_factory=list)
    seed_limit: int = Field(default=10, ge=1, le=100)
    memory_limit: int = Field(default=20, ge=1, le=100)
    graph_memory_limit: int = Field(default=80, ge=1, le=300)
    graph_depth: int = Field(default=1, ge=0, le=2)
    record_artifact: bool = True


class ProjectMemoryRetrievalMemory(BaseModel):
    memory: "AgentMemory"
    distance: float | None = None
    keyword_score: float = 0
    semantic_score: float = 0
    graph_score: float = 0
    combined_score: float = 0
    is_seed: bool = False
    match_reasons: list[str] = Field(default_factory=list)
    shared_connectors: list[str] = Field(default_factory=list)


class ProjectMemoryGraphNode(BaseModel):
    node_id: str
    node_type: str
    label: str
    memory_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectMemoryGraphEdge(BaseModel):
    from_node_id: str
    to_node_id: str
    relationship: str
    weight: float = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectMemoryRetrievalEvaluation(BaseModel):
    evaluation_mode: str
    evaluated: bool
    expected_memory_count: int = 0
    retrieved_memory_count: int = 0
    relevant_retrieved_count: int = 0
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None
    false_positive_memory_ids: list[UUID] = Field(default_factory=list)
    false_negative_memory_ids: list[UUID] = Field(default_factory=list)
    precision_risk_count: int = 0
    recall_gap_count: int = 0
    repeated_query_count: int = 1
    previous_precision: float | None = None
    previous_recall: float | None = None
    precision_delta: float | None = None
    recall_delta: float | None = None
    trend: str = "no_prior"
    notes: list[str] = Field(default_factory=list)


class ProjectMemoryRetrievalResult(BaseModel):
    run_id: UUID
    query: str
    agent_id: str | None = None
    seed_memory_count: int
    related_memory_count: int
    memory_count: int
    graph_node_count: int
    graph_edge_count: int
    memories: list[ProjectMemoryRetrievalMemory] = Field(default_factory=list)
    graph_nodes: list[ProjectMemoryGraphNode] = Field(default_factory=list)
    graph_edges: list[ProjectMemoryGraphEdge] = Field(default_factory=list)
    evaluation: ProjectMemoryRetrievalEvaluation | None = None
    recommended_actions: list[str] = Field(default_factory=list)
    artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str


class AgentMemory(BaseModel):
    memory_id: UUID = Field(default_factory=uuid4)
    agent_id: str
    run_id: UUID | None = None
    memory_kind: str
    content: str = Field(min_length=1)
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentMemoryCreate(BaseModel):
    agent_id: str
    run_id: UUID | None = None
    memory_kind: str
    content: str = Field(min_length=1)
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemorySearchRequest(BaseModel):
    agent_id: str | None = None
    run_id: UUID | None = None
    include_global_memories: bool = True
    query_embedding: list[float] | None = None
    limit: int = Field(default=10, ge=1, le=100)


class MemorySearchResult(BaseModel):
    memory: AgentMemory
    distance: float | None = None


class RunContextPacketRequest(BaseModel):
    agent_id: str | None = None
    query_embedding: list[float] | None = None
    include_global_memories: bool = True
    memory_limit: int = Field(default=10, ge=1, le=100)
    include_project_memory_retrieval: bool = True
    project_memory_query: str | None = None
    project_memory_seed_limit: int = Field(default=5, ge=1, le=25)
    project_memory_retrieval_limit: int = Field(default=20, ge=1, le=100)
    project_memory_graph_depth: int = Field(default=1, ge=0, le=2)
    event_limit: int = Field(default=25, ge=0, le=100)
    max_manifest_items: int = Field(default=40, ge=5, le=200)
    max_context_tokens: int = Field(default=12000, ge=1000, le=200000)
    record_event: bool = True


class ContextManifestItem(BaseModel):
    item_type: str
    item_id: str | None = None
    title: str
    priority: str = "normal"
    reason: str
    estimated_tokens: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextRiskItem(BaseModel):
    risk_type: str
    severity: str
    owner_agent_id: str | None = None
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunContextPacket(BaseModel):
    run: RunState
    conversation_turns: list[ConversationTurn]
    agent_messages: list[AgentMessage]
    recent_events: list[RunEvent] = Field(default_factory=list)
    sources: list[SourceRecord]
    source_evidence: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[ClaimRecord]
    artifacts: list[ArtifactRecord]
    guardrail_audits: list[GuardrailAuditRecord]
    feedback_items: list[FeedbackItem]
    memories: list[MemorySearchResult]
    context_manifest: list[ContextManifestItem] = Field(default_factory=list)
    context_risks: list[ContextRiskItem] = Field(default_factory=list)
    recommended_fetches: list[str] = Field(default_factory=list)
    summary: dict[str, Any]


class RunResumePlan(BaseModel):
    run: RunState
    checkpoint: RunCheckpoint | None = None
    latest_event_id: int | None = None
    event_stream_after_id: int | None = None
    resume_allowed: bool
    blocked_reasons: list[str] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)
    pending_agent_messages: list[AgentMessage] = Field(default_factory=list)
    open_feedback_items: list[FeedbackItem] = Field(default_factory=list)
    active_worker_profiles: list[WorkerProfile] = Field(default_factory=list)
    context_summary: dict[str, Any] = Field(default_factory=dict)
    event_id: int | None = None
    summary: str


class RunWorkPlanRequest(BaseModel):
    record_artifact: bool = True
    include_completed_tasks: bool = False
    create_followup_tasks: bool = False
    max_items: int = Field(default=25, ge=1, le=100)
    refresh_reason: str | None = None


class RunWorkPlanItem(BaseModel):
    item_id: UUID = Field(default_factory=uuid4)
    item_type: str
    title: str
    owner_agent_id: str
    status: str
    priority: str = "normal"
    blocking: bool = False
    source_message_id: UUID | None = None
    source_feedback_id: UUID | None = None
    recommended_action: str
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunWorkPlanResult(BaseModel):
    run_id: UUID
    plan_items: list[RunWorkPlanItem] = Field(default_factory=list)
    recommended_agent_ids: list[str] = Field(default_factory=list)
    open_feedback_count: int = 0
    routed_feedback_count: int = 0
    pending_task_count: int = 0
    blocked_item_count: int = 0
    created_task_message_ids: list[UUID] = Field(default_factory=list)
    skipped_duplicate_task_count: int = 0
    artifact_id: UUID | None = None
    event_id: int | None = None
    refresh_reason: str | None = None
    summary: str


class AgentSyncState(BaseModel):
    agent_id: str
    name: str | None = None
    role: str | None = None
    task_counts: dict[str, int] = Field(default_factory=dict)
    pending_message_ids: list[UUID] = Field(default_factory=list)
    blocked_message_ids: list[UUID] = Field(default_factory=list)
    routed_feedback_ids: list[UUID] = Field(default_factory=list)
    active_profile_ids: list[UUID] = Field(default_factory=list)
    current_focus: str
    recommended_next_action: str


class RunSyncPulseRequest(BaseModel):
    record_artifact: bool = True
    build_work_plan: bool = True
    create_followup_tasks: bool = False
    include_completed_tasks: bool = False
    max_work_items: int = Field(default=25, ge=1, le=100)
    include_all_active_agents: bool = True
    notes: str | None = None
    refresh_reason: str | None = None


class RunSyncPulseResult(BaseModel):
    run_id: UUID
    agent_states: list[AgentSyncState] = Field(default_factory=list)
    work_plan: RunWorkPlanResult | None = None
    blockers: list[str] = Field(default_factory=list)
    recommended_agent_ids: list[str] = Field(default_factory=list)
    artifact_id: UUID | None = None
    event_id: int | None = None
    refresh_reason: str | None = None
    summary: str


class A2ACollaborationGraphRequest(BaseModel):
    record_artifact: bool = True
    include_completed_tasks: bool = True
    max_messages: int = Field(default=500, ge=1, le=2000)


class A2ACollaborationNode(BaseModel):
    node_id: str
    node_type: str
    label: str
    agent_id: str | None = None
    message_id: UUID | None = None
    status: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class A2ACollaborationEdge(BaseModel):
    source_node_id: str
    target_node_id: str
    edge_type: str
    status: str = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)


class A2ACollaborationGraphResult(BaseModel):
    run_id: UUID
    agent_count: int
    task_count: int
    edge_count: int
    ready_task_ids: list[UUID] = Field(default_factory=list)
    dependency_waiting_task_ids: list[UUID] = Field(default_factory=list)
    blocked_task_ids: list[UUID] = Field(default_factory=list)
    retry_exhausted_task_ids: list[UUID] = Field(default_factory=list)
    trace_gap_task_ids: list[UUID] = Field(default_factory=list)
    dependency_cycle_message_ids: list[UUID] = Field(default_factory=list)
    dependency_cycles: list[list[UUID]] = Field(default_factory=list)
    nodes: list[A2ACollaborationNode] = Field(default_factory=list)
    edges: list[A2ACollaborationEdge] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str


class SkillUsageLedgerRequest(BaseModel):
    record_artifact: bool = True
    include_pending_tasks: bool = True
    include_source_contracts: bool = True
    max_messages: int = Field(default=500, ge=1, le=2000)
    max_events: int = Field(default=2000, ge=1, le=10000)


class SkillUsageEntry(BaseModel):
    message_id: UUID
    agent_id: str
    task_type: str
    status: str
    skill_ids: list[str] = Field(default_factory=list)
    skill_source_paths: dict[str, str] = Field(default_factory=dict)
    declared_outputs: dict[str, list[str]] = Field(default_factory=dict)
    guardrails: dict[str, list[str]] = Field(default_factory=dict)
    invocation_event_ids: list[int] = Field(default_factory=list)
    has_result_skill_usage: bool = False
    has_invocation_event: bool = False
    result_generation_mode: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillSourceContractEntry(BaseModel):
    skill_id: str
    source_path: str
    file_exists: bool
    frontmatter_name: str | None = None
    frontmatter_matches_card: bool = False
    description_present: bool = False
    agents_manifest_exists: bool = False
    applies_to_agent_count: int = 0
    unknown_agent_ids: list[str] = Field(default_factory=list)
    issue_count: int = 0
    issues: list[str] = Field(default_factory=list)


class SkillUsageLedgerResult(BaseModel):
    run_id: UUID
    agent_count: int
    task_count: int
    processed_task_count: int
    skill_count: int
    skill_invocation_count: int
    missing_skill_usage_message_ids: list[UUID] = Field(default_factory=list)
    unprocessed_agent_ids: list[str] = Field(default_factory=list)
    skill_source_contract_issue_count: int = 0
    skill_source_contracts: list[SkillSourceContractEntry] = Field(default_factory=list)
    entries: list[SkillUsageEntry] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    artifact_id: UUID | None = None
    event_id: int | None = None
    summary: str
