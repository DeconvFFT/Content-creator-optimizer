import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

test("livekit runtime missing-url guidance points at the OpenRouter LiveKit env", () => {
  const source = readFileSync(join(process.cwd(), "lib/voice/livekitRuntime.ts"), "utf8");

  assert.match(source, /LiveKit URL is missing\. Configure OPENROUTER_LIVEKIT_URL\./);
  assert.doesNotMatch(source, /LiveKit URL is missing\. Configure GEMMA4_REALTIME_LIVEKIT_URL\./);
});
