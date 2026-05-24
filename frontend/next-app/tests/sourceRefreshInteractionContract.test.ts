import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const pageSource = readFileSync("app/page.tsx", "utf8");

test("source refresh has a synchronous run-mutation gate before browser-triggered APIs", () => {
  const handlerStart = pageSource.indexOf("async function handleRefreshSources");
  const handlerEnd = pageSource.indexOf("function handleClearRun", handlerStart);
  const handlerSource = pageSource.slice(handlerStart, handlerEnd);
  const mutationGate = handlerSource.indexOf("blockSameRunMutationIfBusy(runId)");
  const sourceRefreshGate = handlerSource.indexOf(
    "beginRunAction(sourceRefreshActionGateRef.current)"
  );
  const agentCycleLock = handlerSource.indexOf("agentCycleInFlightRef.current = true;");
  const messageCall = handlerSource.indexOf("await sendAgentMessage(message)");
  const cycleCall = handlerSource.indexOf("await runAgentWorkerCycle(");
  const finishGate = handlerSource.indexOf(
    "finishRunAction(sourceRefreshActionGateRef.current, sourceRefreshToken)"
  );

  assert.match(
    pageSource,
    /const sourceRefreshActionGateRef = useRef\(\{ inFlight: false, token: 0 \}\);/
  );
  assert.notEqual(handlerStart, -1);
  assert.notEqual(mutationGate, -1);
  assert.notEqual(sourceRefreshGate, -1);
  assert.notEqual(agentCycleLock, -1);
  assert.notEqual(messageCall, -1);
  assert.notEqual(cycleCall, -1);
  assert.notEqual(finishGate, -1);
  assert.ok(mutationGate < sourceRefreshGate);
  assert.ok(sourceRefreshGate < agentCycleLock);
  assert.ok(agentCycleLock < messageCall);
  assert.ok(messageCall < cycleCall);
  assert.ok(cycleCall < finishGate);
  assert.match(pageSource, /invalidateRunAction\(sourceRefreshActionGateRef\.current\)/);
});

test("source refresh gate blocks later same-run mutation handlers", () => {
  assert.match(pageSource, /function blockSameRunMutationIfBusy\(runId\?: UUID\)/);

  for (const [handlerName, guardCall, mutatingCall] of [
    ["handleCompose", "blockSameRunMutationIfBusy(state.runId)", "beginRunAction(composerSubmitGateRef.current)"],
    ["handleContinueAgents", "blockSameRunMutationIfBusy(runId)", "continueAgents("],
    ["handleLaunchAutopilot", "blockSameRunMutationIfBusy(runId)", "beginRunAction(autopilotActionGateRef.current)"],
    ["handleStopAutopilot", "blockSameRunMutationIfBusy(runId)", "beginRunAction(autopilotActionGateRef.current)"],
    ["handleHeartbeatAutopilot", "blockSameRunMutationIfBusy(runId)", "autopilotHeartbeatInFlightRef.current"],
    ["handleStartWorkerSchedulerProcess", "blockSameRunMutationIfBusy(runId)", "beginRunAction(localSchedulerActionGateRef.current)"],
    ["handleStopWorkerSchedulerProcess", "blockSameRunMutationIfBusy(runId)", "beginRunAction(localSchedulerActionGateRef.current)"],
    ["handleRetryAgentMessage", "blockSameRunMutationIfBusy(runId)", "retryInFlightMessageIdsRef.current.add"],
    ["handleRevise", "blockSameRunMutationIfBusy(runId)", "beginRunAction(feedbackActionGateRef.current)"],
    ["handleResolveFeedback", "blockSameRunMutationIfBusy(runId)", "beginRunAction(feedbackActionGateRef.current)"],
    ["handleBuildGrowthPackage", "blockSameRunMutationIfBusy(runId)", "beginRunAction(productionActionGateRef.current)"],
    ["handleBuildMediaPlan", "blockSameRunMutationIfBusy(runId)", "beginRunAction(productionActionGateRef.current)"],
    ["handleCheckPublishReadiness", "blockSameRunMutationIfBusy(runId)", "beginRunAction(productionActionGateRef.current)"]
  ] as const) {
    const handlerStart = pageSource.indexOf(`async function ${handlerName}`);
    const handlerEnd = pageSource.indexOf("async function", handlerStart + 1);
    const handlerSource = pageSource.slice(handlerStart, handlerEnd === -1 ? undefined : handlerEnd);
    const guard = handlerSource.indexOf(guardCall);
    const mutation = handlerSource.indexOf(mutatingCall);

    assert.notEqual(handlerStart, -1, `${handlerName} exists`);
    assert.notEqual(guard, -1, `${handlerName} checks same-run mutation gate`);
    assert.notEqual(mutation, -1, `${handlerName} has expected mutating call`);
    assert.ok(guard < mutation, `${handlerName} checks source-refresh gate before mutation`);
  }
});

