import type { RunEvent } from "@/lib/api/types";
import { statusLabel } from "./format";

const REFRESH_EVENT_SUFFIXES = [
  "_accepted",
  "_active",
  "_blocked",
  "_built",
  "_committed",
  "_completed",
  "_created",
  "_gated",
  "_generated",
  "_ingested",
  "_materialized",
  "_recorded",
  "_repaired",
  "_resolved",
  "_reused",
  "_revised",
  "_routed",
  "_updated"
];

const STREAM_ONLY_EVENT_TYPES = new Set([
  "heartbeat",
  "assistant_audio_chunk_published",
  "assistant_text_delta",
  "gemma_generation_started",
  "gemma_kokoro_voice_turn_started",
  "voice_user_speech_started"
]);

const REFRESH_EVENT_TYPES = new Set([
  "agent_message_dependency_waiting",
  "agent_message_recovered",
  "agent_message_retry_exhausted",
  "worker_profile_heartbeat"
]);

export const STREAMED_RUN_REFRESH_DEBOUNCE_MS = 750;

export function shouldRefreshRunForStreamEvent(event: RunEvent) {
  if (STREAM_ONLY_EVENT_TYPES.has(event.event_type)) {
    return false;
  }
  if (REFRESH_EVENT_TYPES.has(event.event_type)) {
    return true;
  }
  return REFRESH_EVENT_SUFFIXES.some((suffix) => event.event_type.endsWith(suffix));
}

const CREATOR_EVENT_LABELS: Record<string, string> = {
  artifact_recorded: "artifact saved",
  source_recorded: "source saved",
  claim_recorded: "claim updated",
  agent_message_dependency_waiting: "specialist waiting on prerequisite",
  agent_message_recovered: "specialist task recovered",
  agent_message_retry_exhausted: "specialist needs attention",
  agent_message_status_updated: "specialist status updated",
  worker_profile_heartbeat: "specialist pulse",
  worker_scheduler_pass_completed: "background check",
  voice_user_turn_committed: "voice turn saved",
  feedback_resolved: "feedback resolved",
  content_writer_artifacts_created: "drafts saved"
};

export function creatorRunEventLabel(eventType: string) {
  return CREATOR_EVENT_LABELS[eventType] ?? statusLabel(eventType)
    .replace(/\bagent message\b/g, "specialist task")
    .replace(/\bworker scheduler\b/g, "background runner")
    .replace(/\bworker profile heartbeat\b/g, "specialist pulse");
}

export function buildRunEventStreamSummary(event: RunEvent) {
  return `Live update: ${creatorRunEventLabel(event.event_type)} #${event.event_id}`;
}

export function buildStreamedRunRefreshSummary(event: RunEvent) {
  return `Live context refreshed after ${creatorRunEventLabel(event.event_type)} #${event.event_id}.`;
}
