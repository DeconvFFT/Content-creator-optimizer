import assert from "node:assert/strict";
import test from "node:test";

import { voiceFollowupContinuationForEvent } from "../lib/voice/followup";

test("voice follow-up continuation targets provider recovery agents without Gemma", () => {
  const continuation = voiceFollowupContinuationForEvent({
    run_id: "run-1",
    realtime_session_id: "session-1",
    event_id: 12,
    event_type: "gemma_kokoro_voice_turn_failed",
    followup_task_message_id: "message-1",
    followup_kind: "provider_failure_recovery",
    followup_worker_agent_ids: [
      "inference-systems-engineer",
      "observability-agent",
      "agent-harness-engineer"
    ],
    followup_worker_use_gemma: false,
    summary: "Recorded provider failure."
  });

  assert.equal(continuation.label, "Provider recovery queued");
  assert.match(continuation.detail, /Inference, Observability, and Harness/);
  assert.deepEqual(continuation.options.agentIds, [
    "inference-systems-engineer",
    "observability-agent",
    "agent-harness-engineer"
  ]);
  assert.deepEqual(continuation.options.messageIds, ["message-1"]);
  assert.equal(continuation.options.continueMessageLineage, true);
  assert.equal(continuation.options.useGemma, false);
});

test("voice follow-up continuation leaves normal assistant follow-ups on default worker routing", () => {
  const continuation = voiceFollowupContinuationForEvent({
    run_id: "run-1",
    realtime_session_id: "session-1",
    event_id: 13,
    event_type: "assistant_response_completed",
    materialized_speaker: "assistant",
    followup_task_message_id: "message-2",
    followup_kind: "realtime_turn_context",
    followup_worker_agent_ids: [],
    followup_worker_use_gemma: null,
    summary: "Recorded assistant event."
  });

  assert.equal(continuation.label, "Voice follow-up queued");
  assert.match(continuation.detail, /assistant voice response/);
  assert.deepEqual(continuation.options.agentIds, []);
  assert.deepEqual(continuation.options.messageIds, ["message-2"]);
  assert.equal(continuation.options.continueMessageLineage, true);
  assert.equal(continuation.options.useGemma, null);
});
