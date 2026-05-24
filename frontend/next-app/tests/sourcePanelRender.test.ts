import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import {
  claimSupportCounts,
  SourcePanel,
  sourceEvidenceKind,
  sourceEvidenceBySourceId,
  sourceEvidenceSummary,
  sourceLedgerDrilldownSummary,
  sourceRefreshState,
  sourceResearchStatus
} from "../components/sources/SourcePanel";
import type {
  AgentMessage,
  ClaimRecord,
  RunEvent,
  SourceEvidenceRecord,
  SourceRecord
} from "../lib/api/types";

const liveSource: SourceRecord = {
  source_id: "source-live",
  run_id: "run-1",
  citation_id: "S1",
  title: "Inference systems research note",
  url: "https://example.com/inference",
  publisher: "Example Research",
  retrieved_at: "2026-05-18T12:00:00Z",
  published_at: "2026-05-17T12:00:00Z",
  metadata: {
    source_type: "web_search_result",
    snippet: "Latency and batching are core inference engineering tradeoffs.",
    freshness: "current",
    search_rank: 2,
    rerank_rank: 1,
    rerank_score: 0.97,
    reranker: "test_precision_reranker_v1",
    rerank_reason: "official provider documentation beats the broad blog",
    search_query: "inference engineering social content"
  }
};

const seedSource: SourceRecord = {
  source_id: "source-seed",
  run_id: "run-1",
  citation_id: "S2",
  title: "Live web search required",
  url: "https://www.google.com/search?q=inference",
  publisher: "Web search task",
  retrieved_at: "2026-05-18T12:01:00Z",
  published_at: null,
  metadata: {
    source_type: "search_query_seed",
    requires_web_search: true,
    freshness: "current",
    search_query: "inference engineering"
  }
};

const claims: ClaimRecord[] = [
  {
    claim_id: "claim-1",
    run_id: "run-1",
    claim_text: "Inference systems need batching and latency tradeoffs.",
    support_status: "supported",
    source_ids: ["source-live"],
    reviewer_agent_id: "claim-verification-agent",
    notes: null
  },
  {
    claim_id: "claim-2",
    run_id: "run-1",
    claim_text: "Fresh source review is still required.",
    support_status: "needs_review",
    source_ids: ["source-seed"],
    reviewer_agent_id: "claim-verification-agent",
    notes: null
  }
];

const blockedResearchMessage: AgentMessage = {
  message_id: "message-1",
  run_id: "run-1",
  sender_agent_id: "source-ledger-agent",
  recipient_agent_id: "web-research-agent",
  task_type: "research_topic",
  payload: {},
  depends_on_message_ids: [],
  requires_human_feedback: false,
  status: "completed",
  attempt_count: 0,
  max_attempts: 3,
  result: {
    generation_mode: "web_search_provider_blocked",
    web_research: {
      status: "blocked",
      reason: "TAVILY_API_KEY is not configured.",
      accepted_source_count: 0
    }
  },
  created_at: "2026-05-18T12:00:00Z",
  updated_at: "2026-05-18T12:02:00Z"
};

const completedResearchEvent: RunEvent = {
  event_id: 42,
  run_id: "run-1",
  event_type: "web_research_completed",
  actor: "web-research-agent",
  payload: {
    accepted_source_count: 2
  },
  created_at: "2026-05-18T12:03:00Z"
};

const sourceEvidence: SourceEvidenceRecord[] = [
  {
    source_id: "source-live",
    citation_id: "S1",
    accepted_for_context: true,
    retrieval_rank: 1,
    retrieval_rerank_score: 0.92,
    retrieval_reranker: "test_reranker",
    retrieval_rerank_reason: "Highest precision source for the draft claim.",
    retrieval_precision_risks: [],
    retrieval_recall_risks: ["missing throughput benchmark coverage"],
    retrieval_coverage_topics: ["latency", "batching"],
    quality_status: "usable",
    freshness_status: "current",
    claim_ids: ["claim-1"],
    artifact_ids: ["artifact-1"]
  },
  {
    source_id: "source-seed",
    citation_id: "S2",
    accepted_for_context: false,
    retrieval_rank: 2,
    retrieval_rerank_score: 0.21,
    retrieval_reranker: "test_reranker",
    retrieval_rerank_reason: "Search seed is not evidence until provider-backed research runs.",
    retrieval_precision_risks: ["search seed is not source evidence"],
    retrieval_recall_risks: [],
    retrieval_coverage_topics: ["freshness gap"],
    quality_status: "weak",
    freshness_status: "current",
    quality_flags: ["requires live provider research"],
    claim_ids: ["claim-2"],
    artifact_ids: []
  }
];

