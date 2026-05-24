import type {
  ArtifactRecord,
  ClaimRecord,
  FeedbackItem,
  SourceEvidenceRecord
} from "@/lib/api/types";

export const PUBLISHABLE_ARTIFACT_TYPES = new Set([
  "post",
  "reel_script",
  "substack_article",
  "social_package",
  "visual_brief",
  "image",
  "audio",
  "video"
]);

export type ContentReadinessStatus =
  | "no_content"
  | "blocked"
  | "needs_review"
  | "ready_for_publish_check";

export type ContentReadinessCheckStatus = "pass" | "blocked" | "needs_attention";

export type ContentReadinessCheck = {
  id: string;
  label: string;
  status: ContentReadinessCheckStatus;
  detail: string;
  ownerAgentId: string;
};

export type ContentReadinessSnapshot = {
  status: ContentReadinessStatus;
  label: string;
  summary: string;
  metrics: {
    publishableArtifactCount: number;
    sourceBackedArtifactCount: number;
    claimLinkedArtifactCount: number;
    acceptedContextEvidenceCount: number;
    unsupportedClaimCount: number;
    needsReviewClaimCount: number;
    openFeedbackCount: number;
    missingReviewerDecisionCount: number;
  };
  checks: ContentReadinessCheck[];
  blockers: string[];
  nextActions: string[];
};

type ContentReadinessInput = {
  artifacts: ArtifactRecord[];
  claims: ClaimRecord[];
  feedback: FeedbackItem[];
  sourceEvidence?: SourceEvidenceRecord[];
};

export function isPublishableArtifact(artifact: ArtifactRecord) {
  return PUBLISHABLE_ARTIFACT_TYPES.has(artifact.artifact_type);
}

export function buildContentReadinessSnapshot(
  input: ContentReadinessInput
): ContentReadinessSnapshot {
  const publishableArtifacts = input.artifacts.filter(isPublishableArtifact);
  const acceptedSourceIndex = buildAcceptedSourceIndex(input.sourceEvidence);
  const missingSourceArtifacts = publishableArtifacts.filter(
    (artifact) => !artifactHasAcceptedSourceDependencies(artifact, acceptedSourceIndex)
  );
  const missingClaimArtifacts = publishableArtifacts.filter(
    (artifact) => artifactClaimIds(artifact).length === 0
  );
  const missingReviewerArtifacts = publishableArtifacts.filter(
    (artifact) => artifact.reviewer_decisions.length === 0
  );
  const unsupportedClaims = input.claims.filter(
    (claim) => claim.support_status === "unsupported"
  );
  const needsReviewClaims = input.claims.filter(
    (claim) => claim.support_status === "needs_review"
  );
  const openFeedback = input.feedback.filter((item) =>
    ["open", "routed"].includes(item.status)
  );
  const acceptedContextEvidence = acceptedSourceIndex.evidence;
  const checks = [
    contentCheck({
      id: "publishable-artifacts",
      label: "Publishable content",
      status: publishableArtifacts.length > 0 ? "pass" : "needs_attention",
      detail: `${publishableArtifacts.length} publishable artifact(s) found.`,
      ownerAgentId: "content-strategist"
    }),
    contentCheck({
      id: "source-dependencies",
      label: "Source dependencies",
      status: missingSourceArtifacts.length === 0 ? "pass" : "blocked",
      detail: `${missingSourceArtifacts.length} publishable artifact(s) lack source evidence.`,
      ownerAgentId: "source-ledger-agent"
    }),
    contentCheck({
      id: "claim-traceability",
      label: "Claim traces",
      status: missingClaimArtifacts.length === 0 ? "pass" : "blocked",
      detail: `${missingClaimArtifacts.length} publishable artifact(s) lack claim traces.`,
      ownerAgentId: "claim-verification-agent"
    }),
    contentCheck({
      id: "claim-support",
      label: "Claim support",
      status: unsupportedClaims.length === 0 ? "pass" : "blocked",
      detail: `${unsupportedClaims.length} unsupported claim(s), ${needsReviewClaims.length} claim(s) need review.`,
      ownerAgentId: "claim-verification-agent"
    }),
    contentCheck({
      id: "reviewer-decisions",
      label: "Editorial review",
      status: missingReviewerArtifacts.length === 0 ? "pass" : "needs_attention",
      detail: `${missingReviewerArtifacts.length} publishable artifact(s) lack reviewer decisions.`,
      ownerAgentId: "editor-in-chief"
    }),
    contentCheck({
      id: "feedback-gates",
      label: "Feedback gates",
      status: openFeedback.length === 0 ? "pass" : "needs_attention",
      detail: `${openFeedback.length} open feedback gate(s).`,
      ownerAgentId: "forward-deployed-engineer"
    })
  ];
  const status = contentReadinessStatus(checks);
  const nextActions = contentReadinessNextActions(checks);
  const blockers = checks
    .filter((check) => check.status !== "pass")
    .map((check) => check.detail);

  return {
    status,
    label: contentReadinessLabel(status),
    summary: contentReadinessSummary(status, publishableArtifacts.length, nextActions),
    metrics: {
      publishableArtifactCount: publishableArtifacts.length,
      sourceBackedArtifactCount:
        publishableArtifacts.length - missingSourceArtifacts.length,
      claimLinkedArtifactCount:
        publishableArtifacts.length - missingClaimArtifacts.length,
      acceptedContextEvidenceCount: acceptedContextEvidence.length,
      unsupportedClaimCount: unsupportedClaims.length,
      needsReviewClaimCount: needsReviewClaims.length,
      openFeedbackCount: openFeedback.length,
      missingReviewerDecisionCount: missingReviewerArtifacts.length
    },
    checks,
    blockers,
    nextActions
  };
}

