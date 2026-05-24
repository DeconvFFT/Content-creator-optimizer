import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { AppShell } from "../components/layout/AppShell";
import { ActivityPanel } from "../components/run/ActivityPanel";
import type {
  AgentMessage,
  ArtifactRecord,
  RunEvent,
  RunWorkPlanResult,
  WorkerSchedulerProcessStatusResult,
  WorkerProfile
} from "../lib/api/types";
import { appendCreatorStatusDetail, creatorStatusText } from "../lib/state/creatorStatusCopy";

const pageSource = readFileSync("app/page.tsx", "utf8");
const clientSource = readFileSync("lib/api/client.ts", "utf8");

function stripTechnicalProofDetails(html: string) {
  return html.replace(/<details class="technical-proof-disclosure"[\s\S]*?<\/details>/g, "");
}

const profile: WorkerProfile = {
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
  updated_at: "2026-05-18T12:00:00Z"
};

const ledger: ArtifactRecord = {
  artifact_id: "ledger-1",
  run_id: "run-1",
  artifact_type: "worker_profile_heartbeat_ledger",
  title: "Worker profile heartbeat ledger",
  uri: "artifact://runs/run-1/worker-profiles/profile-active/heartbeat-ledger",
  content: {
    heartbeat_state: "completed",
    processed_tasks: 4,
    idle: false,
    skipped: false,
    blocked_reasons: [],
    profile: { profile_id: "profile-active" },
    linked_artifacts: { work_plan_artifact_id: "work-plan-1" },
    loop_ledgers: {
      realtime_dialogue_status: "ready",
      feedback_resolution_status: "resolved"
    }
  },
  provenance: { profile_id: "profile-active" },
  source_ids: [],
  reviewer_decisions: [],
  revision_history: [],
  created_at: "2026-05-18T12:00:01Z"
};

const heartbeatEvent: RunEvent = {
  event_id: 1,
  run_id: "run-1",
  event_type: "worker_profile_heartbeat",
  actor: "agent-harness-engineer",
  payload: {
    profile_id: "profile-active",
    total_processed_tasks: 4,
    heartbeat_ledger_artifact_id: "ledger-1"
  },
  created_at: "2026-05-18T12:00:01Z"
};

const schedulerEvent: RunEvent = {
  event_id: 2,
  run_id: "run-1",
  event_type: "worker_scheduler_pass_completed",
  actor: "agent-harness-engineer",
  payload: {
    checked_profiles: 1,
    heartbeat_count: 1,
    total_processed_tasks: 4,
    idle: false,
    profile_ids: ["profile-active"],
    heartbeat_ledger_artifact_ids: ["ledger-1"]
  },
  created_at: "2026-05-18T12:00:02Z"
};

const scopedIdleSchedulerEvent: RunEvent = {
  event_id: 3,
  run_id: "run-1",
  event_type: "worker_scheduler_pass_completed",
  actor: "agent-harness-engineer",
  payload: {
    requested_run_id: "run-1",
    requested_execution_mode: "autonomous_pass",
    checked_profiles: 0,
    scheduler_checked_profiles: 0,
    heartbeat_count: 0,
    total_processed_tasks: 0,
    idle: true,
    idle_reason: "no_due_profiles",
    profile_ids: []
  },
  created_at: "2026-05-18T12:00:03Z"
};

const workerSchedulerProcess: WorkerSchedulerProcessStatusResult = {
  enabled: true,
  status: "running",
  running: true,
  pid: 9012,
  run_id: "run-1",
  execution_mode: "autonomous_pass",
  max_profiles: 10,
  poll_interval_seconds: 5,
  returncode: null,
  last_error: null,
  started_at: "2026-05-18T12:00:04Z",
  stopped_at: null,
  command: [
    "python",
    "-m",
    "all_about_llms.cli",
    "run-worker-scheduler",
    "--watch",
    "--run-id",
    "run-1"
  ],
  log_tail: ["worker scheduler started"],
  next_actions: ["Leave this process running for always-on Autopilot wakeups."],
  summary: "Local worker scheduler process is running."
};

