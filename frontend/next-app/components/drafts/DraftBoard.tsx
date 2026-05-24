import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  Clipboard,
  Copy,
  Download,
  History,
  Link2,
  RefreshCcw,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
  ShieldX
} from "lucide-react";
import clsx from "clsx";
import type { ArtifactRecord, ClaimRecord, FeedbackItem, UUID } from "../../lib/api/types";
import {
  ARTIFACT_JUMP_EVENT,
  artifactDomId,
  artifactIdFromHash
} from "../../lib/state/artifactAnchors";
import { artifactBody, compactId, formatDateTime, statusLabel } from "../../lib/state/format";
import { isPublishableArtifact } from "../../lib/state/contentReadiness";

type DraftBoardProps = {
  artifacts: ArtifactRecord[];
  claims: ClaimRecord[];
  feedback: FeedbackItem[];
  selectedArtifactIds: UUID[];
  busy?: boolean;
  onToggleArtifact: (artifactId: UUID) => void;
  onRevise: (feedbackText: string) => Promise<void>;
  onResolveFeedback: (feedbackId: UUID) => Promise<void>;
};

const FORMAT_FILTERS = [
  { id: "content", label: "Content" },
  { id: "post", label: "Posts" },
  { id: "reel_script", label: "Reels" },
  { id: "substack_article", label: "Substack" },
  { id: "social_package", label: "Packages" },
  { id: "growth_strategy", label: "Growth" },
  { id: "media", label: "Media" },
  { id: "proofs", label: "Proofs" },
  { id: "all", label: "All" }
];

type DraftEvidenceTone = "supported" | "review" | "blocked";

export type DraftEvidenceSummary = {
  sourceCount: number;
  linkedClaimCount: number;
  supported: number;
  needsReview: number;
  unsupported: number;
  revisionCount: number;
  reviewerDecision: string;
  tone: DraftEvidenceTone;
};

export type VoiceSetupProofSummary = {
  action: string;
  status: string;
  summary: string;
  provider: string;
  transportFramework: string;
  readinessStatus: string;
  liveKitProcessStatus: string;
  voiceAgentProcessStatus: string;
  primaryBlockerLabel: string;
  primaryBlockerDetail: string;
  stepCount: number;
};

export type ProviderRecoverySummary = {
  status: string;
  provider: string;
  transportFramework: string;
  failedComponent: string;
  failureStage: string;
  failureReason: string;
  checkCount: number;
  requiredActionCount: number;
  blockedFallbacks: string[];
  ownerAgents: string[];
};

export type GrowthStrategySummary = {
  workflow: string;
  topic: string;
  audienceSegmentCount: number;
  communityTargetCount: number;
  pitchCount: number;
  primaryTerms: string[];
  primaryHook: string;
};

