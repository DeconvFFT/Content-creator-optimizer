export const LIVEKIT_AGENT_CONTROL_TOPIC = "agent.voice.control";

export const GEMMA_KOKORO_STOP_RUNTIME_ACTIONS = [
  "drop_outbound_audio_packets",
  "cancel_gemma_inference",
  "clear_kokoro_tts_buffer",
  "stop_livekit_audio"
] as const;

export type RealtimeAgentControlPurpose = "interrupt" | "session_stop";

export function buildRealtimeAgentControlMetadata(input: {
  purpose: RealtimeAgentControlPurpose;
  providerBackedRealtime: boolean;
  transportFramework: string;
  livekitAgentControlId: string | null;
  livekitAgentControlError: string | null;
}) {
  return {
    live_voice_panel: true,
    gemma4_kokoro_audio_stream: input.providerBackedRealtime,
    transport_framework: input.transportFramework,
    livekit_agent_control_sent: input.livekitAgentControlId !== null,
    livekit_agent_control_id: input.livekitAgentControlId,
    livekit_agent_control_error: input.livekitAgentControlError,
    livekit_agent_control_topic: LIVEKIT_AGENT_CONTROL_TOPIC,
    livekit_agent_control_purpose: input.purpose,
    required_runtime_actions: [...GEMMA_KOKORO_STOP_RUNTIME_ACTIONS]
  };
}
