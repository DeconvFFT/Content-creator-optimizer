import type { RunWorkPlanResult } from "../api/types";

const RUN_PLAN_REFRESH_REASON = "creator_app_run_plan";
const RUN_PLAN_POST_RUN_REFRESH_REASON = "creator_app_after_run_plan";
const RUN_PLAN_MIN_ITEMS = 8;

export function workPlanRunnableAgentIds(workPlan?: RunWorkPlanResult | null) {
  if (!workPlan || workPlan.plan_items.length === 0) {
    return [];
  }
  const agentIds = [
    ...workPlan.recommended_agent_ids,
    ...workPlan.plan_items.map((item) => item.owner_agent_id)
  ];
  return Array.from(new Set(agentIds.map((agentId) => agentId.trim()).filter(Boolean)));
}

export function workPlanMaterializationInput(workPlan: RunWorkPlanResult) {
  return {
    runId: workPlan.run_id,
    maxItems: Math.max(RUN_PLAN_MIN_ITEMS, workPlan.plan_items.length),
    createFollowupTasks: true,
    refreshReason: RUN_PLAN_REFRESH_REASON
  };
}

export function workPlanPostRunRefreshInput(workPlan: RunWorkPlanResult) {
  return {
    runId: workPlan.run_id,
    maxItems: Math.max(RUN_PLAN_MIN_ITEMS, workPlan.plan_items.length),
    createFollowupTasks: false,
    refreshReason: RUN_PLAN_POST_RUN_REFRESH_REASON
  };
}
