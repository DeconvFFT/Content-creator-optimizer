import type { UUID } from "@/lib/api/types";

export const LIVEKIT_AGENT_CONTROL_TOPIC = "agent.voice.control";

export type LiveTextTurnPayloadInput = {
  turnId: string;
  runId: UUID;
  realtimeSessionId: UUID;
  roomName?: string | null;
  expectedAgentIdentity?: string | null;
  controlBindingToken?: string | null;
  transcript: string;
  voice?: string | null;
};

export type LiveTextTurnCurrentInput = {
  controlToken: number;
  activeControlToken: number;
  runId: UUID;
  activeRunId?: UUID | null;
  sessionId: UUID;
  activeSessionId?: UUID | null;
};

export function buildLiveTextTurnPayload(input: LiveTextTurnPayloadInput) {
  const transcript = input.transcript.trim();
  if (!transcript) {
    throw new Error("Live text turn transcript is empty.");
  }
  return {
    type: "transcript_turn",
    turn_id: input.turnId,
    run_id: input.runId,
    realtime_session_id: input.realtimeSessionId,
    room_name: input.roomName ?? null,
    expected_agent_identity: input.expectedAgentIdentity ?? null,
    control_binding_token: input.controlBindingToken ?? null,
    transcript,
    voice: input.voice?.trim() || null,
    source: "next_livekit_text_turn"
  };
}

export function isLiveTextTurnCurrent(input: LiveTextTurnCurrentInput) {
  return (
    input.controlToken === input.activeControlToken &&
    input.runId === input.activeRunId &&
    input.sessionId === input.activeSessionId
  );
}

export function liveTextTurnStatusLabel(sending: boolean) {
  return sending ? "Sending text turn" : "Send text turn";
}

export function newLiveTextTurnId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, (character) => {
    const random = Math.floor(Math.random() * 16);
    return (Number(character) ^ (random & (15 >> (Number(character) / 4)))).toString(16);
  });
}
