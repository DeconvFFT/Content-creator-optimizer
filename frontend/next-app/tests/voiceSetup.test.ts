import assert from "node:assert/strict";
import test from "node:test";

import {
  buildVoiceSetupChecklist,
  isVoiceSetupActionDisabled,
  localLiveKitDevSetupProofMetadata,
  voiceSetupActionForStep,
  voiceSetupActionLabel,
  voiceSetupPrimaryBlocker,
  voiceSetupProofStepPayload,
  voiceSetupReadinessProofStatus
} from "../lib/voice/setup";
import type {
  LocalLiveKitProcessStatusResult,
  RealtimeSessionCreateResult,
  VoiceAgentPresenceResult,
  VoiceAgentProcessStatusResult,
  VoiceRuntimeReadinessResult
} from "../lib/api/types";
import type { VoiceProviderReleaseGate } from "../lib/voice/providerReadiness";

function readiness(status: string): VoiceRuntimeReadinessResult {
  return {
    status,
    selected_provider: "gemma4_realtime",
    transport_framework: "livekit",
    audio_input_model: "google/gemma-4-E4B-it",
    reasoning_model: "google/gemma-4-E4B-it",
    audio_output_model: "hexgrad/Kokoro-82M",
    preflight_edge: true,
    checks: [],
    blockers: status === "blocked" ? ["HF_TOKEN missing"] : [],
    next_actions: status === "blocked" ? ["Set HF_TOKEN"] : [],
    summary: status === "blocked" ? "Runtime blocked." : "Runtime ready."
  };
}

function readinessWithKokoro(metadata: Record<string, unknown>): VoiceRuntimeReadinessResult {
  return {
    ...readiness("ready"),
    preflight_tts: metadata.kokoro_preflight_requested === true,
    checks: [
      {
        check_id: "kokoro-tts",
        label: "Kokoro TTS output",
        status: "ready",
        required: true,
        evidence: ["Hosted Kokoro endpoint is configured."],
        missing_env: [],
        next_actions: [],
        metadata
      }
    ]
  };
}

function readinessWithGemma(metadata: Record<string, unknown>): VoiceRuntimeReadinessResult {
  return {
    ...readiness("ready"),
    preflight_gemma: metadata.gemma_preflight_requested === true,
    checks: [
      {
        check_id: "gemma-audio-reasoning",
        label: "Gemma 4 E4B audio reasoning",
        status: "ready",
        required: true,
        evidence: ["Hugging Face token and dedicated Gemma audio endpoint are configured."],
        missing_env: [],
        next_actions: [],
        metadata
      }
    ]
  };
}

function voiceProcess(
  overrides: Partial<VoiceAgentProcessStatusResult> = {}
): VoiceAgentProcessStatusResult {
  return {
    enabled: true,
    status: "running",
    running: true,
    pid: 123,
    returncode: null,
    last_error: null,
    started_at: null,
    stopped_at: null,
    command: ["python", "-m", "all_about_llms.cli", "run-voice-agent"],
    log_tail: [],
    next_actions: [],
    summary: "Local Gemma/Kokoro agent is running.",
    ...overrides
  };
}

function liveKitProcess(
  overrides: Partial<LocalLiveKitProcessStatusResult> = {}
): LocalLiveKitProcessStatusResult {
  return {
    enabled: true,
    mode: "native",
    status: "running",
    running: true,
    pid: 456,
    returncode: null,
    last_error: null,
    started_at: null,
    stopped_at: null,
    command: ["livekit-server", "--dev"],
    log_tail: [],
    next_actions: [],
    summary: "Local LiveKit transport is running.",
    ...overrides
  };
}

const liveSession: RealtimeSessionCreateResult = {
  run_id: "run-1",
  realtime_session_id: "session-1",
  provider: "gemma4_realtime",
  session_id: "provider-session-1",
  transport: {
    framework: "livekit",
    room_name: "voice-room-1",
    participant_identity: "creator",
    agent_identity: "gemma-kokoro-agent",
    has_token: true
  },
  metadata: {}
};

