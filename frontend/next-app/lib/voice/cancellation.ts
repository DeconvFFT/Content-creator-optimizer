export type VoiceCancellationProofStatus =
  | "idle"
  | "requested"
  | "agent_acknowledged"
  | "edge_acknowledged"
  | "stopped"
  | "failed";

export type VoiceCancellationProof = {
  status: VoiceCancellationProofStatus;
  label: string;
  summary: string;
  evidence: string[];
};

export const IDLE_CANCELLATION_PROOF: VoiceCancellationProof = {
  status: "idle",
  label: "Idle",
  summary: "No interrupt cancellation is pending.",
  evidence: []
};

export function requestedCancellationProof(eventId?: number | null): VoiceCancellationProof {
  return {
    status: "requested",
    label: "Requested",
    summary: "Interrupt control was recorded; waiting for runtime cancellation acknowledgement.",
    evidence: eventId ? [`Control event: #${eventId}`] : []
  };
}

export function failedCancellationProofFromControlError(
  current: VoiceCancellationProof,
  message: string
): VoiceCancellationProof {
  if (current.status !== "requested") {
    return current;
  }
  return {
    status: "failed",
    label: "Failed",
    summary: "Interrupt control failed before runtime acknowledgement.",
    evidence: [message || "Unknown interrupt error"]
  };
}

export function cancellationProofFromVoiceAgentEvent(
  current: VoiceCancellationProof,
  eventType: string,
  payload: Record<string, unknown>
): VoiceCancellationProof {
  if (eventType === "voice_edge_error") {
    return {
      status: "failed",
      label: "Edge error",
      summary: "Rust voice-edge reported an error while handling realtime audio.",
      evidence: [stringValue(payload.error) || "Voice-edge error payload did not include a message."].filter(Boolean)
    };
  }
  if (eventType === "voice_edge_cancellation_acknowledged") {
    const cancellation =
      recordValue(recordValue(payload.voice_edge_event)?.cancellation) ??
      recordValue(payload.cancellation);
    return {
      status: "edge_acknowledged",
      label: "Edge ack",
      summary: "Rust voice-edge acknowledged the barge-in cancellation contract.",
      evidence: cancellationEvidence(cancellation)
    };
  }
  if (eventType === "voice_manual_interrupt_received") {
    if (payload.canceled === false) {
      return {
        status: "failed",
        label: "Agent rejected",
        summary: "The Gemma/Kokoro agent received the interrupt but could not cancel the requested response.",
        evidence: cancellationEvidence(payload)
      };
    }
    return {
      status: "agent_acknowledged",
      label: "Agent ack",
      summary: "The Gemma/Kokoro agent received the interrupt; waiting for final stop confirmation.",
      evidence: cancellationEvidence(payload)
    };
  }
  if (eventType === "voice_interrupt_no_active_response") {
    return {
      status: "stopped",
      label: "No active response",
      summary: "The Gemma/Kokoro agent had no active spoken response to cancel.",
      evidence: cancellationEvidence(payload)
    };
  }
  if (eventType === "gemma_kokoro_voice_turn_cancelled") {
    return {
      status: "stopped",
      label: "Stopped",
      summary: "Gemma cancellation, Kokoro buffer clearing, and LiveKit audio stop were acknowledged.",
      evidence: cancellationEvidence(payload)
    };
  }
  return current;
}

function cancellationEvidence(payload: Record<string, unknown> | null | undefined): string[] {
  if (!payload) {
    return [];
  }
  const responseId = stringValue(payload.response_id);
  const reason = stringValue(payload.reason);
  return [
    responseId ? `Response: ${responseId}` : "",
    reason ? `Reason: ${reason}` : "",
    booleanValue(payload.cancel_gemma) ? "Gemma: cancel acknowledged" : "",
    booleanValue(payload.clear_kokoro_buffers) ? "Kokoro: buffer clear acknowledged" : "",
    booleanValue(payload.stop_livekit_audio) ||
    booleanValue(payload.drop_outbound_audio) ||
    booleanValue(payload.drop_outbound_audio_packets)
      ? "LiveKit: output stop acknowledged"
      : ""
  ].filter(Boolean);
}

function recordValue(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function booleanValue(value: unknown): boolean {
  return value === true;
}
