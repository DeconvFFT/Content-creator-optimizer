"use client";

import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ClipboardCheck, Gauge, KeyRound, Mic, MicOff, PhoneCall, PhoneOff, Radio, RotateCw, Scissors, Send, ShieldCheck, Volume2 } from "lucide-react";
import clsx from "clsx";
import {
  buildRealtimeVoiceTimingLedger,
  buildVoiceProviderSmoke,
  configureLocalLiveKitDevConfig,
  controlRealtimeSession,
  endRealtimeSession,
  getLocalLiveKitProcessStatus,
  getProviderReadiness,
  getVoiceAgentPresence,
  getVoiceAgentProcessStatus,
  getVoiceRuntimeReadiness,
  recordVoiceSetupProof,
  recordRealtimeVoiceEvent,
  saveLocalProviderConfig,
  saveLocalSecretFile,
  sendRealtimeTurn,
  startLocalLiveKitProcess,
  startVoiceAgentProcess,
  startRealtimeSession,
  stopLocalLiveKitProcess,
  stopVoiceAgentProcess
} from "@/lib/api/client";
import type {
  ArtifactRecord,
  LocalProviderConfigEnvName,
  LocalSecretFileEnvName,
  ProviderReadinessResult,
  ProviderSmokeRunResult,
  RealtimeSessionCreateResult,
  RealtimeVoiceAgentEventRecordResult,
  RealtimeVoiceTimingLedgerResult,
  LocalLiveKitDevConfigResult,
  LocalLiveKitProcessMode,
  LocalLiveKitProcessStatusResult,
  UUID,
  VoiceAgentPresenceResult,
  VoiceAgentProcessStatusResult,
  VoiceRuntimeReadinessCheck,
  VoiceRuntimeReadinessResult
} from "@/lib/api/types";
import { joinLiveKitRuntime } from "@/lib/voice/livekitRuntime";
import type { LiveKitRuntime } from "@/lib/voice/livekitRuntime";
import {
  buildVoiceAudioFixtureProof,
  buildVoiceStreamingProviderProof,
  findGemmaKokoroStreamingSmokeStep
} from "@/lib/voice/providerSmoke";
import { buildLiveVoiceProofPath } from "@/lib/voice/liveVoiceProofPath";
import {
  buildVoiceProviderReleaseGate,
  providerSmokeArtifactFromResult
} from "@/lib/voice/providerReadiness";
import { buildTranscriptRehearsalTurnInput } from "@/lib/voice/rehearsal";
import { buildVoiceTimingGap, buildVoiceTimingStageProofs, buildVoiceTimingTurnProof } from "@/lib/voice/timingLedger";
import { probeAndWaitForVoiceAgentPresence } from "@/lib/voice/presence";
import {
  shouldProbeVoiceAgentPresence,
  voicePresenceMonitorTone,
  VOICE_AGENT_PRESENCE_MONITOR_INTERVAL_MS
} from "@/lib/voice/presenceMonitor";
import {
  LIVE_VOICE_STAGES,
  stageFromRuntimeEvent,
  stageFromVoiceAgentEvent,
  stageFromVoiceStatus
} from "@/lib/voice/liveStage";
import type { LiveVoiceStageId } from "@/lib/voice/liveStage";
import {
  EMPTY_LIVE_VOICE_TRANSCRIPT,
  liveVoiceTranscriptFromAgentEvent
} from "@/lib/voice/liveTranscript";
import { voiceFollowupContinuationForEvent } from "@/lib/voice/followup";
import {
  cancellationProofFromVoiceAgentEvent,
  failedCancellationProofFromControlError,
  IDLE_CANCELLATION_PROOF,
  requestedCancellationProof
} from "@/lib/voice/cancellation";
import { buildRealtimeAgentControlMetadata } from "@/lib/voice/controlMetadata";
import {
  isMicrophoneControlCurrent,
  microphoneControlLabel,
  microphoneStatusLabel,
  nextMicrophonePublishingState
} from "@/lib/voice/microphone";
import {
  isLiveTextTurnCurrent,
  liveTextTurnStatusLabel
} from "@/lib/voice/liveTextTurn";
import {
  localLiveKitProcessStartBlocker,
  shouldAutoStartLocalLiveKitProcess,
  shouldAutoStartVoiceAgentProcess,
  voiceAgentProcessStartBlocker
} from "@/lib/voice/process";
import {
  LIVEKIT_TRANSPORT_PREFLIGHT_OPTIONS,
  RUNTIME_PREFLIGHT_READINESS_OPTIONS,
  shouldApplyVoiceReadinessResult,
  voiceReadinessRefreshStrength,
  type VoiceReadinessRefreshOptions
} from "@/lib/voice/runtimeReadiness";
import { startKeyedSingleFlight } from "@/lib/voice/keyedSingleFlight";
import { settleVoiceSetupFanout } from "@/lib/voice/setupFanout";
import {
  buildVoiceSetupChecklist,
  isVoiceSetupActionDisabled,
  localLiveKitDevSetupProofMetadata,
  voiceSetupActionForStep,
  voiceSetupActionLabel,
  voiceSetupPrimaryBlocker,
  voiceSetupProofStepPayload,
  voiceSetupReadinessProofStatus
} from "@/lib/voice/setup";
import { isRunBoundRequestCurrent } from "@/lib/state/runOwnership";

type VoiceProvider = "openrouter_livekit" | "local_rehearsal";
type VoiceStatus = "idle" | "starting" | "joining" | "ready" | "blocked" | "stopping" | "stopped" | "error";

type VoiceEvent = {
  id: string;
  label: string;
  detail?: string;
  tone?: "info" | "good" | "warn" | "bad";
};

type LocalLiveKitDevConfigAttempt =
  | { status: "ready"; result: LocalLiveKitDevConfigResult }
  | { status: "failed" }
  | { status: "skipped" };

function canSaveLocalSecret(envName: string): envName is LocalSecretFileEnvName {
  return (
    envName === "HF_TOKEN" ||
    envName === "LIVEKIT_API_KEY" ||
    envName === "LIVEKIT_API_SECRET" ||
    envName === "TAVILY_API_KEY"
  );
}

function secretFileNeedsLocalValue(status: string) {
  return ["missing", "empty", "unreadable"].includes(status);
}

function canSaveLocalProviderConfig(envName: string): envName is LocalProviderConfigEnvName {
  return (
    envName === "GEMMA4_MULTIMODAL_ENDPOINT_URL" ||
    envName === "OPENROUTER_LIVEKIT_URL" ||
    envName === "GEMMA4_REALTIME_LIVEKIT_URL" ||
    envName === "KOKORO_TTS_ENDPOINT_URL"
  );
}

function isLocalLiveKitDevEnv(envName: string) {
  return (
    envName === "OPENROUTER_LIVEKIT_URL" ||
    envName === "GEMMA4_REALTIME_LIVEKIT_URL" ||
    envName === "LIVEKIT_API_KEY" ||
    envName === "LIVEKIT_API_SECRET"
  );
}

function providerConfigPlaceholder(envName: LocalProviderConfigEnvName) {
  if (envName === "OPENROUTER_LIVEKIT_URL" || envName === "GEMMA4_REALTIME_LIVEKIT_URL") {
    return "ws://127.0.0.1:7880";
  }
  if (envName === "KOKORO_TTS_ENDPOINT_URL") {
    return "https://hf.example/kokoro";
  }
  return "https://hf.example/gemma-e4b";
}

function providerConfigAction(envName: LocalProviderConfigEnvName) {
  if (envName === "OPENROUTER_LIVEKIT_URL") {
    return "Save the OpenRouter-backed LiveKit URL to LOCAL_PROVIDER_CONFIG_FILE.";
  }
  if (envName === "GEMMA4_REALTIME_LIVEKIT_URL") {
    return "Save the LiveKit URL to LOCAL_PROVIDER_CONFIG_FILE.";
  }
  if (envName === "KOKORO_TTS_ENDPOINT_URL") {
    return "Save the hosted Kokoro TTS endpoint to LOCAL_PROVIDER_CONFIG_FILE.";
  }
  return "Save the legacy native-audio endpoint to LOCAL_PROVIDER_CONFIG_FILE.";
}

type VoiceSmokeOutcome =
  | {
      status: "built";
      result: ProviderSmokeRunResult;
      presence?: VoiceAgentPresenceResult | null;
    }
  | {
      status: "cancelled" | "failed" | "stale";
      message?: string;
    };

const PROVIDERS: Array<{
  id: VoiceProvider;
  label: string;
  capability: string;
}> = [
  {
    id: "openrouter_livekit",
    label: "OpenRouter DeepSeek + Kokoro",
    capability: "OpenRouter DeepSeek text reasoning with Kokoro-82M speech output over LiveKit"
  },
  {
    id: "local_rehearsal",
    label: "Transcript rehearsal",
    capability: "No live audio model; use the dictation transcript composer"
  }
];

function statusClass(status?: string | null) {
  if (!status) {
    return "status-unknown";
  }
  if (["ready", "passed", "running", "loaded", "direct_env"].includes(status)) {
    return "status-ready";
  }
  if (["blocked", "failed"].includes(status)) {
    return "status-blocked";
  }
  if ([
    "degraded",
    "missing",
    "needs_review",
    "needs_live_smoke",
    "needs_runtime",
    "needs_captured_audio",
    "needs_timing",
    "partial",
    "not_run",
    "not_applicable",
    "pending",
    "starting",
    "stopped",
    "exited",
    "disabled",
    "stale",
    "tool_boundary",
    "empty",
    "not_configured",
    "unreadable"
  ].includes(status)) {
    return "status-degraded";
  }
  return "status-unknown";
}

function readinessEvidence(check: VoiceRuntimeReadinessCheck) {
  return check.evidence[0] ?? "";
}

function readinessMissingEnv(check: VoiceRuntimeReadinessCheck) {
  if (check.missing_env.length === 0) {
    return "";
  }
  return `Missing: ${check.missing_env.join(", ")}`;
}

function readinessNextAction(check: VoiceRuntimeReadinessCheck) {
  return check.next_actions[0] ?? "";
}

function voiceSetupProofStatus(blocker: { status: string } | null) {
  if (!blocker) {
    return "ready";
  }
  return blocker.status === "blocked" ? "blocked" : "pending";
}

function voiceSetupProofTone(status: string): VoiceEvent["tone"] {
  if (status === "ready") {
    return "good";
  }
  if (status === "blocked" || status === "failed") {
    return "bad";
  }
  if (status === "pending") {
    return "warn";
  }
  return "info";
}

