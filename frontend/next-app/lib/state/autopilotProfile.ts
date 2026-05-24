import type { WorkerProfile } from "@/lib/api/types";

const ACTIVE_AUTOPILOT_STATUSES = new Set(["active", "running", "started"]);

function profileCreatedMs(profile: WorkerProfile) {
  const parsed = Date.parse(profile.created_at);
  return Number.isFinite(parsed) ? parsed : 0;
}

function isAutopilotProfile(profile: WorkerProfile, runId?: string | null) {
  return (
    profile.execution_mode === "autonomous_pass" &&
    (!runId || profile.run_id === runId)
  );
}

export function isActiveAutopilotProfile(profile: WorkerProfile) {
  return ACTIVE_AUTOPILOT_STATUSES.has(profile.status);
}

export function latestAutopilotProfile(
  workerProfiles: WorkerProfile[],
  runId?: string | null
) {
  return newestProfile(
    workerProfiles.filter((profile) => isAutopilotProfile(profile, runId))
  );
}

export function latestActiveAutopilotProfile(
  workerProfiles: WorkerProfile[],
  runId?: string | null
) {
  return newestProfile(
    workerProfiles.filter(
      (profile) =>
        isAutopilotProfile(profile, runId) && isActiveAutopilotProfile(profile)
    )
  );
}

function newestProfile(profiles: WorkerProfile[]) {
  return profiles
    .slice()
    .sort((left, right) => {
      const byCreatedAt = profileCreatedMs(right) - profileCreatedMs(left);
      return byCreatedAt || right.profile_id.localeCompare(left.profile_id);
    })[0] ?? null;
}