const workPlan: RunWorkPlanResult = {
  run_id: "run-1",
  plan_items: [
    {
      item_id: "item-1",
      item_type: "feedback_task",
      title: "Revise voiceover pacing",
      owner_agent_id: "audio-producer",
      status: "ready",
      priority: "high",
      blocking: true,
      source_message_id: null,
      source_feedback_id: "feedback-1",
      recommended_action: "Rewrite the narration with shorter spoken beats.",
      reason: "Open creator feedback asks for more natural pacing.",
      metadata: {}
    },
    {
      item_id: "item-2",
      item_type: "source_refresh",
      title: "Refresh evidence",
      owner_agent_id: "web-research-agent",
      status: "ready",
      priority: "normal",
      blocking: false,
      source_message_id: null,
      source_feedback_id: null,
      recommended_action: "Run provider-backed source refresh.",
      reason: "Search seed evidence still needs live source replacement.",
      metadata: {}
    }
  ],
  recommended_agent_ids: ["audio-producer", "web-research-agent"],
  open_feedback_count: 1,
  routed_feedback_count: 0,
  pending_task_count: 2,
  blocked_item_count: 1,
  created_task_message_ids: [],
  skipped_duplicate_task_count: 0,
  artifact_id: "work-plan-artifact-1",
  event_id: 10,
  refresh_reason: "creator_app_next_actions",
  summary: "Built 2 next action(s) with 1 blocker."
};

const materializedWorkPlan: RunWorkPlanResult = {
  ...workPlan,
  created_task_message_ids: ["task-1", "task-2"],
  skipped_duplicate_task_count: 1,
  refresh_reason: "creator_app_run_plan",
  summary: "Built 2 next action(s), created 2 task(s), skipped 1 duplicate task."
};

const postRunWorkPlan: RunWorkPlanResult = {
  ...workPlan,
  plan_items: [workPlan.plan_items[1]],
  recommended_agent_ids: ["web-research-agent"],
  open_feedback_count: 0,
  routed_feedback_count: 1,
  pending_task_count: 1,
  blocked_item_count: 0,
  refresh_reason: "creator_app_after_run_plan",
  summary: "Refreshed 1 next action after running planned agents."
};

const workPlanArtifact: ArtifactRecord = {
  artifact_id: "work-plan-artifact-2",
  run_id: "run-1",
  artifact_type: "system_plan",
  title: "Autonomous run work plan",
  uri: "artifact://runs/run-1/work-plans/work-plan-artifact-2",
  content: {
    plan_items: workPlan.plan_items,
    recommended_agent_ids: workPlan.recommended_agent_ids,
    open_feedback_count: 1,
    routed_feedback_count: 0,
    pending_task_count: 2,
    blocked_item_count: 1,
    refresh_reason: "stream_refresh"
  },
  provenance: { workflow: "run_work_plan_v1" },
  source_ids: [],
  reviewer_decisions: [],
  revision_history: [],
  created_at: "2026-05-18T12:00:04Z"
};

const liveWorkPlanArtifact: ArtifactRecord = {
  ...workPlanArtifact,
  artifact_id: "work-plan-artifact-1",
  uri: "artifact://runs/run-1/work-plans/work-plan-artifact-1",
  created_at: "2026-05-18T12:00:03Z"
};

const partialWorkPlanArtifact: ArtifactRecord = {
  ...workPlanArtifact,
  artifact_id: "partial-plan-artifact",
  content: {
    plan_items: [
      {
        item_id: "bad-item",
        item_type: "source_refresh",
        owner_agent_id: "web-research-agent",
        status: "ready",
        recommended_action: "This item should not render without a title.",
        reason: "Missing required title."
      },
      {
        item_id: "partial-item",
        item_type: "source_refresh",
        title: "Recover source plan",
        owner_agent_id: "web-research-agent",
        status: "ready",
        recommended_action: "Use the saved source-refresh plan even if optional fields are absent.",
        reason: "Older proof artifacts did not always include all display metadata."
      }
    ]
  },
  created_at: "2026-05-18T12:00:05Z"
};

const newerWorkPlanArtifact: ArtifactRecord = {
  ...workPlanArtifact,
  artifact_id: "work-plan-artifact-3",
  content: {
    plan_items: [
      {
        item_id: "item-new",
        item_type: "review_task",
        title: "Review updated plan",
        owner_agent_id: "critic-reviewer-agent",
        status: "ready",
        priority: "high",
        blocking: true,
        recommended_action: "Review the new durable work plan from the latest refresh.",
        reason: "A later backend pass wrote newer saved proof.",
        metadata: {}
      }
    ],
    pending_task_count: 1,
    blocked_item_count: 1
  },
  created_at: "2026-05-18T12:00:06Z"
};

const freshLiveWorkPlan: RunWorkPlanResult = {
  ...workPlan,
  artifact_id: "work-plan-artifact-live-new",
  plan_items: [
    {
      item_id: "item-live-new",
      item_type: "writer_task",
      title: "Draft fresh live plan",
      owner_agent_id: "substack-essay-writer",
      status: "ready",
      priority: "normal",
      blocking: false,
      source_message_id: null,
      source_feedback_id: null,
      recommended_action: "Use the just-returned work plan while saved proof catches up.",
      reason: "The API returned a newer live work plan than the stale artifact list.",
      metadata: {}
    }
  ]
};

