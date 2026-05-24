import assert from "node:assert/strict";
import test from "node:test";

import {
  LIVE_VOICE_STAGES,
  stageFromRuntimeEvent,
  stageFromVoiceAgentEvent,
  stageFromVoiceStatus
} from "../lib/voice/liveStage";

test("voice status maps to the required live voice state machine", () => {
  assert.equal(stageFromVoiceStatus("idle"), "disconnected");
  assert.equal(stageFromVoiceStatus("starting"), "connecting");
  assert.equal(stageFromVoiceStatus("joining"), "connecting");
  assert.equal(stageFromVoiceStatus("ready"), "connected");
  assert.equal(stageFromVoiceStatus("stopping"), "ended");
  assert.equal(stageFromVoiceStatus("stopped"), "ended");
  assert.equal(stageFromVoiceStatus("blocked"), "failed");
  assert.equal(stageFromVoiceStatus("error"), "failed");
});

test("voice runtime events update connection stages", () => {
  assert.equal(
    stageFromRuntimeEvent("connected", {
      label: "LiveKit reconnecting",
      tone: "warn"
    }),
    "reconnecting"
  );
  assert.equal(
    stageFromRuntimeEvent("reconnecting", {
      label: "LiveKit connection state",
      detail: "connected",
      tone: "good"
    }),
    "listening"
  );
  assert.equal(
    stageFromRuntimeEvent("reconnecting", {
      label: "LiveKit connection state",
      detail: "disconnected",
      tone: "info"
    }),
    "reconnecting"
  );
  assert.equal(
    stageFromRuntimeEvent("speaking", {
      label: "LiveKit disconnected",
      tone: "info"
    }),
    "ended"
  );
  assert.equal(
    stageFromRuntimeEvent("connected", {
      label: "Voice event parse failed",
      tone: "warn"
    }),
    "failed"
  );
});

test("voice-agent events project listening thinking speaking and interrupting", () => {
  assert.equal(
    stageFromVoiceAgentEvent("connected", "gemma_kokoro_voice_agent_ready"),
    "listening"
  );
  assert.equal(
    stageFromVoiceAgentEvent("connected", "voice_agent_media_bridge_ready"),
    "listening"
  );
  assert.equal(
    stageFromVoiceAgentEvent("thinking", "voice_agent_media_bridge_ready"),
    "thinking"
  );
  assert.equal(
    stageFromVoiceAgentEvent("speaking", "voice_agent_media_bridge_ready"),
    "speaking"
  );
  assert.equal(
    stageFromVoiceAgentEvent("interrupting", "voice_agent_media_bridge_ready"),
    "interrupting"
  );
  assert.equal(stageFromVoiceAgentEvent("listening", "voice_user_turn_committed"), "thinking");
  assert.equal(stageFromVoiceAgentEvent("thinking", "gemma_generation_started"), "thinking");
  assert.equal(stageFromVoiceAgentEvent("thinking", "assistant_audio_chunk_published"), "speaking");
  assert.equal(stageFromVoiceAgentEvent("speaking", "voice_barge_in_detected"), "interrupting");
  assert.equal(stageFromVoiceAgentEvent("speaking", "voice_manual_interrupt_received"), "interrupting");
  assert.equal(stageFromVoiceAgentEvent("interrupting", "voice_interrupt_no_active_response"), "listening");
  assert.equal(
    stageFromVoiceAgentEvent("interrupting", "gemma_kokoro_voice_turn_cancelled"),
    "listening"
  );
  assert.equal(
    stageFromVoiceAgentEvent("thinking", "gemma_kokoro_voice_turn_failed"),
    "failed"
  );
  assert.equal(stageFromVoiceAgentEvent("speaking", "assistant_response_completed"), "listening");
});

test("voice stage definitions include the required state labels", () => {
  assert.deepEqual(Object.keys(LIVE_VOICE_STAGES), [
    "disconnected",
    "connecting",
    "connected",
    "listening",
    "thinking",
    "speaking",
    "interrupting",
    "reconnecting",
    "ended",
    "failed"
  ]);
});
