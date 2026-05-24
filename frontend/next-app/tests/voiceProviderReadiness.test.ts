import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import {
  buildVoiceProviderReleaseGate,
  providerSmokeArtifactFromResult
} from "../lib/voice/providerReadiness";
import {
  LIVEKIT_TRANSPORT_PREFLIGHT_OPTIONS,
  RUNTIME_PREFLIGHT_READINESS_OPTIONS,
  shouldApplyVoiceReadinessResult,
  voiceReadinessRefreshStrength
} from "../lib/voice/runtimeReadiness";
import { startKeyedSingleFlight } from "../lib/voice/keyedSingleFlight";
import { settleVoiceSetupFanout } from "../lib/voice/setupFanout";
import type {
  ArtifactRecord,
  ProviderReadinessItem,
  ProviderReadinessResult,
  ProviderSmokeRunResult,
  VoiceAgentPresenceResult,
  VoiceRuntimeReadinessResult
} from "../lib/api/types";

function artifact(overrides: Partial<ArtifactRecord>): ArtifactRecord {
  return {
    artifact_id: overrides.artifact_id ?? "artifact-1",
    run_id: overrides.run_id ?? "run-1",
    artifact_type: overrides.artifact_type ?? "provider_operations_ledger",
    title: overrides.title ?? "Artifact",
    uri: overrides.uri ?? "artifact://runs/run-1/artifact-1",
    content: overrides.content ?? {},
    provenance: overrides.provenance ?? {},
    source_ids: overrides.source_ids ?? [],
    reviewer_decisions: overrides.reviewer_decisions ?? [],
    revision_history: overrides.revision_history ?? [],
    created_at: overrides.created_at ?? "2026-05-18T12:00:00Z"
  };
}

function provider(
  overrides: Partial<ProviderReadinessItem> & Pick<ProviderReadinessItem, "provider_id" | "provider_type">
): ProviderReadinessItem {
  return {
    provider_id: overrides.provider_id,
    provider_type: overrides.provider_type,
    display_name: overrides.display_name ?? overrides.provider_id,
    status: overrides.status ?? "ready",
    selected: overrides.selected ?? false,
    required_env: overrides.required_env ?? [],
    configured_env: overrides.configured_env ?? [],
    missing_env: overrides.missing_env ?? [],
    model_ids: overrides.model_ids ?? [],
    endpoint_configured: overrides.endpoint_configured ?? true,
    capabilities: overrides.capabilities ?? [],
    boundary: overrides.boundary ?? "Provider boundary.",
    notes: overrides.notes ?? "Provider notes.",
    documentation_url: overrides.documentation_url ?? null,
    next_actions: overrides.next_actions ?? [],
    secret_files: overrides.secret_files ?? []
  };
}

function readiness(overrides: Partial<ProviderReadinessResult> = {}): ProviderReadinessResult {
  const providers = overrides.providers ?? [
    provider({ provider_id: "gemma4-primary", provider_type: "gemma4_hf_endpoint" }),
    provider({
      provider_id: "gemma4-realtime",
      provider_type: "realtime_audio",
      selected: true
    }),
    provider({
      provider_id: "tavily-search",
      provider_type: "web_search",
      selected: true
    }),
    provider({
      provider_id: "deterministic-reranker",
      provider_type: "reranker",
      selected: true
    })
  ];
  return {
    default_realtime_provider: "gemma4_realtime",
    selected_web_search_provider: "tavily",
    providers,
    ready_provider_ids: providers
      .filter((item) => item.status === "ready")
      .map((item) => item.provider_id),
    missing_provider_ids: providers
      .filter((item) => item.status === "missing_config")
      .map((item) => item.provider_id),
    tool_boundary_provider_ids: [],
    missing_required_env: providers.flatMap((item) => item.missing_env),
    provider_backed_smoke_ready: providers.every((item) => item.status === "ready"),
    smoke_test_plan: [],
    demo_walkthrough: [],
    summary: "Provider readiness summary.",
    ...overrides
  };
}

const runtimeReady: VoiceRuntimeReadinessResult = {
  status: "ready",
  selected_provider: "gemma4_realtime",
  transport_framework: "livekit",
  audio_input_model: "google/gemma-4-E4B-it",
  reasoning_model: "google/gemma-4-E4B-it",
  audio_output_model: "hexgrad/Kokoro-82M",
  preflight_edge: true,
  preflight_agent: true,
  preflight_livekit: true,
  checks: [],
  blockers: [],
  next_actions: [],
  summary: "Voice runtime readiness checks are ready."
};

function runtimeWithKokoro(metadata: Record<string, unknown>): VoiceRuntimeReadinessResult {
  return {
    ...runtimeReady,
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

function runtimeWithGemma(metadata: Record<string, unknown>): VoiceRuntimeReadinessResult {
  return {
    ...runtimeReady,
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

const presenceReady: VoiceAgentPresenceResult = {
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

const liveSmokePassed: ProviderSmokeRunResult = {
  run_id: "run-1",
  status: "passed",
  execute_live_calls: true,
  provider_readiness: readiness(),
  step_count: 1,
  passed_count: 1,
  blocked_count: 0,
  failed_count: 0,
  not_run_count: 0,
  tool_boundary_count: 0,
  source_ids: [],
  realtime_session_ids: ["session-1"],
  provider_configuration_followup_message_ids: [],
  steps: [
    {
      step_id: "gemma-kokoro-voice-streaming-smoke",
      provider_id: "gemma4-realtime",
      provider_type: "realtime_audio",
      title: "Gemma Kokoro voice streaming",
      status: "passed",
      required: true,
      live_call: true,
      smoke_proof_status: "provider_backed",
      evidence: ["Gemma TTFT and Kokoro first-audio measured."],
      blockers: [],
      next_actions: [],
      source_ids: [],
      realtime_session_ids: ["session-1"],
      event_ids: [],
      details: {}
    }
  ],
  summary: "Provider smoke passed."
};

test("provider release gate blocks missing selected provider configuration", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness({
      providers: [
        provider({ provider_id: "gemma4-primary", provider_type: "gemma4_hf_endpoint" }),
        provider({
          provider_id: "gemma4-realtime",
          provider_type: "realtime_audio",
          selected: true,
          status: "missing_config",
          missing_env: ["LIVEKIT_API_SECRET"],
          next_actions: ["Set LIVEKIT_API_SECRET in .env."]
        }),
        provider({
          provider_id: "tavily-search",
          provider_type: "web_search",
          selected: true
        }),
        provider({
          provider_id: "deterministic-reranker",
          provider_type: "reranker",
          selected: true
        }),
        provider({
          provider_id: "openai-realtime",
          provider_type: "realtime_audio",
          selected: false,
          status: "missing_config",
          missing_env: ["OPENAI_API_KEY"]
        })
      ]
    }),
    runtimeReadiness: runtimeReady,
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1"
  });

  assert.equal(gate.status, "blocked");
  assert.match(gate.summary, /Set LIVEKIT_API_SECRET/);
  assert.deepEqual(gate.missingEnv, ["LIVEKIT_API_SECRET"]);
});

test("provider release gate prefers local LiveKit dev bootstrap for fully missing local transport config", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness({
      providers: [
        provider({ provider_id: "gemma4-primary", provider_type: "gemma4_hf_endpoint" }),
        provider({
          provider_id: "gemma4-realtime",
          provider_type: "realtime_audio",
          selected: true,
          status: "missing_config",
          missing_env: [
            "GEMMA4_REALTIME_LIVEKIT_URL",
            "LIVEKIT_API_KEY",
            "LIVEKIT_API_SECRET"
          ],
          next_actions: [
            "Configure GEMMA4_REALTIME_LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET."
          ]
        }),
        provider({
          provider_id: "tavily-search",
          provider_type: "web_search",
          selected: true
        }),
        provider({
          provider_id: "deterministic-reranker",
          provider_type: "reranker",
          selected: true
        })
      ]
    }),
    runtimeReadiness: runtimeReady,
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1"
  });

  const realtimeCheck = gate.checks.find((check) => check.id === "realtime-provider");
  assert.equal(realtimeCheck?.status, "blocked");
  assert.equal(realtimeCheck?.nextAction, "Use local LiveKit dev defaults");
  assert.match(gate.summary, /Use local LiveKit dev defaults/);
});

test("provider release gate exposes selected secret-file diagnostics only", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness({
      providers: [
        provider({
          provider_id: "gemma4-primary",
          provider_type: "gemma4_hf_endpoint",
          secret_files: [
            {
              env_name: "HF_TOKEN",
              file_env_name: "HF_TOKEN_FILE",
              status: "missing",
              configured: false,
              path: ".secrets/hf_token",
              detail: "HF_TOKEN_FILE points to a missing file."
            }
          ]
        }),
        provider({
          provider_id: "gemma4-realtime",
          provider_type: "realtime_audio",
          selected: true
        }),
        provider({
          provider_id: "tavily-search",
          provider_type: "web_search",
          selected: true,
          secret_files: [
            {
              env_name: "TAVILY_API_KEY",
              file_env_name: "TAVILY_API_KEY_FILE",
              status: "loaded",
              configured: true,
              path: ".secrets/tavily_api_key",
              detail: "TAVILY_API_KEY_FILE is configured with a readable non-empty file."
            }
          ]
        }),
        provider({
          provider_id: "deterministic-reranker",
          provider_type: "reranker",
          selected: true
        }),
        provider({
          provider_id: "openai-realtime",
          provider_type: "realtime_audio",
          selected: false,
          secret_files: [
            {
              env_name: "OPENAI_API_KEY",
              file_env_name: "OPENAI_API_KEY_FILE",
              status: "missing",
              configured: false,
              path: ".secrets/openai",
              detail: "Inactive provider secret file."
            }
          ]
        })
      ]
    }),
    runtimeReadiness: runtimeReady,
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1"
  });

  assert.deepEqual(
    gate.secretFiles.map((item) => item.file_env_name),
    ["HF_TOKEN_FILE", "TAVILY_API_KEY_FILE"]
  );
});

