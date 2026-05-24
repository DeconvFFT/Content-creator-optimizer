import assert from "node:assert/strict";
import test from "node:test";

import {
  beginRunAction,
  clearBusyForOwnedRun,
  clearBusyForOwnedRunSnapshot,
  finishRunAction,
  invalidateRunAction,
  isRunBoundRequestCurrent,
  isRunVersionedActionCurrent,
  isRunOwnerCurrent,
  isRunVersionCurrent
} from "../lib/state/runOwnership";

function deferred<TValue>() {
  let resolve!: (value: TValue) => void;
  const promise = new Promise<TValue>((innerResolve) => {
    resolve = innerResolve;
  });
  return { promise, resolve };
}

test("run version guard rejects stale async completions after New", () => {
  const started = { runId: "run-old", version: 4 };

  assert.equal(isRunVersionCurrent(started.version, 4), true);
  assert.equal(isRunVersionCurrent(started.version, 5), false);
  assert.equal(isRunOwnerCurrent(started, "run-old", 4), true);
  assert.equal(isRunOwnerCurrent(started, undefined, 5), false);
});

test("stale async cleanup clears busy state only for the owning run", () => {
  const oldRunStillMounted = {
    runId: "run-old",
    busyLabel: "Generating source-backed drafts",
    lastSummary: "old"
  };
  const cleared = clearBusyForOwnedRun(oldRunStillMounted, "run-old");
  assert.notEqual(cleared, oldRunStillMounted);
  assert.equal(cleared.runId, "run-old");
  assert.equal(cleared.busyLabel, undefined);
  assert.equal(cleared.lastSummary, "old");

  const newerRunBusy = {
    runId: "run-new",
    busyLabel: "Continuing specialist agents",
    lastSummary: "new"
  };
  const preserved = clearBusyForOwnedRun(newerRunBusy, "run-old");
  assert.equal(preserved, newerRunBusy);
  assert.equal(preserved.busyLabel, "Continuing specialist agents");
});

test("New during in-flight create flow does not let old cleanup repopulate busy state", () => {
  const createStarted = { runId: undefined, version: 8 };
  const afterNew = {
    runId: undefined,
    busyLabel: undefined,
    lastSummary: "Started a clean local session."
  };

  assert.equal(isRunOwnerCurrent(createStarted, afterNew.runId, 9), false);
  const cleaned = clearBusyForOwnedRun(afterNew, createStarted.runId);

  assert.equal(cleaned, afterNew);
  assert.equal(cleaned.runId, undefined);
  assert.equal(cleaned.busyLabel, undefined);
  assert.equal(cleaned.lastSummary, "Started a clean local session.");
});

test("stale no-run cleanup does not clear newer no-run work", () => {
  const staleNoRunRequest = { runId: undefined, version: 8 };
  const newerNoRunWork = {
    runId: undefined,
    busyLabel: "Creating voice run",
    lastSummary: "Started a clean local session."
  };

  const preserved = clearBusyForOwnedRunSnapshot(newerNoRunWork, staleNoRunRequest, 9);

  assert.equal(preserved, newerNoRunWork);
  assert.equal(preserved.busyLabel, "Creating voice run");
});

test("version-scoped cleanup clears only the current owner", () => {
  const currentRequest = { runId: "run-1", version: 4 };
  const currentWork = {
    runId: "run-1",
    busyLabel: "Running planned agents",
    lastSummary: "run state"
  };

  const cleared = clearBusyForOwnedRunSnapshot(currentWork, currentRequest, 4);

  assert.notEqual(cleared, currentWork);
  assert.equal(cleared.runId, "run-1");
  assert.equal(cleared.busyLabel, undefined);
  assert.equal(cleared.lastSummary, "run state");
});

test("same-version no-run compose submissions are single-flight before busy propagates", () => {
  const gate = { inFlight: false, token: 0 };
  const firstToken = beginRunAction(gate);
  const duplicateToken = beginRunAction(gate);

  assert.equal(firstToken, 1);
  assert.equal(duplicateToken, undefined);
  assert.deepEqual(gate, { inFlight: true, token: 1 });

  finishRunAction(gate, firstToken ?? 0);

  assert.deepEqual(gate, { inFlight: false, token: 1 });
});

