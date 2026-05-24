import type { RunActionGate } from "./runOwnership";

export type RunMutationGateSnapshot = {
  composer: RunActionGate;
  sourceRefresh: RunActionGate;
  production: RunActionGate;
  feedback: RunActionGate;
  voiceSession: RunActionGate;
  voiceProof: RunActionGate;
  autopilot: RunActionGate;
  localScheduler: RunActionGate;
  agentCycleInFlight?: boolean;
  autopilotHeartbeatInFlight?: boolean;
  autopilotSchedulerInFlightRunIds?: ReadonlySet<string>;
};

export function isWorkPlanPlanningInFlight(workPlanGate: RunActionGate) {
  return workPlanGate.inFlight;
}

export function isRunMutationInFlight(
  gates: RunMutationGateSnapshot,
  runId?: string
) {
  return (
    gates.composer.inFlight ||
    gates.sourceRefresh.inFlight ||
    gates.production.inFlight ||
    gates.feedback.inFlight ||
    gates.voiceSession.inFlight ||
    gates.voiceProof.inFlight ||
    gates.autopilot.inFlight ||
    gates.localScheduler.inFlight ||
    Boolean(gates.agentCycleInFlight) ||
    Boolean(gates.autopilotHeartbeatInFlight) ||
    Boolean(runId && gates.autopilotSchedulerInFlightRunIds?.has(runId))
  );
}