const readyPresence: VoiceAgentPresenceResult = {
  run_id: "run-1",
  realtime_session_id: "session-1",
  status: "ready",
  observed: true,
  stale: false,
  stale_after_seconds: 60,
  evidence: ["Fresh Gemma/Kokoro participant proof recorded."],
  missing_evidence: [],
  next_actions: [],
  summary: "Fresh Gemma/Kokoro participant proof recorded."
};

function releaseGate(
  checks: VoiceProviderReleaseGate["checks"]
): VoiceProviderReleaseGate {
  const status =
    checks.find((check) => check.status === "blocked")?.status ??
    checks.find((check) => check.status === "needs_runtime")?.status ??
    checks.find((check) => check.status === "needs_live_smoke")?.status ??
    (checks.every((check) => check.status === "ready") ? "ready" : "unknown");
  return {
    status,
    label: "Provider release gate",
    summary: "Provider release gate test fixture.",
    checks,
    missingEnv: [],
    secretFiles: [],
    secretFileGuidance: []
  };
}

test("voice setup checklist identifies the first live voice blocker", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: readiness("blocked"),
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess(),
    liveSession: null,
    liveRoomConnected: false,
    voicePresence: null,
    isRehearsalSession: false
  });

  const blocker = voiceSetupPrimaryBlocker(steps);
  assert.equal(blocker?.label, "Runtime readiness");
  assert.equal(blocker?.status, "blocked");
  assert.equal(blocker?.nextAction, "Set HF_TOKEN");
});

test("voice setup checklist labels OpenRouter agent setup without Gemma copy", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "openrouter_livekit",
    readiness: readiness("ready"),
    voiceProcess: null,
    liveKitProcess: liveKitProcess(),
    liveSession: null,
    liveRoomConnected: true,
    voicePresence: null,
    isRehearsalSession: false
  });

  const agentStep = steps.find((step) => step.label.includes("agent"));
  const presenceStep = steps.find((step) => step.label === "Agent presence");

  assert.equal(agentStep?.label, "OpenRouter/Kokoro agent");
  assert.equal(agentStep?.detail, "Local OpenRouter/Kokoro agent status has not been checked.");
  assert.equal(agentStep?.nextAction, "Start OpenRouter/Kokoro agent");
  assert.equal(voiceSetupActionForStep(agentStep ?? null), "start_agent");
  assert.equal(
    presenceStep?.detail,
    "OpenRouter/Kokoro participant has not been observed."
  );
});

test("voice setup checklist uses OpenRouter runtime fallback copy when readiness is missing", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "openrouter_livekit",
    readiness: null,
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess(),
    liveSession: null,
    liveRoomConnected: false,
    voicePresence: null,
    isRehearsalSession: false
  });

  const runtimeStep = steps.find((step) => step.label === "Runtime readiness");

  assert.match(runtimeStep?.detail ?? "", /OpenRouter/);
  assert.doesNotMatch(runtimeStep?.detail ?? "", /Gemma\/HF/);
});

test("voice setup checklist surfaces concrete runtime check blockers", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: {
      ...readiness("blocked"),
      summary: "Voice runtime is blocked.",
      checks: [
        {
          check_id: "gemma-audio-reasoning",
          label: "Gemma 4 E4B audio reasoning",
          status: "blocked",
          required: true,
          evidence: [
            "HF router chat-completions is configured for text/chat, but it does not satisfy native audio proof."
          ],
          missing_env: ["GEMMA4_MULTIMODAL_ENDPOINT_URL"],
          next_actions: ["Configure a dedicated Gemma multimodal endpoint."],
          metadata: {}
        }
      ],
      next_actions: ["Configure a dedicated Gemma multimodal endpoint."]
    },
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess(),
    liveSession: null,
    liveRoomConnected: false,
    voicePresence: null,
    isRehearsalSession: false
  });

  const runtimeStep = steps.find((step) => step.label === "Runtime readiness");
  assert.equal(
    runtimeStep?.detail,
    "Gemma 4 E4B audio reasoning: HF router chat-completions is configured for text/chat, but it does not satisfy native audio proof."
  );
  assert.equal(runtimeStep?.nextAction, "Configure a dedicated Gemma multimodal endpoint.");
});

