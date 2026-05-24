import type {
  ArtifactRecord,
  ProviderReadinessItem,
  ProviderReadinessResult,
  ProviderSecretFileStatus,
  ProviderSmokeRunResult,
  ProviderSmokeStepResult,
  UUID,
  VoiceAgentPresenceResult,
  VoiceRuntimeReadinessResult
} from "@/lib/api/types";
import { runtimeProviderPreflightBlocker } from "./runtimeReadiness";

export type VoiceProviderReleaseGateStatus =
  | "ready"
  | "blocked"
  | "needs_runtime"
  | "needs_live_smoke"
  | "unknown";

export type VoiceProviderReleaseGateCheck = {
  id: string;
  label: string;
  status: VoiceProviderReleaseGateStatus;
  detail: string;
  nextAction?: string;
};

export type VoiceProviderReleaseGate = {
  status: VoiceProviderReleaseGateStatus;
  label: string;
  summary: string;
  checks: VoiceProviderReleaseGateCheck[];
  missingEnv: string[];
  secretFiles: ProviderSecretFileStatus[];
  secretFileGuidance: VoiceProviderSecretFileGuidance[];
};

export type VoiceProviderSecretFileGuidance = {
  envName: string;
  fileEnvName: string;
  status: string;
  configured: boolean;
  path: string | null;
  detail: string;
  action: string;
};

const LOCAL_LIVEKIT_DEV_ENV_NAMES = [
  "GEMMA4_REALTIME_LIVEKIT_URL",
  "LIVEKIT_API_KEY",
  "LIVEKIT_API_SECRET"
];

type VoiceProviderSmokeStepEvidence = {
  step_id: string;
  status: string;
  smoke_proof_status?: string | null;
  realtime_session_ids: string[];
  blockers: string[];
  next_actions: string[];
};

type VoiceProviderSmokeEvidence = {
  status: string;
  execute_live_calls: boolean;
  realtime_session_ids: string[];
  steps: VoiceProviderSmokeStepEvidence[];
  summary: string;
};

