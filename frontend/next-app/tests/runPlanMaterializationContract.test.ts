import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const pageSource = readFileSync("app/page.tsx", "utf8");

test("Run plan holds the agent-cycle lock before materializing follow-up tasks", () => {
  const handlerStart = pageSource.indexOf("async function handleRunWorkPlan");
  const lockAcquire = pageSource.indexOf("agentCycleInFlightRef.current = true;", handlerStart);
  const materializeCall = pageSource.indexOf(
    "buildRunWorkPlan(workPlanMaterializationInput(workPlan))",
    handlerStart
  );
  const cycleCall = pageSource.indexOf("runAgentCycleAndRefresh(", materializeCall);
  const postRunRefreshCall = pageSource.indexOf(
    "buildRunWorkPlan(workPlanPostRunRefreshInput(materializedPlan))",
    cycleCall
  );
  const lockRelease = pageSource.indexOf("agentCycleInFlightRef.current = false;", materializeCall);

  assert.notEqual(handlerStart, -1);
  assert.notEqual(lockAcquire, -1);
  assert.notEqual(materializeCall, -1);
  assert.notEqual(cycleCall, -1);
  assert.notEqual(postRunRefreshCall, -1);
  assert.notEqual(lockRelease, -1);
  assert.ok(lockAcquire < materializeCall);
  assert.ok(materializeCall < cycleCall);
  assert.ok(cycleCall < postRunRefreshCall);
  assert.ok(postRunRefreshCall < lockRelease);
});

