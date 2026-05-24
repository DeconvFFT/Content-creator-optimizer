import type { WorkerProfile } from "@/lib/api/types";

const ACTIVE_PROFILE_STATUSES = new Set(["active", "running", "started"]);

export type AutopilotScheduleStatus = {
  state: "off" | "running" | "due" | "scheduled";
  label: string;
  detail: string;
  nextDueAt?: string | null;
  leaseUntil?: string | null;
  claimedBy?: string | null;
};

function dateMs(value?: string | null) {
  if (!value) {
    return null;
  }
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function safeIntervalMs(profile: WorkerProfile) {
  return Math.max(1, profile.poll_interval_seconds || 0) * 1000;
}

export function buildAutopilotScheduleStatus(
  profile: WorkerProfile | null | undefined,
  now: Date = new Date()
): AutopilotScheduleStatus | null {
  if (!profile) {
    return null;
  }
  if (!ACTIVE_PROFILE_STATUSES.has(profile.status)) {
    return {
      state: "off",
      label: "Not running",
      detail: `Profile is ${profile.status}.`
    };
  }

  const nowMs = now.getTime();
  const leaseUntilMs = dateMs(profile.heartbeat_lease_until);
  if (leaseUntilMs !== null && leaseUntilMs > nowMs) {
    return {
      state: "running",
      label: "Heartbeat running",
      detail: profile.heartbeat_claimed_by
        ? `Lease held by ${profile.heartbeat_claimed_by}.`
        : "Heartbeat lease is active.",
      leaseUntil: profile.heartbeat_lease_until ?? null,
      claimedBy: profile.heartbeat_claimed_by ?? null
    };
  }

  const lastHeartbeatMs = dateMs(profile.last_heartbeat_at);
  if (lastHeartbeatMs === null) {
    return {
      state: "due",
      label: "Due now",
      detail: "No heartbeat has completed yet."
    };
  }

  const nextDueMs = lastHeartbeatMs + safeIntervalMs(profile);
  if (nextDueMs <= nowMs) {
    return {
      state: "due",
      label: "Due now",
      detail: "Heartbeat interval has elapsed.",
      nextDueAt: new Date(nextDueMs).toISOString()
    };
  }

  return {
    state: "scheduled",
    label: "Scheduled",
    detail: "Waiting for the next heartbeat interval.",
    nextDueAt: new Date(nextDueMs).toISOString()
  };
}