const producedReelArtifact: ArtifactRecord = {
  artifact_id: "artifact-1",
  run_id: "run-1",
  artifact_type: "reel_script",
  title: "Inference engineering reel draft",
  uri: "artifact://runs/run-1/reels/artifact-1",
  content: {
    script: "Inference engineering is how models become fast, reliable products."
  },
  provenance: {
    workflow: "eli5_short_form_writer_v1"
  },
  source_ids: [],
  reviewer_decisions: [],
  revision_history: [],
  created_at: "2026-05-18T12:03:30Z"
};

const producedLedgerArtifact: ArtifactRecord = {
  artifact_id: "artifact-2",
  run_id: "run-1",
  artifact_type: "source_ledger",
  title: "Source refresh ledger",
  uri: "artifact://runs/run-1/source-ledger/artifact-2",
  content: {
    summary: "Provider-backed source refresh proof."
  },
  provenance: {
    workflow: "source_refresh_v1"
  },
  source_ids: [],
  reviewer_decisions: [],
  revision_history: [],
  created_at: "2026-05-18T12:03:31Z"
};

const producedStrategyArtifact: ArtifactRecord = {
  artifact_id: "strategy-artifact-1",
  run_id: "run-1",
  artifact_type: "growth_strategy",
  title: "Reviewer strategy follow-up",
  uri: "artifact://runs/run-1/growth-strategies/strategy-artifact-1",
  content: {
    summary: "Reviewer strategy follow-up proof."
  },
  provenance: {
    workflow: "critic_reviewer_followup_v1"
  },
  source_ids: [],
  reviewer_decisions: [],
  revision_history: [],
  created_at: "2026-05-18T12:07:30Z"
};

const completedOutcomeMessages: AgentMessage[] = [
  {
    message_id: "outcome-old",
    run_id: "run-1",
    sender_agent_id: "agent-harness-engineer",
    recipient_agent_id: "content-strategist",
    task_type: "content_strategy",
    payload: {},
    depends_on_message_ids: [],
    requires_human_feedback: false,
    status: "completed",
    claimed_by_agent_id: "content-strategist",
    attempt_count: 1,
    max_attempts: 3,
    result: {
      summary: "Older strategy that should fall out of the compact outcome rail."
    },
    error: null,
    created_at: "2026-05-18T11:00:00Z",
    updated_at: "2026-05-18T11:01:00Z"
  },
  {
    message_id: "outcome-1",
    run_id: "run-1",
    sender_agent_id: "agent-harness-engineer",
    recipient_agent_id: "eli5-short-form-writer",
    task_type: "reel_script",
    payload: {},
    depends_on_message_ids: [],
    requires_human_feedback: false,
    status: "completed",
    claimed_by_agent_id: "eli5-short-form-writer",
    attempt_count: 1,
    max_attempts: 3,
    result: {
      summary: "Drafted a 45-second ELI5 reel script with a source-backed hook.",
      raw_payload_that_should_not_render: { nested: "verbose internal state" }
    },
    error: null,
    created_at: "2026-05-18T12:00:00Z",
    updated_at: "2026-05-18T12:01:00Z"
  },
  {
    message_id: "outcome-2",
    run_id: "run-1",
    sender_agent_id: "agent-harness-engineer",
    recipient_agent_id: "web-research-agent",
    task_type: "source_refresh",
    payload: {},
    depends_on_message_ids: [],
    requires_human_feedback: false,
    status: "completed",
    claimed_by_agent_id: "web-research-agent",
    attempt_count: 1,
    max_attempts: 3,
    result: {
      artifact_ids: ["artifact-1"],
      created_artifact_ids: ["artifact-1", "artifact-2"],
      generation_mode: "web_search_provider",
      content_artifact_ids: ["artifact-1", "artifact-2"]
    },
    error: null,
    created_at: "2026-05-18T12:02:00Z",
    updated_at: "2026-05-18T12:03:00Z"
  },
  {
    message_id: "outcome-3",
    run_id: "run-1",
    sender_agent_id: "agent-harness-engineer",
    recipient_agent_id: "audio-producer",
    task_type: "voiceover_pass",
    payload: {},
    depends_on_message_ids: [],
    requires_human_feedback: false,
    status: "completed",
    claimed_by_agent_id: "audio-producer",
    attempt_count: 1,
    max_attempts: 3,
    result: {
      media_artifact_ids: ["audio-1"]
    },
    error: null,
    created_at: "2026-05-18T12:04:00Z",
    updated_at: "2026-05-18T12:05:00Z"
  },
  {
    message_id: "outcome-4",
    run_id: "run-1",
    sender_agent_id: "agent-harness-engineer",
    recipient_agent_id: "critic-reviewer-agent",
    task_type: "quality_review",
    payload: {},
    depends_on_message_ids: [],
    requires_human_feedback: false,
    status: "completed",
    claimed_by_agent_id: "critic-reviewer-agent",
    attempt_count: 1,
    max_attempts: 3,
    result: {
      strategy_artifact_id: "strategy-artifact-1"
    },
    error: null,
    created_at: "2026-05-18T12:06:00Z",
    updated_at: "2026-05-18T12:07:00Z"
  },
  {
    message_id: "pending-1",
    run_id: "run-1",
    sender_agent_id: "agent-harness-engineer",
    recipient_agent_id: "substack-essay-writer",
    task_type: "substack_article",
    payload: {},
    depends_on_message_ids: [],
    requires_human_feedback: false,
    status: "pending",
    claimed_by_agent_id: null,
    attempt_count: 0,
    max_attempts: 3,
    result: {},
    error: null,
    created_at: "2026-05-18T12:08:00Z",
    updated_at: "2026-05-18T12:08:00Z"
  }
];

