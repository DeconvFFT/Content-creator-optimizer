import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const panelSource = readFileSync(
  join(process.cwd(), "components/voice/RealtimeVoicePanel.tsx"),
  "utf8"
);

test("voice panel keeps primary live controls before diagnostics in the component tree", () => {
  const controlsIndex = panelSource.indexOf('className="realtime-actions"');
  const stageIndex = panelSource.indexOf('aria-label="Live voice state"');
  const captionsIndex = panelSource.indexOf(
    'aria-label="Live voice captions"'
  );
  const readinessIndex = panelSource.indexOf('aria-label="Voice runtime readiness"');
  const proofIndex = panelSource.indexOf('aria-label="Voice proof ledgers"');

  assert.notEqual(controlsIndex, -1);
  assert.notEqual(stageIndex, -1);
  assert.notEqual(captionsIndex, -1);
  assert.notEqual(readinessIndex, -1);
  assert.notEqual(proofIndex, -1);
  assert.ok(controlsIndex > stageIndex);
  assert.ok(controlsIndex < captionsIndex);
  assert.ok(controlsIndex < readinessIndex);
  assert.ok(controlsIndex < proofIndex);
  assert.match(panelSource, /Join voice room/);
});