function contentCheck(input: ContentReadinessCheck): ContentReadinessCheck {
  return input;
}

function contentReadinessStatus(checks: ContentReadinessCheck[]): ContentReadinessStatus {
  const publishable = checks.find((check) => check.id === "publishable-artifacts");
  if (publishable?.status !== "pass") {
    return "no_content";
  }
  if (checks.some((check) => check.status === "blocked")) {
    return "blocked";
  }
  if (checks.some((check) => check.status === "needs_attention")) {
    return "needs_review";
  }
  return "ready_for_publish_check";
}

function contentReadinessLabel(status: ContentReadinessStatus) {
  switch (status) {
    case "ready_for_publish_check":
      return "Ready for publish check";
    case "needs_review":
      return "Needs review";
    case "blocked":
      return "Blocked";
    case "no_content":
      return "No content";
  }
}

function contentReadinessSummary(
  status: ContentReadinessStatus,
  publishableCount: number,
  nextActions: string[]
) {
  if (status === "ready_for_publish_check") {
    return `${publishableCount} publishable artifact(s) have source, claim, feedback, and review proof.`;
  }
  return nextActions[0] ?? "Continue the specialist workflow before publishing.";
}

function contentReadinessNextActions(checks: ContentReadinessCheck[]) {
  const actionByCheck = new Map([
    ["publishable-artifacts", "Generate source-backed post, reel, and Substack drafts."],
    ["source-dependencies", "Run web research and source-ledger repair before packaging."],
    ["claim-traceability", "Run claim verification so every major claim maps to evidence."],
    ["claim-support", "Rewrite, remove, or explicitly mark unsupported claims."],
    ["reviewer-decisions", "Route drafts through Editor-in-Chief and Critic/Reviewer review."],
    ["feedback-gates", "Resolve or route open creator feedback before final packaging."]
  ]);
  const actions = checks
    .filter((check) => check.status !== "pass")
    .map((check) => actionByCheck.get(check.id) ?? `Resolve ${check.label}.`);
  return actions.length > 0
    ? actions
    : ["Run final publish readiness or continue with platform packaging."];
}

type AcceptedSourceIndex = {
  evidence: SourceEvidenceRecord[];
  sourceIds: Set<string>;
  citationIds: Set<string>;
  artifactIds: Set<string>;
};

function buildAcceptedSourceIndex(
  sourceEvidence: SourceEvidenceRecord[] | undefined
): AcceptedSourceIndex {
  const accepted = (sourceEvidence ?? []).filter(
    (source) => source.accepted_for_context === true
  );
  const sourceIds = new Set<string>();
  const citationIds = new Set<string>();
  const artifactIds = new Set<string>();

  for (const source of accepted) {
    addString(sourceIds, source.source_id);
    addString(citationIds, source.citation_id);
    for (const artifactId of source.artifact_ids ?? []) {
      addString(artifactIds, artifactId);
    }
  }

  return { evidence: accepted, sourceIds, citationIds, artifactIds };
}

function artifactHasAcceptedSourceDependencies(
  artifact: ArtifactRecord,
  acceptedSourceIndex: AcceptedSourceIndex
) {
  if (acceptedSourceIndex.artifactIds.has(artifact.artifact_id)) {
    return true;
  }
  const sourceCitations = metadataStringList(artifact.content, "source_citations");
  return (
    artifact.source_ids.some((sourceId) =>
      acceptedSourceIndex.sourceIds.has(sourceId) ||
      acceptedSourceIndex.citationIds.has(sourceId)
    ) ||
    sourceCitations.some((citationId) =>
      acceptedSourceIndex.citationIds.has(citationId) ||
      acceptedSourceIndex.sourceIds.has(citationId)
    )
  );
}

function addString(target: Set<string>, value: unknown) {
  if (typeof value === "string" && value.trim().length > 0) {
    target.add(value);
  }
}

function artifactClaimIds(artifact: ArtifactRecord): string[] {
  const claimIds = [
    ...metadataStringList(artifact.content, "claim_ids"),
    ...metadataStringList(artifact.provenance, "claim_ids"),
    ...metadataClaimTraceIds(artifact.content),
    ...metadataClaimTraceIds(artifact.provenance)
  ];
  return [...new Set(claimIds)];
}

function metadataStringList(metadata: Record<string, unknown>, key: string): string[] {
  const value = metadata[key];
  return Array.isArray(value)
    ? value.filter(
        (item): item is string => typeof item === "string" && item.trim().length > 0
      )
    : [];
}

function metadataClaimTraceIds(metadata: Record<string, unknown>) {
  const value = metadata.claim_trace;
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((entry) => {
    if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
      return typeof entry === "string" ? [entry] : [];
    }
    const claimId = (entry as { claim_id?: unknown }).claim_id;
    return typeof claimId === "string" && claimId.trim().length > 0 ? [claimId] : [];
  });
}