const retryBlockedMessage: AgentMessage = {
  message_id: "retry-blocked-1",
  run_id: "run-1",
  sender_agent_id: "agent-harness-engineer",
  recipient_agent_id: "web-research-agent",
  task_type: "research_topic",
  payload: {},
  depends_on_message_ids: [],
  requires_human_feedback: false,
  status: "blocked",
  claimed_by_agent_id: "web-research-agent",
  attempt_count: 3,
  max_attempts: 3,
  result: {
    retry_policy: {
      attempt_count: 3,
      max_attempts: 3
    }
  },
  error: "A2A task exhausted retry attempts.",
  created_at: "2026-05-18T12:09:00Z",
  updated_at: "2026-05-18T12:10:00Z"
};

test("ActivityPanel renders active Autopilot heartbeat action and durable proof", () => {
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [heartbeatEvent, schedulerEvent],
      messages: [],
      artifacts: [ledger],
      workerProfiles: [profile],
      onContinueAgents: async () => undefined,
      onLaunchAutopilot: async () => undefined,
      onRunAutopilotScheduler: async () => undefined,
      onHeartbeatAutopilot: async () => undefined,
      onStopAutopilot: async () => undefined,
      autopilotAutoWakeEnabled: true,
      autopilotAutoWakeDetail: "Auto continue ready",
      onAutopilotAutoWakeChange: () => undefined,
      eventStreamStatus: "live",
      eventStreamDetail: "Live update: background check #2",
      useGemma: true,
      onUseGemmaChange: () => undefined,
      now: new Date("2026-05-18T12:00:06Z")
    })
  );

  assert.match(html, /Run pulse/);
  assert.match(html, /Check due work/);
  const primaryHtml = stripTechnicalProofDetails(html);

  assert.match(primaryHtml, /Background check/);
  assert.match(primaryHtml, /Specialist pulse/);
  assert.match(html, /completed/);
  assert.match(primaryHtml, /4 specialist update\(s\)/);
  assert.match(primaryHtml, /1 pulse\(s\)/);
  assert.match(primaryHtml, /realtime ready/);
  assert.match(primaryHtml, /feedback resolved/);
  assert.match(html, /Technical proof/);
  assert.match(html, /event #2/);
  assert.match(html, /ledger ledger-1/);
  assert.match(primaryHtml, /Last pulse/);
  assert.match(html, /Last heartbeat/);
  assert.doesNotMatch(primaryHtml, /Schedule proof/);
  assert.doesNotMatch(primaryHtml, /Always-on proof/);
  assert.doesNotMatch(primaryHtml, /profile\(s\)/);
  assert.doesNotMatch(primaryHtml, /heartbeat\(s\)/);
  assert.doesNotMatch(primaryHtml, /event #/);
  assert.doesNotMatch(primaryHtml, /ledger/);
  assert.doesNotMatch(primaryHtml, /Last heartbeat/);
  assert.doesNotMatch(primaryHtml, /agent harness engineer[\s\S]*#[0-9]/i);
  assert.match(html, /Due now/);
  assert.match(primaryHtml, /Ready to check due work/);
  assert.match(html, /Heartbeat interval has elapsed/);
  assert.doesNotMatch(primaryHtml, /Heartbeat interval has elapsed/);
  assert.match(html, /Auto continue/);
  assert.match(html, /Auto continue ready/);
  assert.match(html, /Live updates/);
  assert.match(html, /Live update: background check #2/);
  assert.doesNotMatch(html, /worker_scheduler_pass_completed/);
});

test("ActivityPanel renders local worker scheduler process controls", () => {
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [schedulerEvent],
      messages: [],
      artifacts: [ledger],
      workerProfiles: [profile],
      workerSchedulerProcess,
      onStartWorkerScheduler: async () => undefined,
      onStopWorkerScheduler: async () => undefined,
      now: new Date("2026-05-18T12:00:06Z")
    })
  );

  assert.match(html, /Background runner/);
  const primaryHtml = stripTechnicalProofDetails(html);

  assert.match(html, /running/);
  assert.match(primaryHtml, /Checks due work every 5s/);
  assert.doesNotMatch(primaryHtml, /pid 9012/);
  assert.doesNotMatch(primaryHtml, /autonomous pass/);
  assert.doesNotMatch(primaryHtml, /profile cap/);
  assert.match(html, /pid 9012/);
  assert.match(html, /autonomous pass/);
  assert.match(html, /5s cadence/);
  assert.match(html, /Stop runner/);
  assert.doesNotMatch(html, /Start runner/);
});