test("voice setup checklist requires Gemma endpoint preflight before runtime is ready", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: readinessWithGemma({
      gemma_audio_endpoint_configured: true,
      gemma_preflight_requested: false,
      gemma_preflight_performed: false
    }),
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess(),
    liveSession: null,
    liveRoomConnected: false,
    voicePresence: null,
    isRehearsalSession: false
  });

  const runtimeStep = steps.find((step) => step.label === "Runtime readiness");
  assert.equal(runtimeStep?.status, "pending");
  assert.match(
    runtimeStep?.detail ?? "",
    /Gemma 4 E4B audio endpoint preflight has not run/
  );
  assert.equal(runtimeStep?.nextAction, "Run Runtime preflight.");
});

test("voice setup checklist requires hosted Kokoro synthesis before runtime is ready", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: readinessWithKokoro({
      kokoro_transport: "hf_endpoint",
      kokoro_preflight_requested: false,
      kokoro_preflight_performed: false
    }),
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess(),
    liveSession: null,
    liveRoomConnected: false,
    voicePresence: null,
    isRehearsalSession: false
  });

  const runtimeStep = steps.find((step) => step.label === "Runtime readiness");
  assert.equal(runtimeStep?.status, "pending");
  assert.match(runtimeStep?.detail ?? "", /Kokoro hosted TTS preflight has not run/);
  assert.equal(runtimeStep?.nextAction, "Run Runtime preflight.");
});

test("voice setup checklist maps missing local LiveKit envs to local dev bootstrap", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: {
      ...readiness("blocked"),
      summary: "Voice runtime is blocked.",
      checks: [
        {
          check_id: "livekit-transport",
          label: "LiveKit media transport",
          status: "blocked",
          required: true,
          evidence: ["LiveKit room grants cannot be minted without URL/key/secret."],
          missing_env: [
            "GEMMA4_REALTIME_LIVEKIT_URL",
            "LIVEKIT_API_KEY",
            "LIVEKIT_API_SECRET"
          ],
          next_actions: [
            "Configure GEMMA4_REALTIME_LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET."
          ],
          metadata: {}
        }
      ],
      next_actions: [
        "Configure GEMMA4_REALTIME_LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET."
      ]
    },
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess(),
    liveSession: null,
    liveRoomConnected: false,
    voicePresence: null,
    isRehearsalSession: false
  });

  const blocker = voiceSetupPrimaryBlocker(steps);
  assert.equal(blocker?.label, "Runtime readiness");
  assert.equal(blocker?.nextAction, "Use local LiveKit dev defaults");
  assert.equal(voiceSetupActionForStep(blocker), "configure_local_livekit_dev");
  assert.equal(voiceSetupActionLabel("configure_local_livekit_dev"), "Configure LiveKit dev");
});

test("voice setup checklist maps failed local LiveKit preflight to transport restart", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: {
      ...readiness("blocked"),
      summary: "Voice runtime is blocked.",
      checks: [
        {
          check_id: "livekit-transport",
          label: "LiveKit media transport",
          status: "blocked",
          required: true,
          evidence: ["LiveKit RoomService/ListRooms preflight failed: connection refused."],
          missing_env: [],
          next_actions: [
            "Start or fix the LiveKit server, verify URL/key/secret, then rerun Runtime preflight."
          ],
          metadata: {
            configured_for_local_dev: true,
            connectivity_preflight_performed: true,
            connectivity_error_type: "ConnectError"
          }
        }
      ],
      next_actions: [
        "Start or fix the LiveKit server, verify URL/key/secret, then rerun Runtime preflight."
      ]
    },
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess({ running: true, status: "running" }),
    liveSession: null,
    liveRoomConnected: false,
    voicePresence: null,
    isRehearsalSession: false
  });

  const blocker = voiceSetupPrimaryBlocker(steps);
  assert.equal(blocker?.label, "Runtime readiness");
  assert.equal(blocker?.nextAction, "Restart local LiveKit transport");
  assert.equal(voiceSetupActionForStep(blocker), "restart_livekit");
  assert.equal(voiceSetupActionLabel("restart_livekit"), "Restart LiveKit");
});

