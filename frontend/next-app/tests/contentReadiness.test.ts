import assert from "node:assert/strict";
import test from "node:test";

import type {
  ArtifactRecord,
  ClaimRecord,
  FeedbackItem,
  SourceEvidenceRecord
} from "../lib/api/types";
import {
  buildContentReadinessSnapshot,
  isPublishableArtifact
} from "../lib/state/contentReadiness";

function artifact(overrides: Partial<ArtifactRecord> = {}): ArtifactRecord {
  return {
    artifact_id: "artifact-1",
    run_id: "run-1",
    artifact_type: "post",
    title: "Source-backed post",
    uri: "artifact://runs/run-1/artifacts/artifact-1",
    content: {
      claim_ids: ["claim-1"]
    },
    provenance: {},
    source_ids: ["source-1"],
    reviewer_decisions: [{ status: "approved", reviewer: "editor-in-chief" }],
    revision_history: [],
    created_at: "2026-05-18T12:00:00Z",
    ...overrides
  };
}

function claim(overrides: Partial<ClaimRecord> = {}): ClaimRecord {
  return {
    claim_id: "claim-1",
    run_id: "run-1",
    claim_text: "Gemma routes expert synthesis.",
    support_status: "supported",
    source_ids: ["source-1"],
    reviewer_agent_id: "claim-verification-agent",
    notes: null,
    ...overrides
  };
}

function feedback(overrides: Partial<FeedbackItem> = {}): FeedbackItem {
  return {
    feedback_id: "feedback-1",
    run_id: "run-1",
    author: "user",
    target_agent_id: "editor-in-chief",
    feedback_text: "Tighten the hook.",
    status: "open",
    metadata: {},
    resolution_notes: null,
    resolved_by: null,
    resolved_at: null,
    created_at: "2026-05-18T12:00:00Z",
    updated_at: "2026-05-18T12:00:00Z",
    ...overrides
  };
}

const acceptedEvidence: SourceEvidenceRecord = {
  source_id: "source-1",
  citation_id: "S1",
  title: "Gemma source",
  url: "https://example.com/gemma",
  accepted_for_context: true
};

test("content readiness is ready when content has source claim review and feedback proof", () => {
  const readiness = buildContentReadinessSnapshot({
    artifacts: [artifact()],
    claims: [claim()],
    feedback: [feedback({ status: "resolved" })],
    sourceEvidence: [acceptedEvidence]
  });

  assert.equal(readiness.status, "ready_for_publish_check");
  assert.equal(readiness.metrics.publishableArtifactCount, 1);
  assert.equal(readiness.metrics.sourceBackedArtifactCount, 1);
  assert.equal(readiness.metrics.claimLinkedArtifactCount, 1);
  assert.equal(readiness.metrics.acceptedContextEvidenceCount, 1);
  assert.deepEqual(readiness.blockers, []);
});

test("content readiness blocks unsupported or ungrounded publishable content", () => {
  const readiness = buildContentReadinessSnapshot({
    artifacts: [
      artifact({
        source_ids: [],
        content: {},
        reviewer_decisions: []
      })
    ],
    claims: [claim({ support_status: "unsupported" })],
    feedback: [feedback({ status: "routed" })],
    sourceEvidence: []
  });

  assert.equal(readiness.status, "blocked");
  assert.equal(readiness.metrics.sourceBackedArtifactCount, 0);
  assert.equal(readiness.metrics.claimLinkedArtifactCount, 0);
  assert.equal(readiness.metrics.unsupportedClaimCount, 1);
  assert.equal(readiness.metrics.openFeedbackCount, 1);
  assert.ok(readiness.nextActions.includes("Run web research and source-ledger repair before packaging."));
  assert.ok(readiness.nextActions.includes("Run claim verification so every major claim maps to evidence."));
});

test("content readiness requires accepted source evidence for publishable content", () => {
  const readiness = buildContentReadinessSnapshot({
    artifacts: [artifact()],
    claims: [claim()],
    feedback: [feedback({ status: "resolved" })],
    sourceEvidence: [
      {
        ...acceptedEvidence,
        accepted_for_context: false
      }
    ]
  });

  assert.equal(readiness.status, "blocked");
  assert.equal(readiness.metrics.sourceBackedArtifactCount, 0);
  assert.ok(
    readiness.nextActions.includes("Run web research and source-ledger repair before packaging.")
  );
});

test("content readiness accepts source evidence linked through artifact ids", () => {
  const readiness = buildContentReadinessSnapshot({
    artifacts: [
      artifact({
        source_ids: []
      })
    ],
    claims: [claim()],
    feedback: [feedback({ status: "resolved" })],
    sourceEvidence: [
      {
        ...acceptedEvidence,
        source_id: "unlinked-source",
        artifact_ids: ["artifact-1"]
      }
    ]
  });

  assert.equal(readiness.status, "ready_for_publish_check");
  assert.equal(readiness.metrics.sourceBackedArtifactCount, 1);
});

test("content readiness detects no publishable content and includes visual briefs", () => {
  const emptyReadiness = buildContentReadinessSnapshot({
    artifacts: [],
    claims: [],
    feedback: []
  });

  assert.equal(emptyReadiness.status, "no_content");
  assert.equal(emptyReadiness.nextActions[0], "Generate source-backed post, reel, and Substack drafts.");
  assert.equal(isPublishableArtifact(artifact({ artifact_type: "visual_brief" })), true);
});
