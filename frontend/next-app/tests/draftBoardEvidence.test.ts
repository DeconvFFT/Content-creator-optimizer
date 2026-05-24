import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import {
  claimsLinkedToArtifact,
  DraftBoard,
  draftEvidenceSummary,
  draftBoardFilterForArtifact,
  filterArtifactsForDraftBoard,
  growthStrategySummary,
  isContentArtifact,
  providerRecoverySummary,
  voiceSetupProofSummary
} from "../components/drafts/DraftBoard";
import type { ArtifactRecord, ClaimRecord } from "../lib/api/types";
import { ARTIFACT_JUMP_EVENT, artifactIdFromHash } from "../lib/state/artifactAnchors";

const activityPanelSource = readFileSync("components/run/ActivityPanel.tsx", "utf8");
const draftBoardSource = readFileSync("components/drafts/DraftBoard.tsx", "utf8");
const pageSource = readFileSync("app/page.tsx", "utf8");

const artifact: ArtifactRecord = {
  artifact_id: "artifact-1",
  run_id: "run-1",
  artifact_type: "post",
  title: "Inference engineering post",
  uri: "artifact://runs/run-1/post",
  content: {
    body: "Inference engineering turns models into reliable products.",
    claim_ids: ["claim-supported", "claim-review"]
  },
  provenance: {
    workflow: "content_workflow_v1",
    claim_ids: ["claim-supported", "claim-review"]
  },
  source_ids: ["source-live", "source-seed"],
  reviewer_decisions: [
    {
      reviewer_agent_id: "guardrails-agent",
      decision: "needs_revision",
      reason: "Claim review and source ledger inspection are still required."
    }
  ],
  revision_history: [
    {
      actor: "content-strategist",
      note: "Created first durable draft."
    }
  ],
  created_at: "2026-05-18T12:00:00Z"
};

const claims: ClaimRecord[] = [
  {
    claim_id: "claim-supported",
    run_id: "run-1",
    claim_text: "Inference engineering connects latency, throughput, and reliability.",
    support_status: "supported",
    source_ids: ["source-live"],
    reviewer_agent_id: "claim-verification-agent",
    notes: null
  },
  {
    claim_id: "claim-review",
    run_id: "run-1",
    claim_text: "A search seed still needs live provider-backed research.",
    support_status: "needs_review",
    source_ids: ["source-live", "source-seed"],
    reviewer_agent_id: "claim-verification-agent",
    notes: null
  },
  {
    claim_id: "claim-shared-source-not-artifact",
    run_id: "run-1",
    claim_text: "This claim shares a source but is not in the draft claim trace.",
    support_status: "unsupported",
    source_ids: ["source-live"],
    reviewer_agent_id: "claim-verification-agent",
    notes: null
  },
  {
    claim_id: "claim-other",
    run_id: "run-1",
    claim_text: "This claim belongs to another source.",
    support_status: "unsupported",
    source_ids: ["source-other"],
    reviewer_agent_id: "claim-verification-agent",
    notes: null
  }
];

const voiceSetupProofArtifact: ArtifactRecord = {
  artifact_id: "voice-proof-1",
  run_id: "run-1",
  artifact_type: "voice_setup_proof",
  title: "Voice setup proof: check_setup",
  uri: "artifact://runs/run-1/voice-setup-proof/voice-proof-1",
  content: {
    workflow: "voice_setup_proof_v1",
    action: "check_setup",
    status: "blocked",
    summary: "Voice setup check recorded: LiveKit transport needs attention.",
    provider: "openrouter_livekit",
    transport_framework: "livekit",
    readiness_status: "blocked",
    livekit_process_status: "stopped",
    voice_agent_process_status: "stopped",
    primary_blocker: {
      id: "LiveKit transport",
      label: "LiveKit transport",
      status: "blocked",
      detail: "Local LiveKit dev server is stopped.",
      next_action: "Start LiveKit transport",
      required: true
    },
    steps: [
      {
        id: "Content run",
        label: "Content run",
        status: "ready",
        detail: "Run run-1 is active.",
        required: true
      },
      {
        id: "LiveKit transport",
        label: "LiveKit transport",
        status: "blocked",
        detail: "Local LiveKit dev server is stopped.",
        required: true
      }
    ]
  },
  provenance: {
    workflow: "voice_setup_proof_v1"
  },
  source_ids: [],
  reviewer_decisions: [],
  revision_history: [],
  created_at: "2026-05-18T13:00:00Z"
};

