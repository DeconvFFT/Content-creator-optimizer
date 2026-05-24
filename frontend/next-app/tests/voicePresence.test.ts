import assert from "node:assert/strict";
import test from "node:test";

import { probeAndWaitForVoiceAgentPresence } from "../lib/voice/presence";
import type { VoiceAgentPresenceResult } from "../lib/api/types";

function presence(overrides: Partial<VoiceAgentPresenceResult> = {}): VoiceAgentPresenceResult {
  return {
    run_id: "run-1",
    realtime_session_id: "session-1",
    status: "missing",
    observed: false,
    stale: false,
    stale_after_seconds: 60,
    evidence: [],
    missing_evidence: ["No durable participant proof yet."],
    next_actions: [],
    summary: "No fresh Gemma/Kokoro participant proof was observed.",
    ...overrides
  };
}

test("voice presence wait returns ready after a delayed probe acknowledgement", async () => {
  const sleeps: number[] = [];
  const statuses = [
    presence(),
    presence({
      status: "ready",
      observed: true,
      summary: "Fresh Gemma/Kokoro participant proof recorded."
    })
  ];

  const result = await probeAndWaitForVoiceAgentPresence({
    realtimeSessionId: "session-1",
    probeAgentPresence: async () => "probe-1",
    refreshVoicePresence: async (sessionId, probeId) => {
      assert.equal(sessionId, "session-1");
      assert.equal(probeId, "probe-1");
      return statuses.shift() ?? presence();
    },
    maxAttempts: 3,
    intervalMs: 25,
    sleep: async (milliseconds) => {
      sleeps.push(milliseconds);
    }
  });

  assert.equal(result.ready, true);
  assert.equal(result.cancelled, false);
  assert.equal(result.probeId, "probe-1");
  assert.equal(result.attempts, 2);
  assert.equal(result.summary, "Fresh Gemma/Kokoro participant proof recorded.");
  assert.deepEqual(sleeps, [25]);
});

test("voice presence wait exhausts attempts without treating stale proof as ready", async () => {
  let attempts = 0;
  const result = await probeAndWaitForVoiceAgentPresence({
    realtimeSessionId: "session-1",
    probeAgentPresence: async () => "probe-2",
    refreshVoicePresence: async () => {
      attempts += 1;
      return presence({
        status: "ready",
        observed: true,
        stale: true,
        summary: "Only stale Gemma/Kokoro participant proof exists."
      });
    },
    maxAttempts: 2,
    intervalMs: 10,
    sleep: async () => undefined
  });

  assert.equal(result.ready, false);
  assert.equal(result.cancelled, false);
  assert.equal(result.attempts, 2);
  assert.equal(attempts, 2);
  assert.equal(result.summary, "Only stale Gemma/Kokoro participant proof exists.");
});

test("voice presence wait can cancel before stale polling continues", async () => {
  let shouldContinue = true;
  const result = await probeAndWaitForVoiceAgentPresence({
    realtimeSessionId: "session-1",
    probeAgentPresence: async () => "probe-3",
    refreshVoicePresence: async () => {
      shouldContinue = false;
      return presence();
    },
    shouldContinue: () => shouldContinue,
    maxAttempts: 3,
    intervalMs: 10,
    sleep: async () => {
      throw new Error("sleep should not run after cancellation");
    }
  });

  assert.equal(result.ready, false);
  assert.equal(result.cancelled, true);
  assert.equal(result.attempts, 1);
  assert.equal(
    result.summary,
    "Voice-agent presence wait was cancelled before durable proof completed."
  );
});