test("voice setup checklist does not restart LiveKit for remote preflight failures", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: {
      ...readiness("blocked"),
      summary: "Voice runtime is blocked.",
      checks: [
        {
          check_id: "livekit-transport",
          label: "LiveKit media transport",
          status: "blocked",
          required: true,
          evidence: ["LiveKit RoomService/ListRooms preflight failed with HTTP 503."],
          missing_env: [],
          next_actions: ["Start or fix the LiveKit server, verify URL/key/secret, then rerun Runtime preflight."],
          metadata: {
            configured_for_local_dev: false,
            connectivity_preflight_performed: true,
            connectivity_status_code: 503
          }
        }
      ],
      next_actions: ["Start or fix the LiveKit server, verify URL/key/secret, then rerun Runtime preflight."]
    },
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess({ running: true, status: "running" }),
    liveSession: null,
    liveRoomConnected: false,
    voicePresence: null,
    isRehearsalSession: false
  });

  const blocker = voiceSetupPrimaryBlocker(steps);
  assert.equal(blocker?.label, "Runtime readiness");
  assert.notEqual(blocker?.nextAction, "Restart local LiveKit transport");
  assert.equal(voiceSetupActionForStep(blocker), "run_preflight");
});

test("voice setup checklist does not restart external or stopped LiveKit process states", () => {
  const livekitBlockedReadiness: VoiceRuntimeReadinessResult = {
    ...readiness("blocked"),
    summary: "Voice runtime is blocked.",
    checks: [
      {
        check_id: "livekit-transport",
        label: "LiveKit media transport",
        status: "blocked",
        required: true,
        evidence: ["LiveKit RoomService/ListRooms preflight failed: connection refused."],
        missing_env: [],
        next_actions: ["Start or fix the LiveKit server, verify URL/key/secret, then rerun Runtime preflight."],
        metadata: {
          configured_for_local_dev: true,
          connectivity_preflight_performed: true,
          connectivity_error_type: "ConnectError"
        }
      }
    ],
    next_actions: ["Start or fix the LiveKit server, verify URL/key/secret, then rerun Runtime preflight."]
  };

  const externalSteps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: livekitBlockedReadiness,
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess({ enabled: false, status: "disabled", running: false }),
    liveSession: null,
    liveRoomConnected: false,
    voicePresence: null,
    isRehearsalSession: false
  });
  const externalBlocker = voiceSetupPrimaryBlocker(externalSteps);
  assert.equal(externalBlocker?.label, "Runtime readiness");
  assert.equal(voiceSetupActionForStep(externalBlocker), "run_preflight");

  const stoppedSteps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: livekitBlockedReadiness,
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess({ running: false, status: "stopped" }),
    liveSession: null,
    liveRoomConnected: false,
    voicePresence: null,
    isRehearsalSession: false
  });
  const stoppedBlocker = voiceSetupPrimaryBlocker(stoppedSteps);
  assert.equal(stoppedBlocker?.label, "LiveKit transport");
  assert.equal(voiceSetupActionForStep(stoppedBlocker), "start_livekit");
});

test("voice setup resolver disables local LiveKit bootstrap during local config writes", () => {
  const base = {
    action: "configure_local_livekit_dev" as const,
    readinessLoading: false,
    providerReadinessLoading: false,
    processLoading: false,
    liveKitProcessLoading: false,
    status: "idle"
  };

  assert.equal(
    isVoiceSetupActionDisabled({ ...base, localLiveKitDevConfigBusy: true }),
    true
  );
  assert.equal(
    isVoiceSetupActionDisabled({ ...base, localLiveKitDevConfigBusy: false }),
    false
  );
  assert.equal(
    isVoiceSetupActionDisabled({
      ...base,
      action: "run_preflight",
      localLiveKitDevConfigBusy: true
    }),
    false
  );
});

