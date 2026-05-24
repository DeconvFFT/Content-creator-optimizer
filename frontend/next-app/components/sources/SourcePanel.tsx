import { useMemo } from "react";
import {
  AlertCircle,
  CalendarClock,
  ExternalLink,
  RefreshCw,
  Search,
  ShieldCheck,
  ShieldQuestion,
  ShieldX,
  Target
} from "lucide-react";
import type {
  AgentMessage,
  ClaimRecord,
  RunEvent,
  SourceEvidenceRecord,
  SourceRecord
} from "../../lib/api/types";
import { compactId, formatDateTime, statusLabel } from "../../lib/state/format";
import { sourceNeedsWebResearch } from "../../lib/state/sourceResearch";

type SourcePanelProps = {
  sources: SourceRecord[];
  claims: ClaimRecord[];
  messages?: AgentMessage[];
  events?: RunEvent[];
  sourceEvidence?: SourceEvidenceRecord[];
  disabled?: boolean;
  onRefreshSources?: () => Promise<void>;
};

type SourceResearchStatus = {
  tone: "blocked" | "ready" | "running";
  label: string;
  detail: string;
};

export type SourceLedgerDrilldownSummary = {
  evidenceItemCount: number;
  acceptedCount: number;
  precisionRiskCount: number;
  recallRiskCount: number;
  coverageTopicCount: number;
  qualityIssueCount: number;
};

const WEB_RESEARCH_AGENT_ID = "web-research-agent";
const WEB_RESEARCH_TASK_TYPE = "research_topic";
const WEB_RESEARCH_ACTIVE_STATUSES = new Set(["accepted", "claimed", "in_progress"]);

function ClaimIcon({ status }: { status: string }) {
  if (status === "supported") {
    return <ShieldCheck size={15} aria-hidden="true" />;
  }
  if (status === "unsupported") {
    return <ShieldX size={15} aria-hidden="true" />;
  }
  return <ShieldQuestion size={15} aria-hidden="true" />;
}