function metadataNumber(metadata: Record<string, unknown>, key: string): number | null {
  const value = metadata[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

type RealtimeVoicePanelProps = {
  runId?: UUID;
  busy: boolean;
  artifacts?: ArtifactRecord[];
  onCreateVoiceRun?: (
    goal: string,
    options: {
      provider: VoiceProvider;
    }
  ) => Promise<void>;
  onVoiceRunMutationStart?: (label: string) => VoiceRunMutationSnapshot | undefined;
  onVoiceRunMutationFinish?: (snapshot: VoiceRunMutationSnapshot) => void;
  onVoiceProofMutationStart?: (label: string) => VoiceRunMutationSnapshot | undefined;
  onVoiceProofMutationFinish?: (snapshot: VoiceRunMutationSnapshot) => void;
  onSessionReady: (session: RealtimeSessionCreateResult, sessionKey: string) => void;
  onRunUpdated: (summary?: string) => Promise<void>;
  onVoiceFollowupReady?: (
    followupTaskMessageId: UUID,
    options?: {
      agentIds?: string[];
      useGemma?: boolean | null;
    }
  ) => Promise<void>;
};

type VoiceRunMutationSnapshot = {
  runId: UUID;
  version: number;
  token: number;
};

type ProviderReadinessRefreshOptions = {
  shouldApply?: () => boolean;
};

export function RealtimeVoicePanel({
  runId,
  busy,
  artifacts = [],
  onCreateVoiceRun,
  onVoiceRunMutationStart,
  onVoiceRunMutationFinish,
  onVoiceProofMutationStart,
  onVoiceProofMutationFinish,
  onSessionReady,
  onRunUpdated,
  onVoiceFollowupReady
}: RealtimeVoicePanelProps) {
  const [provider, setProvider] = useState<VoiceProvider>("openrouter_livekit");
  const [voice, setVoice] = useState("af_heart");
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [error, setError] = useState("");
  const [events, setEvents] = useState<VoiceEvent[]>([]);
  const [liveSession, setLiveSession] = useState<RealtimeSessionCreateResult | null>(null);
  const [liveRuntime, setLiveRuntime] = useState<LiveKitRuntime | null>(null);
  const [readiness, setReadiness] = useState<VoiceRuntimeReadinessResult | null>(null);
  const [providerReadiness, setProviderReadiness] = useState<ProviderReadinessResult | null>(null);
  const [voicePresence, setVoicePresence] = useState<VoiceAgentPresenceResult | null>(null);
  const [voiceProcess, setVoiceProcess] = useState<VoiceAgentProcessStatusResult | null>(null);
  const [liveKitProcess, setLiveKitProcess] = useState<LocalLiveKitProcessStatusResult | null>(null);
  const [liveKitMode, setLiveKitMode] = useState<LocalLiveKitProcessMode>("native");
  const [readinessLoading, setReadinessLoading] = useState(false);
  const [providerReadinessLoading, setProviderReadinessLoading] = useState(false);
  const [secretValues, setSecretValues] = useState<Record<string, string>>({});
  const [secretSaving, setSecretSaving] = useState<LocalSecretFileEnvName | null>(null);
  const [providerConfigValues, setProviderConfigValues] = useState<Record<string, string>>({});
  const [providerConfigSaving, setProviderConfigSaving] = useState<LocalProviderConfigEnvName | null>(null);
  const [localLiveKitDevConfigSaving, setLocalLiveKitDevConfigSaving] = useState(false);
  const [processLoading, setProcessLoading] = useState<"start" | "stop" | "status" | null>(null);
  const [liveKitProcessLoading, setLiveKitProcessLoading] = useState<"start" | "stop" | "status" | null>(null);
  const [voiceSmoke, setVoiceSmoke] = useState<ProviderSmokeRunResult | null>(null);
  const [voiceTiming, setVoiceTiming] = useState<RealtimeVoiceTimingLedgerResult | null>(null);
  const [voiceProofLoading, setVoiceProofLoading] = useState<"smoke" | "timing" | null>(null);
  const [liveSmoke, setLiveSmoke] = useState(false);
  const [voiceStage, setVoiceStage] = useState<LiveVoiceStageId>("disconnected");
  const [liveTranscript, setLiveTranscript] = useState(EMPTY_LIVE_VOICE_TRANSCRIPT);
  const [liveTextTurn, setLiveTextTurn] = useState("");
  const [liveTextTurnLoading, setLiveTextTurnLoading] = useState(false);
  const [microphonePublished, setMicrophonePublished] = useState(false);
  const [microphoneControlLoading, setMicrophoneControlLoading] = useState(false);
  const [interruptControlLoading, setInterruptControlLoading] = useState(false);
  const [cancellationProof, setCancellationProof] = useState(IDLE_CANCELLATION_PROOF);
  const [rehearsalTranscript, setRehearsalTranscript] = useState(
    "Create a source-backed ELI5 reel and Substack angle from this spoken idea."
  );
  const [voiceRunGoal, setVoiceRunGoal] = useState(
    "Create source-backed social content from my live voice session."
  );
  const [voiceRunCreating, setVoiceRunCreating] = useState(false);
  const [rehearsalLoading, setRehearsalLoading] = useState(false);
  const [setupCheckLoading, setSetupCheckLoading] = useState(false);
  const [voiceSetupActionLoading, setVoiceSetupActionLoading] = useState(false);
  const [liveVoiceProofPathActionLoading, setLiveVoiceProofPathActionLoading] = useState(false);
  const remoteAudioRootRef = useRef<HTMLDivElement | null>(null);
  const componentMountedRef = useRef(true);
  const voiceRunCreatingRef = useRef(false);
  const currentRunIdRef = useRef<UUID | undefined>(runId);
  const activeRealtimeSessionIdRef = useRef<UUID | null>(null);
  const startSequenceRef = useRef(0);
  const startActionInFlightRef = useRef<{ runId: UUID; token: number } | null>(null);
  const voiceSmokeSequenceRef = useRef(0);
  const voiceTimingSequenceRef = useRef(0);
  const presenceMonitorSequenceRef = useRef(0);
  const microphoneControlSequenceRef = useRef(0);
  const interruptControlSequenceRef = useRef(0);
  const interruptControlInFlightRef = useRef(false);
  const stopActionSequenceRef = useRef(0);
  const stopActionInFlightRef = useRef<number | null>(null);
  const liveTextTurnSequenceRef = useRef(0);
  const liveTextTurnInFlightRef = useRef(false);
  const rehearsalTurnSequenceRef = useRef(0);
  const setupCheckSequenceRef = useRef(0);
  const voiceSetupActionSequenceRef = useRef(0);
  const voiceSetupActionInFlightRef = useRef<number | null>(null);
  const providerReadinessActionSequenceRef = useRef(0);
  const providerReadinessActionInFlightRef = useRef<number | null>(null);
  const runtimePreflightActionSequenceRef = useRef(0);
  const runtimePreflightActionInFlightRef = useRef<number | null>(null);
  const voiceProcessActionSequenceRef = useRef(0);
  const voiceProcessActionInFlightRef = useRef<number | null>(null);
  const liveKitProcessActionSequenceRef = useRef(0);
  const liveKitProcessActionInFlightRef = useRef<number | null>(null);
  const secretFileSaveSequenceRef = useRef(0);
  const secretFileSaveInFlightRef = useRef<number | null>(null);
  const providerConfigSaveSequenceRef = useRef(0);
  const providerConfigSaveInFlightRef = useRef<number | null>(null);
  const localLiveKitDevConfigSequenceRef = useRef(0);
  const localLiveKitDevConfigInFlightRef = useRef<number | null>(null);
  const liveVoiceProofActionSequenceRef = useRef(0);
  const liveVoiceProofPathActionInFlightRef = useRef<number | null>(null);
  const rehearsalTurnInFlightRef = useRef(false);
  const setupCheckInFlightRef = useRef(false);
  const voiceProofActionInFlightRef = useRef<{
    kind: "smoke" | "timing";
    runId: UUID;
    token: number;
  } | null>(null);
  const readinessRefreshInFlightRef = useRef<Map<string, Promise<VoiceRuntimeReadinessResult>>>(
    new Map()
  );
  const readinessRefreshCountRef = useRef(0);
  const readinessEpochRef = useRef(0);
  const readinessAppliedStateRef = useRef({ epoch: 0, strength: 0 });
  const invalidateRehearsalTurn = useCallback((options: { clearLoading?: boolean } = {}) => {
    rehearsalTurnSequenceRef.current += 1;
    rehearsalTurnInFlightRef.current = false;
    if (options.clearLoading && componentMountedRef.current) {
      setRehearsalLoading(false);
    }
  }, []);

  const providerCapability = PROVIDERS.find((item) => item.id === provider)?.capability ?? "";
  const runtimeBlocked = provider === "openrouter_livekit" && readiness?.status === "blocked";
  const canStart =
    Boolean(runId) &&
    !busy &&
    !runtimeBlocked &&
    processLoading === null &&
    !liveSession &&
    !["starting", "joining", "ready"].includes(status);
  const canCreateVoiceRun =
    !runId &&
    Boolean(onCreateVoiceRun) &&
    !busy &&
    !voiceRunCreating;
  const isReady = status === "ready";
  const isRehearsalSession = liveSession?.provider === "local_realtime_rehearsal";
  const canRouteRehearsalTurn = Boolean(
    liveSession &&
      runId &&
      isRehearsalSession &&
      status === "ready" &&
      activeRealtimeSessionIdRef.current === liveSession.realtime_session_id
  );

  const bumpReadinessEpoch = useCallback(() => {
    const nextEpoch = readinessEpochRef.current + 1;
    readinessEpochRef.current = nextEpoch;
    readinessAppliedStateRef.current = { epoch: nextEpoch, strength: 0 };
  }, []);

  useEffect(() => {
    bumpReadinessEpoch();
  }, [bumpReadinessEpoch, provider, runId]);
  const metadata = liveSession?.metadata ?? {};
  const contextWindowTurns = metadataNumber(metadata, "context_window_turns");
  const summarizeAfterTurns = metadataNumber(metadata, "summarize_after_turns");
  const transport = liveSession?.transport ?? null;
  const transportFramework =
    transport?.framework ?? (typeof metadata.transport_framework === "string" ? metadata.transport_framework : "livekit");
  const livekitUrl = transport?.url ?? (typeof metadata.livekit_url === "string" ? metadata.livekit_url : "");
  const roomName = transport?.room_name ?? liveRuntime?.roomName ?? "";
  const participantIdentity = transport?.participant_identity ?? liveRuntime?.participantIdentity ?? "";
  const hasTransportToken = transport?.has_token ?? Boolean(transport?.token);
  const edgeReadiness = readiness?.checks.find((check) => check.check_id === "rust-voice-edge");
  const visibleReadinessChecks = readiness?.checks ?? [];
  const realtimeSmokeStep = voiceSmoke?.steps.find((step) => step.step_id === "selected-realtime-smoke");
  const streamingSmokeStep = findGemmaKokoroStreamingSmokeStep(voiceSmoke);
  const audioFixtureProof = buildVoiceAudioFixtureProof(streamingSmokeStep);
  const streamingProviderProof = buildVoiceStreamingProviderProof(streamingSmokeStep);
  const activeProviderRealtimeSessionId =
    provider === "openrouter_livekit" &&
    status === "ready" &&
    liveSession !== null &&
    liveRuntime !== null &&
    !isRehearsalSession
      ? liveSession.realtime_session_id
      : null;
  const providerReleaseGate = buildVoiceProviderReleaseGate({
    providerReadiness,
    runtimeReadiness: readiness,
    smoke: voiceSmoke,
    presence: voicePresence,
    activeRealtimeSessionId: activeProviderRealtimeSessionId,
    artifacts
  });
  const localProviderConfigNames = [
    ...new Set(
      [
        ...providerReleaseGate.missingEnv,
        ...visibleReadinessChecks.flatMap((check) => check.missing_env)
      ].filter(canSaveLocalProviderConfig)
    )
  ];
  const localLiveKitDevConfigNeeded =
    provider === "openrouter_livekit" &&
    providerReleaseGate.missingEnv.length > 0 &&
    ["OPENROUTER_LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"].every(
      (envName) => isLocalLiveKitDevEnv(envName) && providerReleaseGate.missingEnv.includes(envName)
    );
  const localLiveKitDevConfigBusy =
    localLiveKitDevConfigSaving ||
    secretSaving !== null ||
    providerConfigSaving !== null;
  const timingStageProofs = buildVoiceTimingStageProofs(voiceTiming);
  const timingTurnProof = buildVoiceTimingTurnProof(voiceTiming);
  const liveVoiceProofPath = buildLiveVoiceProofPath({
    providerReleaseGate,
    audioFixtureProof,
    streamingProviderProof,
    timing: voiceTiming
  });
  const smokeBlocker =
    streamingSmokeStep?.blockers[0] ??
    realtimeSmokeStep?.blockers[0] ??
    voiceSmoke?.steps.find((step) => step.blockers.length > 0)?.blockers[0];
  const timingGap = buildVoiceTimingGap(voiceTiming);
  const voiceStageDefinition = LIVE_VOICE_STAGES[voiceStage];
  const presenceDetail =
    voicePresence?.evidence[0] ??
    voicePresence?.missing_evidence[0] ??
    "No durable agent participant proof yet.";
  const liveRoomConnected = Boolean(liveRuntime && status === "ready" && !isRehearsalSession);
  const liveTextTurnAgentReady = liveRoomConnected && voicePresence?.status === "ready";
  const canSendLiveTextTurn =
    liveTextTurnAgentReady &&
    liveTextTurn.trim().length > 0 &&
    !liveTextTurnLoading &&
    !liveTextTurnInFlightRef.current;
  const contextPolicyLabel =
    contextWindowTurns !== null && summarizeAfterTurns !== null && !isRehearsalSession
      ? `${contextWindowTurns} turns; prune after ${summarizeAfterTurns}`
      : "No provider-backed raw-audio window";
  const processRunning = voiceProcess?.running ?? false;
  const liveKitProcessRunning = liveKitProcess?.running ?? false;
  const processDetail =
    voiceProcess?.last_error
      ? `${voiceProcess.summary} Last error: ${voiceProcess.last_error}`
      : voiceProcess?.summary ??
    "Local voice-agent process status has not been checked yet.";
  const liveKitProcessDetail =
    liveKitProcess?.last_error
      ? `${liveKitProcess.summary} Last error: ${liveKitProcess.last_error}`
      : liveKitProcess?.summary ??
    "Local LiveKit dev-server status has not been checked yet.";
  const voiceSetupSteps = buildVoiceSetupChecklist({
    runId,
    provider,
    readiness,
    voiceProcess,
    liveKitProcess,
    liveSession,
    liveRoomConnected,
    voicePresence,
    isRehearsalSession,
    providerReleaseGate
  });
  const voiceSetupBlocker = voiceSetupPrimaryBlocker(voiceSetupSteps);
  const voiceSetupAction = voiceSetupActionForStep(voiceSetupBlocker);
  const voiceSetupActionDisabled = setupCheckLoading || voiceSetupActionLoading || isVoiceSetupActionDisabled({
    action: voiceSetupAction,
    readinessLoading,
    providerReadinessLoading,
    processLoading: processLoading !== null,
    liveKitProcessLoading: liveKitProcessLoading !== null,
    status,
    localLiveKitDevConfigBusy
  });
  const liveVoiceProofPathActionDisabled =
    liveVoiceProofPathActionLoading ||
    !runId ||
    !liveVoiceProofPath.primaryAction ||
    readinessLoading ||
    providerReadinessLoading ||
    voiceProofLoading !== null ||
    ["starting", "joining", "stopping"].includes(status);

  const addEvent = useCallback((event: Omit<VoiceEvent, "id">) => {
    setEvents((current) => [
      {
        id:
          typeof crypto !== "undefined" && "randomUUID" in crypto
            ? crypto.randomUUID()
            : `${Date.now()}-${Math.random()}`,
        ...event
      },
      ...current
    ].slice(0, 8));
  }, []);

  async function persistVoiceSetupProof(input: {
    action: string;
    status: string;
    summary: string;
    steps?: typeof voiceSetupSteps;
    blocker?: typeof voiceSetupBlocker;
    metadata?: Record<string, unknown>;
    readinessStatus?: string | null;
    liveKitStatus?: string | null;
    processStatus?: string | null;
    realtimeSessionId?: UUID | null;
  }) {
    const proofRunId = runId;
    if (!proofRunId) {
      return null;
    }
    const result = await recordVoiceSetupProof({
      runId: proofRunId,
      action: input.action,
      status: input.status,
      provider,
      realtimeSessionId:
        input.realtimeSessionId ??
        liveSession?.realtime_session_id ??
        activeRealtimeSessionIdRef.current,
      transportFramework,
      readinessStatus: input.readinessStatus ?? readiness?.status ?? null,
      liveKitProcessStatus: input.liveKitStatus ?? liveKitProcess?.status ?? null,
      voiceAgentProcessStatus: input.processStatus ?? voiceProcess?.status ?? null,
      primaryBlocker: input.blocker ? voiceSetupProofStepPayload(input.blocker) : null,
      steps: (input.steps ?? voiceSetupSteps).map(voiceSetupProofStepPayload),
      eventSummary: input.summary,
      metadata: {
        source: "creator_voice_panel",
        voice_status: status,
        live_room_connected: liveRoomConnected,
        agent_presence_status: voicePresence?.status ?? null,
        ...input.metadata
      },
      recordArtifact: true
    });
    if (currentRunIdRef.current !== proofRunId) {
      return result;
    }
    addEvent({
      label: "Voice setup proof recorded",
      detail: result.summary,
      tone: voiceSetupProofTone(input.status)
    });
    await onRunUpdated("Recorded voice setup proof.");
    return result;
  }

  const handleRuntimeEvent = useCallback(
    (event: Omit<VoiceEvent, "id">) => {
      addEvent(event);
      setVoiceStage((current) => stageFromRuntimeEvent(current, event));
      if (event.label === "Microphone publishing enabled") {
        setMicrophonePublished(true);
      }
      if (event.label === "Microphone publishing disabled") {
        setMicrophonePublished(false);
      }
      if (event.label === "LiveKit disconnected") {
        setMicrophonePublished(false);
      }
    },
    [addEvent]
  );

  useEffect(() => {
    componentMountedRef.current = true;
    return () => {
      componentMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    currentRunIdRef.current = runId;
    activeRealtimeSessionIdRef.current = null;
    startActionInFlightRef.current = null;
    setVoiceStage("disconnected");
    setLiveTranscript(EMPTY_LIVE_VOICE_TRANSCRIPT);
    setLiveTextTurn("");
    setLiveTextTurnLoading(false);
    liveTextTurnInFlightRef.current = false;
    invalidateRehearsalTurn({ clearLoading: true });
    setMicrophonePublished(false);
    setMicrophoneControlLoading(false);
    setInterruptControlLoading(false);
    microphoneControlSequenceRef.current += 1;
    interruptControlSequenceRef.current += 1;
    interruptControlInFlightRef.current = false;
    stopActionSequenceRef.current += 1;
    stopActionInFlightRef.current = null;
    liveTextTurnSequenceRef.current += 1;
    setupCheckSequenceRef.current += 1;
    setupCheckInFlightRef.current = false;
    setSetupCheckLoading(false);
    voiceSetupActionSequenceRef.current += 1;
    voiceSetupActionInFlightRef.current = null;
    setVoiceSetupActionLoading(false);
    providerReadinessActionSequenceRef.current += 1;
    providerReadinessActionInFlightRef.current = null;
    runtimePreflightActionSequenceRef.current += 1;
    runtimePreflightActionInFlightRef.current = null;
    voiceProcessActionSequenceRef.current += 1;
    voiceProcessActionInFlightRef.current = null;
    liveKitProcessActionSequenceRef.current += 1;
    liveKitProcessActionInFlightRef.current = null;
    secretFileSaveSequenceRef.current += 1;
    secretFileSaveInFlightRef.current = null;
    setSecretSaving(null);
    providerConfigSaveSequenceRef.current += 1;
    providerConfigSaveInFlightRef.current = null;
    setProviderConfigSaving(null);
    localLiveKitDevConfigSequenceRef.current += 1;
    localLiveKitDevConfigInFlightRef.current = null;
    setLocalLiveKitDevConfigSaving(false);
    setProcessLoading(null);
    setLiveKitProcessLoading(null);
    liveVoiceProofActionSequenceRef.current += 1;
    liveVoiceProofPathActionInFlightRef.current = null;
    setLiveVoiceProofPathActionLoading(false);
    setProviderReadinessLoading(false);
    setCancellationProof(IDLE_CANCELLATION_PROOF);
    voiceSmokeSequenceRef.current += 1;
    voiceTimingSequenceRef.current += 1;
    voiceProofActionInFlightRef.current = null;
    presenceMonitorSequenceRef.current += 1;
    setVoiceSmoke(null);
    setVoiceTiming(null);
    setVoiceProofLoading(null);
    setSecretValues({});
    setProviderConfigValues({});
  }, [invalidateRehearsalTurn, runId]);

  useEffect(() => {
    return () => {
      startSequenceRef.current += 1;
      startActionInFlightRef.current = null;
      voiceSmokeSequenceRef.current += 1;
      voiceTimingSequenceRef.current += 1;
      voiceProofActionInFlightRef.current = null;
      presenceMonitorSequenceRef.current += 1;
      microphoneControlSequenceRef.current += 1;
      interruptControlSequenceRef.current += 1;
      interruptControlInFlightRef.current = false;
      stopActionSequenceRef.current += 1;
      stopActionInFlightRef.current = null;
      liveTextTurnSequenceRef.current += 1;
      liveTextTurnInFlightRef.current = false;
      invalidateRehearsalTurn();
      setupCheckSequenceRef.current += 1;
      voiceSetupActionSequenceRef.current += 1;
      setupCheckInFlightRef.current = false;
      voiceSetupActionInFlightRef.current = null;
      providerReadinessActionSequenceRef.current += 1;
      providerReadinessActionInFlightRef.current = null;
      runtimePreflightActionSequenceRef.current += 1;
      runtimePreflightActionInFlightRef.current = null;
      voiceProcessActionSequenceRef.current += 1;
      voiceProcessActionInFlightRef.current = null;
      liveKitProcessActionSequenceRef.current += 1;
      liveKitProcessActionInFlightRef.current = null;
      secretFileSaveSequenceRef.current += 1;
      secretFileSaveInFlightRef.current = null;
      providerConfigSaveSequenceRef.current += 1;
      providerConfigSaveInFlightRef.current = null;
      localLiveKitDevConfigSequenceRef.current += 1;
      localLiveKitDevConfigInFlightRef.current = null;
      liveVoiceProofActionSequenceRef.current += 1;
      liveVoiceProofPathActionInFlightRef.current = null;
    };
  }, [invalidateRehearsalTurn]);

  const refreshProviderReadiness = useCallback(async (options: ProviderReadinessRefreshOptions = {}) => {
    setProviderReadinessLoading(true);
    try {
      const result = await getProviderReadiness();
      const shouldApplyProviderReadiness = options.shouldApply?.() ?? true;
      if (!shouldApplyProviderReadiness) {
        return result;
      }
      setProviderReadiness(result);
      return result;
    } catch (providerError) {
      const shouldApplyProviderReadiness = options.shouldApply?.() ?? true;
      if (!shouldApplyProviderReadiness) {
        throw providerError;
      }
      const message =
        providerError instanceof Error ? providerError.message : "Could not load provider readiness.";
      addEvent({
        label: "Provider readiness check failed",
        detail: message,
        tone: "warn"
      });
      throw providerError;
    } finally {
      const shouldApplyProviderReadiness = options.shouldApply?.() ?? true;
      if (shouldApplyProviderReadiness) {
        setProviderReadinessLoading(false);
      }
    }
  }, [addEvent]);

  const handleSaveLocalSecretFile = useCallback(
    async (envName: string) => {
      if (secretFileSaveInFlightRef.current !== null) {
        return;
      }
      if (!canSaveLocalSecret(envName)) {
        addEvent({
          label: "Secret file save blocked",
          detail: "Only supported local provider secrets can be saved from the setup panel.",
          tone: "warn"
        });
        return;
      }
      const secretValue = (secretValues[envName] ?? "").trim();
      if (!secretValue) {
        addEvent({
          label: "Secret file save blocked",
          detail: `${envName} cannot be blank.`,
          tone: "warn"
        });
        return;
      }
      const secretFileSaveToken = secretFileSaveSequenceRef.current + 1;
      secretFileSaveSequenceRef.current = secretFileSaveToken;
      secretFileSaveInFlightRef.current = secretFileSaveToken;
      const secretFileSaveRunId = runId;
      const isCurrentSecretFileSave = () =>
        secretFileSaveSequenceRef.current === secretFileSaveToken &&
        currentRunIdRef.current === secretFileSaveRunId;
      let parentMutationSnapshot: VoiceRunMutationSnapshot | undefined;
      if (runId) {
        parentMutationSnapshot = onVoiceProofMutationStart?.("Saving local secret file");
        if (onVoiceProofMutationStart && !parentMutationSnapshot) {
          if (secretFileSaveInFlightRef.current === secretFileSaveToken) {
            secretFileSaveInFlightRef.current = null;
          }
          return;
        }
      }
      setSecretSaving(envName);
      try {
        let result: Awaited<ReturnType<typeof saveLocalSecretFile>>;
        try {
          result = await saveLocalSecretFile({ envName, secretValue });
        } catch (secretError) {
          if (isCurrentSecretFileSave()) {
            addEvent({
              label: "Secret file save failed",
              detail:
                secretError instanceof Error
                  ? secretError.message
                  : "Could not write the local secret file.",
              tone: "bad"
            });
          }
          return;
        }
        if (!isCurrentSecretFileSave()) {
          return;
        }
        setSecretValues((current) => ({ ...current, [envName]: "" }));
        addEvent({
          label: "Secret file saved",
          detail: `${result.file_env_name} is ready. Refreshing provider readiness.`,
          tone: "good"
        });
        try {
          await refreshProviderReadiness({ shouldApply: isCurrentSecretFileSave });
        } catch {
          return;
        }
      } finally {
        if (secretFileSaveInFlightRef.current === secretFileSaveToken) {
          secretFileSaveInFlightRef.current = null;
          setSecretSaving(null);
        }
        if (parentMutationSnapshot) {
          onVoiceProofMutationFinish?.(parentMutationSnapshot);
        }
      }
    },
    [
      addEvent,
      onVoiceProofMutationFinish,
      onVoiceProofMutationStart,
      refreshProviderReadiness,
      runId,
      secretValues
    ]
  );

  useEffect(() => {
    void refreshProviderReadiness().catch((providerError) => {
      setError(
        providerError instanceof Error ? providerError.message : "Could not load provider readiness."
      );
    });
  }, [refreshProviderReadiness]);

  const refreshVoiceReadiness = useCallback(
    async (options: VoiceReadinessRefreshOptions = {}) => {
      const preflightEdge = options.preflightEdge ?? false;
      const preflightAgent = options.preflightAgent ?? false;
      const preflightLivekit = options.preflightLivekit ?? false;
      const preflightTts = options.preflightTts ?? false;
      const preflightGemma = options.preflightGemma ?? false;
      const requestEpoch = readinessEpochRef.current;
      const requestKey = [
        requestEpoch,
        preflightEdge,
        preflightAgent,
        preflightLivekit,
        preflightTts,
        preflightGemma
      ].join("|");
      const requestStrength = voiceReadinessRefreshStrength({
        preflightEdge,
        preflightAgent,
        preflightLivekit,
        preflightTts,
        preflightGemma
      });
      const request = startKeyedSingleFlight(
        readinessRefreshInFlightRef.current,
        requestKey,
        async () => {
          readinessRefreshCountRef.current += 1;
          setReadinessLoading(true);
          try {
            const result = await getVoiceRuntimeReadiness({
              preflightEdge,
              preflightAgent,
              preflightLivekit,
              preflightGemma,
              preflightTts
            });
            const shouldApplyReadiness = options.shouldApply?.() ?? true;
            if (!shouldApplyReadiness) {
              return result;
            }
            const nextReadinessState = { epoch: requestEpoch, strength: requestStrength };
            if (shouldApplyVoiceReadinessResult(readinessAppliedStateRef.current, nextReadinessState)) {
              readinessAppliedStateRef.current = nextReadinessState;
              setReadiness(result);
            }
            if (preflightEdge) {
              addEvent({
                label: "Runtime preflight complete",
                detail: result.summary,
                tone: result.status === "ready" ? "good" : result.status === "blocked" ? "bad" : "warn"
              });
            }
            return result;
          } catch (readinessError) {
            const shouldApplyReadiness = options.shouldApply?.() ?? true;
            if (!shouldApplyReadiness) {
              throw readinessError;
            }
            const message =
              readinessError instanceof Error ? readinessError.message : "Could not load voice runtime readiness.";
            addEvent({
              label: "Voice readiness check failed",
              detail: message,
              tone: "bad"
            });
            throw readinessError;
          } finally {
            readinessRefreshCountRef.current = Math.max(0, readinessRefreshCountRef.current - 1);
            if (readinessRefreshCountRef.current === 0) {
              setReadinessLoading(false);
            }
          }
        }
      );
      return request.promise;
    },
    [addEvent]
  );

  async function handleRuntimePreflight() {
    if (runtimePreflightActionInFlightRef.current !== null) {
      return;
    }
    const runtimePreflightToken = runtimePreflightActionSequenceRef.current + 1;
    runtimePreflightActionSequenceRef.current = runtimePreflightToken;
    runtimePreflightActionInFlightRef.current = runtimePreflightToken;
    const runtimePreflightRunId = runId;
    const isCurrentRuntimePreflight = () =>
      runtimePreflightActionSequenceRef.current === runtimePreflightToken &&
      currentRunIdRef.current === runtimePreflightRunId;
    let parentMutationSnapshot: VoiceRunMutationSnapshot | undefined;
    if (runId) {
      parentMutationSnapshot = onVoiceProofMutationStart?.("Running runtime preflight");
      if (onVoiceProofMutationStart && !parentMutationSnapshot) {
        if (runtimePreflightActionInFlightRef.current === runtimePreflightToken) {
          runtimePreflightActionInFlightRef.current = null;
        }
        return;
      }
    }
    try {
      await refreshVoiceReadiness({
        ...RUNTIME_PREFLIGHT_READINESS_OPTIONS,
        shouldApply: isCurrentRuntimePreflight
      });
    } finally {
      if (runtimePreflightActionInFlightRef.current === runtimePreflightToken) {
        runtimePreflightActionInFlightRef.current = null;
      }
      if (parentMutationSnapshot) {
        onVoiceProofMutationFinish?.(parentMutationSnapshot);
      }
    }
  }

  const handleSaveLocalProviderConfig = useCallback(
    async (envName: string) => {
      if (providerConfigSaveInFlightRef.current !== null) {
        return;
      }
      if (!canSaveLocalProviderConfig(envName)) {
        addEvent({
          label: "Provider endpoint save blocked",
          detail: "Only supported local provider endpoints can be saved from the setup panel.",
          tone: "warn"
        });
        return;
      }
      const providerConfigValue = (providerConfigValues[envName] ?? "").trim();
      if (!providerConfigValue) {
        addEvent({
          label: "Provider endpoint save blocked",
          detail: `${envName} cannot be blank.`,
          tone: "warn"
        });
        return;
      }
      const providerConfigSaveToken = providerConfigSaveSequenceRef.current + 1;
      providerConfigSaveSequenceRef.current = providerConfigSaveToken;
      providerConfigSaveInFlightRef.current = providerConfigSaveToken;
      const providerConfigSaveRunId = runId;
      const isCurrentProviderConfigSave = () =>
        providerConfigSaveSequenceRef.current === providerConfigSaveToken &&
        currentRunIdRef.current === providerConfigSaveRunId;
      let parentMutationSnapshot: VoiceRunMutationSnapshot | undefined;
      if (runId) {
        parentMutationSnapshot = onVoiceProofMutationStart?.("Saving provider endpoint");
        if (onVoiceProofMutationStart && !parentMutationSnapshot) {
          if (providerConfigSaveInFlightRef.current === providerConfigSaveToken) {
            providerConfigSaveInFlightRef.current = null;
          }
          return;
        }
      }
      setProviderConfigSaving(envName);
      try {
        const result = await saveLocalProviderConfig({
          envName,
          configValue: providerConfigValue
        });
        if (!isCurrentProviderConfigSave()) {
          return;
        }
        setProviderConfigValues((current) => ({ ...current, [envName]: "" }));
        addEvent({
          label: "Provider endpoint saved",
          detail: `${result.env_name} is ready. Refreshing setup checks.`,
          tone: "good"
        });
        bumpReadinessEpoch();
        const refreshResults = await Promise.allSettled([
          refreshProviderReadiness({ shouldApply: isCurrentProviderConfigSave }),
          refreshVoiceReadiness({ shouldApply: isCurrentProviderConfigSave })
        ]);
        if (!isCurrentProviderConfigSave()) {
          return;
        }
        const failedRefresh = refreshResults.find((refresh) => refresh.status === "rejected");
        if (failedRefresh?.status === "rejected") {
          throw failedRefresh.reason;
        }
      } catch (configError) {
        if (isCurrentProviderConfigSave()) {
          addEvent({
            label: "Provider endpoint save failed",
            detail:
              configError instanceof Error
                ? configError.message
                : "Could not write local provider configuration.",
            tone: "bad"
          });
        }
      } finally {
        if (providerConfigSaveInFlightRef.current === providerConfigSaveToken) {
          providerConfigSaveInFlightRef.current = null;
          setProviderConfigSaving(null);
        }
        if (parentMutationSnapshot) {
          onVoiceProofMutationFinish?.(parentMutationSnapshot);
        }
      }
    },
    [
      addEvent,
      bumpReadinessEpoch,
      onVoiceProofMutationFinish,
      onVoiceProofMutationStart,
      providerConfigValues,
      refreshProviderReadiness,
      refreshVoiceReadiness,
      runId
    ]
  );

  const handleConfigureLocalLiveKitDev = useCallback(async (
    options: { skipParentMutation?: boolean } = {}
  ): Promise<LocalLiveKitDevConfigAttempt> => {
    if (localLiveKitDevConfigInFlightRef.current !== null) {
      return { status: "skipped" };
    }
    const localLiveKitDevConfigToken = localLiveKitDevConfigSequenceRef.current + 1;
    localLiveKitDevConfigSequenceRef.current = localLiveKitDevConfigToken;
    localLiveKitDevConfigInFlightRef.current = localLiveKitDevConfigToken;
    const localLiveKitDevConfigRunId = runId;
    const isCurrentLocalLiveKitDevConfig = () =>
      localLiveKitDevConfigSequenceRef.current === localLiveKitDevConfigToken &&
      currentRunIdRef.current === localLiveKitDevConfigRunId;
    let parentMutationSnapshot: VoiceRunMutationSnapshot | undefined;
    if (runId && !options.skipParentMutation) {
      parentMutationSnapshot = onVoiceProofMutationStart?.("Configuring local LiveKit dev defaults");
      if (onVoiceProofMutationStart && !parentMutationSnapshot) {
        if (localLiveKitDevConfigInFlightRef.current === localLiveKitDevConfigToken) {
          localLiveKitDevConfigInFlightRef.current = null;
        }
        return { status: "skipped" };
      }
    }
    setLocalLiveKitDevConfigSaving(true);
    try {
      const result = await configureLocalLiveKitDevConfig();
      if (!isCurrentLocalLiveKitDevConfig()) {
        return { status: "skipped" };
      }
      addEvent({
        label: "Local LiveKit dev setup saved",
        detail: `${result.configured_env.join(", ")} are ready. Refreshing setup checks.`,
        tone: "good"
      });
      bumpReadinessEpoch();
      const refreshResults = await Promise.allSettled([
        refreshProviderReadiness({ shouldApply: isCurrentLocalLiveKitDevConfig }),
        refreshVoiceReadiness({ shouldApply: isCurrentLocalLiveKitDevConfig })
      ]);
      if (!isCurrentLocalLiveKitDevConfig()) {
        return { status: "skipped" };
      }
      const failedRefresh = refreshResults.find((refresh) => refresh.status === "rejected");
      if (failedRefresh?.status === "rejected") {
        throw failedRefresh.reason;
      }
      return { status: "ready", result };
    } catch (configError) {
      if (isCurrentLocalLiveKitDevConfig()) {
        addEvent({
          label: "Local LiveKit dev setup failed",
          detail:
            configError instanceof Error
              ? configError.message
              : "Could not configure local LiveKit dev defaults.",
            tone: "bad"
        });
        return { status: "failed" };
      }
      return { status: "skipped" };
    } finally {
      if (localLiveKitDevConfigInFlightRef.current === localLiveKitDevConfigToken) {
        localLiveKitDevConfigInFlightRef.current = null;
        setLocalLiveKitDevConfigSaving(false);
      }
      if (parentMutationSnapshot) {
        onVoiceProofMutationFinish?.(parentMutationSnapshot);
      }
    }
  }, [
    addEvent,
    bumpReadinessEpoch,
    onVoiceProofMutationFinish,
    onVoiceProofMutationStart,
    refreshProviderReadiness,
    refreshVoiceReadiness,
    runId
  ]);

  useEffect(() => {
    void refreshVoiceReadiness().catch((readinessError) => {
      setError(
        readinessError instanceof Error ? readinessError.message : "Could not load voice runtime readiness."
      );
    });
  }, [refreshVoiceReadiness]);

  const refreshVoiceProcess = useCallback(async () => {
    setProcessLoading("status");
    try {
      const result = await getVoiceAgentProcessStatus();
      setVoiceProcess(result);
      return result;
    } finally {
      setProcessLoading(null);
    }
  }, []);

  const refreshLiveKitProcess = useCallback(async () => {
    setLiveKitProcessLoading("status");
    try {
      const result = await getLocalLiveKitProcessStatus();
      setLiveKitProcess(result);
      setLiveKitMode(result.mode === "compose" ? "compose" : "native");
      return result;
    } finally {
      setLiveKitProcessLoading(null);
    }
  }, []);

  useEffect(() => {
    void refreshVoiceProcess().catch((processError) => {
      addEvent({
        label: "Voice-agent process status failed",
        detail: processError instanceof Error ? processError.message : "Could not load voice-agent process status.",
        tone: "warn"
      });
    });
    void refreshLiveKitProcess().catch((processError) => {
      addEvent({
        label: "LiveKit process status failed",
        detail: processError instanceof Error ? processError.message : "Could not load local LiveKit process status.",
        tone: "warn"
      });
    });
  }, [addEvent, refreshLiveKitProcess, refreshVoiceProcess]);

  useEffect(() => {
    return () => {
      void liveRuntime?.disconnect().catch((disconnectError) => {
        addEvent({
          label: "LiveKit cleanup failed",
          detail: disconnectError instanceof Error ? disconnectError.message : "Unknown cleanup error",
          tone: "warn"
        });
      });
    };
  }, [addEvent, liveRuntime]);

  const refreshVoicePresence = useCallback(
    async (sessionId?: UUID | null, probeId?: string | null) => {
      if (!runId) {
        return null;
      }
      const result = await getVoiceAgentPresence({
        runId,
        realtimeSessionId: sessionId ?? activeRealtimeSessionIdRef.current,
        probeId: probeId ?? null,
        staleAfterSeconds: 60
      });
      if (currentRunIdRef.current !== runId) {
        return null;
      }
      if (sessionId && activeRealtimeSessionIdRef.current !== sessionId) {
        return null;
      }
      setVoicePresence(result);
      return result;
    },
    [runId]
  );

  useEffect(() => {
    if (!runId) {
      setVoicePresence(null);
      return;
    }
    void refreshVoicePresence(null).catch((presenceError) => {
      addEvent({
        label: "Voice-agent presence check failed",
        detail: presenceError instanceof Error ? presenceError.message : "Could not load voice-agent presence.",
        tone: "warn"
      });
    });
  }, [addEvent, refreshVoicePresence, runId]);

  useEffect(() => {
    const session = liveSession;
    const runtime = liveRuntime;
    if (!session || !runtime || status !== "ready" || isRehearsalSession) {
      return;
    }
    const monitorToken = presenceMonitorSequenceRef.current + 1;
    presenceMonitorSequenceRef.current = monitorToken;
    let stopped = false;
    const isCurrentMonitor = () =>
      !stopped &&
      presenceMonitorSequenceRef.current === monitorToken &&
      currentRunIdRef.current === session.run_id &&
      activeRealtimeSessionIdRef.current === session.realtime_session_id;

    const runPresenceCheck = async () => {
      if (!isCurrentMonitor()) {
        return;
      }
      let currentPresence: VoiceAgentPresenceResult | null = null;
      try {
        currentPresence = await refreshVoicePresence(session.realtime_session_id);
      } catch (presenceError) {
        if (isCurrentMonitor()) {
          addEvent({
            label: "Voice-agent liveness check failed",
            detail: presenceError instanceof Error ? presenceError.message : "Could not refresh voice-agent presence.",
            tone: "warn"
          });
        }
        return;
      }
      if (!isCurrentMonitor() || !shouldProbeVoiceAgentPresence(currentPresence)) {
        return;
      }
      let waitResult;
      try {
        waitResult = await probeAndWaitForVoiceAgentPresence({
          realtimeSessionId: session.realtime_session_id,
          probeAgentPresence: runtime.probeAgentPresence,
          refreshVoicePresence: async (sessionId, probeId) => {
            if (!isCurrentMonitor()) {
              return null;
            }
            const presence = await getVoiceAgentPresence({
              runId: session.run_id,
              realtimeSessionId: sessionId,
              probeId,
              staleAfterSeconds: 60
            });
            if (!isCurrentMonitor()) {
              return null;
            }
            setVoicePresence(presence);
            return presence;
          },
          maxAttempts: 3,
          intervalMs: 300,
          shouldContinue: isCurrentMonitor
        });
      } catch (probeError) {
        if (isCurrentMonitor()) {
          addEvent({
            label: "Voice-agent liveness probe failed",
            detail: probeError instanceof Error ? probeError.message : "Could not publish voice-agent liveness probe.",
            tone: "warn"
          });
        }
        return;
      }
      if (!isCurrentMonitor()) {
        return;
      }
      if (waitResult.presence) {
        setVoicePresence(waitResult.presence);
      }
      addEvent({
        label: waitResult.ready
          ? "Voice-agent liveness refreshed"
          : waitResult.cancelled
          ? "Voice-agent liveness check cancelled"
          : "Voice-agent liveness missing",
        detail: waitResult.summary,
        tone: voicePresenceMonitorTone(waitResult.ready, waitResult.cancelled)
      });
    };

    const intervalId = globalThis.setInterval(() => {
      void runPresenceCheck();
    }, VOICE_AGENT_PRESENCE_MONITOR_INTERVAL_MS);

    return () => {
      stopped = true;
      globalThis.clearInterval(intervalId);
      if (presenceMonitorSequenceRef.current === monitorToken) {
        presenceMonitorSequenceRef.current += 1;
      }
    };
  }, [addEvent, isRehearsalSession, liveRuntime, liveSession, refreshVoicePresence, status]);

  async function handleStartProcess(options: { skipParentMutation?: boolean } = {}) {
    if (voiceProcessActionInFlightRef.current !== null) {
      return;
    }
    const processActionToken = voiceProcessActionSequenceRef.current + 1;
    voiceProcessActionSequenceRef.current = processActionToken;
    voiceProcessActionInFlightRef.current = processActionToken;
    let parentMutationSnapshot: VoiceRunMutationSnapshot | undefined;
    if (runId && !options.skipParentMutation) {
      parentMutationSnapshot = onVoiceProofMutationStart?.("Starting voice agent");
      if (onVoiceProofMutationStart && !parentMutationSnapshot) {
        if (voiceProcessActionInFlightRef.current === processActionToken) {
          voiceProcessActionInFlightRef.current = null;
        }
        return;
      }
    }
    setProcessLoading("start");
    setError("");
    try {
      const result = await startVoiceAgentProcess();
      setVoiceProcess(result);
      addEvent({
        label: "Local voice-agent process start requested",
        detail: result.summary,
        tone: result.running ? "good" : result.status === "failed" ? "bad" : "warn"
      });
      bumpReadinessEpoch();
      await refreshVoiceReadiness().catch(() => undefined);
    } catch (processError) {
      const message = processError instanceof Error ? processError.message : "Could not start voice-agent process.";
      setError(message);
      addEvent({ label: "Voice-agent process start failed", detail: message, tone: "bad" });
    } finally {
      if (voiceProcessActionInFlightRef.current === processActionToken) {
        voiceProcessActionInFlightRef.current = null;
        setProcessLoading(null);
      }
      if (parentMutationSnapshot) {
        onVoiceProofMutationFinish?.(parentMutationSnapshot);
      }
    }
  }

  async function handleStopProcess() {
    if (voiceProcessActionInFlightRef.current !== null) {
      return;
    }
    const processActionToken = voiceProcessActionSequenceRef.current + 1;
    voiceProcessActionSequenceRef.current = processActionToken;
    voiceProcessActionInFlightRef.current = processActionToken;
    let parentMutationSnapshot: VoiceRunMutationSnapshot | undefined;
    if (runId) {
      parentMutationSnapshot = onVoiceProofMutationStart?.("Stopping voice agent");
      if (onVoiceProofMutationStart && !parentMutationSnapshot) {
        if (voiceProcessActionInFlightRef.current === processActionToken) {
          voiceProcessActionInFlightRef.current = null;
        }
        return;
      }
    }
    setProcessLoading("stop");
    setError("");
    try {
      const result = await stopVoiceAgentProcess();
      setVoiceProcess(result);
      addEvent({
        label: result.running
          ? "Local voice-agent process still running"
          : "Local voice-agent process stopped",
        detail: result.summary,
        tone: result.running ? "warn" : result.status === "failed" ? "bad" : "info"
      });
      await refreshVoicePresence(liveSession?.realtime_session_id ?? null).catch(() => undefined);
    } catch (processError) {
      const message = processError instanceof Error ? processError.message : "Could not stop voice-agent process.";
      setError(message);
      addEvent({ label: "Voice-agent process stop failed", detail: message, tone: "bad" });
    } finally {
      if (voiceProcessActionInFlightRef.current === processActionToken) {
        voiceProcessActionInFlightRef.current = null;
        setProcessLoading(null);
      }
      if (parentMutationSnapshot) {
        onVoiceProofMutationFinish?.(parentMutationSnapshot);
      }
    }
  }

  async function handleStartLiveKitProcess(options: { forceRestart?: boolean; skipParentMutation?: boolean } = {}) {
    if (liveKitProcessActionInFlightRef.current !== null) {
      return;
    }
    const liveKitActionToken = liveKitProcessActionSequenceRef.current + 1;
    liveKitProcessActionSequenceRef.current = liveKitActionToken;
    liveKitProcessActionInFlightRef.current = liveKitActionToken;
    let parentMutationSnapshot: VoiceRunMutationSnapshot | undefined;
    if (runId && !options.skipParentMutation) {
      parentMutationSnapshot = onVoiceProofMutationStart?.("Starting local LiveKit");
      if (onVoiceProofMutationStart && !parentMutationSnapshot) {
        if (liveKitProcessActionInFlightRef.current === liveKitActionToken) {
          liveKitProcessActionInFlightRef.current = null;
        }
        return;
      }
    }
    setLiveKitProcessLoading("start");
    setError("");
    try {
      const result = await startLocalLiveKitProcess({
        mode: liveKitMode,
        forceRestart: options.forceRestart ?? false
      });
      setLiveKitProcess(result);
      addEvent({
        label: "Local LiveKit dev server start requested",
        detail: result.summary,
        tone: result.running ? "good" : result.status === "failed" ? "bad" : "warn"
      });
      bumpReadinessEpoch();
      await refreshVoiceReadiness(LIVEKIT_TRANSPORT_PREFLIGHT_OPTIONS).catch(() => undefined);
    } catch (processError) {
      const message = processError instanceof Error ? processError.message : "Could not start local LiveKit.";
      setError(message);
      addEvent({ label: "Local LiveKit start failed", detail: message, tone: "bad" });
    } finally {
      if (liveKitProcessActionInFlightRef.current === liveKitActionToken) {
        liveKitProcessActionInFlightRef.current = null;
        setLiveKitProcessLoading(null);
      }
      if (parentMutationSnapshot) {
        onVoiceProofMutationFinish?.(parentMutationSnapshot);
      }
    }
  }

  async function handleStopLiveKitProcess() {
    if (liveKitProcessActionInFlightRef.current !== null) {
      return;
    }
    const liveKitActionToken = liveKitProcessActionSequenceRef.current + 1;
    liveKitProcessActionSequenceRef.current = liveKitActionToken;
    liveKitProcessActionInFlightRef.current = liveKitActionToken;
    let parentMutationSnapshot: VoiceRunMutationSnapshot | undefined;
    if (runId) {
      parentMutationSnapshot = onVoiceProofMutationStart?.("Stopping local LiveKit");
      if (onVoiceProofMutationStart && !parentMutationSnapshot) {
        if (liveKitProcessActionInFlightRef.current === liveKitActionToken) {
          liveKitProcessActionInFlightRef.current = null;
        }
        return;
      }
    }
    setLiveKitProcessLoading("stop");
    setError("");
    try {
      const result = await stopLocalLiveKitProcess();
      setLiveKitProcess(result);
      addEvent({
        label: result.running ? "Local LiveKit still running" : "Local LiveKit stopped",
        detail: result.summary,
        tone: result.running ? "warn" : result.status === "failed" ? "bad" : "info"
      });
      bumpReadinessEpoch();
      await refreshVoiceReadiness().catch(() => undefined);
    } catch (processError) {
      const message = processError instanceof Error ? processError.message : "Could not stop local LiveKit.";
      setError(message);
      addEvent({ label: "Local LiveKit stop failed", detail: message, tone: "bad" });
    } finally {
      if (liveKitProcessActionInFlightRef.current === liveKitActionToken) {
        liveKitProcessActionInFlightRef.current = null;
        setLiveKitProcessLoading(null);
      }
      if (parentMutationSnapshot) {
        onVoiceProofMutationFinish?.(parentMutationSnapshot);
      }
    }
  }

  async function handleSetupCheck() {
    if (setupCheckInFlightRef.current) {
      return;
    }
    const parentMutationSnapshot = onVoiceProofMutationStart?.("Checking voice setup");
    if (onVoiceProofMutationStart && !parentMutationSnapshot) {
      return;
    }
    const setupCheckRunId = runId;
    const setupCheckToken = setupCheckSequenceRef.current + 1;
    setupCheckSequenceRef.current = setupCheckToken;
    const isCurrentSetupCheck = () =>
      setupCheckSequenceRef.current === setupCheckToken &&
      currentRunIdRef.current === setupCheckRunId;
    setupCheckInFlightRef.current = true;
    setSetupCheckLoading(true);
    setError("");
    addEvent({
      label: "Voice setup check started",
      detail: "Refreshing LiveKit, OpenRouter/Kokoro agent, runtime readiness, and participant proof.",
      tone: "info"
    });
    try {
      const [liveKitStatus, processStatus, readinessResult, providerReadinessResult] = await settleVoiceSetupFanout([
        refreshLiveKitProcess(),
        refreshVoiceProcess(),
        refreshVoiceReadiness({
          ...RUNTIME_PREFLIGHT_READINESS_OPTIONS,
          shouldApply: isCurrentSetupCheck
        }),
        refreshProviderReadiness({ shouldApply: isCurrentSetupCheck })
      ]);
      const presence = await refreshVoicePresence(liveSession?.realtime_session_id ?? null)
        .catch(() => null);
      const checkedProviderReleaseGate = buildVoiceProviderReleaseGate({
        providerReadiness: providerReadinessResult,
        runtimeReadiness: readinessResult,
        smoke: voiceSmoke,
        presence: presence ?? voicePresence,
        activeRealtimeSessionId: activeProviderRealtimeSessionId,
        artifacts
      });
      const checkedSteps = buildVoiceSetupChecklist({
        runId,
        provider,
        readiness: readinessResult,
        voiceProcess: processStatus,
        liveKitProcess: liveKitStatus,
        liveSession,
        liveRoomConnected,
        voicePresence: presence ?? voicePresence,
        isRehearsalSession,
        providerReleaseGate: checkedProviderReleaseGate
      });
      const blocker = voiceSetupPrimaryBlocker(checkedSteps);
      if (!isCurrentSetupCheck()) {
        return;
      }
      addEvent({
        label: blocker ? "Voice setup needs attention" : "Voice setup ready",
        detail: blocker
          ? `${blocker.label}: ${blocker.detail}`
          : "All required launch checks are ready.",
        tone: blocker ? (blocker.status === "blocked" ? "bad" : "warn") : "good"
      });
      await persistVoiceSetupProof({
        action: "check_setup",
        status: voiceSetupProofStatus(blocker),
        summary: blocker
          ? `Voice setup check recorded: ${blocker.label} needs attention.`
          : "Voice setup check recorded: all required launch checks are ready.",
        steps: checkedSteps,
        blocker,
        readinessStatus: readinessResult.status,
        liveKitStatus: liveKitStatus.status,
        processStatus: processStatus.status,
        realtimeSessionId: liveSession?.realtime_session_id ?? null,
        metadata: {
          action_source: "check_setup",
          blocker_label: blocker?.label ?? null,
          blocker_status: blocker?.status ?? null,
          presence_status: (presence ?? voicePresence)?.status ?? null
        }
      }).catch((proofError) => {
        if (!isCurrentSetupCheck()) {
          return;
        }
        addEvent({
          label: "Voice setup proof failed",
          detail:
            proofError instanceof Error
              ? proofError.message
              : "Could not record durable voice setup proof.",
          tone: "warn"
        });
      });
    } catch (setupError) {
      if (!isCurrentSetupCheck()) {
        return;
      }
      const message = setupError instanceof Error ? setupError.message : "Could not check voice setup.";
      setError(message);
      addEvent({ label: "Voice setup check failed", detail: message, tone: "bad" });
      await persistVoiceSetupProof({
        action: "check_setup",
        status: "failed",
        summary: `Voice setup check failed: ${message}`,
        metadata: {
          action_source: "check_setup",
          failure_message: message
        }
      }).catch(() => undefined);
    } finally {
      if (isCurrentSetupCheck()) {
        setupCheckInFlightRef.current = false;
        setSetupCheckLoading(false);
      }
      if (parentMutationSnapshot) {
        onVoiceProofMutationFinish?.(parentMutationSnapshot);
      }
    }
  }

  async function handleResolveVoiceSetup() {
    if (setupCheckInFlightRef.current) {
      return;
    }
    if (voiceSetupActionInFlightRef.current !== null) {
      return;
    }
    if (!voiceSetupAction) {
      return;
    }
    const setupActionRunId = runId;
    const setupActionSessionId = liveSession?.realtime_session_id ?? null;
    const setupActionToken = voiceSetupActionSequenceRef.current + 1;
    voiceSetupActionSequenceRef.current = setupActionToken;
    voiceSetupActionInFlightRef.current = setupActionToken;
    setVoiceSetupActionLoading(true);
    const isCurrentSetupAction = (sessionId = setupActionSessionId) =>
      voiceSetupActionSequenceRef.current === setupActionToken &&
      currentRunIdRef.current === setupActionRunId &&
      (!sessionId || activeRealtimeSessionIdRef.current === sessionId);
    const recordResolverAttempt = async (
      proofStatus: string,
      summary: string,
      extraMetadata: Record<string, unknown> = {}
    ) => {
      if (!isCurrentSetupAction()) {
        return;
      }
      await persistVoiceSetupProof({
        action: voiceSetupAction,
        status: proofStatus,
        summary,
        blocker: voiceSetupBlocker,
        realtimeSessionId: activeRealtimeSessionIdRef.current ?? setupActionSessionId,
        metadata: {
          action_source: "resolve_next",
          blocker_label: voiceSetupBlocker?.label ?? null,
          blocker_status: voiceSetupBlocker?.status ?? null,
          ...extraMetadata
        }
      }).catch((proofError) => {
        if (!isCurrentSetupAction()) {
          return;
        }
        addEvent({
          label: "Voice setup proof failed",
          detail:
            proofError instanceof Error
              ? proofError.message
              : "Could not record durable voice setup proof.",
          tone: "warn"
        });
      });
    };
    const runResolverParentMutation = async (label: string, action: () => Promise<void>) => {
      if (!runId) {
        await action();
        return true;
      }
      const parentMutationSnapshot = onVoiceProofMutationStart?.(label);
      if (onVoiceProofMutationStart && !parentMutationSnapshot) {
        return false;
      }
      try {
        await action();
        return true;
      } finally {
        if (parentMutationSnapshot) {
          onVoiceProofMutationFinish?.(parentMutationSnapshot);
        }
      }
    };
    try {
      if (voiceSetupAction === "start_livekit") {
        await runResolverParentMutation(
          "Starting local LiveKit",
          async () => {
            await handleStartLiveKitProcess({ skipParentMutation: true });
            await recordResolverAttempt(
              "attempted",
              "Voice setup resolver requested local LiveKit transport start."
            );
          }
        );
        return;
      }
      if (voiceSetupAction === "restart_livekit") {
        await runResolverParentMutation(
          "Restarting local LiveKit",
          async () => {
            await handleStartLiveKitProcess({ forceRestart: true, skipParentMutation: true });
            await recordResolverAttempt(
              "attempted",
              "Voice setup resolver requested local LiveKit transport restart.",
              { force_restart: true }
            );
          }
        );
        return;
      }
      if (voiceSetupAction === "configure_local_livekit_dev") {
        await runResolverParentMutation(
          "Configuring local LiveKit dev defaults",
          async () => {
            const configAttempt = await handleConfigureLocalLiveKitDev({ skipParentMutation: true });
            if (configAttempt.status === "skipped") {
              return;
            }
            const configResult = configAttempt.status === "ready" ? configAttempt.result : null;
            await recordResolverAttempt(
              configAttempt.status === "ready" ? "ready" : "failed",
              configAttempt.status === "ready"
                ? "Voice setup resolver configured local LiveKit dev defaults."
                : "Voice setup resolver could not configure local LiveKit dev defaults.",
              localLiveKitDevSetupProofMetadata(configResult)
            );
          }
        );
        return;
      }
      if (voiceSetupAction === "run_preflight") {
        await runResolverParentMutation(
          "Running setup runtime preflight",
          async () => {
            const readinessResult = await refreshVoiceReadiness({
              ...RUNTIME_PREFLIGHT_READINESS_OPTIONS,
              shouldApply: isCurrentSetupAction
            });
            await recordResolverAttempt(
              voiceSetupReadinessProofStatus(readinessResult.status),
              `Voice setup resolver ran runtime preflight: ${readinessResult.summary}`,
              { readiness_status: readinessResult.status }
            );
          }
        );
        return;
      }
      if (voiceSetupAction === "start_agent") {
        await runResolverParentMutation(
          "Starting voice agent",
          async () => {
            await handleStartProcess({ skipParentMutation: true });
            await recordResolverAttempt(
              "attempted",
              "Voice setup resolver requested OpenRouter/Kokoro agent start."
            );
          }
        );
        return;
      }
      if (voiceSetupAction === "join_room" || voiceSetupAction === "start_rehearsal") {
        await handleStart();
        await recordResolverAttempt(
          "attempted",
          `Voice setup resolver requested ${voiceSetupActionLabel(voiceSetupAction).toLowerCase()}.`
        );
        return;
      }
      if (voiceSetupAction === "refresh_provider_readiness") {
        const parentMutationSnapshot = onVoiceProofMutationStart?.("Refreshing provider readiness");
        if (onVoiceProofMutationStart && !parentMutationSnapshot) {
          return;
        }
        try {
          const providerReadinessResult = await refreshProviderReadiness({
            shouldApply: isCurrentSetupAction
          });
          const refreshedProviderReleaseGate = buildVoiceProviderReleaseGate({
            providerReadiness: providerReadinessResult,
            runtimeReadiness: readiness,
            smoke: voiceSmoke,
            presence: voicePresence,
            activeRealtimeSessionId: activeProviderRealtimeSessionId,
            artifacts
          });
          const refreshedSteps = buildVoiceSetupChecklist({
            runId,
            provider,
            readiness,
            voiceProcess,
            liveKitProcess,
            liveSession,
            liveRoomConnected,
            voicePresence,
            isRehearsalSession,
            providerReleaseGate: refreshedProviderReleaseGate
          });
          const refreshedBlocker = voiceSetupPrimaryBlocker(refreshedSteps);
          if (!isCurrentSetupAction()) {
            return;
          }
          await persistVoiceSetupProof({
            action: voiceSetupAction,
            status: voiceSetupProofStatus(refreshedBlocker),
            summary: refreshedBlocker
              ? `Voice setup resolver refreshed provider readiness: ${refreshedBlocker.label} still needs attention.`
              : `Voice setup resolver refreshed provider readiness: ${providerReadinessResult.summary}`,
            steps: refreshedSteps,
            blocker: refreshedBlocker,
            realtimeSessionId: activeRealtimeSessionIdRef.current ?? setupActionSessionId,
            metadata: {
              action_source: "resolve_next",
              provider_release_gate_status: refreshedProviderReleaseGate.status,
              blocker_label: refreshedBlocker?.label ?? null,
              blocker_status: refreshedBlocker?.status ?? null
            }
          }).catch((proofError) => {
            if (!isCurrentSetupAction()) {
              return;
            }
            addEvent({
              label: "Voice setup proof failed",
              detail:
                proofError instanceof Error
                  ? proofError.message
                  : "Could not record durable voice setup proof.",
              tone: "warn"
            });
          });
        } finally {
          if (parentMutationSnapshot) {
            onVoiceProofMutationFinish?.(parentMutationSnapshot);
          }
        }
        return;
      }
      if (voiceSetupAction === "run_live_smoke") {
        const smokeOutcome = await handleVoiceSmoke({ live: true });
        if (smokeOutcome.status === "stale") {
          return;
        }
        if (smokeOutcome.status !== "built") {
          await recordResolverAttempt(
            smokeOutcome.status === "cancelled" ? "pending" : "failed",
            smokeOutcome.status === "cancelled"
              ? "Voice setup resolver cancelled live OpenRouter/Kokoro smoke before external calls."
              : `Voice setup resolver could not build live OpenRouter/Kokoro smoke: ${
                  smokeOutcome.message ?? "Unknown failure"
                }`,
            {
              release_gate_status: providerReleaseGate.status,
              smoke_outcome: smokeOutcome.status
            }
          );
          return;
        }
        const smokePresence = smokeOutcome.presence ?? voicePresence;
        const smokeProviderReleaseGate = buildVoiceProviderReleaseGate({
          providerReadiness,
          runtimeReadiness: readiness,
          smoke: smokeOutcome.result,
          presence: smokePresence,
          activeRealtimeSessionId: activeProviderRealtimeSessionId,
          artifacts: [
            ...artifacts,
            providerSmokeArtifactFromResult(smokeOutcome.result)
          ]
        });
        const smokeSteps = buildVoiceSetupChecklist({
          runId,
          provider,
          readiness,
          voiceProcess,
          liveKitProcess,
          liveSession,
          liveRoomConnected,
          voicePresence: smokePresence,
          isRehearsalSession,
          providerReleaseGate: smokeProviderReleaseGate
        });
        const smokeBlocker = voiceSetupPrimaryBlocker(smokeSteps);
        if (!isCurrentSetupAction()) {
          return;
        }
        await persistVoiceSetupProof({
          action: voiceSetupAction,
          status: voiceSetupProofStatus(smokeBlocker),
          summary: smokeBlocker
            ? `Voice setup resolver built live OpenRouter/Kokoro smoke, but ${smokeBlocker.label} still needs attention.`
            : "Voice setup resolver built live OpenRouter/Kokoro smoke and all setup checks are ready.",
          steps: smokeSteps,
          blocker: smokeBlocker,
          realtimeSessionId: activeRealtimeSessionIdRef.current ?? setupActionSessionId,
          metadata: {
            action_source: "resolve_next",
            provider_release_gate_status: smokeProviderReleaseGate.status,
            provider_smoke_status: smokeOutcome.result.status,
            smoke_outcome: smokeOutcome.status,
            blocker_label: smokeBlocker?.label ?? null,
            blocker_status: smokeBlocker?.status ?? null,
            agent_presence_status: smokePresence?.status ?? null
          }
        }).catch((proofError) => {
          if (!isCurrentSetupAction()) {
            return;
          }
          addEvent({
            label: "Voice setup proof failed",
            detail:
              proofError instanceof Error
                ? proofError.message
                : "Could not record durable voice setup proof.",
            tone: "warn"
          });
        });
        return;
      }
      if (voiceSetupAction === "probe_presence") {
        if (!runId || !liveSession) {
          await refreshVoicePresence(liveSession?.realtime_session_id ?? null);
          return;
        }
        if (!liveRuntime) {
          await refreshVoicePresence(liveSession.realtime_session_id);
          return;
        }
        const waitResult = await probeAndWaitForVoiceAgentPresence({
          realtimeSessionId: liveSession.realtime_session_id,
          probeAgentPresence: liveRuntime.probeAgentPresence,
          refreshVoicePresence: async (sessionId, probeId) => {
            const presence = await getVoiceAgentPresence({
              runId,
              realtimeSessionId: sessionId,
              probeId,
              staleAfterSeconds: 60
            });
            if (
              voiceSetupActionSequenceRef.current === setupActionToken &&
              currentRunIdRef.current === runId &&
              activeRealtimeSessionIdRef.current === sessionId
            ) {
              setVoicePresence(presence);
            }
            return presence;
          },
          maxAttempts: 5,
          intervalMs: 300
        });
        if (!isCurrentSetupAction(liveSession.realtime_session_id)) {
          return;
        }
        addEvent({
          label: waitResult.ready ? "Voice-agent presence ready" : "Voice-agent presence missing",
          detail: waitResult.summary,
          tone: waitResult.ready ? "good" : "warn"
        });
        const proofSteps = buildVoiceSetupChecklist({
          runId,
          provider,
          readiness,
          voiceProcess,
          liveKitProcess,
          liveSession,
          liveRoomConnected,
          voicePresence: waitResult.presence ?? voicePresence,
          isRehearsalSession,
          providerReleaseGate
        });
        await persistVoiceSetupProof({
          action: voiceSetupAction,
          status: waitResult.ready ? "ready" : "blocked",
          summary: `Voice setup resolver probed agent presence: ${waitResult.summary}`,
          steps: proofSteps,
          blocker: voiceSetupPrimaryBlocker(proofSteps),
          realtimeSessionId: liveSession.realtime_session_id,
          metadata: {
            action_source: "resolve_next",
            probe_ready: waitResult.ready,
            probe_cancelled: waitResult.cancelled,
            blocker_label: voiceSetupBlocker?.label ?? null
          }
        }).catch((proofError) => {
          if (!isCurrentSetupAction()) {
            return;
          }
          addEvent({
            label: "Voice setup proof failed",
            detail:
              proofError instanceof Error
                ? proofError.message
                : "Could not record durable voice setup proof.",
            tone: "warn"
          });
        });
      }
    } catch (setupError) {
      if (!isCurrentSetupAction()) {
        return;
      }
      const message =
        setupError instanceof Error ? setupError.message : "Could not resolve the next voice setup step.";
      setError(message);
      addEvent({ label: "Voice setup action failed", detail: message, tone: "bad" });
      await persistVoiceSetupProof({
        action: voiceSetupAction,
        status: "failed",
        summary: `Voice setup resolver failed: ${message}`,
        blocker: voiceSetupBlocker,
        realtimeSessionId: activeRealtimeSessionIdRef.current ?? setupActionSessionId,
        metadata: {
          action_source: "resolve_next",
          failure_message: message,
          blocker_label: voiceSetupBlocker?.label ?? null
        }
      }).catch(() => undefined);
    } finally {
      if (voiceSetupActionInFlightRef.current === setupActionToken) {
        voiceSetupActionInFlightRef.current = null;
        setVoiceSetupActionLoading(false);
      }
    }
  }

  async function handleLiveVoiceProofPathAction() {
    if (liveVoiceProofPathActionInFlightRef.current !== null) {
      return;
    }
    const liveProofAction = liveVoiceProofPath.primaryAction;
    if (!runId || !liveProofAction) {
      return;
    }
    const proofActionRunId = runId;
    const proofActionSessionId = liveSession?.realtime_session_id ?? null;
    const proofActionToken = liveVoiceProofActionSequenceRef.current + 1;
    liveVoiceProofActionSequenceRef.current = proofActionToken;
    liveVoiceProofPathActionInFlightRef.current = proofActionToken;
    setLiveVoiceProofPathActionLoading(true);
    const isCurrentProofAction = (sessionId = proofActionSessionId) =>
      liveVoiceProofActionSequenceRef.current === proofActionToken &&
      currentRunIdRef.current === proofActionRunId &&
      (!sessionId || activeRealtimeSessionIdRef.current === sessionId);
    const needsParentProofGate =
      liveProofAction === "refresh_provider_readiness" ||
      liveProofAction === "run_runtime_preflight" ||
      liveProofAction === "probe_presence";
    let parentMutationSnapshot: VoiceRunMutationSnapshot | undefined;
    try {
      if (needsParentProofGate) {
        parentMutationSnapshot = onVoiceProofMutationStart?.(
          liveProofAction === "refresh_provider_readiness"
            ? "Refreshing live voice provider readiness"
            : liveProofAction === "run_runtime_preflight"
            ? "Running live voice runtime preflight"
            : "Probing live voice agent presence"
        );
        if (onVoiceProofMutationStart && !parentMutationSnapshot) {
          return;
        }
      }
      switch (liveProofAction) {
        case "refresh_provider_readiness":
          await refreshProviderReadiness({
            shouldApply: isCurrentProofAction
          });
          return;
        case "run_runtime_preflight":
          await refreshVoiceReadiness({
            ...RUNTIME_PREFLIGHT_READINESS_OPTIONS,
            shouldApply: isCurrentProofAction
          });
          return;
        case "join_room":
          await handleStart();
          return;
        case "probe_presence":
          if (liveRuntime && liveSession && runId) {
            const waitResult = await probeAndWaitForVoiceAgentPresence({
              realtimeSessionId: liveSession.realtime_session_id,
              probeAgentPresence: liveRuntime.probeAgentPresence,
              refreshVoicePresence: async (sessionId, probeId) => {
                if (!isCurrentProofAction(sessionId)) {
                  return null;
                }
                const presence = await getVoiceAgentPresence({
                  runId,
                  realtimeSessionId: sessionId,
                  probeId,
                  staleAfterSeconds: 60
                });
                if (!isCurrentProofAction(sessionId)) {
                  return null;
                }
                setVoicePresence(presence);
                return presence;
              },
              maxAttempts: 5,
              intervalMs: 300,
              shouldContinue: () => isCurrentProofAction(liveSession.realtime_session_id)
            });
            if (!isCurrentProofAction(liveSession.realtime_session_id)) {
              return;
            }
            addEvent({
              label: waitResult.ready ? "Voice-agent presence ready" : "Voice-agent presence missing",
              detail: waitResult.summary,
              tone: waitResult.ready ? "good" : "warn"
            });
            return;
          }
          await refreshVoicePresence(liveSession?.realtime_session_id ?? null);
          return;
        case "run_live_smoke":
          await handleVoiceSmoke({ live: true });
          return;
        case "build_timing_ledger":
          await handleTimingLedger();
          return;
      }
    } finally {
      if (liveVoiceProofPathActionInFlightRef.current === proofActionToken) {
        liveVoiceProofPathActionInFlightRef.current = null;
        setLiveVoiceProofPathActionLoading(false);
      }
      if (parentMutationSnapshot) {
        onVoiceProofMutationFinish?.(parentMutationSnapshot);
      }
    }
  }

  async function handleProviderReadinessRefresh() {
    if (providerReadinessActionInFlightRef.current !== null) {
      return;
    }
    const providerRefreshRunId = runId;
    const providerRefreshToken = providerReadinessActionSequenceRef.current + 1;
    providerReadinessActionSequenceRef.current = providerRefreshToken;
    providerReadinessActionInFlightRef.current = providerRefreshToken;
    const isCurrentProviderRefresh = () =>
      providerReadinessActionSequenceRef.current === providerRefreshToken &&
      currentRunIdRef.current === providerRefreshRunId;
    if (!runId) {
      try {
        await refreshProviderReadiness({
          shouldApply: isCurrentProviderRefresh
        });
      } finally {
        if (providerReadinessActionInFlightRef.current === providerRefreshToken) {
          providerReadinessActionInFlightRef.current = null;
        }
      }
      return;
    }
    const parentMutationSnapshot = onVoiceProofMutationStart?.("Refreshing provider readiness");
    if (onVoiceProofMutationStart && !parentMutationSnapshot) {
      if (providerReadinessActionInFlightRef.current === providerRefreshToken) {
        providerReadinessActionInFlightRef.current = null;
      }
      return;
    }
    try {
      await refreshProviderReadiness({
        shouldApply: isCurrentProviderRefresh
      });
    } finally {
      if (providerReadinessActionInFlightRef.current === providerRefreshToken) {
        providerReadinessActionInFlightRef.current = null;
      }
      if (parentMutationSnapshot) {
        onVoiceProofMutationFinish?.(parentMutationSnapshot);
      }
    }
  }

  async function handleStart() {
    if (!runId) {
      setError("Create or restore a content run before starting live voice.");
      return;
    }
    if (startActionInFlightRef.current) {
      return;
    }

    const parentMutationSnapshot = onVoiceRunMutationStart?.(
      provider === "local_rehearsal" ? "Starting transcript rehearsal" : "Joining voice room"
    );
    if (onVoiceRunMutationStart && !parentMutationSnapshot) {
      return;
    }

    const startRunId = runId;
    const startToken = startSequenceRef.current + 1;
    startSequenceRef.current = startToken;
    const startActionSnapshot = { runId: startRunId, token: startToken };
    startActionInFlightRef.current = startActionSnapshot;
    activeRealtimeSessionIdRef.current = null;
    const isCurrentStart = () =>
      startSequenceRef.current === startToken && currentRunIdRef.current === startRunId;

    setStatus("starting");
    setVoiceStage("connecting");
    setLiveTranscript(EMPTY_LIVE_VOICE_TRANSCRIPT);
    setLiveTextTurn("");
    setLiveTextTurnLoading(false);
    liveTextTurnInFlightRef.current = false;
    setMicrophonePublished(false);
    setMicrophoneControlLoading(false);
    setInterruptControlLoading(false);
    microphoneControlSequenceRef.current += 1;
    interruptControlSequenceRef.current += 1;
    interruptControlInFlightRef.current = false;
    stopActionSequenceRef.current += 1;
    stopActionInFlightRef.current = null;
    liveTextTurnSequenceRef.current += 1;
    invalidateRehearsalTurn({ clearLoading: true });
    setCancellationProof(IDLE_CANCELLATION_PROOF);
    setError("");

    try {
      if (provider === "local_rehearsal") {
        const sessionKey = `${provider}:${voice || "default"}:dry-run`;
        const session = await startRealtimeSession(runId, {
          provider: "openrouter_livekit",
          voice: voice || undefined,
          transportFramework: "local_rehearsal",
          contextWindowTurns: 4,
          summarizeAfterTurns: 3,
          dryRun: true
        });
        if (!isCurrentStart()) {
          await endRealtimeSession({
            realtimeSessionId: session.realtime_session_id,
            reason: "Discarded stale transcript rehearsal session after the active run changed."
          }).catch(() => undefined);
          return;
        }
        activeRealtimeSessionIdRef.current = session.realtime_session_id;
        setLiveSession(session);
        setLiveRuntime(null);
        setStatus("ready");
        setVoiceStage("connected");
        onSessionReady(session, sessionKey);
        addEvent({
          label: "Transcript rehearsal ready",
          detail: "Dry-run realtime session created without LiveKit/OpenRouter/Kokoro credentials.",
          tone: "info"
        });
        await onRunUpdated("Started a transcript-only realtime rehearsal session.");
        return;
      }

      if (provider === "openrouter_livekit") {
        const liveKitStatus = liveKitProcess ?? await refreshLiveKitProcess();
        if (!isCurrentStart()) {
          return;
        }
        if (liveKitStatus?.enabled === false) {
          addEvent({
            label: "External LiveKit server expected",
            detail: "Local LiveKit supervision is disabled, so the app will use the configured transport as-is.",
            tone: "warn"
          });
        } else if (shouldAutoStartLocalLiveKitProcess(liveKitStatus)) {
          setLiveKitProcessLoading("start");
          addEvent({
            label: "Starting local LiveKit",
            detail: "The live voice start flow is bringing up the local LiveKit dev transport before runtime preflight.",
            tone: "info"
          });
          try {
            const startedLiveKit = await startLocalLiveKitProcess({ mode: liveKitMode });
            setLiveKitProcess(startedLiveKit);
            const blocker = localLiveKitProcessStartBlocker(startedLiveKit);
            if (blocker) {
              setStatus("blocked");
              setVoiceStage("failed");
              setError(blocker);
              addEvent({
                label: "Local LiveKit did not start",
                detail: blocker,
                tone: "bad"
              });
              return;
            }
            addEvent({
              label: "Local LiveKit running",
              detail: startedLiveKit.summary,
              tone: "good"
            });
          } finally {
            setLiveKitProcessLoading(null);
          }
          if (!isCurrentStart()) {
            return;
          }
        } else if (liveKitStatus) {
          const blocker = localLiveKitProcessStartBlocker(liveKitStatus);
          if (blocker) {
            setStatus("blocked");
            setVoiceStage("failed");
            setError(blocker);
            addEvent({
              label: "Local LiveKit not ready",
              detail: blocker,
              tone: "bad"
            });
            return;
          }
        }
        const readinessResult = await refreshVoiceReadiness(RUNTIME_PREFLIGHT_READINESS_OPTIONS);
        if (!isCurrentStart()) {
          return;
        }
        if (readinessResult.status === "blocked") {
          setStatus("blocked");
          setVoiceStage("failed");
          setError(readinessResult.summary);
          return;
        }
        const processStatus = voiceProcess ?? await refreshVoiceProcess();
        if (!isCurrentStart()) {
          return;
        }
        if (processStatus?.enabled === false) {
          addEvent({
            label: "External voice agent expected",
            detail: "Local process supervision is disabled, so the app will wait for an already-running OpenRouter/Kokoro participant.",
            tone: "warn"
          });
        } else if (shouldAutoStartVoiceAgentProcess(processStatus)) {
          setProcessLoading("start");
          addEvent({
            label: "Starting OpenRouter/Kokoro agent",
            detail: "The live voice start flow is bringing up the local LiveKit participant before joining.",
            tone: "info"
          });
          try {
            const startedProcess = await startVoiceAgentProcess();
            setVoiceProcess(startedProcess);
            const blocker = voiceAgentProcessStartBlocker(startedProcess);
            if (blocker) {
              setStatus("blocked");
              setVoiceStage("failed");
              setError(blocker);
              addEvent({
                label: "OpenRouter/Kokoro agent did not start",
                detail: blocker,
                tone: "bad"
              });
              return;
            }
            addEvent({
              label: "OpenRouter/Kokoro agent running",
              detail: startedProcess.summary,
              tone: "good"
            });
          } finally {
            setProcessLoading(null);
          }
          if (!isCurrentStart()) {
            return;
          }
        } else if (processStatus) {
          const blocker = voiceAgentProcessStartBlocker(processStatus);
          if (blocker) {
            setStatus("blocked");
            setVoiceStage("failed");
            setError(blocker);
            addEvent({
              label: "OpenRouter/Kokoro agent not ready",
              detail: blocker,
              tone: "bad"
            });
            return;
          }
        }
      }
      const sessionKey = `${provider}:${voice || "default"}:livekit`;
      const session = await startRealtimeSession(runId, {
        provider,
        voice: voice || undefined,
        transportFramework: "livekit",
        contextWindowTurns: 4,
        summarizeAfterTurns: 3,
        dryRun: false
      });
      const cleanupStartedSession = async (reason: string) => {
        try {
          await endRealtimeSession({
            realtimeSessionId: session.realtime_session_id,
            reason
          });
          return true;
        } catch (endError) {
          if (
            currentRunIdRef.current === session.run_id &&
            activeRealtimeSessionIdRef.current === session.realtime_session_id
          ) {
            addEvent({
              label: "Blocked voice session cleanup failed",
              detail: endError instanceof Error ? endError.message : "Could not end blocked LiveKit session.",
              tone: "warn"
            });
          }
          return false;
        }
      };
      if (!isCurrentStart()) {
        await cleanupStartedSession("Discarded stale OpenRouter/Kokoro voice session after the active run changed.");
        return;
      }
      activeRealtimeSessionIdRef.current = session.realtime_session_id;
      setLiveSession(session);
      addEvent({
        label: "Voice transport grant issued",
        detail: `${session.provider} using ${session.transport?.framework ?? "livekit"}; token ${
          session.transport?.has_token ? "received" : "missing"
        }`,
        tone: "good"
      });
      setStatus("joining");
      setVoiceStage("connecting");

      const joinResult = await joinLiveKitRuntime(session, {
        audioElementRoot: remoteAudioRootRef.current,
        enableMicrophone: true,
        onEvent: (runtimeEvent) => {
          if (
            currentRunIdRef.current !== session.run_id ||
            activeRealtimeSessionIdRef.current !== session.realtime_session_id
          ) {
            return;
          }
          handleRuntimeEvent(runtimeEvent);
        },
        onMicrophonePublishingChanged: (publishing) => {
          if (
            currentRunIdRef.current !== session.run_id ||
            activeRealtimeSessionIdRef.current !== session.realtime_session_id
          ) {
            return;
          }
          setMicrophonePublished(publishing);
        },
        onAgentEvent: async (agentEvent) => {
          if (
            currentRunIdRef.current !== session.run_id ||
            activeRealtimeSessionIdRef.current !== session.realtime_session_id
          ) {
            return;
          }
          setVoiceStage((current) => stageFromVoiceAgentEvent(current, agentEvent.event_type));
          setLiveTranscript((current) =>
            liveVoiceTranscriptFromAgentEvent(current, agentEvent.event_type, agentEvent.payload)
          );
          let recorded: RealtimeVoiceAgentEventRecordResult;
          try {
            recorded = await recordRealtimeVoiceEvent({
              realtimeSessionId: session.realtime_session_id,
              eventType: agentEvent.event_type,
              payload: agentEvent.payload,
              agentCreatedAt: agentEvent.created_at ?? null,
              voiceAgentEventUid:
                typeof agentEvent.payload.voice_agent_event_uid === "string"
                  ? agentEvent.payload.voice_agent_event_uid
                  : null,
              source: "next_livekit_data_channel"
            });
          } catch (recordError) {
            addEvent({
              label: "Voice timing persistence failed",
              detail: recordError instanceof Error ? recordError.message : "Could not persist LiveKit agent timing.",
              tone: "warn"
            });
            return;
          }
          if (
            currentRunIdRef.current !== session.run_id ||
            activeRealtimeSessionIdRef.current !== session.realtime_session_id
          ) {
            return;
          }
          setCancellationProof((current) =>
            cancellationProofFromVoiceAgentEvent(current, recorded.event_type, agentEvent.payload)
          );

          if (recorded.materialized_turn_id) {
            try {
              await onRunUpdated(
                recorded.materialized_speaker === "assistant"
                  ? "Live voice assistant response added to dialogue."
                  : "Live voice user turn added to dialogue."
              );
            } catch (refreshError) {
              addEvent({
                label: "Voice dialogue refresh failed",
                detail:
                  refreshError instanceof Error
                    ? refreshError.message
                    : "Could not refresh the run after the LiveKit voice event.",
                tone: "warn"
              });
            }
          }
          if (recorded.event_type === "gemma_kokoro_voice_agent_ready") {
            try {
              const probeId =
                typeof agentEvent.payload.probe_id === "string"
                  ? agentEvent.payload.probe_id
                  : null;
              const presence = await refreshVoicePresence(
                session.realtime_session_id,
                probeId
              );
              addEvent({
                label: "Voice-agent participant observed",
                detail: presence?.summary ?? "Durable OpenRouter/Kokoro participant proof recorded.",
                tone: presence?.status === "ready" ? "good" : "warn"
              });
            } catch (presenceError) {
              addEvent({
                label: "Voice-agent presence refresh failed",
                detail:
                  presenceError instanceof Error
                    ? presenceError.message
                    : "Could not refresh durable participant proof.",
                tone: "warn"
              });
            }
          }
          if (recorded.followup_task_message_id && onVoiceFollowupReady) {
            const followupContinuation = voiceFollowupContinuationForEvent(recorded);
            addEvent({
              label: followupContinuation.label,
              detail: followupContinuation.detail,
              tone: "info"
            });
            try {
              await onVoiceFollowupReady(
                recorded.followup_task_message_id,
                followupContinuation.options
              );
            } catch (followupError) {
              addEvent({
                label: followupContinuation.failureLabel,
                detail:
                  followupError instanceof Error
                    ? followupError.message
                    : "Could not continue specialist agents from the LiveKit voice event.",
                tone: "warn"
              });
            }
          }
        }
      });

      if (!isCurrentStart()) {
        if (joinResult.status === "joined") {
          await joinResult.runtime.disconnect().catch(() => undefined);
        }
        await cleanupStartedSession("Discarded stale OpenRouter/Kokoro voice session after LiveKit join completed for an inactive start.");
        return;
      }

      if (joinResult.status === "joined") {
        setLiveRuntime(joinResult.runtime);
        setStatus("ready");
        setVoiceStage("connected");
        onSessionReady(session, sessionKey);
        addEvent({
          label: "LiveKit room joined",
          detail: joinResult.message,
          tone: "good"
        });
        try {
          const probeId = await joinResult.runtime.probeAgentPresence();
          addEvent({
            label: "Voice-agent presence probe sent",
            detail: "Waiting for a durable OpenRouter/Kokoro participant ready event.",
            tone: "info"
          });
          await refreshVoicePresence(session.realtime_session_id, probeId).catch((presenceError) => {
            addEvent({
              label: "Voice-agent presence not observed yet",
              detail: presenceError instanceof Error ? presenceError.message : "No durable participant proof yet.",
              tone: "warn"
            });
          });
        } catch (probeError) {
          addEvent({
            label: "Voice-agent presence probe failed",
            detail: probeError instanceof Error ? probeError.message : "Could not publish the LiveKit probe.",
            tone: "warn"
          });
        }
        if (!isCurrentStart()) {
          return;
        }
        await onRunUpdated("Joined the OpenRouter/Kokoro LiveKit voice room.");
        return;
      }

      const cleanupEnded = await cleanupStartedSession("Discarded OpenRouter/Kokoro voice session after LiveKit join did not complete.");
      if (!isCurrentStart()) {
        return;
      }
      if (cleanupEnded) {
        activeRealtimeSessionIdRef.current = null;
        setLiveSession(null);
      } else {
        setStatus(joinResult.status === "blocked" ? "blocked" : "error");
        setVoiceStage("failed");
        setError(`${joinResult.message} Cleanup failed; press Stop to retry ending the durable voice session before joining again.`);
        addEvent({
          label: "Voice session cleanup needed",
          detail: "Press Stop to retry ending the blocked OpenRouter/Kokoro realtime session.",
          tone: "warn"
        });
        return;
      }
      setStatus(joinResult.status === "blocked" ? "blocked" : "error");
      setVoiceStage("failed");
      setError(joinResult.message);
      addEvent({
        label: joinResult.status === "blocked" ? "LiveKit join blocked" : "LiveKit join failed",
        detail: joinResult.message,
        tone: joinResult.status === "blocked" ? "warn" : "bad"
      });
    } catch (startError) {
      if (!isCurrentStart()) {
        return;
      }
      setStatus("error");
      setVoiceStage("failed");
      setError(startError instanceof Error ? startError.message : "Could not prepare OpenRouter/Kokoro live voice.");
    } finally {
      if (startActionInFlightRef.current === startActionSnapshot) {
        startActionInFlightRef.current = null;
      }
      if (parentMutationSnapshot) {
        onVoiceRunMutationFinish?.(parentMutationSnapshot);
      }
    }
  }

  async function handleInterrupt() {
    if (!liveSession || interruptControlInFlightRef.current || status !== "ready") {
      return;
    }
    const interruptSessionId = liveSession.realtime_session_id;
    const interruptRunId = liveSession.run_id;
    const interruptControlToken = interruptControlSequenceRef.current + 1;
    interruptControlSequenceRef.current = interruptControlToken;
    const isCurrentInterrupt = () =>
      interruptControlSequenceRef.current === interruptControlToken &&
      currentRunIdRef.current === interruptRunId &&
      activeRealtimeSessionIdRef.current === interruptSessionId;
    if (!isCurrentInterrupt()) {
      return;
    }
    interruptControlInFlightRef.current = true;
    setInterruptControlLoading(true);
    try {
      setVoiceStage("interrupting");
      setCancellationProof(requestedCancellationProof());
      const runtimeAtInterrupt = liveRuntime;
      runtimeAtInterrupt?.clearRemoteAudio();
      let livekitAgentControlId: string | null = null;
      let livekitAgentControlError: string | null = null;
      if (runtimeAtInterrupt) {
        try {
          livekitAgentControlId = await runtimeAtInterrupt.interruptAgent({
            reason: "Creator interrupted the OpenRouter/Kokoro voice response."
          });
        } catch (agentControlError) {
          livekitAgentControlError =
            agentControlError instanceof Error
              ? agentControlError.message
              : "Unknown LiveKit agent interrupt error";
          if (isCurrentInterrupt()) {
            addEvent({
              label: "Agent interrupt control failed",
              detail: livekitAgentControlError,
              tone: "bad"
            });
          }
        }
      } else {
        livekitAgentControlError = "No active LiveKit runtime was available to signal the agent.";
        if (isCurrentInterrupt()) {
          addEvent({
            label: "Agent interrupt control unavailable",
            detail: livekitAgentControlError,
            tone: "warn"
          });
        }
      }
      if (!isCurrentInterrupt()) {
        return;
      }
      try {
        const result = await controlRealtimeSession({
          realtimeSessionId: interruptSessionId,
          action: "interrupt",
          reason: "Creator interrupted the OpenRouter/Kokoro voice response.",
          cancelGemma: true,
          clearKokoroBuffers: true,
          stopLivekitAudio: true,
          metadata: buildRealtimeAgentControlMetadata({
            purpose: "interrupt",
            providerBackedRealtime: provider === "openrouter_livekit",
            transportFramework,
            livekitAgentControlId,
            livekitAgentControlError
          })
        });
        if (!isCurrentInterrupt()) {
          return;
        }
        setCancellationProof((current) =>
          current.status === "requested"
            ? requestedCancellationProof(result.event_id)
            : current
        );
        if (livekitAgentControlError) {
          setCancellationProof((current) =>
            failedCancellationProofFromControlError(
              current,
              livekitAgentControlError ?? "LiveKit agent interrupt failed"
            )
          );
        }
        addEvent({
          label: "Barge-in cancellation requested",
          detail: livekitAgentControlId ? `Agent control ${livekitAgentControlId}` : undefined,
          tone: "warn"
        });
        await onRunUpdated("Interrupted the live voice response.");
      } catch (interruptError) {
        if (isCurrentInterrupt()) {
          setCancellationProof((current) =>
            livekitAgentControlId
              ? current
              : failedCancellationProofFromControlError(
                  current,
                  interruptError instanceof Error ? interruptError.message : "Unknown interrupt error"
                )
          );
        }
        if (isCurrentInterrupt()) {
          addEvent({
            label: "Interrupt failed",
            detail: interruptError instanceof Error ? interruptError.message : "Unknown interrupt error",
            tone: "bad"
          });
        }
      }
    } finally {
      if (interruptControlSequenceRef.current === interruptControlToken) {
        interruptControlInFlightRef.current = false;
        setInterruptControlLoading(false);
      }
    }
  }

  async function handleToggleMicrophone() {
    if (!liveRuntime || !liveSession || !isReady || isRehearsalSession) {
      return;
    }
    const microphoneSessionId = liveSession.realtime_session_id;
    const microphoneRunId = liveSession.run_id;
    const targetPublishing = nextMicrophonePublishingState(microphonePublished);
    const microphoneControlToken = microphoneControlSequenceRef.current + 1;
    microphoneControlSequenceRef.current = microphoneControlToken;
    const isCurrentMicrophoneControl = () =>
      isMicrophoneControlCurrent({
        controlToken: microphoneControlToken,
        activeControlToken: microphoneControlSequenceRef.current,
        runId: microphoneRunId,
        activeRunId: currentRunIdRef.current,
        sessionId: microphoneSessionId,
        activeSessionId: activeRealtimeSessionIdRef.current
      });
    if (!isCurrentMicrophoneControl()) {
      return;
    }
    setMicrophoneControlLoading(true);
    try {
      const actualPublishing = await liveRuntime.setMicrophonePublishing(targetPublishing);
      if (!isCurrentMicrophoneControl()) {
        return;
      }
      setMicrophonePublished(actualPublishing);
    } catch (microphoneError) {
      if (isCurrentMicrophoneControl()) {
        addEvent({
          label: "Microphone control failed",
          detail: microphoneError instanceof Error ? microphoneError.message : "Could not update LiveKit microphone publishing.",
          tone: "bad"
        });
      }
    } finally {
      if (isCurrentMicrophoneControl()) {
        setMicrophoneControlLoading(false);
      }
    }
  }

  async function handleSendLiveTextTurn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!liveRuntime || !liveSession || !canSendLiveTextTurn || liveTextTurnInFlightRef.current) {
      return;
    }
    const textSessionId = liveSession.realtime_session_id;
    const textRunId = liveSession.run_id;
    const controlToken = liveTextTurnSequenceRef.current + 1;
    const transcript = liveTextTurn.trim();
    liveTextTurnSequenceRef.current = controlToken;
    const isCurrentTextTurn = () =>
      isLiveTextTurnCurrent({
        controlToken,
        activeControlToken: liveTextTurnSequenceRef.current,
        runId: textRunId,
        activeRunId: currentRunIdRef.current,
        sessionId: textSessionId,
        activeSessionId: activeRealtimeSessionIdRef.current
      });
    if (!isCurrentTextTurn()) {
      return;
    }
    liveTextTurnInFlightRef.current = true;
    setLiveTextTurnLoading(true);
    try {
      if (voiceStage === "speaking" || voiceStage === "thinking") {
        liveRuntime.clearRemoteAudio();
        await liveRuntime.interruptAgent({
          reason: "Creator typed a new live text turn."
        });
      }
      if (!isCurrentTextTurn()) {
        return;
      }
      const turnId = await liveRuntime.sendTranscriptTurn({
        transcript,
        voice
      });
      if (!isCurrentTextTurn()) {
        return;
      }
      setLiveTextTurn("");
      addEvent({
        label: "Live text turn queued",
        detail: turnId,
        tone: "info"
      });
    } catch (textTurnError) {
      if (isCurrentTextTurn()) {
        addEvent({
          label: "Live text turn failed",
          detail: textTurnError instanceof Error ? textTurnError.message : "Could not send the typed LiveKit turn.",
          tone: "bad"
        });
      }
    } finally {
      if (isCurrentTextTurn()) {
        liveTextTurnInFlightRef.current = false;
        setLiveTextTurnLoading(false);
      }
    }
  }

  async function handleRehearsalTurn() {
    if (
      !liveSession ||
      !runId ||
      !isRehearsalSession ||
      status !== "ready" ||
      activeRealtimeSessionIdRef.current !== liveSession.realtime_session_id
    ) {
      setError("Start a transcript rehearsal session before routing a rehearsal turn.");
      return;
    }
    if (rehearsalTurnInFlightRef.current) {
      return;
    }
    const rehearsalRunId = runId;
    const rehearsalSessionId = liveSession.realtime_session_id;
    const rehearsalTurnToken = rehearsalTurnSequenceRef.current + 1;
    rehearsalTurnSequenceRef.current = rehearsalTurnToken;
    const isCurrentRehearsalTurn = () =>
      componentMountedRef.current &&
      isLiveTextTurnCurrent({
        controlToken: rehearsalTurnToken,
        activeControlToken: rehearsalTurnSequenceRef.current,
        runId: rehearsalRunId,
        activeRunId: currentRunIdRef.current,
        sessionId: rehearsalSessionId,
        activeSessionId: activeRealtimeSessionIdRef.current
      });
    if (!isCurrentRehearsalTurn()) {
      return;
    }
    const parentMutationSnapshot = onVoiceRunMutationStart?.("Routing rehearsal turn");
    if (onVoiceRunMutationStart && !parentMutationSnapshot) {
      return;
    }
    let parentMutationFinished = false;
    const finishParentMutation = () => {
      if (!parentMutationFinished && parentMutationSnapshot) {
        onVoiceRunMutationFinish?.(parentMutationSnapshot);
        parentMutationFinished = true;
      }
    };
    rehearsalTurnInFlightRef.current = true;
    setRehearsalLoading(true);
    setError("");
    try {
      const result = await sendRealtimeTurn(
        buildTranscriptRehearsalTurnInput({
          realtimeSessionId: liveSession.realtime_session_id,
          transcript: rehearsalTranscript
        })
      );
      if (!isCurrentRehearsalTurn()) {
        return;
      }
      addEvent({
        label: "Rehearsal turn routed",
        detail: result.summary,
        tone: "good"
      });
      try {
        if (!isCurrentRehearsalTurn()) {
          return;
        }
        await onRunUpdated("Routed a transcript rehearsal through the realtime turn contract.");
      } catch (refreshError) {
        if (isCurrentRehearsalTurn()) {
          addEvent({
            label: "Rehearsal run refresh failed",
            detail: refreshError instanceof Error ? refreshError.message : "Could not refresh the run after rehearsal routing.",
            tone: "warn"
          });
        }
      }
      if (!isCurrentRehearsalTurn()) {
        return;
      }
      if (result.brief_task_message_id && onVoiceFollowupReady) {
        finishParentMutation();
        addEvent({
          label: "Rehearsal follow-up queued",
          detail: "Continuing specialist agents from the realtime rehearsal turn.",
          tone: "info"
        });
        try {
          await onVoiceFollowupReady(result.brief_task_message_id);
        } catch (followupError) {
          if (isCurrentRehearsalTurn()) {
            addEvent({
              label: "Rehearsal follow-up continuation failed",
              detail:
                followupError instanceof Error
                  ? followupError.message
                  : "Could not continue specialist agents from the realtime rehearsal turn.",
              tone: "warn"
            });
          }
        }
      }
    } catch (rehearsalError) {
      if (isCurrentRehearsalTurn()) {
        const message = rehearsalError instanceof Error ? rehearsalError.message : "Could not route the rehearsal turn.";
        setError(message);
        addEvent({ label: "Rehearsal turn failed", detail: message, tone: "bad" });
      }
    } finally {
      if (isCurrentRehearsalTurn()) {
        rehearsalTurnInFlightRef.current = false;
        setRehearsalLoading(false);
      }
      finishParentMutation();
    }
  }

  async function handleCreateVoiceRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!onCreateVoiceRun || !canCreateVoiceRun || voiceRunCreatingRef.current) {
      return;
    }
    voiceRunCreatingRef.current = true;
    setVoiceRunCreating(true);
    setError("");
    try {
      await onCreateVoiceRun(voiceRunGoal, { provider });
      if (componentMountedRef.current) {
        addEvent({
          label: "Voice run created",
          detail: "The durable run is ready for Live Voice setup.",
          tone: "good"
        });
      }
    } catch (createError) {
      const message = createError instanceof Error ? createError.message : "Could not create a voice run.";
      if (componentMountedRef.current) {
        setError(message);
        addEvent({ label: "Voice run creation failed", detail: message, tone: "bad" });
      }
    } finally {
      if (componentMountedRef.current) {
        setVoiceRunCreating(false);
      }
      voiceRunCreatingRef.current = false;
    }
  }

  async function handleStop() {
    if (stopActionInFlightRef.current !== null) {
      return;
    }
    const sessionAtStop = liveSession;
    const stopRunIdForGate = sessionAtStop?.run_id ?? currentRunIdRef.current;
    const parentMutationSnapshot = stopRunIdForGate
      ? onVoiceRunMutationStart?.("Stopping voice session")
      : undefined;
    if (stopRunIdForGate && onVoiceRunMutationStart && !parentMutationSnapshot) {
      return;
    }
    const stopActionToken = stopActionSequenceRef.current + 1;
    stopActionSequenceRef.current = stopActionToken;
    stopActionInFlightRef.current = stopActionToken;
    const stopSequence = startSequenceRef.current + 1;
    startSequenceRef.current = stopSequence;
    voiceSmokeSequenceRef.current += 1;
    voiceTimingSequenceRef.current += 1;
    presenceMonitorSequenceRef.current += 1;
    microphoneControlSequenceRef.current += 1;
    interruptControlSequenceRef.current += 1;
    interruptControlInFlightRef.current = false;
    liveTextTurnSequenceRef.current += 1;
    activeRealtimeSessionIdRef.current = null;
    invalidateRehearsalTurn({ clearLoading: true });
    setVoiceProofLoading(null);
    setStatus("stopping");
    setVoiceStage(stageFromVoiceStatus("stopping"));
    setLiveTranscript(EMPTY_LIVE_VOICE_TRANSCRIPT);
    setLiveTextTurn("");
    setLiveTextTurnLoading(false);
    liveTextTurnInFlightRef.current = false;
    setMicrophonePublished(false);
    setMicrophoneControlLoading(false);
    setInterruptControlLoading(false);
    setCancellationProof(IDLE_CANCELLATION_PROOF);
    try {
      const session = sessionAtStop;
      const runtime = liveRuntime;
      const stopRunId = session?.run_id ?? currentRunIdRef.current;
      const stopSessionId = session?.realtime_session_id ?? null;
      const isCurrentStop = () =>
        startSequenceRef.current === stopSequence &&
        stopActionInFlightRef.current === stopActionToken &&
        currentRunIdRef.current === stopRunId &&
        (stopSessionId === null ||
          activeRealtimeSessionIdRef.current === stopSessionId ||
          activeRealtimeSessionIdRef.current === null);
      let livekitAgentControlId: string | null = null;
      let livekitAgentControlError: string | null = null;
      if (runtime && session && !isRehearsalSession) {
        try {
          runtime.clearRemoteAudio();
          livekitAgentControlId = await runtime.interruptAgent({
            reason: "Creator stopped the OpenRouter/Kokoro live voice session."
          });
          if (isCurrentStop()) {
            addEvent({
              label: "Stop-output control sent",
              detail: livekitAgentControlId,
              tone: "warn"
            });
          }
        } catch (agentControlError) {
          livekitAgentControlError =
            agentControlError instanceof Error
              ? agentControlError.message
              : "Unknown LiveKit stop-output control error";
          if (isCurrentStop()) {
            addEvent({
              label: "Stop-output control failed",
              detail: livekitAgentControlError,
              tone: "warn"
            });
          }
        }
      }
      if (isCurrentStop()) {
        activeRealtimeSessionIdRef.current = null;
      }
      if (session && !isRehearsalSession) {
        try {
          await controlRealtimeSession({
            realtimeSessionId: session.realtime_session_id,
            action: "stop_output",
            reason: "Creator stopped the OpenRouter/Kokoro live voice session.",
            cancelGemma: true,
            clearKokoroBuffers: true,
            stopLivekitAudio: true,
            createFollowupTask: false,
            metadata: buildRealtimeAgentControlMetadata({
              purpose: "session_stop",
              providerBackedRealtime: provider === "openrouter_livekit",
              transportFramework,
              livekitAgentControlId,
              livekitAgentControlError
            })
          });
        } catch (controlError) {
          if (isCurrentStop()) {
            addEvent({
              label: "Stop-output control record failed",
              detail: controlError instanceof Error ? controlError.message : "Unknown stop-output record error",
              tone: "warn"
            });
          }
        }
      }
      if (runtime) {
        try {
          await runtime.disconnect();
        } catch (disconnectError) {
          if (isCurrentStop()) {
            addEvent({
              label: "LiveKit disconnect failed",
              detail: disconnectError instanceof Error ? disconnectError.message : "Unknown disconnect error",
              tone: "warn"
            });
          }
        }
      }
      if (session) {
        try {
          await endRealtimeSession({
            realtimeSessionId: session.realtime_session_id,
            reason: "Creator stopped the OpenRouter/Kokoro live voice session."
          });
          if (isCurrentStop()) {
            await onRunUpdated("Stopped the live voice session.");
          }
        } catch (stopError) {
          if (isCurrentStop()) {
            addEvent({
              label: "Session status update failed",
              detail: stopError instanceof Error ? stopError.message : "Unknown stop error",
              tone: "warn"
            });
          }
        }
      }
      if (!isCurrentStop()) {
        return;
      }
      setLiveRuntime(null);
      setLiveSession(null);
      setStatus("stopped");
      setVoiceStage(stageFromVoiceStatus("stopped"));
      addEvent({ label: "Live voice session stopped", tone: "info" });
    } finally {
      if (stopActionInFlightRef.current === stopActionToken) {
        stopActionInFlightRef.current = null;
      }
      if (parentMutationSnapshot) {
        onVoiceRunMutationFinish?.(parentMutationSnapshot);
      }
    }
  }

  async function handleVoiceSmoke(options: { live?: boolean } = {}): Promise<VoiceSmokeOutcome> {
    if (!runId) {
      const message = "Create or restore a content run before building voice smoke proof.";
      setError(message);
      return { status: "failed", message };
    }
    if (voiceProofActionInFlightRef.current) {
      return { status: "cancelled" };
    }
    const shouldRunLiveSmoke = options.live ?? liveSmoke;
    if (options.live === true) {
      setLiveSmoke(true);
    }
    const proofRunId = runId;
    const proofToken = voiceSmokeSequenceRef.current + 1;
    voiceSmokeSequenceRef.current = proofToken;
    const proofActionSnapshot = { kind: "smoke" as const, runId: proofRunId, token: proofToken };
    voiceProofActionInFlightRef.current = proofActionSnapshot;
    const parentMutationSnapshot = onVoiceProofMutationStart?.(
      shouldRunLiveSmoke ? "Running live voice smoke" : "Building voice smoke proof"
    );
    if (onVoiceProofMutationStart && !parentMutationSnapshot) {
      voiceProofActionInFlightRef.current = null;
      return { status: "cancelled" };
    }
    const proofSnapshot = { runId: proofRunId, token: proofToken };
    const isCurrentProof = () =>
      isRunBoundRequestCurrent(
        proofSnapshot,
        currentRunIdRef.current,
        voiceSmokeSequenceRef.current
      );
    if (shouldRunLiveSmoke) {
      const confirmed = window.confirm(
        "Run live OpenRouter/Kokoro provider smoke with configured external endpoints?"
      );
      if (!confirmed) {
        if (voiceProofActionInFlightRef.current === proofActionSnapshot) {
          voiceProofActionInFlightRef.current = null;
        }
        if (parentMutationSnapshot) {
          onVoiceProofMutationFinish?.(parentMutationSnapshot);
        }
        setError("");
        addEvent({ label: "Live voice smoke cancelled", tone: "info" });
        return { status: "cancelled" };
      }
    }
    const sessionBoundLiveSmoke =
      shouldRunLiveSmoke &&
      provider === "openrouter_livekit" &&
      liveSession !== null &&
      liveRuntime !== null &&
      status === "ready" &&
      !isRehearsalSession;
    if (shouldRunLiveSmoke && provider === "openrouter_livekit" && !sessionBoundLiveSmoke) {
      addEvent({
        label: "Live smoke is not session-bound",
        detail: "Join the OpenRouter/Kokoro LiveKit room first and keep it connected to require fresh participant presence proof.",
        tone: "warn"
      });
    }
    setVoiceProofLoading("smoke");
    setError("");
    let smokePresence: VoiceAgentPresenceResult | null = null;
    try {
      if (sessionBoundLiveSmoke) {
        addEvent({
          label: "Voice-agent presence probe sent",
          detail: "Checking the active LiveKit room before session-bound smoke.",
          tone: "info"
        });
        const waitResult = await probeAndWaitForVoiceAgentPresence({
          realtimeSessionId: liveSession.realtime_session_id,
          probeAgentPresence: liveRuntime.probeAgentPresence,
          refreshVoicePresence: async (sessionId, probeId) => {
            if (!isCurrentProof()) {
              return null;
            }
            const presence = await getVoiceAgentPresence({
              runId: proofRunId,
              realtimeSessionId: sessionId,
              probeId,
              staleAfterSeconds: 60
            });
            if (!isCurrentProof()) {
              return null;
            }
            setVoicePresence(presence);
            return presence;
          },
          maxAttempts: 5,
          intervalMs: 300,
          shouldContinue: isCurrentProof
        });
        if (!isCurrentProof()) {
          return { status: "stale" };
        }
        if (waitResult.presence) {
          smokePresence = waitResult.presence;
          setVoicePresence(waitResult.presence);
        }
        addEvent({
          label: waitResult.cancelled
            ? "Voice-agent presence check cancelled"
            : waitResult.ready
            ? "Voice-agent participant verified"
            : "Voice-agent participant not observed before smoke",
          detail: waitResult.summary,
          tone: waitResult.ready ? "good" : "warn"
        });
      }
      const result = await buildVoiceProviderSmoke({
        runId,
        voice: voice || "af_heart",
        executeLiveCalls: shouldRunLiveSmoke,
        realtimeSessionId: sessionBoundLiveSmoke
          ? liveSession.realtime_session_id
          : undefined,
        requireVoiceAgentPresence: sessionBoundLiveSmoke,
        voiceAgentPresenceStaleAfterSeconds: 60
      });
      if (!isCurrentProof()) {
        return { status: "stale" };
      }
      setVoiceSmoke(result);
      addEvent({
        label: "Voice smoke ledger built",
        detail: result.summary,
        tone: result.status === "passed" ? "good" : result.status === "blocked" ? "bad" : "warn"
      });
      if (isCurrentProof()) {
        await onRunUpdated("Built the OpenRouter/Kokoro voice smoke ledger.");
      }
      return { status: "built", result, presence: smokePresence };
    } catch (smokeError) {
      if (!isCurrentProof()) {
        return { status: "stale" };
      }
      const message = smokeError instanceof Error ? smokeError.message : "Could not build voice smoke proof.";
      setError(message);
      addEvent({ label: "Voice smoke failed", detail: message, tone: "bad" });
      return { status: "failed", message };
    } finally {
      if (voiceProofActionInFlightRef.current === proofActionSnapshot) {
        voiceProofActionInFlightRef.current = null;
      }
      if (isCurrentProof()) {
        setVoiceProofLoading(null);
      }
      if (parentMutationSnapshot) {
        onVoiceProofMutationFinish?.(parentMutationSnapshot);
      }
    }
  }

  async function handleTimingLedger() {
    if (!runId) {
      setError("Create or restore a content run before building voice timing proof.");
      return;
    }
    if (voiceProofActionInFlightRef.current) {
      return;
    }
    const proofRunId = runId;
    const proofToken = voiceTimingSequenceRef.current + 1;
    voiceTimingSequenceRef.current = proofToken;
    const proofActionSnapshot = { kind: "timing" as const, runId: proofRunId, token: proofToken };
    voiceProofActionInFlightRef.current = proofActionSnapshot;
    const parentMutationSnapshot = onVoiceProofMutationStart?.("Building voice timing ledger");
    if (onVoiceProofMutationStart && !parentMutationSnapshot) {
      voiceProofActionInFlightRef.current = null;
      return;
    }
    const proofSnapshot = { runId: proofRunId, token: proofToken };
    const isCurrentProof = () =>
      isRunBoundRequestCurrent(
        proofSnapshot,
        currentRunIdRef.current,
        voiceTimingSequenceRef.current
      );
    setVoiceProofLoading("timing");
    setError("");
    try {
      const result = await buildRealtimeVoiceTimingLedger({ runId });
      if (!isCurrentProof()) {
        return;
      }
      setVoiceTiming(result);
      addEvent({
        label: "Voice timing ledger built",
        detail: result.summary,
        tone: result.status === "ready" ? "good" : result.status === "blocked" ? "bad" : "warn"
      });
      if (isCurrentProof()) {
        await onRunUpdated("Built the realtime voice timing ledger.");
      }
    } catch (timingError) {
      if (!isCurrentProof()) {
        return;
      }
      const message = timingError instanceof Error ? timingError.message : "Could not build voice timing proof.";
      setError(message);
      addEvent({ label: "Voice timing failed", detail: message, tone: "bad" });
    } finally {
      if (voiceProofActionInFlightRef.current === proofActionSnapshot) {
        voiceProofActionInFlightRef.current = null;
      }
      if (isCurrentProof()) {
        setVoiceProofLoading(null);
      }
      if (parentMutationSnapshot) {
        onVoiceProofMutationFinish?.(parentMutationSnapshot);
      }
    }
  }

  return (
    <section className="realtime-voice-panel" aria-label="OpenRouter Kokoro live voice session">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Live Voice</p>
          <h2>OpenRouter DeepSeek + Kokoro voice runtime</h2>
        </div>
        <span className={clsx("live-dot", isReady && "active")}>
          {isReady
            ? isRehearsalSession
              ? "Rehearsal ready"
              : "Live room joined"
            : status === "starting"
              ? "Preparing"
              : status === "joining"
                ? "Joining"
                : status === "blocked"
                  ? "Blocked"
                  : status === "error"
                    ? "Error"
                  : "Offline"}
        </span>
      </div>

      <div className="realtime-voice-grid">
        <label>
          <span>Runtime</span>
          <select value={provider} onChange={(event) => setProvider(event.target.value as VoiceProvider)} disabled={isReady}>
            {PROVIDERS.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Kokoro voice preset</span>
          <input
            value={voice}
            onChange={(event) => setVoice(event.target.value)}
            placeholder="Kokoro voice preset, e.g. af_heart"
            disabled={isReady}
          />
        </label>
      </div>

      <div className="voice-capability-row">
        <Radio size={16} aria-hidden="true" />
        <span>{providerCapability}</span>
      </div>

      {!runId && onCreateVoiceRun && (
        <form className="voice-run-starter" aria-label="Create a voice-first run" onSubmit={handleCreateVoiceRun}>
          <label>
            <span>Voice run brief</span>
            <textarea
              value={voiceRunGoal}
              onChange={(event) => setVoiceRunGoal(event.target.value)}
              placeholder="What should the agents help you make?"
              disabled={busy || voiceRunCreating}
              rows={3}
            />
          </label>
          <button className="primary-button" type="submit" disabled={!canCreateVoiceRun}>
            {voiceRunCreating ? (
              <RotateCw size={18} aria-hidden="true" />
            ) : (
              <PhoneCall size={18} aria-hidden="true" />
            )}
            Create voice run
          </button>
          <small>
            Creates the durable run first, then Live Voice can join the OpenRouter/Kokoro room.
          </small>
        </form>
      )}

      <div
        className={clsx("voice-stage-strip", `voice-stage-${voiceStage}`)}
        aria-label="Live voice state"
      >
        <div className="voice-stage-main">
          <Radio size={16} aria-hidden="true" />
          <span>Realtime state</span>
          <strong>{isRehearsalSession ? "Transcript rehearsal" : voiceStageDefinition.label}</strong>
          <small>
            {isRehearsalSession
              ? "Typed transcript route; no provider-backed audio loop is active."
              : voiceStageDefinition.description}
          </small>
        </div>
        <div className="voice-stage-signals" aria-label="Live voice signals">
          <small className={statusClass(liveRoomConnected ? "ready" : "missing")}>
            Room: {liveRoomConnected ? "connected" : "not connected"}
          </small>
          <small className={statusClass(microphonePublished ? "ready" : "missing")}>
            Mic: {microphoneStatusLabel(microphonePublished)}
          </small>
          <small className={statusClass(voicePresence?.status)}>
            Agent: {voicePresence?.status ?? "not observed"}
          </small>
          <small>Context: {contextPolicyLabel}</small>
          <small className={statusClass(cancellationProof.status === "failed" ? "failed" : cancellationProof.status === "idle" ? "missing" : "ready")}>
            Cancel: {cancellationProof.label}
          </small>
        </div>
        {cancellationProof.status !== "idle" && (
          <div className="voice-cancellation-proof" aria-label="Cancellation acknowledgement">
            <span>{cancellationProof.summary}</span>
            {cancellationProof.evidence.map((item) => (
              <small key={item}>{item}</small>
            ))}
          </div>
        )}
      </div>

      <div className="realtime-actions">
        <button className="primary-button" type="button" onClick={handleStart} disabled={!canStart}>
          {status === "starting" || status === "joining" ? (
            <RotateCw size={18} aria-hidden="true" />
          ) : (
            <PhoneCall size={18} aria-hidden="true" />
          )}
          {status === "starting"
            ? "Preparing runtime"
            : status === "joining"
              ? "Joining room"
              : isRehearsalSession
                ? "Rehearsal active"
                : provider === "local_rehearsal"
                ? "Start transcript rehearsal"
                : "Join voice room"}
        </button>
        <button
          className="secondary-button"
          type="button"
          onClick={handleToggleMicrophone}
          disabled={!liveRuntime || !isReady || isRehearsalSession || microphoneControlLoading}
        >
          {microphonePublished ? (
            <MicOff size={18} aria-hidden="true" />
          ) : (
            <Mic size={18} aria-hidden="true" />
          )}
          {microphoneControlLabel(microphonePublished, microphoneControlLoading)}
        </button>
        <button
          className="secondary-button"
          type="button"
          onClick={handleInterrupt}
          disabled={!liveSession || !isReady || interruptControlLoading}
        >
          <Scissors size={18} aria-hidden="true" />
          {interruptControlLoading ? "Interrupting" : "Interrupt"}
        </button>
        <button
          className="secondary-button"
          type="button"
          onClick={handleStop}
          disabled={!liveSession || status === "stopping"}
        >
          <PhoneOff size={18} aria-hidden="true" />
          Stop
        </button>
      </div>

      <div className="voice-transcript-grid" aria-label="Live voice captions">
        <article className={clsx(`voice-caption-${liveTranscript.userStatus}`)}>
          <div>
            <Mic size={16} aria-hidden="true" />
            <span>You</span>
            <strong>{liveTranscript.userStatus}</strong>
          </div>
          <p>{liveTranscript.userCaption}</p>
        </article>
        <article className={clsx(`voice-caption-${liveTranscript.assistantStatus}`)}>
          <div>
            <Volume2 size={16} aria-hidden="true" />
            <span>Agent</span>
            <strong>{liveTranscript.assistantStatus}</strong>
          </div>
          <p>{liveTranscript.assistantCaption}</p>
        </article>
      </div>

      {!isRehearsalSession && (
        <form className="voice-live-text-turn" aria-label="Send text to live voice agent" onSubmit={handleSendLiveTextTurn}>
          <label>
            <span>Text into live agent</span>
            <input
              value={liveTextTurn}
              onChange={(event) => setLiveTextTurn(event.target.value)}
              placeholder={
                liveTextTurnAgentReady
                  ? "Type while the mic stays available..."
                  : liveRoomConnected
                    ? "Waiting for the OpenRouter/Kokoro agent participant..."
                    : "Join the voice room to send typed turns"
              }
              disabled={!liveTextTurnAgentReady || liveTextTurnLoading}
            />
          </label>
          <button className="secondary-button" type="submit" disabled={!canSendLiveTextTurn}>
            {liveTextTurnLoading ? (
              <RotateCw size={16} aria-hidden="true" />
            ) : (
              <Send size={16} aria-hidden="true" />
            )}
            {liveTextTurnStatusLabel(liveTextTurnLoading)}
          </button>
        </form>
      )}

      <details className="voice-diagnostics-disclosure" aria-label="Voice setup details" open={Boolean(runId)}>
        <summary>
          <span>Setup details</span>
          <strong className={statusClass(voiceSetupBlocker?.status ?? "ready")}>
            {voiceSetupBlocker ? voiceSetupBlocker.label : "Ready"}
          </strong>
          <small>
            {voiceSetupBlocker
              ? voiceSetupBlocker.nextAction ?? voiceSetupBlocker.detail
              : "Runtime, provider, proof, and process checks are available here."}
          </small>
        </summary>

      <div className="voice-readiness-panel" aria-label="Voice runtime readiness">
        <div className="voice-readiness-header">
          <div>
            <ShieldCheck size={16} aria-hidden="true" />
            <span>Runtime readiness</span>
          </div>
          <strong className={clsx(readiness?.status && `status-${readiness.status}`)}>
            {readinessLoading ? "Checking" : readiness?.status ?? "Unknown"}
          </strong>
          <button
            className="secondary-button"
            type="button"
            onClick={() => void handleRuntimePreflight()}
            disabled={readinessLoading || isReady}
          >
            <RotateCw size={16} aria-hidden="true" />
            Runtime preflight
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={handleSetupCheck}
            disabled={
              setupCheckLoading ||
              readinessLoading ||
              processLoading !== null ||
              liveKitProcessLoading !== null
            }
          >
            <ClipboardCheck size={16} aria-hidden="true" />
            Check setup
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={handleResolveVoiceSetup}
            disabled={voiceSetupActionDisabled}
          >
            <PhoneCall size={16} aria-hidden="true" />
            {voiceSetupActionLabel(voiceSetupAction)}
          </button>
        </div>
        <div className="voice-setup-checklist" aria-label="Voice launch checklist">
          <div className="voice-setup-summary">
            <span>Launch checklist</span>
            <strong className={statusClass(voiceSetupBlocker?.status ?? "ready")}>
              {voiceSetupBlocker ? voiceSetupBlocker.label : "Ready"}
            </strong>
            <small>
              {voiceSetupBlocker
                ? voiceSetupBlocker.nextAction ?? voiceSetupBlocker.detail
                : "All required voice launch checks are ready."}
            </small>
          </div>
          <div className="voice-setup-steps">
            {voiceSetupSteps.map((step) => (
              <article key={step.id} className={clsx(`status-${step.status}`)}>
                <span>{step.label}</span>
                <strong>{step.status.replace("_", " ")}</strong>
                <small>{step.detail}</small>
                {step.nextAction && <small className="voice-readiness-next">{step.nextAction}</small>}
              </article>
            ))}
          </div>
        </div>
        <div className="voice-readiness-checks">
          {visibleReadinessChecks.map((check) => (
            <article key={check.check_id} className={clsx(`status-${check.status}`)}>
              <div className="voice-readiness-check-title">
                <span>{check.label}</span>
                <strong>{check.status}</strong>
              </div>
              {readinessEvidence(check) && <small>{readinessEvidence(check)}</small>}
              {readinessMissingEnv(check) && (
                <small className="voice-readiness-missing">{readinessMissingEnv(check)}</small>
              )}
              {readinessNextAction(check) && (
                <small className="voice-readiness-next">{readinessNextAction(check)}</small>
              )}
            </article>
          ))}
        </div>
        {edgeReadiness?.evidence[0] && <p>{edgeReadiness.evidence[0]}</p>}
        <div className="voice-agent-process-row">
          <div>
            <span>Local LiveKit transport</span>
            <strong className={statusClass(liveKitProcess?.status)}>
              {liveKitProcessLoading === "status" ? "checking" : liveKitProcess?.status ?? "unknown"}
            </strong>
            <small>{liveKitProcessDetail}</small>
          </div>
          <div>
            <select
              value={liveKitMode}
              onChange={(event) => setLiveKitMode(event.target.value as LocalLiveKitProcessMode)}
              disabled={liveKitProcessLoading !== null || liveKitProcessRunning || isReady}
              aria-label="Local LiveKit start mode"
            >
              <option value="native">Native</option>
              <option value="compose">Compose</option>
            </select>
            <button
              className="secondary-button"
              type="button"
              onClick={() => {
                void handleStartLiveKitProcess();
              }}
              disabled={liveKitProcessLoading !== null || liveKitProcessRunning || isReady}
            >
              <PhoneCall size={16} aria-hidden="true" />
              {liveKitProcessLoading === "start" ? "Starting" : "Start LiveKit"}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={handleStopLiveKitProcess}
              disabled={liveKitProcessLoading !== null || !liveKitProcessRunning}
            >
              <PhoneOff size={16} aria-hidden="true" />
              {liveKitProcessLoading === "stop" ? "Stopping" : "Stop LiveKit"}
            </button>
          </div>
        </div>
        <div className="voice-agent-process-row">
          <div>
            <span>Local agent process</span>
            <strong className={statusClass(voiceProcess?.status)}>
              {processLoading === "status" ? "checking" : voiceProcess?.status ?? "unknown"}
            </strong>
            <small>{processDetail}</small>
          </div>
          <div>
            <button
              className="secondary-button"
              type="button"
              onClick={() => void handleStartProcess()}
              disabled={processLoading !== null || processRunning || isReady}
            >
              <PhoneCall size={16} aria-hidden="true" />
              {processLoading === "start" ? "Starting" : "Start agent"}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={handleStopProcess}
              disabled={processLoading !== null || !processRunning}
            >
              <PhoneOff size={16} aria-hidden="true" />
              {processLoading === "stop" ? "Stopping" : "Stop agent"}
            </button>
          </div>
        </div>
      </div>

      <div className="voice-runtime-contract" aria-label="Voice runtime contract">
        <article>
          <Mic size={16} aria-hidden="true" />
          <span>Transport</span>
          <p>{transportFramework === "livekit" ? "LiveKit production media transport" : transportFramework}</p>
          {livekitUrl && <small>{livekitUrl}</small>}
          {roomName && <small>Room: {roomName}</small>}
        </article>
        <article>
          <ShieldCheck size={16} aria-hidden="true" />
          <span>Grant</span>
          <p>
            {isRehearsalSession
              ? "No media token; transcript-only dry-run proof."
              : hasTransportToken
                ? "Ephemeral room token received; not persisted."
                : "Waiting for LiveKit token."}
          </p>
          {participantIdentity && <small>Participant: {participantIdentity}</small>}
        </article>
        <article>
          <Volume2 size={16} aria-hidden="true" />
          <span>Barge-in</span>
          <p>Rust VAD cancels OpenRouter/Kokoro output and clears speech buffers.</p>
        </article>
        <article>
          <Radio size={16} aria-hidden="true" />
          <span>Agent participant</span>
          <p className={statusClass(voicePresence?.status)}>
            {voicePresence?.status ?? "Not observed"}
          </p>
          <small>{presenceDetail}</small>
          {voicePresence?.livekit_sender_identity && (
            <small>Sender: {voicePresence.livekit_sender_identity}</small>
          )}
        </article>
      </div>

      {provider === "local_rehearsal" && (
        <div className="voice-rehearsal-panel" aria-label="Transcript rehearsal controls">
          <div>
            <Radio size={16} aria-hidden="true" />
            <span>Transcript rehearsal</span>
            <strong>Not production audio</strong>
          </div>
          <p>
            Routes a typed transcript through the realtime session and specialist handoff contracts. It does not prove LiveKit media, OpenRouter dialogue, or Kokoro speech output.
          </p>
          <textarea
            value={rehearsalTranscript}
            onChange={(event) => setRehearsalTranscript(event.target.value)}
            disabled={!canRouteRehearsalTurn || rehearsalLoading}
            rows={3}
          />
          <button
            className="secondary-button"
            type="button"
            onClick={handleRehearsalTurn}
            disabled={!canRouteRehearsalTurn || rehearsalLoading}
          >
            {rehearsalLoading ? <RotateCw size={16} aria-hidden="true" /> : <Radio size={16} aria-hidden="true" />}
            {rehearsalLoading ? "Routing rehearsal" : "Route rehearsal turn"}
          </button>
        </div>
      )}

      <div className="voice-proof-panel" aria-label="Voice proof ledgers">
        <div className="voice-proof-header">
          <div>
            <ClipboardCheck size={16} aria-hidden="true" />
            <span>Voice proof</span>
          </div>
          <label className="voice-live-toggle">
            <input
              type="checkbox"
              checked={liveSmoke}
              onChange={(event) => setLiveSmoke(event.target.checked)}
              disabled={voiceProofLoading !== null}
            />
            <span>Live smoke</span>
          </label>
        </div>
        <div className="voice-provider-release-gate" aria-label="Provider-backed voice release gate">
          <div className="voice-live-proof-path" aria-label="Live voice proof path">
            <div className="voice-live-proof-summary">
              <div>
                <ShieldCheck size={15} aria-hidden="true" />
                <span>Live voice proof path</span>
              </div>
              <strong className={statusClass(liveVoiceProofPath.status)}>
                {liveVoiceProofPath.label}
              </strong>
              <small>{liveVoiceProofPath.summary}</small>
              {liveVoiceProofPath.nextAction && (
                <small className="voice-readiness-next">{liveVoiceProofPath.nextAction}</small>
              )}
            </div>
            {liveVoiceProofPath.primaryActionLabel && (
              <button
                className="secondary-button voice-live-proof-action"
                type="button"
                onClick={() => {
                  void handleLiveVoiceProofPathAction();
                }}
                disabled={liveVoiceProofPathActionDisabled}
              >
                {voiceProofLoading !== null || readinessLoading || providerReadinessLoading ? (
                  <RotateCw size={16} aria-hidden="true" />
                ) : (
                  <ShieldCheck size={16} aria-hidden="true" />
                )}
                {liveVoiceProofPath.primaryActionLabel}
              </button>
            )}
            <div className="voice-live-proof-steps">
              {liveVoiceProofPath.steps.map((step) => (
                <article key={step.id} className={clsx(`status-${step.status}`)}>
                  <span>{step.label}</span>
                  <strong>{step.status.replaceAll("_", " ")}</strong>
                  <small>{step.detail}</small>
                  {step.nextAction && <small className="voice-readiness-next">{step.nextAction}</small>}
                </article>
              ))}
            </div>
          </div>
          <div className="voice-provider-release-summary">
            <div>
              <ShieldCheck size={15} aria-hidden="true" />
              <span>{providerReleaseGate.label}</span>
            </div>
            <strong className={statusClass(providerReleaseGate.status)}>
              {providerReadinessLoading ? "checking" : providerReleaseGate.status.replace("_", " ")}
            </strong>
            <small>{providerReleaseGate.summary}</small>
            {providerReleaseGate.missingEnv.length > 0 && (
              <small className="voice-readiness-missing">
                Missing provider env: {providerReleaseGate.missingEnv.join(", ")}
              </small>
            )}
            {localLiveKitDevConfigNeeded && (
              <button
                className="secondary-button voice-local-livekit-dev-button"
                type="button"
                onClick={() => void handleConfigureLocalLiveKitDev()}
                disabled={localLiveKitDevConfigBusy}
              >
                <Radio size={14} aria-hidden="true" />
                {localLiveKitDevConfigSaving ? "Configuring" : "Use local LiveKit dev defaults"}
              </button>
            )}
          </div>
          {providerReleaseGate.secretFileGuidance.length > 0 && (
            <div className="voice-secret-file-list" aria-label="Secret file diagnostics">
              {providerReleaseGate.secretFileGuidance.map((secretFile) => (
                <article key={`${secretFile.fileEnvName}-${secretFile.envName}`}>
                  <span>{secretFile.fileEnvName}</span>
                  <strong className={statusClass(secretFile.status)}>
                    {secretFile.status.replace("_", " ")}
                  </strong>
                  <small>{secretFile.detail}</small>
                  <small className="voice-readiness-next">{secretFile.action}</small>
                  {secretFile.path && <small>{secretFile.path}</small>}
                  {secretFileNeedsLocalValue(secretFile.status) && canSaveLocalSecret(secretFile.envName) && (
                    <div className="voice-secret-file-form">
                      <label>
                        <span>{secretFile.envName}</span>
                        <input
                          type="password"
                          value={secretValues[secretFile.envName] ?? ""}
                          disabled={localLiveKitDevConfigSaving}
                          onChange={(event) =>
                            setSecretValues((current) => ({
                              ...current,
                              [secretFile.envName]: event.target.value
                            }))
                          }
                          autoComplete="off"
                          placeholder="Paste value"
                        />
                      </label>
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => void handleSaveLocalSecretFile(secretFile.envName)}
                        disabled={localLiveKitDevConfigSaving || secretSaving === secretFile.envName}
                      >
                        <KeyRound size={14} aria-hidden="true" />
                        {secretSaving === secretFile.envName ? "Saving" : "Save locally"}
                      </button>
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
          {localProviderConfigNames.length > 0 && (
            <div className="voice-provider-config-list" aria-label="Provider endpoint setup">
              {localProviderConfigNames.map((envName) => (
                <article key={envName}>
                  <span>{envName}</span>
                  <strong>missing</strong>
                  <small>{providerConfigAction(envName)}</small>
                  <div className="voice-provider-config-form">
                    <label>
                      <span>Endpoint URL</span>
                      <input
                        type="url"
                        value={providerConfigValues[envName] ?? ""}
                        disabled={localLiveKitDevConfigSaving || providerConfigSaving !== null}
                        onChange={(event) =>
                          setProviderConfigValues((current) => ({
                            ...current,
                            [envName]: event.target.value
                          }))
                        }
                        autoComplete="off"
                        placeholder={providerConfigPlaceholder(envName)}
                      />
                    </label>
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => void handleSaveLocalProviderConfig(envName)}
                      disabled={localLiveKitDevConfigSaving || providerConfigSaving !== null}
                    >
                      <KeyRound size={14} aria-hidden="true" />
                      {providerConfigSaving === envName ? "Saving" : "Save endpoint"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
          <div className="voice-provider-release-checks">
            {providerReleaseGate.checks.map((check) => (
              <article key={check.id} className={clsx(`status-${check.status}`)}>
                <span>{check.label}</span>
                <strong>{check.status.replace("_", " ")}</strong>
                <small>{check.detail}</small>
                {check.nextAction && <small className="voice-readiness-next">{check.nextAction}</small>}
              </article>
            ))}
          </div>
          <button
            className="secondary-button"
            type="button"
            onClick={() => void handleProviderReadinessRefresh()}
            disabled={providerReadinessLoading}
          >
            <RotateCw size={16} aria-hidden="true" />
            Provider readiness
          </button>
        </div>
        <div className="voice-proof-grid">
          <article>
            <span>Runtime smoke</span>
            <strong className={statusClass(voiceSmoke?.status)}>{voiceSmoke?.status ?? "Not run"}</strong>
            <small>
              {voiceSmoke
                ? `${voiceSmoke.passed_count}/${voiceSmoke.step_count} passed`
                : "No provider smoke ledger yet"}
            </small>
            {streamingSmokeStep?.status && <small>OpenRouter/Kokoro: {streamingSmokeStep.status}</small>}
            {smokeBlocker && <small>{smokeBlocker}</small>}
            <div
              className={clsx("voice-streaming-proof", `voice-streaming-proof-${streamingProviderProof.status}`)}
              data-smoke-proof-id="openrouter-kokoro-transport"
              aria-label="OpenRouter Kokoro transport proof"
            >
              <span>{streamingProviderProof.title}</span>
              <small>{streamingProviderProof.summary}</small>
              {streamingProviderProof.evidence.map((item) => (
                <small key={item}>{item}</small>
              ))}
              {streamingProviderProof.metrics.length > 0 && (
                <div className="voice-streaming-metrics" aria-label="OpenRouter Kokoro latency proof">
                  {streamingProviderProof.metrics.map((metric) => (
                    <small key={metric.label}>
                      {metric.label}: {metric.value}
                    </small>
                  ))}
                </div>
              )}
            </div>
            <div
              className={clsx("voice-audio-proof", `voice-audio-proof-${audioFixtureProof.status}`)}
              data-smoke-proof-id="openrouter-kokoro-captured-audio"
              aria-label="Captured audio proof"
            >
              <span>{audioFixtureProof.title}</span>
              <small>{audioFixtureProof.summary}</small>
              {audioFixtureProof.evidence.map((item) => (
                <small key={item}>{item}</small>
              ))}
            </div>
          </article>
          <article>
            <span>Timing ledger</span>
            <strong className={statusClass(voiceTiming?.status)}>{voiceTiming?.status ?? "Not run"}</strong>
            <small>
              {voiceTiming
                ? `${voiceTiming.measured_stage_count}/${voiceTiming.stages.length} stages measured`
                : "No timing ledger yet"}
            </small>
            {timingGap && <small>{timingGap}</small>}
            {timingStageProofs.length > 0 && (
              <div className="voice-timing-proof" aria-label="Realtime voice timing proof">
                {timingStageProofs.map((stage) => (
                  <div key={stage.stageId} className={clsx("voice-timing-stage", `status-${stage.status}`)}>
                    <span>{stage.title}</span>
                    <strong>{stage.latency || stage.status}</strong>
                    <small>{stage.detail}</small>
                  </div>
                ))}
              </div>
            )}
            {timingTurnProof && (
              <div className="voice-timing-turn" aria-label="Latest voice turn timing">
                <span>{timingTurnProof.title}</span>
                {timingTurnProof.metrics.map((metric) => (
                  <small key={metric.label}>
                    {metric.label}: {metric.value}
                  </small>
                ))}
              </div>
            )}
          </article>
        </div>
        <div className="voice-proof-actions">
          <button
            className="secondary-button"
            type="button"
            onClick={() => {
              void handleVoiceSmoke();
            }}
            disabled={!runId || voiceProofLoading !== null}
          >
            {voiceProofLoading === "smoke" ? (
              <RotateCw size={16} aria-hidden="true" />
            ) : (
              <Gauge size={16} aria-hidden="true" />
            )}
            Runtime smoke
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={handleTimingLedger}
            disabled={!runId || voiceProofLoading !== null}
          >
            {voiceProofLoading === "timing" ? (
              <RotateCw size={16} aria-hidden="true" />
            ) : (
              <ClipboardCheck size={16} aria-hidden="true" />
            )}
            Timing ledger
          </button>
        </div>
      </div>
      </details>

      {error && (
        <p className="voice-message" aria-live="polite">
          {error}
        </p>
      )}

      <div className="voice-event-list" aria-label="Live voice event log">
        {events.length === 0 ? (
          <p className="muted">
            This panel joins a LiveKit room from an ephemeral backend grant. OpenRouter DeepSeek handles live dialogue reasoning and Kokoro produces speech.
          </p>
        ) : (
          events.map((event) => (
            <article key={event.id} className={clsx(event.tone && `tone-${event.tone}`)}>
              <strong>{event.label}</strong>
              {event.detail && <span>{event.detail}</span>}
            </article>
          ))
        )}
      </div>
      <div ref={remoteAudioRootRef} className="remote-audio-sink" aria-hidden="true" />
    </section>
  );
}
