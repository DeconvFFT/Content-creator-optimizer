import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from all_about_llms.agents import get_agent_card
from all_about_llms.contracts import (
    AgentMemory,
    ArtifactRecord,
    ArtifactType,
    ProjectMemoryGraphEdge,
    ProjectMemoryGraphNode,
    ProjectMemoryKind,
    ProjectMemoryRetrievalEvaluation,
    ProjectMemoryRetrievalMemory,
    ProjectMemoryRetrievalRequest,
    ProjectMemoryRetrievalResult,
    RunEvent,
)


class ProjectMemoryRetrievalRunNotFoundError(RuntimeError):
    """Raised when project-memory retrieval references a missing run."""


class ProjectMemoryRetrievalAgentNotFoundError(RuntimeError):
    """Raised when project-memory retrieval targets an unknown agent."""


PROJECT_MEMORY_KINDS = {kind.value for kind in ProjectMemoryKind}
STOP_WORDS = {
    "about",
    "after",
    "again",
    "agent",
    "agents",
    "and",
    "are",
    "for",
    "from",
    "into",
    "our",
    "should",
    "that",
    "the",
    "this",
    "use",
    "with",
}
CONNECTOR_WEIGHTS = {
    "target_wiki_note": 0.16,
    "tag": 0.14,
    "source_artifact": 0.12,
}


class ProjectMemoryRetrievalWorkflow:
    """Retrieve synthesized project memory and expose a small traversal graph."""

    def __init__(self, store):
        self._store = store

    async def retrieve(
        self,
        run_id: UUID,
        request: ProjectMemoryRetrievalRequest,
    ) -> ProjectMemoryRetrievalResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise ProjectMemoryRetrievalRunNotFoundError(f"Run not found: {run_id}")
        if request.agent_id and get_agent_card(request.agent_id) is None:
            raise ProjectMemoryRetrievalAgentNotFoundError(
                f"Agent not found: {request.agent_id}"
            )

        search_limit = min(
            100,
            max(request.seed_limit * 4, request.memory_limit * 2, 20),
        )
        semantic_results = await self._store.search_memories(
            agent_id=request.agent_id,
            run_id=run_id,
            include_global_memories=request.include_global_memories,
            query_embedding=request.query_embedding,
            limit=search_limit,
        )
        graph_results = await self._store.search_memories(
            agent_id=request.agent_id,
            run_id=run_id,
            include_global_memories=request.include_global_memories,
            query_embedding=None,
            limit=request.graph_memory_limit,
        )

        query_terms = _query_terms(request.query)
        candidate_entries = _candidate_entries(
            semantic_results=semantic_results,
            graph_results=graph_results,
            query=request.query,
            query_terms=query_terms,
            request=request,
        )
        seed_entries = _seed_entries(candidate_entries, request.seed_limit)
        ranked_entries = _expand_graph(seed_entries, candidate_entries, request)
        ranked_entries = sorted(
            ranked_entries,
            key=lambda entry: (
                -entry.combined_score,
                -entry.semantic_score,
                -entry.keyword_score,
                entry.memory.created_at,
            ),
        )[: request.memory_limit]
        graph_nodes, graph_edges = _graph_projection(ranked_entries)
        artifacts = await self._store.list_artifacts(run_id)
        previous_ledgers = _previous_retrieval_ledgers(
            artifacts=artifacts,
            request=request,
        )
        evaluation = _evaluate_retrieval(
            request=request,
            ranked_entries=ranked_entries,
            candidate_entries=candidate_entries,
            previous_ledgers=previous_ledgers,
        )
        recommended_actions = _recommended_actions(
            request=request,
            seed_entries=seed_entries,
            ranked_entries=ranked_entries,
            graph_edges=graph_edges,
            evaluation=evaluation,
        )

        result = ProjectMemoryRetrievalResult(
            run_id=run_id,
            query=request.query,
            agent_id=request.agent_id,
            seed_memory_count=sum(1 for entry in ranked_entries if entry.is_seed),
            related_memory_count=sum(
                1 for entry in ranked_entries if not entry.is_seed
            ),
            memory_count=len(ranked_entries),
            graph_node_count=len(graph_nodes),
            graph_edge_count=len(graph_edges),
            memories=ranked_entries,
            graph_nodes=graph_nodes,
            graph_edges=graph_edges,
            evaluation=evaluation,
            recommended_actions=recommended_actions,
            summary=(
                f"Retrieved {len(ranked_entries)} project memory item(s) for "
                f"'{request.query}' with {len(graph_nodes)} graph node(s) and "
                f"{len(graph_edges)} edge(s)."
            ),
        )

        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.PROJECT_MEMORY_RETRIEVAL_LEDGER,
                title=f"Project memory retrieval - {request.query[:80]}",
                uri=f"artifact://runs/{run_id}/project-memory-retrieval",
                content={
                    "format": "project_memory_retrieval_ledger",
                    **result.model_dump(mode="json"),
                },
                provenance={
                    "workflow": "project_memory_retrieval_v1",
                    "agent_id": request.agent_id or "context-engineering-agent",
                    "query": request.query,
                    "uses_pgvector": request.query_embedding is not None,
                    "uses_graph_traversal": request.graph_depth > 0,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
                revision_history=[
                    {
                        "actor": "context-engineering-agent",
                        "workflow": "project_memory_retrieval_v1",
                        "note": (
                            "Built hybrid project-memory retrieval and graph "
                            "traversal ledger."
                        ),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            )
            await self._store.record_artifact(artifact)
            await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="artifact_recorded",
                    actor="artifact-librarian",
                    payload=artifact.model_dump(mode="json"),
                )
            )
            event = await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="project_memory_retrieval_completed",
                    actor="context-engineering-agent",
                    payload={
                        "artifact_id": str(artifact.artifact_id),
                        "query": request.query,
                        "agent_id": request.agent_id,
                        "memory_count": result.memory_count,
                        "seed_memory_count": result.seed_memory_count,
                        "related_memory_count": result.related_memory_count,
                        "graph_node_count": result.graph_node_count,
                        "graph_edge_count": result.graph_edge_count,
                        "evaluation": (
                            result.evaluation.model_dump(mode="json")
                            if result.evaluation
                            else None
                        ),
                        "precision": (
                            result.evaluation.precision
                            if result.evaluation
                            else None
                        ),
                        "recall": (
                            result.evaluation.recall
                            if result.evaluation
                            else None
                        ),
                        "precision_risk_count": (
                            result.evaluation.precision_risk_count
                            if result.evaluation
                            else 0
                        ),
                        "recall_gap_count": (
                            result.evaluation.recall_gap_count
                            if result.evaluation
                            else 0
                        ),
                        "repeated_query_count": (
                            result.evaluation.repeated_query_count
                            if result.evaluation
                            else 1
                        ),
                        "uses_pgvector": request.query_embedding is not None,
                        "uses_graph_traversal": request.graph_depth > 0,
                    },
                )
            )
            result.artifact_id = artifact.artifact_id
            result.event_id = event.event_id

        return result


