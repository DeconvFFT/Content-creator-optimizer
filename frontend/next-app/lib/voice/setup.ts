import type {
  LocalLiveKitProcessStatusResult,
  LocalLiveKitDevConfigResult,
  RealtimeSessionCreateResult,
  UUID,
  VoiceAgentPresenceResult,
  VoiceAgentProcessStatusResult,
  VoiceSetupProofStepPayload,
  VoiceRuntimeReadinessResult
} from "@/lib/api/types";
import {
  localLiveKitProcessStartBlocker,
  voiceAgentProcessStartBlocker
} from "./process";
import type { VoiceProviderReleaseGate, VoiceProviderReleaseGateCheck } from "./providerReadiness";
import { runtimeProviderPreflightBlocker } from "./runtimeReadiness";

export type VoiceSetupStepStatus = "ready" | "blocked" | "pending" | "not_applicable";

export type VoiceSetupStep = {
  id: string;
  label: string;
  status: VoiceSetupStepStatus;
  detail: string;
  nextAction?: string;
  required: boolean;
};

export type VoiceSetupAction =
  | "create_run"
  | "start_rehearsal"
  | "configure_local_livekit_dev"
  | "start_livekit"
  | "restart_livekit"
  | "run_preflight"
  | "start_agent"
  | "join_room"
  | "probe_presence"
  | "refresh_provider_readiness"
  | "run_live_smoke";

export type VoiceSetupActionDisabledInput = {
  action: VoiceSetupAction | null;
  readinessLoading: boolean;
  providerReadinessLoading: boolean;
  processLoading: boolean;
  liveKitProcessLoading: boolean;
  status: string;
  localLiveKitDevConfigBusy?: boolean;
};

type VoiceSetupChecklistInput = {
  runId?: UUID;
  provider: string;
  readiness: VoiceRuntimeReadinessResult | null;
  voiceProcess: VoiceAgentProcessStatusResult | null;
  liveKitProcess: LocalLiveKitProcessStatusResult | null;
  liveSession: RealtimeSessionCreateResult | null;
  liveRoomConnected: boolean;
  voicePresence: VoiceAgentPresenceResult | null;
  isRehearsalSession: boolean;
  providerReleaseGate?: VoiceProviderReleaseGate | null;
};

const LOCAL_LIVEKIT_DEV_ENV_NAMES = [
  "GEMMA4_REALTIME_LIVEKIT_URL",
  "LIVEKIT_API_KEY",
  "LIVEKIT_API_SECRET"
];

function pending(label: string, detail: string, nextAction?: string): VoiceSetupStep {
  return { id: label, label, status: "pending", detail, nextAction, required: true };
}

function ready(label: string, detail: string): VoiceSetupStep {
  return { id: label, label, status: "ready", detail, required: true };
}

function blocked(label: string, detail: string, nextAction?: string): VoiceSetupStep {
  return { id: label, label, status: "blocked", detail, nextAction, required: true };
}

function notApplicable(label: string, detail: string): VoiceSetupStep {
  return { id: label, label, status: "not_applicable", detail, required: false };
}

function processStep(
  label: string,
  process: VoiceAgentProcessStatusResult | LocalLiveKitProcessStatusResult | null,
  fallback: string,
  blocker: (process: never) => string | null,
  startAction: string
): VoiceSetupStep {
  if (!process) {
    return pending(label, `${fallback} status has not been checked.`, "Check setup");
  }
  if (!process.enabled) {
    return ready(label, `${fallback} is externally managed.`);
  }
  if (process.running || ["running", "starting", "started"].includes(process.status)) {
    return ready(label, process.summary);
  }
  const reason = blocker(process as never);
  if (reason) {
    return blocked(label, reason, startAction);
  }
  return pending(label, process.summary, "Check setup");
}

function releaseGateStep(
  check: VoiceProviderReleaseGateCheck,
  options: {
    label: string;
    fallbackAction: string;
  }
): VoiceSetupStep | null {
  if (check.status === "ready") {
    return ready(options.label, check.detail);
  }
  if (check.status === "blocked") {
    return blocked(options.label, check.detail, check.nextAction ?? options.fallbackAction);
  }
  if (check.status === "needs_live_smoke") {
    return pending(options.label, check.detail, check.nextAction ?? options.fallbackAction);
  }
  if (check.status === "needs_runtime" || check.status === "unknown") {
    return pending(options.label, check.detail, check.nextAction ?? options.fallbackAction);
  }
  return null;
}

function releaseGateSteps(
  gate: VoiceProviderReleaseGate | null | undefined
): VoiceSetupStep[] {
  if (!gate) {
    return [];
  }
  const providerRecovery = gate.checks.find((check) => check.id === "provider-recovery");
  const liveSmoke = gate.checks.find((check) => check.id === "live-smoke");
  const explicitReleaseChecks = new Set(["provider-recovery", "live-smoke"]);
  const generalReleaseBlockers = gate.checks
    .filter((check) => !explicitReleaseChecks.has(check.id) && check.status !== "ready")
    .map((check) =>
      releaseGateStep(check, {
        label: `Provider release gate: ${check.label}`,
        fallbackAction: "Refresh provider readiness"
      })
    );
  return [
    ...generalReleaseBlockers,
    providerRecovery
      ? releaseGateStep(providerRecovery, {
          label: providerRecovery.label,
          fallbackAction: "Run live smoke"
        })
      : null,
    liveSmoke
      ? releaseGateStep(liveSmoke, {
          label: "Live smoke proof",
          fallbackAction: "Run live smoke"
        })
      : null
  ].filter((step): step is VoiceSetupStep => step !== null);
}

