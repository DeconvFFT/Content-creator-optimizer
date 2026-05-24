import type {
  VoiceRuntimeReadinessCheck,
  VoiceRuntimeReadinessResult
} from "@/lib/api/types";

export type RuntimePreflightBlocker = {
  detail: string;
  nextAction: string;
};

export type VoiceReadinessRefreshOptions = {
  preflightEdge?: boolean;
  preflightAgent?: boolean;
  preflightLivekit?: boolean;
  preflightTts?: boolean;
  preflightGemma?: boolean;
  shouldApply?: () => boolean;
};

export const RUNTIME_PREFLIGHT_READINESS_OPTIONS: VoiceReadinessRefreshOptions = {
  preflightEdge: true,
  preflightAgent: true,
  preflightLivekit: true,
  preflightTts: true,
  preflightGemma: true
};

export const LIVEKIT_TRANSPORT_PREFLIGHT_OPTIONS: VoiceReadinessRefreshOptions = {
  preflightLivekit: true
};

export function voiceReadinessRefreshStrength(options: VoiceReadinessRefreshOptions): number {
  return [
    options.preflightEdge,
    options.preflightAgent,
    options.preflightLivekit,
    options.preflightTts,
    options.preflightGemma
  ].filter(Boolean).length;
}

export type VoiceReadinessAppliedState = {
  epoch: number;
  strength: number;
};

export function shouldApplyVoiceReadinessResult(
  current: VoiceReadinessAppliedState,
  next: VoiceReadinessAppliedState
): boolean {
  return next.epoch > current.epoch || (
    next.epoch === current.epoch &&
    next.strength >= current.strength
  );
}

function gemmaCheck(
  readiness: VoiceRuntimeReadinessResult | null
): VoiceRuntimeReadinessCheck | null {
  return readiness?.checks.find((check) => check.check_id === "gemma-audio-reasoning") ?? null;
}

function kokoroCheck(
  readiness: VoiceRuntimeReadinessResult | null
): VoiceRuntimeReadinessCheck | null {
  return readiness?.checks.find((check) => check.check_id === "kokoro-tts") ?? null;
}

function positiveNumber(value: unknown): boolean {
  return typeof value === "number" && Number.isFinite(value) && value > 0;
}

export function hostedGemmaPreflightBlocker(
  readiness: VoiceRuntimeReadinessResult | null
): RuntimePreflightBlocker | null {
  if (
    readiness?.status !== "ready" &&
    readiness?.status !== "degraded"
  ) {
    return null;
  }
  const check = gemmaCheck(readiness);
  if (check?.metadata.gemma_audio_endpoint_configured !== true) {
    return null;
  }
  if (
    readiness?.preflight_gemma === true &&
    check.metadata.gemma_preflight_performed === true &&
    positiveNumber(check.metadata.gemma_preflight_text_chars)
  ) {
    return null;
  }
  return {
    detail:
      "Gemma 4 E4B audio endpoint preflight has not run for this runtime check. Run Runtime preflight so the endpoint accepts audio and returns a text delta before claiming voice readiness.",
    nextAction: "Run Runtime preflight."
  };
}

export function hostedKokoroPreflightBlocker(
  readiness: VoiceRuntimeReadinessResult | null
): RuntimePreflightBlocker | null {
  if (
    readiness?.status !== "ready" &&
    readiness?.status !== "degraded"
  ) {
    return null;
  }
  const check = kokoroCheck(readiness);
  if (check?.metadata.kokoro_transport !== "hf_endpoint") {
    return null;
  }
  if (
    readiness?.preflight_tts === true &&
    check.metadata.kokoro_preflight_performed === true &&
    positiveNumber(check.metadata.kokoro_preflight_audio_bytes)
  ) {
    return null;
  }
  return {
    detail:
      "Kokoro hosted TTS preflight has not run for this runtime check. Run Runtime preflight so the endpoint returns real audio bytes before claiming voice readiness.",
    nextAction: "Run Runtime preflight."
  };
}

export function runtimeProviderPreflightBlocker(
  readiness: VoiceRuntimeReadinessResult | null
): RuntimePreflightBlocker | null {
  return hostedGemmaPreflightBlocker(readiness) ?? hostedKokoroPreflightBlocker(readiness);
}
