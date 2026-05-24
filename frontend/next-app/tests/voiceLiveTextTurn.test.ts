import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import {
  buildLiveTextTurnPayload,
  isLiveTextTurnCurrent,
  liveTextTurnStatusLabel,
  LIVEKIT_AGENT_CONTROL_TOPIC,
  newLiveTextTurnId
} from "../lib/voice/liveTextTurn";

test("live text turn payload targets the active LiveKit Gemma Kokoro session", () => {
  const payload = buildLiveTextTurnPayload({
    turnId: "turn-1",
    runId: "run-1",
    realtimeSessionId: "session-1",
    roomName: "voice-room",
    expectedAgentIdentity: "gemma4-kokoro-agent",
    controlBindingToken: "binding-token",
    transcript: "  Explain inference engineering like I am five.  ",
    voice: " af_heart "
  });

  assert.equal(LIVEKIT_AGENT_CONTROL_TOPIC, "agent.voice.control");
  assert.equal(payload.type, "transcript_turn");
  assert.equal(payload.turn_id, "turn-1");
  assert.equal(payload.run_id, "run-1");
  assert.equal(payload.realtime_session_id, "session-1");
  assert.equal(payload.room_name, "voice-room");
  assert.equal(payload.expected_agent_identity, "gemma4-kokoro-agent");
  assert.equal(payload.control_binding_token, "binding-token");
  assert.equal(payload.transcript, "Explain inference engineering like I am five.");
  assert.equal(payload.voice, "af_heart");
  assert.equal(payload.source, "next_livekit_text_turn");
});

test("live text turn payload rejects empty transcripts", () => {
  assert.throws(
    () =>
      buildLiveTextTurnPayload({
        turnId: "turn-1",
        runId: "run-1",
        realtimeSessionId: "session-1",
        transcript: "   "
      }),
    /empty/
  );
});

test("live text turn ownership rejects stale run session or token completions", () => {
  assert.equal(
    isLiveTextTurnCurrent({
      controlToken: 3,
      activeControlToken: 3,
      runId: "run-1",
      activeRunId: "run-1",
      sessionId: "session-1",
      activeSessionId: "session-1"
    }),
    true
  );
  assert.equal(
    isLiveTextTurnCurrent({
      controlToken: 2,
      activeControlToken: 3,
      runId: "run-1",
      activeRunId: "run-1",
      sessionId: "session-1",
      activeSessionId: "session-1"
    }),
    false
  );
  assert.equal(
    isLiveTextTurnCurrent({
      controlToken: 3,
      activeControlToken: 3,
      runId: "run-1",
      activeRunId: "run-2",
      sessionId: "session-1",
      activeSessionId: "session-1"
    }),
    false
  );
  assert.equal(liveTextTurnStatusLabel(true), "Sending text turn");
  assert.equal(liveTextTurnStatusLabel(false), "Send text turn");
});

test("live text turn ids are raw uuids for durable materialization", () => {
  assert.match(
    newLiveTextTurnId(),
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
  );
});

test("live text turn submit has a synchronous duplicate-submit gate before LiveKit send", () => {
  const panelSource = readFileSync(
    join(process.cwd(), "components/voice/RealtimeVoicePanel.tsx"),
    "utf8"
  );
  const handlerSource =
    panelSource.match(/async function handleSendLiveTextTurn[\s\S]*?\n  async function handleRehearsalTurn/)?.[0] ?? "";

  assert.match(panelSource, /const liveTextTurnInFlightRef = useRef\(false\)/);
  assert.match(panelSource, /!liveTextTurnInFlightRef\.current/);
  assert.match(
    handlerSource,
    /if \(!liveRuntime \|\| !liveSession \|\| !canSendLiveTextTurn \|\| liveTextTurnInFlightRef\.current\)/
  );
  assert.match(
    handlerSource,
    /liveTextTurnInFlightRef\.current = true;[\s\S]*?setLiveTextTurnLoading\(true\);[\s\S]*?liveRuntime\.sendTranscriptTurn/
  );
  assert.match(
    handlerSource,
    /await liveRuntime\.interruptAgent[\s\S]*?if \(!isCurrentTextTurn\(\)\) \{\s+return;\s+\}[\s\S]*?const turnId = await liveRuntime\.sendTranscriptTurn/
  );
  assert.match(
    handlerSource,
    /if \(isCurrentTextTurn\(\)\) \{\s+liveTextTurnInFlightRef\.current = false;\s+setLiveTextTurnLoading\(false\);/
  );
});
