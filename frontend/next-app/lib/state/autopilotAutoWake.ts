import type { WorkerProfile } from "@/lib/api/types";
import {
  buildAutopilotScheduleStatus,
  type AutopilotScheduleStatus
} from "./autopilotSchedule";
import {
  isActiveAutopilotProfile,
  latestActiveAutopilotProfile
} from "./autopilotProfile";

export type AutopilotAutoWakeDecision = {
  shouldRun: boolean;
  reason:
    | "disabled"
    | "missing_run"
    | "busy"
    | "in_flight"
    | "no_active_profile"
    | "not_due"
    | "already_attempted"
    | "due";
  profile?: WorkerProfile | null;
  schedule?: AutopilotScheduleStatus | null;
  wakeKey?: string | null;
};

export type AutopilotAutoWakeInput = {
  runId?: string | null;
  workerProfiles?: WorkerProfile[] | null;
  enabled: boolean;
  busy?: boolean;
  now?: Date;
  inFlightRunIds?: Iterable<string>;
  lastWakeKey?: string | null;
};

export function buildAutopilotAutoWakeDecision(
  input: AutopilotAutoWakeInput
): AutopilotAutoWakeDecision {
  if (!input.enabled) {
    return { shouldRun: false, reason: "disabled" };
  }
  if (!input.runId) {
    return { shouldRun: false, reason: "missing_run" };
  }
  if (input.busy) {
    return { shouldRun: false, reason: "busy" };
  }
  if (isRunInFlight(input.inFlightRunIds, input.runId)) {
    return { shouldRun: false, reason: "in_flight" };
  }

  const profile = activeDueAutopilotProfile(
    input.workerProfiles ?? [],
    input.runId,
    input.now ?? new Date()
  ) ?? latestActiveAutopilotProfile(input.workerProfiles ?? [], input.runId);
  if (!profile) {
    return { shouldRun: false, reason: "no_active_profile" };
  }

  const schedule = buildAutopilotScheduleStatus(profile, input.now ?? new Date());
  if (schedule?.state !== "due") {
    return { shouldRun: false, reason: "not_due", profile, schedule };
  }

  const wakeKey = buildAutopilotWakeKey(input.runId, profile, schedule);
  if (wakeKey === input.lastWakeKey) {
    return { shouldRun: false, reason: "already_attempted", profile, schedule, wakeKey };
  }

  return { shouldRun: true, reason: "due", profile, schedule, wakeKey };
}

function activeDueAutopilotProfile(
  workerProfiles: WorkerProfile[],
  runId: string,
  now: Date
) {
  return latestActiveAutopilotProfile(
    workerProfiles.filter((profile) => {
      if (profile.run_id !== runId || !isActiveAutopilotProfile(profile)) {
        return false;
      }
      return buildAutopilotScheduleStatus(profile, now)?.state === "due";
    }),
    runId
  );
}

function isRunInFlight(inFlightRunIds: Iterable<string> | undefined, runId: string) {
  if (!inFlightRunIds) {
    return false;
  }
  for (const inFlightRunId of inFlightRunIds) {
    if (inFlightRunId === runId) {
      return true;
    }
  }
  return false;
}

function buildAutopilotWakeKey(
  runId: string,
  profile: WorkerProfile,
  schedule: AutopilotScheduleStatus
) {
  return [
    runId,
    profile.profile_id,
    profile.last_heartbeat_at ?? "no-heartbeat",
    profile.poll_interval_seconds,
    schedule.nextDueAt ?? "due-now"
  ].join(":");
}