test("Run plan executes through the lock-free internal cycle runner", () => {
  const handlerStart = pageSource.indexOf("async function handleRunWorkPlan");
  const handlerEnd = pageSource.indexOf("async function handleRefreshSources", handlerStart);
  const handlerSource = pageSource.slice(handlerStart, handlerEnd);

  assert.match(handlerSource, /runAgentCycleAndRefresh\(/);
  assert.doesNotMatch(handlerSource, /await continueAgents\(/);
});

test("Plan next uses a synchronous single-flight gate before async work", () => {
  const handlerStart = pageSource.indexOf("async function handleBuildWorkPlan");
  const handlerEnd = pageSource.indexOf("async function handleRunWorkPlan", handlerStart);
  const handlerSource = pageSource.slice(handlerStart, handlerEnd);

  assert.match(pageSource, /const workPlanActionGateRef = useRef\(\{ inFlight: false, token: 0 \}\);/);
  assert.notEqual(handlerStart, -1);
  assert.match(handlerSource, /beginRunAction\(workPlanActionGateRef\.current\)/);
  assert.match(handlerSource, /isRunVersionedActionCurrent\(/);
  assert.match(handlerSource, /finishRunAction\(workPlanActionGateRef\.current, workPlanToken\)/);
  assert.match(pageSource, /invalidateRunAction\(workPlanActionGateRef\.current\)/);
});

test("Plan next and Run plan block each other's in-flight work", () => {
  const buildStart = pageSource.indexOf("async function handleBuildWorkPlan");
  const buildEnd = pageSource.indexOf("async function handleRunWorkPlan", buildStart);
  const buildSource = pageSource.slice(buildStart, buildEnd);
  const runStart = buildEnd;
  const runEnd = pageSource.indexOf("async function handleRefreshSources", runStart);
  const runSource = pageSource.slice(runStart, runEnd);
  const buildCycleGate = buildSource.indexOf("agentCycleInFlightRef.current");
  const buildActionGate = buildSource.indexOf("beginRunAction(workPlanActionGateRef.current)");
  const runPlanningGate = runSource.indexOf("workPlanActionGateRef.current.inFlight");
  const runCycleGate = runSource.indexOf("if (agentCycleInFlightRef.current)");
  const runLockAcquire = runSource.indexOf("agentCycleInFlightRef.current = true;");

  assert.notEqual(buildCycleGate, -1);
  assert.notEqual(buildActionGate, -1);
  assert.notEqual(runPlanningGate, -1);
  assert.notEqual(runCycleGate, -1);
  assert.notEqual(runLockAcquire, -1);
  assert.ok(buildCycleGate < buildActionGate);
  assert.ok(runPlanningGate < runCycleGate);
  assert.ok(runCycleGate < runLockAcquire);
});

test("agent-cycle entry points block while Plan next is in flight", () => {
  const continueStart = pageSource.indexOf("const continueAgents = useCallback");
  const continueEnd = pageSource.indexOf("async function handleCompose", continueStart);
  const continueSource = pageSource.slice(continueStart, continueEnd);
  const sourceStart = pageSource.indexOf("async function handleRefreshSources");
  const sourceEnd = pageSource.indexOf("function handleClearRun", sourceStart);
  const sourceRefreshSource = pageSource.slice(sourceStart, sourceEnd);
  const retryStart = pageSource.indexOf("async function handleRetryAgentMessage");
  const retryEnd = pageSource.indexOf("function toggleArtifact", retryStart);
  const retrySource = pageSource.slice(retryStart, retryEnd);

  for (const handlerSource of [continueSource, sourceRefreshSource, retrySource]) {
    const sharedGate = handlerSource.indexOf("blockSameRunMutationIfBusy(runId)");
    const planningGate = sharedGate === -1
      ? handlerSource.indexOf("workPlanActionGateRef.current.inFlight")
      : sharedGate;
    const cycleLock = handlerSource.indexOf("agentCycleInFlightRef.current");

    assert.notEqual(planningGate, -1);
    assert.notEqual(cycleLock, -1);
    assert.ok(planningGate < cycleLock);
  }
});

test("Plan next and composer submit block each other's run mutations", () => {
  const composeStart = pageSource.indexOf("async function handleCompose");
  const composeEnd = pageSource.indexOf("async function handleCreateVoiceRun", composeStart);
  const composeSource = pageSource.slice(composeStart, composeEnd);
  const buildStart = pageSource.indexOf("async function handleBuildWorkPlan");
  const buildEnd = pageSource.indexOf("async function handleRunWorkPlan", buildStart);
  const buildSource = pageSource.slice(buildStart, buildEnd);
  const composePlanningGate = composeSource.indexOf("blockSameRunMutationIfBusy(state.runId)");
  const composeRouteCall = composeSource.indexOf("routeConversationTurn({");
  const buildMutationGate = buildSource.indexOf("blockSameRunMutationIfBusy(runId)");
  const buildPlanGate = buildSource.indexOf("beginRunAction(workPlanActionGateRef.current)");

  assert.notEqual(composePlanningGate, -1);
  assert.notEqual(composeRouteCall, -1);
  assert.notEqual(buildMutationGate, -1);
  assert.notEqual(buildPlanGate, -1);
  assert.ok(composePlanningGate < composeRouteCall);
  assert.ok(buildMutationGate < buildPlanGate);
});

test("Plan next is mutually exclusive with same-run mutation gates", () => {
  const buildStart = pageSource.indexOf("async function handleBuildWorkPlan");
  const buildEnd = pageSource.indexOf("async function handleRunWorkPlan", buildStart);
  const buildSource = pageSource.slice(buildStart, buildEnd);
  const runMutationGate = buildSource.indexOf("blockSameRunMutationIfBusy(runId)");
  const buildPlanGate = buildSource.indexOf("beginRunAction(workPlanActionGateRef.current)");

  assert.match(pageSource, /function isWorkPlanPlanningInFlight\(\)/);
  assert.match(pageSource, /function isRunMutationInFlight\(runId\?: UUID\)/);
  assert.notEqual(runMutationGate, -1);
  assert.notEqual(buildPlanGate, -1);
  assert.ok(runMutationGate < buildPlanGate);

  for (const [handlerName, gateName] of [
    ["handleRevise", "feedbackActionGateRef"],
    ["handleResolveFeedback", "feedbackActionGateRef"],
    ["handleBuildGrowthPackage", "productionActionGateRef"],
    ["handleBuildMediaPlan", "productionActionGateRef"],
    ["handleCheckPublishReadiness", "productionActionGateRef"],
    ["handleLaunchAutopilot", "autopilotActionGateRef"],
    ["handleStopAutopilot", "autopilotActionGateRef"],
    ["handleStartWorkerSchedulerProcess", "localSchedulerActionGateRef"],
    ["handleStopWorkerSchedulerProcess", "localSchedulerActionGateRef"]
  ] as const) {
    const handlerStart = pageSource.indexOf(`async function ${handlerName}`);
    const handlerEnd = pageSource.indexOf("async function", handlerStart + 1);
    const handlerSource = pageSource.slice(handlerStart, handlerEnd === -1 ? undefined : handlerEnd);
    const planningGate = handlerSource.indexOf("blockSameRunMutationIfBusy(runId)");
    const actionGate = handlerSource.indexOf(`beginRunAction(${gateName}.current)`);

    assert.notEqual(handlerStart, -1);
    assert.notEqual(planningGate, -1);
    assert.notEqual(actionGate, -1);
    assert.ok(planningGate < actionGate);
  }
});