def project_memory_retrieval_digest(
    result: ProjectMemoryRetrievalResult | None,
    *,
    max_memories: int = 5,
) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "query": result.query,
        "agent_id": result.agent_id,
        "artifact_id": str(result.artifact_id) if result.artifact_id else None,
        "event_id": result.event_id,
        "memory_count": result.memory_count,
        "seed_memory_count": result.seed_memory_count,
        "related_memory_count": result.related_memory_count,
        "graph_node_count": result.graph_node_count,
        "graph_edge_count": result.graph_edge_count,
        "evaluation": (
            result.evaluation.model_dump(mode="json")
            if result.evaluation
            else None
        ),
        "precision": result.evaluation.precision if result.evaluation else None,
        "recall": result.evaluation.recall if result.evaluation else None,
        "precision_risk_count": (
            result.evaluation.precision_risk_count if result.evaluation else 0
        ),
        "recall_gap_count": (
            result.evaluation.recall_gap_count if result.evaluation else 0
        ),
        "repeated_query_count": (
            result.evaluation.repeated_query_count if result.evaluation else 1
        ),
        "recommended_actions": result.recommended_actions,
        "top_memories": [
            {
                "memory_id": str(entry.memory.memory_id),
                "agent_id": entry.memory.agent_id,
                "memory_kind": entry.memory.memory_kind,
                "project_memory_kind": _project_memory_kind(entry.memory),
                "content_preview": entry.memory.content[:180],
                "distance": entry.distance,
                "keyword_score": entry.keyword_score,
                "semantic_score": entry.semantic_score,
                "graph_score": entry.graph_score,
                "combined_score": entry.combined_score,
                "is_seed": entry.is_seed,
                "shared_connectors": entry.shared_connectors[:10],
                "tags": _memory_tags(entry.memory),
                "target_wiki_notes": _memory_target_wiki_notes(entry.memory),
            }
            for entry in result.memories[:max_memories]
        ],
    }