function requiredRuntimeBlocker(readiness: VoiceRuntimeReadinessResult) {
  return readiness.checks.find(
    (check) =>
      check.required !== false &&
      (check.status === "blocked" || check.status === "failed")
  );
}

function runtimeReadinessDetail(readiness: VoiceRuntimeReadinessResult | null) {
  if (!readiness) {
    return "Runtime readiness has not been checked with LiveKit, Rust edge, Gemma/HF, and Kokoro.";
  }
  const providerPreflightBlocker = runtimeProviderPreflightBlocker(readiness);
  if (providerPreflightBlocker) {
    return providerPreflightBlocker.detail;
  }
  const blocker = requiredRuntimeBlocker(readiness);
  if (!blocker) {
    return readiness.summary;
  }
  const detail = blocker.evidence[0] ?? blocker.missing_env[0] ?? readiness.summary;
  return `${blocker.label}: ${detail}`;
}

function runtimeReadinessAction(readiness: VoiceRuntimeReadinessResult) {
  const providerPreflightBlocker = runtimeProviderPreflightBlocker(readiness);
  if (providerPreflightBlocker) {
    return providerPreflightBlocker.nextAction;
  }
  return (
    requiredRuntimeBlocker(readiness)?.next_actions[0] ??
    readiness.next_actions[0] ??
    "Run preflight"
  );
}

function missingLocalLiveKitDevConfig(missingEnv: string[]) {
  return LOCAL_LIVEKIT_DEV_ENV_NAMES.every((envName) => missingEnv.includes(envName));
}

function liveKitPreflightFailedWithRunningLocalProcess(
  readiness: VoiceRuntimeReadinessResult,
  liveKitProcess: LocalLiveKitProcessStatusResult | null
) {
  const blocker = requiredRuntimeBlocker(readiness);
  return (
    blocker?.check_id === "livekit-transport" &&
    blocker.missing_env.length === 0 &&
    blocker.metadata.configured_for_local_dev === true &&
    blocker.metadata.connectivity_preflight_performed === true &&
    liveKitProcess?.enabled === true &&
    (liveKitProcess.running || ["running", "starting", "started"].includes(liveKitProcess.status))
  );
}

function runtimeReadinessNextAction(
  readiness: VoiceRuntimeReadinessResult,
  liveKitProcess: LocalLiveKitProcessStatusResult | null
) {
  const blocker = requiredRuntimeBlocker(readiness);
  if (blocker?.check_id === "livekit-transport" && missingLocalLiveKitDevConfig(blocker.missing_env)) {
    return "Use local LiveKit dev defaults";
  }
  if (liveKitPreflightFailedWithRunningLocalProcess(readiness, liveKitProcess)) {
    return "Restart local LiveKit transport";
  }
  return runtimeReadinessAction(readiness);
}

export function buildVoiceSetupChecklist(input: VoiceSetupChecklistInput): VoiceSetupStep[] {
  if (input.provider === "local_rehearsal") {
    return [
      input.runId
        ? ready("Content run", `Run ${input.runId} is active.`)
        : blocked("Content run", "Create or restore a run before starting rehearsal."),
      input.isRehearsalSession && input.liveSession
        ? ready("Rehearsal session", "Transcript rehearsal session is active.")
        : pending("Rehearsal session", "Transcript rehearsal is not running.", "Start transcript rehearsal"),
      notApplicable("LiveKit transport", "Transcript rehearsal does not use LiveKit media."),
      notApplicable("Gemma/Kokoro agent", "Transcript rehearsal does not prove provider-backed speech.")
    ];
  }

  const readiness = input.readiness;
  const readinessDetail = runtimeReadinessDetail(readiness);
  const providerPreflightBlocker = runtimeProviderPreflightBlocker(readiness);
  let readinessStep: VoiceSetupStep;
  if (providerPreflightBlocker) {
    readinessStep = pending(
      "Runtime readiness",
      readinessDetail,
      providerPreflightBlocker.nextAction
    );
  } else if (readiness?.status === "ready" || readiness?.status === "degraded") {
    readinessStep = ready("Runtime readiness", readinessDetail);
  } else if (readiness?.status === "blocked" || readiness?.status === "failed") {
    readinessStep = blocked(
      "Runtime readiness",
      readinessDetail,
      runtimeReadinessNextAction(readiness, input.liveKitProcess)
    );
  } else {
    readinessStep = pending("Runtime readiness", readinessDetail, "Run preflight");
  }

  const roomStep =
    input.liveRoomConnected && input.liveSession
      ? ready("LiveKit room", input.liveSession.transport?.room_name ?? "LiveKit room is joined.")
      : pending("LiveKit room", "No active provider-backed room is joined.", "Join voice room");

  const presenceStep =
    !input.liveRoomConnected
      ? pending("Agent presence", "Join the LiveKit room before checking participant presence.")
      : input.voicePresence?.status === "ready"
        ? ready("Agent presence", input.voicePresence.summary)
        : blocked(
            "Agent presence",
            input.voicePresence?.summary ?? "Gemma/Kokoro participant has not been observed.",
            input.voicePresence?.next_actions[0] ?? "Probe agent presence"
          );

  return [
    input.runId
      ? ready("Content run", `Run ${input.runId} is active.`)
      : blocked("Content run", "Create or restore a run before starting live voice."),
    processStep(
      "LiveKit transport",
      input.liveKitProcess,
      "Local LiveKit transport",
      localLiveKitProcessStartBlocker as (process: never) => string | null,
      "Start LiveKit transport"
    ),
    readinessStep,
    processStep(
      "Gemma/Kokoro agent",
      input.voiceProcess,
      "Local Gemma/Kokoro agent",
      voiceAgentProcessStartBlocker as (process: never) => string | null,
      "Start Gemma/Kokoro agent"
    ),
    roomStep,
    presenceStep,
    ...releaseGateSteps(input.providerReleaseGate)
  ];
}

