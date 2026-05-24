import assert from "node:assert/strict";
import test from "node:test";

import type { WorkerProfile } from "../lib/api/types";
import { buildAutopilotScheduleStatus } from "../lib/state/autopilotSchedule";

function profile(overrides: Partial<WorkerProfile> = {}): WorkerProfile {
  return {
    profile_id: "profile-active",
    run_id: "run-1",
    name: "Creator app autopilot",
    execution_mode: "autonomous_pass",
    agent_ids: ["web-research-agent"],
    max_tasks_per_agent: 1,
    max_rounds: 2,
    poll_interval_seconds: 5,
    include_global_memories: true,
    memory_limit: 6,
    autonomous_auto_refresh_research_sources: true,
    autonomous_block_on_research_freshness_blocked: true,
    autonomous_block_on_retrieval_quality_blocked: true,
    autonomous_export_memory_summary_to_obsidian: true,
    autonomous_memory_summary_agent_id: null,
    autonomous_memory_summary_limit: 8,
    use_gemma: true,
    fail_on_provider_error: false,
    status: "active",
    last_heartbeat_at: "2026-05-18T12:00:00Z",
    created_at: "2026-05-18T11:00:00Z",
    updated_at: "2026-05-18T12:00:00Z",
    ...overrides
  };
}

test("autopilot schedule is due when no heartbeat completed", () => {
  const status = buildAutopilotScheduleStatus(
    profile({ last_heartbeat_at: null }),
    new Date("2026-05-18T12:00:00Z")
  );

  assert.equal(status?.state, "due");
  assert.equal(status?.label, "Due now");
  assert.equal(status?.detail, "No heartbeat has completed yet.");
});

test("autopilot schedule is due when the polling interval elapsed", () => {
  const status = buildAutopilotScheduleStatus(
    profile({ last_heartbeat_at: "2026-05-18T12:00:00Z", poll_interval_seconds: 5 }),
    new Date("2026-05-18T12:00:05Z")
  );

  assert.equal(status?.state, "due");
  assert.equal(status?.nextDueAt, "2026-05-18T12:00:05.000Z");
  assert.equal(status?.detail, "Heartbeat interval has elapsed.");
});

test("autopilot schedule reports the next due time before the interval elapses", () => {
  const status = buildAutopilotScheduleStatus(
    profile({ last_heartbeat_at: "2026-05-18T12:00:00Z", poll_interval_seconds: 30 }),
    new Date("2026-05-18T12:00:05Z")
  );

  assert.equal(status?.state, "scheduled");
  assert.equal(status?.label, "Scheduled");
  assert.equal(status?.nextDueAt, "2026-05-18T12:00:30.000Z");
});

test("autopilot schedule reports an active heartbeat lease", () => {
  const status = buildAutopilotScheduleStatus(
    profile({
      heartbeat_claimed_by: "scheduler-worker-1",
      heartbeat_lease_until: "2026-05-18T12:01:00Z"
    }),
    new Date("2026-05-18T12:00:30Z")
  );

  assert.equal(status?.state, "running");
  assert.equal(status?.label, "Heartbeat running");
  assert.equal(status?.leaseUntil, "2026-05-18T12:01:00Z");
  assert.equal(status?.claimedBy, "scheduler-worker-1");
  assert.equal(status?.detail, "Lease held by scheduler-worker-1.");
});

test("autopilot schedule reports inactive profiles as not running", () => {
  const status = buildAutopilotScheduleStatus(
    profile({ status: "stopped" }),
    new Date("2026-05-18T12:00:30Z")
  );

  assert.equal(status?.state, "off");
  assert.equal(status?.label, "Not running");
  assert.equal(status?.detail, "Profile is stopped.");
});
