import assert from "node:assert/strict";
import test from "node:test";

import {
  buildVoiceAudioFixtureProof,
  buildVoiceStreamingProviderProof,
  findGemmaKokoroStreamingSmokeStep,
  formatAudioBytes,
  shortSha256
} from "../lib/voice/providerSmoke";
import type {
  ProviderReadinessResult,
  ProviderSmokeRunResult,
  ProviderSmokeStepResult
} from "../lib/api/types";

const providerReadiness: ProviderReadinessResult = {
  default_realtime_provider: "gemma4_realtime",
  selected_web_search_provider: "tavily",
  providers: [],
  ready_provider_ids: [],
  missing_provider_ids: [],
  tool_boundary_provider_ids: [],
  missing_required_env: [],
  provider_backed_smoke_ready: true,
  smoke_test_plan: [],
  demo_walkthrough: [],
  summary: "Provider readiness fixture."
};

function step(overrides: Partial<ProviderSmokeStepResult> = {}): ProviderSmokeStepResult {
  return {
    step_id: "gemma-kokoro-voice-streaming-smoke",
    provider_id: "gemma4_realtime",
    provider_type: "realtime_audio",
    title: "Gemma/Kokoro voice streaming smoke",
    status: "passed",
    required: true,
    live_call: true,
    latency_class: "measured",
    end_to_end_latency_ms: 800,
    provider_latency_ms: 620,
    smoke_proof_status: "passed",
    evidence: [],
    blockers: [],
    next_actions: [],
    source_ids: [],
    realtime_session_ids: [],
    event_ids: [],
    details: {},
    ...overrides
  };
}

test("voice smoke proof exposes captured microphone artifact evidence", () => {
  const proof = buildVoiceAudioFixtureProof(
    step({
      details: {
        audio_fixture_source: "captured_voice_audio_artifact",
        audio_artifact_used: true,
        audio_artifact_relative_path: "voice-audio/run/session/turn.pcm",
        audio_artifact_sha256: "1234567890abcdef1234567890abcdef",
        audio_artifact_bytes: 13440,
        audio_fixture_turn_id: "turn-1"
      }
    })
  );

  assert.equal(proof.status, "captured");
  assert.equal(proof.title, "Captured audio proof");
  assert.equal(proof.summary, "Gemma smoke used the latest persisted microphone PCM from this run.");
  assert.deepEqual(proof.evidence, [
    "Artifact: voice-audio/run/session/turn.pcm",
    "Size: 13 KB",
    "SHA-256: 1234567890ab...",
    "Turn: turn-1"
  ]);
});

test("voice smoke proof labels session-bound captured audio evidence", () => {
  const proof = buildVoiceAudioFixtureProof(
    step({
      details: {
        audio_fixture_source: "captured_voice_audio_artifact",
        audio_artifact_used: true,
        audio_artifact_relative_path: "voice-audio/run/session-1/turn.pcm",
        audio_artifact_sha256: "abcdef1234567890",
        audio_artifact_bytes: 2048,
        audio_fixture_turn_id: "turn-1",
        audio_fixture_realtime_session_id: "session-1"
      }
    })
  );

  assert.equal(proof.status, "captured");
  assert.equal(
    proof.summary,
    "Gemma smoke used persisted microphone PCM from the bound LiveKit session."
  );
});

test("voice smoke proof labels synthetic fallback when no captured artifact is used", () => {
  const proof = buildVoiceAudioFixtureProof(
    step({
      status: "passed",
      details: {
        audio_fixture_source: "synthetic_silence_probe",
        audio_artifact_used: false
      }
    })
  );

  assert.equal(proof.status, "synthetic");
  assert.equal(proof.title, "Synthetic fallback");
  assert.equal(
    proof.summary,
    "No valid captured voice artifact was available, so the smoke used the configured probe audio."
  );
  assert.deepEqual(proof.evidence, ["Fixture: synthetic silence probe"]);
});

