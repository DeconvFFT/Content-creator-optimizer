import assert from "node:assert/strict";
import test from "node:test";

import { buildLiveVoiceProofPath } from "../lib/voice/liveVoiceProofPath";
import type { RealtimeVoiceTimingLedgerResult } from "../lib/api/types";
import type { VoiceProviderReleaseGate } from "../lib/voice/providerReadiness";
import type {
  VoiceAudioFixtureProof,
  VoiceStreamingProviderProof
} from "../lib/voice/providerSmoke";

function gate(overrides: Partial<VoiceProviderReleaseGate> = {}): VoiceProviderReleaseGate {
  return {
    status: "ready",
    label: "Provider release gate",
    summary: "Provider-backed Gemma/Kokoro voice is release-ready for this run.",
    checks: [
      {
        id: "live-smoke",
        label: "Live Gemma/Kokoro smoke",
        status: "ready",
        detail: "Provider-backed Gemma/Kokoro voice streaming smoke passed."
      }
    ],
    missingEnv: [],
    secretFiles: [],
    secretFileGuidance: [],
    ...overrides
  };
}

const capturedAudio: VoiceAudioFixtureProof = {
  status: "captured",
  title: "Captured audio proof",
  summary: "Gemma smoke used persisted microphone PCM from the bound LiveKit session.",
  evidence: ["Artifact: voice-audio/run/session/turn.pcm"]
};

const syntheticAudio: VoiceAudioFixtureProof = {
  status: "synthetic",
  title: "Synthetic fallback",
  summary: "No valid captured voice artifact was available.",
  evidence: ["Fixture: synthetic silence probe"]
};

const streamingPassed: VoiceStreamingProviderProof = {
  status: "passed",
  title: "Gemma/Kokoro transport",
  summary: "Live smoke measured Gemma streaming into Kokoro speech output.",
  evidence: ["Gemma: google/gemma-4-E4B-it", "TTS: hexgrad/Kokoro-82M"],
  metrics: [{ label: "End-to-end first audio", value: "132 ms" }]
};

function timing(
  overrides: Partial<RealtimeVoiceTimingLedgerResult> = {}
): RealtimeVoiceTimingLedgerResult {
  return {
    run_id: "run-1",
    status: "ready",
    session_count: 1,
    event_count: 9,
    measured_stage_count: 7,
    missing_stage_count: 0,
    stages: [
      {
        stage_id: "first_audio_out",
        title: "First Kokoro audio reaches LiveKit output",
        status: "measured",
        latency_ms: 132,
        evidence: ["assistant_audio_chunk_published is correlated."],
        missing_evidence: [],
        event_ids: [1, 2]
      }
    ],
    turns: [],
    recommended_next_actions: [],
    ledger_artifact_id: null,
    event_id: null,
    summary: "Realtime voice timing ledger is ready.",
    ...overrides
  };
}

test("live voice proof path is ready only after captured audio streaming and timing proof", () => {
  const path = buildLiveVoiceProofPath({
    providerReleaseGate: gate(),
    audioFixtureProof: capturedAudio,
    streamingProviderProof: streamingPassed,
    timing: timing()
  });

  assert.equal(path.status, "ready");
  assert.equal(path.primaryAction, undefined);
  assert.equal(path.steps.every((step) => step.status === "ready"), true);
  assert.match(path.summary, /Captured microphone audio/);
});

test("live voice proof path does not treat synthetic smoke as voice-to-voice proof", () => {
  const path = buildLiveVoiceProofPath({
    providerReleaseGate: gate(),
    audioFixtureProof: syntheticAudio,
    streamingProviderProof: streamingPassed,
    timing: timing()
  });

  assert.equal(path.status, "needs_captured_audio");
  assert.equal(path.primaryAction, "run_live_smoke");
  assert.equal(path.primaryActionLabel, "Run live smoke");
  assert.match(path.summary, /synthetic audio/);
  assert.match(path.nextAction ?? "", /Speak in the active LiveKit room/);
});

