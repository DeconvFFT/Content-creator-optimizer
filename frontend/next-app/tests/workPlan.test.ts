import assert from "node:assert/strict";
import test from "node:test";

import {
  workPlanMaterializationInput,
  workPlanPostRunRefreshInput,
  workPlanRunnableAgentIds
} from "../lib/state/workPlan";
import type { RunWorkPlanResult } from "../lib/api/types";

const baseWorkPlan: RunWorkPlanResult = {
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
      reason: "Creator feedback asks for more natural pacing.",
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
  artifact_id: "work-plan-1",
  event_id: 10,
  refresh_reason: "creator_app_next_actions",
  summary: "Built 2 next action(s)."
};

test("workPlanRunnableAgentIds dedupes recommended and owner agents in plan order", () => {
  assert.deepEqual(workPlanRunnableAgentIds(baseWorkPlan), [
    "audio-producer",
    "web-research-agent"
  ]);
});

test("workPlanRunnableAgentIds falls back to item owners when recommendations are absent", () => {
  assert.deepEqual(
    workPlanRunnableAgentIds({
      ...baseWorkPlan,
      recommended_agent_ids: []
    }),
    ["audio-producer", "web-research-agent"]
  );
});

test("workPlanRunnableAgentIds ignores blank agent ids and empty plans", () => {
  assert.deepEqual(
    workPlanRunnableAgentIds({
      ...baseWorkPlan,
      recommended_agent_ids: ["  ", "editor-in-chief"],
      plan_items: [
        {
          ...baseWorkPlan.plan_items[0],
          owner_agent_id: ""
        }
      ]
    }),
    ["editor-in-chief"]
  );
  assert.deepEqual(workPlanRunnableAgentIds(null), []);
});

test("workPlanRunnableAgentIds refuses recommendations for zero-item plans", () => {
  assert.deepEqual(
    workPlanRunnableAgentIds({
      ...baseWorkPlan,
      plan_items: [],
      recommended_agent_ids: ["audio-producer"]
    }),
    []
  );
});

test("workPlanMaterializationInput requests durable follow-up tasks for run-plan execution", () => {
  assert.deepEqual(workPlanMaterializationInput(baseWorkPlan), {
    runId: "run-1",
    maxItems: 8,
    createFollowupTasks: true,
    refreshReason: "creator_app_run_plan"
  });
});

test("workPlanMaterializationInput preserves larger visible plans when materializing", () => {
  const longPlan: RunWorkPlanResult = {
    ...baseWorkPlan,
    plan_items: Array.from({ length: 9 }, (_, index) => ({
      ...baseWorkPlan.plan_items[0],
      item_id: `item-${index}`,
      title: `Plan item ${index}`
    }))
  };

  assert.equal(workPlanMaterializationInput(longPlan).maxItems, 9);
});

test("workPlanPostRunRefreshInput refreshes next actions without creating tasks", () => {
  assert.deepEqual(workPlanPostRunRefreshInput(baseWorkPlan), {
    runId: "run-1",
    maxItems: 8,
    createFollowupTasks: false,
    refreshReason: "creator_app_after_run_plan"
  });
});
