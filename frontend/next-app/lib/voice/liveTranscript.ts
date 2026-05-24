export type LiveVoiceTranscriptStatus =
  | "idle"
  | "listening"
  | "committed"
  | "thinking"
  | "speaking"
  | "completed"
  | "cancelled"
  | "failed";

export type LiveVoiceTranscriptState = {
  userStatus: LiveVoiceTranscriptStatus;
  userCaption: string;
  assistantStatus: LiveVoiceTranscriptStatus;
  assistantCaption: string;
  assistantText: string;
  turnId?: string | null;
  responseId?: string | null;
  previousTurnIds?: string[];
};

export const EMPTY_LIVE_VOICE_TRANSCRIPT: LiveVoiceTranscriptState = {
  userStatus: "idle",
  userCaption: "No spoken turn yet.",
  assistantStatus: "idle",
  assistantCaption: "No assistant response yet.",
  assistantText: "",
  turnId: null,
  responseId: null,
  previousTurnIds: []
};

const MAX_ASSISTANT_CAPTION_CHARS = 1600;
const MAX_PREVIOUS_TURN_IDS = 8;

function optionalText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function optionalDeltaText(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function boundedAppend(current: string, delta: string): string {
  const combined = `${current}${delta}`;
  if (combined.length <= MAX_ASSISTANT_CAPTION_CHARS) {
    return combined;
  }
  return combined.slice(combined.length - MAX_ASSISTANT_CAPTION_CHARS);
}

function isTerminalAssistantStatus(status: LiveVoiceTranscriptStatus): boolean {
  return status === "idle" || status === "completed" || status === "cancelled" || status === "failed";
}

function isKnownPreviousTurn(
  current: LiveVoiceTranscriptState,
  incomingTurnId: string | null
): boolean {
  return Boolean(
    incomingTurnId &&
      current.turnId &&
      incomingTurnId !== current.turnId &&
      (current.previousTurnIds ?? []).includes(incomingTurnId)
  );
}

function rememberPreviousTurn(
  current: LiveVoiceTranscriptState,
  incomingTurnId: string | null
): string[] {
  const previousTurnIds = current.previousTurnIds ?? [];
  if (!incomingTurnId || !current.turnId || incomingTurnId === current.turnId) {
    return previousTurnIds;
  }
  return [current.turnId, ...previousTurnIds.filter((turnId) => turnId !== current.turnId)].slice(
    0,
    MAX_PREVIOUS_TURN_IDS
  );
}

function eventMatchesCurrentCaption(
  current: LiveVoiceTranscriptState,
  payload: Record<string, unknown>
): boolean {
  const incomingTurnId = optionalText(payload.turn_id);
  const incomingResponseId = optionalText(payload.response_id);
  if (incomingTurnId && current.turnId && incomingTurnId !== current.turnId) {
    return false;
  }
  if (
    incomingResponseId &&
    current.responseId &&
    incomingResponseId !== current.responseId
  ) {
    return false;
  }
  return true;
}

export function liveVoiceTranscriptFromAgentEvent(
  current: LiveVoiceTranscriptState,
  eventType: string,
  payload: Record<string, unknown>
): LiveVoiceTranscriptState {
  const incomingTurnId = optionalText(payload.turn_id);
  const incomingResponseId = optionalText(payload.response_id);
  const turnId = incomingTurnId ?? current.turnId ?? null;
  const responseId = incomingResponseId ?? current.responseId ?? null;

  if (eventType === "voice_user_speech_started") {
    if (isKnownPreviousTurn(current, incomingTurnId)) {
      return current;
    }
    return {
      ...current,
      userStatus: "listening",
      userCaption: "Listening...",
      turnId,
      responseId: incomingTurnId ? null : current.responseId ?? null,
      previousTurnIds: rememberPreviousTurn(current, incomingTurnId)
    };
  }

  if (eventType === "voice_user_turn_committed") {
    const transcript = optionalText(payload.transcript);
    const sameTurn = Boolean(incomingTurnId && current.turnId === incomingTurnId);
    if (isKnownPreviousTurn(current, incomingTurnId)) {
      return current;
    }
    if (sameTurn && current.userStatus === "committed") {
      return {
        ...current,
        userCaption: transcript ?? current.userCaption,
        turnId,
        responseId: current.responseId ?? incomingResponseId ?? null
      };
    }
    return {
      ...current,
      userStatus: "committed",
      userCaption: transcript ?? "Audio turn committed; transcript pending.",
      assistantStatus: "thinking",
      assistantCaption: "Gemma is thinking...",
      assistantText: "",
      turnId,
      responseId: incomingResponseId ?? null,
      previousTurnIds: rememberPreviousTurn(current, incomingTurnId)
    };
  }

  if (eventType === "gemma_generation_started" || eventType === "gemma_kokoro_voice_turn_started") {
    if (
      incomingTurnId &&
      current.turnId &&
      incomingTurnId !== current.turnId &&
      !isTerminalAssistantStatus(current.assistantStatus)
    ) {
      return current;
    }
    return {
      ...current,
      assistantStatus: "thinking",
      assistantCaption: current.assistantText || "Gemma is thinking...",
      turnId,
      responseId
    };
  }

  if (eventType === "assistant_text_delta") {
    if (!eventMatchesCurrentCaption(current, payload)) {
      return current;
    }
    const delta = optionalDeltaText(payload.text_delta) ?? optionalDeltaText(payload.delta) ?? "";
    const assistantText = delta ? boundedAppend(current.assistantText, delta) : current.assistantText;
    return {
      ...current,
      assistantStatus: "thinking",
      assistantCaption: assistantText || "Gemma is drafting...",
      assistantText,
      turnId,
      responseId
    };
  }

  if (eventType === "kokoro_tts_fragment_started" || eventType === "assistant_audio_chunk_published") {
    if (!eventMatchesCurrentCaption(current, payload)) {
      return current;
    }
    return {
      ...current,
      assistantStatus: "speaking",
      assistantCaption: current.assistantText || "Kokoro is speaking...",
      turnId,
      responseId
    };
  }

  if (eventType === "assistant_response_completed") {
    if (!eventMatchesCurrentCaption(current, payload)) {
      return current;
    }
    const assistantText = optionalText(payload.assistant_text) ?? current.assistantText;
    return {
      ...current,
      assistantStatus: "completed",
      assistantCaption: assistantText || "Assistant response completed.",
      assistantText,
      turnId,
      responseId
    };
  }

  if (eventType === "gemma_kokoro_voice_turn_cancelled") {
    if (!eventMatchesCurrentCaption(current, payload)) {
      return current;
    }
    return {
      ...current,
      assistantStatus: "cancelled",
      assistantCaption: "Response stopped.",
      turnId,
      responseId
    };
  }

  if (eventType === "gemma_kokoro_voice_turn_failed") {
    if (!eventMatchesCurrentCaption(current, payload)) {
      return current;
    }
    const stage = optionalText(payload.failure_stage) ?? "voice turn";
    const reason = optionalText(payload.failure_reason) ?? optionalText(payload.reason);
    return {
      ...current,
      assistantStatus: "failed",
      assistantCaption: reason ? `${stage} failed: ${reason}` : `${stage} failed.`,
      turnId,
      responseId
    };
  }

  if (eventType === "voice_interrupt_no_active_response") {
    return {
      ...current,
      assistantStatus: "completed",
      assistantCaption: "No active response to stop.",
      turnId,
      responseId
    };
  }

  return current;
}
