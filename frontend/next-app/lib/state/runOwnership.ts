export type RunOwnedState = {
  runId?: string;
  busyLabel?: string;
};

export type RunVersionSnapshot = {
  runId?: string;
  version: number;
};

export type RunBoundRequestSnapshot = {
  runId?: string;
  token: number;
};

export type RunActionGate = {
  inFlight: boolean;
  token: number;
};

export type RunVersionedActionSnapshot = {
  version: number;
  token: number;
};

export function isRunVersionCurrent(expectedVersion: number, currentVersion: number) {
  return expectedVersion === currentVersion;
}

export function isRunOwnerCurrent(
  snapshot: RunVersionSnapshot,
  currentRunId: string | undefined,
  currentVersion: number
) {
  return snapshot.runId === currentRunId && isRunVersionCurrent(snapshot.version, currentVersion);
}

export function isRunBoundRequestCurrent(
  snapshot: RunBoundRequestSnapshot,
  currentRunId: string | undefined,
  currentToken: number
) {
  return snapshot.runId === currentRunId && snapshot.token === currentToken;
}

export function isRunVersionedActionCurrent(
  snapshot: RunVersionedActionSnapshot,
  currentVersion: number,
  currentToken: number
) {
  return isRunVersionCurrent(snapshot.version, currentVersion) && snapshot.token === currentToken;
}

export function beginRunAction(gate: RunActionGate) {
  if (gate.inFlight) {
    return undefined;
  }
  gate.inFlight = true;
  gate.token += 1;
  return gate.token;
}

export function finishRunAction(gate: RunActionGate, token: number) {
  if (gate.token === token) {
    gate.inFlight = false;
  }
}

export function invalidateRunAction(gate: RunActionGate) {
  gate.token += 1;
  gate.inFlight = false;
  return gate.token;
}

export function clearBusyForOwnedRun<TState extends RunOwnedState>(
  state: TState,
  runId?: string | null
) {
  if (state.runId !== (runId ?? undefined)) {
    return state;
  }
  if (state.busyLabel === undefined) {
    return state;
  }
  return {
    ...state,
    busyLabel: undefined
  };
}

export function clearBusyForOwnedRunSnapshot<TState extends RunOwnedState>(
  state: TState,
  snapshot: RunVersionSnapshot,
  currentVersion: number
) {
  if (!isRunOwnerCurrent(snapshot, state.runId, currentVersion)) {
    return state;
  }
  return clearBusyForOwnedRun(state, snapshot.runId);
}