export function voiceSetupPrimaryBlocker(steps: VoiceSetupStep[]) {
  return (
    steps.find((step) => step.required && step.status === "blocked") ??
    steps.find((step) => step.required && step.status === "pending") ??
    null
  );
}

export function voiceSetupActionForStep(step: VoiceSetupStep | null): VoiceSetupAction | null {
  if (!step) {
    return null;
  }
  if (step.label === "Content run") {
    return "create_run";
  }
  if (step.label === "Rehearsal session") {
    return "start_rehearsal";
  }
  if (step.label === "LiveKit transport") {
    return "start_livekit";
  }
  if (step.label === "Runtime readiness") {
    if (step.nextAction === "Use local LiveKit dev defaults") {
      return "configure_local_livekit_dev";
    }
    if (step.nextAction === "Restart local LiveKit transport") {
      return "restart_livekit";
    }
    return "run_preflight";
  }
  if (step.label === "Gemma/Kokoro agent") {
    return "start_agent";
  }
  if (step.label === "LiveKit room") {
    return "join_room";
  }
  if (step.label === "Agent presence") {
    return "probe_presence";
  }
  if (
    step.label === "Provider failure recovery" ||
    step.label === "Provider configuration recovery" ||
    step.label === "Live smoke proof"
  ) {
    return "run_live_smoke";
  }
  if (step.label.startsWith("Provider release gate:")) {
    if (step.nextAction === "Use local LiveKit dev defaults") {
      return "configure_local_livekit_dev";
    }
    return "refresh_provider_readiness";
  }
  return null;
}

export function voiceSetupActionLabel(action: VoiceSetupAction | null) {
  switch (action) {
    case "create_run":
      return "Create run first";
    case "start_rehearsal":
      return "Start rehearsal";
    case "configure_local_livekit_dev":
      return "Configure LiveKit dev";
    case "start_livekit":
      return "Start LiveKit";
    case "restart_livekit":
      return "Restart LiveKit";
    case "run_preflight":
      return "Run preflight";
    case "start_agent":
      return "Start agent";
    case "join_room":
      return "Join room";
    case "probe_presence":
      return "Probe presence";
    case "refresh_provider_readiness":
      return "Refresh providers";
    case "run_live_smoke":
      return "Run live smoke";
    default:
      return "Resolve next";
  }
}

export function isVoiceSetupActionDisabled(input: VoiceSetupActionDisabledInput) {
  if (!input.action || input.action === "create_run") {
    return true;
  }
  if (
    input.action === "configure_local_livekit_dev" &&
    input.localLiveKitDevConfigBusy
  ) {
    return true;
  }
  return (
    input.readinessLoading ||
    input.providerReadinessLoading ||
    input.processLoading ||
    input.liveKitProcessLoading ||
    ["starting", "joining", "stopping"].includes(input.status)
  );
}

export function localLiveKitDevSetupProofMetadata(
  result: LocalLiveKitDevConfigResult | null
): Record<string, unknown> {
  return {
    configured_env: result?.configured_env ?? [],
    config_file_env_name: result?.config_file_env_name ?? null,
    secret_file_env_names: result?.secret_file_env_names ?? []
  };
}

export function voiceSetupReadinessProofStatus(status?: string | null) {
  if (status === "ready" || status === "degraded") {
    return "ready";
  }
  if (status === "blocked" || status === "failed") {
    return status;
  }
  return "pending";
}

export function voiceSetupProofStepPayload(
  step: VoiceSetupStep
): VoiceSetupProofStepPayload {
  return {
    id: step.id,
    label: step.label,
    status: step.status,
    detail: step.detail,
    next_action: step.nextAction ?? null,
    required: step.required
  };
}