const providerRecoveryArtifact: ArtifactRecord = {
  artifact_id: "provider-recovery-1",
  run_id: "run-1",
  artifact_type: "provider_operations_ledger",
  title: "Realtime provider failure recovery plan",
  uri: "artifact://runs/run-1/provider-failure-recovery/message-1",
  content: {
    format: "realtime_provider_failure_recovery",
    status: "blocked_until_realtime_provider_recheck",
    provider: "gemma4_realtime",
    transport_framework: "livekit",
    failure: {
      stage: "gemma_generation",
      reason: "Gemma stream failed for Bearer [redacted].",
      component: "gemma_audio_reasoner"
    },
    recovery_checks: [
      {
        id: "runtime_preflight",
        owner_agent_id: "observability-agent",
        status: "required",
        detail: "Refresh runtime readiness."
      },
      {
        id: "gemma_streaming_route",
        owner_agent_id: "inference-systems-engineer",
        status: "required",
        detail: "Verify Gemma streaming route."
      }
    ],
    required_actions: [
      "Run Runtime preflight before another provider-backed voice turn.",
      "Run session-bound provider smoke."
    ],
    fallback_policy: {
      blocked: [
        "openai_realtime_fallback",
        "fake_assistant_voice_turns"
      ]
    }
  },
  provenance: {
    workflow: "realtime_provider_failure_recovery_worker_v1"
  },
  source_ids: [],
  reviewer_decisions: [
    {
      reviewer_agent_id: "inference-systems-engineer",
      decision: "blocked"
    }
  ],
  revision_history: [],
  created_at: "2026-05-18T14:00:00Z"
};

const providerConfigurationRecoveryArtifact: ArtifactRecord = {
  artifact_id: "provider-config-recovery-1",
  run_id: "run-1",
  artifact_type: "provider_operations_ledger",
  title: "Provider configuration recovery plan",
  uri: "artifact://runs/run-1/provider-configuration-recovery/message-1",
  content: {
    format: "provider_configuration_recovery",
    status: "blocked_until_provider_configuration_recheck",
    provider_smoke_status: "blocked",
    blocked_step_count: 2,
    blocked_steps: [
      {
        step_id: "selected-realtime-smoke",
        provider_id: "gemma4-realtime",
        provider_type: "realtime_audio",
        title: "Create selected realtime audio session",
        blockers: ["Missing LIVEKIT_API_SECRET for Bearer [redacted]."]
      },
      {
        step_id: "selected-web-search-smoke",
        provider_id: "tavily-search",
        provider_type: "web_search",
        title: "Run selected web-search grounding smoke",
        blockers: ["Missing TAVILY_API_KEY_FILE."]
      }
    ],
    recovery_checks: [
      {
        id: "selected-realtime-smoke_configuration",
        owner_agent_id: "inference-systems-engineer",
        status: "blocked"
      },
      {
        id: "selected-web-search-smoke_configuration",
        owner_agent_id: "agent-harness-engineer",
        status: "blocked"
      },
      {
        id: "selected-web-search-smoke_source_grounding_recheck",
        owner_agent_id: "web-research-agent",
        status: "required_after_configuration"
      }
    ],
    required_actions: [
      "Repair missing provider configuration outside durable artifacts.",
      "Rerun provider smoke after configuration is repaired."
    ],
    fallback_policy: {
      blocked: [
        "persist_provider_secret_values",
        "count_provider_free_rehearsal_as_provider_backed_smoke"
      ]
    }
  },
  provenance: {
    workflow: "provider_configuration_recovery_worker_v1"
  },
  source_ids: [],
  reviewer_decisions: [
    {
      reviewer_agent_id: "inference-systems-engineer",
      decision: "blocked"
    }
  ],
  revision_history: [],
  created_at: "2026-05-19T10:00:00Z"
};

