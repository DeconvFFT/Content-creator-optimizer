import type {
  RealtimeVoiceTimingLedgerResult,
  RealtimeVoiceTimingStageEntry,
  RealtimeVoiceTimingTurnEntry
} from "@/lib/api/types";

export type VoiceTimingStageProof = {
  stageId: string;
  title: string;
  status: string;
  latency: string;
  detail: string;
};

export type VoiceTimingTurnMetric = {
  label: string;
  value: string;
};

export type VoiceTimingTurnProof = {
  title: string;
  metrics: VoiceTimingTurnMetric[];
};

const MEDIA_BRIDGE_STAGE_ID = "livekit_audio_track_bridge";
const MEDIA_BRIDGE_DETAIL =
  "The backend agent has not confirmed that the active LiveKit microphone track is bridged into Rust VAD.";
const MEDIA_BRIDGE_NEXT_ACTION =
  "Speak in the active LiveKit room, wait for the backend agent to subscribe to the microphone track, then rebuild the Timing ledger.";

type TurnMetricKey = keyof Pick<
  RealtimeVoiceTimingTurnEntry,
  | "speech_start_to_turn_commit_ms"
  | "turn_commit_to_agent_turn_ms"
  | "turn_start_to_gemma_start_ms"
  | "gemma_start_to_first_text_ms"
  | "gemma_start_to_first_audio_ms"
  | "turn_start_to_first_audio_ms"
  | "barge_in_to_cancelled_ms"
>;

const TURN_METRIC_LABELS: Array<[TurnMetricKey, string]> = [
  ["speech_start_to_turn_commit_ms", "Speech -> turn commit"],
  ["turn_commit_to_agent_turn_ms", "Turn commit -> agent"],
  ["turn_start_to_gemma_start_ms", "Agent -> OpenRouter"],
  ["gemma_start_to_first_text_ms", "OpenRouter -> first text"],
  ["gemma_start_to_first_audio_ms", "OpenRouter -> first audio"],
  ["turn_start_to_first_audio_ms", "Agent -> first audio"],
  ["barge_in_to_cancelled_ms", "Barge-in -> stopped"]
];

export function formatLatencyMs(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "";
  }
  if (value < 0) {
    return "invalid latency";
  }
  if (value < 10) {
    return `${value.toFixed(1)} ms`;
  }
  if (value < 1000) {
    return `${Math.round(value)} ms`;
  }
  const seconds = value / 1000;
  const label = seconds >= 10 ? Math.round(seconds).toString() : seconds.toFixed(1);
  return `${label} s`;
}

export function buildVoiceTimingStageProofs(
  timing: RealtimeVoiceTimingLedgerResult | null | undefined
): VoiceTimingStageProof[] {
  if (!timing) {
    return [];
  }
  return timing.stages.map((stage) => buildStageProof(stage));
}

export function buildVoiceTimingGap(
  timing: RealtimeVoiceTimingLedgerResult | null | undefined
): string | null {
  if (!timing) {
    return null;
  }
  if (timing.status === "failed" || timing.stages.some((stage) => stage.status === "failed")) {
    return (
      first(timing.stages.filter((stage) => stage.status === "failed").flatMap((stage) => stage.missing_evidence)) ??
      first(timing.recommended_next_actions) ??
      null
    );
  }
  const mediaBridge = timing.stages.find(
    (stage) => stage.stage_id === MEDIA_BRIDGE_STAGE_ID
  );
  if (mediaBridge && mediaBridge.status !== "measured") {
    return MEDIA_BRIDGE_NEXT_ACTION;
  }
  return (
    first(timing.recommended_next_actions) ??
    first(timing.stages.flatMap((stage) => stage.missing_evidence)) ??
    null
  );
}

export function buildVoiceTimingIssue(
  timing: RealtimeVoiceTimingLedgerResult | null | undefined
): string | null {
  if (!timing) {
    return null;
  }
  const mediaBridge = timing.stages.find(
    (stage) => stage.stage_id === MEDIA_BRIDGE_STAGE_ID
  );
  if (mediaBridge && mediaBridge.status !== "measured") {
    return MEDIA_BRIDGE_DETAIL;
  }
  return first(timing.stages.flatMap((stage) => stage.missing_evidence)) ?? null;
}

export function buildVoiceTimingTurnProof(
  timing: RealtimeVoiceTimingLedgerResult | null | undefined
): VoiceTimingTurnProof | null {
  if (!timing || timing.turns.length === 0) {
    return null;
  }
  const turn = timing.turns[timing.turns.length - 1];
  const title = turn.response_id
    ? `Latest voice turn ${turn.response_id}`
    : turn.turn_id
      ? `Latest voice turn ${turn.turn_id}`
      : "Latest voice turn";
  const metrics = TURN_METRIC_LABELS.map(([key, label]) => ({
    label,
    value: formatLatencyMs(turn[key])
  })).filter((item) => item.value);

  return metrics.length > 0 ? { title, metrics } : null;
}

function buildStageProof(stage: RealtimeVoiceTimingStageEntry): VoiceTimingStageProof {
  const latency = formatLatencyMs(stage.latency_ms);
  const detail = stageDetail(stage);
  return {
    stageId: stage.stage_id,
    title: stage.title,
    status: stage.status,
    latency,
    detail
  };
}

function stageDetail(stage: RealtimeVoiceTimingStageEntry): string {
  if (stage.stage_id === MEDIA_BRIDGE_STAGE_ID && stage.status !== "measured") {
    return MEDIA_BRIDGE_DETAIL;
  }
  const detail =
    first(stage.evidence) ??
    first(stage.missing_evidence) ??
    (stage.status === "measured" ? "Measured durable voice-loop evidence." : "No durable evidence yet.");
  return detail;
}

function first(items: string[]): string | undefined {
  return items.find((item) => item.trim().length > 0);
}
