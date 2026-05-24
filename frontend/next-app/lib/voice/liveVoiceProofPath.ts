import type { RealtimeVoiceTimingLedgerResult } from "@/lib/api/types";
import type { VoiceProviderReleaseGate } from "./providerReadiness";
import type {
  VoiceAudioFixtureProof,
  VoiceStreamingProviderProof
} from "./providerSmoke";
import { buildVoiceTimingGap, buildVoiceTimingIssue } from "./timingLedger";

export type LiveVoiceProofPathStatus =
  | "ready"
  | "blocked"
  | "needs_runtime"
  | "needs_live_smoke"
  | "needs_captured_audio"
  | "needs_timing"
  | "unknown";

export type LiveVoiceProofPathStep = {
  id: string;
  label: string;
  status: LiveVoiceProofPathStatus;
  detail: string;
  nextAction?: string;
};

export type LiveVoiceProofPathAction =
  | "refresh_provider_readiness"
  | "run_runtime_preflight"
  | "join_room"
  | "probe_presence"
  | "run_live_smoke"
  | "build_timing_ledger";

export type LiveVoiceProofPath = {
  status: LiveVoiceProofPathStatus;
  label: string;
  summary: string;
  nextAction?: string;
  primaryAction?: LiveVoiceProofPathAction;
  primaryActionLabel?: string;
  steps: LiveVoiceProofPathStep[];
};

type LiveVoiceProofPathInput = {
  providerReleaseGate: VoiceProviderReleaseGate;
  audioFixtureProof: VoiceAudioFixtureProof;
  streamingProviderProof: VoiceStreamingProviderProof;
  timing: RealtimeVoiceTimingLedgerResult | null | undefined;
};

export function buildLiveVoiceProofPath(
  input: LiveVoiceProofPathInput
): LiveVoiceProofPath {
  const steps = [
    providerGateStep(input.providerReleaseGate),
    capturedAudioStep(input.audioFixtureProof),
    streamingTransportStep(input.streamingProviderProof),
    timingLedgerStep(input.timing)
  ];
  const firstOpenStep = steps.find((step) => step.status !== "ready");
  const status = firstOpenStep?.status ?? "ready";

  return {
    status,
    label: liveVoiceProofPathLabel(status),
    summary:
      status === "ready"
        ? "Captured microphone audio, Gemma streaming, Kokoro first audio, and realtime timing are proven for this run."
        : firstOpenStep?.detail ?? "Live voice proof has not been evaluated yet.",
    nextAction: firstOpenStep?.nextAction,
    primaryAction: firstOpenStep ? liveVoiceProofPathAction(firstOpenStep) : undefined,
    primaryActionLabel: firstOpenStep
      ? liveVoiceProofPathActionLabel(liveVoiceProofPathAction(firstOpenStep))
      : undefined,
    steps
  };
}

function providerGateStep(gate: VoiceProviderReleaseGate): LiveVoiceProofPathStep {
  const firstOpenCheck = gate.checks.find((check) => check.status !== "ready");
  return {
    id: firstOpenCheck ? `provider-release-gate:${firstOpenCheck.id}` : "provider-release-gate",
    label: "Provider route",
    status: gate.status,
    detail:
      gate.status === "ready"
        ? "Gemma, realtime voice, web search, reranker, runtime, participant, and live smoke gates are ready."
        : gate.summary,
    nextAction: firstOpenCheck?.nextAction
  };
}

function capturedAudioStep(proof: VoiceAudioFixtureProof): LiveVoiceProofPathStep {
  if (proof.status === "captured") {
    return {
      id: "captured-audio",
      label: "Captured audio",
      status: "ready",
      detail: proof.summary
    };
  }
  if (proof.status === "blocked" || proof.status === "failed") {
    return {
      id: "captured-audio",
      label: "Captured audio",
      status: "blocked",
      detail: proof.summary,
      nextAction: proof.evidence.find((item) => item.startsWith("Next:"))?.replace(/^Next: /, "")
    };
  }
  return {
    id: "captured-audio",
    label: "Captured audio",
    status: "needs_captured_audio",
    detail:
      proof.status === "synthetic"
        ? "Runtime smoke used synthetic audio; true voice-to-voice proof still needs captured microphone PCM from the LiveKit room."
        : proof.summary,
    nextAction: "Speak in the active LiveKit room, wait for the turn to persist, then rerun live Runtime smoke."
  };
}