const growthStrategyArtifact: ArtifactRecord = {
  artifact_id: "growth-strategy-1",
  run_id: "run-1",
  artifact_type: "growth_strategy",
  title: "Influencer strategy: inference engineering",
  uri: "artifact://runs/run-1/growth-strategies/growth-strategy-1",
  content: {
    workflow: "influencer_strategy_v1",
    topic: "inference engineering",
    audience_segments: [
      {
        segment: "AI-curious beginners",
        promise: "Explain inference engineering without jargon."
      },
      {
        segment: "builders and operators",
        promise: "Show the workflow and caveats."
      }
    ],
    hashtag_strategy: {
      primary: ["#AI", "#LLMs", "#AIAgents"]
    },
    keyword_strategy: {
      primary: ["source-backed AI", "inference engineering"]
    },
    creator_packaging: {
      hook_angles: [
        {
          platform: "instagram_reel",
          hook: "Inference engineering explained before claims outrun sources."
        }
      ]
    },
    do_not_say: ["Do not imply unsupported claims are proven."],
    source_ids: ["source-live"],
    claim_ids: ["claim-supported"]
  },
  provenance: {
    workflow: "influencer_strategy_v1",
    created_by_agent_id: "influencer-strategy-agent"
  },
  source_ids: ["source-live"],
  reviewer_decisions: [
    {
      reviewer_agent_id: "editor-in-chief",
      status: "needs_revision"
    }
  ],
  revision_history: [],
  created_at: "2026-05-18T15:00:00Z"
};

test("draft evidence helpers deduplicate linked claims and classify review risk", () => {
  const claimsBySource = claims.reduce<Record<string, ClaimRecord[]>>((index, claim) => {
    claim.source_ids.forEach((sourceId) => {
      index[sourceId] = [...(index[sourceId] ?? []), claim];
    });
    return index;
  }, {});
  const linkedClaims = claimsLinkedToArtifact(artifact, claims, claimsBySource);
  const summary = draftEvidenceSummary(artifact, linkedClaims);

  assert.deepEqual(
    linkedClaims.map((claim) => claim.claim_id),
    ["claim-supported", "claim-review"]
  );
  assert.deepEqual(summary, {
    sourceCount: 2,
    linkedClaimCount: 2,
    supported: 1,
    needsReview: 1,
    unsupported: 0,
    revisionCount: 1,
    reviewerDecision: "needs revision",
    tone: "review"
  });
});

test("DraftBoard renders source, claim, reviewer, and revision evidence per draft", () => {
  const html = renderToStaticMarkup(
    React.createElement(DraftBoard, {
      artifacts: [artifact],
      claims,
      feedback: [],
      selectedArtifactIds: [],
      onToggleArtifact: () => {},
      onRevise: async () => {},
      onResolveFeedback: async () => {}
    })
  );

  assert.match(html, /Draft evidence summary/);
  assert.match(html, /id="artifact-artifact-1"/);
  assert.match(html, /2 sources/);
  assert.match(html, /1 supported/);
  assert.match(html, /1 review/);
  assert.match(html, /0 unsupported/);
  assert.match(html, /Reviewer: needs revision/);
  assert.match(html, /1 revisions/);
  assert.doesNotMatch(html, /claim-shared-source-not-artifact/);
  assert.doesNotMatch(html, /claim-other/);
});

