import assert from "node:assert/strict";
import test from "node:test";

import {
  buildRunEventStreamSummary,
  buildStreamedRunRefreshSummary,
  shouldRefreshRunForStreamEvent
} from "../lib/state/runEventRefresh";
import type { RunEvent } from "../lib/api/types";

function event(eventType: string, eventId = 42): RunEvent {
  return {
    event_id: eventId,
    run_id: "run-1",
    event_type: eventType,
    actor: "agent-harness-engineer",
    payload: {},
    created_at: "2026-05-18T12:00:00Z"
  };
}

test("streamed run refresh follows durable run-state mutation events", () => {
  for (const eventType of [
    "artifact_recorded",
    "source_recorded",
    "claim_recorded",
    "agent_message_dependency_waiting",
    "agent_message_recovered",
    "agent_message_retry_exhausted",
    "agent_message_status_updated",
    "worker_profile_heartbeat",
    "worker_scheduler_pass_completed",
    "voice_user_turn_committed",
    "feedback_resolved",
    "content_writer_artifacts_created"
  ]) {
    assert.equal(shouldRefreshRunForStreamEvent(event(eventType)), true, eventType);
  }
});

test("streamed run refresh ignores high-frequency voice stream-only events", () => {
  for (const eventType of [
    "assistant_text_delta",
    "assistant_audio_chunk_published",
    "gemma_generation_started",
    "voice_user_speech_started"
  ]) {
    assert.equal(shouldRefreshRunForStreamEvent(event(eventType)), false, eventType);
  }
});

test("streamed run refresh summary names the triggering event", () => {
  assert.equal(
    buildStreamedRunRefreshSummary(event("worker_scheduler_pass_completed", 77)),
    "Live context refreshed after background check #77."
  );
});

test("live run event stream summary hides raw internal event names", () => {
  const summary = buildRunEventStreamSummary(event("worker_scheduler_pass_completed", 77));

  assert.equal(summary, "Live update: background check #77");
  assert.doesNotMatch(summary, /worker_scheduler_pass_completed/);
  assert.doesNotMatch(summary, /event #/);
});
