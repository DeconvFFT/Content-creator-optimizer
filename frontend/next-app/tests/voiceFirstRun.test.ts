import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import {
  buildVoiceRunCreateInput,
  DEFAULT_LIVE_VOICE_RUN_GOAL
} from "../lib/voice/voiceRun";

const appSource = readFileSync(join(process.cwd(), "app/page.tsx"), "utf8");
const panelSource = readFileSync(
  join(process.cwd(), "components/voice/RealtimeVoicePanel.tsx"),
  "utf8"
);
const stylesSource = readFileSync(join(process.cwd(), "app/globals.css"), "utf8");

test("live voice is the first primary creation surface in the app shell", () => {
  const voiceIndex = appSource.indexOf("<RealtimeVoicePanel");
  const composerIndex = appSource.indexOf("<Composer");

  assert.notEqual(voiceIndex, -1);
  assert.notEqual(composerIndex, -1);
  assert.ok(voiceIndex < composerIndex);
  assert.match(appSource, /onCreateVoiceRun=\{handleCreateVoiceRun\}/);
});

test("live voice panel exposes a no-run voice-first starter before diagnostics", () => {
  const starterIndex = panelSource.indexOf('className="voice-run-starter"');
  const stateIndex = panelSource.indexOf('aria-label="Live voice state"');
  const setupIndex = panelSource.indexOf('aria-label="Voice runtime readiness"');

  assert.notEqual(starterIndex, -1);
  assert.notEqual(stateIndex, -1);
  assert.notEqual(setupIndex, -1);
  assert.ok(starterIndex < stateIndex);
  assert.ok(starterIndex < setupIndex);
  assert.match(panelSource, /aria-label="Create a voice-first run"/);
  assert.match(panelSource, /Create voice run/);
  assert.match(panelSource, /voiceRunCreatingRef\.current/);
});

test("voice-first starter uses a natural multi-line brief field", () => {
  const starterIndex = panelSource.indexOf('className="voice-run-starter"');
  const textareaIndex = panelSource.indexOf("<textarea", starterIndex);
  const inputIndex = panelSource.indexOf("<input", starterIndex);

  assert.notEqual(starterIndex, -1);
  assert.notEqual(textareaIndex, -1);
  assert.ok(inputIndex === -1 || textareaIndex < inputIndex);
  assert.match(panelSource, /<span>Voice run brief<\/span>/);
  assert.doesNotMatch(panelSource, /aria-label="Voice run brief"/);
  assert.match(panelSource, /rows=\{3\}/);
});

test("voice-first starter keeps a natural one-column mobile layout", () => {
  const starterRule = stylesSource.match(
    /\.voice-run-starter\s*\{[\s\S]*?grid-template-columns:\s*minmax\(0,\s*1fr\)\s*auto;[\s\S]*?\}/
  );
  const mobileIndex = stylesSource.indexOf("@media (max-width: 700px)");
  const mobileGridEnd = stylesSource.indexOf(".topic-input", mobileIndex);
  const mobileGridSlice = stylesSource.slice(mobileIndex, mobileGridEnd);
  const twoColumnStart = stylesSource.indexOf(".realtime-voice-grid,");
  const twoColumnEnd = stylesSource.indexOf(".voice-runtime-contract {", twoColumnStart);
  const twoColumnSlice = stylesSource.slice(twoColumnStart, twoColumnEnd);

  assert.ok(starterRule);
  assert.notEqual(mobileIndex, -1);
  assert.notEqual(mobileGridEnd, -1);
  assert.match(mobileGridSlice, /\.voice-run-starter,/);
  assert.match(mobileGridSlice, /grid-template-columns:\s*1fr;/);
  assert.doesNotMatch(twoColumnSlice, /\.voice-run-starter/);
});

test("no-run voice diagnostics are collapsed behind setup details", () => {
  const disclosureIndex = panelSource.indexOf('className="voice-diagnostics-disclosure"');
  const readinessIndex = panelSource.indexOf('aria-label="Voice runtime readiness"');
  const proofIndex = panelSource.indexOf('aria-label="Voice proof ledgers"');

  assert.notEqual(disclosureIndex, -1);
  assert.notEqual(readinessIndex, -1);
  assert.notEqual(proofIndex, -1);
  assert.ok(disclosureIndex < readinessIndex);
  assert.ok(disclosureIndex < proofIndex);
  assert.match(panelSource, /open=\{Boolean\(runId\)\}/);
  assert.match(panelSource, /Setup details/);
});

test("voice-first run creation records provider-backed model and surface provenance", () => {
  const input = buildVoiceRunCreateInput("  Inference engineering explained simply  ");

  assert.equal(input.goal, "Inference engineering explained simply");
  assert.equal(input.input_mode, "voice");
  assert.equal(input.initial_context.input_surface, "live_voice_panel");
  assert.equal(input.initial_context.voice_provider, "openrouter_livekit");
  assert.equal(input.initial_context.provider_backed_realtime, true);
  assert.equal(input.initial_context.rehearsal_only, false);
  assert.equal(input.initial_context.audio_understanding_model, "deepseek/deepseek-v4-flash");
  assert.equal(input.initial_context.tts_model, "hexgrad/Kokoro-82M");
});

test("voice-first run creation records truthful rehearsal provenance", () => {
  const input = buildVoiceRunCreateInput("Rehearse the flow", "local_rehearsal");

  assert.equal(input.goal, "Rehearse the flow");
  assert.equal(input.input_mode, "voice");
  assert.equal(input.initial_context.voice_provider, "local_rehearsal");
  assert.equal(input.initial_context.provider_backed_realtime, false);
  assert.equal(input.initial_context.rehearsal_only, true);
  assert.equal(input.initial_context.audio_understanding_model, null);
  assert.equal(input.initial_context.tts_model, null);
});

test("voice-first run creation falls back to a useful default goal", () => {
  const input = buildVoiceRunCreateInput("   ");

  assert.equal(input.goal, DEFAULT_LIVE_VOICE_RUN_GOAL);
  assert.equal(input.initial_context.voice_first, true);
});

test("voice-first run creation has parent and child duplicate-submit guards", () => {
  assert.match(appSource, /voiceRunCreateInFlightRef\.current/);
  assert.match(panelSource, /voiceRunCreatingRef\.current/);
});

test("text composer submit has a parent duplicate-submit guard", () => {
  const handlerStart = appSource.indexOf("async function handleCompose");
  const handlerEnd = appSource.indexOf("async function handleCreateVoiceRun", handlerStart);
  const handlerSource = appSource.slice(handlerStart, handlerEnd);
  const beginIndex = handlerSource.indexOf("beginRunAction(composerSubmitGateRef.current)");
  const routeIndex = handlerSource.indexOf("routeConversationTurn");

  assert.notEqual(handlerStart, -1);
  assert.notEqual(handlerEnd, -1);
  assert.notEqual(beginIndex, -1);
  assert.notEqual(routeIndex, -1);
  assert.ok(beginIndex < routeIndex);
  assert.match(handlerSource, /finishRunAction\(composerSubmitGateRef\.current, composeToken\)/);
  assert.match(handlerSource, /isRunVersionedActionCurrent/);
  assert.match(appSource, /invalidateRunAction\(composerSubmitGateRef\.current\)/);
});
