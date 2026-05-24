export function nextMicrophonePublishingState(currentlyPublishing: boolean): boolean {
  return !currentlyPublishing;
}

export type MicrophoneControlOwnership = {
  controlToken: number;
  activeControlToken: number;
  runId?: string | null;
  activeRunId?: string | null;
  sessionId?: string | null;
  activeSessionId?: string | null;
};

export function isMicrophoneControlCurrent({
  controlToken,
  activeControlToken,
  runId,
  activeRunId,
  sessionId,
  activeSessionId
}: MicrophoneControlOwnership): boolean {
  return (
    controlToken === activeControlToken &&
    Boolean(runId) &&
    runId === activeRunId &&
    Boolean(sessionId) &&
    sessionId === activeSessionId
  );
}

export function microphoneControlLabel(
  publishing: boolean,
  loading: boolean
): string {
  if (loading) {
    return publishing ? "Muting mic" : "Unmuting mic";
  }
  return publishing ? "Mute mic" : "Unmute mic";
}

export function microphoneStatusLabel(publishing: boolean): string {
  return publishing ? "publishing" : "muted";
}
