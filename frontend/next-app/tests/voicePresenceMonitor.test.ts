import assert from "node:assert/strict";
import test from "node:test";

import {
  shouldProbeVoiceAgentPresence,
  voicePresenceMonitorTone
} from "../lib/voice/presenceMonitor";
import type { VoiceAgentPresenceResult } from "../lib/api/types";

function presence(overrides: Partial<VoiceAgentPresenceResult> = {}): VoiceAgentPresenceResult {
  return {
    run_id: "run-1",
    realtime_session_id: "session-1",
    status: "ready",
    observed: true,
    stale: false,
    stale_after_seconds: 60,
    event_age_seconds: 10,
    evidence: ["Fresh proof"],
    missing_evidence: [],
    next_actions: [],
    summary: "Fresh Gemma/Kokoro participant proof recorded.",
    ...overrides
  };
}

test("voice presence monitor probes missing stale or old proof", () => {
  assert.equal(shouldProbeVoiceAgentPresence(null), true);
  assert.equal(shouldProbeVoiceAgentPresence(presence({ status: "missing", observed: false })), true);
  assert.equal(shouldProbeVoiceAgentPresence(presence({ stale: true })), true);
  assert.equal(shouldProbeVoiceAgentPresence(presence({ event_age_seconds: 46 }), 45), true);
  assert.equal(shouldProbeVoiceAgentPresence(presence({ event_age_seconds: undefined })), true);
});

test("voice presence monitor does not probe fresh ready proof", () => {
  assert.equal(shouldProbeVoiceAgentPresence(presence({ event_age_seconds: 12 }), 45), false);
});

test("voice presence monitor labels ready cancelled and missing checks", () => {
  assert.equal(voicePresenceMonitorTone(true, false), "good");
  assert.equal(voicePresenceMonitorTone(false, true), "info");
  assert.equal(voicePresenceMonitorTone(false, false), "warn");
});