def _previous_retrieval_ledgers(
    *,
    artifacts: list[ArtifactRecord],
    request: ProjectMemoryRetrievalRequest,
) -> list[ArtifactRecord]:
    ledgers = []
    for artifact in artifacts:
        if artifact.artifact_type != ArtifactType.PROJECT_MEMORY_RETRIEVAL_LEDGER:
            continue
        content = artifact.content or {}
        if content.get("query") != request.query:
            continue
        if content.get("agent_id") != request.agent_id:
            continue
        ledgers.append(artifact)
    return ledgers


def _evaluate_retrieval(
    *,
    request: ProjectMemoryRetrievalRequest,
    ranked_entries: list[ProjectMemoryRetrievalMemory],
    candidate_entries: list[ProjectMemoryRetrievalMemory],
    previous_ledgers: list[ArtifactRecord],
) -> ProjectMemoryRetrievalEvaluation:
    candidate_ids = {entry.memory.memory_id for entry in candidate_entries}
    retrieved_ids = {entry.memory.memory_id for entry in ranked_entries}
    expected_ids = _expected_memory_ids(request, candidate_entries)
    evaluation_mode = "labeled" if _has_labeled_expectations(request) else "heuristic"
    if not expected_ids:
        expected_ids = {
            entry.memory.memory_id
            for entry in candidate_entries
            if entry.semantic_score > 0 or entry.keyword_score > 0
        }
    relevant_retrieved_ids = retrieved_ids.intersection(expected_ids)
    false_positive_ids = sorted(retrieved_ids - expected_ids, key=str)
    false_negative_ids = sorted(expected_ids - retrieved_ids, key=str)
    precision = _ratio(len(relevant_retrieved_ids), len(retrieved_ids))
    recall = _ratio(len(relevant_retrieved_ids), len(expected_ids))
    f1_score = _f1(precision, recall)
    previous_evaluation = _previous_evaluation(previous_ledgers)
    previous_precision = (
        previous_evaluation.get("precision") if previous_evaluation else None
    )
    previous_recall = previous_evaluation.get("recall") if previous_evaluation else None
    precision_delta = (
        round(precision - previous_precision, 4)
        if precision is not None and previous_precision is not None
        else None
    )
    recall_delta = (
        round(recall - previous_recall, 4)
        if recall is not None and previous_recall is not None
        else None
    )
    notes = []
    if evaluation_mode == "heuristic":
        notes.append(
            "No labeled relevance set was supplied; precision/recall use direct semantic or keyword matches as the expected memory set."
        )
    if request.relevant_memory_ids:
        missing_label_ids = sorted(set(request.relevant_memory_ids) - candidate_ids, key=str)
        if missing_label_ids:
            notes.append(
                "Relevant memory ids were supplied but absent from the candidate universe: "
                + ", ".join(str(memory_id) for memory_id in missing_label_ids[:8])
            )
    if false_positive_ids:
        notes.append(
            "Retrieved memories outside the expected set; review before using as policy."
        )
    if false_negative_ids:
        notes.append(
            "Expected memories were not retrieved; increase recall or adjust metadata."
        )
    return ProjectMemoryRetrievalEvaluation(
        evaluation_mode=evaluation_mode,
        evaluated=True,
        expected_memory_count=len(expected_ids),
        retrieved_memory_count=len(retrieved_ids),
        relevant_retrieved_count=len(relevant_retrieved_ids),
        precision=precision,
        recall=recall,
        f1_score=f1_score,
        false_positive_memory_ids=false_positive_ids,
        false_negative_memory_ids=false_negative_ids,
        precision_risk_count=len(false_positive_ids),
        recall_gap_count=len(false_negative_ids),
        repeated_query_count=len(previous_ledgers) + 1,
        previous_precision=previous_precision,
        previous_recall=previous_recall,
        precision_delta=precision_delta,
        recall_delta=recall_delta,
        trend=_trend(precision_delta, recall_delta),
        notes=notes,
    )