test("source evidence helpers expose live search and seed fallback provenance", () => {
  assert.equal(
    sourceEvidenceSummary(liveSource),
    "Latency and batching are core inference engineering tradeoffs."
  );
  assert.match(sourceEvidenceSummary(seedSource), /needs to replace this search seed/);
  assert.deepEqual(claimSupportCounts(claims), {
    supported: 1,
    needsReview: 1,
    unsupported: 0
  });
  assert.deepEqual(sourceRefreshState([liveSource, seedSource]), {
    liveSearchCount: 1,
    searchSeedCount: 1
  });
  assert.deepEqual(
    sourceRefreshState(
      [
        {
          ...liveSource,
          metadata: {
            ...liveSource.metadata,
            source_type: "worker_web_search_result",
            search_query: "inference engineering"
          }
        },
        seedSource
      ],
      [{ ...claims[0], source_ids: ["source-live"] }]
    ),
    {
      liveSearchCount: 1,
      searchSeedCount: 0
    }
  );
  assert.deepEqual(sourceEvidenceKind(liveSource), {
    sourceType: "web_search_result",
    isLiveSearch: true,
    isSearchSeed: false
  });
  assert.deepEqual(sourceEvidenceKind(seedSource), {
    sourceType: "search_query_seed",
    isLiveSearch: false,
    isSearchSeed: true
  });
  assert.match(
    sourceEvidenceSummary({
      ...seedSource,
      metadata: { source_type: "search_query_seed" }
    }),
    /needs to replace this search seed/
  );
  assert.deepEqual(sourceResearchStatus([blockedResearchMessage]), {
    tone: "blocked",
    label: "Research blocked",
    detail: "TAVILY_API_KEY is not configured."
  });
  assert.deepEqual(sourceResearchStatus([], [completedResearchEvent]), {
    tone: "ready",
    label: "Research refreshed",
    detail: "2 provider-backed sources recorded"
  });
  assert.deepEqual(sourceResearchStatus([blockedResearchMessage], [completedResearchEvent]), {
    tone: "ready",
    label: "Research refreshed",
    detail: "2 provider-backed sources recorded"
  });
  assert.deepEqual(
    sourceResearchStatus(
      [{ ...blockedResearchMessage, updated_at: "not-a-timestamp" }],
      [completedResearchEvent]
    ),
    {
      tone: "ready",
      label: "Research refreshed",
      detail: "2 provider-backed sources recorded"
    }
  );
  assert.deepEqual(
    sourceResearchStatus(
      [
        {
          ...blockedResearchMessage,
          status: "in_progress",
          updated_at: "2026-05-18T12:04:00Z"
        }
      ],
      [completedResearchEvent]
    ),
    {
      tone: "running",
      label: "Research queued",
      detail: "in progress by web research agent"
    }
  );
  assert.deepEqual(
    sourceResearchStatus([], [
      completedResearchEvent,
      {
        ...completedResearchEvent,
        event_id: 999,
        event_type: "web_research_blocked",
        created_at: "not-a-timestamp",
        payload: {
          reason: "Malformed stale blocker should not mask completed research."
        }
      }
    ]),
    {
      tone: "ready",
      label: "Research refreshed",
      detail: "2 provider-backed sources recorded"
    }
  );
  assert.deepEqual(
    sourceResearchStatus([], [
      {
        ...completedResearchEvent,
        event_id: 1,
        event_type: "web_research_blocked",
        created_at: "z-malformed-timestamp",
        payload: {
          reason: "Lower event id with malformed timestamp should not win."
        }
      },
      {
        ...completedResearchEvent,
        event_id: 2,
        created_at: "a-malformed-timestamp"
      }
    ]),
    {
      tone: "ready",
      label: "Research refreshed",
      detail: "2 provider-backed sources recorded"
    }
  );
  assert.equal(sourceEvidenceBySourceId(sourceEvidence)["source-live"].accepted_for_context, true);
  assert.deepEqual(sourceLedgerDrilldownSummary(sourceEvidence), {
    evidenceItemCount: 2,
    acceptedCount: 1,
    precisionRiskCount: 1,
    recallRiskCount: 1,
    coverageTopicCount: 3,
    qualityIssueCount: 1
  });
});

