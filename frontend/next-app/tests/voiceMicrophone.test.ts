import assert from "node:assert/strict";
import test from "node:test";

import {
  isMicrophoneControlCurrent,
  microphoneControlLabel,
  microphoneStatusLabel,
  nextMicrophonePublishingState
} from "../lib/voice/microphone";

test("microphone publishing state toggles between muted and publishing", () => {
  assert.equal(nextMicrophonePublishingState(true), false);
  assert.equal(nextMicrophonePublishingState(false), true);
});

test("microphone labels distinguish idle and in-flight controls", () => {
  assert.equal(microphoneControlLabel(true, false), "Mute mic");
  assert.equal(microphoneControlLabel(false, false), "Unmute mic");
  assert.equal(microphoneControlLabel(true, true), "Muting mic");
  assert.equal(microphoneControlLabel(false, true), "Unmuting mic");
  assert.equal(microphoneStatusLabel(true), "publishing");
  assert.equal(microphoneStatusLabel(false), "muted");
});

test("microphone control ownership rejects stale run session or token completions", () => {
  assert.equal(
    isMicrophoneControlCurrent({
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
    isMicrophoneControlCurrent({
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
    isMicrophoneControlCurrent({
      controlToken: 3,
      activeControlToken: 3,
      runId: "run-1",
      activeRunId: "run-2",
      sessionId: "session-1",
      activeSessionId: "session-1"
    }),
    false
  );
  assert.equal(
    isMicrophoneControlCurrent({
      controlToken: 3,
      activeControlToken: 3,
      runId: "run-1",
      activeRunId: "run-1",
      sessionId: "session-1",
      activeSessionId: null
    }),
    false
  );
});
