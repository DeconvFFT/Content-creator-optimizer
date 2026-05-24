import type { ArtifactRecord, RunEvent, WorkerProfile } from "@/lib/api/types";
import { latestActiveAutopilotProfile, latestAutopilotProfile } from "./autopilotProfile";

const HEARTBEAT_EVENT_TYPES = new Set([
  "worker_profile_heartbeat",
  "worker_profile_heartbeat_blocked"
]);

type JsonRecord = Record<string, unknown>;

export type AutopilotEvidence = {
  profile?: WorkerProfile | null;
  heartbeatState: string;
  processedTasks?: number | null;
  idle?: boolean | null;
  skipped?: boolean | null;
  skippedReason?: string | null;
  blockedReasons: string[];
  ledgerArtifactId?: string | null;
  ledgerTitle?: string | null;
  workPlanArtifactId?: string | null;
  contextPacketArtifactId?: string | null;
  realtimeDialogueStatus?: string | null;
  feedbackResolutionStatus?: string | null;
  source: "heartbeat_ledger_artifact" | "heartbeat_event";
};

export function buildAutopilotEvidence(input: {
  workerProfiles: WorkerProfile[];
  artifacts: ArtifactRecord[];
  events: RunEvent[];
}): AutopilotEvidence | null {
  const profile =
    latestActiveAutopilotProfile(input.workerProfiles) ??
    latestAutopilotProfile(input.workerProfiles);
  if (!profile) {
    return null;
  }
  const ledger = latestMatchingHeartbeatLedger(input.artifacts, profile.profile_id);
  if (ledger) {
    return evidenceFromLedger(ledger, profile);
  }

  const event = latestMatchingHeartbeatEvent(input.events, profile.profile_id);
  if (event) {
    return evidenceFromEvent(event, profile);
  }

  return null;
}

function latestMatchingHeartbeatLedger(
  artifacts: ArtifactRecord[],
  profileId: string
) {
  const ledgers = [...artifacts]
    .filter((artifact) => artifact.artifact_type === "worker_profile_heartbeat_ledger")
    .sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at));
  return ledgers.find((artifact) => profileIdFromArtifact(artifact) === profileId) ?? null;
}

function latestMatchingHeartbeatEvent(events: RunEvent[], profileId: string) {
  const heartbeatEvents = [...events]
    .filter((event) => HEARTBEAT_EVENT_TYPES.has(event.event_type))
    .sort((left, right) => {
      const byTime = Date.parse(right.created_at) - Date.parse(left.created_at);
      return byTime || right.event_id - left.event_id;
    });
  return (
    heartbeatEvents.find((event) => stringValue(event.payload.profile_id) === profileId) ??
    null
  );
}

function evidenceFromLedger(
  artifact: ArtifactRecord,
  profile?: WorkerProfile | null
): AutopilotEvidence {
  const linkedArtifacts = recordValue(artifact.content.linked_artifacts);
  const loopLedgers = recordValue(artifact.content.loop_ledgers);
  return {
    profile,
    heartbeatState: stringValue(artifact.content.heartbeat_state) ?? "recorded",
    processedTasks: numberValue(artifact.content.processed_tasks),
    idle: booleanValue(artifact.content.idle),
    skipped: booleanValue(artifact.content.skipped),
    skippedReason: stringValue(artifact.content.skipped_reason),
    blockedReasons: stringArray(artifact.content.blocked_reasons),
    ledgerArtifactId: artifact.artifact_id,
    ledgerTitle: artifact.title,
    workPlanArtifactId: stringValue(linkedArtifacts.work_plan_artifact_id),
    contextPacketArtifactId: stringValue(linkedArtifacts.context_packet_artifact_id),
    realtimeDialogueStatus: stringValue(loopLedgers.realtime_dialogue_status),
    feedbackResolutionStatus: stringValue(loopLedgers.feedback_resolution_status),
    source: "heartbeat_ledger_artifact"
  };
}

function evidenceFromEvent(
  event: RunEvent,
  profile?: WorkerProfile | null
): AutopilotEvidence {
  return {
    profile,
    heartbeatState:
      event.event_type === "worker_profile_heartbeat_blocked" ? "blocked" : "completed",
    processedTasks: numberValue(event.payload.total_processed_tasks),
    idle: booleanValue(event.payload.idle),
    skipped: null,
    skippedReason: stringValue(event.payload.skipped_reason),
    blockedReasons: stringArray(event.payload.blocked_reasons),
    ledgerArtifactId: stringValue(event.payload.heartbeat_ledger_artifact_id),
    workPlanArtifactId: stringValue(event.payload.work_plan_artifact_id),
    contextPacketArtifactId: stringValue(event.payload.context_packet_artifact_id),
    realtimeDialogueStatus: stringValue(event.payload.realtime_dialogue_status),
    feedbackResolutionStatus: stringValue(event.payload.feedback_resolution_status),
    source: "heartbeat_event"
  };
}

function profileIdFromArtifact(artifact: ArtifactRecord) {
  const profile = recordValue(artifact.content.profile);
  return stringValue(profile.profile_id) ?? stringValue(artifact.provenance.profile_id);
}

function recordValue(value: unknown): JsonRecord {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonRecord)
    : {};
}

function stringValue(value: unknown) {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function numberValue(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function booleanValue(value: unknown) {
  return typeof value === "boolean" ? value : null;
}

function stringArray(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.length > 0)
    : [];
}
