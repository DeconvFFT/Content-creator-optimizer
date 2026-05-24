import type { UUID, VoiceAgentPresenceResult } from "@/lib/api/types";

export type VoiceAgentPresenceWaitResult = {
  probeId: string;
  attempts: number;
  presence: VoiceAgentPresenceResult | null;
  ready: boolean;
  cancelled: boolean;
  summary: string;
};

export type VoiceAgentPresenceWaitOptions = {
  realtimeSessionId: UUID;
  probeAgentPresence: () => Promise<string>;
  refreshVoicePresence: (
    realtimeSessionId: UUID,
    probeId: string
  ) => Promise<VoiceAgentPresenceResult | null>;
  maxAttempts?: number;
  intervalMs?: number;
  sleep?: (milliseconds: number) => Promise<void>;
  shouldContinue?: () => boolean;
};

const DEFAULT_MAX_ATTEMPTS = 5;
const DEFAULT_INTERVAL_MS = 300;

function defaultSleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => globalThis.setTimeout(resolve, milliseconds));
}

export async function probeAndWaitForVoiceAgentPresence(
  options: VoiceAgentPresenceWaitOptions
): Promise<VoiceAgentPresenceWaitResult> {
  const maxAttempts = Math.max(1, Math.floor(options.maxAttempts ?? DEFAULT_MAX_ATTEMPTS));
  const intervalMs = Math.max(0, Math.floor(options.intervalMs ?? DEFAULT_INTERVAL_MS));
  const sleep = options.sleep ?? defaultSleep;
  const probeId = await options.probeAgentPresence();
  let latestPresence: VoiceAgentPresenceResult | null = null;
  let attempts = 0;

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    if (options.shouldContinue?.() === false) {
      return {
        probeId,
        attempts,
        presence: latestPresence,
        ready: false,
        cancelled: true,
        summary: "Voice-agent presence wait was cancelled before durable proof completed."
      };
    }
    if (attempt > 1 && intervalMs > 0) {
      await sleep(intervalMs);
    }
    if (options.shouldContinue?.() === false) {
      return {
        probeId,
        attempts,
        presence: latestPresence,
        ready: false,
        cancelled: true,
        summary: "Voice-agent presence wait was cancelled before durable proof completed."
      };
    }
    attempts = attempt;
    latestPresence = await options.refreshVoicePresence(options.realtimeSessionId, probeId);
    if (latestPresence?.status === "ready" && latestPresence.observed && !latestPresence.stale) {
      return {
        probeId,
        attempts: attempt,
        presence: latestPresence,
        ready: true,
        cancelled: false,
        summary: latestPresence.summary
      };
    }
  }

  return {
    probeId,
    attempts,
    presence: latestPresence,
    ready: false,
    cancelled: false,
    summary: latestPresence?.summary ?? "No fresh Gemma/Kokoro participant proof was observed."
  };
}