test("voice setup proof metadata for local LiveKit bootstrap never includes paths or values", () => {
  const metadata = localLiveKitDevSetupProofMetadata({
    status: "ready",
    configured: true,
    configured_env: [
      "GEMMA4_REALTIME_LIVEKIT_URL",
      "LIVEKIT_API_KEY",
      "LIVEKIT_API_SECRET"
    ],
    config_file_env_name: "LOCAL_PROVIDER_CONFIG_FILE",
    secret_file_env_names: ["LIVEKIT_API_KEY_FILE", "LIVEKIT_API_SECRET_FILE"],
    paths: {
      LOCAL_PROVIDER_CONFIG_FILE: ".secrets/local_provider_config.json",
      LIVEKIT_API_KEY_FILE: ".secrets/livekit_api_key",
      LIVEKIT_API_SECRET_FILE: ".secrets/livekit_api_secret"
    },
    detail: "Configured local LiveKit dev transport defaults."
  });

  assert.deepEqual(metadata, {
    configured_env: [
      "GEMMA4_REALTIME_LIVEKIT_URL",
      "LIVEKIT_API_KEY",
      "LIVEKIT_API_SECRET"
    ],
    config_file_env_name: "LOCAL_PROVIDER_CONFIG_FILE",
    secret_file_env_names: ["LIVEKIT_API_KEY_FILE", "LIVEKIT_API_SECRET_FILE"]
  });
  assert.doesNotMatch(JSON.stringify(metadata), /paths|\.secrets|devkey/i);
});

test("voice setup checklist uses polished local start actions", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: readiness("ready"),
    voiceProcess: voiceProcess({ running: false, status: "stopped" }),
    liveKitProcess: liveKitProcess({ running: false, status: "stopped" }),
    liveSession: null,
    liveRoomConnected: false,
    voicePresence: null,
    isRehearsalSession: false
  });

  assert.equal(
    steps.find((step) => step.label === "LiveKit transport")?.nextAction,
    "Start LiveKit transport"
  );
  assert.equal(
    steps.find((step) => step.label === "Gemma/Kokoro agent")?.nextAction,
    "Start Gemma/Kokoro agent"
  );
  assert.equal(
    voiceSetupActionForStep(steps.find((step) => step.label === "LiveKit transport") ?? null),
    "start_livekit"
  );
  assert.equal(voiceSetupActionLabel("start_livekit"), "Start LiveKit");
});

test("voice setup checklist requires room and participant proof after runtime is ready", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: readiness("ready"),
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess(),
    liveSession: null,
    liveRoomConnected: false,
    voicePresence: null,
    isRehearsalSession: false
  });

  assert.equal(voiceSetupPrimaryBlocker(steps)?.label, "LiveKit room");
  assert.equal(voiceSetupActionForStep(voiceSetupPrimaryBlocker(steps)), "join_room");

  const readySteps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: readiness("ready"),
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess(),
    liveSession,
    liveRoomConnected: true,
    voicePresence: readyPresence,
    isRehearsalSession: false
  });
  assert.equal(voiceSetupPrimaryBlocker(readySteps), null);
  assert.equal(voiceSetupActionForStep(voiceSetupPrimaryBlocker(readySteps)), null);
});

test("voice setup checklist blocks ready rooms on unresolved provider failure recovery", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: readiness("ready"),
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess(),
    liveSession,
    liveRoomConnected: true,
    voicePresence: readyPresence,
    isRehearsalSession: false,
    providerReleaseGate: releaseGate([
      {
        id: "provider-recovery",
        label: "Provider failure recovery",
        status: "blocked",
        detail: "Latest provider failure recovery is still blocking live voice readiness.",
        nextAction: "Run recovery checks, speak in the active room, then rerun live Runtime smoke."
      },
      {
        id: "live-smoke",
        label: "Live Gemma/Kokoro smoke",
        status: "ready",
        detail: "Provider-backed Gemma/Kokoro voice streaming smoke passed."
      }
    ])
  });

  const blocker = voiceSetupPrimaryBlocker(steps);
  assert.equal(blocker?.label, "Provider failure recovery");
  assert.equal(blocker?.status, "blocked");
  assert.equal(voiceSetupActionForStep(blocker), "run_live_smoke");
  assert.equal(voiceSetupActionLabel("run_live_smoke"), "Run live smoke");
});