function metadataString(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function metadataBoolean(record: Record<string, unknown>, key: string): boolean | null {
  const value = record[key];
  return typeof value === "boolean" ? value : null;
}

function metadataStringList(record: Record<string, unknown>, key: string): string[] {
  const value = record[key];
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string");
}

function metadataRecords(record: Record<string, unknown>, key: string): Record<string, unknown>[] {
  const value = record[key];
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(
    (item): item is Record<string, unknown> =>
      typeof item === "object" && item !== null && !Array.isArray(item)
  );
}

function artifactTime(artifact: ArtifactRecord): number {
  const parsed = Date.parse(artifact.created_at);
  return Number.isFinite(parsed) ? parsed : 0;
}

function latestArtifactBy(
  artifacts: ArtifactRecord[],
  predicate: (artifact: ArtifactRecord) => boolean
) {
  return artifacts
    .filter(predicate)
    .sort((left, right) => artifactTime(right) - artifactTime(left))[0] ?? null;
}

function selectedProvider(
  readiness: ProviderReadinessResult,
  providerType: string
): ProviderReadinessItem | null {
  return readiness.providers.find((provider) => provider.provider_type === providerType && provider.selected) ?? null;
}

function providerCheck(
  id: string,
  label: string,
  provider: ProviderReadinessItem | null
): VoiceProviderReleaseGateCheck {
  if (!provider) {
    return {
      id,
      label,
      status: "blocked",
      detail: "Selected provider is not present in provider readiness.",
      nextAction: "Refresh provider readiness and check backend provider configuration."
    };
  }
  if (provider.status === "ready") {
    return {
      id,
      label,
      status: "ready",
      detail: `${provider.display_name} is configured.`
    };
  }
  const localLiveKitDevBootstrapAvailable =
    provider.provider_id === "gemma4-realtime" &&
    provider.provider_type === "realtime_audio" &&
    LOCAL_LIVEKIT_DEV_ENV_NAMES.every((envName) => provider.missing_env.includes(envName));
  return {
    id,
    label,
    status: "blocked",
    detail:
      provider.missing_env.length > 0
        ? `${provider.display_name} is missing ${provider.missing_env.join(", ")}.`
        : `${provider.display_name} is ${provider.status}.`,
    nextAction: localLiveKitDevBootstrapAvailable
      ? "Use local LiveKit dev defaults"
      : provider.next_actions[0]
  };
}

function runtimeCheck(
  readiness: VoiceRuntimeReadinessResult | null
): VoiceProviderReleaseGateCheck {
  if (!readiness) {
    return {
      id: "runtime",
      label: "Runtime preflight",
      status: "needs_runtime",
      detail: "Voice runtime preflight has not been checked yet.",
      nextAction: "Run Runtime preflight."
    };
  }
  const providerPreflightBlocker = runtimeProviderPreflightBlocker(readiness);
  if (providerPreflightBlocker) {
    return {
      id: "runtime",
      label: "Runtime preflight",
      status: "needs_runtime",
      detail: providerPreflightBlocker.detail,
      nextAction: providerPreflightBlocker.nextAction
    };
  }
  if (readiness.status === "ready" || readiness.status === "degraded") {
    return {
      id: "runtime",
      label: "Runtime preflight",
      status: "ready",
      detail: readiness.summary
    };
  }
  return {
    id: "runtime",
    label: "Runtime preflight",
    status: readiness.status === "blocked" ? "blocked" : "needs_runtime",
    detail: readiness.summary,
    nextAction: readiness.next_actions[0] ?? "Run Runtime preflight."
  };
}

function activeSessionCheck(activeRealtimeSessionId: UUID | null): VoiceProviderReleaseGateCheck {
  if (activeRealtimeSessionId) {
    return {
      id: "active-session",
      label: "Active LiveKit session",
      status: "ready",
      detail: `Current session ${activeRealtimeSessionId} is joined.`
    };
  }
  return {
    id: "active-session",
    label: "Active LiveKit session",
    status: "needs_runtime",
    detail: "No active provider-backed Gemma/Kokoro LiveKit session is joined.",
    nextAction: "Join the Gemma/Kokoro voice room before claiming current-session readiness."
  };
}

function liveSmokeCheck(
  smoke: VoiceProviderSmokeEvidence | null,
  activeRealtimeSessionId: UUID | null
): VoiceProviderReleaseGateCheck {
  const streamingStep = smoke?.steps.find(
    (step) => step.step_id === "gemma-kokoro-voice-streaming-smoke"
  );
  if (!smoke) {
    return {
      id: "live-smoke",
      label: "Live Gemma/Kokoro smoke",
      status: "needs_live_smoke",
      detail: "No provider smoke ledger has been built for this run.",
      nextAction: "Join the room, speak once, enable Live smoke, then run Runtime smoke."
    };
  }
  if (
    activeRealtimeSessionId &&
    (!smoke.realtime_session_ids.includes(activeRealtimeSessionId) ||
      !streamingStep?.realtime_session_ids.includes(activeRealtimeSessionId))
  ) {
    return {
      id: "live-smoke",
      label: "Live Gemma/Kokoro smoke",
      status: "needs_live_smoke",
      detail: "The latest provider smoke proof is not bound to the active LiveKit session.",
      nextAction: "Speak in the active room and rerun live Runtime smoke."
    };
  }
  if (
    smoke.execute_live_calls &&
    smoke.status === "passed" &&
    streamingStep?.status === "passed" &&
    streamingStep.smoke_proof_status === "provider_backed"
  ) {
    return {
      id: "live-smoke",
      label: "Live Gemma/Kokoro smoke",
      status: "ready",
      detail: "Provider-backed Gemma/Kokoro voice streaming smoke passed."
    };
  }
  if (!smoke.execute_live_calls) {
    return {
      id: "live-smoke",
      label: "Live Gemma/Kokoro smoke",
      status: "needs_live_smoke",
      detail: "The latest smoke ledger did not execute live provider calls.",
      nextAction: "Enable Live smoke and rerun Runtime smoke after speaking in the active room."
    };
  }
  if (smoke.status === "blocked" || smoke.status === "failed" || streamingStep?.status === "blocked") {
    return {
      id: "live-smoke",
      label: "Live Gemma/Kokoro smoke",
      status: "blocked",
      detail: streamingStep?.blockers[0] ?? smoke.summary,
      nextAction: streamingStep?.next_actions[0] ?? "Resolve the smoke blocker and rerun Runtime smoke."
    };
  }
  return {
    id: "live-smoke",
    label: "Live Gemma/Kokoro smoke",
    status: "needs_live_smoke",
    detail: smoke.summary,
    nextAction: "Rerun live Runtime smoke until Gemma/Kokoro streaming proof passes."
  };
}

function providerSmokeEvidenceFromArtifact(
  artifact: ArtifactRecord | null
): VoiceProviderSmokeEvidence | null {
  if (!artifact) {
    return null;
  }
  const status = metadataString(artifact.content, "status");
  const executeLiveCalls = metadataBoolean(artifact.content, "execute_live_calls");
  if (!status || executeLiveCalls === null) {
    return null;
  }
  return {
    status,
    execute_live_calls: executeLiveCalls,
    realtime_session_ids: metadataStringList(artifact.content, "realtime_session_ids"),
    steps: metadataRecords(artifact.content, "steps").map((step) => ({
      step_id: metadataString(step, "step_id") ?? "",
      status: metadataString(step, "status") ?? "not_run",
      smoke_proof_status: metadataString(step, "smoke_proof_status"),
      realtime_session_ids: metadataStringList(step, "realtime_session_ids"),
      blockers: metadataStringList(step, "blockers"),
      next_actions: metadataStringList(step, "next_actions")
    })),
    summary: metadataString(artifact.content, "summary") ?? artifact.title
  };
}

function latestProviderSmokeArtifact(artifacts: ArtifactRecord[]) {
  return latestArtifactBy(
    artifacts,
    (artifact) =>
      artifact.artifact_type === "provider_smoke_ledger" &&
      metadataString(artifact.provenance, "workflow") === "provider_smoke_ledger_v1"
  );
}

function providerSmokeStepContent(step: ProviderSmokeStepResult): Record<string, unknown> {
  return {
    step_id: step.step_id,
    status: step.status,
    smoke_proof_status: step.smoke_proof_status ?? null,
    realtime_session_ids: step.realtime_session_ids,
    blockers: step.blockers,
    next_actions: step.next_actions
  };
}

export function providerSmokeArtifactFromResult(
  smoke: ProviderSmokeRunResult,
  createdAt = new Date().toISOString()
): ArtifactRecord {
  const artifactId = smoke.ledger_artifact_id ?? `current-provider-smoke-${smoke.event_id ?? "pending"}`;
  return {
    artifact_id: artifactId,
    run_id: smoke.run_id,
    artifact_type: "provider_smoke_ledger",
    title: "Current provider smoke ledger",
    uri: `artifact://runs/${smoke.run_id}/provider-smoke/${artifactId}`,
    content: {
      status: smoke.status,
      execute_live_calls: smoke.execute_live_calls,
      realtime_session_ids: smoke.realtime_session_ids,
      steps: smoke.steps.map(providerSmokeStepContent),
      summary: smoke.summary
    },
    provenance: {
      workflow: "provider_smoke_ledger_v1",
      source: "current_provider_smoke_result"
    },
    source_ids: smoke.source_ids,
    reviewer_decisions: [],
    revision_history: [],
    created_at: createdAt
  };
}

function providerRecoveryCheck(
  artifacts: ArtifactRecord[],
  activeRealtimeSessionId: UUID | null
): VoiceProviderReleaseGateCheck | null {
  const latestRecovery = latestArtifactBy(
    artifacts,
    (artifact) =>
      artifact.artifact_type === "provider_operations_ledger" &&
      [
        "realtime_provider_failure_recovery",
        "provider_configuration_recovery"
      ].includes(metadataString(artifact.content, "format") ?? "")
  );
  if (!latestRecovery) {
    return null;
  }

  const latestSmoke = latestProviderSmokeArtifact(artifacts);
  const recoveryTime = artifactTime(latestRecovery);
  const smokeTime = latestSmoke ? artifactTime(latestSmoke) : 0;
  const smokeIsNewer = latestSmoke !== null && smokeTime > recoveryTime;
  const smokeSessionIds = latestSmoke
    ? metadataStringList(latestSmoke.content, "realtime_session_ids")
    : [];
  const smokeIsSessionBound =
    !activeRealtimeSessionId || smokeSessionIds.includes(activeRealtimeSessionId);
  const smokePassed =
    latestSmoke !== null &&
    metadataString(latestSmoke.content, "status") === "passed" &&
    metadataBoolean(latestSmoke.content, "execute_live_calls") === true &&
    smokeIsSessionBound;

  if (smokeIsNewer && smokePassed) {
    const format = metadataString(latestRecovery.content, "format");
    return {
      id: "provider-recovery",
      label:
        format === "provider_configuration_recovery"
          ? "Provider configuration recovery"
          : "Provider failure recovery",
      status: "ready",
      detail:
        format === "provider_configuration_recovery"
          ? "A newer provider-backed smoke ledger supersedes the last provider configuration recovery."
          : "A newer provider-backed smoke ledger supersedes the last provider failure."
    };
  }

  const format = metadataString(latestRecovery.content, "format");
  if (format === "provider_configuration_recovery") {
    const blockedSteps = metadataRecords(latestRecovery.content, "blocked_steps");
    const blockedStepCount =
      typeof latestRecovery.content.blocked_step_count === "number"
        ? latestRecovery.content.blocked_step_count
        : blockedSteps.length;
    return {
      id: "provider-recovery",
      label: "Provider configuration recovery",
      status: "blocked",
      detail:
        blockedStepCount > 0
          ? `Latest provider configuration recovery is still blocking ${blockedStepCount} provider-smoke configuration step(s).`
          : "Latest provider configuration recovery is still blocking live voice readiness.",
      nextAction:
        "Rerun live Runtime smoke after provider configuration is repaired."
    };
  }

  const failure = latestRecovery.content.failure;
  const failureComponent =
    failure && typeof failure === "object" && !Array.isArray(failure)
      ? metadataString(failure as Record<string, unknown>, "component")
      : null;
  return {
    id: "provider-recovery",
    label: "Provider failure recovery",
    status: "blocked",
    detail: failureComponent
      ? `Latest provider failure recovery is still blocking ${failureComponent}.`
      : "Latest provider failure recovery is still blocking live voice readiness.",
    nextAction:
      "Run recovery checks, speak in the active room, then rerun live Runtime smoke."
  };
}

function presenceCheck(
  presence: VoiceAgentPresenceResult | null,
  activeRealtimeSessionId: UUID | null
): VoiceProviderReleaseGateCheck {
  if (!presence) {
    return {
      id: "presence",
      label: "Agent participant",
      status: "needs_runtime",
      detail: "No Gemma/Kokoro LiveKit participant proof has been checked.",
      nextAction: "Join the room and probe agent presence."
    };
  }
  if (activeRealtimeSessionId && presence.realtime_session_id !== activeRealtimeSessionId) {
    return {
      id: "presence",
      label: "Agent participant",
      status: "needs_runtime",
      detail: "Gemma/Kokoro participant proof belongs to a different or stale session.",
      nextAction: "Probe agent presence in the active room."
    };
  }
  if (presence.status === "ready") {
    return {
      id: "presence",
      label: "Agent participant",
      status: "ready",
      detail: presence.summary
    };
  }
  return {
    id: "presence",
    label: "Agent participant",
    status: "needs_runtime",
    detail: presence.summary,
    nextAction: presence.next_actions[0] ?? "Probe agent presence."
  };
}

function gateStatus(checks: VoiceProviderReleaseGateCheck[]): VoiceProviderReleaseGateStatus {
  if (checks.some((check) => check.status === "blocked")) {
    return "blocked";
  }
  if (checks.some((check) => check.status === "needs_runtime")) {
    return "needs_runtime";
  }
  if (checks.some((check) => check.status === "needs_live_smoke")) {
    return "needs_live_smoke";
  }
  return checks.every((check) => check.status === "ready") ? "ready" : "unknown";
}

function secretFileAction(secretFile: ProviderSecretFileStatus): string {
  const path = secretFile.path?.trim() || null;
  if (secretFile.status === "loaded") {
    return path ? `Ready from ${path}.` : `${secretFile.file_env_name} points to a readable secret file.`;
  }
  if (secretFile.status === "direct_env") {
    return path
      ? `${secretFile.env_name} is set directly; ${path} is optional for this run.`
      : `${secretFile.env_name} is set directly; no file write is needed for this run.`;
  }
  if (secretFile.status === "missing") {
    return path
      ? `Create ${path} with the ${secretFile.env_name} value, or set ${secretFile.env_name} directly for this process.`
      : `Set ${secretFile.env_name} directly, or configure ${secretFile.file_env_name} to point to a readable secret file.`;
  }
  if (secretFile.status === "not_configured") {
    return `Set ${secretFile.env_name} directly, or configure ${secretFile.file_env_name} to point to a readable secret file.`;
  }
  if (secretFile.status === "empty") {
    return path
      ? `Put the ${secretFile.env_name} value in ${path}, or set ${secretFile.env_name} directly for this process.`
      : `Set ${secretFile.env_name} directly, or point ${secretFile.file_env_name} to a non-empty secret file.`;
  }
  if (secretFile.status === "unreadable") {
    return path
      ? `Fix read permissions for ${path}, or set ${secretFile.env_name} directly for this process.`
      : `Fix ${secretFile.file_env_name}, or set ${secretFile.env_name} directly for this process.`;
  }
  return secretFile.configured
    ? `${secretFile.file_env_name} is configured without exposing the secret value.`
    : `Configure ${secretFile.env_name} directly or through ${secretFile.file_env_name}.`;
}

function buildSecretFileGuidance(
  secretFiles: ProviderSecretFileStatus[]
): VoiceProviderSecretFileGuidance[] {
  return secretFiles.map((secretFile) => ({
    envName: secretFile.env_name,
    fileEnvName: secretFile.file_env_name,
    status: secretFile.status,
    configured: secretFile.configured,
    path: secretFile.path?.trim() || null,
    detail: secretFile.detail,
    action: secretFileAction(secretFile)
  }));
}

export function buildVoiceProviderReleaseGate(input: {
  providerReadiness: ProviderReadinessResult | null;
  runtimeReadiness: VoiceRuntimeReadinessResult | null;
  smoke: ProviderSmokeRunResult | null;
  presence: VoiceAgentPresenceResult | null;
  activeRealtimeSessionId?: UUID | null;
  artifacts?: ArtifactRecord[];
}): VoiceProviderReleaseGate {
  if (!input.providerReadiness) {
    return {
      status: "unknown",
      label: "Provider release gate",
      summary: "Provider readiness has not been loaded yet.",
      checks: [
        {
          id: "provider-readiness",
          label: "Provider readiness",
          status: "unknown",
          detail: "Refresh provider readiness before claiming provider-backed voice readiness.",
          nextAction: "Refresh provider readiness."
        }
      ],
      missingEnv: [],
      secretFiles: [],
      secretFileGuidance: []
    };
  }

  const readiness = input.providerReadiness;
  const gemmaProvider =
    readiness.providers.find((provider) => provider.provider_id === "gemma4-primary") ?? null;
  const realtimeProvider = selectedProvider(readiness, "realtime_audio");
  const webSearchProvider = selectedProvider(readiness, "web_search");
  const rerankerProvider = selectedProvider(readiness, "reranker");
  const activeRealtimeSessionId = input.activeRealtimeSessionId ?? null;
  const recoveryCheck = providerRecoveryCheck(input.artifacts ?? [], activeRealtimeSessionId);
  const smokeEvidence =
    input.smoke ?? providerSmokeEvidenceFromArtifact(
      latestProviderSmokeArtifact(input.artifacts ?? [])
    );
  const checks = [
    providerCheck(
      "gemma-primary",
      "Gemma expert endpoint",
      gemmaProvider
    ),
    providerCheck(
      "realtime-provider",
      "Realtime voice provider",
      realtimeProvider
    ),
    providerCheck(
      "web-search",
      "Web search provider",
      webSearchProvider
    ),
    providerCheck(
      "reranker",
      "Reranker provider",
      rerankerProvider
    ),
    runtimeCheck(input.runtimeReadiness),
    activeSessionCheck(activeRealtimeSessionId),
    presenceCheck(input.presence, activeRealtimeSessionId),
    ...(recoveryCheck ? [recoveryCheck] : []),
    liveSmokeCheck(smokeEvidence, activeRealtimeSessionId)
  ];
  const status = gateStatus(checks);
  const firstAction = checks.find((check) => check.status !== "ready")?.nextAction;
  const selectedProviders = [
    gemmaProvider,
    realtimeProvider,
    webSearchProvider,
    rerankerProvider
  ].filter((provider): provider is ProviderReadinessItem => Boolean(provider));
  const secretFiles = selectedProviders.flatMap((provider) => provider.secret_files);
  const summary =
    status === "ready"
      ? "Provider-backed Gemma/Kokoro voice is release-ready for this run."
      : firstAction ?? readiness.summary;
  return {
    status,
    label: "Provider release gate",
    summary,
    checks,
    missingEnv: [
      ...new Set(
        selectedProviders.flatMap((provider) => provider.missing_env)
      )
    ],
    secretFiles,
    secretFileGuidance: buildSecretFileGuidance(secretFiles)
  };
}
