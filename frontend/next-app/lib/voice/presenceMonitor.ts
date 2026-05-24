import type { VoiceAgentPresenceResult } from "@/lib/api/types";

export const VOICE_AGENT_PRESENCE_MONITOR_INTERVAL_MS = 30_000;
export const VOICE_AGENT_PRESENCE_REFRESH_AFTER_SECONDS = 45;

export function shouldProbeVoiceAgentPresence(
  presence: VoiceAgentPresenceResult | null,
  refreshAfterSeconds = VOICE_AGENT_PRESENCE_REFRESH_AFTER_SECONDS
): boolean {
  if (!presence) {
    return true;
  }
  if (presence.status !== "ready" || !presence.observed || presence.stale) {
    return true;
  }
  if (typeof presence.event_age_seconds !== "number") {
    return true;
  }
  return presence.event_age_seconds >= refreshAfterSeconds;
}

export function voicePresenceMonitorTone(
  ready: boolean,
  cancelled: boolean
): "good" | "warn" | "info" {
  if (cancelled) {
    return "info";
  }
  return ready ? "good" : "warn";
}