test("voice smoke proof stays pending before the Gemma streaming step runs", () => {
  const proof = buildVoiceAudioFixtureProof(
    step({
      status: "not_run",
      live_call: false,
      details: {
        audio_fixture_source: "synthetic_silence_probe",
        audio_artifact_used: false
      }
    })
  );

  assert.equal(proof.status, "pending");
  assert.equal(proof.summary, "Runtime smoke has not executed the Gemma/Kokoro audio step yet.");
});

test("voice smoke proof does not call blocked runtime smoke a synthetic fallback", () => {
  const proof = buildVoiceAudioFixtureProof(
    step({
      status: "blocked",
      blockers: ["HF_TOKEN is required."],
      details: {
        audio_fixture_source: "synthetic_silence_probe",
        audio_artifact_used: false
      }
    })
  );

  assert.equal(proof.status, "blocked");
  assert.equal(proof.title, "Runtime smoke blocked");
  assert.equal(proof.summary, "Gemma/Kokoro smoke did not run, so captured-audio proof is unavailable.");
  assert.deepEqual(proof.evidence, ["HF_TOKEN is required.", "Fixture: synthetic silence probe"]);
});

test("voice smoke proof explains missing same-session audio artifact", () => {
  const proof = buildVoiceAudioFixtureProof(
    step({
      status: "blocked",
      smoke_proof_status: "session_audio_artifact_missing",
      blockers: ["No captured voice-audio artifact is available for the requested LiveKit session."],
      next_actions: [
        "Speak into the active LiveKit room, wait for the user voice turn to materialize with a local audio artifact, then rerun session-bound live smoke."
      ],
      details: {
        audio_fixture_source: "missing_session_voice_audio_artifact",
        audio_artifact_used: false
      }
    })
  );

  assert.equal(proof.status, "blocked");
  assert.equal(
    proof.summary,
    "Session-bound smoke is waiting for a captured user voice turn from this LiveKit room."
  );
  assert.deepEqual(proof.evidence, [
    "No captured voice-audio artifact is available for the requested LiveKit session.",
    "Next: Speak into the active LiveKit room, wait for the user voice turn to materialize with a local audio artifact, then rerun session-bound live smoke.",
    "Fixture: missing session voice audio artifact"
  ]);
});

test("voice smoke proof explains stale same-session audio artifact", () => {
  const proof = buildVoiceAudioFixtureProof(
    step({
      status: "blocked",
      smoke_proof_status: "session_audio_artifact_stale",
      blockers: [
        "The latest captured voice-audio artifact for the requested LiveKit session is stale."
      ],
      next_actions: [
        "Speak into the active LiveKit room again, wait for a fresh user voice turn to materialize with a local audio artifact, then rerun session-bound live smoke."
      ],
      details: {
        audio_fixture_source: "stale_session_voice_audio_artifact",
        audio_artifact_used: false,
        stale_audio_artifact_count: 1,
        latest_stale_audio_artifact_age_seconds: 640,
        max_voice_audio_artifact_age_seconds: 60
      }
    })
  );

  assert.equal(proof.status, "blocked");
  assert.equal(
    proof.summary,
    "Session-bound smoke found only stale captured audio; speak again before rerunning live smoke."
  );
  assert.deepEqual(proof.evidence, [
    "The latest captured voice-audio artifact for the requested LiveKit session is stale.",
    "Next: Speak into the active LiveKit room again, wait for a fresh user voice turn to materialize with a local audio artifact, then rerun session-bound live smoke.",
    "Fixture: stale session voice audio artifact",
    "Age: 640s; max: 60s"
  ]);
});