test("ActivityPanel renders creator work plan actions without a Kanban board", () => {
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [],
      messages: [],
      workPlan,
      onBuildWorkPlan: async () => undefined,
      onRunWorkPlan: async () => undefined
    })
  );

  assert.match(html, /Suggest next step/);
  assert.match(html, /Run next steps/);
  assert.match(html, /Next studio steps/);
  assert.match(html, /2 item\(s\)/);
  assert.match(html, /1 blocker\(s\)/);
  assert.match(html, /audio producer/);
  assert.match(html, /Revise voiceover pacing/);
  assert.match(html, /Rewrite the narration with shorter spoken beats/);
  assert.match(html, /web research agent/);
  assert.doesNotMatch(html, /Kanban/);
});

test("ActivityPanel uses creator-facing rail language instead of operations-dashboard labels", () => {
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [schedulerEvent],
      messages: [retryBlockedMessage, completedOutcomeMessages[1], completedOutcomeMessages[5]],
      artifacts: [ledger],
      workPlan,
      workerProfiles: [profile],
      workerSchedulerProcess,
      onContinueAgents: async () => undefined,
      onBuildWorkPlan: async () => undefined,
      onRunWorkPlan: async () => undefined,
      onLaunchAutopilot: async () => undefined,
      onRunAutopilotScheduler: async () => undefined,
      onHeartbeatAutopilot: async () => undefined,
      onStopAutopilot: async () => undefined,
      onStartWorkerScheduler: async () => undefined,
      onStopWorkerScheduler: async () => undefined,
      onUseGemmaChange: () => undefined,
      onAutopilotAutoWakeChange: () => undefined,
      useGemma: true,
      autopilotAutoWakeDetail: "Auto continue ready",
      eventStreamStatus: "live",
      eventStreamDetail: "Studio stream connected",
      now: new Date("2026-05-18T12:00:06Z")
    })
  );

  assert.match(html, /Studio flow/);
  assert.match(html, /Continue specialists/);
  assert.match(html, /Suggest next step/);
  assert.match(html, /Gemma experts/);
  assert.match(html, /Always-on studio/);
  assert.match(html, /Background runner/);
  assert.match(html, /Recent specialist outputs/);
  assert.match(html, /Live updates|Studio updates/);

  [
    /Agents and events/,
    /Run agents/,
    /Plan next/,
    /Gemma workers/,
    /Autopilot/,
    /Local scheduler/,
    /Start scheduler/,
    /Stop scheduler/,
    /Scheduler proof/,
    /Heartbeat proof/,
    /Run due/
  ].forEach((forbidden) => assert.doesNotMatch(html, forbidden));
});

test("creator rail parent summaries use always-on studio language", () => {
  [
    /Autopilot auto wake/,
    /Autopilot scheduler/,
    /Autopilot started/,
    /Autopilot stopped/,
    /Autopilot heartbeat/,
    /Launching autopilot/,
    /Stopping autopilot/,
    /Running autopilot heartbeat/,
    /Could not launch autopilot/,
    /Could not stop autopilot/,
    /Could not run autopilot heartbeat/,
    /The selected Autopilot profile/,
    /Checking due autopilot/,
    /Could not run autopilot scheduler/,
    /Start Autopilot before starting the local scheduler process/,
    /Starting local scheduler/,
    /Stopping local scheduler/,
    /Could not start local scheduler/,
    /Could not stop local scheduler/,
    /Auto wake will/,
    /Auto wake is paused/,
    /Auto wake could/
  ].forEach((forbidden) => assert.doesNotMatch(pageSource, forbidden));

  assert.match(pageSource, /Auto continue checked this run/);
  assert.match(pageSource, /Always-on studio checked due work/);
  assert.match(pageSource, /Always-on studio started/);
  assert.match(pageSource, /Always-on studio stopped/);
  assert.match(pageSource, /Specialist pulse finished/);
  assert.match(pageSource, /Start always-on studio before starting the background runner/);
  assert.match(pageSource, /Starting background runner/);
  assert.match(pageSource, /Stopping background runner/);
  assert.match(pageSource, /Auto continue will run due studio work/);
  assert.match(clientSource, /Creator always-on studio/);
  assert.doesNotMatch(clientSource, /Creator app autopilot/);
});