test("out-of-order no-run compose completions commit only the latest owner", async () => {
  let currentVersion = 8;
  const gate = { inFlight: false, token: 0 };
  const firstToken = beginRunAction(gate);
  assert.equal(firstToken, 1);
  const firstOwner = { version: currentVersion, token: firstToken ?? 0 };
  const firstRequest = deferred<string>();

  invalidateRunAction(gate);
  currentVersion += 1;
  const secondToken = beginRunAction(gate);
  assert.equal(secondToken, 3);
  const secondOwner = { version: currentVersion, token: secondToken ?? 0 };
  const secondRequest = deferred<string>();
  const committed: string[] = [];

  const firstCompletion = (async () => {
    const value = await firstRequest.promise;
    if (isRunVersionedActionCurrent(firstOwner, currentVersion, gate.token)) {
      committed.push(value);
    }
  })();
  const secondCompletion = (async () => {
    const value = await secondRequest.promise;
    if (isRunVersionedActionCurrent(secondOwner, currentVersion, gate.token)) {
      committed.push(value);
    }
  })();

  secondRequest.resolve("new no-run compose result");
  firstRequest.resolve("stale no-run compose result");
  await Promise.all([firstCompletion, secondCompletion]);

  assert.deepEqual(committed, ["new no-run compose result"]);
  finishRunAction(gate, secondToken ?? 0);
  assert.deepEqual(gate, { inFlight: false, token: 3 });
});

test("late async completion preserves a newer run that took ownership", async () => {
  let currentVersion = 12;
  let state: {
    runId: string;
    busyLabel?: string;
    lastSummary: string;
  } = {
    runId: "run-old",
    busyLabel: "Generating source-backed drafts",
    lastSummary: "old run"
  };
  const owner = { runId: state.runId, version: currentVersion };
  const routedTurn = deferred<{ runId: string }>();

  const staleCompletion = (async () => {
    await routedTurn.promise;
    if (!isRunOwnerCurrent(owner, state.runId, currentVersion)) {
      state = clearBusyForOwnedRun(state, owner.runId);
      return;
    }
    state = {
      ...state,
      busyLabel: undefined,
      lastSummary: "stale completion incorrectly committed"
    };
  })();

  currentVersion += 1;
  state = {
    runId: "run-new",
    busyLabel: "Continuing specialist agents",
    lastSummary: "new run"
  };

  routedTurn.resolve({ runId: "run-old" });
  await staleCompletion;

  assert.equal(state.runId, "run-new");
  assert.equal(state.busyLabel, "Continuing specialist agents");
  assert.equal(state.lastSummary, "new run");
});

test("run-bound proof guard rejects stale voice smoke and timing completions", async () => {
  let currentRunId: string | undefined = "run-old";
  let smokeToken = 7;
  let timingToken = 3;
  const smokeStarted = { runId: currentRunId, token: smokeToken + 1 };
  const timingStarted = { runId: currentRunId, token: timingToken + 1 };
  smokeToken = smokeStarted.token;
  timingToken = timingStarted.token;
  const smoke = deferred<string>();
  const timing = deferred<string>();
  const committed: string[] = [];

  const smokeCompletion = (async () => {
    const value = await smoke.promise;
    if (isRunBoundRequestCurrent(smokeStarted, currentRunId, smokeToken)) {
      committed.push(value);
    }
  })();
  const timingCompletion = (async () => {
    const value = await timing.promise;
    if (isRunBoundRequestCurrent(timingStarted, currentRunId, timingToken)) {
      committed.push(value);
    }
  })();

  currentRunId = "run-new";
  smokeToken += 1;
  timingToken += 1;

  smoke.resolve("stale smoke proof");
  timing.resolve("stale timing proof");
  await Promise.all([smokeCompletion, timingCompletion]);

  assert.deepEqual(committed, []);
});