test("voice smoke proof reports failed runtime smoke explicitly", () => {
  const proof = buildVoiceAudioFixtureProof(
    step({
      status: "failed",
      error: "Kokoro TTS returned no audio bytes.",
      details: {
        audio_fixture_source: "captured_voice_audio_artifact",
        audio_artifact_used: false
      }
    })
  );

  assert.equal(proof.status, "failed");
  assert.equal(proof.title, "Runtime smoke failed");
  assert.equal(proof.summary, "Gemma/Kokoro smoke failed before a usable audio proof was completed.");
  assert.deepEqual(proof.evidence, [
    "Kokoro TTS returned no audio bytes.",
    "Fixture: captured voice artifact"
  ]);
});

test("voice smoke proof keeps unknown statuses pending instead of synthetic", () => {
  const proof = buildVoiceAudioFixtureProof(
    step({
      status: "degraded",
      details: {
        audio_fixture_source: "synthetic_silence_probe",
        audio_artifact_used: false
      }
    })
  );

  assert.equal(proof.status, "pending");
  assert.equal(
    proof.summary,
    "Gemma/Kokoro smoke status is degraded; no completed audio fixture proof is available."
  );
  assert.deepEqual(proof.evidence, ["Fixture: synthetic silence probe"]);
});

test("voice streaming proof exposes hosted Kokoro transport and latency evidence", () => {
  const proof = buildVoiceStreamingProviderProof(
    step({
      details: {
        kokoro_provider: "huggingface_kokoro",
        kokoro_transport: "hf_endpoint",
        voice_agent_presence_required: true,
        voice_agent_presence_status: "ready",
        realtime_session_id: "session-1",
        gemma_model_id: "google/gemma-4-E4B-it",
        kokoro_model_id: "hexgrad/Kokoro-82M",
        gemma_ttft_ms: 42.4,
        kokoro_first_audio_ms: 89.8,
        first_audio_end_to_end_ms: 132.2
      }
    })
  );

  assert.equal(proof.status, "passed");
  assert.equal(proof.title, "Gemma/Kokoro transport");
  assert.equal(proof.summary, "Live smoke measured Gemma streaming into Kokoro speech output.");
  assert.deepEqual(proof.evidence, [
    "Kokoro: Hosted Kokoro via HF endpoint",
    "LiveKit agent presence: ready for session session-1",
    "Gemma: google/gemma-4-E4B-it",
    "TTS: hexgrad/Kokoro-82M"
  ]);
  assert.deepEqual(proof.metrics, [
    { label: "Gemma TTFT", value: "42 ms" },
    { label: "Kokoro first audio", value: "90 ms" },
    { label: "End-to-end first audio", value: "132 ms" }
  ]);
});

test("voice streaming proof exposes local Kokoro package transport", () => {
  const proof = buildVoiceStreamingProviderProof(
    step({
      details: {
        kokoro_provider: "local_kokoro",
        kokoro_transport: "local_package",
        gemma_ttft_ms: 8.25,
        kokoro_first_audio_ms: 11.2,
        first_audio_end_to_end_ms: 20.1
      }
    })
  );

  assert.equal(proof.status, "passed");
  assert.equal(proof.evidence[0], "Kokoro: Local Kokoro via local package");
  assert.deepEqual(proof.metrics, [
    { label: "Gemma TTFT", value: "8.3 ms" },
    { label: "Kokoro first audio", value: "11 ms" },
    { label: "End-to-end first audio", value: "20 ms" }
  ]);

  const fallbackProof = buildVoiceStreamingProviderProof(
    step({
      details: {
        kokoro_provider: "local_kokoro",
        kokoro_transport: "local_package",
        kokoro_endpoint_error: "KOKORO_TTS_ENDPOINT_URL must be an http(s) URL with a host."
      }
    })
  );
  assert.equal(
    fallbackProof.evidence[0],
    "Kokoro: Local Kokoro via local package; malformed hosted endpoint ignored"
  );
});