test("voice setup checklist preserves provider configuration recovery label and action", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: readiness("ready"),
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess(),
    liveSession,
    liveRoomConnected: true,
    voicePresence: readyPresence,
    isRehearsalSession: false,
    providerReleaseGate: releaseGate([
      {
        id: "provider-recovery",
        label: "Provider configuration recovery",
        status: "blocked",
        detail:
          "Latest provider configuration recovery is still blocking 2 provider-smoke configuration step(s).",
        nextAction:
          "Rerun live Runtime smoke after provider configuration is repaired."
      },
      {
        id: "live-smoke",
        label: "Live Gemma/Kokoro smoke",
        status: "ready",
        detail: "Provider-backed Gemma/Kokoro voice streaming smoke passed."
      }
    ])
  });

  const blocker = voiceSetupPrimaryBlocker(steps);
  assert.equal(blocker?.label, "Provider configuration recovery");
  assert.equal(blocker?.status, "blocked");
  assert.equal(
    blocker?.detail,
    "Latest provider configuration recovery is still blocking 2 provider-smoke configuration step(s)."
  );
  assert.equal(voiceSetupActionForStep(blocker), "run_live_smoke");
});

test("voice setup checklist treats degraded non-required runtime checks as usable", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: {
      ...readiness("degraded"),
      summary: "Voice runtime is usable but direct event persistence is degraded."
    },
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess(),
    liveSession,
    liveRoomConnected: true,
    voicePresence: readyPresence,
    isRehearsalSession: false,
    providerReleaseGate: releaseGate([
      {
        id: "selected-provider",
        label: "Selected provider",
        status: "ready",
        detail: "Selected provider checks are ready."
      },
      {
        id: "live-smoke",
        label: "Live smoke",
        status: "ready",
        detail: "Live smoke is ready."
      }
    ])
  });

  assert.equal(
    steps.find((step) => step.label === "Runtime readiness")?.status,
    "ready"
  );
  assert.equal(voiceSetupPrimaryBlocker(steps), null);
});

test("voice setup checklist requires live smoke proof before claiming provider-backed readiness", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: readiness("ready"),
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess(),
    liveSession,
    liveRoomConnected: true,
    voicePresence: readyPresence,
    isRehearsalSession: false,
    providerReleaseGate: releaseGate([
      {
        id: "provider-recovery",
        label: "Provider failure recovery",
        status: "ready",
        detail: "A newer provider-backed smoke ledger supersedes the last provider failure."
      },
      {
        id: "live-smoke",
        label: "Live Gemma/Kokoro smoke",
        status: "needs_live_smoke",
        detail: "No provider smoke ledger has been built for this run.",
        nextAction: "Join the room, speak once, enable Live smoke, then run Runtime smoke."
      }
    ])
  });

  const blocker = voiceSetupPrimaryBlocker(steps);
  assert.equal(blocker?.label, "Live smoke proof");
  assert.equal(blocker?.status, "pending");
  assert.equal(voiceSetupActionForStep(blocker), "run_live_smoke");
});

test("voice setup checklist surfaces selected-provider release blockers", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: readiness("ready"),
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess(),
    liveSession,
    liveRoomConnected: true,
    voicePresence: readyPresence,
    isRehearsalSession: false,
    providerReleaseGate: releaseGate([
      {
        id: "gemma-primary",
        label: "Gemma expert endpoint",
        status: "blocked",
        detail: "Gemma 4 HF endpoint is missing HF_TOKEN_FILE.",
        nextAction: "Configure HF_TOKEN_FILE and refresh provider readiness."
      },
      {
        id: "provider-recovery",
        label: "Provider failure recovery",
        status: "ready",
        detail: "A newer provider-backed smoke ledger supersedes the last provider failure."
      },
      {
        id: "live-smoke",
        label: "Live Gemma/Kokoro smoke",
        status: "ready",
        detail: "Provider-backed Gemma/Kokoro voice streaming smoke passed."
      }
    ])
  });

  const blocker = voiceSetupPrimaryBlocker(steps);
  assert.equal(blocker?.label, "Provider release gate: Gemma expert endpoint");
  assert.equal(blocker?.status, "blocked");
  assert.equal(voiceSetupActionForStep(blocker), "refresh_provider_readiness");
  assert.equal(voiceSetupActionLabel("refresh_provider_readiness"), "Refresh providers");
});