test("live voice proof path requires a ready timing ledger after smoke proof", () => {
  const path = buildLiveVoiceProofPath({
    providerReleaseGate: gate(),
    audioFixtureProof: capturedAudio,
    streamingProviderProof: streamingPassed,
    timing: timing({
      status: "needs_more_evidence",
      missing_stage_count: 1,
      summary: "Realtime voice timing ledger is needs_more_evidence.",
      recommended_next_actions: ["Persist assistant_audio_chunk_published."]
    })
  });

  assert.equal(path.status, "needs_timing");
  assert.equal(path.primaryAction, "build_timing_ledger");
  assert.equal(path.primaryActionLabel, "Build timing ledger");
  assert.equal(path.nextAction, "Persist assistant_audio_chunk_published.");
});

test("live voice proof path gives a creator action for missing media bridge timing", () => {
  const path = buildLiveVoiceProofPath({
    providerReleaseGate: gate(),
    audioFixtureProof: capturedAudio,
    streamingProviderProof: streamingPassed,
    timing: timing({
      status: "needs_more_evidence",
      missing_stage_count: 1,
      stages: [
        {
          stage_id: "livekit_audio_track_bridge",
          title: "LiveKit audio track is bridged to Rust VAD",
          status: "missing",
          latency_ms: null,
          evidence: [],
          missing_evidence: [
            "No voice_agent_media_bridge_ready event was found."
          ],
          event_ids: []
        }
      ],
      summary: "Realtime voice timing ledger is needs_more_evidence.",
      recommended_next_actions: [
        "No voice_agent_media_bridge_ready event was found."
      ]
    })
  });

  assert.equal(path.status, "needs_timing");
  assert.equal(path.primaryAction, "build_timing_ledger");
  assert.match(path.summary, /backend agent has not confirmed/);
  assert.match(path.nextAction ?? "", /Speak in the active LiveKit room/);
  assert.doesNotMatch(path.nextAction ?? "", /voice_agent_media_bridge_ready/);
});

test("live voice proof path keeps provider recovery action for failed timing ledger", () => {
  const path = buildLiveVoiceProofPath({
    providerReleaseGate: gate(),
    audioFixtureProof: capturedAudio,
    streamingProviderProof: streamingPassed,
    timing: timing({
      status: "failed",
      missing_stage_count: 1,
      stages: [
        {
          stage_id: "livekit_audio_track_bridge",
          title: "LiveKit audio track is bridged to Rust VAD",
          status: "missing",
          latency_ms: null,
          evidence: [],
          missing_evidence: ["No voice_agent_media_bridge_ready event was found."],
          event_ids: []
        },
        {
          stage_id: "voice_turn_failed",
          title: "Gemma/Kokoro voice turn failed",
          status: "failed",
          latency_ms: null,
          evidence: ["Gemma/Kokoro voice turn failed during gemma_generation."],
          missing_evidence: [
            "Fix the Gemma/Kokoro provider route and rerun live provider smoke before treating this voice session as ready."
          ],
          event_ids: [9]
        }
      ],
      turns: [
        {
          turn_id: "turn-failed",
          response_id: "response-failed",
          realtime_session_id: "session-1",
          speech_start_to_turn_commit_ms: null,
          turn_commit_to_agent_turn_ms: null,
          speech_start_to_turn_start_ms: null,
          turn_start_to_gemma_start_ms: null,
          gemma_start_to_first_text_ms: null,
          gemma_start_to_first_audio_ms: null,
          turn_start_to_first_audio_ms: null,
          barge_in_to_cancelled_ms: null,
          failure_stage: "gemma_generation",
          failure_reason: "Gemma 4 streaming request failed.",
          failed_at_ms: 80,
          event_ids: [7, 8, 9]
        }
      ],
      recommended_next_actions: [
        "No voice_agent_media_bridge_ready event was found.",
        "Fix the Gemma/Kokoro provider route and rerun live provider smoke before treating this voice session as ready."
      ],
      summary: "Realtime voice timing ledger is failed."
    })
  });

  assert.equal(path.status, "blocked");
  assert.match(path.summary, /Gemma 4 streaming request failed/);
  assert.match(path.nextAction ?? "", /Fix the Gemma\/Kokoro provider route/);
  assert.doesNotMatch(path.nextAction ?? "", /Speak in the active LiveKit room/);
});

