import assert from "node:assert/strict";
import test from "node:test";

import type { WorkerProfile } from "../lib/api/types";
import {
  nextWorkerSchedulerStatusToken,
  selectedWorkerSchedulerProfile,
  shouldCommitWorkerSchedulerStatus
} from "../lib/state/workerSchedulerProcess";

function profile(overrides: Partial<WorkerProfile> = {}): WorkerProfile {
  return {
    profile_id: "profile-old",
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
    last_heartbeat_at: null,
    created_at: "2026-05-18T11:00:00Z",
    updated_at: "2026-05-18T11:00:00Z",
    ...overrides
  };
}

test("worker scheduler polling cannot overwrite a newer control result", () => {
  let token = 0;
  const pollStartedToken = token;

  token = nextWorkerSchedulerStatusToken(token);
  const startStartedToken = token;

  assert.equal(shouldCommitWorkerSchedulerStatus(pollStartedToken, token), false);
  assert.equal(shouldCommitWorkerSchedulerStatus(startStartedToken, token), true);
});

test("worker scheduler start uses newest active run-scoped Autopilot profile", () => {
  const older = profile({
    profile_id: "profile-old",
    poll_interval_seconds: 5,
    created_at: "2026-05-18T11:00:00Z"
  });
  const newer = profile({
    profile_id: "profile-new",
    poll_interval_seconds: 0.25,
    created_at: "2026-05-18T12:00:00Z"
  });
  const wrongRun = profile({
    profile_id: "profile-other-run",
    run_id: "run-2",
    poll_interval_seconds: 30,
    created_at: "2026-05-18T13:00:00Z"
  });

  const selected = selectedWorkerSchedulerProfile([older, newer, wrongRun], "run-1");

  assert.equal(selected?.profile_id, "profile-new");
  assert.equal(selected?.poll_interval_seconds, 0.25);
});