test("AppShell parent status sanitizes backend always-on and runner summaries", () => {
  const alwaysOnSummary = appendCreatorStatusDetail(
    "Always-on studio started.",
    "Autopilot launch recorded. Creator app autopilot will run specialist heartbeats."
  );
  const runnerSummary = creatorStatusText("Local worker scheduler process is running.");
  const html = renderToStaticMarkup(
    React.createElement(React.Fragment, null,
      React.createElement(AppShell, {
        lastSummary: alwaysOnSummary,
        onClear: () => undefined,
        onRefresh: () => undefined,
        children: null
      }, null),
      React.createElement(AppShell, {
        lastSummary: runnerSummary,
        onClear: () => undefined,
        onRefresh: () => undefined,
        children: null
      }, null)
    )
  );

  assert.match(html, /Always-on studio started/);
  assert.match(html, /Always-on studio launch recorded/);
  assert.match(html, /Creator always-on studio will run specialist heartbeats/);
  assert.match(html, /Background runner is running/);
  assert.doesNotMatch(html, /Autopilot/);
  assert.doesNotMatch(html, /autopilot/);
  assert.doesNotMatch(html, /Local worker scheduler process/);
  assert.doesNotMatch(html, /local scheduler/);
});

test("always-on launch and stop use a synchronous single-flight gate", () => {
  assert.match(pageSource, /const autopilotActionGateRef = useRef\(\{ inFlight: false, token: 0 \}\);/);
  for (const handlerName of ["handleLaunchAutopilot", "handleStopAutopilot"]) {
    const handlerIndex = pageSource.indexOf(`async function ${handlerName}(`);
    const nextHandlerIndex = pageSource.indexOf("async function ", handlerIndex + 1);
    const handlerSource = pageSource.slice(
      handlerIndex,
      nextHandlerIndex === -1 ? undefined : nextHandlerIndex
    );

    assert.notEqual(handlerIndex, -1);
    assert.match(handlerSource, /beginRunAction\(autopilotActionGateRef\.current\)/);
    assert.match(handlerSource, /isRunVersionedActionCurrent\(/);
    assert.match(handlerSource, /finishRunAction\(autopilotActionGateRef\.current, autopilotToken\)/);
  }
  assert.match(pageSource, /invalidateRunAction\(autopilotActionGateRef\.current\)/);
});

test("ActivityPanel renders materialized work-plan execution proof", () => {
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [],
      messages: [],
      workPlan: materializedWorkPlan,
      onRunWorkPlan: async () => undefined
    })
  );

  assert.match(html, /execution plan/);
  assert.match(html, /2 task\(s\) created/);
  assert.match(html, /1 duplicate task\(s\) skipped/);
  assert.match(html, /1 open feedback/);
});

test("ActivityPanel renders post-run work-plan refresh proof", () => {
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [],
      messages: [],
      workPlan: postRunWorkPlan,
      onRunWorkPlan: async () => undefined
    })
  );

  assert.match(html, /post-run refresh/);
  assert.match(html, /1 routed feedback/);
  assert.match(html, /0 blocker\(s\)/);
  assert.doesNotMatch(html, /task\(s\) created/);
});

test("ActivityPanel renders recent completed specialist outcomes", () => {
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [],
      messages: completedOutcomeMessages,
      artifacts: [producedReelArtifact, producedLedgerArtifact, producedStrategyArtifact]
    })
  );

  assert.match(html, /Recent specialist outputs/);
  assert.match(html, /critic reviewer agent/);
  assert.match(html, /quality review/);
  assert.match(html, /href="#artifact-strategy-artifact-1"/);
  assert.match(html, /Reviewer strategy follow-up/);
  assert.match(html, /audio producer/);
  assert.match(html, /Created 1 artifact/);
  assert.match(html, /web research agent/);
  assert.match(html, /Created 2 artifacts/);
  assert.match(html, /via web search provider/);
  assert.match(html, /Produced artifacts/);
  assert.match(html, /href="#artifact-artifact-1"/);
  assert.match(html, /Inference engineering reel draft/);
  assert.match(html, /href="#artifact-artifact-2"/);
  assert.match(html, /Source refresh ledger/);
  assert.match(html, /eli5 short form writer/);
  assert.match(html, /Drafted a 45-second ELI5 reel script/);
  assert.match(html, /substack essay writer/);
  assert.match(html, /pending/);
  assert.doesNotMatch(html, /Older strategy/);
  assert.doesNotMatch(html, /verbose internal state/);
});