function streamingTransportStep(
  proof: VoiceStreamingProviderProof
): LiveVoiceProofPathStep {
  if (proof.status === "passed") {
    return {
      id: "gemma-kokoro-streaming",
      label: "Gemma/Kokoro streaming",
      status: "ready",
      detail: proof.summary
    };
  }
  if (proof.status === "blocked" || proof.status === "failed") {
    return {
      id: "gemma-kokoro-streaming",
      label: "Gemma/Kokoro streaming",
      status: "blocked",
      detail: proof.summary,
      nextAction: proof.evidence.find((item) => item.startsWith("Next:"))?.replace(/^Next: /, "")
    };
  }
  return {
    id: "gemma-kokoro-streaming",
    label: "Gemma/Kokoro streaming",
    status: "needs_live_smoke",
    detail: proof.summary,
    nextAction: "Enable Live smoke and run Runtime smoke after the room has captured a voice turn."
  };
}

function timingLedgerStep(
  timing: RealtimeVoiceTimingLedgerResult | null | undefined
): LiveVoiceProofPathStep {
  if (!timing) {
    return {
      id: "timing-ledger",
      label: "Realtime timing",
      status: "needs_timing",
      detail: "No realtime timing ledger has been built for this run.",
      nextAction: "Run Timing ledger after a provider-backed voice turn."
    };
  }
  if (timing.status === "ready" && timing.missing_stage_count === 0) {
    return {
      id: "timing-ledger",
      label: "Realtime timing",
      status: "ready",
      detail: `${timing.measured_stage_count}/${timing.stages.length} realtime stages are measured.`
    };
  }
  const failedTurn = timing.turns.find((turn) => turn.failure_reason);
  const timingGap = buildVoiceTimingGap(timing);
  const timingIssue = buildVoiceTimingIssue(timing);
  return {
    id: "timing-ledger",
    label: "Realtime timing",
    status: failedTurn ? "blocked" : "needs_timing",
    detail: failedTurn?.failure_reason ?? timingIssue ?? timing.summary,
    nextAction:
      timingGap ??
      "Persist the missing LiveKit/Gemma/Kokoro events and rerun Timing ledger."
  };
}

function liveVoiceProofPathLabel(status: LiveVoiceProofPathStatus) {
  switch (status) {
    case "ready":
      return "Ready";
    case "blocked":
      return "Blocked";
    case "needs_runtime":
      return "Needs runtime";
    case "needs_live_smoke":
      return "Needs live smoke";
    case "needs_captured_audio":
      return "Needs captured audio";
    case "needs_timing":
      return "Needs timing";
    case "unknown":
      return "Unknown";
  }
}

function liveVoiceProofPathAction(
  step: LiveVoiceProofPathStep
): LiveVoiceProofPathAction | undefined {
  if (step.status === "ready") {
    return undefined;
  }
  if (step.id.startsWith("provider-release-gate:")) {
    const checkId = step.id.split(":")[1] ?? "";
    if (["provider-readiness", "gemma-primary", "realtime-provider", "web-search", "reranker"].includes(checkId)) {
      return "refresh_provider_readiness";
    }
    if (checkId === "runtime") {
      return "run_runtime_preflight";
    }
    if (checkId === "active-session") {
      return "join_room";
    }
    if (checkId === "presence") {
      return "probe_presence";
    }
    if (checkId === "provider-recovery" || checkId === "live-smoke") {
      return "run_live_smoke";
    }
    return "refresh_provider_readiness";
  }
  if (step.id === "captured-audio" || step.id === "gemma-kokoro-streaming") {
    return "run_live_smoke";
  }
  if (step.id === "timing-ledger") {
    return "build_timing_ledger";
  }
  return undefined;
}

function liveVoiceProofPathActionLabel(action: LiveVoiceProofPathAction | undefined) {
  switch (action) {
    case "refresh_provider_readiness":
      return "Refresh provider readiness";
    case "run_runtime_preflight":
      return "Run runtime preflight";
    case "join_room":
      return "Join voice room";
    case "probe_presence":
      return "Probe agent presence";
    case "run_live_smoke":
      return "Run live smoke";
    case "build_timing_ledger":
      return "Build timing ledger";
    case undefined:
      return undefined;
  }
}