def _has_labeled_expectations(request: ProjectMemoryRetrievalRequest) -> bool:
    return bool(
        request.relevant_memory_ids
        or request.relevant_tags
        or request.relevant_target_wiki_notes
    )


def _expected_memory_ids(
    request: ProjectMemoryRetrievalRequest,
    candidate_entries: list[ProjectMemoryRetrievalMemory],
) -> set[UUID]:
    expected_ids = set(request.relevant_memory_ids)
    relevant_tags = {tag.lower() for tag in request.relevant_tags}
    relevant_wiki_notes = set(request.relevant_target_wiki_notes)
    for entry in candidate_entries:
        if relevant_tags.intersection(set(_memory_tags(entry.memory))):
            expected_ids.add(entry.memory.memory_id)
        if relevant_wiki_notes.intersection(set(_memory_target_wiki_notes(entry.memory))):
            expected_ids.add(entry.memory.memory_id)
    return expected_ids


def _previous_evaluation(previous_ledgers: list[ArtifactRecord]) -> dict[str, Any] | None:
    if not previous_ledgers:
        return None
    for artifact in reversed(previous_ledgers):
        evaluation = (artifact.content or {}).get("evaluation")
        if isinstance(evaluation, dict):
            return evaluation
    return None


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return 1.0 if numerator == 0 else None
    return round(numerator / denominator, 4)


def _f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None:
        return None
    if precision + recall == 0:
        return 0.0
    return round((2 * precision * recall) / (precision + recall), 4)


def _trend(
    precision_delta: float | None,
    recall_delta: float | None,
) -> str:
    if precision_delta is None and recall_delta is None:
        return "no_prior"
    precision_delta = precision_delta or 0.0
    recall_delta = recall_delta or 0.0
    if precision_delta >= 0 and recall_delta >= 0 and (precision_delta or recall_delta):
        return "improved"
    if precision_delta < 0 or recall_delta < 0:
        return "regressed"
    return "stable"


def _candidate_entries(
    *,
    semantic_results: list[tuple[AgentMemory, float | None]],
    graph_results: list[tuple[AgentMemory, float | None]],
    query: str,
    query_terms: set[str],
    request: ProjectMemoryRetrievalRequest,
) -> list[ProjectMemoryRetrievalMemory]:
    by_id: dict[UUID, tuple[AgentMemory, float | None]] = {}
    for memory, distance in [*graph_results, *semantic_results]:
        if not _is_project_memory(memory) or not _passes_filters(memory, request):
            continue
        current = by_id.get(memory.memory_id)
        if current is None or current[1] is None:
            by_id[memory.memory_id] = (memory, distance)
        elif distance is not None and distance < current[1]:
            by_id[memory.memory_id] = (memory, distance)

    entries = []
    for memory, distance in by_id.values():
        keyword_score, keyword_matches = _keyword_score(memory, query, query_terms)
        semantic_score = _semantic_score(distance)
        combined_score = round((semantic_score * 0.55) + (keyword_score * 0.35), 4)
        match_reasons = []
        if distance is not None:
            match_reasons.append(f"semantic_distance={distance:.4f}")
        if keyword_matches:
            match_reasons.append(
                "keyword_matches=" + ",".join(sorted(keyword_matches)[:8])
            )
        if _memory_tags(memory):
            match_reasons.append("tags=" + ",".join(_memory_tags(memory)[:5]))
        entries.append(
            ProjectMemoryRetrievalMemory(
                memory=memory,
                distance=distance,
                keyword_score=keyword_score,
                semantic_score=semantic_score,
                combined_score=combined_score,
                match_reasons=match_reasons,
            )
        )
    return entries


