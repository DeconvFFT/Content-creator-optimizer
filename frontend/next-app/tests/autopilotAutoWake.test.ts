import assert from "node:assert/strict";
import test from "node:test";

import type { WorkerProfile } from "../lib/api/types";
import { buildAutopilotAutoWakeDecision } from "../lib/state/autopilotAutoWake";

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

test("autopilot auto wake runs only when the active profile is due", () => {
  const due = buildAutopilotAutoWakeDecision({
    runId: "run-1",
    workerProfiles: [profile()],
    enabled: true,
    now: new Date("2026-05-18T12:00:05Z")
  });

  assert.equal(due.shouldRun, true);
  assert.equal(due.reason, "due");
  assert.equal(due.profile?.profile_id, "profile-active");
  assert.equal(due.schedule?.state, "due");
  assert.ok(due.wakeKey?.includes("profile-active"));
});

test("autopilot auto wake waits while the profile is scheduled", () => {
  const decision = buildAutopilotAutoWakeDecision({
    runId: "run-1",
    workerProfiles: [profile({ poll_interval_seconds: 30 })],
    enabled: true,
    now: new Date("2026-05-18T12:00:05Z")
  });

  assert.equal(decision.shouldRun, false);
  assert.equal(decision.reason, "not_due");
  assert.equal(decision.schedule?.state, "scheduled");
});

test("autopilot auto wake runs when any active profile is due", () => {
  const decision = buildAutopilotAutoWakeDecision({
    runId: "run-1",
    workerProfiles: [
      profile({
        profile_id: "older-due",
        last_heartbeat_at: "2026-05-18T12:00:00Z",
        poll_interval_seconds: 5,
        created_at: "2026-05-18T11:00:00Z"
      }),
      profile({
        profile_id: "newer-scheduled",
        last_heartbeat_at: "2026-05-18T12:00:00Z",
        poll_interval_seconds: 30,
        created_at: "2026-05-18T11:30:00Z"
      })
    ],
    enabled: true,
    now: new Date("2026-05-18T12:00:05Z")
  });

  assert.equal(decision.shouldRun, true);
  assert.equal(decision.reason, "due");
  assert.equal(decision.profile?.profile_id, "older-due");
});

test("autopilot auto wake chooses newest due profile when several are due", () => {
  const decision = buildAutopilotAutoWakeDecision({
    runId: "run-1",
    workerProfiles: [
      profile({
        profile_id: "older-due",
        created_at: "2026-05-18T11:00:00Z"
      }),
      profile({
        profile_id: "newer-due",
        created_at: "2026-05-18T11:30:00Z"
      })
    ],
    enabled: true,
    now: new Date("2026-05-18T12:00:05Z")
  });

  assert.equal(decision.shouldRun, true);
  assert.equal(decision.profile?.profile_id, "newer-due");
  assert.ok(decision.wakeKey?.includes("newer-due"));
});

test("autopilot auto wake does not overlap existing app work", () => {
  const decision = buildAutopilotAutoWakeDecision({
    runId: "run-1",
    workerProfiles: [profile()],
    enabled: true,
    busy: true,
    now: new Date("2026-05-18T12:00:05Z")
  });

  assert.equal(decision.shouldRun, false);
  assert.equal(decision.reason, "busy");
});

test("autopilot auto wake does not run while a scheduler call is in flight", () => {
  const decision = buildAutopilotAutoWakeDecision({
    runId: "run-1",
    workerProfiles: [profile()],
    enabled: true,
    inFlightRunIds: ["run-1"],
    now: new Date("2026-05-18T12:00:05Z")
  });

  assert.equal(decision.shouldRun, false);
  assert.equal(decision.reason, "in_flight");
});

test("autopilot auto wake suppresses repeated attempts for the same due window", () => {
  const first = buildAutopilotAutoWakeDecision({
    runId: "run-1",
    workerProfiles: [profile()],
    enabled: true,
    now: new Date("2026-05-18T12:00:05Z")
  });
  const second = buildAutopilotAutoWakeDecision({
    runId: "run-1",
    workerProfiles: [profile()],
    enabled: true,
    now: new Date("2026-05-18T12:00:10Z"),
    lastWakeKey: first.wakeKey
  });

  assert.equal(second.shouldRun, false);
  assert.equal(second.reason, "already_attempted");
});

test("autopilot auto wake ignores inactive profiles", () => {
  const decision = buildAutopilotAutoWakeDecision({
    runId: "run-1",
    workerProfiles: [profile({ status: "stopped" })],
    enabled: true,
    now: new Date("2026-05-18T12:00:05Z")
  });

  assert.equal(decision.shouldRun, false);
  assert.equal(decision.reason, "no_active_profile");
});
