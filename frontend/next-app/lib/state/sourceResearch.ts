import type {
  AgentMessage,
  AgentMessageCreate,
  AgentWorkerCycleResult,
  SourceRecord,
  UUID
} from "../api/types";

export const WEB_RESEARCH_AGENT_IDS = ["web-research-agent"] as const;
export const SOURCE_REFRESH_AGENT_IDS = [
  "web-research-agent",
  "claim-verification-agent"
] as const;
export const MAX_SOURCE_REFRESH_SEARCH_QUERIES = 5;
const RUNNABLE_TASK_STATUSES = new Set(["accepted", "claimed", "in_progress"]);
const WEB_RESEARCH_TASK_TYPE = "research_topic";

function metadataString(metadata: Record<string, unknown>, key: string) {
  const value = metadata[key];
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

export function sourceNeedsWebResearch(source: SourceRecord) {
  return (
    source.metadata.requires_web_search === true ||
    metadataString(source.metadata, "source_type") === "search_query_seed"
  );
}

export function buildSourceRefreshCycleInput(runId: UUID) {
  return {
    runId,
    agentIds: [...SOURCE_REFRESH_AGENT_IDS],
    maxTasksPerAgent: 3,
    maxRounds: 2,
    useGemma: false
  };
}

export function hasRunnableWebResearchTask(messages: AgentMessage[]) {
  return messages.some(
    (message) =>
      message.recipient_agent_id === "web-research-agent" &&
      message.task_type === WEB_RESEARCH_TASK_TYPE &&
      RUNNABLE_TASK_STATUSES.has(message.status)
  );
}

export function buildSourceRefreshMessage(
  runId: UUID,
  sources: SourceRecord[],
  fallbackTopic: string
): AgentMessageCreate | null {
  const seedSources = sources.filter(sourceNeedsWebResearch);
  if (seedSources.length === 0) {
    return null;
  }
  const topic =
    seedSources
      .map((source) => metadataString(source.metadata, "search_query"))
      .find(Boolean) ?? fallbackTopic;
  const allSearchQueries = [
    ...new Set(
      seedSources
        .map((source) => metadataString(source.metadata, "search_query"))
        .filter((query): query is string => Boolean(query))
    )
  ];
  const searchQueries = allSearchQueries.slice(0, MAX_SOURCE_REFRESH_SEARCH_QUERIES);
  return {
    run_id: runId,
    sender_agent_id: "source-ledger-agent",
    recipient_agent_id: "web-research-agent",
    task_type: WEB_RESEARCH_TASK_TYPE,
    requires_human_feedback: false,
    payload: {
      workflow: "source_panel_web_research_refresh_v1",
      topic,
      reason: "replace_search_seed_sources",
      source_ids: seedSources.map((source) => source.source_id),
      search_queries: searchQueries,
      skipped_search_query_count: Math.max(0, allSearchQueries.length - searchQueries.length)
    }
  };
}

export function sourceRefreshActivitySummary(cycle: AgentWorkerCycleResult) {
  const processedTasks = cycle.worker_results.flatMap((result) => result.processed_tasks);
  const webResearchRan = processedTasks.some((task) => task.task_type === WEB_RESEARCH_TASK_TYPE);
  const claimVerificationRan = processedTasks.some(
    (task) => task.generation_mode === "claim_verification_worker"
  );
  if (processedTasks.some((task) => task.generation_mode === "web_search_provider_blocked")) {
    return claimVerificationRan
      ? `Web research blocked; claims rechecked against existing sources. ${cycle.summary}`
      : `Web research blocked. ${cycle.summary}`;
  }
  if (processedTasks.some((task) => task.generation_mode === "web_search_provider")) {
    return claimVerificationRan
      ? `Ran provider-backed web research and claim verification. ${cycle.summary}`
      : `Ran provider-backed web research. ${cycle.summary}`;
  }
  if (webResearchRan) {
    return `Processed web research task. ${cycle.summary}`;
  }
  if (claimVerificationRan) {
    return `Processed claim verification task. ${cycle.summary}`;
  }
  if (cycle.total_processed_tasks > 0) {
    return `Processed source-refresh worker cycle. ${cycle.summary}`;
  }
  return "No pending web research task needed work.";
}