test("ActivityPanel surfaces failed or blocked tasks with retry action", () => {
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [],
      messages: [retryBlockedMessage, completedOutcomeMessages[5]],
      onRetryAgentMessage: async () => undefined
    })
  );

  assert.match(html, /Needs attention/);
  assert.match(html, /research topic/);
  assert.match(html, /web research agent/);
  assert.match(html, /blocked/);
  assert.match(html, /A2A task exhausted retry attempts/);
  assert.match(html, /3\/3 attempts/);
  assert.match(html, />Queue and run</);
  assert.match(html, /substack essay writer/);
  assert.match(html, /pending/);
});

test("ActivityPanel redacts token-shaped backend errors in attention summaries", () => {
  const fakeHfToken = "hf_" + "123456789012345678901234";
  const fakeTavilyKey = "tvly-" + "abcdefghijklmnopqrstuvwxyz";
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [],
      messages: [
        {
          ...retryBlockedMessage,
          error: `Provider failed with Bearer livekit-token and ${fakeHfToken} and ${fakeTavilyKey}`
        }
      ],
      onRetryAgentMessage: async () => undefined
    })
  );

  assert.equal(html.includes(fakeHfToken), false);
  assert.equal(html.includes(fakeTavilyKey), false);
  assert.match(html, /Bearer \[redacted\]/);
  assert.match(html, /hf_\[redacted\]/);
  assert.match(html, /tvly-\[redacted\]/);
});

test("ActivityPanel disables only the retry button already being queued", () => {
  const secondRetryMessage: AgentMessage = {
    ...retryBlockedMessage,
    message_id: "retry-blocked-2",
    task_type: "second_retry_task",
    recipient_agent_id: "editor-in-chief"
  };
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [],
      messages: [retryBlockedMessage, secondRetryMessage],
      retryingMessageIds: [retryBlockedMessage.message_id],
      onRetryAgentMessage: async () => undefined
    })
  );

  assert.match(html, /disabled="">.*Running/);
  assert.match(html, />Queue and run</);
  assert.match(html, /editor in chief/);
});

test("ActivityPanel prioritizes latest failed or blocked tasks before capping the rail", () => {
  const attentionMessages = Array.from({ length: 5 }, (_, index): AgentMessage => ({
    ...retryBlockedMessage,
    message_id: `retry-blocked-${index + 1}`,
    recipient_agent_id: index === 0 ? "old-hidden-agent" : `attention-agent-${index + 1}`,
    task_type: index === 0 ? "old_hidden_task" : `attention_task_${index + 1}`,
    created_at: `2026-05-18T12:0${index}:00Z`,
    updated_at: `2026-05-18T12:1${index}:00Z`
  }));

  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [],
      messages: attentionMessages,
      onRetryAgentMessage: async () => undefined
    })
  );

  assert.doesNotMatch(html, /old hidden task/);
  assert.doesNotMatch(html, /old-hidden-agent/);
  assert.match(html, /attention task 5/);
  assert.match(html, /attention agent 5/);
  assert.match(html, /attention task 2/);
});

test("ActivityPanel restores latest work plan from artifact proof", () => {
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [],
      messages: [],
      artifacts: [workPlanArtifact]
    })
  );

  assert.match(html, /Next studio steps/);
  assert.match(html, /source refresh/);
  assert.match(html, /Refresh evidence/);
  assert.match(html, /Run provider-backed source refresh/);
  assert.match(html, /plan work-plan/);
});

test("ActivityPanel restores partial work plan artifacts without crashing", () => {
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [],
      messages: [],
      artifacts: [partialWorkPlanArtifact]
    })
  );

  assert.match(html, /Recover source plan/);
  assert.match(html, /normal/);
  assert.match(html, /Use the saved source-refresh plan/);
  assert.doesNotMatch(html, /This item should not render/);
});

test("ActivityPanel prefers newer durable work-plan proof over stale live state", () => {
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [],
      messages: [],
      workPlan,
      artifacts: [liveWorkPlanArtifact, workPlanArtifact, newerWorkPlanArtifact]
    })
  );

  assert.match(html, /Review updated plan/);
  assert.match(html, /critic reviewer agent/);
  assert.match(html, /Review the new durable work plan/);
  assert.doesNotMatch(html, /Revise voiceover pacing/);
});

