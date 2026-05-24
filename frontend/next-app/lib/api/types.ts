export type UUID = string;

export type RunStatus =
  | "created"
  | "running"
  | "waiting_for_human"
  | "completed"
  | "failed"
  | "canceled";

export type ArtifactType =
  | "post"
  | "reel_script"
  | "substack_article"
  | "social_package"
  | "growth_strategy"
  | "data_brief"
  | "claim_revision_plan"
  | "multimodal_review"
  | "image"
  | "audio"
  | "video"
  | "html_note"
  | "obsidian_note"
  | "source_ledger"
  | string;

export type FeedbackStatus = "open" | "routed" | "resolved" | "rejected";

export type ClaimSupportStatus = "supported" | "unsupported" | "needs_review";

export type RunState = {
  run_id: UUID;
  goal: string;
  status: RunStatus;
  conversation_state: Record<string, unknown>;
  active_agents: string[];
  source_record_ids: UUID[];
  artifact_ids: UUID[];
  feedback_item_ids: UUID[];
  created_at: string;
  updated_at: string;
};

export type RunCreateInput = {
  goal: string;
  input_mode?: string;
  initial_context?: Record<string, unknown>;
};

export type ConversationTurn = {
  turn_id: UUID;
  run_id: UUID;
  speaker: string;
  modality: "text" | "voice" | string;
  transcript: string;
  audio_uri?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AgentMessage = {
  message_id: UUID;
  run_id: UUID;
  sender_agent_id: string;
  recipient_agent_id: string;
  task_type: string;
  payload: Record<string, unknown>;
  depends_on_message_ids: UUID[];
  requires_human_feedback: boolean;
  status: string;
  claimed_by_agent_id?: string | null;
  attempt_count: number;
  max_attempts: number;
  result: Record<string, unknown>;
  error?: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentMessageCreate = {
  run_id: UUID;
  sender_agent_id: string;
  recipient_agent_id: string;
  task_type: string;
  payload?: Record<string, unknown>;
  depends_on_message_ids?: UUID[];
  requires_human_feedback?: boolean;
  max_attempts?: number;
};

export type AgentMessageCreateResult = {
  message_id: UUID;
  run_id: UUID;
  accepted: boolean;
  recipient_agent_id: string;
  event_id?: number | null;
  status: string;
};

export type AgentMessageRetryResult = {
  message: AgentMessage;
  event_id?: number | null;
  summary: string;
};

export type RunEvent = {
  event_id: number;
  run_id: UUID;
  event_type: string;
  actor: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type SourceRecord = {
  source_id: UUID;
  run_id: UUID;
  citation_id: string;
  title: string;
  url: string;
  publisher?: string | null;
  retrieved_at: string;
  published_at?: string | null;
  metadata: Record<string, unknown>;
};

export type SourceEvidenceRecord = {
  source_id?: UUID;
  citation_id?: string;
  title?: string;
  url?: string;
  publisher?: string | null;
  source_type?: string;
  snippet?: string | null;
  search_query?: string | null;
  search_rank?: number | null;
  published_at?: string | null;
  retrieved_at?: string | null;
  quality_status?: string | null;
  freshness_status?: string | null;
  quality_flags?: string[];
  claim_ids?: UUID[];
  artifact_ids?: UUID[];
  accepted_for_context?: boolean;
  retrieval_rank?: number | null;
  retrieval_rerank_score?: number | null;
  retrieval_reranker?: string | null;
  retrieval_rerank_reason?: string | null;
  retrieval_precision_risks?: string[];
  retrieval_recall_risks?: string[];
  retrieval_coverage_topics?: string[];
};

export type ClaimRecord = {
  claim_id: UUID;
  run_id: UUID;
  claim_text: string;
  support_status: ClaimSupportStatus;
  source_ids: UUID[];
  reviewer_agent_id?: string | null;
  notes?: string | null;
};

export type ArtifactRecord = {
  artifact_id: UUID;
  run_id: UUID;
  artifact_type: ArtifactType;
  title: string;
  uri: string;
  content: Record<string, unknown>;
  provenance: Record<string, unknown>;
  source_ids: UUID[];
  reviewer_decisions: Array<Record<string, unknown>>;
  revision_history: Array<Record<string, unknown>>;
  created_at: string;
};

export type FeedbackItem = {
  feedback_id: UUID;
  run_id: UUID;
  author: string;
  target_agent_id?: string | null;
  feedback_text: string;
  status: FeedbackStatus;
  metadata: Record<string, unknown>;
  resolution_notes?: string | null;
  resolved_by?: string | null;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type RunContextPacket = {
  run: RunState;
  conversation_turns: ConversationTurn[];
  agent_messages: AgentMessage[];
  recent_events: RunEvent[];
  sources: SourceRecord[];
  claims: ClaimRecord[];
  artifacts: ArtifactRecord[];
  feedback_items: FeedbackItem[];
  summary: Record<string, unknown>;
  context_risks?: Array<
    | string
    | {
        risk_type?: string;
        severity?: string;
        owner_agent_id?: string;
        reason?: string;
        metadata?: Record<string, unknown>;
      }
  >;
  recommended_fetches?: string[];
  source_evidence?: SourceEvidenceRecord[];
};

export type RunWorkPlanItem = {
  item_id: UUID;
  item_type: string;
  title: string;
  owner_agent_id: string;
  status: string;
  priority: string;
  blocking: boolean;
  source_message_id?: UUID | null;
  source_feedback_id?: UUID | null;
  recommended_action: string;
  reason: string;
  metadata: Record<string, unknown>;
};

export type RunWorkPlanResult = {
  run_id: UUID;
  plan_items: RunWorkPlanItem[];
  recommended_agent_ids: string[];
  open_feedback_count: number;
  routed_feedback_count: number;
  pending_task_count: number;
  blocked_item_count: number;
  created_task_message_ids: UUID[];
  skipped_duplicate_task_count: number;
  artifact_id?: UUID | null;
  event_id?: number | null;
  refresh_reason?: string | null;
  summary: string;
};

export type OrchestrationRequest = {
  transcript: string;
  modality: "text" | "voice";
  speaker: "user";
  audio_uri?: string | null;
  topic?: string | null;
  target_formats: string[];
  require_human_feedback: boolean;
};

export type OrchestrationResult = {
  run_id: UUID;
  turn_id: UUID;
  task_message_ids: UUID[];
  source_ids: UUID[];
  claim_ids: UUID[];
  artifact_ids: UUID[];
  feedback_gate_opened: boolean;
  summary: string;
};

export type ConversationRouteIntent =
  | "auto"
  | "create_content"
  | "revise_content"
  | "route_task"
  | "record_only";

export type ConversationRouteRequest = {
  run_id?: UUID | null;
  transcript: string;
  modality: "text" | "voice" | string;
  speaker: "user" | string;
  audio_uri?: string | null;
  topic?: string | null;
  target_artifact_ids: UUID[];
  target_formats: string[];
  intent: ConversationRouteIntent;
  require_human_feedback: boolean;
  metadata: Record<string, unknown>;
};

export type ConversationRouteResult = {
  run_id: UUID;
  turn_id: UUID;
  response_turn_id?: UUID | null;
  routed_intent: ConversationRouteIntent;
  response_text: string;
  created_run: boolean;
  task_message_ids: UUID[];
  artifact_ids: UUID[];
  target_artifact_ids: UUID[];
  feedback_id?: UUID | null;
  feedback_gate_opened: boolean;
  summary: string;
};

export type AgentWorkerTaskResult = {
  message_id: UUID;
  task_type: string;
  status: string;
  generation_mode: string;
  summary: string;
};

export type AgentWorkerRunResult = {
  run_id: UUID;
  agent_id: string;
  processed_tasks: AgentWorkerTaskResult[];
  recovered_stale_tasks: number;
  blocked_exhausted_tasks: number;
  dependency_blocked_tasks: number;
  idle: boolean;
  summary: string;
};

export type AgentWorkerCycleResult = {
  run_id: UUID;
  agent_ids: string[];
  rounds_completed: number;
  worker_results: AgentWorkerRunResult[];
  total_processed_tasks: number;
  idle: boolean;
  summary: string;
};

export type WorkerProfile = {
  profile_id: UUID;
  run_id: UUID;
  name: string;
  execution_mode: "worker_cycle" | "autonomous_pass" | string;
  agent_ids: string[];
  max_tasks_per_agent: number;
  max_rounds: number;
  poll_interval_seconds: number;
  include_global_memories: boolean;
  memory_limit: number;
  autonomous_auto_refresh_research_sources: boolean;
  autonomous_block_on_research_freshness_blocked: boolean;
  autonomous_block_on_retrieval_quality_blocked: boolean;
  autonomous_export_memory_summary_to_obsidian: boolean;
  autonomous_memory_summary_agent_id?: string | null;
  autonomous_memory_summary_limit: number;
  use_gemma: boolean;
  fail_on_provider_error: boolean;
  status: "paused" | "active" | "running" | "started" | "stopped" | string;
  last_heartbeat_at?: string | null;
  heartbeat_claimed_at?: string | null;
  heartbeat_claimed_by?: string | null;
  heartbeat_lease_until?: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkerProfileHeartbeatResult = {
  profile: WorkerProfile;
  skipped: boolean;
  skipped_reason?: string | null;
  summary: string;
  heartbeat_ledger_artifact?: ArtifactRecord | null;
  context_packet_artifact?: ArtifactRecord | null;
  autonomous_pass_result?: Record<string, unknown> | null;
  cycle_result?: AgentWorkerCycleResult | null;
};

export type WorkerSchedulerRunResult = {
  checked_profiles: number;
  heartbeat_results: WorkerProfileHeartbeatResult[];
  total_processed_tasks: number;
  idle: boolean;
  summary: string;
};

export type AutopilotLaunchResult = {
  run_id: UUID;
  profile: WorkerProfile;
  created_profile: boolean;
  reused_profile: boolean;
  started_profile: boolean;
  heartbeat_result?: WorkerProfileHeartbeatResult | null;
  launch_ledger_artifact?: ArtifactRecord | null;
  event_id?: number | null;
  summary: string;
};

export type RealtimeSessionCreateResult = {
  run_id: UUID;
  realtime_session_id: UUID;
  provider: string;
  session_id: string;
  client_secret?: string | null;
  websocket_url?: string | null;
  transport?: {
    framework: string;
    url?: string | null;
    room_name?: string | null;
    participant_identity?: string | null;
    agent_identity?: string | null;
    token?: string | null;
    has_token?: boolean;
    token_persisted?: boolean;
    expires_at_unix?: number | null;
    metadata?: Record<string, unknown>;
  } | null;
  expires_at_unix?: number | null;
  event_id?: number | null;
  metadata: Record<string, unknown>;
};

export type RealtimeSessionCreateInput = {
  provider?: string;
  voice?: string;
  transportFramework?: string;
  roomName?: string;
  participantIdentity?: string;
  agentParticipantIdentity?: string;
  contextWindowTurns?: number;
  summarizeAfterTurns?: number;
  dryRun: boolean;
};

export type RealtimeVoiceAgentEventRecordResult = {
  run_id: UUID;
  realtime_session_id: UUID;
  event_id: number;
  event_type: string;
  materialized_turn_id?: UUID | null;
  materialized_speaker?: string | null;
  followup_task_message_id?: UUID | null;
  followup_kind?: string | null;
  followup_worker_agent_ids?: string[];
  followup_worker_use_gemma?: boolean | null;
  summary: string;
};

export type VoiceAgentPresenceResult = {
  run_id: UUID;
  realtime_session_id?: UUID | null;
  status: "ready" | "stale" | "missing" | string;
  observed: boolean;
  stale: boolean;
  stale_after_seconds: number;
  event_age_seconds?: number | null;
  latest_event_id?: number | null;
  latest_event_type?: string | null;
  latest_event_created_at?: string | null;
  provider?: string | null;
  provider_session_id?: string | null;
  transport_framework?: string | null;
  room_name?: string | null;
  agent_participant_identity?: string | null;
  livekit_sender_identity?: string | null;
  probe_id?: string | null;
  audio_input_model?: string | null;
  reasoning_model?: string | null;
  audio_output_model?: string | null;
  evidence: string[];
  missing_evidence: string[];
  next_actions: string[];
  summary: string;
};

export type VoiceAgentProcessStatusResult = {
  enabled: boolean;
  status: "disabled" | "stopped" | "starting" | "running" | "exited" | "failed" | string;
  running: boolean;
  pid?: number | null;
  returncode?: number | null;
  last_error?: string | null;
  started_at?: string | null;
  stopped_at?: string | null;
  command: string[];
  log_tail: string[];
  next_actions: string[];
  summary: string;
};

export type LocalLiveKitProcessMode = "native" | "compose" | string;

export type LocalLiveKitProcessStatusResult = {
  enabled: boolean;
  mode: LocalLiveKitProcessMode;
  status: "disabled" | "stopped" | "starting" | "running" | "exited" | "failed" | string;
  running: boolean;
  pid?: number | null;
  returncode?: number | null;
  last_error?: string | null;
  started_at?: string | null;
  stopped_at?: string | null;
  command: string[];
  log_tail: string[];
  next_actions: string[];
  summary: string;
};

export type WorkerSchedulerProcessStatusResult = {
  enabled: boolean;
  status: "disabled" | "stopped" | "starting" | "running" | "exited" | "failed" | string;
  running: boolean;
  pid?: number | null;
  returncode?: number | null;
  last_error?: string | null;
  started_at?: string | null;
  stopped_at?: string | null;
  run_id?: UUID | null;
  execution_mode: "worker_cycle" | "autonomous_pass" | string;
  max_profiles: number;
  poll_interval_seconds: number;
  command: string[];
  log_tail: string[];
  next_actions: string[];
  summary: string;
};

export type VoiceRuntimeReadinessCheck = {
  check_id: string;
  label: string;
  status: "ready" | "degraded" | "blocked" | "unknown" | string;
  required: boolean;
  evidence: string[];
  missing_env: string[];
  next_actions: string[];
  metadata: Record<string, unknown>;
};

export type VoiceRuntimeReadinessResult = {
  status: "ready" | "degraded" | "blocked" | "unknown" | string;
  selected_provider: string;
  transport_framework: string;
  audio_input_model: string;
  reasoning_model: string;
  audio_output_model: string;
  preflight_livekit?: boolean;
  preflight_edge: boolean;
  preflight_agent?: boolean;
  preflight_gemma?: boolean;
  preflight_tts?: boolean;
  checks: VoiceRuntimeReadinessCheck[];
  blockers: string[];
  next_actions: string[];
  summary: string;
};

export type ProviderReadinessItem = {
  provider_id: string;
  provider_type: string;
  display_name: string;
  status: "ready" | "missing_config" | "tool_boundary" | string;
  selected: boolean;
  required_env: string[];
  configured_env: string[];
  missing_env: string[];
  model_ids: string[];
  endpoint_configured?: boolean | null;
  capabilities: string[];
  boundary: string;
  notes: string;
  documentation_url?: string | null;
  next_actions: string[];
  secret_files: ProviderSecretFileStatus[];
};

export type ProviderSecretFileStatus = {
  env_name: string;
  file_env_name: string;
  status: string;
  configured: boolean;
  path?: string | null;
  detail: string;
};

export type LocalSecretFileEnvName =
  | "HF_TOKEN"
  | "LIVEKIT_API_KEY"
  | "LIVEKIT_API_SECRET"
  | "TAVILY_API_KEY";

export type LocalSecretFileWriteResult = {
  env_name: LocalSecretFileEnvName;
  file_env_name: string;
  status: string;
  configured: boolean;
  path: string;
  detail: string;
};

export type LocalProviderConfigEnvName =
  | "GEMMA4_MULTIMODAL_ENDPOINT_URL"
  | "OPENROUTER_LIVEKIT_URL"
  | "GEMMA4_REALTIME_LIVEKIT_URL"
  | "KOKORO_TTS_ENDPOINT_URL";

export type LocalProviderConfigWriteResult = {
  env_name: LocalProviderConfigEnvName;
  status: string;
  configured: boolean;
  config_file_env_name: string;
  path: string;
  detail: string;
};

export type LocalLiveKitDevConfigResult = {
  status: string;
  configured: boolean;
  configured_env: string[];
  config_file_env_name: string;
  secret_file_env_names: string[];
  paths: Record<string, string>;
  detail: string;
};

export type ProviderSmokeTestPlanStep = {
  step_id: string;
  provider_id: string;
  provider_type: string;
  title: string;
  status: string;
  required: boolean;
  live_call: boolean;
  cockpit_action?: string | null;
  api_path?: string | null;
  documentation_url?: string | null;
  required_env: string[];
  missing_env: string[];
  expected_evidence: string[];
  blockers: string[];
  next_actions: string[];
};

export type ProviderReadinessResult = {
  default_realtime_provider: string;
  selected_web_search_provider: string;
  providers: ProviderReadinessItem[];
  ready_provider_ids: string[];
  missing_provider_ids: string[];
  tool_boundary_provider_ids: string[];
  missing_required_env: string[];
  provider_backed_smoke_ready: boolean;
  smoke_test_plan: ProviderSmokeTestPlanStep[];
  demo_walkthrough: string[];
  summary: string;
};

export type VoiceSetupProofStepPayload = {
  id: string;
  label: string;
  status: string;
  detail: string;
  next_action?: string | null;
  required: boolean;
};

export type VoiceSetupProofInput = {
  runId: UUID;
  action: string;
  status: string;
  trigger?: string;
  provider?: string | null;
  realtimeSessionId?: UUID | null;
  transportFramework?: string | null;
  readinessStatus?: string | null;
  liveKitProcessStatus?: string | null;
  voiceAgentProcessStatus?: string | null;
  primaryBlocker?: VoiceSetupProofStepPayload | null;
  steps?: VoiceSetupProofStepPayload[];
  eventSummary?: string | null;
  metadata?: Record<string, unknown>;
  recordArtifact?: boolean;
};

export type VoiceSetupProofResult = {
  run_id: UUID;
  status: string;
  action: string;
  artifact_id?: UUID | null;
  event_id?: number | null;
  summary: string;
  artifact?: ArtifactRecord | null;
};

export type KnownProviderSmokeStepStatus =
  | "passed"
  | "blocked"
  | "failed"
  | "not_run"
  | "tool_boundary";

export type KnownProviderSmokeRunStatus =
  | "passed"
  | "blocked"
  | "failed"
  | "needs_live_smoke"
  | "needs_review";

export type ProviderSmokeStepStatus = KnownProviderSmokeStepStatus | (string & {});
export type ProviderSmokeRunStatus = KnownProviderSmokeRunStatus | (string & {});

export type ProviderSmokeStepResult = {
  step_id: string;
  provider_id: string;
  provider_type: string;
  title: string;
  status: ProviderSmokeStepStatus;
  required: boolean;
  live_call: boolean;
  latency_class?: string | null;
  end_to_end_latency_ms?: number | null;
  provider_latency_ms?: number | null;
  smoke_proof_status?: string | null;
  evidence: string[];
  blockers: string[];
  next_actions: string[];
  source_ids: UUID[];
  realtime_session_ids: UUID[];
  event_ids: number[];
  error?: string | null;
  details: Record<string, unknown>;
};

export type ProviderSmokeRunResult = {
  run_id: UUID;
  status: ProviderSmokeRunStatus;
  execute_live_calls: boolean;
  provider_readiness: ProviderReadinessResult;
  step_count: number;
  passed_count: number;
  blocked_count: number;
  failed_count: number;
  not_run_count: number;
  tool_boundary_count: number;
  source_ids: UUID[];
  realtime_session_ids: UUID[];
  provider_configuration_followup_message_ids: UUID[];
  steps: ProviderSmokeStepResult[];
  ledger_artifact_id?: UUID | null;
  event_id?: number | null;
  summary: string;
};

export type RealtimeVoiceTimingStageEntry = {
  stage_id: string;
  title: string;
  status: string;
  latency_ms?: number | null;
  evidence: string[];
  missing_evidence: string[];
  event_ids: number[];
};

export type RealtimeVoiceTimingTurnEntry = {
  turn_id?: string | null;
  response_id?: string | null;
  realtime_session_id?: UUID | null;
  speech_start_to_turn_commit_ms?: number | null;
  turn_commit_to_agent_turn_ms?: number | null;
  speech_start_to_turn_start_ms?: number | null;
  turn_start_to_gemma_start_ms?: number | null;
  gemma_start_to_first_text_ms?: number | null;
  gemma_start_to_first_audio_ms?: number | null;
  turn_start_to_first_audio_ms?: number | null;
  barge_in_to_cancelled_ms?: number | null;
  failure_stage?: string | null;
  failure_reason?: string | null;
  failed_at_ms?: number | null;
  event_ids: number[];
};

export type RealtimeVoiceTimingLedgerResult = {
  run_id: UUID;
  status: string;
  session_count: number;
  event_count: number;
  measured_stage_count: number;
  missing_stage_count: number;
  stages: RealtimeVoiceTimingStageEntry[];
  turns: RealtimeVoiceTimingTurnEntry[];
  recommended_next_actions: string[];
  ledger_artifact_id?: UUID | null;
  event_id?: number | null;
  summary: string;
};

export type MediaProductionResult = {
  run_id: UUID;
  source_artifact_ids: UUID[];
  media_artifact_ids: UUID[];
  image_artifact_id?: UUID | null;
  audio_artifact_id?: UUID | null;
  video_artifact_id?: UUID | null;
  event_id?: number | null;
  summary: string;
};

export type DistributionPackageResult = {
  run_id: UUID;
  source_artifact_ids: UUID[];
  distribution_artifact_id: UUID;
  platforms: string[];
  event_id?: number | null;
  summary: string;
};

export type GrowthPackageResult = {
  run_id: UUID;
  source_artifact_ids: UUID[];
  distribution_artifact_id: UUID;
  platforms: string[];
  influencer_strategy_artifact_id: UUID;
  outreach_strategy_artifact_id: UUID;
  strategy_artifact_ids: UUID[];
  agent_message_ids: UUID[];
  event_id?: number | null;
  summary: string;
};

export type PublishReadinessStatus = "ready" | "needs_review" | "blocked" | string;

export type PublishChannelCheck = {
  platform: string;
  credential_envs: string[];
  credential_status: string;
  policy_status: string;
  blocking_issues: string[];
  recommended_next_actions: string[];
};

export type PublishReadinessResult = {
  run_id: UUID;
  status: PublishReadinessStatus;
  ready: boolean;
  artifact_ids: UUID[];
  source_count: number;
  claim_count: number;
  audit_count: number;
  open_feedback_count: number;
  blocking_issues: string[];
  recommended_next_actions: string[];
  publish_channel_checks: PublishChannelCheck[];
  feedback_gate_opened: boolean;
  feedback_id?: UUID | null;
  summary: string;
};

export type RealtimeTurnResult = {
  realtime_session?: Record<string, unknown>;
  conversation_turn?: ConversationTurn | null;
  routed_result?: ConversationRouteResult | null;
  summary: string;
  event_id?: number | null;
  brief_task_message_id?: UUID | null;
  spoken_response?: {
    text: string;
    output_channel: string;
    interrupt_previous: boolean;
  } | null;
};

export type RealtimeSessionControlAction = "interrupt" | "resume" | "stop_output";

export type RealtimeSessionControlResult = {
  run_id: UUID;
  realtime_session_id: UUID;
  action: RealtimeSessionControlAction;
  event_id?: number | null;
  followup_task_message_id?: UUID | null;
  summary: string;
};

export type RevisionResult = {
  run_id: UUID;
  feedback_id: UUID;
  task_message_ids: UUID[];
  revised_artifact_ids: UUID[];
  feedback_gate_opened: boolean;
  summary: string;
};

export type FeedbackResolutionResult = {
  feedback: FeedbackItem;
  run_status: RunStatus;
  open_feedback_count: number;
  resolution_ledger?: Record<string, unknown> | null;
  event_id?: number | null;
  summary: string;
};