function metadataString(metadata: Record<string, unknown> | undefined, key: string) {
  const value = metadata?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function metadataStringList(metadata: Record<string, unknown> | undefined, key: string) {
  const value = metadata?.[key];
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : [];
}

function metadataClaimTraceIds(metadata: Record<string, unknown> | undefined) {
  const value = metadata?.claim_trace;
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((entry) =>
    entry && typeof entry === "object" && "claim_id" in entry
      ? metadataString(entry as Record<string, unknown>, "claim_id") ?? []
      : []
  );
}

function explicitArtifactClaimIds(artifact: ArtifactRecord) {
  return new Set<UUID>([
    ...metadataStringList(artifact.content, "claim_ids"),
    ...metadataStringList(artifact.provenance, "claim_ids"),
    ...metadataClaimTraceIds(artifact.content),
    ...metadataClaimTraceIds(artifact.provenance)
  ]);
}

function humanLabel(value: string) {
  return statusLabel(value.replaceAll("-", "_"));
}

function metadataRecord(metadata: Record<string, unknown> | undefined, key: string) {
  const value = metadata?.[key];
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function metadataArray(metadata: Record<string, unknown> | undefined, key: string) {
  const value = metadata?.[key];
  return Array.isArray(value) ? value : [];
}

function metadataRecordArray(metadata: Record<string, unknown> | undefined, key: string) {
  return metadataArray(metadata, key).filter(
    (item): item is Record<string, unknown> =>
      item !== null && typeof item === "object" && !Array.isArray(item)
  );
}

function uniqueMetadataStrings(records: Record<string, unknown>[], key: string) {
  return Array.from(
    new Set(
      records
        .map((record) => metadataString(record, key))
        .filter((item): item is string => Boolean(item))
    )
  );
}

function providerConfigurationBlockerReason(blockedSteps: Record<string, unknown>[]) {
  for (const step of blockedSteps) {
    const blocker = metadataStringList(step, "blockers")[0];
    if (blocker) {
      return blocker;
    }
  }
  if (blockedSteps.length > 0) {
    return `${blockedSteps.length} provider-smoke step(s) require configuration repair.`;
  }
  return "Provider configuration blockers were not captured.";
}

function voiceSetupFallbackBlocker(status: string) {
  if (status === "ready") {
    return {
      label: "No blocker",
      detail: "All required setup checks passed."
    };
  }
  if (status === "failed") {
    return {
      label: "Setup proof failed",
      detail: "The setup attempt failed before a blocker snapshot was captured."
    };
  }
  if (status === "blocked") {
    return {
      label: "Blocked setup",
      detail: "The setup proof was blocked but no primary blocker was captured."
    };
  }
  return {
    label: "Setup attempt recorded",
    detail: "No primary blocker snapshot was captured yet."
  };
}

export function voiceSetupProofSummary(
  artifact: ArtifactRecord
): VoiceSetupProofSummary | null {
  if (
    artifact.artifact_type !== "voice_setup_proof" &&
    metadataString(artifact.content, "workflow") !== "voice_setup_proof_v1"
  ) {
    return null;
  }
  const blocker = metadataRecord(artifact.content, "primary_blocker");
  const rawStatus = metadataString(artifact.content, "status") ?? "unknown";
  const fallbackBlocker = voiceSetupFallbackBlocker(rawStatus);
  return {
    action: humanLabel(metadataString(artifact.content, "action") ?? "unknown"),
    status: humanLabel(rawStatus),
    summary:
      metadataString(artifact.content, "summary") ??
      metadataString(artifact.content, "event_summary") ??
      "Voice setup proof recorded.",
    provider: humanLabel(metadataString(artifact.content, "provider") ?? "unknown"),
    transportFramework: humanLabel(
      metadataString(artifact.content, "transport_framework") ?? "unknown"
    ),
    readinessStatus: humanLabel(
      metadataString(artifact.content, "readiness_status") ?? "unknown"
    ),
    liveKitProcessStatus: humanLabel(
      metadataString(artifact.content, "livekit_process_status") ?? "unknown"
    ),
    voiceAgentProcessStatus: humanLabel(
      metadataString(artifact.content, "voice_agent_process_status") ?? "unknown"
    ),
    primaryBlockerLabel:
      metadataString(blocker ?? undefined, "label") ?? fallbackBlocker.label,
    primaryBlockerDetail:
      metadataString(blocker ?? undefined, "detail") ?? fallbackBlocker.detail,
    stepCount: metadataArray(artifact.content, "steps").length
  };
}

export function providerRecoverySummary(
  artifact: ArtifactRecord
): ProviderRecoverySummary | null {
  if (artifact.artifact_type !== "provider_operations_ledger") {
    return null;
  }
  const format = metadataString(artifact.content, "format");
  if (format === "provider_configuration_recovery") {
    const blockedSteps = metadataRecordArray(artifact.content, "blocked_steps");
    const recoveryChecks = metadataRecordArray(artifact.content, "recovery_checks");
    const fallbackPolicy = metadataRecord(artifact.content, "fallback_policy");
    const providerIds = uniqueMetadataStrings(blockedSteps, "provider_id");
    const ownerAgents = uniqueMetadataStrings(recoveryChecks, "owner_agent_id");
    return {
      status: humanLabel(metadataString(artifact.content, "status") ?? "unknown"),
      provider:
        providerIds.length > 0
          ? providerIds.map(humanLabel).join(", ")
          : "unknown",
      transportFramework: "provider smoke",
      failedComponent: "provider configuration",
      failureStage: "configuration recheck required",
      failureReason: providerConfigurationBlockerReason(blockedSteps),
      checkCount: recoveryChecks.length,
      requiredActionCount: metadataArray(artifact.content, "required_actions").length,
      blockedFallbacks: metadataStringList(fallbackPolicy ?? undefined, "blocked").map(humanLabel),
      ownerAgents
    };
  }
  if (format !== "realtime_provider_failure_recovery") {
    return null;
  }
  const failure = metadataRecord(artifact.content, "failure");
  const fallbackPolicy = metadataRecord(artifact.content, "fallback_policy");
  const recoveryChecks = metadataRecordArray(artifact.content, "recovery_checks");
  const ownerAgents = uniqueMetadataStrings(recoveryChecks, "owner_agent_id");
  return {
    status: humanLabel(metadataString(artifact.content, "status") ?? "unknown"),
    provider: humanLabel(metadataString(artifact.content, "provider") ?? "unknown"),
    transportFramework: humanLabel(
      metadataString(artifact.content, "transport_framework") ?? "unknown"
    ),
    failedComponent: humanLabel(metadataString(failure ?? undefined, "component") ?? "unknown"),
    failureStage: humanLabel(metadataString(failure ?? undefined, "stage") ?? "unknown"),
    failureReason:
      metadataString(failure ?? undefined, "reason") ??
      "Provider failure reason was not captured.",
    checkCount: recoveryChecks.length,
    requiredActionCount: metadataArray(artifact.content, "required_actions").length,
    blockedFallbacks: metadataStringList(fallbackPolicy ?? undefined, "blocked").map(humanLabel),
    ownerAgents
  };
}

export function growthStrategySummary(
  artifact: ArtifactRecord
): GrowthStrategySummary | null {
  if (artifact.artifact_type !== "growth_strategy") {
    return null;
  }
  const workflow = metadataString(artifact.content, "workflow") ?? "growth_strategy";
  const hashtagStrategy = metadataRecord(artifact.content, "hashtag_strategy");
  const keywordStrategy = metadataRecord(artifact.content, "keyword_strategy");
  const creatorPackaging = metadataRecord(artifact.content, "creator_packaging");
  const hookAngles = metadataRecordArray(creatorPackaging ?? undefined, "hook_angles");
  const collaborationPitches = metadataRecordArray(
    artifact.content,
    "collaboration_pitches"
  );
  const primaryTerms = [
    ...metadataStringList(hashtagStrategy ?? undefined, "primary"),
    ...metadataStringList(keywordStrategy ?? undefined, "primary")
  ].slice(0, 4);
  return {
    workflow: humanLabel(workflow.replace(/_v\d+$/, "")),
    topic: metadataString(artifact.content, "topic") ?? "growth strategy",
    audienceSegmentCount: metadataArray(artifact.content, "audience_segments").length,
    communityTargetCount: metadataArray(artifact.content, "community_targets").length,
    pitchCount: collaborationPitches.length,
    primaryTerms,
    primaryHook:
      metadataString(hookAngles[0], "hook") ??
      metadataString(collaborationPitches[0], "pitch") ??
      "No primary hook captured."
  };
}

export function isContentArtifact(artifact: ArtifactRecord) {
  return isPublishableArtifact(artifact);
}

export function filterArtifactsForDraftBoard(
  artifacts: ArtifactRecord[],
  filter: string
) {
  if (filter === "all") {
    return artifacts;
  }
  if (filter === "content") {
    return artifacts.filter(isContentArtifact);
  }
  if (filter === "media") {
    return artifacts.filter((artifact) => ["image", "audio", "video"].includes(artifact.artifact_type));
  }
  if (filter === "proofs") {
    return artifacts.filter((artifact) => !isContentArtifact(artifact));
  }
  return artifacts.filter((artifact) => artifact.artifact_type === filter);
}

export function draftBoardFilterForArtifact(artifact: ArtifactRecord) {
  if (isContentArtifact(artifact)) {
    return "content";
  }
  if (["image", "audio", "video"].includes(artifact.artifact_type)) {
    return "media";
  }
  if (artifact.artifact_type === "growth_strategy") {
    return "growth_strategy";
  }
  return "proofs";
}

function latestReviewerDecision(artifact: ArtifactRecord) {
  const latestDecision = [...artifact.reviewer_decisions]
    .reverse()
    .find((decision) => metadataString(decision, "decision") ?? metadataString(decision, "status"));
  const decision =
    metadataString(latestDecision, "decision") ??
    metadataString(latestDecision, "status") ??
    "not_reviewed";
  return humanLabel(decision);
}

export function draftEvidenceSummary(
  artifact: ArtifactRecord,
  linkedClaims: ClaimRecord[]
): DraftEvidenceSummary {
  const counts = linkedClaims.reduce(
    (summary, claim) => ({
      supported: summary.supported + (claim.support_status === "supported" ? 1 : 0),
      needsReview: summary.needsReview + (claim.support_status === "needs_review" ? 1 : 0),
      unsupported: summary.unsupported + (claim.support_status === "unsupported" ? 1 : 0)
    }),
    { supported: 0, needsReview: 0, unsupported: 0 }
  );
  const tone: DraftEvidenceTone =
    artifact.source_ids.length === 0 || counts.unsupported > 0
      ? "blocked"
      : counts.needsReview > 0
        ? "review"
        : "supported";
  return {
    sourceCount: artifact.source_ids.length,
    linkedClaimCount: linkedClaims.length,
    supported: counts.supported,
    needsReview: counts.needsReview,
    unsupported: counts.unsupported,
    revisionCount: artifact.revision_history.length,
    reviewerDecision: latestReviewerDecision(artifact),
    tone
  };
}

export function claimsLinkedToArtifact(
  artifact: ArtifactRecord,
  claims: ClaimRecord[],
  claimsBySource: Record<string, ClaimRecord[]>
) {
  const explicitClaimIds = explicitArtifactClaimIds(artifact);
  if (explicitClaimIds.size > 0) {
    return claims.filter((claim) => explicitClaimIds.has(claim.claim_id));
  }

  const seenClaimIds = new Set<UUID>();
  const linkedClaims: ClaimRecord[] = [];
  artifact.source_ids.forEach((sourceId) => {
    (claimsBySource[sourceId] ?? []).forEach((claim) => {
      if (!seenClaimIds.has(claim.claim_id)) {
        seenClaimIds.add(claim.claim_id);
        linkedClaims.push(claim);
      }
    });
  });
  return linkedClaims;
}

export function DraftBoard({
  artifacts,
  claims,
  feedback,
  selectedArtifactIds,
  busy = false,
  onToggleArtifact,
  onRevise,
  onResolveFeedback
}: DraftBoardProps) {
  const [feedbackText, setFeedbackText] = useState("");
  const [filter, setFilter] = useState("content");
  const [copiedArtifactId, setCopiedArtifactId] = useState<UUID | null>(null);
  const openFeedback = feedback.filter((item) => item.status !== "resolved");

  const hasContentArtifacts = artifacts.some(isContentArtifact);
  const effectiveFilter = filter === "content" && !hasContentArtifacts ? "all" : filter;
  const visibleArtifacts = useMemo(
    () => filterArtifactsForDraftBoard(artifacts, effectiveFilter),
    [artifacts, effectiveFilter]
  );
  const selectedContentArtifactIds = useMemo(
    () =>
      artifacts
        .filter((artifact) => isContentArtifact(artifact))
        .map((artifact) => artifact.artifact_id)
        .filter((artifactId) => selectedArtifactIds.includes(artifactId)),
    [artifacts, selectedArtifactIds]
  );

  useEffect(() => {
    function syncArtifactTarget(targetArtifactId: string | null) {
      if (!targetArtifactId) {
        return;
      }
      const targetArtifact = artifacts.find((item) => item.artifact_id === targetArtifactId);
      if (!targetArtifact) {
        return;
      }
      setFilter(draftBoardFilterForArtifact(targetArtifact));
      window.requestAnimationFrame(() => {
        document
          .getElementById(artifactDomId(targetArtifact.artifact_id))
          ?.scrollIntoView({ block: "center" });
      });
    }

    function syncHashArtifactTarget() {
      syncArtifactTarget(artifactIdFromHash(window.location.hash));
    }

    function syncArtifactJumpEvent(event: Event) {
      const detail = (event as CustomEvent<{ artifactId?: unknown }>).detail;
      syncArtifactTarget(typeof detail?.artifactId === "string" ? detail.artifactId : null);
    }

    syncHashArtifactTarget();
    window.addEventListener("hashchange", syncHashArtifactTarget);
    window.addEventListener(ARTIFACT_JUMP_EVENT, syncArtifactJumpEvent);
    return () => {
      window.removeEventListener("hashchange", syncHashArtifactTarget);
      window.removeEventListener(ARTIFACT_JUMP_EVENT, syncArtifactJumpEvent);
    };
  }, [artifacts]);

  const claimsBySource = useMemo(() => {
    return claims.reduce<Record<string, ClaimRecord[]>>((index, claim) => {
      claim.source_ids.forEach((sourceId) => {
        index[sourceId] = [...(index[sourceId] ?? []), claim];
      });
      return index;
    }, {});
  }, [claims]);

  async function handleRevision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!feedbackText.trim()) {
      return;
    }
    await onRevise(feedbackText.trim());
    setFeedbackText("");
  }

  async function copyArtifact(artifact: ArtifactRecord) {
    await navigator.clipboard.writeText(artifactBody(artifact.content));
    setCopiedArtifactId(artifact.artifact_id);
    window.setTimeout(() => setCopiedArtifactId(null), 1400);
  }

  function exportArtifact(artifact: ArtifactRecord) {
    const body = artifactBody(artifact.content);
    const blob = new Blob([body], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${artifact.title.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}-${compactId(artifact.artifact_id)}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="draft-board">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Artifacts</p>
          <h2>Generated content and proof</h2>
        </div>
        <span>
          {visibleArtifacts.length} of {artifacts.length} artifacts
        </span>
      </div>

      <div className="draft-filter" aria-label="Artifact type filter">
        {FORMAT_FILTERS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={clsx(effectiveFilter === item.id && "active")}
            aria-pressed={effectiveFilter === item.id}
            onClick={() => setFilter(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {artifacts.length === 0 ? (
        <div className="empty-state">
          <Clipboard size={24} aria-hidden="true" />
          <p>Generated drafts will appear here with source and claim linkage.</p>
        </div>
      ) : visibleArtifacts.length === 0 ? (
        <div className="empty-state compact">
          <Clipboard size={24} aria-hidden="true" />
          <p>No artifacts in this view.</p>
        </div>
      ) : (
        <div className="draft-list">
          {visibleArtifacts.map((artifact) => {
            const linkedClaims = claimsLinkedToArtifact(artifact, claims, claimsBySource);
            const evidence = draftEvidenceSummary(artifact, linkedClaims);
            const voiceSetupProof = voiceSetupProofSummary(artifact);
            const providerRecovery = providerRecoverySummary(artifact);
            const growthStrategy = growthStrategySummary(artifact);
            const canReviseArtifact = isContentArtifact(artifact);
            const selected = selectedContentArtifactIds.includes(artifact.artifact_id);
            const nonContentLabel =
              artifact.artifact_type === "growth_strategy" ? "Growth strategy" : "Operational proof";
            return (
              <article
                className={clsx("draft-card", selected && "selected")}
                id={artifactDomId(artifact.artifact_id)}
                key={artifact.artifact_id}
              >
                <div className="draft-card-header">
                  {canReviseArtifact ? (
                    <label className="select-row">
                      <input
                        type="checkbox"
                        checked={selected}
                        disabled={busy}
                        onChange={() => onToggleArtifact(artifact.artifact_id)}
                      />
                      <span>{artifact.title}</span>
                    </label>
                  ) : (
                    <div className="select-row">
                      <ShieldCheck size={16} aria-hidden="true" />
                      <span>{artifact.title}</span>
                    </div>
                  )}
                  <span className="badge">{statusLabel(artifact.artifact_type)}</span>
                </div>
                <p className="draft-meta">
                  {compactId(artifact.artifact_id)} - {formatDateTime(artifact.created_at)}
                </p>
                {voiceSetupProof ? (
                  <>
                    <div
                      className="draft-evidence-strip draft-evidence-review"
                      aria-label="Voice setup proof summary"
                    >
                      <span>
                        <ShieldAlert size={14} aria-hidden="true" />
                        Status: {voiceSetupProof.status}
                      </span>
                      <span>
                        <History size={14} aria-hidden="true" />
                        Action: {voiceSetupProof.action}
                      </span>
                      <span>
                        <Link2 size={14} aria-hidden="true" />
                        Provider: {voiceSetupProof.provider}
                      </span>
                      <span>
                        <ShieldCheck size={14} aria-hidden="true" />
                        Transport: {voiceSetupProof.transportFramework}
                      </span>
                    </div>
                    <div className="voice-setup-proof-card">
                      <strong>{voiceSetupProof.summary}</strong>
                      <span>{voiceSetupProof.primaryBlockerLabel}</span>
                      <p>{voiceSetupProof.primaryBlockerDetail}</p>
                      <div>
                        <small>Runtime readiness: {voiceSetupProof.readinessStatus}</small>
                        <small>LiveKit transport: {voiceSetupProof.liveKitProcessStatus}</small>
                        <small>OpenRouter/Kokoro agent: {voiceSetupProof.voiceAgentProcessStatus}</small>
                        <small>{voiceSetupProof.stepCount} checklist steps captured</small>
                      </div>
                    </div>
                  </>
                ) : providerRecovery ? (
                  <>
                    <div
                      className="draft-evidence-strip draft-evidence-review"
                      aria-label="Provider recovery proof summary"
                    >
                      <span>
                        <ShieldAlert size={14} aria-hidden="true" />
                        Status: {providerRecovery.status}
                      </span>
                      <span>
                        <ShieldX size={14} aria-hidden="true" />
                        Component: {providerRecovery.failedComponent}
                      </span>
                      <span>
                        <Link2 size={14} aria-hidden="true" />
                        Provider: {providerRecovery.provider}
                      </span>
                      <span>
                        <ShieldCheck size={14} aria-hidden="true" />
                        Transport: {providerRecovery.transportFramework}
                      </span>
                    </div>
                    <div className="provider-recovery-proof-card">
                      <strong>{providerRecovery.failureStage}</strong>
                      <span>{providerRecovery.failureReason}</span>
                      <div>
                        <small>{providerRecovery.checkCount} recovery checks</small>
                        <small>{providerRecovery.requiredActionCount} required actions</small>
                        <small>
                          Owners:{" "}
                          {providerRecovery.ownerAgents.length > 0
                            ? providerRecovery.ownerAgents.join(", ")
                            : "not assigned"}
                        </small>
                        <small>
                          Blocked fallback:{" "}
                          {providerRecovery.blockedFallbacks.length > 0
                            ? providerRecovery.blockedFallbacks[0]
                            : "none listed"}
                        </small>
                      </div>
                    </div>
                  </>
                ) : growthStrategy ? (
                  <>
                    <div
                      className="draft-evidence-strip draft-evidence-review"
                      aria-label="Growth strategy summary"
                    >
                      <span>
                        <ShieldQuestion size={14} aria-hidden="true" />
                        {growthStrategy.workflow}
                      </span>
                      <span>
                        <Link2 size={14} aria-hidden="true" />
                        Topic: {growthStrategy.topic}
                      </span>
                      <span>
                        <ShieldCheck size={14} aria-hidden="true" />
                        {growthStrategy.audienceSegmentCount} audience segments
                      </span>
                      <span>
                        <ShieldAlert size={14} aria-hidden="true" />
                        {growthStrategy.communityTargetCount} community targets
                      </span>
                    </div>
                    <div className="provider-recovery-proof-card">
                      <strong>{growthStrategy.primaryHook}</strong>
                      <span>
                        {growthStrategy.primaryTerms.length > 0
                          ? growthStrategy.primaryTerms.join(", ")
                          : "No primary keyword or hashtag terms captured."}
                      </span>
                      <div>
                        <small>{growthStrategy.pitchCount} collaboration pitches</small>
                        <small>{evidence.linkedClaimCount} linked claims</small>
                        <small>{evidence.sourceCount} sources</small>
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <div
                      className={clsx("draft-evidence-strip", `draft-evidence-${evidence.tone}`)}
                      aria-label="Draft evidence summary"
                    >
                      <span>
                        <Link2 size={14} aria-hidden="true" />
                        {evidence.sourceCount} sources
                      </span>
                      <span>
                        <ShieldCheck size={14} aria-hidden="true" />
                        {evidence.supported} supported
                      </span>
                      <span>
                        <ShieldQuestion size={14} aria-hidden="true" />
                        {evidence.needsReview} review
                      </span>
                      <span>
                        <ShieldX size={14} aria-hidden="true" />
                        {evidence.unsupported} unsupported
                      </span>
                      <span>
                        <ShieldAlert size={14} aria-hidden="true" />
                        Reviewer: {evidence.reviewerDecision}
                      </span>
                      <span>
                        <History size={14} aria-hidden="true" />
                        {evidence.revisionCount} revisions
                      </span>
                    </div>
                    <pre className="draft-body">{artifactBody(artifact.content)}</pre>
                  </>
                )}
                <div className="draft-actions">
                  {canReviseArtifact ? (
                    <button
                      type="button"
                      onClick={() => onToggleArtifact(artifact.artifact_id)}
                      disabled={busy}
                    >
                      <RefreshCcw size={16} aria-hidden="true" />
                      {selected ? "Queued" : "Revise"}
                    </button>
                  ) : (
                    <span className="claim-pill">
                      <ShieldCheck size={15} aria-hidden="true" />
                      {nonContentLabel}
                    </span>
                  )}
                  <button type="button" onClick={() => copyArtifact(artifact)}>
                    <Copy size={16} aria-hidden="true" />
                    {copiedArtifactId === artifact.artifact_id ? "Copied" : "Copy"}
                  </button>
                  <button type="button" onClick={() => exportArtifact(artifact)}>
                    <Download size={16} aria-hidden="true" />
                    Export
                  </button>
                  {canReviseArtifact && (
                    <span className={clsx("claim-pill", evidence.linkedClaimCount === 0 && "warning")}>
                      {evidence.linkedClaimCount > 0 ? (
                        <CheckCircle2 size={15} aria-hidden="true" />
                      ) : (
                        <ShieldAlert size={15} aria-hidden="true" />
                      )}
                      {evidence.linkedClaimCount} linked claims
                    </span>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}

      <form className="revision-box" onSubmit={handleRevision}>
        <textarea
          value={feedbackText}
          onChange={(event) => setFeedbackText(event.target.value)}
          disabled={busy}
          placeholder="Tell the agents what to change in the selected drafts..."
          aria-label="Revision feedback"
        />
        <div className="revision-footer">
          <span>{selectedContentArtifactIds.length} selected</span>
          <button
            type="submit"
            disabled={busy || !feedbackText.trim() || selectedContentArtifactIds.length === 0}
          >
            <RefreshCcw size={16} aria-hidden="true" />
            {busy ? "Working" : "Send revision"}
          </button>
        </div>
      </form>

      {openFeedback.length > 0 && (
        <div className="feedback-stack">
          {openFeedback.map((item) => (
            <article key={item.feedback_id}>
              <p>
                <strong>{statusLabel(item.status)}:</strong> {item.feedback_text}
              </p>
              <button
                type="button"
                onClick={() => onResolveFeedback(item.feedback_id)}
                disabled={busy}
              >
                <CheckCircle2 size={15} aria-hidden="true" />
                Resolve
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