def _seed_entries(
    entries: list[ProjectMemoryRetrievalMemory],
    seed_limit: int,
) -> list[ProjectMemoryRetrievalMemory]:
    scored = sorted(
        entries,
        key=lambda entry: (
            -entry.combined_score,
            -entry.semantic_score,
            -entry.keyword_score,
            entry.memory.created_at,
        ),
    )
    positive = [
        entry
        for entry in scored
        if entry.semantic_score > 0 or entry.keyword_score > 0
    ]
    seeds = positive[:seed_limit] if positive else scored[:seed_limit]
    seed_ids = {entry.memory.memory_id for entry in seeds}
    for entry in entries:
        entry.is_seed = entry.memory.memory_id in seed_ids
    return seeds


def _expand_graph(
    seed_entries: list[ProjectMemoryRetrievalMemory],
    entries: list[ProjectMemoryRetrievalMemory],
    request: ProjectMemoryRetrievalRequest,
) -> list[ProjectMemoryRetrievalMemory]:
    if request.graph_depth == 0 or not seed_entries:
        return seed_entries

    selected_ids = {entry.memory.memory_id for entry in seed_entries}
    active_connectors = _entry_connectors(seed_entries)
    entries_by_id = {entry.memory.memory_id: entry for entry in entries}
    for _depth in range(request.graph_depth):
        added_connectors: set[str] = set()
        for entry in entries:
            connectors = _connectors(entry.memory)
            shared = sorted(active_connectors.intersection(connectors))
            if not shared:
                continue
            connector_score = min(
                0.45,
                sum(_connector_weight(connector) for connector in shared),
            )
            if connector_score > entry.graph_score:
                entry.graph_score = round(connector_score, 4)
                entry.shared_connectors = shared
                entry.combined_score = round(
                    entry.combined_score + entry.graph_score,
                    4,
                )
                entry.match_reasons.append(
                    "graph_connectors=" + ",".join(shared[:8])
                )
            if entry.memory.memory_id not in selected_ids:
                selected_ids.add(entry.memory.memory_id)
                added_connectors.update(connectors)
        if not added_connectors:
            break
        active_connectors.update(added_connectors)

    return [entries_by_id[memory_id] for memory_id in selected_ids]


def _graph_projection(
    entries: list[ProjectMemoryRetrievalMemory],
) -> tuple[list[ProjectMemoryGraphNode], list[ProjectMemoryGraphEdge]]:
    nodes: dict[str, ProjectMemoryGraphNode] = {}
    edges: dict[tuple[str, str, str], ProjectMemoryGraphEdge] = {}
    for entry in entries:
        memory = entry.memory
        memory_node_id = f"memory:{memory.memory_id}"
        nodes[memory_node_id] = ProjectMemoryGraphNode(
            node_id=memory_node_id,
            node_type="memory",
            label=memory.content[:90],
            memory_id=memory.memory_id,
            metadata={
                "agent_id": memory.agent_id,
                "memory_kind": memory.memory_kind,
                "project_memory_kind": _project_memory_kind(memory),
                "is_seed": entry.is_seed,
                "combined_score": entry.combined_score,
                "created_at": memory.created_at.isoformat(),
            },
        )
        for connector in _connectors(memory):
            relationship, label = connector.split(":", 1)
            connector_node_id = f"{relationship}:{label}"
            nodes.setdefault(
                connector_node_id,
                ProjectMemoryGraphNode(
                    node_id=connector_node_id,
                    node_type=relationship,
                    label=label,
                    metadata={"connector": connector},
                ),
            )
            edge_key = (memory_node_id, connector_node_id, relationship)
            edges[edge_key] = ProjectMemoryGraphEdge(
                from_node_id=memory_node_id,
                to_node_id=connector_node_id,
                relationship=relationship,
                weight=_connector_weight(connector),
                metadata={"connector": connector},
            )
    return list(nodes.values()), list(edges.values())