test("SourcePanel renders provenance, freshness, snippets, claim counts, and research action", () => {
  const html = renderToStaticMarkup(
    React.createElement(SourcePanel, {
      sources: [liveSource, seedSource],
      claims,
      messages: [blockedResearchMessage],
      onRefreshSources: async () => {}
    })
  );

  assert.match(html, /1 supported/);
  assert.match(html, /1 review/);
  assert.match(html, /0 unsupported/);
  assert.match(html, /1 live source/);
  assert.match(html, /1 search seed/);
  assert.match(html, /Run web research/);
  assert.match(html, /Live web search/);
  assert.match(html, /Search seed/);
  assert.match(html, /Freshness: current/);
  assert.match(html, /Rank: 2/);
  assert.match(html, /Rerank: 1/);
  assert.match(html, /Score: 0.97/);
  assert.match(html, /Reranker: test precision reranker v1/);
  assert.match(html, /official provider documentation beats the broad blog/);
  assert.match(html, /Query: inference engineering social content/);
  assert.match(html, /Latency and batching are core inference engineering tradeoffs/);
  assert.match(html, /Provider-backed web research still needs to replace this search seed before publish/);
  assert.match(html, /Research blocked/);
  assert.match(html, /TAVILY_API_KEY is not configured/);
});

test("SourcePanel renders accepted retrieval evidence drilldown", () => {
  const html = renderToStaticMarkup(
    React.createElement(SourcePanel, {
      sources: [liveSource, seedSource],
      claims,
      sourceEvidence
    })
  );

  assert.match(html, /Accepted evidence coverage/);
  assert.match(html, /1\/2 accepted for context/);
  assert.match(html, /1 precision risks/);
  assert.match(html, /1 recall risks/);
  assert.match(html, /3 coverage topics/);
  assert.match(html, /1 quality issues/);
  assert.match(html, /Accepted for context/);
  assert.match(html, /Not accepted for context/);
  assert.match(html, /Reranker: test reranker/);
  assert.match(html, /Score: 0.92/);
  assert.match(html, /Highest precision source for the draft claim/);
  assert.match(html, /Coverage: latency, batching/);
  assert.match(html, /Quality flag: requires live provider research/);
  assert.match(html, /Precision risk: search seed is not source evidence/);
  assert.match(html, /Recall risk: missing throughput benchmark coverage/);
});

test("SourcePanel labels worker web-search sources as live search and disables refresh while busy", () => {
  const html = renderToStaticMarkup(
    React.createElement(SourcePanel, {
      sources: [
        {
          ...liveSource,
          source_id: "worker-source",
          metadata: {
            ...liveSource.metadata,
            source_type: "worker_web_search_result"
          }
        },
        seedSource
      ],
      claims,
      disabled: true,
      onRefreshSources: async () => {}
    })
  );

  assert.match(html, /1 live source/);
  assert.match(html, /1 search seed/);
  assert.match(html, /Live web search/);
  assert.match(html, /disabled=""/);
});

test("SourcePanel disables source refresh while provider-backed research is already running", () => {
  const html = renderToStaticMarkup(
    React.createElement(SourcePanel, {
      sources: [liveSource, seedSource],
      claims,
      messages: [
        {
          ...blockedResearchMessage,
          status: "in_progress",
          updated_at: "2026-05-18T12:04:00Z"
        }
      ],
      onRefreshSources: async () => {}
    })
  );

  assert.match(html, /Research queued/);
  assert.match(html, /disabled=""/);
});

test("SourcePanel falls back to a non-link title for malformed source URLs", () => {
  const html = renderToStaticMarkup(
    React.createElement(SourcePanel, {
      sources: [
        {
          ...liveSource,
          url: "not a url"
        }
      ],
      claims: []
    })
  );

  assert.match(html, /source-title-fallback/);
  assert.doesNotMatch(html, /href="not a url"/);
});
