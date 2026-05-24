import assert from "node:assert/strict";
import test from "node:test";

import { buildAutopilotEvidence } from "../lib/state/autopilotEvidence";
import type { ArtifactRecord, RunEvent, WorkerProfile } from "../lib/api/types";

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

function heartbeatLedger(overrides: Partial<ArtifactRecord> = {}): ArtifactRecord {
  return {
    artifact_id: "ledger-1",
    run_id: "run-1",
    artifact_type: "worker_profile_heartbeat_ledger",
    title: "Worker profile heartbeat ledger",
    uri: "artifact://runs/run-1/worker-profiles/profile-active/heartbeat-ledger",
    content: {
      heartbeat_state: "completed",
      processed_tasks: 3,
      idle: false,
      skipped: false,
      blocked_reasons: [],
      profile: {
        profile_id: "profile-active",
        execution_mode: "autonomous_pass"
      },
      linked_artifacts: {
        work_plan_artifact_id: "work-plan-1",
        context_packet_artifact_id: "context-1"
      },
      loop_ledgers: {
        realtime_dialogue_status: "ready",
        feedback_resolution_status: "resolved"
      }
    },
    provenance: {
      workflow: "worker_profile_heartbeat_ledger_v1",
      profile_id: "profile-active"
    },
    source_ids: [],
    reviewer_decisions: [],
    revision_history: [],
    created_at: "2026-05-18T12:00:01Z",
    ...overrides
  };
}

function heartbeatEvent(overrides: Partial<RunEvent> = {}): RunEvent {
  return {
    event_id: 10,
    run_id: "run-1",
    event_type: "worker_profile_heartbeat_blocked",
    actor: "agent-harness-engineer",
    payload: {
      profile_id: "profile-active",
      total_processed_tasks: 0,
      idle: true,
      blocked_reasons: ["open_human_feedback_gate"],
      heartbeat_ledger_artifact_id: "ledger-from-event",
      realtime_dialogue_status: "missing",
      feedback_resolution_status: "open"
    },
    created_at: "2026-05-18T12:00:02Z",
    ...overrides
  };
}

test("autopilot evidence prefers the matching durable heartbeat ledger", () => {
  const evidence = buildAutopilotEvidence({
    workerProfiles: [profile()],
    artifacts: [heartbeatLedger()],
    events: [heartbeatEvent()]
  });

  assert.equal(evidence?.source, "heartbeat_ledger_artifact");
  assert.equal(evidence?.heartbeatState, "completed");
  assert.equal(evidence?.processedTasks, 3);
  assert.equal(evidence?.ledgerArtifactId, "ledger-1");
  assert.equal(evidence?.workPlanArtifactId, "work-plan-1");
  assert.equal(evidence?.realtimeDialogueStatus, "ready");
  assert.equal(evidence?.feedbackResolutionStatus, "resolved");
});

test("autopilot evidence falls back to a matching heartbeat event", () => {
  const evidence = buildAutopilotEvidence({
    workerProfiles: [profile()],
    artifacts: [
      heartbeatLedger({
        artifact_id: "other-ledger",
        content: {
          profile: { profile_id: "other-profile" },
          heartbeat_state: "completed"
        },
        provenance: { profile_id: "other-profile" }
      })
    ],
    events: [heartbeatEvent()]
  });

  assert.equal(evidence?.source, "heartbeat_event");
  assert.equal(evidence?.heartbeatState, "blocked");
  assert.deepEqual(evidence?.blockedReasons, ["open_human_feedback_gate"]);
  assert.equal(evidence?.ledgerArtifactId, "ledger-from-event");
});

test("autopilot evidence does not borrow another profile's proof", () => {
  const artifacts = [
    heartbeatLedger({
      artifact_id: "other-ledger",
      created_at: "2026-05-18T12:05:00Z",
      content: {
        profile: { profile_id: "other-profile" },
        heartbeat_state: "completed",
        processed_tasks: 9
      },
      provenance: { profile_id: "other-profile" }
    })
  ];
  const events = [
    heartbeatEvent({
      event_id: 20,
      payload: {
        profile_id: "other-profile",
        total_processed_tasks: 9,
        heartbeat_ledger_artifact_id: "other-ledger"
      }
    })
  ];

  const evidence = buildAutopilotEvidence({
    workerProfiles: [profile()],
    artifacts,
    events
  });

  assert.equal(evidence, null);
  assert.equal(artifacts[0].artifact_id, "other-ledger");
  assert.equal(events[0].event_id, 20);
});

test("autopilot evidence uses the newest active autopilot profile", () => {
  const olderProfile = profile({
    profile_id: "older-profile",
    created_at: "2026-05-18T10:00:00Z"
  });
  const newerProfile = profile({
    profile_id: "newer-profile",
    created_at: "2026-05-18T11:00:00Z",
    last_heartbeat_at: null
  });
  const evidence = buildAutopilotEvidence({
    workerProfiles: [olderProfile, newerProfile],
    artifacts: [
      heartbeatLedger({
        artifact_id: "older-ledger",
        content: {
          profile: { profile_id: "older-profile" },
          heartbeat_state: "completed",
          processed_tasks: 7
        },
        provenance: { profile_id: "older-profile" }
      })
    ],
    events: [
      heartbeatEvent({
        payload: {
          profile_id: "older-profile",
          total_processed_tasks: 7,
          heartbeat_ledger_artifact_id: "older-ledger"
        }
      })
    ]
  });

  assert.equal(evidence, null);
});

test("autopilot evidence is hidden when the run has no autopilot profile", () => {
  const evidence = buildAutopilotEvidence({
    workerProfiles: [],
    artifacts: [heartbeatLedger()],
    events: [heartbeatEvent()]
  });

  assert.equal(evidence, null);
});