test("voice setup checklist stays ready when provider release proof is ready", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: readiness("ready"),
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess(),
    liveSession,
    liveRoomConnected: true,
    voicePresence: readyPresence,
    isRehearsalSession: false,
    providerReleaseGate: releaseGate([
      {
        id: "provider-recovery",
        label: "Provider failure recovery",
        status: "ready",
        detail: "A newer provider-backed smoke ledger supersedes the last provider failure."
      },
      {
        id: "live-smoke",
        label: "Live Gemma/Kokoro smoke",
        status: "ready",
        detail: "Provider-backed Gemma/Kokoro voice streaming smoke passed."
      }
    ])
  });

  assert.equal(voiceSetupPrimaryBlocker(steps), null);
  assert.equal(voiceSetupActionForStep(voiceSetupPrimaryBlocker(steps)), null);
});

test("voice setup checklist separates transcript rehearsal from provider-backed audio", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "local_rehearsal",
    readiness: null,
    voiceProcess: null,
    liveKitProcess: null,
    liveSession,
    liveRoomConnected: false,
    voicePresence: null,
    isRehearsalSession: true
  });

  assert.equal(voiceSetupPrimaryBlocker(steps), null);
  assert.deepEqual(
    steps.filter((step) => step.status === "not_applicable").map((step) => step.label),
    ["LiveKit transport", "Gemma/Kokoro agent"]
  );
});

test("voice setup checklist maps participant presence to a probe action", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: readiness("ready"),
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess(),
    liveSession,
    liveRoomConnected: true,
    voicePresence: {
      ...readyPresence,
      status: "missing",
      observed: false,
      summary: "Gemma/Kokoro participant has not been observed.",
      evidence: [],
      missing_evidence: ["No durable ready event."]
    },
    isRehearsalSession: false
  });

  const blocker = voiceSetupPrimaryBlocker(steps);
  assert.equal(blocker?.label, "Agent presence");
  assert.equal(voiceSetupActionForStep(blocker), "probe_presence");
  assert.equal(voiceSetupActionLabel("probe_presence"), "Probe presence");
});

test("voice setup proof payload preserves blocker details for durable events", () => {
  const steps = buildVoiceSetupChecklist({
    runId: "run-1",
    provider: "gemma4_realtime",
    readiness: readiness("ready"),
    voiceProcess: voiceProcess(),
    liveKitProcess: liveKitProcess(),
    liveSession: null,
    liveRoomConnected: false,
    voicePresence: null,
    isRehearsalSession: false
  });

  const blocker = voiceSetupPrimaryBlocker(steps);
  assert.equal(blocker?.label, "LiveKit room");
  assert.deepEqual(blocker ? voiceSetupProofStepPayload(blocker) : null, {
    id: "LiveKit room",
    label: "LiveKit room",
    status: "pending",
    detail: "No active provider-backed room is joined.",
    next_action: "Join voice room",
    required: true
  });
});

test("voice setup readiness proof status follows refreshed preflight state", () => {
  assert.equal(voiceSetupReadinessProofStatus("ready"), "ready");
  assert.equal(voiceSetupReadinessProofStatus("blocked"), "blocked");
  assert.equal(voiceSetupReadinessProofStatus("failed"), "failed");
  assert.equal(voiceSetupReadinessProofStatus("degraded"), "ready");
  assert.equal(voiceSetupReadinessProofStatus(null), "pending");
});