test("voice streaming proof keeps blocked and unknown statuses unproven", () => {
  const blocked = buildVoiceStreamingProviderProof(
    step({
      status: "blocked",
      blockers: ["HF_TOKEN is required.", "Kokoro endpoint or local package is required."],
      details: {
        kokoro_transport: "missing"
      }
    })
  );
  const blockedMalformed = buildVoiceStreamingProviderProof(
    step({
      status: "blocked",
      blockers: ["Kokoro endpoint or local package is required."],
      details: {
        kokoro_transport: "missing",
        kokoro_endpoint_error: "KOKORO_TTS_ENDPOINT_URL must be an http(s) URL with a host."
      }
    })
  );
  const blockedPresence = buildVoiceStreamingProviderProof(
    step({
      status: "blocked",
      blockers: ["No fresh gemma_kokoro_voice_agent_ready event is bound to the requested LiveKit session."],
      details: {
        voice_agent_presence_required: true,
        voice_agent_presence_status: "missing"
      }
    })
  );
  const unknown = buildVoiceStreamingProviderProof(
    step({
      status: "degraded",
      evidence: ["Partial setup only."]
    })
  );

  assert.equal(blocked.status, "blocked");
  assert.deepEqual(blocked.evidence, [
    "HF_TOKEN is required.",
    "Kokoro endpoint or local package is required.",
    "Kokoro: missing hosted endpoint or local package"
  ]);
  assert.deepEqual(blockedMalformed.evidence, [
    "Kokoro endpoint or local package is required.",
    "Kokoro: malformed hosted endpoint and no local package"
  ]);
  assert.deepEqual(blockedPresence.evidence, [
    "No fresh gemma_kokoro_voice_agent_ready event is bound to the requested LiveKit session.",
    "LiveKit agent presence: missing"
  ]);

  const blockedSessionAudio = buildVoiceStreamingProviderProof(
    step({
      status: "blocked",
      blockers: ["No captured voice-audio artifact is available for the requested LiveKit session."],
      next_actions: ["Speak into the active LiveKit room, then rerun session-bound live smoke."],
      details: {
        voice_agent_presence_required: true,
        voice_agent_presence_status: "ready",
        realtime_session_id: "session-1"
      }
    })
  );
  assert.deepEqual(blockedSessionAudio.evidence, [
    "No captured voice-audio artifact is available for the requested LiveKit session.",
    "Next: Speak into the active LiveKit room, then rerun session-bound live smoke.",
    "LiveKit agent presence: ready for session session-1"
  ]);
  assert.equal(unknown.status, "pending");
  assert.equal(
    unknown.summary,
    "Gemma/Kokoro smoke status is degraded; no completed transport proof is available."
  );
});

test("streaming smoke lookup does not borrow another provider step", () => {
  const smoke: ProviderSmokeRunResult = {
    run_id: "run-1",
    status: "passed",
    execute_live_calls: true,
    provider_readiness: providerReadiness,
    step_count: 2,
    passed_count: 1,
    blocked_count: 0,
    failed_count: 0,
    not_run_count: 1,
    tool_boundary_count: 0,
    source_ids: [],
    realtime_session_ids: [],
    provider_configuration_followup_message_ids: [],
    steps: [
      step({ step_id: "selected-realtime-smoke" }),
      step({ step_id: "gemma-kokoro-voice-streaming-smoke", details: { audio_artifact_used: true } })
    ],
    ledger_artifact_id: null,
    event_id: null,
    summary: "ok"
  };

  assert.equal(findGemmaKokoroStreamingSmokeStep(smoke)?.step_id, "gemma-kokoro-voice-streaming-smoke");
});

test("voice proof formatting keeps compact byte and hash labels", () => {
  assert.equal(formatAudioBytes(null), "");
  assert.equal(formatAudioBytes(512), "512 B");
  assert.equal(formatAudioBytes(1536), "1.5 KB");
  assert.equal(formatAudioBytes(10 * 1024), "10 KB");
  assert.equal(shortSha256("abcdef1234567890"), "abcdef123456...");
});
