import assert from "node:assert/strict";
import test from "node:test";

import {
  buildRealtimeAgentControlMetadata,
  GEMMA_KOKORO_STOP_RUNTIME_ACTIONS,
  LIVEKIT_AGENT_CONTROL_TOPIC
} from "../lib/voice/controlMetadata";

test("realtime agent control metadata records successful LiveKit stop contract", () => {
  const metadata = buildRealtimeAgentControlMetadata({
    purpose: "session_stop",
    providerBackedRealtime: true,
    transportFramework: "livekit",
    livekitAgentControlId: "voice-interrupt-123",
    livekitAgentControlError: null
  });

  assert.equal(metadata.livekit_agent_control_sent, true);
  assert.equal(metadata.livekit_agent_control_id, "voice-interrupt-123");
  assert.equal(metadata.livekit_agent_control_error, null);
  assert.equal(metadata.livekit_agent_control_topic, LIVEKIT_AGENT_CONTROL_TOPIC);
  assert.equal(metadata.livekit_agent_control_purpose, "session_stop");
  assert.deepEqual(metadata.required_runtime_actions, [
    "drop_outbound_audio_packets",
    "cancel_gemma_inference",
    "clear_kokoro_tts_buffer",
    "stop_livekit_audio"
  ]);
  assert.deepEqual(metadata.required_runtime_actions, [...GEMMA_KOKORO_STOP_RUNTIME_ACTIONS]);
});

test("realtime agent control metadata preserves failed LiveKit control evidence", () => {
  const metadata = buildRealtimeAgentControlMetadata({
    purpose: "interrupt",
    providerBackedRealtime: true,
    transportFramework: "livekit",
    livekitAgentControlId: null,
    livekitAgentControlError: "publish failed"
  });

  assert.equal(metadata.livekit_agent_control_sent, false);
  assert.equal(metadata.livekit_agent_control_id, null);
  assert.equal(metadata.livekit_agent_control_error, "publish failed");
  assert.equal(metadata.livekit_agent_control_purpose, "interrupt");
});
