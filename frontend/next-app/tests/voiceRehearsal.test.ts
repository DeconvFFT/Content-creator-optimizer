import assert from "node:assert/strict";
import test from "node:test";

import { buildTranscriptRehearsalTurnInput } from "../lib/voice/rehearsal";

test("transcript rehearsal turn payload is routeable but marked non-production", () => {
  const payload = buildTranscriptRehearsalTurnInput({
    realtimeSessionId: "session-1",
    transcript: "  Explain realtime Gemma Kokoro rehearsal for creators.  "
  });

  assert.equal(payload.realtimeSessionId, "session-1");
  assert.equal(payload.transcript, "Explain realtime Gemma Kokoro rehearsal for creators.");
  assert.equal(payload.modality, "voice");
  assert.equal(payload.topic, "voice rehearsal to source-backed content");
  assert.deepEqual(payload.targetFormats, ["post", "reel", "substack"]);
  assert.equal(payload.routeTurn, true);
  assert.equal(payload.metadata.input_surface, "voice_runtime_transcript_rehearsal");
  assert.equal(payload.metadata.provider_backed_realtime, false);
  assert.equal(payload.metadata.rehearsal_only, true);
});

test("transcript rehearsal refuses empty turns before the API call", () => {
  assert.throws(
    () =>
      buildTranscriptRehearsalTurnInput({
        realtimeSessionId: "session-1",
        transcript: "   "
      }),
    /Enter a rehearsal transcript/
  );
});
