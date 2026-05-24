import assert from "node:assert/strict";
import test from "node:test";

import {
  buildSourceRefreshMessage,
  buildSourceRefreshCycleInput,
  hasRunnableWebResearchTask,
  MAX_SOURCE_REFRESH_SEARCH_QUERIES,
  SOURCE_REFRESH_AGENT_IDS,
  sourceRefreshActivitySummary,
  sourceNeedsWebResearch,
  WEB_RESEARCH_AGENT_IDS
} from "../lib/state/sourceResearch";
import type { AgentMessage, SourceRecord } from "../lib/api/types";

test("source refresh runs Web Research then Claim Verification without Gemma fallback", () => {
  assert.deepEqual(WEB_RESEARCH_AGENT_IDS, ["web-research-agent"]);
  assert.deepEqual(SOURCE_REFRESH_AGENT_IDS, [
    "web-research-agent",
    "claim-verification-agent"
  ]);
  assert.deepEqual(buildSourceRefreshCycleInput("run-1"), {
    runId: "run-1",
    agentIds: ["web-research-agent", "claim-verification-agent"],
    maxTasksPerAgent: 3,
    maxRounds: 2,
    useGemma: false
  });
});

test("source refresh creates a targeted web research task for visible search seeds", () => {
  const seedSource = {
    source_id: "seed-source",
    run_id: "run-1",
    citation_id: "S1",
    title: "Search seed",
    url: "https://www.google.com/search?q=inference",
    publisher: "Web search task",
    retrieved_at: "2026-05-18T12:00:00Z",
    published_at: null,
    metadata: {
      source_type: "search_query_seed",
      search_query: "inference engineering"
    }
  } satisfies SourceRecord;

  assert.equal(sourceNeedsWebResearch(seedSource), true);
  const message = buildSourceRefreshMessage(
    "run-1",
    [seedSource],
    "fallback topic"
  );

  assert.equal(message?.recipient_agent_id, "web-research-agent");
  assert.equal(message?.task_type, "research_topic");
  assert.equal(message?.payload?.topic, "inference engineering");
  assert.deepEqual(message?.payload?.source_ids, ["seed-source"]);
  assert.deepEqual(message?.payload?.search_queries, ["inference engineering"]);
  assert.equal(message?.payload?.workflow, "source_panel_web_research_refresh_v1");

  const duplicateQueryMessage = buildSourceRefreshMessage(
    "run-1",
    [
      seedSource,
      {
        ...seedSource,
        source_id: "seed-source-2",
        citation_id: "S2"
      }
    ],
    "fallback topic"
  );
  assert.deepEqual(duplicateQueryMessage?.payload?.search_queries, [
    "inference engineering"
  ]);

  const manyQueriesMessage = buildSourceRefreshMessage(
    "run-1",
    Array.from({ length: MAX_SOURCE_REFRESH_SEARCH_QUERIES + 2 }, (_, index) => ({
      ...seedSource,
      source_id: `seed-source-${index}`,
      citation_id: `S${index + 1}`,
      metadata: {
        ...seedSource.metadata,
        search_query: `query ${index}`
      }
    })),
    "fallback topic"
  );
  assert.deepEqual(manyQueriesMessage?.payload?.search_queries, [
    "query 0",
    "query 1",
    "query 2",
    "query 3",
    "query 4"
  ]);
  assert.equal(manyQueriesMessage?.payload?.skipped_search_query_count, 2);
});

test("source refresh detects existing runnable web research tasks", () => {
  const baseMessage: AgentMessage = {
    message_id: "message-1",
    run_id: "run-1",
    sender_agent_id: "source-ledger-agent",
    recipient_agent_id: "web-research-agent",
    task_type: "research_topic",
    payload: {},
    depends_on_message_ids: [],
    requires_human_feedback: false,
    status: "accepted",
    attempt_count: 0,
    max_attempts: 3,
    result: {},
    created_at: "2026-05-18T12:00:00Z",
    updated_at: "2026-05-18T12:00:00Z"
  };

  assert.equal(hasRunnableWebResearchTask([baseMessage]), true);
  assert.equal(hasRunnableWebResearchTask([{ ...baseMessage, status: "claimed" }]), true);
  assert.equal(hasRunnableWebResearchTask([{ ...baseMessage, status: "in_progress" }]), true);
  assert.equal(hasRunnableWebResearchTask([{ ...baseMessage, status: "completed" }]), false);
  assert.equal(hasRunnableWebResearchTask([{ ...baseMessage, status: "failed" }]), false);
  assert.equal(hasRunnableWebResearchTask([{ ...baseMessage, status: "blocked" }]), false);
  assert.equal(
    hasRunnableWebResearchTask([{ ...baseMessage, status: "waiting_for_human" }]),
    false
  );
  assert.equal(
    hasRunnableWebResearchTask([
      { ...baseMessage, recipient_agent_id: "claim-verification-agent" }
    ]),
    false
  );
  assert.equal(hasRunnableWebResearchTask([{ ...baseMessage, task_type: "draft_review" }]), false);
});

test("source refresh activity summary distinguishes blocked and completed provider research", () => {
  const baseCycle = {
    run_id: "run-1",
    agent_ids: ["web-research-agent", "claim-verification-agent"],
    rounds_completed: 1,
    worker_results: [
      {
        run_id: "run-1",
        agent_id: "web-research-agent",
        recovered_stale_tasks: 0,
        blocked_exhausted_tasks: 0,
        dependency_blocked_tasks: 0,
        idle: false,
        summary: "Web Research Agent processed 1 task(s): 1 completed, 0 failed.",
        processed_tasks: [
          {
            message_id: "message-1",
            task_type: "research_topic",
            status: "completed",
            generation_mode: "web_search_provider_blocked",
            summary: "Provider-backed web research is blocked."
          },
          {
            message_id: "message-2",
            task_type: "verify_source_refresh_claims",
            status: "completed",
            generation_mode: "claim_verification_worker",
            summary: "Claim verification completed."
          }
        ]
      }
    ],
    total_processed_tasks: 2,
    idle: false,
    summary: "Worker cycle ran 1 round(s) across 2 agent(s) and processed 2 task(s)."
  };

  assert.match(
    sourceRefreshActivitySummary(baseCycle),
    /^Web research blocked; claims rechecked/
  );
  assert.match(
    sourceRefreshActivitySummary({
      ...baseCycle,
      worker_results: [
        {
          ...baseCycle.worker_results[0],
          processed_tasks: [
            {
              ...baseCycle.worker_results[0].processed_tasks[0],
              generation_mode: "web_search_provider"
            },
            {
              ...baseCycle.worker_results[0].processed_tasks[1],
              generation_mode: "claim_verification_worker"
            }
          ]
        }
      ]
    }),
    /^Ran provider-backed web research and claim verification\./
  );
  assert.match(
    sourceRefreshActivitySummary({
      ...baseCycle,
      worker_results: [
        {
          ...baseCycle.worker_results[0],
          agent_id: "claim-verification-agent",
          processed_tasks: [
            {
              ...baseCycle.worker_results[0].processed_tasks[1],
              generation_mode: "claim_verification_worker"
            }
          ]
        }
      ],
      total_processed_tasks: 1
    }),
    /^Processed claim verification task\./
  );
});
