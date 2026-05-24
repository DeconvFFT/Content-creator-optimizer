import json
from datetime import datetime, timedelta, timezone
from typing import Any

from all_about_llms.contracts import (
    AgentMessage,
    AgentTaskStatus,
    ArtifactRecord,
    ArtifactType,
    ClaimRecord,
    ClaimSupportStatus,
    ContextManifestItem,
    ContextRiskItem,
    ConversationTurn,
    FeedbackItem,
    FeedbackStatus,
    GuardrailAuditRecord,
    GuardrailAuditStatus,
    MemorySearchResult,
    RunEvent,
    RunState,
    SourceFreshnessStatus,
    SourceQualityStatus,
    SourceRecord,
)
from all_about_llms.foundation_references import list_foundation_references
from all_about_llms.orchestration.retrieval_evidence import (
    order_sources_by_retrieval_evidence,
)
from all_about_llms.orchestration.source_quality import evaluate_source_quality


PRIORITY_ORDER = {"critical": 0, "high": 1, "normal": 2, "low": 3}
PROJECT_MEMORY_KINDS = {"user_preference", "project_decision"}
LOW_CONFIDENCE_MEMORY_VALUES = {"low", "unknown", "tentative"}
DEFAULT_PROJECT_MEMORY_REVIEW_DAYS = 90
CONFLICT_TERMS = {
    "audio",
    "gemma",
    "html",
    "obsidian",
    "pgvector",
    "postgres",
    "sqlite",
    "voice",
}
NEGATION_MARKERS = (
    "do not",
    "don't",
    "dont",
    "avoid",
    "never",
    "no ",
    "not ",
    "without",
)