test("voice follow-up continuation participates in the same-run mutation gate", () => {
  const mutationGateSnapshot = pageSource.indexOf("agentCycleInFlight: agentCycleInFlightRef.current");
  const handlerStart = pageSource.indexOf("const handleVoiceFollowupReady = useCallback(");
  const handlerEnd = pageSource.indexOf("async function handleCompose", handlerStart);
  const handlerSource = pageSource.slice(handlerStart, handlerEnd);
  const sameRunGuard = handlerSource.indexOf("blockSameRunMutationIfBusy(runId)");
  const continuation = handlerSource.indexOf("continueAgents(");

  assert.notEqual(mutationGateSnapshot, -1);
  assert.notEqual(handlerStart, -1);
  assert.notEqual(sameRunGuard, -1);
  assert.notEqual(continuation, -1);
  assert.ok(sameRunGuard < continuation);
});

test("voice session start uses and clears the shared run mutation gate", () => {
  assert.match(
    pageSource,
    /const voiceSessionActionGateRef = useRef\(\{ inFlight: false, token: 0 \}\);/
  );
  assert.match(
    pageSource,
    /const voiceProofActionGateRef = useRef\(\{ inFlight: false, token: 0 \}\);/
  );

  const startHandlerStart = pageSource.indexOf("function handleVoiceRunMutationStart");
  const startHandlerEnd = pageSource.indexOf("function handleVoiceRunMutationFinish", startHandlerStart);
  const startHandlerSource = pageSource.slice(startHandlerStart, startHandlerEnd);
  const startGuard = startHandlerSource.indexOf("blockSameRunMutationIfBusy(runId)");
  const startGate = startHandlerSource.indexOf("beginRunAction(voiceSessionActionGateRef.current)");

  assert.notEqual(startHandlerStart, -1);
  assert.notEqual(startGuard, -1);
  assert.notEqual(startGate, -1);
  assert.ok(startGuard < startGate);

  const proofHandlerStart = pageSource.indexOf("function handleVoiceProofMutationStart");
  const proofHandlerEnd = pageSource.indexOf("function handleVoiceProofMutationFinish", proofHandlerStart);
  const proofHandlerSource = pageSource.slice(proofHandlerStart, proofHandlerEnd);
  const proofGuard = proofHandlerSource.indexOf("blockSameRunMutationIfBusy(runId)");
  const proofGate = proofHandlerSource.indexOf("beginRunAction(voiceProofActionGateRef.current)");

  assert.notEqual(proofHandlerStart, -1);
  assert.notEqual(proofGuard, -1);
  assert.notEqual(proofGate, -1);
  assert.ok(proofGuard < proofGate);

  const clearRunStart = pageSource.indexOf("function handleClearRun()");
  const clearRunEnd = pageSource.indexOf("async function handleLaunchAutopilot", clearRunStart);
  const clearRunSource = pageSource.slice(clearRunStart, clearRunEnd);

  assert.notEqual(clearRunStart, -1);
  assert.match(clearRunSource, /invalidateRunAction\(voiceSessionActionGateRef\.current\)/);
  assert.match(clearRunSource, /invalidateRunAction\(voiceProofActionGateRef\.current\)/);
});
