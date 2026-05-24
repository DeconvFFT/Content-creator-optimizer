import type { UUID, WorkerProfile } from "../api/types";
import { latestActiveAutopilotProfile } from "./autopilotProfile";

export function nextWorkerSchedulerStatusToken(currentToken: number) {
  return currentToken + 1;
}

export function shouldCommitWorkerSchedulerStatus(
  requestToken: number,
  currentToken: number
) {
  return requestToken === currentToken;
}

export function selectedWorkerSchedulerProfile(
  workerProfiles: WorkerProfile[],
  runId: UUID
) {
  return latestActiveAutopilotProfile(workerProfiles, runId);
}