def _recommended_actions(
    *,
    request: ProjectMemoryRetrievalRequest,
    seed_entries: list[ProjectMemoryRetrievalMemory],
    ranked_entries: list[ProjectMemoryRetrievalMemory],
    graph_edges: list[ProjectMemoryGraphEdge],
    evaluation: ProjectMemoryRetrievalEvaluation,
) -> list[str]:
    actions = []
    if request.query_embedding is None:
        actions.append(
            "Provide query_embedding to use pgvector semantic ordering before graph expansion."
        )
    if not ranked_entries:
        actions.append(
            "Record project_decision or user_preference memories before relying on synthesized memory."
        )
    if seed_entries and not graph_edges and request.graph_depth > 0:
        actions.append(
            "Add tags, target_wiki_notes, source artifacts, or source run metadata so project memories can be traversed as a graph."
        )
    if any(entry.graph_score > 0 and not entry.is_seed for entry in ranked_entries):
        actions.append(
            "Review graph-related memories before promoting them into current policy."
        )
    if evaluation.precision_risk_count:
        actions.append(
            "Review project-memory precision risks before applying graph-neighbor memories as policy."
        )
    if evaluation.recall_gap_count:
        actions.append(
            "Improve project-memory recall by adding embeddings, tags, wiki targets, or source-artifact links for missed memories."
        )
    if evaluation.trend == "regressed":
        actions.append(
            "Compare this retrieval ledger with the prior run before trusting the current memory set."
        )
    return actions


def _is_project_memory(memory: AgentMemory) -> bool:
    return _project_memory_kind(memory) in PROJECT_MEMORY_KINDS


def _project_memory_kind(memory: AgentMemory) -> str:
    return str(memory.metadata.get("project_memory_kind") or memory.memory_kind)


def _passes_filters(
    memory: AgentMemory,
    request: ProjectMemoryRetrievalRequest,
) -> bool:
    if request.memory_kinds:
        allowed_kinds = {kind.value for kind in request.memory_kinds}
        if _project_memory_kind(memory) not in allowed_kinds:
            return False
    if request.tags:
        memory_tags = set(_memory_tags(memory))
        if not memory_tags.intersection({tag.lower() for tag in request.tags}):
            return False
    if request.target_wiki_notes:
        memory_wiki_notes = set(_memory_target_wiki_notes(memory))
        if not memory_wiki_notes.intersection(request.target_wiki_notes):
            return False
    return True


def _query_terms(query: str) -> set[str]:
    return {
        term
        for term in re.findall(r"[a-z0-9][a-z0-9_-]*", query.lower())
        if len(term) > 2 and term not in STOP_WORDS
    }


def _keyword_score(
    memory: AgentMemory,
    query: str,
    query_terms: set[str],
) -> tuple[float, set[str]]:
    if not query_terms:
        return 0.0, set()
    text = _memory_search_text(memory)
    matches = {term for term in query_terms if term in text}
    score = len(matches) / len(query_terms)
    if query.lower() in text:
        score += 0.2
    return round(min(1.0, score), 4), matches


def _semantic_score(distance: float | None) -> float:
    if distance is None:
        return 0.0
    return round(1 / (1 + max(distance, 0.0)), 4)


def _memory_search_text(memory: AgentMemory) -> str:
    metadata = memory.metadata
    fields = [
        memory.content,
        memory.agent_id,
        memory.memory_kind,
        str(metadata.get("project_memory_kind", "")),
        " ".join(_memory_tags(memory)),
        " ".join(_memory_target_wiki_notes(memory)),
        " ".join(str(item) for item in metadata.get("source_artifact_ids", [])),
        str(metadata.get("source_run_id", "")),
    ]
    return " ".join(fields).lower()


def _memory_tags(memory: AgentMemory) -> list[str]:
    tags = memory.metadata.get("tags") or []
    return [str(tag).lower() for tag in tags if str(tag).strip()]


def _memory_target_wiki_notes(memory: AgentMemory) -> list[str]:
    wiki_notes = memory.metadata.get("target_wiki_notes") or []
    return [str(note) for note in wiki_notes if str(note).strip()]


def _connectors(memory: AgentMemory) -> set[str]:
    metadata = memory.metadata
    connectors = set()
    for tag in _memory_tags(memory):
        connectors.add(f"tag:{tag}")
    for wiki_note in _memory_target_wiki_notes(memory):
        connectors.add(f"target_wiki_note:{wiki_note}")
    for artifact_id in metadata.get("source_artifact_ids", []):
        connectors.add(f"source_artifact:{artifact_id}")
    return connectors


def _entry_connectors(entries: list[ProjectMemoryRetrievalMemory]) -> set[str]:
    connectors: set[str] = set()
    for entry in entries:
        connectors.update(_connectors(entry.memory))
    return connectors


def _connector_weight(connector: str) -> float:
    relationship = connector.split(":", 1)[0]
    return CONNECTOR_WEIGHTS.get(relationship, 0.03)
