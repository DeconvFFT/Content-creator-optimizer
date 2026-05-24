import assert from "node:assert/strict";
import test from "node:test";

import {
  localLiveKitProcessStartBlocker,
  shouldAutoStartLocalLiveKitProcess,
  shouldAutoStartVoiceAgentProcess,
  voiceAgentProcessStartBlocker
} from "../lib/voice/process";
import type {
  LocalLiveKitProcessStatusResult,
  VoiceAgentProcessStatusResult
} from "../lib/api/types";

function processStatus(
  overrides: Partial<VoiceAgentProcessStatusResult> = {}
): VoiceAgentProcessStatusResult {
  return {
    enabled: true,
    status: "stopped",
    running: false,
    pid: null,
    returncode: null,
    last_error: null,
    started_at: null,
    stopped_at: null,
    command: ["python", "-m", "all_about_llms.cli", "run-voice-agent"],
    log_tail: [],
    next_actions: [],
    summary: "Local Gemma/Kokoro LiveKit voice-agent process is stopped.",
    ...overrides
  };
}

function liveKitProcessStatus(
  overrides: Partial<LocalLiveKitProcessStatusResult> = {}
): LocalLiveKitProcessStatusResult {
  return {
    enabled: true,
    mode: "native",
    status: "stopped",
    running: false,
    pid: null,
    returncode: null,
    last_error: null,
    started_at: null,
    stopped_at: null,
    command: ["livekit-server", "--dev"],
    log_tail: [],
    next_actions: [],
    summary: "Local LiveKit dev server is stopped.",
    ...overrides
  };
}

test("live voice start auto-starts only supervised stopped local processes", () => {
  assert.equal(shouldAutoStartVoiceAgentProcess(null), false);
  assert.equal(shouldAutoStartVoiceAgentProcess(processStatus()), true);
  assert.equal(
    shouldAutoStartVoiceAgentProcess(processStatus({ running: true, status: "running" })),
    false
  );
  assert.equal(
    shouldAutoStartVoiceAgentProcess(processStatus({ running: false, status: "starting" })),
    false
  );
  assert.equal(
    shouldAutoStartVoiceAgentProcess(processStatus({ running: false, status: "started" })),
    false
  );
  assert.equal(
    shouldAutoStartVoiceAgentProcess(processStatus({ enabled: false, status: "disabled" })),
    false
  );
  assert.equal(
    shouldAutoStartVoiceAgentProcess(processStatus({ running: false, status: "unknown" })),
    false
  );
});

test("voice process blocker reports failed local starts without blocking external supervision", () => {
  assert.equal(voiceAgentProcessStartBlocker(processStatus({ running: true, status: "running" })), null);
  assert.equal(voiceAgentProcessStartBlocker(processStatus({ running: false, status: "starting" })), null);
  assert.equal(voiceAgentProcessStartBlocker(processStatus({ running: false, status: "started" })), null);
  assert.equal(voiceAgentProcessStartBlocker(processStatus({ enabled: false, status: "disabled" })), null);
  assert.match(
    voiceAgentProcessStartBlocker(
      processStatus({
        status: "failed",
        summary: "Local voice-agent process failed with return code 1."
      })
    ) ?? "",
    /failed/
  );
  assert.match(
    voiceAgentProcessStartBlocker(
      processStatus({
        status: "unknown",
        summary: "Local voice-agent process status is ambiguous."
      })
    ) ?? "",
    /ambiguous/
  );
});

test("local LiveKit process auto-start and blockers mirror local supervisor rules", () => {
  assert.equal(shouldAutoStartLocalLiveKitProcess(null), false);
  assert.equal(shouldAutoStartLocalLiveKitProcess(liveKitProcessStatus()), true);
  assert.equal(
    shouldAutoStartLocalLiveKitProcess(liveKitProcessStatus({ running: true, status: "running" })),
    false
  );
  assert.equal(
    shouldAutoStartLocalLiveKitProcess(liveKitProcessStatus({ enabled: false, status: "disabled" })),
    false
  );
  assert.equal(
    localLiveKitProcessStartBlocker(liveKitProcessStatus({ running: true, status: "running" })),
    null
  );
  assert.match(
    localLiveKitProcessStartBlocker(
      liveKitProcessStatus({
        status: "failed",
        summary: "Local LiveKit dev server failed with return code 1."
      })
    ) ?? "",
    /failed/
  );
});