function metadataString(metadata: Record<string, unknown>, key: string) {
  const value = metadata[key];
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function metadataNumber(metadata: Record<string, unknown>, key: string) {
  const value = metadata[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function evidenceStringList(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : [];
}

function recordValue(value: unknown) {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function resultString(result: Record<string, unknown>, key: string) {
  const value = result[key];
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function resultNumber(result: Record<string, unknown>, key: string) {
  const value = result[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function timestampMillis(value: string) {
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function compareTimestampDescending(leftTimestamp: string, rightTimestamp: string) {
  const leftMillis = timestampMillis(leftTimestamp);
  const rightMillis = timestampMillis(rightTimestamp);
  if (leftMillis !== null && rightMillis !== null && leftMillis !== rightMillis) {
    return rightMillis - leftMillis;
  }
  if (leftMillis !== null && rightMillis === null) {
    return -1;
  }
  if (leftMillis === null && rightMillis !== null) {
    return 1;
  }
  return rightTimestamp.localeCompare(leftTimestamp);
}

function eventIsAtLeastAsRecentAsMessage(event: RunEvent, message: AgentMessage) {
  const eventMillis = timestampMillis(event.created_at);
  const messageMillis = timestampMillis(message.updated_at);
  if (eventMillis !== null && messageMillis !== null) {
    return eventMillis >= messageMillis;
  }
  if (eventMillis !== null && messageMillis === null) {
    return true;
  }
  if (eventMillis === null && messageMillis !== null) {
    return false;
  }
  return event.created_at.localeCompare(message.updated_at) >= 0;
}

function newestMessage(messages: AgentMessage[]) {
  return [...messages]
    .filter(
      (message) =>
        message.recipient_agent_id === WEB_RESEARCH_AGENT_ID &&
        message.task_type === WEB_RESEARCH_TASK_TYPE
    )
    .sort((left, right) => compareTimestampDescending(left.updated_at, right.updated_at))[0] ?? null;
}

function newestEventFirst(left: RunEvent, right: RunEvent) {
  const leftMillis = timestampMillis(left.created_at);
  const rightMillis = timestampMillis(right.created_at);
  if (leftMillis !== null && rightMillis !== null && leftMillis !== rightMillis) {
    return rightMillis - leftMillis;
  }
  if (leftMillis !== null && rightMillis === null) {
    return -1;
  }
  if (leftMillis === null && rightMillis !== null) {
    return 1;
  }
  const eventDelta = Number(right.event_id) - Number(left.event_id);
  if (Number.isFinite(eventDelta) && eventDelta !== 0) {
    return eventDelta;
  }
  return 0;
}

function newestResearchEvent(events: RunEvent[]) {
  return [...events]
    .filter(
      (event) =>
        event.actor === WEB_RESEARCH_AGENT_ID &&
        ["web_research_completed", "web_research_blocked", "provider_fallback"].includes(
          event.event_type
        )
    )
    .sort(newestEventFirst)[0] ?? null;
}

function researchStatusFromEvent(event: RunEvent): SourceResearchStatus {
  if (event.event_type === "web_research_completed") {
    const count = resultNumber(event.payload, "accepted_source_count") ?? 0;
    return {
      tone: count > 0 ? "ready" : "blocked",
      label: count > 0 ? "Research refreshed" : "No research sources",
      detail: `${count} provider-backed source${count === 1 ? "" : "s"} recorded`
    };
  }
  const reason = resultString(event.payload, "reason") ?? "Provider-backed web research is not ready.";
  return { tone: "blocked", label: "Research blocked", detail: reason };
}

export function sourceEvidenceKind(source: SourceRecord) {
  const sourceType = metadataString(source.metadata, "source_type");
  const isSearchSeed = sourceNeedsWebResearch(source);
  const isLiveSearch = sourceType === "web_search_result" || sourceType === "worker_web_search_result";
  return { sourceType, isSearchSeed, isLiveSearch };
}

function sourceTypeLabel(source: SourceRecord) {
  const { sourceType, isLiveSearch } = sourceEvidenceKind(source);
  if (isLiveSearch) {
    return "Live web search";
  }
  if (sourceType === "search_query_seed") {
    return "Search seed";
  }
  if (sourceType === "provider_reference") {
    return "Provider reference";
  }
  return sourceType ? statusLabel(sourceType) : "Source record";
}

function sourceTone(source: SourceRecord) {
  const { isLiveSearch, isSearchSeed } = sourceEvidenceKind(source);
  if (isSearchSeed) {
    return "needs-search";
  }
  if (isLiveSearch) {
    return "live-search";
  }
  return "reference";
}

function liveSearchQueries(sources: SourceRecord[]) {
  return new Set(
    sources
      .filter((source) => sourceEvidenceKind(source).isLiveSearch)
      .map((source) => metadataString(source.metadata, "search_query"))
      .filter((query): query is string => Boolean(query))
  );
}

export function sourceEvidenceBySourceId(sourceEvidence: SourceEvidenceRecord[] = []) {
  return sourceEvidence.reduce<Record<string, SourceEvidenceRecord>>((index, item) => {
    if (item.source_id) {
      index[item.source_id] = item;
    }
    return index;
  }, {});
}

export function sourceLedgerDrilldownSummary(
  sourceEvidence: SourceEvidenceRecord[] = []
): SourceLedgerDrilldownSummary {
  const coverageTopics = new Set<string>();
  return sourceEvidence.reduce(
    (summary, item) => {
      const precisionRisks = evidenceStringList(item.retrieval_precision_risks);
      const recallRisks = evidenceStringList(item.retrieval_recall_risks);
      evidenceStringList(item.retrieval_coverage_topics).forEach((topic) =>
        coverageTopics.add(topic)
      );
      const qualityStatus = item.quality_status;
      const freshnessStatus = item.freshness_status;
      const qualityIssue =
        (typeof qualityStatus === "string" &&
          qualityStatus.trim() &&
          !["usable", "strong", "current", "fresh"].includes(qualityStatus)) ||
        (typeof freshnessStatus === "string" &&
          freshnessStatus.trim() &&
          !["current", "fresh"].includes(freshnessStatus));
      return {
        evidenceItemCount: summary.evidenceItemCount + 1,
        acceptedCount: summary.acceptedCount + (item.accepted_for_context ? 1 : 0),
        precisionRiskCount: summary.precisionRiskCount + precisionRisks.length,
        recallRiskCount: summary.recallRiskCount + recallRisks.length,
        coverageTopicCount: coverageTopics.size,
        qualityIssueCount: summary.qualityIssueCount + (qualityIssue ? 1 : 0)
      };
    },
    {
      evidenceItemCount: 0,
      acceptedCount: 0,
      precisionRiskCount: 0,
      recallRiskCount: 0,
      coverageTopicCount: 0,
      qualityIssueCount: 0
    }
  );
}

export function sourceRefreshState(sources: SourceRecord[], claims: ClaimRecord[] = []) {
  const sourceIdsLinkedToClaims = new Set(claims.flatMap((claim) => claim.source_ids));
  const hasClaimContext = claims.length > 0;
  const resolvedQueries = liveSearchQueries(sources);
  return sources.reduce(
    (state, source) => {
      const { isLiveSearch, isSearchSeed } = sourceEvidenceKind(source);
      const searchQuery = metadataString(source.metadata, "search_query");
      const unresolvedSearchSeed =
        isSearchSeed &&
        (hasClaimContext
          ? sourceIdsLinkedToClaims.has(source.source_id)
          : !searchQuery || !resolvedQueries.has(searchQuery));
      return {
        searchSeedCount: state.searchSeedCount + (unresolvedSearchSeed ? 1 : 0),
        liveSearchCount: state.liveSearchCount + (isLiveSearch ? 1 : 0)
      };
    },
    { searchSeedCount: 0, liveSearchCount: 0 }
  );
}

function sourceUrl(source: SourceRecord) {
  try {
    return new URL(source.url).toString();
  } catch {
    return null;
  }
}

function sourceEvidenceDetails(source: SourceRecord) {
  const details: string[] = [];
  const freshness = metadataString(source.metadata, "freshness");
  const searchRank = metadataNumber(source.metadata, "search_rank");
  const rerankRank = metadataNumber(source.metadata, "rerank_rank");
  const rerankScore = metadataNumber(source.metadata, "rerank_score");
  const reranker = metadataString(source.metadata, "reranker");
  const searchQuery = metadataString(source.metadata, "search_query");
  if (freshness) {
    details.push(`Freshness: ${statusLabel(freshness)}`);
  }
  if (searchRank !== null) {
    details.push(`Rank: ${searchRank}`);
  }
  if (rerankRank !== null) {
    details.push(`Rerank: ${rerankRank}`);
  }
  if (rerankScore !== null) {
    details.push(`Score: ${rerankScore.toFixed(2)}`);
  }
  if (reranker) {
    details.push(`Reranker: ${statusLabel(reranker)}`);
  }
  if (searchQuery) {
    details.push(`Query: ${searchQuery}`);
  }
  if (source.published_at) {
    details.push(`Published: ${formatDateTime(source.published_at)}`);
  }
  details.push(`Retrieved: ${formatDateTime(source.retrieved_at)}`);
  return details;
}

function sourceRetrievalDetails(evidence: SourceEvidenceRecord) {
  const details: string[] = [];
  if (typeof evidence.retrieval_rank === "number") {
    details.push(`Rank: ${evidence.retrieval_rank}`);
  }
  if (typeof evidence.retrieval_rerank_score === "number") {
    details.push(`Score: ${evidence.retrieval_rerank_score.toFixed(2)}`);
  }
  if (evidence.retrieval_reranker) {
    details.push(`Reranker: ${statusLabel(evidence.retrieval_reranker)}`);
  }
  if (evidence.quality_status) {
    details.push(`Quality: ${statusLabel(evidence.quality_status)}`);
  }
  if (evidence.freshness_status) {
    details.push(`Freshness: ${statusLabel(evidence.freshness_status)}`);
  }
  return details;
}

export function sourceEvidenceSummary(source: SourceRecord) {
  const snippet = metadataString(source.metadata, "snippet");
  if (sourceEvidenceKind(source).isSearchSeed) {
    return "Provider-backed web research still needs to replace this search seed before publish.";
  }
  if (snippet) {
    return snippet;
  }
  return "No snippet was recorded for this source.";
}

export function claimSupportCounts(claims: ClaimRecord[]) {
  return claims.reduce(
    (counts, claim) => ({
      supported: counts.supported + (claim.support_status === "supported" ? 1 : 0),
      needsReview: counts.needsReview + (claim.support_status === "needs_review" ? 1 : 0),
      unsupported: counts.unsupported + (claim.support_status === "unsupported" ? 1 : 0)
    }),
    { supported: 0, needsReview: 0, unsupported: 0 }
  );
}

export function sourceResearchStatus(
  messages: AgentMessage[] = [],
  events: RunEvent[] = []
): SourceResearchStatus | null {
  const message = newestMessage(messages);
  const event = newestResearchEvent(events);
  if (event && (!message || eventIsAtLeastAsRecentAsMessage(event, message))) {
    return researchStatusFromEvent(event);
  }
  if (message) {
    if (WEB_RESEARCH_ACTIVE_STATUSES.has(message.status)) {
      return {
        tone: "running",
        label: "Research queued",
        detail: `${statusLabel(message.status)} by ${statusLabel(message.recipient_agent_id)}`
      };
    }
    const webResearch = recordValue(message.result.web_research);
    const generationMode = resultString(message.result, "generation_mode");
    const researchStatus = resultString(webResearch, "status");
    const acceptedSourceCount = resultNumber(webResearch, "accepted_source_count");
    const reason = resultString(webResearch, "reason") ?? message.error ?? "Provider-backed web research is not ready.";
    if (
      message.status === "failed" ||
      generationMode === "web_search_provider_blocked" ||
      researchStatus === "blocked"
    ) {
      return { tone: "blocked", label: "Research blocked", detail: reason };
    }
    if (acceptedSourceCount !== null && acceptedSourceCount > 0) {
      return {
        tone: "ready",
        label: "Research refreshed",
        detail: `${acceptedSourceCount} provider-backed source${acceptedSourceCount === 1 ? "" : "s"} recorded`
      };
    }
  }

  if (!event) {
    return null;
  }
  return researchStatusFromEvent(event);
}

export function SourcePanel({
  sources,
  claims,
  messages = [],
  events = [],
  sourceEvidence = [],
  disabled = false,
  onRefreshSources
}: SourcePanelProps) {
  const counts = claimSupportCounts(claims);
  const refreshState = sourceRefreshState(sources, claims);
  const needsWebResearch = refreshState.searchSeedCount > 0;
  const researchStatus = sourceResearchStatus(messages, events);
  const sourceRefreshDisabled = disabled || researchStatus?.tone === "running";
  const sourceEvidenceIndex = useMemo(
    () => sourceEvidenceBySourceId(sourceEvidence),
    [sourceEvidence]
  );
  const drilldownSummary = useMemo(
    () => sourceLedgerDrilldownSummary(sourceEvidence),
    [sourceEvidence]
  );
  const claimsBySource = useMemo(() => {
    return claims.reduce<Record<string, ClaimRecord[]>>((index, claim) => {
      claim.source_ids.forEach((sourceId) => {
        index[sourceId] = [...(index[sourceId] ?? []), claim];
      });
      return index;
    }, {});
  }, [claims]);

  return (
    <section className="rail-panel">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">Sources</p>
          <h2>Evidence links</h2>
        </div>
        <span>{sources.length}</span>
      </div>

      <div className="source-ledger-summary" aria-label="Claim support summary">
        <span>
          <ShieldCheck size={14} aria-hidden="true" />
          {counts.supported} supported
        </span>
        <span>
          <ShieldQuestion size={14} aria-hidden="true" />
          {counts.needsReview} review
        </span>
        <span>
          <ShieldX size={14} aria-hidden="true" />
          {counts.unsupported} unsupported
        </span>
      </div>

      {sources.length > 0 && (
        <div className="source-research-actions" aria-label="Web research status">
          <span>
            {refreshState.liveSearchCount} live source
            {refreshState.liveSearchCount === 1 ? "" : "s"}
          </span>
          <span className={needsWebResearch ? "warning" : undefined}>
            {refreshState.searchSeedCount} search seed
            {refreshState.searchSeedCount === 1 ? "" : "s"}
          </span>
          {onRefreshSources && needsWebResearch && (
            <button
              className="secondary-button"
              type="button"
              disabled={sourceRefreshDisabled}
              onClick={onRefreshSources}
            >
              <RefreshCw size={14} aria-hidden="true" />
              Run web research
            </button>
          )}
        </div>
      )}

      {researchStatus && (
        <div className={`source-research-status ${researchStatus.tone}`}>
          <AlertCircle size={15} aria-hidden="true" />
          <div>
            <strong>{researchStatus.label}</strong>
            <span>{researchStatus.detail}</span>
          </div>
        </div>
      )}

      {sources.length > 0 && (
        <div className="source-ledger-drilldown" aria-label="Accepted evidence coverage">
          <div>
            <strong>Accepted evidence coverage</strong>
            <span>
              {drilldownSummary.evidenceItemCount === 0
                ? "No context evidence packet has been built for this run yet."
                : `${drilldownSummary.acceptedCount}/${drilldownSummary.evidenceItemCount} accepted for context`}
            </span>
          </div>
          {drilldownSummary.evidenceItemCount > 0 && (
            <div className="source-ledger-drilldown-grid">
              <span>{drilldownSummary.precisionRiskCount} precision risks</span>
              <span>{drilldownSummary.recallRiskCount} recall risks</span>
              <span>{drilldownSummary.coverageTopicCount} coverage topics</span>
              <span>{drilldownSummary.qualityIssueCount} quality issues</span>
            </div>
          )}
        </div>
      )}

      {sources.length === 0 ? (
        <p className="muted">Source records and claim support will appear after generation.</p>
      ) : (
        <div className="source-list">
          {sources.map((source) => {
            const linkedClaims = claimsBySource[source.source_id] ?? [];
            const details = sourceEvidenceDetails(source);
            const href = sourceUrl(source);
            const evidence = sourceEvidenceIndex[source.source_id];
            const rerankReason = metadataString(source.metadata, "rerank_reason");
            const retrievalDetails = evidence ? sourceRetrievalDetails(evidence) : [];
            const precisionRisks = evidenceStringList(evidence?.retrieval_precision_risks);
            const recallRisks = evidenceStringList(evidence?.retrieval_recall_risks);
            const coverageTopics = evidenceStringList(evidence?.retrieval_coverage_topics);
            const qualityFlags = evidenceStringList(evidence?.quality_flags);
            return (
              <article key={source.source_id} className={`source-item source-${sourceTone(source)}`}>
                {href ? (
                  <a href={href} target="_blank" rel="noreferrer">
                    <span>{source.title}</span>
                    <ExternalLink size={14} aria-hidden="true" />
                  </a>
                ) : (
                  <span className="source-title-fallback">{source.title}</span>
                )}
                <p>{source.publisher ?? "Unknown publisher"} - {compactId(source.source_id)}</p>
                <div className="source-evidence-badges" aria-label="Source provenance">
                  <span>
                    <Search size={13} aria-hidden="true" />
                    {sourceTypeLabel(source)}
                  </span>
                  {details.map((detail, index) => (
                    <span key={`${index}-${detail}`}>
                      <CalendarClock size={13} aria-hidden="true" />
                      {detail}
                    </span>
                  ))}
                </div>
                <p className="source-snippet">{sourceEvidenceSummary(source)}</p>
                {rerankReason && (
                  <p className="source-snippet">Rerank: {rerankReason}</p>
                )}
                {sourceEvidence.length > 0 && (
                  <div
                    className={`source-retrieval-drilldown ${
                      evidence?.accepted_for_context ? "accepted" : "not-accepted"
                    }`}
                    aria-label="Retrieval evidence drilldown"
                  >
                    <div className="source-retrieval-status">
                      <Target size={14} aria-hidden="true" />
                      <strong>
                        {evidence
                          ? evidence.accepted_for_context
                            ? "Accepted for context"
                            : "Not accepted for context"
                          : "Not in context packet"}
                      </strong>
                    </div>
                    {retrievalDetails.length > 0 && (
                      <div className="source-retrieval-badges">
                        {retrievalDetails.map((detail) => (
                          <span key={detail}>{detail}</span>
                        ))}
                      </div>
                    )}
                    {evidence?.retrieval_rerank_reason && (
                      <p>{evidence.retrieval_rerank_reason}</p>
                    )}
                    {coverageTopics.length > 0 && (
                      <p>Coverage: {coverageTopics.join(", ")}</p>
                    )}
                    {[...qualityFlags, ...precisionRisks, ...recallRisks].length > 0 && (
                      <ul>
                        {qualityFlags.map((flag) => (
                          <li key={`quality-${flag}`}>Quality flag: {flag}</li>
                        ))}
                        {precisionRisks.map((risk) => (
                          <li key={`precision-${risk}`}>Precision risk: {risk}</li>
                        ))}
                        {recallRisks.map((risk) => (
                          <li key={`recall-${risk}`}>Recall risk: {risk}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
                <div className="claim-stack">
                  {linkedClaims.map((claim) => (
                    <span key={claim.claim_id} className="claim-row">
                      <ClaimIcon status={claim.support_status} />
                      {statusLabel(claim.support_status)}: {claim.claim_text}
                    </span>
                  ))}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