test("artifact board defaults to creator content instead of operational proof", () => {
  assert.equal(isContentArtifact(artifact), true);
  assert.equal(isContentArtifact(voiceSetupProofArtifact), false);
  assert.equal(isContentArtifact(providerRecoveryArtifact), false);
  assert.equal(draftBoardFilterForArtifact(artifact), "content");
  assert.equal(draftBoardFilterForArtifact(voiceSetupProofArtifact), "proofs");
  assert.deepEqual(
    filterArtifactsForDraftBoard(
      [artifact, voiceSetupProofArtifact, providerRecoveryArtifact],
      "content"
    ).map(
      (item) => item.artifact_id
    ),
    ["artifact-1"]
  );
  assert.deepEqual(
    filterArtifactsForDraftBoard(
      [artifact, voiceSetupProofArtifact, providerRecoveryArtifact],
      "proofs"
    ).map(
      (item) => item.artifact_id
    ),
    ["voice-proof-1", "provider-recovery-1"]
  );

  const html = renderToStaticMarkup(
    React.createElement(DraftBoard, {
      artifacts: [artifact, voiceSetupProofArtifact, providerRecoveryArtifact],
      claims,
      feedback: [],
      selectedArtifactIds: [],
      onToggleArtifact: () => {},
      onRevise: async () => {},
      onResolveFeedback: async () => {}
    })
  );

  assert.match(html, /1 of 3 artifacts/);
  assert.match(html, /Inference engineering post/);
  assert.doesNotMatch(html, /Voice setup proof summary/);
  assert.doesNotMatch(html, /Provider recovery proof summary/);
});

