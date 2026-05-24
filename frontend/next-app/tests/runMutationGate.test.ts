import assert from "node:assert/strict";
import test from "node:test";

import {
  isRunMutationInFlight,
  isWorkPlanPlanningInFlight
} from "../lib/state/runMutationGate";

test("work-plan planning gate reports only active planning", () => {
  assert.equal(isWorkPlanPlanningInFlight({ inFlight: false, token: 2 }), false);
  assert.equal(isWorkPlanPlanningInFlight({ inFlight: true, token: 3 }), true);
});

test("run mutation gate covers same-run mutation actions", () => {
  const idleGates = {
    composer: { inFlight: false, token: 0 },
    sourceRefresh: { inFlight: false, token: 0 },
    production: { inFlight: false, token: 0 },
    feedback: { inFlight: false, token: 0 },
    voiceSession: { inFlight: false, token: 0 },
    voiceProof: { inFlight: false, token: 0 },
    autopilot: { inFlight: false, token: 0 },
    localScheduler: { inFlight: false, token: 0 }
  };

  assert.equal(isRunMutationInFlight(idleGates, "run-1"), false);
  assert.equal(isRunMutationInFlight({
    ...idleGates,
    feedback: { inFlight: true, token: 1 }
  }, "run-1"), true);
  assert.equal(isRunMutationInFlight({
    ...idleGates,
    sourceRefresh: { inFlight: true, token: 1 }
  }, "run-1"), true);
  assert.equal(isRunMutationInFlight({
    ...idleGates,
    production: { inFlight: true, token: 1 }
  }, "run-1"), true);
  assert.equal(isRunMutationInFlight({
    ...idleGates,
    voiceSession: { inFlight: true, token: 1 }
  }, "run-1"), true);
  assert.equal(isRunMutationInFlight({
    ...idleGates,
    voiceProof: { inFlight: true, token: 1 }
  }, "run-1"), true);
  assert.equal(isRunMutationInFlight({
    ...idleGates,
    autopilotHeartbeatInFlight: true
  }, "run-1"), true);
  assert.equal(isRunMutationInFlight({
    ...idleGates,
    agentCycleInFlight: true
  }, "run-1"), true);
});

test("run-scoped scheduler mutation blocks only its active run", () => {
  const schedulerRuns = new Set(["run-1"]);
  const gates = {
    composer: { inFlight: false, token: 0 },
    sourceRefresh: { inFlight: false, token: 0 },
    production: { inFlight: false, token: 0 },
    feedback: { inFlight: false, token: 0 },
    voiceSession: { inFlight: false, token: 0 },
    voiceProof: { inFlight: false, token: 0 },
    autopilot: { inFlight: false, token: 0 },
    localScheduler: { inFlight: false, token: 0 },
    autopilotSchedulerInFlightRunIds: schedulerRuns
  };

  assert.equal(isRunMutationInFlight(gates, "run-1"), true);
  assert.equal(isRunMutationInFlight(gates, "run-2"), false);
  assert.equal(isRunMutationInFlight(gates), false);
});