test("provider release gate builds non-secret setup guidance for selected secret files", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness({
      providers: [
        provider({
          provider_id: "gemma4-primary",
          provider_type: "gemma4_hf_endpoint",
          secret_files: [
            {
              env_name: "HF_TOKEN",
              file_env_name: "HF_TOKEN_FILE",
              status: "missing",
              configured: false,
              path: ".secrets/hf_token",
              detail: "HF_TOKEN_FILE points to a missing file."
            }
          ]
        }),
        provider({
          provider_id: "gemma4-realtime",
          provider_type: "realtime_audio",
          selected: true
        }),
        provider({
          provider_id: "tavily-search",
          provider_type: "web_search",
          selected: true,
          secret_files: [
            {
              env_name: "TAVILY_API_KEY",
              file_env_name: "TAVILY_API_KEY_FILE",
              status: "loaded",
              configured: true,
              path: ".secrets/tavily_api_key",
              detail: "TAVILY_API_KEY_FILE is configured with a readable non-empty file."
            }
          ]
        }),
        provider({
          provider_id: "deterministic-reranker",
          provider_type: "reranker",
          selected: true
        })
      ]
    }),
    runtimeReadiness: runtimeReady,
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1"
  });

  assert.deepEqual(
    gate.secretFileGuidance.map((item) => ({
      fileEnvName: item.fileEnvName,
      configured: item.configured,
      action: item.action
    })),
    [
      {
        fileEnvName: "HF_TOKEN_FILE",
        configured: false,
        action: "Create .secrets/hf_token with the HF_TOKEN value, or set HF_TOKEN directly for this process."
      },
      {
        fileEnvName: "TAVILY_API_KEY_FILE",
        configured: true,
        action: "Ready from .secrets/tavily_api_key."
      }
    ]
  );
});

test("voice panel provides local secret-file save controls without exposing values", () => {
  const panelSource = readFileSync(
    join(process.cwd(), "components/voice/RealtimeVoicePanel.tsx"),
    "utf8"
  );
  const clientSource = readFileSync(join(process.cwd(), "lib/api/client.ts"), "utf8");
  const typesSource = readFileSync(join(process.cwd(), "lib/api/types.ts"), "utf8");

  assert.match(clientSource, /saveLocalSecretFile/);
  assert.match(clientSource, /saveLocalProviderConfig/);
  assert.match(clientSource, /configureLocalLiveKitDevConfig/);
  assert.match(clientSource, /local-livekit-dev-config/);
  assert.match(clientSource, /preflightTts/);
  assert.match(clientSource, /preflight_tts/);
  assert.match(typesSource, /LocalSecretFileWriteResult/);
  assert.match(typesSource, /LocalProviderConfigWriteResult/);
  assert.match(typesSource, /LocalLiveKitDevConfigResult/);
  assert.match(typesSource, /preflight_tts/);
  assert.match(typesSource, /GEMMA4_MULTIMODAL_ENDPOINT_URL/);
  assert.match(typesSource, /GEMMA4_REALTIME_LIVEKIT_URL/);
  assert.match(typesSource, /KOKORO_TTS_ENDPOINT_URL/);
  assert.match(typesSource, /LIVEKIT_API_KEY/);
  assert.match(typesSource, /LIVEKIT_API_SECRET/);
  assert.match(panelSource, /handleSaveLocalSecretFile/);
  assert.match(panelSource, /handleSaveLocalProviderConfig/);
  assert.match(panelSource, /handleConfigureLocalLiveKitDev/);
  const secretFileHandler =
    panelSource.match(/const handleSaveLocalSecretFile = useCallback\([\s\S]*?\n  \);/)?.[0] ?? "";
  const providerConfigHandler =
    panelSource.match(/const handleSaveLocalProviderConfig = useCallback\([\s\S]*?\n  \);/)?.[0] ?? "";
  const localLiveKitDevHandler =
    panelSource.match(/const handleConfigureLocalLiveKitDev = useCallback[\s\S]*?\n  }, \[/)?.[0] ?? "";
  assert.match(panelSource, /type="password"/);
  assert.match(panelSource, /Save locally/);
  assert.match(panelSource, /Save endpoint/);
  assert.match(panelSource, /Use local LiveKit dev defaults/);
  assert.match(panelSource, /configure_local_livekit_dev/);
  assert.match(panelSource, /restart_livekit/);
  assert.match(panelSource, /forceRestart: true/);
  assert.match(panelSource, /Voice setup resolver configured local LiveKit dev defaults/);
  assert.match(panelSource, /isVoiceSetupActionDisabled/);
  assert.match(panelSource, /type LocalLiveKitDevConfigAttempt/);
  assert.match(panelSource, /localLiveKitDevSetupProofMetadata\(configResult\)/);
  assert.match(panelSource, /localLiveKitDevConfigNeeded/);
  assert.match(panelSource, /localLiveKitDevConfigBusy/);
  assert.match(panelSource, /disabled={localLiveKitDevConfigBusy}/);
  assert.match(panelSource, /localLiveKitDevConfigSaving \\|\\| secretSaving/);
  assert.match(panelSource, /localLiveKitDevConfigSaving \\|\\| providerConfigSaving/);
  assert.match(panelSource, /providerConfigSaving !== null/);
  assert.match(panelSource, /secretValue/);
  assert.match(panelSource, /providerConfigValue/);
  assert.match(panelSource, /LIVEKIT_API_KEY/);
  assert.match(panelSource, /LIVEKIT_API_SECRET/);
  assert.match(panelSource, /GEMMA4_MULTIMODAL_ENDPOINT_URL/);
  assert.match(panelSource, /GEMMA4_REALTIME_LIVEKIT_URL/);
  assert.match(panelSource, /KOKORO_TTS_ENDPOINT_URL/);
  assert.match(panelSource, /Only supported local provider secrets/);
  assert.doesNotMatch(panelSource, /Only HF_TOKEN and TAVILY_API_KEY can be saved/);
  assert.doesNotMatch(panelSource, /secret-hf-token-local-setup/);
  assert.match(secretFileHandler, /secretFileSaveSequenceRef/);
  assert.match(secretFileHandler, /secretFileSaveInFlightRef/);
  assert.match(secretFileHandler, /onVoiceProofMutationStart\?\.\("Saving local secret file"\)/);
  assert.match(secretFileHandler, /isCurrentSecretFileSave/);
  assert.match(secretFileHandler, /saveLocalSecretFile/);
  assert.match(secretFileHandler, /refreshProviderReadiness\(\{ shouldApply: isCurrentSecretFileSave \}\)/);
  assert.match(secretFileHandler, /onVoiceProofMutationFinish\?\.\(parentMutationSnapshot\)/);
  const secretFileParentGate = secretFileHandler.indexOf(
    'onVoiceProofMutationStart?.("Saving local secret file")'
  );
  const secretFileSaveCall = secretFileHandler.indexOf("saveLocalSecretFile");
  const secretFileSaveFailure = secretFileHandler.indexOf('label: "Secret file save failed"');
  const secretFileSaveFailureReturn = secretFileHandler.indexOf("return;", secretFileSaveFailure);
  const secretFileSuccessEvent = secretFileHandler.indexOf('label: "Secret file saved"');
  const secretFileRefresh = secretFileHandler.indexOf(
    "refreshProviderReadiness({ shouldApply: isCurrentSecretFileSave })"
  );
  const secretFileParentFinish = secretFileHandler.indexOf(
    "onVoiceProofMutationFinish?.(parentMutationSnapshot)"
  );

  assert.notEqual(secretFileParentGate, -1);
  assert.notEqual(secretFileSaveCall, -1);
  assert.notEqual(secretFileSaveFailure, -1);
  assert.notEqual(secretFileSaveFailureReturn, -1);
  assert.notEqual(secretFileSuccessEvent, -1);
  assert.notEqual(secretFileRefresh, -1);
  assert.notEqual(secretFileParentFinish, -1);
  assert.ok(secretFileParentGate < secretFileSaveCall);
  assert.ok(secretFileSaveCall < secretFileSaveFailure);
  assert.ok(secretFileSaveFailure < secretFileSaveFailureReturn);
  assert.ok(secretFileSaveFailureReturn < secretFileSuccessEvent);
  assert.ok(secretFileSuccessEvent < secretFileRefresh);
  assert.ok(secretFileRefresh < secretFileParentFinish);
  assert.match(providerConfigHandler, /providerConfigSaveSequenceRef/);
  assert.match(providerConfigHandler, /providerConfigSaveInFlightRef/);
  assert.match(providerConfigHandler, /onVoiceProofMutationStart\?\.\("Saving provider endpoint"\)/);
  assert.match(providerConfigHandler, /isCurrentProviderConfigSave/);
  assert.match(providerConfigHandler, /saveLocalProviderConfig/);
  assert.match(providerConfigHandler, /Promise\.allSettled/);
  assert.match(providerConfigHandler, /refreshProviderReadiness\(\{ shouldApply: isCurrentProviderConfigSave \}\)/);
  assert.match(providerConfigHandler, /refreshVoiceReadiness\(\{ shouldApply: isCurrentProviderConfigSave \}\)/);
  assert.match(providerConfigHandler, /onVoiceProofMutationFinish\?\.\(parentMutationSnapshot\)/);
  const providerConfigParentGate = providerConfigHandler.indexOf(
    'onVoiceProofMutationStart?.("Saving provider endpoint")'
  );
  const providerConfigSaveCall = providerConfigHandler.indexOf("saveLocalProviderConfig");
  const providerConfigAllSettled = providerConfigHandler.indexOf("Promise.allSettled");
  const providerConfigParentFinish = providerConfigHandler.indexOf(
    "onVoiceProofMutationFinish?.(parentMutationSnapshot)"
  );

  assert.notEqual(providerConfigParentGate, -1);
  assert.notEqual(providerConfigSaveCall, -1);
  assert.notEqual(providerConfigAllSettled, -1);
  assert.notEqual(providerConfigParentFinish, -1);
  assert.ok(providerConfigParentGate < providerConfigSaveCall);
  assert.ok(providerConfigSaveCall < providerConfigAllSettled);
  assert.ok(providerConfigAllSettled < providerConfigParentFinish);
  assert.match(
    localLiveKitDevHandler,
    /onVoiceProofMutationStart\?\.\("Configuring local LiveKit dev defaults"\)/
  );
  assert.match(localLiveKitDevHandler, /localLiveKitDevConfigSequenceRef/);
  assert.match(localLiveKitDevHandler, /localLiveKitDevConfigInFlightRef/);
  assert.match(localLiveKitDevHandler, /status: "skipped"/);
  assert.match(localLiveKitDevHandler, /skipParentMutation/);
  assert.match(localLiveKitDevHandler, /isCurrentLocalLiveKitDevConfig/);
  assert.match(localLiveKitDevHandler, /configureLocalLiveKitDevConfig\(\)/);
  assert.match(localLiveKitDevHandler, /Promise\.allSettled/);
  assert.match(localLiveKitDevHandler, /refreshProviderReadiness\(\{ shouldApply: isCurrentLocalLiveKitDevConfig \}\)/);
  assert.match(localLiveKitDevHandler, /refreshVoiceReadiness\(\{ shouldApply: isCurrentLocalLiveKitDevConfig \}\)/);
  assert.match(localLiveKitDevHandler, /onVoiceProofMutationFinish\?\.\(parentMutationSnapshot\)/);
  const localLiveKitParentGate = localLiveKitDevHandler.indexOf(
    'onVoiceProofMutationStart?.("Configuring local LiveKit dev defaults")'
  );
  const localLiveKitSaveCall = localLiveKitDevHandler.indexOf("configureLocalLiveKitDevConfig()");
  const localLiveKitAllSettled = localLiveKitDevHandler.indexOf("Promise.allSettled");
  const localLiveKitParentFinish = localLiveKitDevHandler.indexOf(
    "onVoiceProofMutationFinish?.(parentMutationSnapshot)"
  );

  assert.notEqual(localLiveKitParentGate, -1);
  assert.notEqual(localLiveKitSaveCall, -1);
  assert.notEqual(localLiveKitAllSettled, -1);
  assert.notEqual(localLiveKitParentFinish, -1);
  assert.ok(localLiveKitParentGate < localLiveKitSaveCall);
  assert.ok(localLiveKitSaveCall < localLiveKitAllSettled);
  assert.ok(localLiveKitAllSettled < localLiveKitParentFinish);
  const localSaveHelper = panelSource.match(/function secretFileNeedsLocalValue[\s\S]*?\n}/)?.[0] ?? "";
  assert.match(localSaveHelper, /missing/);
  assert.match(localSaveHelper, /empty/);
  assert.match(localSaveHelper, /unreadable/);
  assert.doesNotMatch(localSaveHelper, /not_configured/);
});