test("ActivityPanel keeps newer live work plan when saved proof list is stale", () => {
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [],
      messages: [],
      workPlan: freshLiveWorkPlan,
      artifacts: [workPlanArtifact]
    })
  );

  assert.match(html, /Draft fresh live plan/);
  assert.match(html, /substack essay writer/);
  assert.match(html, /just-returned work plan/);
  assert.doesNotMatch(html, /Refresh evidence/);
});

test("ActivityPanel renders scoped scheduler idle proof without a profile heartbeat", () => {
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [scopedIdleSchedulerEvent],
      messages: [],
      artifacts: [],
      workerProfiles: [profile],
      onRunAutopilotScheduler: async () => undefined,
      now: new Date("2026-05-18T12:00:06Z")
    })
  );

  const primaryHtml = stripTechnicalProofDetails(html);

  assert.match(primaryHtml, /Background check/);
  assert.match(html, /idle/);
  assert.match(primaryHtml, /No specialist updates this pass/);
  assert.doesNotMatch(primaryHtml, /0 profile\(s\)/);
  assert.doesNotMatch(primaryHtml, /0 heartbeat\(s\)/);
  assert.doesNotMatch(primaryHtml, /0 task\(s\)/);
  assert.doesNotMatch(primaryHtml, /event #3/);
  assert.match(html, /event #3/);
});

test("ActivityPanel renders active Autopilot heartbeat lease status", () => {
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [heartbeatEvent],
      messages: [],
      artifacts: [],
      workerProfiles: [
        {
          ...profile,
          heartbeat_claimed_by: "scheduler-worker-1",
          heartbeat_lease_until: "2026-05-18T12:01:00Z"
        }
      ],
      onRunAutopilotScheduler: async () => undefined,
      onHeartbeatAutopilot: async () => undefined,
      now: new Date("2026-05-18T12:00:30Z")
    })
  );

  const primaryHtml = stripTechnicalProofDetails(html);

  assert.match(primaryHtml, /Pulse running/);
  assert.match(primaryHtml, /A specialist pulse is already in progress/);
  assert.doesNotMatch(primaryHtml, /Heartbeat running/);
  assert.doesNotMatch(primaryHtml, /heartbeat/i);
  assert.doesNotMatch(primaryHtml, /lease until/i);
  assert.doesNotMatch(primaryHtml, /Lease held/i);
  assert.doesNotMatch(primaryHtml, /scheduler-worker-1/);
  assert.match(html, /Heartbeat running/);
  assert.match(html, /lease until/);
  assert.match(html, /claimed by scheduler-worker-1/);
  assert.match(html, /Lease held by scheduler-worker-1/);
});

test("ActivityPanel renders proof only for the newest active Autopilot profile", () => {
  const newerProfile: WorkerProfile = {
    ...profile,
    profile_id: "profile-new",
    last_heartbeat_at: null,
    created_at: "2026-05-18T11:30:00Z",
    updated_at: "2026-05-18T11:30:00Z"
  };
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [heartbeatEvent, schedulerEvent],
      messages: [],
      artifacts: [ledger],
      workerProfiles: [profile, newerProfile],
      onRunAutopilotScheduler: async () => undefined,
      onHeartbeatAutopilot: async () => undefined,
      now: new Date("2026-05-18T12:00:06Z")
    })
  );

  assert.match(html, /Due now/);
  assert.match(html, /No heartbeat has completed yet/);
  assert.doesNotMatch(html, /Schedule proof/);
  assert.doesNotMatch(html, /Always-on proof/);
  assert.doesNotMatch(html, /4 task\(s\)/);
});

test("ActivityPanel ignores scoped idle scheduler proof older than newest Autopilot profile", () => {
  const newerProfile: WorkerProfile = {
    ...profile,
    profile_id: "profile-new",
    last_heartbeat_at: null,
    created_at: "2026-05-18T11:30:00Z",
    updated_at: "2026-05-18T11:30:00Z"
  };
  const staleIdleSchedulerEvent: RunEvent = {
    ...scopedIdleSchedulerEvent,
    event_id: 4,
    created_at: "2026-05-18T11:05:00Z"
  };
  const html = renderToStaticMarkup(
    React.createElement(ActivityPanel, {
      events: [staleIdleSchedulerEvent],
      messages: [],
      artifacts: [],
      workerProfiles: [profile, newerProfile],
      onRunAutopilotScheduler: async () => undefined,
      now: new Date("2026-05-18T12:00:06Z")
    })
  );

  const primaryHtml = stripTechnicalProofDetails(html);

  assert.match(html, /Due now/);
  assert.match(html, /No heartbeat has completed yet/);
  assert.doesNotMatch(html, /Schedule proof/);
  assert.doesNotMatch(primaryHtml, /event #4/);
  assert.match(html, /event #4/);
});