def build_context_engineering_payload(
    *,
    run: RunState,
    conversation_turns: list[ConversationTurn],
    agent_messages: list[AgentMessage],
    recent_events: list[RunEvent],
    sources: list[SourceRecord],
    claims: list[ClaimRecord],
    artifacts: list[ArtifactRecord],
    guardrail_audits: list[GuardrailAuditRecord],
    feedback_items: list[FeedbackItem],
    memories: list[MemorySearchResult],
    agent_id: str | None,
    max_manifest_items: int,
    max_context_tokens: int,
    project_memory_retrieval: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a budgeted manifest so agents know what context matters first."""

    memory_health = _memory_health(memories)
    candidates = _candidate_manifest_items(
        run=run,
        conversation_turns=conversation_turns,
        agent_messages=agent_messages,
        recent_events=recent_events,
        sources=sources,
        claims=claims,
        artifacts=artifacts,
        guardrail_audits=guardrail_audits,
        feedback_items=feedback_items,
        memories=memories,
        memory_health=memory_health,
        project_memory_retrieval=project_memory_retrieval,
        agent_id=agent_id,
    )
    foundation_references = _foundation_reference_manifest_items(agent_id)
    candidates.extend(foundation_references)
    candidates = sorted(
        candidates,
        key=lambda item: (PRIORITY_ORDER.get(item.priority, 9), item.title.lower()),
    )
    selected, omitted_count = _select_manifest_items(
        candidates=candidates,
        max_manifest_items=max_manifest_items,
        max_context_tokens=max_context_tokens,
    )
    risks = _context_risks(
        sources=sources,
        claims=claims,
        conversation_turns=conversation_turns,
        feedback_items=feedback_items,
        agent_messages=agent_messages,
        recent_events=recent_events,
        artifacts=artifacts,
        guardrail_audits=guardrail_audits,
        memories=memories,
        memory_health=memory_health,
        agent_id=agent_id,
        omitted_count=omitted_count,
    )
    recommended_fetches = _recommended_fetches(
        run=run,
        risks=risks,
        agent_messages=agent_messages,
        recent_events=recent_events,
        agent_id=agent_id,
    )
    source_evidence, omitted_source_evidence_count = _source_evidence_digest(
        sources=sources,
        claims=claims,
        artifacts=artifacts,
        max_items=max_manifest_items,
    )
    estimated_tokens = sum(item.estimated_tokens for item in selected)
    return {
        "context_manifest": selected,
        "context_risks": risks,
        "recommended_fetches": recommended_fetches,
        "source_evidence": source_evidence,
        "summary": {
            "context_manifest_items": len(selected),
            "context_manifest_estimated_tokens": estimated_tokens,
            "context_budget_tokens": max_context_tokens,
            "context_omitted_items": omitted_count,
            "source_evidence_items": len(source_evidence),
            "source_evidence_omitted_items": omitted_source_evidence_count,
            "source_evidence_with_snippets": sum(
                1 for item in source_evidence if item.get("snippet")
            ),
            "source_evidence_with_published_dates": sum(
                1 for item in source_evidence if item.get("published_at")
            ),
            "accepted_retrieval_evidence_items": sum(
                1 for item in source_evidence if item.get("accepted_for_context")
            ),
            "memory_health": memory_health,
            "project_memory_retrieval": project_memory_retrieval,
            "context_risk_count": len(risks),
            "recommended_fetches": len(recommended_fetches),
            "recent_events": len(recent_events),
            "foundation_references": len(foundation_references),
            "latest_web_research": _latest_web_research_summary(recent_events),
            "latest_ledgers": _latest_ledger_summary(artifacts),
            "latest_retrieval_quality": _latest_retrieval_quality_summary(
                artifacts
            ),
            "latest_publishing_handoff": _latest_publishing_handoff_summary(
                artifacts
            ),
            "latest_foundation_audit": _latest_foundation_audit_summary(artifacts),
            "latest_coordination": _latest_coordination_summary(artifacts),
        },
    }


def _candidate_manifest_items(
    *,
    run: RunState,
    conversation_turns: list[ConversationTurn],
    agent_messages: list[AgentMessage],
    recent_events: list[RunEvent],
    sources: list[SourceRecord],
    claims: list[ClaimRecord],
    artifacts: list[ArtifactRecord],
    guardrail_audits: list[GuardrailAuditRecord],
    feedback_items: list[FeedbackItem],
    memories: list[MemorySearchResult],
    memory_health: dict[str, Any],
    project_memory_retrieval: dict[str, Any] | None,
    agent_id: str | None,
) -> list[ContextManifestItem]:
    candidates: list[ContextManifestItem] = [
        ContextManifestItem(
            item_type="run_state",
            item_id=str(run.run_id),
            title=run.goal,
            priority="critical",
            reason="Root goal, run status, active agents, and conversation state.",
            estimated_tokens=_estimate_tokens(run.model_dump(mode="json")),
            metadata={
                "status": run.status.value,
                "active_agents": run.active_agents,
                "conversation_state_keys": sorted(run.conversation_state.keys()),
            },
        )
    ]

    if project_memory_retrieval and project_memory_retrieval.get("memory_count"):
        candidates.append(
            ContextManifestItem(
                item_type="project_memory_retrieval",
                item_id=project_memory_retrieval.get("artifact_id")
                or project_memory_retrieval.get("query"),
                title=(
                    "Project memory retrieval: "
                    f"{project_memory_retrieval.get('query')}"
                )[:120],
                priority="high",
                reason=(
                    "Hybrid synthesized-memory lookup ranks direct semantic or "
                    "keyword matches and graph-neighbor memories before agents act."
                ),
                estimated_tokens=_estimate_tokens(project_memory_retrieval),
                metadata={
                    "query": project_memory_retrieval.get("query"),
                    "memory_count": project_memory_retrieval.get("memory_count", 0),
                    "seed_memory_count": project_memory_retrieval.get(
                        "seed_memory_count",
                        0,
                    ),
                    "related_memory_count": project_memory_retrieval.get(
                        "related_memory_count",
                        0,
                    ),
                    "graph_node_count": project_memory_retrieval.get(
                        "graph_node_count",
                        0,
                    ),
                    "graph_edge_count": project_memory_retrieval.get(
                        "graph_edge_count",
                        0,
                    ),
                    "top_memories": project_memory_retrieval.get(
                        "top_memories",
                        [],
                    ),
                },
            )
        )

    for feedback in feedback_items:
        if feedback.status in {FeedbackStatus.OPEN, FeedbackStatus.ROUTED}:
            candidates.append(
                ContextManifestItem(
                    item_type="feedback_gate",
                    item_id=str(feedback.feedback_id),
                    title=feedback.feedback_text[:90],
                    priority="critical",
                    reason="Open or routed human feedback changes what autonomous agents may do next.",
                    estimated_tokens=_estimate_tokens(feedback.model_dump(mode="json")),
                    metadata={
                        "status": feedback.status.value,
                        "target_agent_id": feedback.target_agent_id,
                    },
                )
            )

    messages_by_id = {message.message_id: message for message in agent_messages}
    for message in agent_messages:
        if message.status in {
            AgentTaskStatus.ACCEPTED,
            AgentTaskStatus.CLAIMED,
            AgentTaskStatus.IN_PROGRESS,
            AgentTaskStatus.WAITING_FOR_HUMAN,
            AgentTaskStatus.BLOCKED,
            AgentTaskStatus.FAILED,
        }:
            retry_exhausted = _retry_exhausted(message)
            unmet_dependency_ids = _unmet_dependency_message_ids(
                message,
                messages_by_id,
            )
            waiting_for_dependencies = (
                message.status == AgentTaskStatus.ACCEPTED
                and bool(unmet_dependency_ids)
            )
            priority = (
                "critical"
                if message.status
                in {AgentTaskStatus.WAITING_FOR_HUMAN, AgentTaskStatus.BLOCKED}
                or waiting_for_dependencies
                else "high"
            )
            candidates.append(
                ContextManifestItem(
                    item_type=(
                        "retry_exhausted_agent_task"
                        if retry_exhausted
                        else "dependency_waiting_agent_task"
                        if waiting_for_dependencies
                        else "agent_task"
                    ),
                    item_id=str(message.message_id),
                    title=f"{message.recipient_agent_id}: {message.task_type}",
                    priority=priority,
                    reason=(
                        "Retry-exhausted A2A work needs explicit authorization "
                        "before resumed agents continue."
                        if retry_exhausted
                        else "Accepted A2A work is waiting for upstream "
                        "message dependencies before it can be claimed."
                        if waiting_for_dependencies
                        else "Pending or blocked A2A work is needed for resumable coordination."
                    ),
                    estimated_tokens=_estimate_tokens(message.model_dump(mode="json")),
                    metadata={
                        "status": message.status.value,
                        "sender_agent_id": message.sender_agent_id,
                        "recipient_agent_id": message.recipient_agent_id,
                        "attempt_count": message.attempt_count,
                        "max_attempts": message.max_attempts,
                        "retry_exhausted": retry_exhausted,
                        "handoff_trace_count": len(message.handoff_trace),
                        "latest_handoff_action": (
                            message.handoff_trace[-1].get("action")
                            if message.handoff_trace
                            else None
                        ),
                        "depends_on_message_ids": [
                            str(dependency_id)
                            for dependency_id in message.depends_on_message_ids
                        ],
                        "unmet_dependency_message_ids": [
                            str(dependency_id)
                            for dependency_id in unmet_dependency_ids
                        ],
                    },
                )
            )

    for claim in claims:
        if claim.support_status != ClaimSupportStatus.SUPPORTED:
            candidates.append(
                ContextManifestItem(
                    item_type="claim_review",
                    item_id=str(claim.claim_id),
                    title=claim.claim_text[:110],
                    priority=(
                        "critical"
                        if claim.support_status == ClaimSupportStatus.UNSUPPORTED
                        else "high"
                    ),
                    reason="Unsupported or needs-review claims must be handled before publishing.",
                    estimated_tokens=_estimate_tokens(claim.model_dump(mode="json")),
                    metadata={
                        "support_status": claim.support_status.value,
                        "source_ids": [str(source_id) for source_id in claim.source_ids],
                    },
                )
            )

    for source in sources:
        entry = evaluate_source_quality(source)
        if (
            entry.quality_status
            in {SourceQualityStatus.WEAK, SourceQualityStatus.NEEDS_REVIEW}
            or entry.freshness_status
            in {SourceFreshnessStatus.STALE, SourceFreshnessStatus.UNKNOWN}
        ):
            candidates.append(
                ContextManifestItem(
                    item_type="source_quality",
                    item_id=str(source.source_id),
                    title=f"{source.citation_id}: {source.title}",
                    priority=(
                        "critical"
                        if entry.quality_status == SourceQualityStatus.WEAK
                        else "high"
                    ),
                    reason="Source quality and freshness determine whether claims can be trusted.",
                    estimated_tokens=_estimate_tokens(source.model_dump(mode="json")),
                    metadata={
                        "quality_status": entry.quality_status.value,
                        "freshness_status": entry.freshness_status.value,
                        "flags": entry.flags,
                    },
                )
            )

    for audit in guardrail_audits:
        if audit.status != GuardrailAuditStatus.APPROVED:
            candidates.append(
                ContextManifestItem(
                    item_type="guardrail_audit",
                    item_id=str(audit.audit_id),
                    title=f"{audit.status.value}: {audit.artifact_id}",
                    priority="critical",
                    reason="Blocked or needs-revision guardrail audits gate publish readiness.",
                    estimated_tokens=_estimate_tokens(audit.model_dump(mode="json")),
                    metadata={
                        "artifact_id": str(audit.artifact_id),
                        "status": audit.status.value,
                        "blocking_issues": audit.blocking_issues,
                    },
                )
            )

    explicit_ledger_ids = set()
    for ledger_item, artifact_id in _ledger_manifest_items(artifacts):
        candidates.append(ledger_item)
        explicit_ledger_ids.add(artifact_id)
    for audit_item, artifact_id in _foundation_audit_manifest_items(artifacts):
        candidates.append(audit_item)
        explicit_ledger_ids.add(artifact_id)
    for coordination_item, artifact_id in _coordination_manifest_items(artifacts):
        candidates.append(coordination_item)
        explicit_ledger_ids.add(artifact_id)
    for handoff_item, artifact_id in _publishing_handoff_manifest_items(artifacts):
        candidates.append(handoff_item)
        explicit_ledger_ids.add(artifact_id)

    for artifact in reversed(artifacts[-10:]):
        if artifact.artifact_id in explicit_ledger_ids:
            continue
        candidates.append(
            ContextManifestItem(
                item_type="artifact",
                item_id=str(artifact.artifact_id),
                title=artifact.title,
                priority="normal",
                reason="Latest artifacts provide the current draft and provenance surface.",
                estimated_tokens=_estimate_tokens(
                    {
                        "artifact_type": artifact.artifact_type.value,
                        "title": artifact.title,
                        "source_ids": [str(source_id) for source_id in artifact.source_ids],
                        "provenance": artifact.provenance,
                    }
                ),
                metadata={
                    "artifact_type": artifact.artifact_type.value,
                    "uri": artifact.uri,
                    "source_count": len(artifact.source_ids),
                },
            )
        )

    for memory_result in memories:
        memory = memory_result.memory
        memory_metadata = _memory_manifest_metadata(memory_result, memory_health)
        candidates.append(
            ContextManifestItem(
                item_type="memory",
                item_id=str(memory.memory_id),
                title=f"{memory.agent_id}: {memory.memory_kind}",
                priority="normal",
                reason="Retrieved memories preserve user preferences and agent learnings across turns.",
                estimated_tokens=_estimate_tokens(memory.model_dump(mode="json")),
                metadata={**memory_metadata, "target_agent_id": agent_id},
            )
        )

    for turn in reversed(conversation_turns[-8:]):
        candidates.append(
            ContextManifestItem(
                item_type="conversation_turn",
                item_id=str(turn.turn_id),
                title=f"{turn.speaker}: {turn.transcript[:90]}",
                priority="normal",
                reason="Recent dialogue keeps natural user intent available to the next agent.",
                estimated_tokens=_estimate_tokens(turn.model_dump(mode="json")),
                metadata={"speaker": turn.speaker, "modality": turn.modality},
            )
        )

    for event in reversed(recent_events[-10:]):
        candidates.append(
            ContextManifestItem(
                item_type="timeline_event",
                item_id=str(event.event_id) if event.event_id is not None else None,
                title=f"{event.event_type} by {event.actor}",
                priority="low",
                reason="Recent timeline events help reconstruct what just changed.",
                estimated_tokens=_estimate_tokens(event.model_dump(mode="json")),
                metadata={"event_type": event.event_type, "actor": event.actor},
            )
        )

    return candidates


def _source_evidence_digest(
    *,
    sources: list[SourceRecord],
    claims: list[ClaimRecord],
    artifacts: list[ArtifactRecord],
    max_items: int,
) -> tuple[list[dict[str, Any]], int]:
    claim_ids_by_source_id: dict[Any, list[str]] = {}
    for claim in claims:
        for source_id in claim.source_ids:
            claim_ids_by_source_id.setdefault(source_id, []).append(str(claim.claim_id))

    artifact_ids_by_source_id: dict[Any, list[str]] = {}
    for artifact in artifacts:
        for source_id in artifact.source_ids:
            artifact_ids_by_source_id.setdefault(source_id, []).append(
                str(artifact.artifact_id)
            )

    ordered_sources, evidence_by_source_id, _ = order_sources_by_retrieval_evidence(
        sources,
        artifacts,
    )
    limit = min(len(ordered_sources), max(1, min(max_items, 12))) if sources else 0
    evidence = []
    for source in ordered_sources[:limit]:
        metadata = source.metadata or {}
        quality = evaluate_source_quality(source)
        retrieval_evidence = evidence_by_source_id.get(source.source_id)
        evidence.append(
            {
                "source_id": str(source.source_id),
                "citation_id": source.citation_id,
                "title": source.title,
                "url": str(source.url),
                "publisher": source.publisher,
                "source_type": str(metadata.get("source_type") or "manual_source"),
                "snippet": metadata.get("snippet"),
                "search_query": metadata.get("search_query"),
                "search_rank": metadata.get("search_rank"),
                "published_at": _source_published_at(source),
                "retrieved_at": source.retrieved_at.isoformat(),
                "quality_status": quality.quality_status.value,
                "freshness_status": quality.freshness_status.value,
                "quality_flags": quality.flags,
                "claim_ids": claim_ids_by_source_id.get(source.source_id, []),
                "artifact_ids": artifact_ids_by_source_id.get(source.source_id, []),
                "accepted_for_context": retrieval_evidence is not None,
                "retrieval_rank": (
                    retrieval_evidence.fused_rank if retrieval_evidence else None
                ),
                "retrieval_rerank_score": (
                    retrieval_evidence.rerank_score if retrieval_evidence else None
                ),
                "retrieval_reranker": (
                    retrieval_evidence.reranker if retrieval_evidence else None
                ),
                "retrieval_rerank_reason": (
                    retrieval_evidence.rerank_reason if retrieval_evidence else None
                ),
                "retrieval_precision_risks": (
                    list(retrieval_evidence.precision_risks)
                    if retrieval_evidence
                    else []
                ),
                "retrieval_recall_risks": (
                    list(retrieval_evidence.recall_risks)
                    if retrieval_evidence
                    else []
                ),
                "retrieval_coverage_topics": (
                    list(retrieval_evidence.coverage_topics)
                    if retrieval_evidence
                    else []
                ),
            }
        )
    return evidence, max(0, len(ordered_sources) - len(evidence))


def _memory_health(memories: list[MemorySearchResult]) -> dict[str, Any]:
    entries = [_memory_health_entry(memory_result) for memory_result in memories]
    project_entries = [
        entry for entry in entries if entry["memory_kind"] in PROJECT_MEMORY_KINDS
    ]
    stale_entries = [entry for entry in project_entries if entry["is_stale"]]
    low_confidence_entries = [
        entry for entry in project_entries if entry["is_low_confidence"]
    ]
    conflict_pairs = _memory_conflict_pairs(project_entries)
    return {
        "memory_count": len(entries),
        "project_memory_count": len(project_entries),
        "stale_memory_count": len(stale_entries),
        "low_confidence_memory_count": len(low_confidence_entries),
        "conflict_count": len(conflict_pairs),
        "stale_memory_ids": [entry["memory_id"] for entry in stale_entries],
        "low_confidence_memory_ids": [
            entry["memory_id"] for entry in low_confidence_entries
        ],
        "conflict_pairs": conflict_pairs,
    }


def _memory_manifest_metadata(
    memory_result: MemorySearchResult,
    memory_health: dict[str, Any],
) -> dict[str, Any]:
    memory = memory_result.memory
    memory_id = str(memory.memory_id)
    conflict_ids = {
        conflict_memory_id
        for pair in memory_health["conflict_pairs"]
        for conflict_memory_id in pair["memory_ids"]
    }
    return {
        "agent_id": memory.agent_id,
        "memory_kind": _memory_kind(memory),
        "memory_scope": _memory_scope(memory),
        "confidence": _memory_confidence(memory),
        "created_at": memory.created_at.isoformat(),
        "distance": memory_result.distance,
        "is_stale": memory_id in set(memory_health["stale_memory_ids"]),
        "is_low_confidence": memory_id
        in set(memory_health["low_confidence_memory_ids"]),
        "has_conflict": memory_id in conflict_ids,
    }


def _memory_health_entry(memory_result: MemorySearchResult) -> dict[str, Any]:
    memory = memory_result.memory
    metadata = memory.metadata or {}
    confidence = _memory_confidence(memory)
    tags = [
        str(tag).strip().lower()
        for tag in metadata.get("tags", [])
        if str(tag).strip()
    ]
    target_wiki_notes = [
        str(note).strip().lower()
        for note in metadata.get("target_wiki_notes", [])
        if str(note).strip()
    ]
    content = _normalize_memory_content(memory.content)
    return {
        "memory_id": str(memory.memory_id),
        "agent_id": memory.agent_id,
        "memory_kind": _memory_kind(memory),
        "memory_scope": _memory_scope(memory),
        "confidence": confidence,
        "tags": tags,
        "target_wiki_notes": target_wiki_notes,
        "content": content,
        "is_stale": _memory_is_stale(memory),
        "is_low_confidence": confidence.lower() in LOW_CONFIDENCE_MEMORY_VALUES,
        "has_negation": _has_negation(content),
    }


def _memory_kind(memory) -> str:
    return str(memory.metadata.get("project_memory_kind") or memory.memory_kind)


def _memory_scope(memory) -> str:
    if memory.metadata.get("memory_scope"):
        return str(memory.metadata["memory_scope"])
    return "run" if memory.run_id else "global"


def _memory_confidence(memory) -> str:
    return str(memory.metadata.get("confidence") or "medium")


def _memory_is_stale(memory) -> bool:
    metadata = memory.metadata or {}
    expires_at = _parse_datetime(metadata.get("expires_at"))
    now = datetime.now(timezone.utc)
    if expires_at is not None and expires_at <= now:
        return True
    if _memory_kind(memory) not in PROJECT_MEMORY_KINDS:
        return False
    review_after_days = _int_metadata(
        metadata.get("review_after_days"),
        default=DEFAULT_PROJECT_MEMORY_REVIEW_DAYS,
    )
    reference_time = _parse_datetime(metadata.get("reviewed_at")) or memory.created_at
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)
    return reference_time <= now - timedelta(days=review_after_days)


def _memory_conflict_pairs(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conflicts = []
    for index, left in enumerate(entries):
        for right in entries[index + 1 :]:
            if left["memory_kind"] != right["memory_kind"]:
                continue
            terms = _shared_conflict_terms(left, right)
            if not terms:
                continue
            if left["has_negation"] == right["has_negation"]:
                continue
            conflicts.append(
                {
                    "memory_ids": [left["memory_id"], right["memory_id"]],
                    "memory_kind": left["memory_kind"],
                    "terms": terms,
                }
            )
    return conflicts


def _shared_conflict_terms(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    shared_tags = sorted(set(left["tags"]) & set(right["tags"]))
    shared_wiki = sorted(set(left["target_wiki_notes"]) & set(right["target_wiki_notes"]))
    shared_content_terms = sorted(
        term
        for term in CONFLICT_TERMS
        if term in left["content"] and term in right["content"]
    )
    return [*shared_tags, *shared_content_terms, *shared_wiki]


def _normalize_memory_content(content: str) -> str:
    return " ".join(content.lower().replace("-", " ").split())


def _has_negation(content: str) -> bool:
    return any(marker in content for marker in NEGATION_MARKERS)


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _int_metadata(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, parsed)


def _source_published_at(source: SourceRecord) -> str | None:
    if source.published_at:
        return source.published_at.isoformat()
    published_at = (source.metadata or {}).get("published_at")
    return str(published_at) if published_at else None


def _latest_web_research_summary(
    recent_events: list[RunEvent],
) -> dict[str, Any] | None:
    for event in reversed(recent_events):
        if event.event_type != "web_research_completed":
            continue
        payload = event.payload or {}
        return {
            "event_id": event.event_id,
            "query": payload.get("query"),
            "freshness": payload.get("freshness"),
            "provider_result_count": payload.get("provider_result_count"),
            "accepted_source_count": payload.get("accepted_source_count"),
            "deduplicated_result_count": payload.get("deduplicated_result_count"),
            "citation_ids": payload.get("citation_ids", []),
        }
    return None


def _foundation_reference_manifest_items(
    agent_id: str | None,
) -> list[ContextManifestItem]:
    references = list_foundation_references().references
    relevant_references = [
        reference
        for reference in references
        if agent_id is None or agent_id in reference.applies_to
    ]
    items = []
    for reference in relevant_references:
        items.append(
            ContextManifestItem(
                item_type="foundation_reference",
                item_id=reference.reference_id,
                title=reference.title,
                priority="high",
                reason=(
                    "Official foundation guidance for protocol, persistence, "
                    "model, provider, memory, or specialist-agent assumptions."
                ),
                estimated_tokens=_estimate_tokens(reference.model_dump(mode="json")),
                metadata={
                    "publisher": reference.publisher,
                    "url": reference.url,
                    "reference_type": reference.reference_type,
                    "applies_to": reference.applies_to,
                    "architecture_decisions": reference.architecture_decisions,
                    "freshness_policy": reference.freshness_policy,
                    "last_verified": reference.last_verified,
                },
            )
        )
    return items


def _select_manifest_items(
    *,
    candidates: list[ContextManifestItem],
    max_manifest_items: int,
    max_context_tokens: int,
) -> tuple[list[ContextManifestItem], int]:
    selected: list[ContextManifestItem] = []
    used_tokens = 0
    omitted_count = 0
    for candidate in candidates:
        must_keep = candidate.priority == "critical" or not selected
        would_fit = used_tokens + candidate.estimated_tokens <= max_context_tokens
        if len(selected) < max_manifest_items and (must_keep or would_fit):
            selected.append(candidate)
            used_tokens += candidate.estimated_tokens
            continue
        omitted_count += 1
    return selected, omitted_count


def _context_risks(
    *,
    sources: list[SourceRecord],
    claims: list[ClaimRecord],
    conversation_turns: list[ConversationTurn],
    feedback_items: list[FeedbackItem],
    agent_messages: list[AgentMessage],
    recent_events: list[RunEvent],
    artifacts: list[ArtifactRecord],
    guardrail_audits: list[GuardrailAuditRecord],
    memories: list[MemorySearchResult],
    memory_health: dict[str, Any],
    agent_id: str | None,
    omitted_count: int,
) -> list[ContextRiskItem]:
    risks: list[ContextRiskItem] = []

    open_feedback = [
        feedback
        for feedback in feedback_items
        if feedback.status in {FeedbackStatus.OPEN, FeedbackStatus.ROUTED}
    ]
    if open_feedback:
        risks.append(
            ContextRiskItem(
                risk_type="open_human_feedback",
                severity="high",
                owner_agent_id="forward-deployed-engineer",
                reason="Human feedback is still open or routed and can gate autonomous work.",
                metadata={"feedback_ids": [str(item.feedback_id) for item in open_feedback]},
            )
        )
    latest_realtime_ledger = _latest_artifact_of_type(
        artifacts,
        ArtifactType.REALTIME_DIALOGUE_LEDGER,
    )
    latest_feedback_ledger = _latest_artifact_of_type(
        artifacts,
        ArtifactType.FEEDBACK_RESOLUTION_LEDGER,
    )
    latest_retrieval_ledger = _latest_artifact_of_type(
        artifacts,
        ArtifactType.RETRIEVAL_QUALITY_LEDGER,
    )
    if latest_realtime_ledger is None and _has_realtime_dialogue_evidence(
        conversation_turns,
        recent_events,
    ):
        risks.append(
            ContextRiskItem(
                risk_type="missing_realtime_dialogue_ledger",
                severity="medium",
                owner_agent_id="realtime-conversation-host",
                reason=(
                    "Realtime or voice dialogue exists, but no realtime dialogue "
                    "ledger is available for turn-taking and interruption continuity."
                ),
                metadata={},
            )
        )
    if latest_realtime_ledger is not None and _ledger_status(
        latest_realtime_ledger
    ) not in {None, "ready"}:
        risks.append(
            ContextRiskItem(
                risk_type="realtime_dialogue_ledger_needs_attention",
                severity="high",
                owner_agent_id="realtime-conversation-host",
                reason=(
                    "The latest realtime dialogue ledger reports unresolved "
                    "turn, interruption, follow-up, or feedback continuity work."
                ),
                metadata=_ledger_risk_metadata(latest_realtime_ledger),
            )
        )
    if latest_feedback_ledger is None and feedback_items:
        risks.append(
            ContextRiskItem(
                risk_type="missing_feedback_resolution_ledger",
                severity="medium",
                owner_agent_id="forward-deployed-engineer",
                reason=(
                    "Feedback exists, but no feedback resolution ledger is "
                    "available to show whether human notes have unblocked the loop."
                ),
                metadata={"feedback_count": len(feedback_items)},
            )
        )
    if latest_feedback_ledger is not None and _ledger_status(
        latest_feedback_ledger
    ) not in {None, "ready"}:
        risks.append(
            ContextRiskItem(
                risk_type="feedback_resolution_ledger_needs_attention",
                severity="high",
                owner_agent_id="forward-deployed-engineer",
                reason=(
                    "The latest feedback resolution ledger reports open, routed, "
                    "pending, or blocked feedback-linked work."
                ),
                metadata=_ledger_risk_metadata(latest_feedback_ledger),
            )
        )
    if latest_retrieval_ledger is None and (sources or claims or artifacts):
        risks.append(
            ContextRiskItem(
                risk_type="missing_retrieval_quality_ledger",
                severity="medium",
                owner_agent_id="retrieval-intelligence-agent",
                reason=(
                    "Run evidence exists, but no retrieval quality ledger is "
                    "available to prove ranking, recall, precision, and graph coverage."
                ),
                metadata={
                    "sources": len(sources),
                    "claims": len(claims),
                    "artifacts": len(artifacts),
                },
            )
        )
    if latest_retrieval_ledger is not None and _ledger_status(
        latest_retrieval_ledger
    ) not in {None, "ready"}:
        status = _ledger_status(latest_retrieval_ledger)
        risks.append(
            ContextRiskItem(
                risk_type="retrieval_quality_needs_attention",
                severity="critical" if status == "blocked" else "high",
                owner_agent_id="retrieval-intelligence-agent",
                reason=(
                    "The latest retrieval quality ledger reports precision, "
                    "recall, reranking, or graph coverage work before final synthesis."
                ),
                metadata=_retrieval_quality_digest(latest_retrieval_ledger),
            )
        )
    latest_foundation_audit = _latest_artifact_of_type(
        artifacts,
        ArtifactType.FOUNDATION_AUDIT,
    )
    if latest_foundation_audit is not None:
        audit_status = _foundation_audit_status(latest_foundation_audit)
        remediation_count = _foundation_audit_remediation_count(
            latest_foundation_audit
        )
        if audit_status not in {None, "pass"} or remediation_count:
            risks.append(
                ContextRiskItem(
                    risk_type="foundation_audit_remediation_required",
                    severity=(
                        "high"
                        if _foundation_audit_blocking_count(latest_foundation_audit)
                        else "medium"
                    ),
                    owner_agent_id="product-manager",
                    reason=(
                        "The latest foundation audit has unresolved requirement "
                        "evidence that should be routed before claiming the "
                        "foundation complete."
                    ),
                    metadata=_foundation_audit_digest(latest_foundation_audit),
                )
            )
    latest_publishing_handoff = _latest_publishing_handoff_summary(artifacts)
    if latest_publishing_handoff is None and _has_publishable_artifacts(artifacts):
        risks.append(
            ContextRiskItem(
                risk_type="missing_publishing_handoff",
                severity="medium",
                owner_agent_id="artifact-librarian",
                reason=(
                    "Publishable content exists, but no artifact-index publishing "
                    "handoff is available for resumed agents."
                ),
                metadata={
                    "publishable_artifact_count": _publishable_artifact_count(
                        artifacts
                    )
                },
            )
        )
    elif latest_publishing_handoff is not None and latest_publishing_handoff.get(
        "status"
    ) not in {"ready", "ready_for_publish_readiness"}:
        risks.append(
            ContextRiskItem(
                risk_type="publishing_handoff_needs_attention",
                severity=(
                    "high"
                    if str(latest_publishing_handoff.get("status", "")).startswith(
                        "blocked"
                    )
                    else "medium"
                ),
                owner_agent_id="artifact-librarian",
                reason=(
                    "The latest publishing handoff reports remaining source, "
                    "claim, packaging, guardrail, feedback, or readiness work."
                ),
                metadata=latest_publishing_handoff,
            )
        )

    pending_messages = [
        message
        for message in agent_messages
        if message.status
        in {
            AgentTaskStatus.ACCEPTED,
            AgentTaskStatus.CLAIMED,
            AgentTaskStatus.IN_PROGRESS,
            AgentTaskStatus.WAITING_FOR_HUMAN,
            AgentTaskStatus.BLOCKED,
        }
    ]
    if pending_messages:
        risks.append(
            ContextRiskItem(
                risk_type="pending_agent_tasks",
                severity="medium",
                owner_agent_id="agent-harness-engineer",
                reason="A2A work remains pending, claimed, waiting, or blocked.",
                metadata={
                    "message_ids": [str(message.message_id) for message in pending_messages]
                },
            )
        )
    messages_by_id = {message.message_id: message for message in agent_messages}
    dependency_waiting_messages = [
        message
        for message in pending_messages
        if message.status == AgentTaskStatus.ACCEPTED
        and _unmet_dependency_message_ids(message, messages_by_id)
    ]
    if dependency_waiting_messages:
        risks.append(
            ContextRiskItem(
                risk_type="agent_task_dependency_waiting",
                severity="medium",
                owner_agent_id="agent-harness-engineer",
                reason=(
                    "One or more accepted A2A tasks cannot be claimed until "
                    "their upstream message dependencies complete."
                ),
                metadata={
                    "message_ids": [
                        str(message.message_id)
                        for message in dependency_waiting_messages
                    ],
                    "unmet_dependencies_by_message_id": {
                        str(message.message_id): [
                            str(dependency_id)
                            for dependency_id in _unmet_dependency_message_ids(
                                message,
                                messages_by_id,
                            )
                        ]
                        for message in dependency_waiting_messages
                    },
                },
            )
        )
    retry_exhausted_messages = [
        message for message in pending_messages if _retry_exhausted(message)
    ]
    if retry_exhausted_messages:
        risks.append(
            ContextRiskItem(
                risk_type="retry_exhausted_agent_tasks",
                severity="critical",
                owner_agent_id="agent-harness-engineer",
                reason=(
                    "One or more A2A tasks exhausted retry attempts and need "
                    "human-authorized retry before autonomous resume."
                ),
                metadata={
                    "message_ids": [
                        str(message.message_id)
                        for message in retry_exhausted_messages
                    ],
                    "recipient_agent_ids": sorted(
                        {
                            message.recipient_agent_id
                            for message in retry_exhausted_messages
                        }
                    ),
                },
            )
        )

    unsupported_claims = [
        claim
        for claim in claims
        if claim.support_status == ClaimSupportStatus.UNSUPPORTED
    ]
    needs_review_claims = [
        claim
        for claim in claims
        if claim.support_status == ClaimSupportStatus.NEEDS_REVIEW
    ]
    if unsupported_claims:
        risks.append(
            ContextRiskItem(
                risk_type="unsupported_claims",
                severity="critical",
                owner_agent_id="claim-verification-agent",
                reason="Unsupported claims cannot ship in source-backed content.",
                metadata={"claim_ids": [str(claim.claim_id) for claim in unsupported_claims]},
            )
        )
    if needs_review_claims:
        risks.append(
            ContextRiskItem(
                risk_type="claims_need_review",
                severity="high",
                owner_agent_id="claim-verification-agent",
                reason="Claims still need evidence review before final approval.",
                metadata={"claim_ids": [str(claim.claim_id) for claim in needs_review_claims]},
            )
        )

    weak_sources = []
    freshness_review_sources = []
    for source in sources:
        entry = evaluate_source_quality(source)
        if entry.quality_status == SourceQualityStatus.WEAK:
            weak_sources.append(source)
        if entry.freshness_status in {
            SourceFreshnessStatus.STALE,
            SourceFreshnessStatus.UNKNOWN,
        }:
            freshness_review_sources.append(source)
    if weak_sources:
        risks.append(
            ContextRiskItem(
                risk_type="weak_source_records",
                severity="critical",
                owner_agent_id="web-research-agent",
                reason="Placeholder or weak sources must be replaced before publishing.",
                metadata={"source_ids": [str(source.source_id) for source in weak_sources]},
            )
        )
    if freshness_review_sources:
        risks.append(
            ContextRiskItem(
                risk_type="source_freshness_review",
                severity="medium",
                owner_agent_id="web-research-agent",
                reason="Some sources are stale or missing publication dates.",
                metadata={
                    "source_ids": [str(source.source_id) for source in freshness_review_sources]
                },
            )
        )

    blocking_audits = [
        audit
        for audit in guardrail_audits
        if audit.status != GuardrailAuditStatus.APPROVED
    ]
    if blocking_audits:
        risks.append(
            ContextRiskItem(
                risk_type="guardrail_audit_not_approved",
                severity="high",
                owner_agent_id="guardrails-agent",
                reason="One or more guardrail audits are blocked or need revision.",
                metadata={"audit_ids": [str(audit.audit_id) for audit in blocking_audits]},
            )
        )

    if agent_id and not memories:
        risks.append(
            ContextRiskItem(
                risk_type="no_retrieved_memories",
                severity="low",
                owner_agent_id="context-engineering-agent",
                reason="No memories were retrieved for the target agent and run scope.",
                metadata={"agent_id": agent_id},
            )
        )
    if memory_health["stale_memory_count"]:
        risks.append(
            ContextRiskItem(
                risk_type="stale_project_memories",
                severity="medium",
                owner_agent_id="context-engineering-agent",
                reason=(
                    "One or more retrieved project memories are expired or older "
                    "than their review window."
                ),
                metadata={
                    "memory_ids": memory_health["stale_memory_ids"],
                    "stale_memory_count": memory_health["stale_memory_count"],
                },
            )
        )
    if memory_health["low_confidence_memory_count"]:
        risks.append(
            ContextRiskItem(
                risk_type="low_confidence_project_memories",
                severity="low",
                owner_agent_id="context-engineering-agent",
                reason=(
                    "One or more retrieved project memories have low, unknown, "
                    "or tentative confidence."
                ),
                metadata={
                    "memory_ids": memory_health["low_confidence_memory_ids"],
                    "low_confidence_memory_count": memory_health[
                        "low_confidence_memory_count"
                    ],
                },
            )
        )
    if memory_health["conflict_count"]:
        risks.append(
            ContextRiskItem(
                risk_type="conflicting_project_memories",
                severity="high",
                owner_agent_id="product-manager",
                reason=(
                    "Retrieved project memories appear to contradict each other. "
                    "Resolve the memory conflict before using them as policy."
                ),
                metadata={
                    "conflict_count": memory_health["conflict_count"],
                    "conflict_pairs": memory_health["conflict_pairs"],
                },
            )
        )

    if omitted_count:
        risks.append(
            ContextRiskItem(
                risk_type="context_budget_omissions",
                severity="medium",
                owner_agent_id="context-engineering-agent",
                reason="The context manifest omitted lower-priority items to respect the request budget.",
                metadata={"omitted_count": omitted_count},
            )
        )

    return risks


def _recommended_fetches(
    *,
    run: RunState,
    risks: list[ContextRiskItem],
    agent_messages: list[AgentMessage],
    recent_events: list[RunEvent],
    agent_id: str | None,
) -> list[str]:
    risk_types = {risk.risk_type for risk in risks}
    fetches = []
    if "weak_source_records" in risk_types or "source_freshness_review" in risk_types:
        fetches.append(
            "Run web-research-agent or build a source ledger before final content approval."
        )
    if "unsupported_claims" in risk_types or "claims_need_review" in risk_types:
        fetches.append("Run claim-verification-agent after source repair or research.")
    if "open_human_feedback" in risk_types:
        fetches.append("Resolve or route open feedback before autonomous publishing work.")
    if (
        "missing_realtime_dialogue_ledger" in risk_types
        or "realtime_dialogue_ledger_needs_attention" in risk_types
    ):
        fetches.append(
            "Build or refresh the realtime dialogue ledger before resuming voice-led work."
        )
    if (
        "missing_feedback_resolution_ledger" in risk_types
        or "feedback_resolution_ledger_needs_attention" in risk_types
    ):
        fetches.append(
            "Build or review the feedback resolution ledger before clearing human-feedback work."
        )
    if (
        "missing_retrieval_quality_ledger" in risk_types
        or "retrieval_quality_needs_attention" in risk_types
    ):
        fetches.append(
            "Build or review the retrieval quality ledger before source-backed synthesis."
        )
    if "foundation_audit_remediation_required" in risk_types:
        fetches.append(
            "Run the Sprint/Progress work plan to route latest foundation-audit remediation."
        )
    if "missing_publishing_handoff" in risk_types:
        fetches.append(
            "Run Artifact Librarian indexing to create the latest publishing handoff."
        )
    if "publishing_handoff_needs_attention" in risk_types:
        fetches.append(
            "Review the latest publishing handoff before final editor or publish-readiness work."
        )
    if "pending_agent_tasks" in risk_types:
        pending_agents = sorted(
            {
                message.recipient_agent_id
                for message in agent_messages
                if message.status
                in {
                    AgentTaskStatus.ACCEPTED,
                    AgentTaskStatus.CLAIMED,
                    AgentTaskStatus.IN_PROGRESS,
                    AgentTaskStatus.WAITING_FOR_HUMAN,
                    AgentTaskStatus.BLOCKED,
                }
            }
        )
        fetches.append(
            "Inspect specialist inboxes for: " + ", ".join(pending_agents)
        )
    if "retry_exhausted_agent_tasks" in risk_types:
        retry_message_ids = [
            str(message.message_id)
            for message in agent_messages
            if _retry_exhausted(message)
        ]
        fetches.append(
            "Authorize retry for exhausted A2A task(s) before resume: "
            + ", ".join(retry_message_ids)
            + "."
        )
    if "agent_task_dependency_waiting" in risk_types:
        fetches.append(
            "Inspect upstream A2A dependency tasks before trying to claim dependent work."
        )
    if agent_id and "no_retrieved_memories" in risk_types:
        fetches.append(
            f"Record or retrieve run memories for {agent_id} before long-context synthesis."
        )
    if "stale_project_memories" in risk_types:
        fetches.append(
            "Refresh or reconfirm stale project memories before using them as current policy."
        )
    if "low_confidence_project_memories" in risk_types:
        fetches.append(
            "Review low-confidence project memories before relying on them for agent behavior."
        )
    if "conflicting_project_memories" in risk_types:
        fetches.append(
            "Resolve conflicting project memories through Product Manager or Forward Deployed Engineer review."
        )
    if recent_events:
        last_event_id = recent_events[-1].event_id
        fetches.append(
            f"Resume timeline streaming after event {last_event_id or 0} for run {run.run_id}."
        )
    return fetches


def _ledger_manifest_items(
    artifacts: list[ArtifactRecord],
) -> list[tuple[ContextManifestItem, Any]]:
    items = []
    for artifact_type, item_type, title, owner, reason in [
        (
            ArtifactType.REALTIME_DIALOGUE_LEDGER,
            "realtime_dialogue_ledger",
            "Latest realtime dialogue ledger",
            "realtime-conversation-host",
            "Voice/text continuity evidence for turn-taking, interruptions, spoken acknowledgements, and host follow-ups.",
        ),
        (
            ArtifactType.FEEDBACK_RESOLUTION_LEDGER,
            "feedback_resolution_ledger",
            "Latest feedback resolution ledger",
            "forward-deployed-engineer",
            "Human-feedback loop evidence for open, routed, resolved, pending, and blocked feedback-linked work.",
        ),
        (
            ArtifactType.RETRIEVAL_QUALITY_LEDGER,
            "retrieval_quality_ledger",
            "Latest retrieval quality ledger",
            "retrieval-intelligence-agent",
            "Ranking, reranking, precision, recall, source coverage, and knowledge-graph evidence for source-backed synthesis.",
        ),
        (
            ArtifactType.PROVIDER_SMOKE_LEDGER,
            "provider_smoke_ledger",
            "Latest provider smoke ledger",
            "observability-agent",
            "Provider-readiness smoke evidence for Gemma/HF, realtime audio, web search, deterministic reranking, and imagegen boundaries.",
        ),
    ]:
        artifact = _latest_artifact_of_type(artifacts, artifact_type)
        if artifact is None:
            continue
        status = _ledger_status(artifact)
        priority = "high" if status in {None, "ready"} else "critical"
        items.append(
            (
                ContextManifestItem(
                    item_type=item_type,
                    item_id=str(artifact.artifact_id),
                    title=f"{title}: {status or 'unknown'}",
                    priority=priority,
                    reason=reason,
                    estimated_tokens=_estimate_tokens(
                        {
                            "artifact_type": artifact.artifact_type.value,
                            "title": artifact.title,
                            "status": status,
                            "summary": artifact.content.get("summary"),
                            "recommended_next_actions": artifact.content.get(
                                "recommended_next_actions",
                                [],
                            ),
                            "ledger_counts": _ledger_counts(artifact),
                        }
                    ),
                    metadata={
                        "artifact_type": artifact.artifact_type.value,
                        "owner_agent_id": owner,
                        "status": status,
                        "uri": artifact.uri,
                        **_ledger_counts(artifact),
                    },
                ),
                artifact.artifact_id,
            )
        )
    return items


def _foundation_audit_manifest_items(
    artifacts: list[ArtifactRecord],
) -> list[tuple[ContextManifestItem, Any]]:
    artifact = _latest_artifact_of_type(artifacts, ArtifactType.FOUNDATION_AUDIT)
    if artifact is None:
        return []
    audit_status = _foundation_audit_status(artifact)
    remediation_count = _foundation_audit_remediation_count(artifact)
    priority = (
        "critical"
        if audit_status not in {None, "pass"} or remediation_count
        else "high"
    )
    item = ContextManifestItem(
        item_type="foundation_audit",
        item_id=str(artifact.artifact_id),
        title=f"Latest foundation audit: {audit_status or 'unknown'}",
        priority=priority,
        reason=(
            "Requirement-level evidence for the multi-agent foundation, including "
            "owner-routed remediation for missing or failing checks."
        ),
        estimated_tokens=_estimate_tokens(
            {
                "artifact_type": artifact.artifact_type.value,
                "title": artifact.title,
                "status": audit_status,
                "remediation_count": remediation_count,
                "blocking_remediation_count": (
                    _foundation_audit_blocking_count(artifact)
                ),
                "remediation_items": _foundation_audit_remediation_items(artifact),
            }
        ),
        metadata={
            "artifact_type": artifact.artifact_type.value,
            "status": audit_status,
            "uri": artifact.uri,
            "remediation_count": remediation_count,
            "blocking_remediation_count": _foundation_audit_blocking_count(
                artifact
            ),
            "owner_agent_ids": _foundation_audit_owner_agent_ids(artifact),
        },
    )
    return [(item, artifact.artifact_id)]


def _coordination_manifest_items(
    artifacts: list[ArtifactRecord],
) -> list[tuple[ContextManifestItem, Any]]:
    items = []
    for workflow, item_type, title, owner, reason in [
        (
            "run_work_plan_v1",
            "work_plan",
            "Latest Sprint/Progress work plan",
            "sprint-progress-agent",
            "Durable next-pass work routing, including same-pass foundation remediation tasks.",
        ),
        (
            "run_sync_pulse_v1",
            "sync_pulse",
            "Latest Product Manager sync pulse",
            "product-manager",
            "Manager coordination view of blockers, recommended agents, and refreshed post-audit state.",
        ),
    ]:
        artifact = _latest_artifact_with_workflow(artifacts, workflow)
        if artifact is None:
            continue
        digest = (
            _work_plan_digest(artifact)
            if workflow == "run_work_plan_v1"
            else _sync_pulse_digest(artifact)
        )
        remediation_count = int(digest.get("foundation_audit_remediation_count") or 0)
        blocked_count = int(digest.get("blocked_item_count") or 0)
        refresh_reason = digest.get("refresh_reason")
        priority = (
            "critical"
            if remediation_count or blocked_count
            else "high"
            if refresh_reason
            else "normal"
        )
        items.append(
            (
                ContextManifestItem(
                    item_type=item_type,
                    item_id=str(artifact.artifact_id),
                    title=f"{title}: {refresh_reason or 'current'}",
                    priority=priority,
                    reason=reason,
                    estimated_tokens=_estimate_tokens(digest),
                    metadata={
                        "artifact_type": artifact.artifact_type.value,
                        "owner_agent_id": owner,
                        "uri": artifact.uri,
                        **digest,
                    },
                ),
                artifact.artifact_id,
            )
        )
    return items


def _publishing_handoff_manifest_items(
    artifacts: list[ArtifactRecord],
) -> list[tuple[ContextManifestItem, Any]]:
    artifact = _latest_artifact_of_type(artifacts, ArtifactType.ARTIFACT_INDEX)
    if artifact is None:
        return []
    digest = _publishing_handoff_digest(artifact)
    if digest is None:
        return []
    status = digest.get("status")
    priority = "high" if status in {"ready", "ready_for_publish_readiness"} else "critical"
    item = ContextManifestItem(
        item_type="publishing_handoff",
        item_id=str(artifact.artifact_id),
        title=f"Latest publishing handoff: {status or 'unknown'}",
        priority=priority,
        reason=(
            "Compact package state for resumed content agents, including drafts, "
            "source ledger state, claim support, distribution/media readiness, "
            "guardrails, open feedback, and publish-readiness evidence."
        ),
        estimated_tokens=_estimate_tokens(digest),
        metadata={
            "artifact_type": artifact.artifact_type.value,
            "owner_agent_id": "artifact-librarian",
            "uri": artifact.uri,
            **digest,
        },
    )
    return [(item, artifact.artifact_id)]


def _latest_artifact_of_type(
    artifacts: list[ArtifactRecord],
    artifact_type: ArtifactType,
) -> ArtifactRecord | None:
    for artifact in reversed(artifacts):
        if artifact.artifact_type == artifact_type:
            return artifact
    return None


def _latest_artifact_with_workflow(
    artifacts: list[ArtifactRecord],
    workflow: str,
) -> ArtifactRecord | None:
    for artifact in reversed(artifacts):
        if artifact.provenance.get("workflow") == workflow:
            return artifact
    return None


def _latest_ledger_summary(artifacts: list[ArtifactRecord]) -> dict[str, Any]:
    summary = {}
    for artifact_type, key in [
        (ArtifactType.REALTIME_DIALOGUE_LEDGER, "realtime_dialogue_ledger"),
        (ArtifactType.FEEDBACK_RESOLUTION_LEDGER, "feedback_resolution_ledger"),
        (ArtifactType.RETRIEVAL_QUALITY_LEDGER, "retrieval_quality_ledger"),
        (ArtifactType.PROVIDER_SMOKE_LEDGER, "provider_smoke_ledger"),
        (
            ArtifactType.WORKER_PROFILE_HEARTBEAT_LEDGER,
            "worker_profile_heartbeat_ledger",
        ),
    ]:
        artifact = _latest_artifact_of_type(artifacts, artifact_type)
        if artifact is None:
            summary[key] = None
            continue
        summary[key] = {
            "artifact_id": str(artifact.artifact_id),
            "status": _ledger_status(artifact),
            **_ledger_counts(artifact),
        }
    return summary


def _latest_retrieval_quality_summary(
    artifacts: list[ArtifactRecord],
) -> dict[str, Any] | None:
    artifact = _latest_artifact_of_type(
        artifacts,
        ArtifactType.RETRIEVAL_QUALITY_LEDGER,
    )
    if artifact is None:
        return None
    return _retrieval_quality_digest(artifact)


def _latest_publishing_handoff_summary(
    artifacts: list[ArtifactRecord],
) -> dict[str, Any] | None:
    artifact = _latest_artifact_of_type(artifacts, ArtifactType.ARTIFACT_INDEX)
    if artifact is None:
        return None
    return _publishing_handoff_digest(artifact)


def _publishing_handoff_digest(artifact: ArtifactRecord) -> dict[str, Any] | None:
    handoff = artifact.content.get("publishing_handoff")
    if not isinstance(handoff, dict):
        return None
    guardrail = handoff.get("guardrail")
    if not isinstance(guardrail, dict):
        guardrail = {}
    feedback_gates = handoff.get("feedback_gates")
    if not isinstance(feedback_gates, dict):
        feedback_gates = {}
    source_ledger = handoff.get("source_ledger")
    if not isinstance(source_ledger, dict):
        source_ledger = {}
    claim_revision = handoff.get("claim_revision")
    if not isinstance(claim_revision, dict):
        claim_revision = {}
    latest_publish_readiness = handoff.get("latest_publish_readiness")
    if not isinstance(latest_publish_readiness, dict):
        latest_publish_readiness = None
    recommended_next_actions = handoff.get("recommended_next_actions", [])
    if not isinstance(recommended_next_actions, list):
        recommended_next_actions = []
    return {
        "artifact_id": str(artifact.artifact_id),
        "status": handoff.get("status"),
        "publishable_artifact_count": handoff.get("publishable_artifact_count", 0),
        "source_draft_count": handoff.get("source_draft_count", 0),
        "distribution_package_count": handoff.get("distribution_package_count", 0),
        "media_artifact_count": handoff.get("media_artifact_count", 0),
        "source_dependency_count": handoff.get("source_dependency_count", 0),
        "claim_dependency_count": handoff.get("claim_dependency_count", 0),
        "unsupported_claim_count": _list_count(handoff, "unsupported_claim_ids"),
        "needs_review_claim_count": _list_count(handoff, "needs_review_claim_ids"),
        "missing_source_count": _list_count(handoff, "missing_source_ids"),
        "claim_revision_status": claim_revision.get("status"),
        "claim_revision_open_held_claim_count": claim_revision.get(
            "open_held_claim_count",
            0,
        ),
        "claim_revision_pending_followup_count": claim_revision.get(
            "pending_followup_count",
            0,
        ),
        "claim_revision_blocked_followup_count": claim_revision.get(
            "blocked_followup_count",
            0,
        ),
        "claim_revision_revised_artifact_count": claim_revision.get(
            "revised_artifact_count",
            0,
        ),
        "source_ledger_artifact_count": _list_count(source_ledger, "artifact_ids"),
        "source_ledger_snapshot_event_count": _list_count(
            source_ledger,
            "snapshot_event_ids",
        ),
        "guardrail_audit_count": guardrail.get("audit_count", 0),
        "missing_guardrail_artifact_count": _list_count(
            guardrail,
            "missing_guardrail_artifact_ids",
        ),
        "non_approved_audit_count": _list_count(
            guardrail,
            "non_approved_audit_ids",
        ),
        "open_feedback_count": feedback_gates.get("open_or_routed_count", 0),
        "latest_publish_readiness_status": (
            latest_publish_readiness.get("status")
            if latest_publish_readiness
            else None
        ),
        "latest_publish_readiness_event_id": (
            latest_publish_readiness.get("event_id")
            if latest_publish_readiness
            else None
        ),
        "recommended_next_actions": recommended_next_actions,
    }


def _latest_coordination_summary(artifacts: list[ArtifactRecord]) -> dict[str, Any]:
    work_plan = _latest_artifact_with_workflow(artifacts, "run_work_plan_v1")
    sync_pulse = _latest_artifact_with_workflow(artifacts, "run_sync_pulse_v1")
    return {
        "work_plan": _work_plan_digest(work_plan) if work_plan else None,
        "sync_pulse": _sync_pulse_digest(sync_pulse) if sync_pulse else None,
    }


def _work_plan_digest(artifact: ArtifactRecord) -> dict[str, Any]:
    plan_items = artifact.content.get("plan_items", [])
    if not isinstance(plan_items, list):
        plan_items = []
    remediation_items = [
        item
        for item in plan_items
        if isinstance(item, dict)
        and item.get("item_type") == "foundation_audit_remediation"
    ]
    created_task_ids = artifact.content.get("created_task_message_ids", [])
    if not isinstance(created_task_ids, list):
        created_task_ids = []
    recommended_agent_ids = artifact.content.get("recommended_agent_ids", [])
    if not isinstance(recommended_agent_ids, list):
        recommended_agent_ids = []
    return {
        "artifact_id": str(artifact.artifact_id),
        "refresh_reason": artifact.content.get("refresh_reason")
        or artifact.provenance.get("refresh_reason"),
        "plan_item_count": len(plan_items),
        "foundation_audit_remediation_count": len(remediation_items),
        "blocked_item_count": artifact.content.get("blocked_item_count", 0),
        "pending_task_count": artifact.content.get("pending_task_count", 0),
        "created_task_count": len(created_task_ids),
        "recommended_agent_ids": recommended_agent_ids,
        "foundation_audit_artifact_ids": sorted(
            {
                str(item.get("metadata", {}).get("foundation_audit_artifact_id"))
                for item in remediation_items
                if isinstance(item.get("metadata"), dict)
                and item.get("metadata", {}).get("foundation_audit_artifact_id")
            }
        ),
    }


def _sync_pulse_digest(artifact: ArtifactRecord) -> dict[str, Any]:
    blockers = artifact.content.get("blockers", [])
    if not isinstance(blockers, list):
        blockers = []
    recommended_agent_ids = artifact.content.get("recommended_agent_ids", [])
    if not isinstance(recommended_agent_ids, list):
        recommended_agent_ids = []
    agent_states = artifact.content.get("agent_states", [])
    if not isinstance(agent_states, list):
        agent_states = []
    work_plan = artifact.content.get("work_plan") or {}
    if not isinstance(work_plan, dict):
        work_plan = {}
    return {
        "artifact_id": str(artifact.artifact_id),
        "refresh_reason": artifact.content.get("refresh_reason")
        or artifact.provenance.get("refresh_reason"),
        "blocker_count": len(blockers),
        "agent_count": len(agent_states),
        "recommended_agent_ids": recommended_agent_ids,
        "work_plan_refresh_reason": work_plan.get("refresh_reason"),
        "work_plan_item_count": len(work_plan.get("plan_items", []))
        if isinstance(work_plan.get("plan_items"), list)
        else 0,
    }


def _latest_foundation_audit_summary(
    artifacts: list[ArtifactRecord],
) -> dict[str, Any] | None:
    artifact = _latest_artifact_of_type(artifacts, ArtifactType.FOUNDATION_AUDIT)
    if artifact is None:
        return None
    return _foundation_audit_digest(artifact)


def _foundation_audit_digest(artifact: ArtifactRecord) -> dict[str, Any]:
    return {
        "artifact_id": str(artifact.artifact_id),
        "status": _foundation_audit_status(artifact),
        "check_count": artifact.content.get("check_count"),
        "completion_score": artifact.content.get("completion_score"),
        "remediation_count": _foundation_audit_remediation_count(artifact),
        "blocking_remediation_count": _foundation_audit_blocking_count(artifact),
        "owner_agent_ids": _foundation_audit_owner_agent_ids(artifact),
        "remediation_items": _foundation_audit_remediation_items(artifact),
    }


def _foundation_audit_status(artifact: ArtifactRecord) -> str | None:
    status = artifact.content.get("status")
    return str(status) if status is not None else None


def _foundation_audit_remediation_count(artifact: ArtifactRecord) -> int:
    value = artifact.content.get("remediation_count")
    if isinstance(value, int):
        return value
    remediation_items = _foundation_audit_remediation_items(artifact)
    if remediation_items:
        return len(remediation_items)
    checks = artifact.content.get("checks", [])
    if not isinstance(checks, list):
        return 0
    return sum(
        1
        for check in checks
        if isinstance(check, dict) and check.get("status") != "pass"
    )


def _foundation_audit_blocking_count(artifact: ArtifactRecord) -> int:
    value = artifact.content.get("blocking_remediation_count")
    if isinstance(value, int):
        return value
    return sum(
        1
        for item in _foundation_audit_remediation_items(artifact)
        if item.get("blocking")
    )


def _foundation_audit_remediation_items(
    artifact: ArtifactRecord,
) -> list[dict[str, Any]]:
    items = artifact.content.get("remediation_items", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _foundation_audit_owner_agent_ids(artifact: ArtifactRecord) -> list[str]:
    owner_ids = []
    for item in _foundation_audit_remediation_items(artifact):
        owner = item.get("owner_agent_id")
        if isinstance(owner, str) and owner and owner not in owner_ids:
            owner_ids.append(owner)
    return owner_ids


def _ledger_status(artifact: ArtifactRecord) -> str | None:
    status = artifact.content.get("status") or artifact.content.get("heartbeat_state")
    return str(status) if status is not None else None


def _ledger_counts(artifact: ArtifactRecord) -> dict[str, Any]:
    count_keys = [
        "session_count",
        "turn_count",
        "voice_turn_count",
        "interrupted_turn_count",
        "pending_followup_task_ids",
        "unacknowledged_interruption_turn_ids",
        "unanswered_user_turn_ids",
        "control_event_count",
        "unresolved_control_event_ids",
        "control_action_counts",
        "feedback_count",
        "open_feedback_count",
        "routed_feedback_count",
        "resolved_feedback_count",
        "pending_linked_task_count",
        "blocked_linked_task_count",
        "spoken_response_plan_count",
        "processed_tasks",
        "candidate_count",
        "accepted_candidate_count",
        "reranked_candidate_count",
        "graph_node_count",
        "precision_risk_count",
        "recall_gap_count",
        "coverage_gap_count",
        "recommended_queries",
        "step_count",
        "passed_count",
        "blocked_count",
        "failed_count",
        "not_run_count",
        "tool_boundary_count",
        "source_ids",
        "realtime_session_ids",
    ]
    counts: dict[str, Any] = {}
    for key in count_keys:
        if key not in artifact.content:
            continue
        value = artifact.content[key]
        counts[key] = len(value) if isinstance(value, list) else value
    return counts


def _retrieval_quality_digest(artifact: ArtifactRecord) -> dict[str, Any]:
    return {
        "artifact_id": str(artifact.artifact_id),
        "artifact_type": artifact.artifact_type.value,
        "status": _ledger_status(artifact),
        "summary": artifact.content.get("summary"),
        "topic": artifact.content.get("topic"),
        "candidate_count": artifact.content.get("candidate_count", 0),
        "accepted_candidate_count": artifact.content.get(
            "accepted_candidate_count",
            0,
        ),
        "reranked_candidate_count": artifact.content.get(
            "reranked_candidate_count",
            0,
        ),
        "graph_node_count": artifact.content.get("graph_node_count", 0),
        "precision_risk_count": artifact.content.get("precision_risk_count", 0),
        "recall_gap_count": artifact.content.get("recall_gap_count", 0),
        "coverage_gap_count": artifact.content.get("coverage_gap_count", 0),
        "recommended_queries": artifact.content.get("recommended_queries", []),
    }


def _list_count(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key, [])
    return len(value) if isinstance(value, list) else 0


def _ledger_risk_metadata(artifact: ArtifactRecord) -> dict[str, Any]:
    return {
        "artifact_id": str(artifact.artifact_id),
        "status": _ledger_status(artifact),
        "recommended_next_actions": artifact.content.get("recommended_next_actions", []),
        **_ledger_counts(artifact),
    }


def _has_realtime_dialogue_evidence(
    conversation_turns: list[ConversationTurn],
    recent_events: list[RunEvent],
) -> bool:
    if any(
        turn.modality == "voice" or turn.metadata.get("realtime_session_id")
        for turn in conversation_turns
    ):
        return True
    return any(event.event_type.startswith("realtime_") for event in recent_events)


def _has_publishable_artifacts(artifacts: list[ArtifactRecord]) -> bool:
    return _publishable_artifact_count(artifacts) > 0


def _publishable_artifact_count(artifacts: list[ArtifactRecord]) -> int:
    return sum(
        1
        for artifact in artifacts
        if artifact.artifact_type
        in {
            ArtifactType.POST,
            ArtifactType.REEL_SCRIPT,
            ArtifactType.SUBSTACK_ARTICLE,
            ArtifactType.SOCIAL_PACKAGE,
        }
    )


def _estimate_tokens(value: Any) -> int:
    text = json.dumps(value, default=str, sort_keys=True)
    return max(1, len(text) // 4)


def _retry_exhausted(message: AgentMessage) -> bool:
    retry_policy = message.result.get("retry_policy", {})
    retry_policy_attempts = retry_policy.get("attempt_count", message.attempt_count)
    retry_policy_max_attempts = retry_policy.get("max_attempts", message.max_attempts)
    return (
        message.status == AgentTaskStatus.BLOCKED
        and retry_policy_attempts >= retry_policy_max_attempts
    )


def _unmet_dependency_message_ids(
    message: AgentMessage,
    messages_by_id: dict[Any, AgentMessage],
) -> list[Any]:
    unmet_dependency_ids = []
    for dependency_id in message.depends_on_message_ids:
        dependency = messages_by_id.get(dependency_id)
        if dependency is None or dependency.status != AgentTaskStatus.COMPLETED:
            unmet_dependency_ids.append(dependency_id)
    return unmet_dependency_ids
