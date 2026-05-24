import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const packageJson = JSON.parse(readFileSync("package.json", "utf8")) as {
  scripts: Record<string, string>;
};
const browserSingleFlightSource = readFileSync("tests/browser_single_flight.py", "utf8");

test("browser single-flight smoke is wired into package scripts", () => {
  assert.equal(
    packageJson.scripts["test:browser-single-flight"],
    "python tests/browser_single_flight.py"
  );
});

test("browser single-flight smoke exercises real guarded creator controls", () => {
  for (const label of [
    "Create voice run",
    "Runtime preflight",
    "Check setup",
    "Runtime smoke",
    "Timing ledger",
    "Start transcript rehearsal",
    "Generate",
    "Run web research",
    "Start always-on",
    "Start runner",
    "Queue and run",
    "Suggest next step",
    "Run next steps",
    "Publish check",
    "Send revision"
  ]) {
    assert.match(browserSingleFlightSource, new RegExp(label));
  }
  for (const actionCounter of [
    'counts["voice_run_create"]',
    'counts["voice_run_context_refresh"]',
    'counts["runtime_preflight"]',
    'counts["setup_check_livekit_process"]',
    'counts["setup_check_voice_process"]',
    'counts["setup_check_provider_readiness"]',
    'counts["setup_check_runtime_preflight"]',
    'counts["setup_check_presence"]',
    'counts["setup_check_proof"]',
    'counts["voice_provider_smoke"]',
    'counts["voice_timing_ledger"]',
    'counts["transcript_rehearsal_start"]',
    'counts["transcript_rehearsal_turn"]',
    'counts["conversation"]',
    'counts["source_refresh_message"]',
    'counts["source_refresh_cycle"]',
    'counts["work_plan"]',
    'counts["run_plan_materialize"]',
    'counts["run_plan_cycle"]',
    'counts["run_plan_refresh"]',
    'counts["retry_authorize"]',
    'counts["retry_cycle"]',
    'counts["publish"]',
    'counts["revision"]'
  ]) {
    assert.ok(browserSingleFlightSource.includes(actionCounter));
  }
  assert.match(browserSingleFlightSource, /delay=0\.5/);
  assert.match(browserSingleFlightSource, /button\.click\(\); button\.click\(\);/);
  assert.match(browserSingleFlightSource, /Expected one .* after rapid/);
  assert.match(browserSingleFlightSource, /voice_run_create_payloads/);
  assert.match(browserSingleFlightSource, /runtime_preflight_queries/);
  assert.match(browserSingleFlightSource, /preflight_livekit/);
  assert.match(browserSingleFlightSource, /preflight_gemma/);
  assert.match(browserSingleFlightSource, /preflight_tts/);
  assert.match(browserSingleFlightSource, /Runtime preflight did not request the full provider checks/);
  assert.match(browserSingleFlightSource, /setup_check_proof_payloads/);
  assert.match(browserSingleFlightSource, /Expected one durable voice setup proof after rapid Check setup clicks/);
  assert.match(browserSingleFlightSource, /Expected one LiveKit process refresh after rapid Check setup clicks/);
  assert.match(browserSingleFlightSource, /action_source.*check_setup/);
  assert.match(browserSingleFlightSource, /voice_provider_smoke_payloads/);
  assert.match(browserSingleFlightSource, /Expected one provider smoke request after rapid Runtime smoke clicks/);
  assert.match(browserSingleFlightSource, /execute_live_calls": False/);
  assert.match(browserSingleFlightSource, /voice_timing_ledger_payloads/);
  assert.match(browserSingleFlightSource, /Expected one timing ledger request after rapid Timing ledger clicks/);
  assert.match(browserSingleFlightSource, /event_limit": 500/);
  assert.match(browserSingleFlightSource, /Runtime smoke then Timing ledger/);
  assert.match(browserSingleFlightSource, /Timing ledger then Runtime smoke/);
  assert.match(browserSingleFlightSource, /Expected no extra timing ledger request while Runtime smoke is in flight/);
  assert.match(browserSingleFlightSource, /Expected no extra provider smoke request while Timing ledger is in flight/);
  assert.match(browserSingleFlightSource, /transcript_rehearsal_payloads/);
  assert.match(browserSingleFlightSource, /Expected one realtime session request after rapid Start transcript rehearsal clicks/);
  assert.match(browserSingleFlightSource, /transport_framework": "local_rehearsal"/);
  assert.match(browserSingleFlightSource, /dry_run": True/);
  assert.match(browserSingleFlightSource, /transcript_rehearsal_turn_payloads/);
  assert.match(browserSingleFlightSource, /Expected one realtime turn request after rapid Route rehearsal turn clicks/);
  assert.match(browserSingleFlightSource, /voice_runtime_transcript_rehearsal/);
  assert.match(browserSingleFlightSource, /provider_backed_realtime": False/);
  assert.match(browserSingleFlightSource, /conversation_payloads/);
  assert.match(browserSingleFlightSource, /voice_run_create_pending/);
  assert.match(browserSingleFlightSource, /Created a voice-first run\. Join Live Voice/);
  assert.match(browserSingleFlightSource, /Expected Generate after voice-run create to continue run/);
  assert.match(browserSingleFlightSource, /Expected Generate after voice-run create to use auto intent/);
  assert.match(browserSingleFlightSource, /provider_backed_realtime/);
  assert.match(browserSingleFlightSource, /google\/gemma-4-E4B-it/);
  assert.match(browserSingleFlightSource, /hexgrad\/Kokoro-82M/);
  assert.match(browserSingleFlightSource, /wait_for_load_state\("networkidle"\)/);
  assert.match(browserSingleFlightSource, /retry_phase_worker_payloads/);
  assert.match(browserSingleFlightSource, /Unexpected retry-phase worker cycle payload/);
  assert.match(browserSingleFlightSource, /Queue and run must not create an extra broad/);
  assert.match(
    browserSingleFlightSource,
    /Expected retry authorization count to remain one at smoke end/
  );
  assert.match(
    browserSingleFlightSource,
    /Expected targeted retry worker cycle count to remain one at smoke end/
  );
  assert.match(
    browserSingleFlightSource,
    /Expected no late broad\/default worker cycle after retry/
  );
});

test("browser smoke proves creator-facing always-on status copy", () => {
  for (const staleBackendPhrase of [
    "Autopilot launch recorded",
    "Creator app autopilot",
    "Local worker scheduler process"
  ]) {
    assert.match(browserSingleFlightSource, new RegExp(staleBackendPhrase));
  }
  for (const creatorPhrase of [
    "Always-on studio launch recorded",
    "Creator always-on studio",
    "Background runner is running"
  ]) {
    assert.match(browserSingleFlightSource, new RegExp(creatorPhrase));
  }
  assert.match(browserSingleFlightSource, /not_to_be_visible\(\)/);
});
