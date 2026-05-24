import type {
  AgentMessageCreate,
  AgentMessageCreateResult,
  AgentMessageRetryResult,
  AgentWorkerCycleResult,
  AutopilotLaunchResult,
  ArtifactRecord,
  ClaimRecord,
  ConversationRouteRequest,
  ConversationRouteResult,
  FeedbackResolutionResult,
  FeedbackItem,
  GrowthPackageResult,
  LocalLiveKitDevConfigResult,
  LocalProviderConfigEnvName,
  LocalProviderConfigWriteResult,
  LocalSecretFileEnvName,
  LocalSecretFileWriteResult,
  LocalLiveKitProcessMode,
  LocalLiveKitProcessStatusResult,
  MediaProductionResult,
  OrchestrationRequest,
  OrchestrationResult,
  ProviderReadinessResult,
  ProviderSmokeRunResult,
  PublishReadinessResult,
  RealtimeVoiceTimingLedgerResult,
  RealtimeVoiceAgentEventRecordResult,
  RunCreateInput,
  RealtimeSessionCreateInput,
  RealtimeSessionCreateResult,
  RealtimeSessionControlAction,
  RealtimeSessionControlResult,
  RealtimeTurnResult,
  RevisionResult,
  RunContextPacket,
  RunState,
  RunWorkPlanResult,
  SourceRecord,
  UUID,
  VoiceAgentPresenceResult,
  VoiceAgentProcessStatusResult,
  VoiceRuntimeReadinessResult,
  VoiceSetupProofInput,
  VoiceSetupProofResult,
  WorkerProfile,
  WorkerProfileHeartbeatResult,
  WorkerSchedulerProcessStatusResult,
  WorkerSchedulerRunResult
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "";

type ApiList<T, K extends string> = Record<K, T[]>;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers
      },
      cache: "no-store"
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error("Could not reach the content API. Check that the FastAPI backend is running.");
    }
    throw error;
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail ?? detail;
    } catch {
      // Keep the status text when the backend does not return JSON.
    }
    throw new Error(`${response.status} ${detail}`);
  }

  return response.json() as Promise<T>;
}

