import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const pageSource = readFileSync("app/page.tsx", "utf8");
const clientSource = readFileSync("lib/api/client.ts", "utf8");

test("Activity retry uses the existing A2A retry endpoint", () => {
  assert.match(clientSource, /authorizeAgentMessageRetry/);
  assert.match(clientSource, /\/api\/a2a\/messages\/\$\{input\.messageId\}\/retry/);
  assert.match(clientSource, /agent_id: input\.agentId \?\? "agent-harness-engineer"/);
  assert.match(clientSource, /reset_attempt_count: input\.resetAttemptCount !== false/);
});

test("Activity retry is guarded by active run ownership before refreshing", () => {
  const handlerStart = pageSource.indexOf("async function handleRetryAgentMessage");
  const handlerEnd = pageSource.indexOf("function toggleArtifact", handlerStart);
  const handlerSource = pageSource.slice(handlerStart, handlerEnd);
  const guardIndex = handlerSource.indexOf(
    "retryInFlightMessageIdsRef.current.has(message.message_id)"
  );
  const addIndex = handlerSource.indexOf(
    "retryInFlightMessageIdsRef.current.add(message.message_id)"
  );
  const cycleLockIndex = handlerSource.indexOf("agentCycleInFlightRef.current = true");
  const authorizeIndex = handlerSource.indexOf("authorizeAgentMessageRetry");
  const cycleIndex = handlerSource.indexOf("runAgentCycleAndRefresh");

  assert.notEqual(handlerStart, -1);
  assert.notEqual(handlerEnd, -1);
  assert.match(handlerSource, /message\.run_id !== runId/);
  assert.match(handlerSource, /isActiveRunOwner\(runId, runVersion\)/);
  assert.match(handlerSource, /agentCycleInFlightRef\.current/);
  assert.notEqual(guardIndex, -1);
  assert.notEqual(addIndex, -1);
  assert.notEqual(cycleLockIndex, -1);
  assert.notEqual(authorizeIndex, -1);
  assert.notEqual(cycleIndex, -1);
  assert.ok(guardIndex < addIndex);
  assert.ok(addIndex < authorizeIndex);
  assert.ok(cycleLockIndex < authorizeIndex);
  assert.ok(authorizeIndex < cycleIndex);
  assert.match(handlerSource, /authorizeAgentMessageRetry/);
  assert.match(handlerSource, /agentIds: \[result\.message\.recipient_agent_id\]/);
  assert.match(handlerSource, /messageIds: \[result\.message\.message_id\]/);
  assert.match(handlerSource, /maxTasksPerAgent: 1/);
  assert.match(handlerSource, /maxRounds: 1/);
  assert.match(handlerSource, /isRunVersionCurrent\(runVersion, runVersionRef\.current\)/);
  assert.match(
    handlerSource,
    /finally\s*{[\s\S]*retryInFlightMessageIdsRef\.current\.delete\(message\.message_id\)/
  );
  assert.match(
    handlerSource,
    /finally\s*{[\s\S]*agentCycleInFlightRef\.current = false/
  );
  assert.match(handlerSource, /setRetryingMessageIds\(\(current\) => current\.filter/);
});

test("Activity retry passes in-flight ids to the rail for button-level disablement", () => {
  assert.match(pageSource, /const \[retryingMessageIds, setRetryingMessageIds\]/);
  assert.match(pageSource, /const retryInFlightMessageIdsRef = useRef<Set<UUID>>/);
  assert.match(pageSource, /retryingMessageIds={retryingMessageIds}/);
});

test("Worker cycle client supports message-targeted execution", () => {
  assert.match(clientSource, /messageIds\?: UUID\[\]/);
  assert.match(clientSource, /continueMessageLineage\?: boolean/);
  assert.match(clientSource, /message_ids: input\.messageIds \?\? \[\]/);
  assert.match(
    clientSource,
    /continue_message_lineage: input\.continueMessageLineage === true/
  );
});

test("Creator app exposes supervised local worker scheduler process controls", () => {
  assert.match(clientSource, /getWorkerSchedulerProcessStatus/);
  assert.match(clientSource, /\/api\/worker-scheduler-process/);
  assert.match(clientSource, /startWorkerSchedulerProcess/);
  assert.match(clientSource, /\/api\/worker-scheduler-process\/start/);
  assert.match(clientSource, /stopWorkerSchedulerProcess/);
  assert.match(clientSource, /\/api\/worker-scheduler-process\/stop/);
  assert.match(clientSource, /poll_interval_seconds: input\.pollIntervalSeconds/);

  assert.match(pageSource, /workerSchedulerProcess\?: WorkerSchedulerProcessStatusResult/);
  assert.match(pageSource, /handleStartWorkerSchedulerProcess/);
  assert.match(pageSource, /handleStopWorkerSchedulerProcess/);
  assert.match(pageSource, /selectedWorkerSchedulerProfile\(\s*state\.workerProfiles \?\? \[\],\s*runId\s*\)/);
  assert.doesNotMatch(
    pageSource.slice(
      pageSource.indexOf("async function handleStartWorkerSchedulerProcess"),
      pageSource.indexOf("async function handleStopWorkerSchedulerProcess")
    ),
    /state\.workerProfiles\?\.find/
  );
  assert.match(pageSource, /getWorkerSchedulerProcessStatus/);
  assert.match(pageSource, /startWorkerSchedulerProcess/);
  assert.match(pageSource, /stopWorkerSchedulerProcess/);
  assert.match(pageSource, /onStartWorkerScheduler={handleStartWorkerSchedulerProcess}/);
  assert.match(pageSource, /onStopWorkerScheduler={handleStopWorkerSchedulerProcess}/);
});

test("local scheduler process controls use a synchronous single-flight gate", () => {
  assert.match(pageSource, /const localSchedulerActionGateRef = useRef\(\{ inFlight: false, token: 0 \}\);/);
  for (const handlerName of [
    "handleStartWorkerSchedulerProcess",
    "handleStopWorkerSchedulerProcess"
  ]) {
    const handlerIndex = pageSource.indexOf(`async function ${handlerName}(`);
    const nextHandlerIndex = pageSource.indexOf("async function ", handlerIndex + 1);
    const handlerSource = pageSource.slice(
      handlerIndex,
      nextHandlerIndex === -1 ? undefined : nextHandlerIndex
    );

    assert.notEqual(handlerIndex, -1);
    assert.match(handlerSource, /beginRunAction\(localSchedulerActionGateRef\.current\)/);
    assert.match(handlerSource, /isRunVersionedActionCurrent\(/);
    assert.match(handlerSource, /finishRunAction\(localSchedulerActionGateRef\.current, localSchedulerToken\)/);
  }
  assert.match(pageSource, /invalidateRunAction\(localSchedulerActionGateRef\.current\)/);
});
