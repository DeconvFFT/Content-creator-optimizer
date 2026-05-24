import type {
  LocalLiveKitProcessStatusResult,
  VoiceAgentProcessStatusResult
} from "@/lib/api/types";

const AUTO_STARTABLE_PROCESS_STATUSES = new Set(["stopped", "exited", "failed"]);
const USABLE_OR_PENDING_PROCESS_STATUSES = new Set(["running", "starting", "started"]);

type LocalProcessStatusLike = Pick<
  VoiceAgentProcessStatusResult | LocalLiveKitProcessStatusResult,
  "enabled" | "running" | "status" | "summary"
>;

export function shouldAutoStartLocalProcess(process?: LocalProcessStatusLike | null) {
  if (!process || !process.enabled) {
    return false;
  }
  return !process.running && AUTO_STARTABLE_PROCESS_STATUSES.has(process.status);
}

export function localProcessStartBlocker(
  process: LocalProcessStatusLike,
  fallbackSummary: string
) {
  if (!process.enabled) {
    return null;
  }
  if (process.running || USABLE_OR_PENDING_PROCESS_STATUSES.has(process.status)) {
    return null;
  }
  return process.summary || fallbackSummary;
}

export function shouldAutoStartVoiceAgentProcess(
  process?: VoiceAgentProcessStatusResult | null
) {
  return shouldAutoStartLocalProcess(process);
}

export function shouldAutoStartLocalLiveKitProcess(
  process?: LocalLiveKitProcessStatusResult | null
) {
  return shouldAutoStartLocalProcess(process);
}

export function voiceAgentProcessStartBlocker(
  process: VoiceAgentProcessStatusResult
) {
  return localProcessStartBlocker(
    process,
    "Local Gemma/Kokoro voice-agent process is not running."
  );
}

export function localLiveKitProcessStartBlocker(
  process: LocalLiveKitProcessStatusResult
) {
  return localProcessStartBlocker(process, "Local LiveKit dev server is not running.");
}