test("voice panel uses named runtime-readiness refresh options", () => {
  const panelSource = readFileSync(
    join(process.cwd(), "components/voice/RealtimeVoicePanel.tsx"),
    "utf8"
  );
  const runtimeSource = readFileSync(
    join(process.cwd(), "lib/voice/runtimeReadiness.ts"),
    "utf8"
  );

  assert.deepEqual(RUNTIME_PREFLIGHT_READINESS_OPTIONS, {
    preflightEdge: true,
    preflightAgent: true,
    preflightLivekit: true,
    preflightTts: true,
    preflightGemma: true
  });
  assert.deepEqual(LIVEKIT_TRANSPORT_PREFLIGHT_OPTIONS, {
    preflightLivekit: true
  });
  assert.match(runtimeSource, /shouldApply\?: \(\) => boolean;/);
  assert.match(panelSource, /RUNTIME_PREFLIGHT_READINESS_OPTIONS/);
  assert.match(panelSource, /refreshVoiceReadiness\(LIVEKIT_TRANSPORT_PREFLIGHT_OPTIONS\)/);
  assert.match(panelSource, /refreshVoiceReadiness\(\)/);
  assert.match(panelSource, /readinessRefreshInFlightRef/);
  assert.match(panelSource, /startKeyedSingleFlight/);
  assert.match(panelSource, /Map<string, Promise<VoiceRuntimeReadinessResult>>/);
  assert.match(panelSource, /readinessAppliedStateRef/);
  assert.match(panelSource, /bumpReadinessEpoch/);
  assert.match(panelSource, /requestEpoch,\s*\n\s*preflightEdge/);
  assert.match(panelSource, /shouldApplyVoiceReadinessResult/);
  assert.match(panelSource, /const shouldApplyReadiness = options\.shouldApply\?\.\(\) \?\? true;/);
  assert.match(panelSource, /type ProviderReadinessRefreshOptions = {\n\s+shouldApply\?: \(\) => boolean;/);
  assert.match(panelSource, /const shouldApplyProviderReadiness = options\.shouldApply\?\.\(\) \?\? true;/);
  assert.match(panelSource, /setupCheckInFlightRef/);
  assert.match(panelSource, /setupCheckLoading \|\| voiceSetupActionLoading \|\| isVoiceSetupActionDisabled/);
  assert.match(panelSource, /liveVoiceProofPathActionLoading \|\|\n\s+!runId/);
  assert.match(panelSource, /settleVoiceSetupFanout/);
  const setupHandlerStart = panelSource.indexOf("async function handleSetupCheck");
  const setupHandlerEnd = panelSource.indexOf("async function handleResolveVoiceSetup", setupHandlerStart);
  const setupHandlerSource = panelSource.slice(setupHandlerStart, setupHandlerEnd);
  const resolveHandlerStart = panelSource.indexOf("async function handleResolveVoiceSetup");
  const resolveHandlerEnd = panelSource.indexOf("async function handleLiveVoiceProofPathAction", resolveHandlerStart);
  const resolveHandlerSource = panelSource.slice(resolveHandlerStart, resolveHandlerEnd);
  const liveProofHandlerStart = panelSource.indexOf("async function handleLiveVoiceProofPathAction");
  const liveProofHandlerEnd = panelSource.indexOf("async function handleStart", liveProofHandlerStart);
  const liveProofHandlerSource = panelSource.slice(liveProofHandlerStart, liveProofHandlerEnd);
  const runtimePreflightHandlerStart = panelSource.indexOf("async function handleRuntimePreflight");
  const runtimePreflightHandlerEnd = panelSource.indexOf("const handleSaveLocalProviderConfig", runtimePreflightHandlerStart);
  const runtimePreflightHandlerSource = panelSource.slice(runtimePreflightHandlerStart, runtimePreflightHandlerEnd);
  const providerPanelHandlerStart = panelSource.indexOf("async function handleProviderReadinessRefresh");
  const providerPanelHandlerEnd = panelSource.indexOf("async function handleStart", providerPanelHandlerStart);
  const providerPanelHandlerSource = panelSource.slice(providerPanelHandlerStart, providerPanelHandlerEnd);
  const voiceProcessStartHandlerStart = panelSource.indexOf("async function handleStartProcess");
  const voiceProcessStartHandlerEnd = panelSource.indexOf("async function handleStopProcess", voiceProcessStartHandlerStart);
  const voiceProcessStartHandlerSource = panelSource.slice(voiceProcessStartHandlerStart, voiceProcessStartHandlerEnd);
  const voiceProcessStopHandlerStart = panelSource.indexOf("async function handleStopProcess");
  const voiceProcessStopHandlerEnd = panelSource.indexOf("async function handleStartLiveKitProcess", voiceProcessStopHandlerStart);
  const voiceProcessStopHandlerSource = panelSource.slice(voiceProcessStopHandlerStart, voiceProcessStopHandlerEnd);
  const liveKitProcessStartHandlerStart = panelSource.indexOf("async function handleStartLiveKitProcess");
  const liveKitProcessStartHandlerEnd = panelSource.indexOf("async function handleStopLiveKitProcess", liveKitProcessStartHandlerStart);
  const liveKitProcessStartHandlerSource = panelSource.slice(liveKitProcessStartHandlerStart, liveKitProcessStartHandlerEnd);
  const liveKitProcessStopHandlerStart = panelSource.indexOf("async function handleStopLiveKitProcess");
  const liveKitProcessStopHandlerEnd = panelSource.indexOf("async function handleSetupCheck", liveKitProcessStopHandlerStart);
  const liveKitProcessStopHandlerSource = panelSource.slice(liveKitProcessStopHandlerStart, liveKitProcessStopHandlerEnd);
  const providerResolveStart = resolveHandlerSource.indexOf(
    'if (voiceSetupAction === "refresh_provider_readiness")'
  );
  const providerResolveEnd = resolveHandlerSource.indexOf(
    'if (voiceSetupAction === "run_live_smoke")',
    providerResolveStart
  );
  const providerResolveSource = resolveHandlerSource.slice(providerResolveStart, providerResolveEnd);
  const parentGate = setupHandlerSource.indexOf("onVoiceProofMutationStart?.(\"Checking voice setup\")");
  const sequenceToken = setupHandlerSource.indexOf("setupCheckSequenceRef.current = setupCheckToken");
  const ownershipGuard = setupHandlerSource.indexOf("const isCurrentSetupCheck = () =>");
  const localGate = setupHandlerSource.indexOf("setupCheckInFlightRef.current = true");
  const loadingState = setupHandlerSource.indexOf("setSetupCheckLoading(true)");
  const fanout = setupHandlerSource.indexOf("settleVoiceSetupFanout");
  const setupReadinessRefresh = setupHandlerSource.indexOf("refreshVoiceReadiness({", fanout);
  const setupReadinessOptions = setupHandlerSource.indexOf("...RUNTIME_PREFLIGHT_READINESS_OPTIONS", setupReadinessRefresh);
  const setupReadinessOwnership = setupHandlerSource.indexOf("shouldApply: isCurrentSetupCheck", setupReadinessRefresh);
  const setupProviderRefresh = setupHandlerSource.indexOf("refreshProviderReadiness({", setupReadinessOwnership);
  const setupProviderOwnership = setupHandlerSource.indexOf("shouldApply: isCurrentSetupCheck", setupProviderRefresh);
  const staleCompletionGuard = setupHandlerSource.indexOf("if (!isCurrentSetupCheck())");
  const clearLoadingState = setupHandlerSource.indexOf("setSetupCheckLoading(false)");
  const finishParentGate = setupHandlerSource.indexOf("onVoiceProofMutationFinish?.(parentMutationSnapshot)");
  const resolveSetupGuard = resolveHandlerSource.indexOf("if (setupCheckInFlightRef.current)");
  const resolveInFlightGuard = resolveHandlerSource.indexOf("if (voiceSetupActionInFlightRef.current !== null)");
  const resolveActionToken = resolveHandlerSource.indexOf("voiceSetupActionSequenceRef.current = setupActionToken");
  const resolveInFlightOwner = resolveHandlerSource.indexOf("voiceSetupActionInFlightRef.current = setupActionToken");
  const resolveLoadingState = resolveHandlerSource.indexOf("setVoiceSetupActionLoading(true)");
  const resolveClearInFlight = resolveHandlerSource.indexOf("voiceSetupActionInFlightRef.current = null");
  const resolveClearLoading = resolveHandlerSource.indexOf("setVoiceSetupActionLoading(false)");
  const resolverParentHelper = resolveHandlerSource.indexOf("const runResolverParentMutation = async");
  const resolverParentHelperGate = resolveHandlerSource.indexOf("const parentMutationSnapshot = onVoiceProofMutationStart?.(label)", resolverParentHelper);
  const resolverParentHelperFinish = resolveHandlerSource.indexOf("onVoiceProofMutationFinish?.(parentMutationSnapshot)", resolverParentHelper);
  const resolverStartLiveKitParent = resolveHandlerSource.indexOf('runResolverParentMutation(\n          "Starting local LiveKit"');
  const resolverRestartLiveKitParent = resolveHandlerSource.indexOf('runResolverParentMutation(\n          "Restarting local LiveKit"');
  const resolverConfigureLiveKitDevParent = resolveHandlerSource.indexOf('runResolverParentMutation(\n          "Configuring local LiveKit dev defaults"');
  const resolverConfigureLiveKitDevCall = resolveHandlerSource.indexOf("handleConfigureLocalLiveKitDev({ skipParentMutation: true })");
  const resolverConfigureLiveKitDevSkip = resolveHandlerSource.indexOf('if (configAttempt.status === "skipped")');
  const resolverConfigureLiveKitDevRecord = resolveHandlerSource.indexOf("await recordResolverAttempt(", resolverConfigureLiveKitDevSkip);
  const resolverRunPreflightParent = resolveHandlerSource.indexOf('runResolverParentMutation(\n          "Running setup runtime preflight"');
  const resolverRunPreflightRefresh = resolveHandlerSource.indexOf("const readinessResult = await refreshVoiceReadiness({", resolverRunPreflightParent);
  const resolverRunPreflightOptions = resolveHandlerSource.indexOf("...RUNTIME_PREFLIGHT_READINESS_OPTIONS", resolverRunPreflightRefresh);
  const resolverRunPreflightOwnership = resolveHandlerSource.indexOf("shouldApply: isCurrentSetupAction", resolverRunPreflightRefresh);
  const resolverRunPreflightRecord = resolveHandlerSource.indexOf("await recordResolverAttempt(", resolverRunPreflightOwnership);
  const resolverStartAgentParent = resolveHandlerSource.indexOf('runResolverParentMutation(\n          "Starting voice agent"');
  const providerResolveParentGate = providerResolveSource.indexOf(
    'onVoiceProofMutationStart?.("Refreshing provider readiness")'
  );
  const providerResolveRefresh = providerResolveSource.indexOf("const providerReadinessResult = await refreshProviderReadiness({");
  const providerResolveOwnership = providerResolveSource.indexOf("shouldApply: isCurrentSetupAction", providerResolveRefresh);
  const providerResolveCatchGuard = providerResolveSource.indexOf("if (!isCurrentSetupAction())");
  const providerResolveFinishGate = providerResolveSource.indexOf("onVoiceProofMutationFinish?.(parentMutationSnapshot)");
  const liveProofInFlightGuard = liveProofHandlerSource.indexOf("if (liveVoiceProofPathActionInFlightRef.current !== null)");
  const liveProofActionCapture = liveProofHandlerSource.indexOf("const liveProofAction = liveVoiceProofPath.primaryAction");
  const liveProofInFlightOwner = liveProofHandlerSource.indexOf("liveVoiceProofPathActionInFlightRef.current = proofActionToken");
  const liveProofLoadingState = liveProofHandlerSource.indexOf("setLiveVoiceProofPathActionLoading(true)");
  const liveProofParentGate = liveProofHandlerSource.indexOf("onVoiceProofMutationStart?.(");
  const liveProofProviderRefresh = liveProofHandlerSource.indexOf("await refreshProviderReadiness({");
  const liveProofProviderRefreshOwnership = liveProofHandlerSource.indexOf("shouldApply: isCurrentProofAction");
  const liveProofRuntimePreflightCase = liveProofHandlerSource.indexOf('case "run_runtime_preflight":');
  const liveProofRuntimePreflightRefresh = liveProofHandlerSource.indexOf("await refreshVoiceReadiness({", liveProofRuntimePreflightCase);
  const liveProofRuntimePreflightOptions = liveProofHandlerSource.indexOf("...RUNTIME_PREFLIGHT_READINESS_OPTIONS", liveProofRuntimePreflightRefresh);
  const liveProofRuntimePreflightOwnership = liveProofHandlerSource.indexOf("shouldApply: isCurrentProofAction", liveProofRuntimePreflightRefresh);
  const liveProofClearInFlight = liveProofHandlerSource.indexOf("liveVoiceProofPathActionInFlightRef.current = null");
  const liveProofClearLoading = liveProofHandlerSource.indexOf("setLiveVoiceProofPathActionLoading(false)");
  const liveProofFinishGate = liveProofHandlerSource.indexOf("onVoiceProofMutationFinish?.(parentMutationSnapshot)");
  const runtimePreflightInFlightGuard = runtimePreflightHandlerSource.indexOf("if (runtimePreflightActionInFlightRef.current !== null)");
  const runtimePreflightOwner = runtimePreflightHandlerSource.indexOf("runtimePreflightActionInFlightRef.current = runtimePreflightToken");
  const runtimePreflightParentGate = runtimePreflightHandlerSource.indexOf('onVoiceProofMutationStart?.("Running runtime preflight")');
  const runtimePreflightRefresh = runtimePreflightHandlerSource.indexOf("await refreshVoiceReadiness({");
  const runtimePreflightOptions = runtimePreflightHandlerSource.indexOf("...RUNTIME_PREFLIGHT_READINESS_OPTIONS");
  const runtimePreflightOwnership = runtimePreflightHandlerSource.indexOf("shouldApply: isCurrentRuntimePreflight");
  const runtimePreflightClearInFlight = runtimePreflightHandlerSource.lastIndexOf("runtimePreflightActionInFlightRef.current = null");
  const runtimePreflightFinishGate = runtimePreflightHandlerSource.indexOf("onVoiceProofMutationFinish?.(parentMutationSnapshot)");
  const providerPanelInFlightGuard = providerPanelHandlerSource.indexOf("if (providerReadinessActionInFlightRef.current !== null)");
  const providerPanelInFlightOwner = providerPanelHandlerSource.indexOf("providerReadinessActionInFlightRef.current = providerRefreshToken");
  const providerPanelNoRunBranch = providerPanelHandlerSource.indexOf("if (!runId)");
  const providerPanelParentGate = providerPanelHandlerSource.indexOf('onVoiceProofMutationStart?.("Refreshing provider readiness")');
  const providerPanelRefresh = providerPanelHandlerSource.lastIndexOf("await refreshProviderReadiness({");
  const providerPanelOwnership = providerPanelHandlerSource.lastIndexOf("shouldApply: isCurrentProviderRefresh");
  const providerPanelClearInFlight = providerPanelHandlerSource.lastIndexOf("providerReadinessActionInFlightRef.current = null");
  const providerPanelFinishGate = providerPanelHandlerSource.indexOf("onVoiceProofMutationFinish?.(parentMutationSnapshot)");
  const voiceProcessStartGate = voiceProcessStartHandlerSource.indexOf("if (voiceProcessActionInFlightRef.current !== null)");
  const voiceProcessStartOwner = voiceProcessStartHandlerSource.indexOf("voiceProcessActionInFlightRef.current = processActionToken");
  const voiceProcessStartParentGate = voiceProcessStartHandlerSource.indexOf('onVoiceProofMutationStart?.("Starting voice agent")');
  const voiceProcessStopGate = voiceProcessStopHandlerSource.indexOf("if (voiceProcessActionInFlightRef.current !== null)");
  const voiceProcessStopOwner = voiceProcessStopHandlerSource.indexOf("voiceProcessActionInFlightRef.current = processActionToken");
  const voiceProcessStopParentGate = voiceProcessStopHandlerSource.indexOf('onVoiceProofMutationStart?.("Stopping voice agent")');
  const liveKitProcessStartGate = liveKitProcessStartHandlerSource.indexOf("if (liveKitProcessActionInFlightRef.current !== null)");
  const liveKitProcessStartOwner = liveKitProcessStartHandlerSource.indexOf("liveKitProcessActionInFlightRef.current = liveKitActionToken");
  const liveKitProcessStartParentGate = liveKitProcessStartHandlerSource.indexOf('onVoiceProofMutationStart?.("Starting local LiveKit")');
  const liveKitProcessStopGate = liveKitProcessStopHandlerSource.indexOf("if (liveKitProcessActionInFlightRef.current !== null)");
  const liveKitProcessStopOwner = liveKitProcessStopHandlerSource.indexOf("liveKitProcessActionInFlightRef.current = liveKitActionToken");
  const liveKitProcessStopParentGate = liveKitProcessStopHandlerSource.indexOf('onVoiceProofMutationStart?.("Stopping local LiveKit")');

  assert.notEqual(setupHandlerStart, -1);
  assert.notEqual(resolveHandlerStart, -1);
  assert.notEqual(liveProofHandlerStart, -1);
  assert.notEqual(runtimePreflightHandlerStart, -1);
  assert.notEqual(providerPanelHandlerStart, -1);
  assert.notEqual(voiceProcessStartHandlerStart, -1);
  assert.notEqual(voiceProcessStopHandlerStart, -1);
  assert.notEqual(liveKitProcessStartHandlerStart, -1);
  assert.notEqual(liveKitProcessStopHandlerStart, -1);
  assert.notEqual(providerResolveStart, -1);
  assert.notEqual(parentGate, -1);
  assert.notEqual(sequenceToken, -1);
  assert.notEqual(ownershipGuard, -1);
  assert.notEqual(localGate, -1);
  assert.notEqual(loadingState, -1);
  assert.notEqual(fanout, -1);
  assert.notEqual(setupReadinessRefresh, -1);
  assert.notEqual(setupReadinessOptions, -1);
  assert.notEqual(setupReadinessOwnership, -1);
  assert.notEqual(setupProviderRefresh, -1);
  assert.notEqual(setupProviderOwnership, -1);
  assert.notEqual(staleCompletionGuard, -1);
  assert.notEqual(clearLoadingState, -1);
  assert.notEqual(finishParentGate, -1);
  assert.notEqual(resolveSetupGuard, -1);
  assert.notEqual(resolveInFlightGuard, -1);
  assert.notEqual(resolveActionToken, -1);
  assert.notEqual(resolveInFlightOwner, -1);
  assert.notEqual(resolveLoadingState, -1);
  assert.notEqual(resolveClearInFlight, -1);
  assert.notEqual(resolveClearLoading, -1);
  assert.notEqual(resolverParentHelper, -1);
  assert.notEqual(resolverParentHelperGate, -1);
  assert.notEqual(resolverParentHelperFinish, -1);
  assert.notEqual(resolverStartLiveKitParent, -1);
  assert.notEqual(resolverRestartLiveKitParent, -1);
  assert.notEqual(resolverConfigureLiveKitDevParent, -1);
  assert.notEqual(resolverConfigureLiveKitDevCall, -1);
  assert.notEqual(resolverConfigureLiveKitDevSkip, -1);
  assert.notEqual(resolverConfigureLiveKitDevRecord, -1);
  assert.notEqual(resolverRunPreflightParent, -1);
  assert.notEqual(resolverRunPreflightRefresh, -1);
  assert.notEqual(resolverRunPreflightOptions, -1);
  assert.notEqual(resolverRunPreflightOwnership, -1);
  assert.notEqual(resolverRunPreflightRecord, -1);
  assert.notEqual(resolverStartAgentParent, -1);
  assert.notEqual(providerResolveParentGate, -1);
  assert.notEqual(providerResolveRefresh, -1);
  assert.notEqual(providerResolveOwnership, -1);
  assert.notEqual(providerResolveCatchGuard, -1);
  assert.notEqual(providerResolveFinishGate, -1);
  assert.notEqual(liveProofInFlightGuard, -1);
  assert.notEqual(liveProofActionCapture, -1);
  assert.notEqual(liveProofInFlightOwner, -1);
  assert.notEqual(liveProofLoadingState, -1);
  assert.notEqual(liveProofParentGate, -1);
  assert.notEqual(liveProofProviderRefresh, -1);
  assert.notEqual(liveProofProviderRefreshOwnership, -1);
  assert.notEqual(liveProofRuntimePreflightCase, -1);
  assert.notEqual(liveProofRuntimePreflightRefresh, -1);
  assert.notEqual(liveProofRuntimePreflightOptions, -1);
  assert.notEqual(liveProofRuntimePreflightOwnership, -1);
  assert.notEqual(liveProofClearInFlight, -1);
  assert.notEqual(liveProofClearLoading, -1);
  assert.notEqual(liveProofFinishGate, -1);
  assert.notEqual(runtimePreflightInFlightGuard, -1);
  assert.notEqual(runtimePreflightOwner, -1);
  assert.notEqual(runtimePreflightParentGate, -1);
  assert.notEqual(runtimePreflightRefresh, -1);
  assert.notEqual(runtimePreflightOptions, -1);
  assert.notEqual(runtimePreflightOwnership, -1);
  assert.notEqual(runtimePreflightClearInFlight, -1);
  assert.notEqual(runtimePreflightFinishGate, -1);
  assert.notEqual(providerPanelInFlightGuard, -1);
  assert.notEqual(providerPanelInFlightOwner, -1);
  assert.notEqual(providerPanelNoRunBranch, -1);
  assert.notEqual(providerPanelParentGate, -1);
  assert.notEqual(providerPanelRefresh, -1);
  assert.notEqual(providerPanelOwnership, -1);
  assert.notEqual(providerPanelClearInFlight, -1);
  assert.notEqual(providerPanelFinishGate, -1);
  assert.notEqual(voiceProcessStartGate, -1);
  assert.notEqual(voiceProcessStartOwner, -1);
  assert.notEqual(voiceProcessStartParentGate, -1);
  assert.notEqual(voiceProcessStopGate, -1);
  assert.notEqual(voiceProcessStopOwner, -1);
  assert.notEqual(voiceProcessStopParentGate, -1);
  assert.notEqual(liveKitProcessStartGate, -1);
  assert.notEqual(liveKitProcessStartOwner, -1);
  assert.notEqual(liveKitProcessStartParentGate, -1);
  assert.notEqual(liveKitProcessStopGate, -1);
  assert.notEqual(liveKitProcessStopOwner, -1);
  assert.notEqual(liveKitProcessStopParentGate, -1);
  assert.ok(parentGate < sequenceToken);
  assert.ok(sequenceToken < ownershipGuard);
  assert.ok(ownershipGuard < localGate);
  assert.ok(localGate < loadingState);
  assert.ok(loadingState < fanout);
  assert.ok(fanout < setupReadinessRefresh);
  assert.ok(setupReadinessRefresh < setupReadinessOptions);
  assert.ok(setupReadinessOptions < setupReadinessOwnership);
  assert.ok(setupReadinessOwnership < setupProviderRefresh);
  assert.ok(setupProviderRefresh < setupProviderOwnership);
  assert.ok(setupProviderOwnership < staleCompletionGuard);
  assert.ok(staleCompletionGuard < clearLoadingState);
  assert.ok(clearLoadingState < finishParentGate);
  assert.ok(resolveSetupGuard < resolveInFlightGuard);
  assert.ok(resolveInFlightGuard < resolveActionToken);
  assert.ok(resolveActionToken < resolveInFlightOwner);
  assert.ok(resolveInFlightOwner < resolveLoadingState);
  assert.ok(resolveLoadingState < resolveClearInFlight);
  assert.ok(resolveClearInFlight < resolveClearLoading);
  assert.ok(resolveLoadingState < resolverParentHelper);
  assert.ok(resolverParentHelper < resolverParentHelperGate);
  assert.ok(resolverParentHelperGate < resolverParentHelperFinish);
  assert.ok(resolverParentHelperFinish < resolverStartLiveKitParent);
  assert.ok(resolverStartLiveKitParent < resolverRestartLiveKitParent);
  assert.ok(resolverRestartLiveKitParent < resolverConfigureLiveKitDevParent);
  assert.ok(resolverConfigureLiveKitDevParent < resolverConfigureLiveKitDevCall);
  assert.ok(resolverConfigureLiveKitDevCall < resolverConfigureLiveKitDevSkip);
  assert.ok(resolverConfigureLiveKitDevSkip < resolverConfigureLiveKitDevRecord);
  assert.ok(resolverConfigureLiveKitDevRecord < resolverRunPreflightParent);
  assert.ok(resolverRunPreflightParent < resolverRunPreflightRefresh);
  assert.ok(resolverRunPreflightRefresh < resolverRunPreflightOptions);
  assert.ok(resolverRunPreflightOptions < resolverRunPreflightOwnership);
  assert.ok(resolverRunPreflightOwnership < resolverRunPreflightRecord);
  assert.ok(resolverRunPreflightRecord < resolverStartAgentParent);
  assert.ok(providerResolveParentGate < providerResolveRefresh);
  assert.ok(providerResolveRefresh < providerResolveOwnership);
  assert.ok(providerResolveOwnership < providerResolveCatchGuard);
  assert.ok(providerResolveCatchGuard < providerResolveFinishGate);
  assert.ok(liveProofInFlightGuard < liveProofActionCapture);
  assert.ok(liveProofActionCapture < liveProofInFlightOwner);
  assert.ok(liveProofInFlightOwner < liveProofLoadingState);
  assert.ok(liveProofLoadingState < liveProofParentGate);
  assert.ok(liveProofParentGate < liveProofProviderRefresh);
  assert.ok(liveProofProviderRefresh < liveProofProviderRefreshOwnership);
  assert.ok(liveProofProviderRefreshOwnership < liveProofRuntimePreflightCase);
  assert.ok(liveProofRuntimePreflightCase < liveProofRuntimePreflightRefresh);
  assert.ok(liveProofRuntimePreflightRefresh < liveProofRuntimePreflightOptions);
  assert.ok(liveProofRuntimePreflightOptions < liveProofRuntimePreflightOwnership);
  assert.ok(liveProofProviderRefresh < liveProofClearInFlight);
  assert.ok(liveProofClearInFlight < liveProofClearLoading);
  assert.ok(liveProofClearLoading < liveProofFinishGate);
  assert.ok(runtimePreflightInFlightGuard < runtimePreflightOwner);
  assert.ok(runtimePreflightOwner < runtimePreflightParentGate);
  assert.ok(runtimePreflightParentGate < runtimePreflightRefresh);
  assert.ok(runtimePreflightRefresh < runtimePreflightOptions);
  assert.ok(runtimePreflightOptions < runtimePreflightOwnership);
  assert.ok(runtimePreflightOwnership < runtimePreflightClearInFlight);
  assert.ok(runtimePreflightClearInFlight < runtimePreflightFinishGate);
  assert.ok(providerPanelInFlightGuard < providerPanelInFlightOwner);
  assert.ok(providerPanelInFlightOwner < providerPanelNoRunBranch);
  assert.ok(providerPanelInFlightOwner < providerPanelParentGate);
  assert.ok(providerPanelParentGate < providerPanelRefresh);
  assert.ok(providerPanelRefresh < providerPanelOwnership);
  assert.ok(providerPanelOwnership < providerPanelClearInFlight);
  assert.ok(providerPanelClearInFlight < providerPanelFinishGate);
  assert.ok(voiceProcessStartGate < voiceProcessStartOwner);
  assert.ok(voiceProcessStartOwner < voiceProcessStartParentGate);
  assert.ok(voiceProcessStopGate < voiceProcessStopOwner);
  assert.ok(voiceProcessStopOwner < voiceProcessStopParentGate);
  assert.ok(liveKitProcessStartGate < liveKitProcessStartOwner);
  assert.ok(liveKitProcessStartOwner < liveKitProcessStartParentGate);
  assert.ok(liveKitProcessStopGate < liveKitProcessStopOwner);
  assert.ok(liveKitProcessStopOwner < liveKitProcessStopParentGate);
  assert.match(panelSource, /setupCheckSequenceRef\.current \+= 1;\n\s+setupCheckInFlightRef\.current = false;\n\s+setSetupCheckLoading\(false\);/);
  assert.match(panelSource, /voiceSetupActionSequenceRef\.current \+= 1;\n\s+voiceSetupActionInFlightRef\.current = null;\n\s+setVoiceSetupActionLoading\(false\);/);
  assert.match(panelSource, /providerReadinessActionSequenceRef\.current \+= 1;\n\s+providerReadinessActionInFlightRef\.current = null;/);
  assert.match(panelSource, /runtimePreflightActionSequenceRef\.current \+= 1;\n\s+runtimePreflightActionInFlightRef\.current = null;/);
  assert.match(panelSource, /voiceProcessActionSequenceRef\.current \+= 1;\n\s+voiceProcessActionInFlightRef\.current = null;/);
  assert.match(panelSource, /liveKitProcessActionSequenceRef\.current \+= 1;\n\s+liveKitProcessActionInFlightRef\.current = null;/);
  assert.match(panelSource, /handleStartLiveKitProcess\(\{ skipParentMutation: true \}\)/);
  assert.match(panelSource, /handleStartLiveKitProcess\(\{ forceRestart: true, skipParentMutation: true \}\)/);
  assert.match(panelSource, /handleConfigureLocalLiveKitDev\(\{ skipParentMutation: true \}\)/);
  assert.match(panelSource, /handleStartProcess\(\{ skipParentMutation: true \}\)/);
  assert.match(panelSource, /onClick=\{\(\) => void handleRuntimePreflight\(\)\}/);
  assert.match(panelSource, /liveVoiceProofActionSequenceRef\.current \+= 1;\n\s+liveVoiceProofPathActionInFlightRef\.current = null;\n\s+setLiveVoiceProofPathActionLoading\(false\);/);
  assert.doesNotMatch(panelSource, /refreshVoiceReadiness\(\s*(?:true|false)\b/);
});

test("voice setup fanout waits for delayed branches before surfacing failure", async () => {
  let delayedSettled = false;
  const delayedBranch = new Promise<string>((resolve) => {
    setTimeout(() => {
      delayedSettled = true;
      resolve("delayed");
    }, 10);
  });
  const quickFailure = Promise.reject(new Error("fast setup failure"));

  await assert.rejects(
    settleVoiceSetupFanout([quickFailure, delayedBranch] as const),
    /fast setup failure/
  );
  assert.equal(delayedSettled, true);
});

test("voice panel owns transcript rehearsal turn completions by run and session", () => {
  const panelSource = readFileSync(
    join(process.cwd(), "components/voice/RealtimeVoicePanel.tsx"),
    "utf8"
  );
  const rehearsalTurnHandler =
    panelSource.match(/async function handleRehearsalTurn\(\)[\s\S]*?\n  async function handleCreateVoiceRun/)?.[0] ?? "";
  const handleStartSource = panelSource.match(/async function handleStart\(\)[\s\S]*?\n  async function handleInterrupt/)?.[0] ?? "";
  const handleStopSource = panelSource.match(/async function handleStop\(\)[\s\S]*?\n  async function handleVoiceSmoke/)?.[0] ?? "";

  assert.match(panelSource, /const invalidateRehearsalTurn = useCallback/);
  assert.match(
    panelSource,
    /if \(options\.clearLoading && componentMountedRef\.current\) \{\s+setRehearsalLoading\(false\);/
  );
  assert.match(panelSource, /rehearsalTurnSequenceRef/);
  assert.match(panelSource, /rehearsalTurnInFlightRef/);
  assert.match(panelSource, /const canRouteRehearsalTurn = Boolean/);
  assert.match(panelSource, /activeRealtimeSessionIdRef\.current === liveSession\.realtime_session_id/);
  assert.match(panelSource, /disabled=\{!canRouteRehearsalTurn \|\| rehearsalLoading\}/);
  assert.match(handleStartSource, /invalidateRehearsalTurn\(\{ clearLoading: true \}\)/);
  assert.match(handleStopSource, /invalidateRehearsalTurn\(\{ clearLoading: true \}\)/);
  assert.match(handleStopSource, /activeRealtimeSessionIdRef\.current = null/);
  assert.match(rehearsalTurnHandler, /const rehearsalRunId = runId/);
  assert.match(rehearsalTurnHandler, /const rehearsalSessionId = liveSession\.realtime_session_id/);
  assert.match(rehearsalTurnHandler, /const rehearsalTurnToken = rehearsalTurnSequenceRef\.current \+ 1/);
  assert.match(rehearsalTurnHandler, /activeRealtimeSessionIdRef\.current !== liveSession\.realtime_session_id/);
  assert.match(rehearsalTurnHandler, /activeControlToken: rehearsalTurnSequenceRef\.current/);
  assert.match(rehearsalTurnHandler, /activeRunId: currentRunIdRef\.current/);
  assert.match(rehearsalTurnHandler, /activeSessionId: activeRealtimeSessionIdRef\.current/);
  assert.match(rehearsalTurnHandler, /if \(!isCurrentRehearsalTurn\(\)\) \{\s+return;\s+\}/);
  assert.match(rehearsalTurnHandler, /onVoiceRunMutationStart\?\.\("Routing rehearsal turn"\)/);
  assert.match(rehearsalTurnHandler, /const finishParentMutation = \(\) =>/);
  assert.match(
    rehearsalTurnHandler,
    /if \(isCurrentRehearsalTurn\(\)\) \{\s+rehearsalTurnInFlightRef\.current = false;\s+setRehearsalLoading\(false\)/
  );
  const parentGate = rehearsalTurnHandler.indexOf('onVoiceRunMutationStart?.("Routing rehearsal turn")');
  const turnApi = rehearsalTurnHandler.indexOf("const result = await sendRealtimeTurn");
  const finishBeforeFollowup = rehearsalTurnHandler.indexOf("finishParentMutation();");
  const followup = rehearsalTurnHandler.indexOf("await onVoiceFollowupReady(result.brief_task_message_id)");

  assert.notEqual(parentGate, -1);
  assert.notEqual(turnApi, -1);
  assert.notEqual(finishBeforeFollowup, -1);
  assert.notEqual(followup, -1);
  assert.ok(parentGate < turnApi);
  assert.ok(turnApi < finishBeforeFollowup);
  assert.ok(finishBeforeFollowup < followup);
});

test("voice panel cleans up failed provider joins without hiding durable cleanup failures", () => {
  const panelSource = readFileSync(
    join(process.cwd(), "components/voice/RealtimeVoicePanel.tsx"),
    "utf8"
  );
  const handleStartSource = panelSource.match(/async function handleStart\(\)[\s\S]*?\n  async function handleInterrupt/)?.[0] ?? "";

  assert.match(panelSource, /!liveSession &&\s+!\["starting", "joining", "ready"\]\.includes\(status\)/);
  assert.match(handleStartSource, /const cleanupStartedSession = async \(reason: string\)/);
  assert.match(
    handleStartSource,
    /if \(!isCurrentStart\(\)\) \{\s+if \(joinResult\.status === "joined"\) \{[\s\S]*?await cleanupStartedSession\("Discarded stale OpenRouter\/Kokoro voice session after LiveKit join completed for an inactive start\."\);[\s\S]*?return;/
  );
  assert.match(
    handleStartSource,
    /const cleanupEnded = await cleanupStartedSession\("Discarded OpenRouter\/Kokoro voice session after LiveKit join did not complete\."\);/
  );
  assert.match(
    handleStartSource,
    /if \(cleanupEnded\) \{\s+activeRealtimeSessionIdRef\.current = null;\s+setLiveSession\(null\);/
  );
  assert.match(handleStartSource, /else \{[\s\S]*?setError\(`\$\{joinResult\.message\} Cleanup failed/);
});

test("readiness result strength keeps full preflight proof over weaker overlap", () => {
  assert.equal(voiceReadinessRefreshStrength({}), 0);
  assert.equal(voiceReadinessRefreshStrength(LIVEKIT_TRANSPORT_PREFLIGHT_OPTIONS), 1);
  assert.equal(voiceReadinessRefreshStrength(RUNTIME_PREFLIGHT_READINESS_OPTIONS), 5);
  assert.equal(
    shouldApplyVoiceReadinessResult({ epoch: 1, strength: 5 }, { epoch: 1, strength: 0 }),
    false
  );
  assert.equal(
    shouldApplyVoiceReadinessResult({ epoch: 1, strength: 5 }, { epoch: 1, strength: 1 }),
    false
  );
  assert.equal(
    shouldApplyVoiceReadinessResult({ epoch: 1, strength: 1 }, { epoch: 1, strength: 5 }),
    true
  );
  assert.equal(
    shouldApplyVoiceReadinessResult({ epoch: 1, strength: 5 }, { epoch: 1, strength: 5 }),
    true
  );
  assert.equal(
    shouldApplyVoiceReadinessResult({ epoch: 1, strength: 5 }, { epoch: 2, strength: 0 }),
    true
  );
});

test("keyed single-flight coalesces identical readiness refreshes during interleaving", async () => {
  const inFlight = new Map<string, Promise<string>>();
  const pending = {
    full: null as ((value: string) => void) | null,
    passive: null as ((value: string) => void) | null
  };
  let fullStarts = 0;
  let passiveStarts = 0;

  const fullFirst = startKeyedSingleFlight(inFlight, "full", () => {
    fullStarts += 1;
    return new Promise<string>((resolve) => {
      pending.full = resolve;
    });
  });
  const passive = startKeyedSingleFlight(inFlight, "passive", () => {
    passiveStarts += 1;
    return new Promise<string>((resolve) => {
      pending.passive = resolve;
    });
  });
  const fullSecond = startKeyedSingleFlight(inFlight, "full", () => {
    fullStarts += 1;
    return Promise.resolve("duplicate");
  });

  assert.equal(fullFirst.started, true);
  assert.equal(passive.started, true);
  assert.equal(fullSecond.started, false);
  assert.equal(fullSecond.promise, fullFirst.promise);
  assert.equal(fullStarts, 1);
  assert.equal(passiveStarts, 1);

  pending.passive?.("passive-done");
  assert.equal(await passive.promise, "passive-done");
  assert.equal(inFlight.has("passive"), false);
  assert.equal(inFlight.has("full"), true);

  const fullThird = startKeyedSingleFlight(inFlight, "full", () => Promise.resolve("late-duplicate"));
  assert.equal(fullThird.started, false);
  assert.equal(fullThird.promise, fullFirst.promise);
  assert.equal(fullStarts, 1);

  pending.full?.("full-done");
  assert.equal(await fullFirst.promise, "full-done");
  assert.equal(inFlight.has("full"), false);
});

test("provider release gate treats direct env secret status as configured without file-write guidance", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness({
      providers: [
        provider({
          provider_id: "gemma4-primary",
          provider_type: "gemma4_hf_endpoint",
          secret_files: [
            {
              env_name: "HF_TOKEN",
              file_env_name: "HF_TOKEN_FILE",
              status: "direct_env",
              configured: true,
              path: ".secrets/hf_token",
              detail: "HF_TOKEN is set directly and overrides the file."
            }
          ]
        }),
        provider({
          provider_id: "gemma4-realtime",
          provider_type: "realtime_audio",
          selected: true
        }),
        provider({
          provider_id: "tavily-search",
          provider_type: "web_search",
          selected: true
        }),
        provider({
          provider_id: "deterministic-reranker",
          provider_type: "reranker",
          selected: true
        })
      ]
    }),
    runtimeReadiness: runtimeReady,
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1"
  });

  assert.deepEqual(gate.secretFileGuidance, [
    {
      envName: "HF_TOKEN",
      fileEnvName: "HF_TOKEN_FILE",
      status: "direct_env",
      configured: true,
      path: ".secrets/hf_token",
      detail: "HF_TOKEN is set directly and overrides the file.",
      action: "HF_TOKEN is set directly; .secrets/hf_token is optional for this run."
    }
  ]);
});

test("provider release gate gives direct setup copy when a secret file env is not configured", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness({
      providers: [
        provider({
          provider_id: "gemma4-primary",
          provider_type: "gemma4_hf_endpoint",
          secret_files: [
            {
              env_name: "HF_TOKEN",
              file_env_name: "HF_TOKEN_FILE",
              status: "not_configured",
              configured: false,
              path: null,
              detail: "HF_TOKEN_FILE is not configured."
            }
          ]
        }),
        provider({
          provider_id: "gemma4-realtime",
          provider_type: "realtime_audio",
          selected: true
        }),
        provider({
          provider_id: "tavily-search",
          provider_type: "web_search",
          selected: true
        }),
        provider({
          provider_id: "deterministic-reranker",
          provider_type: "reranker",
          selected: true
        })
      ]
    }),
    runtimeReadiness: runtimeReady,
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1"
  });

  assert.deepEqual(gate.secretFileGuidance[0], {
    envName: "HF_TOKEN",
    fileEnvName: "HF_TOKEN_FILE",
    status: "not_configured",
    configured: false,
    path: null,
    detail: "HF_TOKEN_FILE is not configured.",
    action: "Set HF_TOKEN directly, or configure HF_TOKEN_FILE to point to a readable secret file."
  });
});

test("provider release gate requires runtime and live smoke before ready", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness(),
    runtimeReadiness: null,
    presence: null,
    smoke: {
      ...liveSmokePassed,
      execute_live_calls: false,
      status: "needs_live_smoke",
      summary: "Rehearsal-only smoke is not provider backed."
    },
    activeRealtimeSessionId: "session-1"
  });

  assert.equal(gate.status, "needs_runtime");
  assert.match(gate.summary, /Run Runtime preflight/);
  assert.equal(
    gate.checks.find((check) => check.id === "live-smoke")?.status,
    "needs_live_smoke"
  );
});

test("provider release gate becomes ready only after provider-backed live smoke", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness(),
    runtimeReadiness: runtimeReady,
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1"
  });

  assert.equal(gate.status, "ready");
  assert.match(gate.summary, /release-ready/);
  assert.equal(gate.checks.every((check) => check.status === "ready"), true);
});

test("provider release gate does not accept passive Gemma audio endpoint readiness as runtime preflight", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness(),
    runtimeReadiness: runtimeWithGemma({
      gemma_audio_endpoint_configured: true,
      gemma_preflight_requested: false,
      gemma_preflight_performed: false
    }),
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1"
  });

  const runtime = gate.checks.find((check) => check.id === "runtime");
  assert.equal(gate.status, "needs_runtime");
  assert.equal(runtime?.status, "needs_runtime");
  assert.match(runtime?.detail ?? "", /Gemma 4 E4B audio endpoint preflight has not run/);
  assert.equal(runtime?.nextAction, "Run Runtime preflight.");
});

test("provider release gate accepts active Gemma audio endpoint preflight proof", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness(),
    runtimeReadiness: runtimeWithGemma({
      gemma_audio_endpoint_configured: true,
      gemma_preflight_requested: true,
      gemma_preflight_performed: true,
      gemma_preflight_text_chars: 5
    }),
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1"
  });

  assert.equal(gate.status, "ready");
  assert.equal(
    gate.checks.find((check) => check.id === "runtime")?.status,
    "ready"
  );
});

test("provider release gate does not accept passive hosted Kokoro readiness as runtime preflight", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness(),
    runtimeReadiness: runtimeWithKokoro({
      kokoro_transport: "hf_endpoint",
      kokoro_preflight_requested: false,
      kokoro_preflight_performed: false
    }),
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1"
  });

  const runtime = gate.checks.find((check) => check.id === "runtime");
  assert.equal(gate.status, "needs_runtime");
  assert.equal(runtime?.status, "needs_runtime");
  assert.match(runtime?.detail ?? "", /Kokoro hosted TTS preflight has not run/);
  assert.equal(runtime?.nextAction, "Run Runtime preflight.");
});

test("provider release gate accepts active hosted Kokoro TTS preflight proof", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness(),
    runtimeReadiness: runtimeWithKokoro({
      kokoro_transport: "hf_endpoint",
      kokoro_preflight_requested: true,
      kokoro_preflight_performed: true,
      kokoro_preflight_audio_bytes: 1024
    }),
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1"
  });

  assert.equal(gate.status, "ready");
  assert.equal(
    gate.checks.find((check) => check.id === "runtime")?.status,
    "ready"
  );
});

test("provider release gate allows local Kokoro readiness without hosted TTS preflight", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness(),
    runtimeReadiness: runtimeWithKokoro({
      kokoro_transport: "local_package",
      kokoro_preflight_requested: false,
      kokoro_preflight_performed: false
    }),
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1"
  });

  assert.equal(gate.status, "ready");
  assert.equal(
    gate.checks.find((check) => check.id === "runtime")?.status,
    "ready"
  );
});

test("provider release gate accepts degraded runtime when required checks passed", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness(),
    runtimeReadiness: {
      ...runtimeReady,
      status: "degraded",
      summary: "Voice runtime is usable but direct event persistence is degraded."
    },
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1"
  });

  assert.equal(gate.status, "ready");
  assert.equal(
    gate.checks.find((check) => check.id === "runtime")?.status,
    "ready"
  );
});

test("provider release gate requires current session proof", () => {
  const stalePresence: VoiceAgentPresenceResult = {
    ...presenceReady,
    realtime_session_id: "old-session",
    summary: "Old session proof."
  };
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness(),
    runtimeReadiness: runtimeReady,
    presence: stalePresence,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "new-session"
  });

  assert.equal(gate.status, "needs_runtime");
  assert.match(gate.summary, /Probe agent presence/);
  assert.equal(
    gate.checks.find((check) => check.id === "presence")?.status,
    "needs_runtime"
  );
  assert.equal(
    gate.checks.find((check) => check.id === "live-smoke")?.status,
    "needs_live_smoke"
  );
});

test("provider release gate blocks when a newer provider failure recovery exists", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness(),
    runtimeReadiness: runtimeReady,
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1",
    artifacts: [
      artifact({
        artifact_id: "old-smoke",
        artifact_type: "provider_smoke_ledger",
        content: {
          status: "passed",
          execute_live_calls: true,
          realtime_session_ids: ["session-1"]
        },
        provenance: { workflow: "provider_smoke_ledger_v1" },
        created_at: "2026-05-18T12:00:00Z"
      }),
      artifact({
        artifact_id: "provider-recovery",
        artifact_type: "provider_operations_ledger",
        content: {
          format: "realtime_provider_failure_recovery",
          status: "blocked_until_realtime_provider_recheck",
          failure: { component: "kokoro_tts" }
        },
        provenance: { workflow: "realtime_provider_failure_recovery_worker_v1" },
        created_at: "2026-05-18T12:01:00Z"
      })
    ]
  });

  assert.equal(gate.status, "blocked");
  const recovery = gate.checks.find((check) => check.id === "provider-recovery");
  assert.equal(recovery?.status, "blocked");
  assert.match(recovery?.detail ?? "", /kokoro_tts/);
  assert.match(gate.summary, /Run recovery checks/);
});

test("provider release gate blocks when a newer provider configuration recovery exists", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness(),
    runtimeReadiness: runtimeReady,
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1",
    artifacts: [
      artifact({
        artifact_id: "old-smoke",
        artifact_type: "provider_smoke_ledger",
        content: {
          status: "passed",
          execute_live_calls: true,
          realtime_session_ids: ["session-1"]
        },
        provenance: { workflow: "provider_smoke_ledger_v1" },
        created_at: "2026-05-18T12:00:00Z"
      }),
      artifact({
        artifact_id: "provider-config-recovery",
        artifact_type: "provider_operations_ledger",
        content: {
          format: "provider_configuration_recovery",
          status: "blocked_until_provider_configuration_recheck",
          blocked_step_count: 2,
          blocked_steps: [
            {
              step_id: "selected-realtime-smoke",
              provider_id: "gemma4-realtime",
              provider_type: "realtime_audio",
              blockers: ["Missing LIVEKIT_API_SECRET."]
            },
            {
              step_id: "selected-web-search-smoke",
              provider_id: "tavily-search",
              provider_type: "web_search",
              blockers: ["Missing TAVILY_API_KEY_FILE."]
            }
          ]
        },
        provenance: { workflow: "provider_configuration_recovery_worker_v1" },
        created_at: "2026-05-18T12:01:00Z"
      })
    ]
  });

  assert.equal(gate.status, "blocked");
  const recovery = gate.checks.find((check) => check.id === "provider-recovery");
  assert.equal(recovery?.status, "blocked");
  assert.equal(recovery?.label, "Provider configuration recovery");
  assert.match(recovery?.detail ?? "", /2 provider-smoke configuration step/);
  assert.match(gate.summary, /Rerun live Runtime smoke/);
});

test("provider release gate allows a newer same-session live smoke after recovery", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness(),
    runtimeReadiness: runtimeReady,
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1",
    artifacts: [
      artifact({
        artifact_id: "provider-recovery",
        artifact_type: "provider_operations_ledger",
        content: {
          format: "realtime_provider_failure_recovery",
          status: "blocked_until_realtime_provider_recheck",
          failure: { component: "gemma_audio_reasoner" }
        },
        provenance: { workflow: "realtime_provider_failure_recovery_worker_v1" },
        created_at: "2026-05-18T12:01:00Z"
      }),
      artifact({
        artifact_id: "new-smoke",
        artifact_type: "provider_smoke_ledger",
        content: {
          status: "passed",
          execute_live_calls: true,
          realtime_session_ids: ["session-1"]
        },
        provenance: { workflow: "provider_smoke_ledger_v1" },
        created_at: "2026-05-18T12:02:00Z"
      })
    ]
  });

  assert.equal(gate.status, "ready");
  assert.equal(
    gate.checks.find((check) => check.id === "provider-recovery")?.status,
    "ready"
  );
});

test("provider release gate allows a newer same-session live smoke after provider configuration recovery", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness(),
    runtimeReadiness: runtimeReady,
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1",
    artifacts: [
      artifact({
        artifact_id: "provider-config-recovery",
        artifact_type: "provider_operations_ledger",
        content: {
          format: "provider_configuration_recovery",
          status: "blocked_until_provider_configuration_recheck",
          blocked_step_count: 1,
          blocked_steps: [
            {
              step_id: "selected-realtime-smoke",
              provider_id: "gemma4-realtime",
              provider_type: "realtime_audio",
              blockers: ["Missing LIVEKIT_API_SECRET."]
            }
          ]
        },
        provenance: { workflow: "provider_configuration_recovery_worker_v1" },
        created_at: "2026-05-18T12:01:00Z"
      }),
      artifact({
        artifact_id: "new-smoke",
        artifact_type: "provider_smoke_ledger",
        content: {
          status: "passed",
          execute_live_calls: true,
          realtime_session_ids: ["session-1"]
        },
        provenance: { workflow: "provider_smoke_ledger_v1" },
        created_at: "2026-05-18T12:02:00Z"
      })
    ]
  });

  assert.equal(gate.status, "ready");
  assert.equal(
    gate.checks.find((check) => check.id === "provider-recovery")?.status,
    "ready"
  );
});

test("provider release gate restores newer durable smoke proof after reload", () => {
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness(),
    runtimeReadiness: runtimeReady,
    presence: presenceReady,
    smoke: null,
    activeRealtimeSessionId: "session-1",
    artifacts: [
      artifact({
        artifact_id: "provider-recovery",
        artifact_type: "provider_operations_ledger",
        content: {
          format: "realtime_provider_failure_recovery",
          status: "blocked_until_realtime_provider_recheck",
          failure: { component: "gemma_audio_reasoner" }
        },
        provenance: { workflow: "realtime_provider_failure_recovery_worker_v1" },
        created_at: "2026-05-18T12:01:00Z"
      }),
      artifact({
        artifact_id: "new-smoke",
        artifact_type: "provider_smoke_ledger",
        content: {
          status: "passed",
          execute_live_calls: true,
          realtime_session_ids: ["session-1"],
          steps: [
            {
              step_id: "gemma-kokoro-voice-streaming-smoke",
              status: "passed",
              smoke_proof_status: "provider_backed",
              realtime_session_ids: ["session-1"],
              blockers: [],
              next_actions: []
            }
          ],
          summary: "Restored provider smoke passed."
        },
        provenance: { workflow: "provider_smoke_ledger_v1" },
        created_at: "2026-05-18T12:02:00Z"
      })
    ]
  });

  assert.equal(gate.status, "ready");
  assert.equal(
    gate.checks.find((check) => check.id === "provider-recovery")?.status,
    "ready"
  );
  assert.equal(
    gate.checks.find((check) => check.id === "live-smoke")?.status,
    "ready"
  );
});

test("provider release gate can clear recovery with the just-built smoke result", () => {
  const currentSmokeArtifact = providerSmokeArtifactFromResult(
    {
      ...liveSmokePassed,
      ledger_artifact_id: "current-smoke-ledger"
    },
    "2026-05-18T12:02:00Z"
  );
  const gate = buildVoiceProviderReleaseGate({
    providerReadiness: readiness(),
    runtimeReadiness: runtimeReady,
    presence: presenceReady,
    smoke: liveSmokePassed,
    activeRealtimeSessionId: "session-1",
    artifacts: [
      artifact({
        artifact_id: "provider-recovery",
        artifact_type: "provider_operations_ledger",
        content: {
          format: "realtime_provider_failure_recovery",
          status: "blocked_until_realtime_provider_recheck",
          failure: { component: "kokoro_tts" }
        },
        provenance: { workflow: "realtime_provider_failure_recovery_worker_v1" },
        created_at: "2026-05-18T12:01:00Z"
      }),
      currentSmokeArtifact
    ]
  });

  assert.equal(currentSmokeArtifact.content.status, "passed");
  assert.equal(currentSmokeArtifact.content.execute_live_calls, true);
  assert.equal(currentSmokeArtifact.provenance.workflow, "provider_smoke_ledger_v1");
  assert.equal(gate.status, "ready");
  assert.equal(
    gate.checks.find((check) => check.id === "provider-recovery")?.status,
    "ready"
  );
});
