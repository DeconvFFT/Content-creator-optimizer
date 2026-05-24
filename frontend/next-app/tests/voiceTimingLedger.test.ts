import assert from "node:assert/strict";
import test from "node:test";

import {
  buildVoiceTimingGap,
  buildVoiceTimingStageProofs,
  buildVoiceTimingTurnProof,
  formatLatencyMs
} from "../lib/voice/timingLedger";
import type { RealtimeVoiceTimingLedgerResult } from "../lib/api/types";

function ledger(overrides: Partial<RealtimeVoiceTimingLedgerResult> = {}): RealtimeVoiceTimingLedgerResult {
  return {
    run_id: "run-1",
    status: "needs_more_evidence",
    session_count: 1,
    event_count: 6,
    measured_stage_count: 2,
    missing_stage_count: 1,
    stages: [
      {
        stage_id: "gemma_response_start",
        title: "OpenRouter response generation starts",
        status: "measured",
        latency_ms: 42.4,
        evidence: [
          "Found OpenRouter generation-start evidence for the same response (legacy persisted event type: gemma_generation_started)."
        ],
        missing_evidence: [],
        event_ids: [4, 5]
      },
      {
        stage_id: "first_audio_out",
        title: "First Kokoro audio reaches LiveKit output",
        status: "missing",
        evidence: [],
        missing_evidence: [
          "No correlated OpenRouter generation-start and assistant_audio_chunk_published event pair was found (legacy persisted generation event type: gemma_generation_started)."
        ],
        event_ids: []
      }
    ],
    turns: [
      {
        turn_id: "turn-1",
        response_id: "response-1",
        realtime_session_id: "session-1",
        speech_start_to_turn_commit_ms: 650,
        turn_commit_to_agent_turn_ms: 21.2,
        speech_start_to_turn_start_ms: 671.2,
        turn_start_to_gemma_start_ms: 9.4,
        gemma_start_to_first_text_ms: 118.6,
        gemma_start_to_first_audio_ms: 412.9,
        turn_start_to_first_audio_ms: 422.3,
        barge_in_to_cancelled_ms: null,
        event_ids: [1, 2, 3, 4, 5]
      }
    ],
    recommended_next_actions: [
      "Persist assistant_audio_chunk_published for the same OpenRouter/Kokoro response."
    ],
    ledger_artifact_id: null,
    event_id: null,
    summary: "Realtime voice timing ledger is needs_more_evidence.",
    ...overrides
  };
}

test("voice timing stage proof preserves measured and missing stage evidence", () => {
  const proof = buildVoiceTimingStageProofs(ledger());

  assert.equal(proof.length, 2);
  assert.deepEqual(proof[0], {
    stageId: "gemma_response_start",
    title: "OpenRouter response generation starts",
    status: "measured",
    latency: "42 ms",
    detail: "Found OpenRouter generation-start evidence for the same response (legacy persisted event type: gemma_generation_started)."
  });
  assert.equal(proof[1].status, "missing");
  assert.equal(proof[1].latency, "");
  assert.match(proof[1].detail, /assistant_audio_chunk_published/);
});

test("voice timing turn proof exposes latest turn latency chain", () => {
  const proof = buildVoiceTimingTurnProof(ledger());

  assert.equal(proof?.title, "Latest voice turn response-1");
  assert.deepEqual(proof?.metrics, [
    { label: "Speech -> turn commit", value: "650 ms" },
    { label: "Turn commit -> agent", value: "21 ms" },
    { label: "Agent -> OpenRouter", value: "9.4 ms" },
    { label: "OpenRouter -> first text", value: "119 ms" },
    { label: "OpenRouter -> first audio", value: "413 ms" },
    { label: "Agent -> first audio", value: "422 ms" }
  ]);
});

test("voice timing proof stays quiet until a ledger exists", () => {
  assert.deepEqual(buildVoiceTimingStageProofs(null), []);
  assert.equal(buildVoiceTimingTurnProof(ledger({ turns: [] })), null);
});

test("voice timing proof explains missing LiveKit media bridge without raw event names", () => {
  const proof = buildVoiceTimingStageProofs(
    ledger({
      stages: [
        {
          stage_id: "livekit_audio_track_bridge",
          title: "LiveKit audio track is bridged to Rust VAD",
          status: "missing",
          latency_ms: null,
          evidence: [],
          missing_evidence: [
            "No voice_agent_media_bridge_ready event was found. The timing ledger needs proof that the backend participant subscribed to the creator audio track."
          ],
          event_ids: []
        }
      ],
      recommended_next_actions: [
        "No voice_agent_media_bridge_ready event was found. The timing ledger needs proof that the backend participant subscribed to the creator audio track."
      ]
    })
  );

  assert.equal(proof[0].stageId, "livekit_audio_track_bridge");
  assert.equal(proof[0].status, "missing");
  assert.match(proof[0].detail, /backend agent has not confirmed/);
  assert.doesNotMatch(proof[0].detail, /voice_agent_media_bridge_ready/);

  const gap = buildVoiceTimingGap(
    ledger({
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
      recommended_next_actions: [
        "No voice_agent_media_bridge_ready event was found."
      ]
    })
  );

  assert.match(gap ?? "", /Speak in the active LiveKit room/);
  assert.doesNotMatch(gap ?? "", /voice_agent_media_bridge_ready/);
});

test("voice timing gap prioritizes failed provider recovery over missing media bridge", () => {
  const gap = buildVoiceTimingGap(
    ledger({
      status: "failed",
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
      recommended_next_actions: [
        "No voice_agent_media_bridge_ready event was found.",
        "Fix the Gemma/Kokoro provider route and rerun live provider smoke before treating this voice session as ready."
      ]
    })
  );

  assert.match(gap ?? "", /Fix the Gemma\/Kokoro provider route/);
  assert.doesNotMatch(gap ?? "", /Speak in the active LiveKit room/);
});

test("voice timing latency formatting stays compact across ranges", () => {
  assert.equal(formatLatencyMs(null), "");
  assert.equal(formatLatencyMs(-1), "invalid latency");
  assert.equal(formatLatencyMs(3.25), "3.3 ms");
  assert.equal(formatLatencyMs(42.4), "42 ms");
  assert.equal(formatLatencyMs(1540), "1.5 s");
  assert.equal(formatLatencyMs(10_400), "10 s");
});