test("live voice proof path prioritizes provider release blockers", () => {
  const path = buildLiveVoiceProofPath({
    providerReleaseGate: gate({
      status: "blocked",
      summary: "HF_TOKEN_FILE points to a missing file.",
      checks: [
        {
          id: "gemma-primary",
          label: "Gemma expert endpoint",
          status: "blocked",
          detail: "Gemma endpoint is missing HF_TOKEN_FILE.",
          nextAction: "Configure HF_TOKEN_FILE."
        }
      ]
    }),
    audioFixtureProof: capturedAudio,
    streamingProviderProof: streamingPassed,
    timing: timing()
  });

  assert.equal(path.status, "blocked");
  assert.equal(path.primaryAction, "refresh_provider_readiness");
  assert.equal(path.primaryActionLabel, "Refresh provider readiness");
  assert.equal(path.nextAction, "Configure HF_TOKEN_FILE.");
});

test("live voice proof path maps runtime session presence and smoke blockers to executable actions", () => {
  const runtimePath = buildLiveVoiceProofPath({
    providerReleaseGate: gate({
      status: "needs_runtime",
      summary: "Run Runtime preflight.",
      checks: [
        {
          id: "runtime",
          label: "Runtime preflight",
          status: "needs_runtime",
          detail: "Runtime preflight has not run.",
          nextAction: "Run Runtime preflight."
        }
      ]
    }),
    audioFixtureProof: capturedAudio,
    streamingProviderProof: streamingPassed,
    timing: timing()
  });
  const sessionPath = buildLiveVoiceProofPath({
    providerReleaseGate: gate({
      status: "needs_runtime",
      summary: "Join the Gemma/Kokoro voice room.",
      checks: [
        {
          id: "active-session",
          label: "Active LiveKit session",
          status: "needs_runtime",
          detail: "No active provider-backed session.",
          nextAction: "Join the Gemma/Kokoro voice room."
        }
      ]
    }),
    audioFixtureProof: capturedAudio,
    streamingProviderProof: streamingPassed,
    timing: timing()
  });
  const presencePath = buildLiveVoiceProofPath({
    providerReleaseGate: gate({
      status: "needs_runtime",
      summary: "Probe agent presence.",
      checks: [
        {
          id: "presence",
          label: "Agent participant",
          status: "needs_runtime",
          detail: "No participant proof.",
          nextAction: "Probe agent presence."
        }
      ]
    }),
    audioFixtureProof: capturedAudio,
    streamingProviderProof: streamingPassed,
    timing: timing()
  });
  const smokePath = buildLiveVoiceProofPath({
    providerReleaseGate: gate({
      status: "needs_live_smoke",
      summary: "Run live Runtime smoke.",
      checks: [
        {
          id: "live-smoke",
          label: "Live Gemma/Kokoro smoke",
          status: "needs_live_smoke",
          detail: "No live smoke proof.",
          nextAction: "Run live Runtime smoke."
        }
      ]
    }),
    audioFixtureProof: capturedAudio,
    streamingProviderProof: streamingPassed,
    timing: timing()
  });

  assert.equal(runtimePath.primaryAction, "run_runtime_preflight");
  assert.equal(sessionPath.primaryAction, "join_room");
  assert.equal(presencePath.primaryAction, "probe_presence");
  assert.equal(smokePath.primaryAction, "run_live_smoke");
});