test("artifact anchor helpers recover same-hash artifact jumps", () => {
  assert.equal(artifactIdFromHash("#artifact-artifact-1"), "artifact-1");
  assert.equal(artifactIdFromHash("#artifact-%E0%A4%A"), null);
  assert.match(activityPanelSource, /dispatchArtifactJump\(artifact\.artifact_id\)/);
  assert.equal(ARTIFACT_JUMP_EVENT, "agentstudio:artifact-jump");
  assert.match(draftBoardSource, /addEventListener\(ARTIFACT_JUMP_EVENT/);
  assert.match(draftBoardSource, /setFilter\(draftBoardFilterForArtifact\(targetArtifact\)\)/);
});

test("DraftBoard renders growth strategies as creator strategy artifacts", () => {
  const summary = growthStrategySummary(growthStrategyArtifact);
  assert.equal(summary?.workflow, "influencer strategy");
  assert.equal(summary?.topic, "inference engineering");
  assert.equal(summary?.audienceSegmentCount, 2);
  assert.equal(
    summary?.primaryTerms.join(", "),
    "#AI, #LLMs, #AIAgents, source-backed AI"
  );
  assert.equal(isContentArtifact(growthStrategyArtifact), false);
  assert.deepEqual(
    filterArtifactsForDraftBoard([artifact, growthStrategyArtifact], "growth_strategy").map(
      (item) => item.artifact_id
    ),
    ["growth-strategy-1"]
  );

  const html = renderToStaticMarkup(
    React.createElement(DraftBoard, {
      artifacts: [growthStrategyArtifact],
      claims,
      feedback: [],
      selectedArtifactIds: [],
      onToggleArtifact: () => {},
      onRevise: async () => {},
      onResolveFeedback: async () => {}
    })
  );

  assert.match(html, /Growth strategy summary/);
  assert.match(html, /influencer strategy/);
  assert.match(html, /2 audience segments/);
  assert.match(html, /#AI, #LLMs, #AIAgents/);
  assert.match(html, /Growth strategy/);
  assert.doesNotMatch(html, /Operational proof/);
  assert.doesNotMatch(html, /&quot;workflow&quot;/);
  assert.doesNotMatch(html, />Revise</);
});


test("draft evidence falls back to source-related claims when explicit claim ids are missing", () => {
  const claimsBySource = claims.reduce<Record<string, ClaimRecord[]>>((index, claim) => {
    claim.source_ids.forEach((sourceId) => {
      index[sourceId] = [...(index[sourceId] ?? []), claim];
    });
    return index;
  }, {});
  const fallbackArtifact: ArtifactRecord = {
    ...artifact,
    content: { body: "Legacy draft without explicit claim ids." },
    provenance: { workflow: "legacy_content_workflow" }
  };

  assert.deepEqual(
    claimsLinkedToArtifact(fallbackArtifact, claims, claimsBySource).map((claim) => claim.claim_id),
    ["claim-supported", "claim-review", "claim-shared-source-not-artifact"]
  );
});

test("DraftBoard renders voice setup proof as compact operational evidence", () => {
  const summary = voiceSetupProofSummary(voiceSetupProofArtifact);
  assert.equal(summary?.primaryBlockerLabel, "LiveKit transport");
  assert.equal(summary?.liveKitProcessStatus, "stopped");

  const html = renderToStaticMarkup(
    React.createElement(DraftBoard, {
      artifacts: [voiceSetupProofArtifact],
      claims: [],
      feedback: [],
      selectedArtifactIds: [],
      onToggleArtifact: () => {},
      onRevise: async () => {},
      onResolveFeedback: async () => {}
    })
  );

  assert.match(html, /Voice setup proof summary/);
  assert.match(html, /Status: blocked/);
  assert.match(html, /Provider: openrouter livekit/);
  assert.match(html, /LiveKit transport/);
  assert.match(html, /Local LiveKit dev server is stopped/);
  assert.match(html, /Runtime readiness: blocked/);
  assert.match(html, /OpenRouter\/Kokoro agent: stopped/);
  assert.match(html, /2 checklist steps captured/);
  assert.match(html, /Operational proof/);
  assert.doesNotMatch(html, /&quot;workflow&quot;/);
  assert.doesNotMatch(html, /type="checkbox"/);
  assert.doesNotMatch(html, />Revise</);
});

test("voice setup proof fallback copy does not claim failed setup passed", () => {
  const failedProof: ArtifactRecord = {
    ...voiceSetupProofArtifact,
    content: {
      workflow: "voice_setup_proof_v1",
      action: "check_setup",
      status: "failed",
      summary: "Voice setup check failed: readiness API timeout.",
      provider: "gemma4_realtime"
    }
  };

  const summary = voiceSetupProofSummary(failedProof);
  assert.equal(summary?.status, "failed");
  assert.equal(summary?.primaryBlockerLabel, "Setup proof failed");
  assert.equal(
    summary?.primaryBlockerDetail,
    "The setup attempt failed before a blocker snapshot was captured."
  );
  assert.notEqual(summary?.primaryBlockerDetail, "All required setup checks passed.");
});

test("DraftBoard renders provider recovery proof as compact operational evidence", () => {
  const summary = providerRecoverySummary(providerRecoveryArtifact);
  assert.equal(summary?.failedComponent, "gemma audio reasoner");
  assert.equal(summary?.checkCount, 2);
  assert.deepEqual(summary?.ownerAgents, [
    "observability-agent",
    "inference-systems-engineer"
  ]);

  const html = renderToStaticMarkup(
    React.createElement(DraftBoard, {
      artifacts: [providerRecoveryArtifact],
      claims: [],
      feedback: [],
      selectedArtifactIds: [],
      onToggleArtifact: () => {},
      onRevise: async () => {},
      onResolveFeedback: async () => {}
    })
  );

  assert.match(html, /Provider recovery proof summary/);
  assert.match(html, /Status: blocked until realtime provider recheck/);
  assert.match(html, /Component: gemma audio reasoner/);
  assert.match(html, /Provider: gemma4 realtime/);
  assert.match(html, /Transport: livekit/);
  assert.match(html, /Gemma stream failed for Bearer \[redacted\]/);
  assert.match(html, /2 recovery checks/);
  assert.match(html, /2 required actions/);
  assert.match(html, /Owners: observability-agent, inference-systems-engineer/);
  assert.match(html, /Blocked fallback: openai realtime fallback/);
  assert.match(html, /Operational proof/);
  assert.doesNotMatch(html, /&quot;workflow&quot;/);
  assert.doesNotMatch(html, /type="checkbox"/);
  assert.doesNotMatch(html, />Revise</);
});

test("DraftBoard renders provider configuration recovery proof as compact operational evidence", () => {
  const summary = providerRecoverySummary(providerConfigurationRecoveryArtifact);
  assert.equal(summary?.failedComponent, "provider configuration");
  assert.equal(summary?.failureStage, "configuration recheck required");
  assert.equal(
    summary?.failureReason,
    "Missing LIVEKIT_API_SECRET for Bearer [redacted]."
  );
  assert.equal(summary?.provider, "gemma4 realtime, tavily search");
  assert.equal(summary?.transportFramework, "provider smoke");
  assert.deepEqual(summary?.ownerAgents, [
    "inference-systems-engineer",
    "agent-harness-engineer",
    "web-research-agent"
  ]);

  const html = renderToStaticMarkup(
    React.createElement(DraftBoard, {
      artifacts: [providerConfigurationRecoveryArtifact],
      claims: [],
      feedback: [],
      selectedArtifactIds: [],
      onToggleArtifact: () => {},
      onRevise: async () => {},
      onResolveFeedback: async () => {}
    })
  );

  assert.match(html, /Provider recovery proof summary/);
  assert.match(html, /Status: blocked until provider configuration recheck/);
  assert.match(html, /Component: provider configuration/);
  assert.match(html, /Provider: gemma4 realtime, tavily search/);
  assert.match(html, /Transport: provider smoke/);
  assert.match(html, /Missing LIVEKIT_API_SECRET for Bearer \[redacted\]/);
  assert.match(html, /3 recovery checks/);
  assert.match(html, /2 required actions/);
  assert.match(
    html,
    /Owners: inference-systems-engineer, agent-harness-engineer, web-research-agent/
  );
  assert.match(html, /Blocked fallback: persist provider secret values/);
  assert.match(html, /Operational proof/);
  assert.doesNotMatch(html, /&quot;workflow&quot;/);
  assert.doesNotMatch(html, /type="checkbox"/);
  assert.doesNotMatch(html, />Revise</);
});

test("non-content artifacts are browseable but not revision targets", () => {
  const sourceLedger: ArtifactRecord = {
    ...voiceSetupProofArtifact,
    artifact_id: "source-ledger-1",
    artifact_type: "source_ledger",
    title: "Source ledger",
    content: {
      summary: "Source ledger proof",
      status: "needs_review"
    },
    provenance: {
      workflow: "source_ledger_snapshot_v1"
    }
  };

  const html = renderToStaticMarkup(
    React.createElement(DraftBoard, {
      artifacts: [sourceLedger],
      claims: [],
      feedback: [],
      selectedArtifactIds: ["source-ledger-1"],
      onToggleArtifact: () => {},
      onRevise: async () => {},
      onResolveFeedback: async () => {}
    })
  );

  assert.match(html, /Source ledger/);
  assert.match(html, /Operational proof/);
  assert.match(html, />Copy</);
  assert.match(html, />Export</);
  assert.doesNotMatch(html, /type="checkbox"/);
  assert.doesNotMatch(html, />Revise</);
  assert.doesNotMatch(html, /linked claims/);
  assert.match(html, /0 selected/);
});

test("DraftBoard disables revision feedback while the app is busy", () => {
  const html = renderToStaticMarkup(
    React.createElement(DraftBoard, {
      artifacts: [artifact],
      claims,
      feedback: [],
      selectedArtifactIds: ["artifact-1"],
      busy: true,
      onToggleArtifact: () => {},
      onRevise: async () => {},
      onResolveFeedback: async () => {}
    })
  );

  assert.match(html, /<textarea[^>]*disabled=""/);
  assert.match(html, />Working</);
});

test("feedback actions use a synchronous single-flight gate before async work", () => {
  assert.match(pageSource, /const feedbackActionGateRef = useRef\(\{ inFlight: false, token: 0 \}\);/);
  for (const handlerName of ["handleRevise", "handleResolveFeedback"]) {
    const handlerIndex = pageSource.indexOf(`async function ${handlerName}(`);
    const nextHandlerIndex = pageSource.indexOf("async function ", handlerIndex + 1);
    const handlerSource = pageSource.slice(
      handlerIndex,
      nextHandlerIndex === -1 ? undefined : nextHandlerIndex
    );

    assert.notEqual(handlerIndex, -1);
    assert.match(handlerSource, /beginRunAction\(feedbackActionGateRef\.current\)/);
    assert.match(handlerSource, /isRunVersionedActionCurrent\(/);
    assert.match(handlerSource, /finishRunAction\(feedbackActionGateRef\.current, feedbackToken\)/);
  }
  assert.match(pageSource, /invalidateRunAction\(feedbackActionGateRef\.current\)/);
});
