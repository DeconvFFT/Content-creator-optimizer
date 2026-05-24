import type { ProviderSmokeRunResult, ProviderSmokeStepResult } from "@/lib/api/types";
import { formatLatencyMs } from "./timingLedger";

export const GEMMA_KOKORO_STREAMING_SMOKE_STEP_ID = "gemma-kokoro-voice-streaming-smoke";

export type VoiceAudioFixtureProofStatus = "captured" | "synthetic" | "pending" | "blocked" | "failed";

export type VoiceAudioFixtureProof = {
  status: VoiceAudioFixtureProofStatus;
  title: string;
  summary: string;
  evidence: string[];
};

export type VoiceStreamingProviderProofStatus = "passed" | "blocked" | "failed" | "pending";

export type VoiceStreamingProviderProof = {
  status: VoiceStreamingProviderProofStatus;
  title: string;
  summary: string;
  evidence: string[];
  metrics: Array<{ label: string; value: string }>;
};

function detailString(details: Record<string, unknown>, key: string): string {
  const value = details[key];
  return typeof value === "string" ? value.trim() : "";
}

function detailBoolean(details: Record<string, unknown>, key: string): boolean {
  return details[key] === true;
}

function detailNumber(details: Record<string, unknown>, key: string): number | null {
  const value = details[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function humanizeFixtureSource(source: string): string {
  if (source === "captured_voice_audio_artifact") {
    return "captured voice artifact";
  }
  if (source === "synthetic_silence_probe") {
    return "synthetic silence probe";
  }
  return source.replaceAll("_", " ");
}

function humanizeKokoroProvider(provider: string): string {
  if (provider === "huggingface_kokoro") {
    return "Hosted Kokoro";
  }
  if (provider === "local_kokoro") {
    return "Local Kokoro";
  }
  return provider.replaceAll("_", " ");
}

function humanizeKokoroTransport(transport: string): string {
  if (transport === "hf_endpoint") {
    return "HF endpoint";
  }
  if (transport === "local_package") {
    return "local package";
  }
  return transport.replaceAll("_", " ");
}

function kokoroRouteEvidence(details: Record<string, unknown>): string {
  const kokoroProvider = detailString(details, "kokoro_provider");
  const kokoroTransport = detailString(details, "kokoro_transport");
  const endpointError = detailString(details, "kokoro_endpoint_error");
  if (kokoroTransport === "missing") {
    if (endpointError) {
      return "Kokoro: malformed hosted endpoint and no local package";
    }
    return "Kokoro: missing hosted endpoint or local package";
  }
  if (!kokoroTransport) {
    return "";
  }
  const providerLabel = kokoroProvider ? humanizeKokoroProvider(kokoroProvider) : "Kokoro";
  const route = `Kokoro: ${providerLabel} via ${humanizeKokoroTransport(kokoroTransport)}`;
  return endpointError ? `${route}; malformed hosted endpoint ignored` : route;
}

function firstNextAction(step: ProviderSmokeStepResult): string {
  const action = step.next_actions[0]?.trim();
  return action ? `Next: ${action}` : "";
}

function voiceAgentPresenceEvidence(details: Record<string, unknown>): string {
  const required = detailBoolean(details, "voice_agent_presence_required");
  if (!required) {
    return "";
  }
  const status = detailString(details, "voice_agent_presence_status");
  const sessionId = detailString(details, "realtime_session_id");
  if (status === "ready") {
    return sessionId
      ? `LiveKit agent presence: ready for session ${sessionId}`
      : "LiveKit agent presence: ready";
  }
  if (status === "stale") {
    return "LiveKit agent presence: stale";
  }
  if (status === "missing_session_id") {
    return "LiveKit agent presence: no session id";
  }
  if (status === "missing_session") {
    return "LiveKit agent presence: session not found";
  }
  return "LiveKit agent presence: missing";
}

export function shortSha256(sha256: string): string {
  const clean = sha256.trim();
  if (clean.length <= 12) {
    return clean;
  }
  return `${clean.slice(0, 12)}...`;
}

export function formatAudioBytes(bytes: number | null): string {
  if (bytes === null || bytes < 0) {
    return "";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const kilobytes = bytes / 1024;
  if (kilobytes < 1024) {
    const value = kilobytes >= 10 ? Math.round(kilobytes).toString() : kilobytes.toFixed(1);
    return `${value} KB`;
  }
  const megabytes = kilobytes / 1024;
  const value = megabytes >= 10 ? Math.round(megabytes).toString() : megabytes.toFixed(1);
  return `${value} MB`;
}

export function findGemmaKokoroStreamingSmokeStep(
  smoke: ProviderSmokeRunResult | null | undefined
): ProviderSmokeStepResult | undefined {
  return smoke?.steps.find((step) => step.step_id === GEMMA_KOKORO_STREAMING_SMOKE_STEP_ID);
}

export function buildVoiceAudioFixtureProof(
  step: ProviderSmokeStepResult | null | undefined
): VoiceAudioFixtureProof {
  if (!step) {
    return {
      status: "pending",
      title: "Captured audio proof",
      summary: "Run runtime smoke to show whether Gemma receives a captured voice artifact or a probe fixture.",
      evidence: []
    };
  }

  const source = detailString(step.details, "audio_fixture_source");
  const sourceLabel = source ? humanizeFixtureSource(source) : "fixture not reported";
  const sessionAudioMissing =
    step.smoke_proof_status === "session_audio_artifact_missing" ||
    source === "missing_session_voice_audio_artifact";
  const sessionAudioStale =
    step.smoke_proof_status === "session_audio_artifact_stale" ||
    source === "stale_session_voice_audio_artifact";

  if (step.status === "blocked") {
    const staleAge = detailNumber(step.details, "latest_stale_audio_artifact_age_seconds");
    const maxAge = detailNumber(step.details, "max_voice_audio_artifact_age_seconds");
    return {
      status: "blocked",
      title: "Runtime smoke blocked",
      summary: sessionAudioStale
        ? "Session-bound smoke found only stale captured audio; speak again before rerunning live smoke."
        : sessionAudioMissing
          ? "Session-bound smoke is waiting for a captured user voice turn from this LiveKit room."
          : "Gemma/Kokoro smoke did not run, so captured-audio proof is unavailable.",
      evidence: [
        ...step.blockers.slice(0, 2),
        firstNextAction(step),
        source ? `Fixture: ${sourceLabel}` : "",
        sessionAudioStale && staleAge !== null && maxAge !== null
          ? `Age: ${Math.round(staleAge)}s; max: ${Math.round(maxAge)}s`
          : ""
      ].filter(Boolean)
    };
  }

  if (step.status === "failed") {
    const failure = step.error || step.evidence[0] || step.blockers[0] || "";
    return {
      status: "failed",
      title: "Runtime smoke failed",
      summary: "Gemma/Kokoro smoke failed before a usable audio proof was completed.",
      evidence: [failure, source ? `Fixture: ${sourceLabel}` : ""].filter(Boolean)
    };
  }

  if (detailBoolean(step.details, "audio_artifact_used")) {
    const path = detailString(step.details, "audio_artifact_relative_path");
    const sha256 = detailString(step.details, "audio_artifact_sha256");
    const byteLabel = formatAudioBytes(detailNumber(step.details, "audio_artifact_bytes"));
    const turnId = detailString(step.details, "audio_fixture_turn_id");
    const evidence = [
      path ? `Artifact: ${path}` : "Artifact path was not returned.",
      byteLabel ? `Size: ${byteLabel}` : "",
      sha256 ? `SHA-256: ${shortSha256(sha256)}` : "",
      turnId ? `Turn: ${turnId}` : ""
    ].filter(Boolean);

    return {
      status: "captured",
      title: "Captured audio proof",
      summary: detailString(step.details, "audio_fixture_realtime_session_id")
        ? "Gemma smoke used persisted microphone PCM from the bound LiveKit session."
        : "Gemma smoke used the latest persisted microphone PCM from this run.",
      evidence
    };
  }

  if (step.status === "not_run") {
    return {
      status: "pending",
      title: "Captured audio proof",
      summary: "Runtime smoke has not executed the Gemma/Kokoro audio step yet.",
      evidence: source ? [`Fixture: ${sourceLabel}`] : []
    };
  }

  if (step.status !== "passed") {
    return {
      status: "pending",
      title: "Captured audio proof",
      summary: `Gemma/Kokoro smoke status is ${step.status}; no completed audio fixture proof is available.`,
      evidence: source ? [`Fixture: ${sourceLabel}`] : []
    };
  }

  return {
    status: "synthetic",
    title: "Synthetic fallback",
    summary: "No valid captured voice artifact was available, so the smoke used the configured probe audio.",
    evidence: [`Fixture: ${sourceLabel}`]
  };
}

export function buildVoiceStreamingProviderProof(
  step: ProviderSmokeStepResult | null | undefined
): VoiceStreamingProviderProof {
  if (!step) {
    return {
      status: "pending",
      title: "Gemma/Kokoro transport",
      summary: "Run runtime smoke to prove Gemma streaming and Kokoro first audio.",
      evidence: [],
      metrics: []
    };
  }

  if (step.status === "blocked") {
    const evidence = [
      ...step.blockers.slice(0, 3),
      firstNextAction(step),
      voiceAgentPresenceEvidence(step.details),
      kokoroRouteEvidence(step.details)
    ].filter(Boolean);
    return {
      status: "blocked",
      title: "Gemma/Kokoro transport blocked",
      summary: "Streaming proof is blocked before Gemma or Kokoro can produce live evidence.",
      evidence,
      metrics: []
    };
  }

  if (step.status === "failed") {
    const failure = step.error || step.evidence[0] || "Gemma/Kokoro runtime smoke failed.";
    return {
      status: "failed",
      title: "Gemma/Kokoro transport failed",
      summary: "Streaming proof ran but did not complete first-audio evidence.",
      evidence: [failure],
      metrics: []
    };
  }

  if (step.status !== "passed") {
    return {
      status: "pending",
      title: "Gemma/Kokoro transport",
      summary: `Gemma/Kokoro smoke status is ${step.status}; no completed transport proof is available.`,
      evidence: step.evidence.slice(0, 2),
      metrics: []
    };
  }

  const gemmaModel = detailString(step.details, "gemma_model_id");
  const kokoroModel = detailString(step.details, "kokoro_model_id");
  const metrics = [
    { label: "Gemma TTFT", value: formatLatencyMs(detailNumber(step.details, "gemma_ttft_ms")) },
    {
      label: "Kokoro first audio",
      value: formatLatencyMs(detailNumber(step.details, "kokoro_first_audio_ms"))
    },
    {
      label: "End-to-end first audio",
      value: formatLatencyMs(detailNumber(step.details, "first_audio_end_to_end_ms"))
    }
  ].filter((item) => item.value);
  const evidence = [
    kokoroRouteEvidence(step.details) || "Kokoro: transport not reported",
    voiceAgentPresenceEvidence(step.details),
    gemmaModel ? `Gemma: ${gemmaModel}` : "",
    kokoroModel ? `TTS: ${kokoroModel}` : ""
  ].filter(Boolean);

  return {
    status: "passed",
    title: "Gemma/Kokoro transport",
    summary: "Live smoke measured Gemma streaming into Kokoro speech output.",
    evidence,
    metrics
  };
}