export async function createContentRun(input: OrchestrationRequest) {
  return request<OrchestrationResult>("/api/orchestrations/content-studio", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function createRun(input: RunCreateInput) {
  return request<RunState>("/api/runs", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function routeConversationTurn(input: ConversationRouteRequest) {
  return request<ConversationRouteResult>("/api/conversation/turns", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function runAgentWorkerCycle(input: {
  runId: UUID;
  agentIds?: string[];
  messageIds?: UUID[];
  continueMessageLineage?: boolean;
  maxTasksPerAgent?: number;
  maxRounds?: number;
  useGemma?: boolean;
}) {
  return request<AgentWorkerCycleResult>("/api/a2a/workers/run-cycle", {
    method: "POST",
    body: JSON.stringify({
      run_id: input.runId,
      agent_ids: input.agentIds ?? [],
      message_ids: input.messageIds ?? [],
      continue_message_lineage: input.continueMessageLineage === true,
      max_tasks_per_agent: input.maxTasksPerAgent ?? 3,
      max_rounds: input.maxRounds ?? 3,
      include_global_memories: true,
      memory_limit: 6,
      use_gemma: input.useGemma === true,
      fail_on_provider_error: false,
      recover_stale_tasks: true
    })
  });
}

export async function sendAgentMessage(input: AgentMessageCreate) {
  return request<AgentMessageCreateResult>("/api/a2a/messages", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function authorizeAgentMessageRetry(input: {
  messageId: UUID;
  agentId?: string;
  reason: string;
  resetAttemptCount?: boolean;
  maxAttempts?: number;
}) {
  return request<AgentMessageRetryResult>(`/api/a2a/messages/${input.messageId}/retry`, {
    method: "POST",
    body: JSON.stringify({
      agent_id: input.agentId ?? "agent-harness-engineer",
      reason: input.reason,
      reset_attempt_count: input.resetAttemptCount !== false,
      max_attempts: input.maxAttempts ?? null
    })
  });
}

export async function listWorkerProfiles(runId: UUID) {
  const payload = await request<{ profiles: WorkerProfile[] }>(
    `/api/runs/${runId}/worker-profiles`
  );
  return payload.profiles;
}

export async function launchAutopilot(input: {
  runId: UUID;
  profileName?: string;
  useGemma?: boolean;
}) {
  return request<AutopilotLaunchResult>(`/api/runs/${input.runId}/autopilot-launch`, {
    method: "POST",
    body: JSON.stringify({
      profile_name: input.profileName ?? "Creator always-on studio",
      autonomous_export_memory_summary_to_obsidian: true,
      use_gemma: input.useGemma === true,
      reuse_existing_profile: true,
      run_first_heartbeat: true,
      record_artifact: true
    })
  });
}

export async function stopWorkerProfile(profileId: UUID) {
  return request<WorkerProfile>(`/api/worker-profiles/${profileId}/stop`, {
    method: "POST"
  });
}

export async function heartbeatWorkerProfile(profileId: UUID) {
  return request<WorkerProfileHeartbeatResult>(
    `/api/worker-profiles/${profileId}/heartbeat`,
    {
      method: "POST"
    }
  );
}

export async function runWorkerScheduler(input: {
  runId?: UUID;
  executionMode?: string;
  maxProfiles?: number;
}) {
  return request<WorkerSchedulerRunResult>("/api/worker-profiles/scheduler/run", {
    method: "POST",
    body: JSON.stringify({
      max_profiles: input.maxProfiles ?? 10,
      run_id: input.runId ?? null,
      execution_mode: input.executionMode ?? null
    })
  });
}

export async function getWorkerSchedulerProcessStatus() {
  return request<WorkerSchedulerProcessStatusResult>("/api/worker-scheduler-process");
}

export async function startWorkerSchedulerProcess(input: {
  runId: UUID;
  executionMode?: string;
  maxProfiles?: number;
  pollIntervalSeconds?: number;
  forceRestart?: boolean;
}) {
  return request<WorkerSchedulerProcessStatusResult>("/api/worker-scheduler-process/start", {
    method: "POST",
    body: JSON.stringify({
      run_id: input.runId,
      execution_mode: input.executionMode ?? "autonomous_pass",
      max_profiles: input.maxProfiles ?? 10,
      poll_interval_seconds: input.pollIntervalSeconds ?? 5,
      force_restart: input.forceRestart === true
    })
  });
}

export async function stopWorkerSchedulerProcess() {
  return request<WorkerSchedulerProcessStatusResult>("/api/worker-scheduler-process/stop", {
    method: "POST"
  });
}

export async function getRun(runId: UUID) {
  return request<RunState>(`/api/runs/${runId}`);
}

export async function getRunContext(runId: UUID) {
  return request<RunContextPacket>(`/api/runs/${runId}/context-packet`, {
    method: "POST",
    body: JSON.stringify({
      agent_id: null,
      record_event: false,
      include_project_memory_retrieval: true
    })
  });
}

export async function buildRunWorkPlan(input: {
  runId: UUID;
  maxItems?: number;
  createFollowupTasks?: boolean;
  refreshReason?: string;
}) {
  return request<RunWorkPlanResult>(`/api/runs/${input.runId}/work-plan`, {
    method: "POST",
    body: JSON.stringify({
      record_artifact: true,
      include_completed_tasks: false,
      create_followup_tasks: input.createFollowupTasks === true,
      max_items: input.maxItems ?? 8,
      refresh_reason: input.refreshReason ?? "creator_app_next_actions"
    })
  });
}

export async function getProviderReadiness() {
  return request<ProviderReadinessResult>("/api/provider-readiness");
}

export async function saveLocalSecretFile(input: {
  envName: LocalSecretFileEnvName;
  secretValue: string;
}) {
  return request<LocalSecretFileWriteResult>("/api/local-secret-files", {
    method: "POST",
    body: JSON.stringify({
      env_name: input.envName,
      secret_value: input.secretValue
    })
  });
}

export async function saveLocalProviderConfig(input: {
  envName: LocalProviderConfigEnvName;
  configValue: string;
}) {
  return request<LocalProviderConfigWriteResult>("/api/local-provider-config", {
    method: "POST",
    body: JSON.stringify({
      env_name: input.envName,
      config_value: input.configValue
    })
  });
}

export async function configureLocalLiveKitDevConfig() {
  return request<LocalLiveKitDevConfigResult>("/api/local-livekit-dev-config", {
    method: "POST"
  });
}

export async function listArtifacts(runId: UUID) {
  const payload = await request<ApiList<ArtifactRecord, "artifacts">>(
    `/api/runs/${runId}/artifacts`
  );
  return payload.artifacts;
}

export async function listSources(runId: UUID) {
  const payload = await request<ApiList<SourceRecord, "sources">>(
    `/api/runs/${runId}/sources`
  );
  return payload.sources;
}

export async function listClaims(runId: UUID) {
  const payload = await request<ApiList<ClaimRecord, "claims">>(
    `/api/runs/${runId}/claims`
  );
  return payload.claims;
}

export async function listFeedback(runId: UUID) {
  const payload = await request<ApiList<FeedbackItem, "feedback">>(
    `/api/runs/${runId}/feedback`
  );
  return payload.feedback;
}

export async function startRealtimeSession(
  runId: UUID,
  input: RealtimeSessionCreateInput
) {
  return request<RealtimeSessionCreateResult>(
    `/api/runs/${runId}/realtime-session`,
    {
      method: "POST",
      body: JSON.stringify({
        provider: input.provider || null,
        voice: input.voice || null,
        transport_framework: input.transportFramework ?? "livekit",
        room_name: input.roomName ?? null,
        participant_identity: input.participantIdentity ?? null,
        agent_participant_identity: input.agentParticipantIdentity ?? null,
        context_window_turns: input.contextWindowTurns ?? 4,
        summarize_after_turns: input.summarizeAfterTurns ?? 3,
        dry_run: input.dryRun,
        metadata: {
          frontend: "next-app",
          selected_voice_provider: input.provider || "local_rehearsal"
        }
      })
    }
  );
}

export async function sendRealtimeTurn(input: {
  realtimeSessionId: UUID;
  transcript: string;
  speaker?: "user" | "assistant";
  modality?: "voice" | "text";
  topic?: string;
  targetFormats: string[];
  routeTurn?: boolean;
  interrupted?: boolean;
  metadata?: Record<string, unknown>;
}) {
  return request<RealtimeTurnResult>(
    `/api/realtime-sessions/${input.realtimeSessionId}/turns`,
    {
      method: "POST",
      body: JSON.stringify({
        speaker: input.speaker ?? "user",
        transcript: input.transcript,
        modality: input.modality ?? "voice",
        topic: input.topic || null,
        target_formats: input.targetFormats,
        route_turn: input.routeTurn ?? true,
        create_realtime_brief_task: true,
        require_human_feedback: true,
        interrupted: input.interrupted ?? false,
        metadata: { frontend: "next-app", ...(input.metadata ?? {}) }
      })
    }
  );
}

export async function controlRealtimeSession(input: {
  realtimeSessionId: UUID;
  action: RealtimeSessionControlAction;
  reason?: string;
  cancelGemma?: boolean;
  clearKokoroBuffers?: boolean;
  stopLivekitAudio?: boolean;
  interruptedResponseId?: string;
  clientAudioTimestampMs?: number;
  createFollowupTask?: boolean;
  metadata?: Record<string, unknown>;
}) {
  return request<RealtimeSessionControlResult>(
    `/api/realtime-sessions/${input.realtimeSessionId}/control`,
    {
      method: "POST",
      body: JSON.stringify({
        action: input.action,
        reason: input.reason ?? null,
        cancel_gemma: input.cancelGemma ?? null,
        clear_kokoro_buffers: input.clearKokoroBuffers ?? null,
        stop_livekit_audio: input.stopLivekitAudio ?? null,
        interrupted_response_id: input.interruptedResponseId ?? null,
        client_audio_timestamp_ms: input.clientAudioTimestampMs ?? null,
        create_followup_task: input.createFollowupTask ?? true,
        metadata: { frontend: "next-app", ...(input.metadata ?? {}) }
      })
    }
  );
}

export async function recordRealtimeVoiceEvent(input: {
  realtimeSessionId: UUID;
  eventType: string;
  payload: Record<string, unknown>;
  agentCreatedAt?: string | null;
  voiceAgentEventUid?: string | null;
  source?: string;
}) {
  return request<RealtimeVoiceAgentEventRecordResult>(
    `/api/realtime-sessions/${input.realtimeSessionId}/voice-events`,
    {
      method: "POST",
      body: JSON.stringify({
        event_type: input.eventType,
        voice_agent_event_uid: input.voiceAgentEventUid ?? null,
        payload: input.payload,
        agent_created_at: input.agentCreatedAt ?? null,
        source: input.source ?? "livekit_data_channel"
      })
    }
  );
}

export async function endRealtimeSession(input: {
  realtimeSessionId: UUID;
  reason?: string;
}) {
  return request<Record<string, unknown>>(
    `/api/realtime-sessions/${input.realtimeSessionId}/status`,
    {
      method: "POST",
      body: JSON.stringify({
        status: "ended",
        reason: input.reason ?? "Ended from Next live voice panel."
      })
    }
  );
}

export async function getVoiceRuntimeReadiness(input?: {
  preflightLivekit?: boolean;
  preflightEdge?: boolean;
  preflightAgent?: boolean;
  preflightGemma?: boolean;
  preflightTts?: boolean;
}) {
  const params = new URLSearchParams();
  if (input?.preflightLivekit) {
    params.set("preflight_livekit", "true");
  }
  if (input?.preflightEdge) {
    params.set("preflight_edge", "true");
  }
  if (input?.preflightAgent) {
    params.set("preflight_agent", "true");
  }
  if (input?.preflightGemma) {
    params.set("preflight_gemma", "true");
  }
  if (input?.preflightTts) {
    params.set("preflight_tts", "true");
  }
  const search = params.size > 0 ? `?${params.toString()}` : "";
  return request<VoiceRuntimeReadinessResult>(`/api/voice-runtime-readiness${search}`);
}

export async function getVoiceAgentPresence(input: {
  runId: UUID;
  realtimeSessionId?: UUID | null;
  probeId?: string | null;
  staleAfterSeconds?: number;
}) {
  const params = new URLSearchParams();
  if (input.realtimeSessionId) {
    params.set("realtime_session_id", input.realtimeSessionId);
  }
  if (input.probeId) {
    params.set("probe_id", input.probeId);
  }
  if (input.staleAfterSeconds) {
    params.set("stale_after_seconds", String(input.staleAfterSeconds));
  }
  const search = params.size > 0 ? `?${params.toString()}` : "";
  return request<VoiceAgentPresenceResult>(
    `/api/runs/${input.runId}/voice-agent-presence${search}`
  );
}

export async function recordVoiceSetupProof(input: VoiceSetupProofInput) {
  return request<VoiceSetupProofResult>(`/api/runs/${input.runId}/voice-setup-proof`, {
    method: "POST",
    body: JSON.stringify({
      action: input.action,
      status: input.status,
      trigger: input.trigger ?? "voice_panel",
      provider: input.provider ?? null,
      realtime_session_id: input.realtimeSessionId ?? null,
      transport_framework: input.transportFramework ?? null,
      readiness_status: input.readinessStatus ?? null,
      livekit_process_status: input.liveKitProcessStatus ?? null,
      voice_agent_process_status: input.voiceAgentProcessStatus ?? null,
      primary_blocker: input.primaryBlocker ?? null,
      steps: input.steps ?? [],
      event_summary: input.eventSummary ?? null,
      metadata: input.metadata ?? {},
      record_artifact: input.recordArtifact ?? true
    })
  });
}

export async function getVoiceAgentProcessStatus() {
  return request<VoiceAgentProcessStatusResult>("/api/voice-agent-process");
}

export async function startVoiceAgentProcess(input?: {
  dev?: boolean;
  unregistered?: boolean;
  forceRestart?: boolean;
}) {
  return request<VoiceAgentProcessStatusResult>("/api/voice-agent-process/start", {
    method: "POST",
    body: JSON.stringify({
      dev: input?.dev ?? false,
      unregistered: input?.unregistered ?? false,
      force_restart: input?.forceRestart ?? false
    })
  });
}

export async function stopVoiceAgentProcess() {
  return request<VoiceAgentProcessStatusResult>("/api/voice-agent-process/stop", {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function getLocalLiveKitProcessStatus() {
  return request<LocalLiveKitProcessStatusResult>("/api/local-livekit-process");
}

export async function startLocalLiveKitProcess(input?: {
  mode?: LocalLiveKitProcessMode;
  forceRestart?: boolean;
}) {
  return request<LocalLiveKitProcessStatusResult>("/api/local-livekit-process/start", {
    method: "POST",
    body: JSON.stringify({
      mode: input?.mode ?? "native",
      force_restart: input?.forceRestart ?? false
    })
  });
}

export async function stopLocalLiveKitProcess() {
  return request<LocalLiveKitProcessStatusResult>("/api/local-livekit-process/stop", {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function buildVoiceProviderSmoke(input: {
  runId: UUID;
  voice?: string;
  executeLiveCalls?: boolean;
  realtimeSessionId?: UUID;
  requireVoiceAgentPresence?: boolean;
  voiceAgentPresenceStaleAfterSeconds?: number;
  maxVoiceAudioArtifactAgeSeconds?: number;
}) {
  return request<ProviderSmokeRunResult>(`/api/runs/${input.runId}/provider-smoke`, {
    method: "POST",
    body: JSON.stringify({
      record_artifact: true,
      execute_live_calls: input.executeLiveCalls ?? false,
      realtime_provider: "openrouter_livekit",
      realtime_session_id: input.realtimeSessionId ?? null,
      require_voice_agent_presence: input.requireVoiceAgentPresence === true,
      voice_agent_presence_stale_after_seconds:
        input.voiceAgentPresenceStaleAfterSeconds ?? 60,
      max_voice_audio_artifact_age_seconds:
        input.maxVoiceAudioArtifactAgeSeconds ?? 120,
      voice: input.voice || "af_heart",
      include_gemma: false,
      include_realtime: true,
      include_web_search: false,
      include_reranker: false,
      include_imagegen_boundary: false,
      topic: "OpenRouter DeepSeek Kokoro LiveKit voice runtime smoke"
    })
  });
}

export async function buildRealtimeVoiceTimingLedger(input: { runId: UUID }) {
  return request<RealtimeVoiceTimingLedgerResult>(
    `/api/runs/${input.runId}/realtime-voice-timing-ledger`,
    {
      method: "POST",
      body: JSON.stringify({
        record_artifact: true,
        event_limit: 500
      })
    }
  );
}

export async function submitRevision(input: {
  runId: UUID;
  feedbackText: string;
  artifactIds: UUID[];
}) {
  return request<RevisionResult>(`/api/runs/${input.runId}/revision-loop`, {
    method: "POST",
    body: JSON.stringify({
      feedback_text: input.feedbackText,
      author: "user",
      target_artifact_ids: input.artifactIds,
      require_human_feedback: true
    })
  });
}

export async function buildMediaProductionPlan(input: {
  runId: UUID;
  artifactIds: UUID[];
}) {
  return request<MediaProductionResult>(`/api/runs/${input.runId}/media-production`, {
    method: "POST",
    body: JSON.stringify({
      target_artifact_ids: input.artifactIds,
      include_image_prompt: true,
      include_audio_brief: true,
      include_video_storyboard: true,
      image_style: "clean educational social visual",
      voice_style: "natural, warm, interruptible, ELI5",
      platform: "instagram_reel"
    })
  });
}

export async function buildGrowthPackage(input: {
  runId: UUID;
  artifactIds: UUID[];
}) {
  return request<GrowthPackageResult>(`/api/runs/${input.runId}/growth-package`, {
    method: "POST",
    body: JSON.stringify({
      target_artifact_ids: input.artifactIds,
      platforms: ["instagram_post", "instagram_reel", "linkedin", "x_thread", "substack"],
      audience: "AI-curious builders, creators, and operators",
      campaign_goal: "educate with source-backed, ELI5 content",
      include_outreach: true,
      created_by_agent_id: "platform-optimization-agent",
      initiated_by_agent_id: "product-manager"
    })
  });
}

export async function checkPublishReadiness(input: {
  runId: UUID;
  artifactIds: UUID[];
}) {
  return request<PublishReadinessResult>(`/api/runs/${input.runId}/publish-readiness`, {
    method: "POST",
    body: JSON.stringify({
      target_artifact_ids: input.artifactIds,
      open_feedback_gate: true,
      mark_run_completed_if_ready: false,
      check_publish_channel_readiness: true,
      acknowledge_publish_channel_policy: false
    })
  });
}

export async function resolveFeedback(input: {
  feedbackId: UUID;
  notes: string;
  resolvedBy?: string;
}) {
  return request<FeedbackResolutionResult>(`/api/feedback/${input.feedbackId}/resolve`, {
    method: "POST",
    body: JSON.stringify({
      resolution_notes: input.notes,
      resolver: input.resolvedBy ?? "user"
    })
  });
}
