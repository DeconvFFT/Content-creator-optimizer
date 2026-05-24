import type { LiveKitRuntimeEvent } from "./livekitRuntime";

export type LiveVoiceStageId =
  | "disconnected"
  | "connecting"
  | "connected"
  | "listening"
  | "thinking"
  | "speaking"
  | "interrupting"
  | "reconnecting"
  | "ended"
  | "failed";

export type LiveVoiceStageDefinition = {
  id: LiveVoiceStageId;
  label: string;
  description: string;
};

export const LIVE_VOICE_STAGES: Record<LiveVoiceStageId, LiveVoiceStageDefinition> = {
  disconnected: {
    id: "disconnected",
    label: "Disconnected",
    description: "No active provider-backed voice room is connected."
  },
  connecting: {
    id: "connecting",
    label: "Connecting",
    description: "Preparing runtime checks, transport, and room join."
  },
  connected: {
    id: "connected",
    label: "Connected",
    description: "LiveKit media is connected; waiting for the agent loop."
  },
  listening: {
    id: "listening",
    label: "Listening",
    description: "The room is ready for your next spoken turn."
  },
  thinking: {
    id: "thinking",
    label: "Thinking",
    description: "Gemma is processing the captured voice turn."
  },
  speaking: {
    id: "speaking",
    label: "Speaking",
    description: "Kokoro speech output is being published to LiveKit."
  },
  interrupting: {
    id: "interrupting",
    label: "Interrupting",
    description: "Barge-in cancellation is dropping output and clearing buffers."
  },
  reconnecting: {
    id: "reconnecting",
    label: "Reconnecting",
    description: "LiveKit is reconnecting the active media room."
  },
  ended: {
    id: "ended",
    label: "Ended",
    description: "The previous voice session has ended."
  },
  failed: {
    id: "failed",
    label: "Failed",
    description: "The live voice runtime hit a blocking error."
  }
};

export function stageFromVoiceStatus(status: string): LiveVoiceStageId {
  if (status === "starting" || status === "joining") {
    return "connecting";
  }
  if (status === "ready") {
    return "connected";
  }
  if (status === "stopping" || status === "stopped") {
    return "ended";
  }
  if (status === "blocked" || status === "error") {
    return "failed";
  }
  return "disconnected";
}

export function stageFromRuntimeEvent(
  currentStage: LiveVoiceStageId,
  event: LiveKitRuntimeEvent
): LiveVoiceStageId {
  if (event.label === "LiveKit reconnecting") {
    return "reconnecting";
  }
  if (event.label === "LiveKit disconnected") {
    return "ended";
  }
  if (event.label === "LiveKit connection state") {
    if (event.detail === "connected") {
      return currentStage === "reconnecting" ? "listening" : "connected";
    }
    if (event.detail === "disconnected") {
      if (currentStage === "reconnecting") {
        return "reconnecting";
      }
      return "ended";
    }
  }
  if (event.label === "Voice event parse failed") {
    return "failed";
  }
  return currentStage;
}

export function stageFromVoiceAgentEvent(
  currentStage: LiveVoiceStageId,
  eventType: string
): LiveVoiceStageId {
  if (
    eventType === "voice_barge_in_detected" ||
    eventType === "voice_edge_cancellation_acknowledged" ||
    eventType === "voice_manual_interrupt_received"
  ) {
    return "interrupting";
  }
  if (eventType === "voice_interrupt_no_active_response") {
    return "listening";
  }
  if (
    eventType === "voice_edge_error" ||
    eventType === "gemma_kokoro_voice_turn_cancelled" ||
    eventType === "gemma_kokoro_voice_turn_failed"
  ) {
    return eventType === "gemma_kokoro_voice_turn_cancelled" ? "listening" : "failed";
  }
  if (
    eventType === "gemma_kokoro_voice_agent_ready" ||
    eventType === "voice_user_speech_started" ||
    eventType === "assistant_response_completed"
  ) {
    return "listening";
  }
  if (eventType === "voice_agent_media_bridge_ready") {
    return currentStage === "connected" ? "listening" : currentStage;
  }
  if (
    eventType === "voice_user_turn_committed" ||
    eventType === "gemma_kokoro_voice_turn_started" ||
    eventType === "voice_context_pruned" ||
    eventType === "gemma_generation_started" ||
    eventType === "assistant_text_delta"
  ) {
    return "thinking";
  }
  if (
    eventType === "kokoro_tts_fragment_started" ||
    eventType === "assistant_audio_chunk_published"
  ) {
    return "speaking";
  }
  return currentStage;
}
