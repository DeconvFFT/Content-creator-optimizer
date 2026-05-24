from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from all_about_llms.contracts import (
    AgentTaskStatus,
    ArtifactRecord,
    ArtifactType,
    FeedbackStatus,
    ObsidianMemoryPromotionRequest,
    ObsidianMemoryPromotionResult,
    RunEvent,
)


class ObsidianMemoryPromotionRunNotFoundError(RuntimeError):
    """Raised when an Obsidian memory promotion references a missing run."""


class ObsidianMemoryPromotionWorkflow:
    """Promote durable run observations into vault-native wiki memory proposals."""

    def __init__(self, store, vault_path: Path):
        self._store = store
        self._vault_path = vault_path

    async def generate(
        self,
        run_id: UUID,
        request: ObsidianMemoryPromotionRequest,
    ) -> ObsidianMemoryPromotionResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise ObsidianMemoryPromotionRunNotFoundError(f"Run not found: {run_id}")

        events = await self._store.list_events(run_id, limit=request.event_limit)
        messages = await self._store.list_agent_messages(run_id)
        sources = await self._store.list_sources(run_id)
        claims = await self._store.list_claims(run_id)
        artifacts = await self._store.list_artifacts(run_id)
        feedback_items = await self._store.list_feedback(run_id)
        audits = await self._store.list_guardrail_audits(run_id)

        latest_review_note = _latest_artifact_of_type(
            artifacts,
            ArtifactType.OBSIDIAN_NOTE,
        )
        latest_retrieval = _latest_artifact_of_type(
            artifacts,
            ArtifactType.RETRIEVAL_QUALITY_LEDGER,
        )
        latest_claim_revision = _latest_artifact_of_type(
            artifacts,
            ArtifactType.CLAIM_REVISION_LEDGER,
        )
        latest_artifact_index = _latest_artifact_of_type(
            artifacts,
            ArtifactType.ARTIFACT_INDEX,
        )
        pending_messages = [
            message
            for message in messages
            if message.status
            in {
                AgentTaskStatus.ACCEPTED,
                AgentTaskStatus.CLAIMED,
                AgentTaskStatus.IN_PROGRESS,
                AgentTaskStatus.WAITING_FOR_HUMAN,
                AgentTaskStatus.BLOCKED,
            }
        ]
        open_feedback = [
            item
            for item in feedback_items
            if item.status in {FeedbackStatus.OPEN, FeedbackStatus.ROUTED}
        ]
        promoted_items = _promoted_items(
            run=run,
            sources=sources,
            claims=claims,
            artifacts=artifacts,
            feedback_items=open_feedback,
            audits=audits,
            pending_messages=pending_messages,
            latest_review_note=latest_review_note,
            latest_retrieval=latest_retrieval,
            latest_claim_revision=latest_claim_revision,
            latest_artifact_index=latest_artifact_index,
            target_wiki_notes=request.target_wiki_notes,
        )

        note_title = request.title or f"Memory promotion - {run.goal[:80]}"
        note_dir = self._vault_path / "wiki" / "run-memory-promotions" / str(run_id)
        note_dir.mkdir(parents=True, exist_ok=True)
        note_path = note_dir / f"{_slug(request.promotion_kind)}.md"
        note_body = _render_promotion_note(
            title=note_title,
            promotion_kind=request.promotion_kind,
            run=run,
            events=events,
            promoted_items=promoted_items,
            target_wiki_notes=request.target_wiki_notes,
            latest_review_note=latest_review_note
            if request.include_review_note_links
            else None,
        )
        note_path.write_text(note_body, encoding="utf-8")

        relative_note_path = note_path.relative_to(self._vault_path)
        uri = f"obsidian://agent-studio/{relative_note_path.as_posix()}"
        source_artifact_ids = _source_artifact_ids(promoted_items)
        artifact = ArtifactRecord(
            run_id=run_id,
            artifact_type=ArtifactType.OBSIDIAN_MEMORY_PROMOTION,
            title=note_title,
            uri=uri,
            content={
                "format": "obsidian_memory_promotion",
                "promotion_kind": request.promotion_kind,
                "vault_path": str(self._vault_path),
                "relative_path": relative_note_path.as_posix(),
                "target_wiki_notes": request.target_wiki_notes,
                "promoted_item_count": len(promoted_items),
                "promoted_items": promoted_items,
                "source_artifact_ids": source_artifact_ids,
                "latest_review_note_artifact_id": (
                    str(latest_review_note.artifact_id)
                    if latest_review_note
                    else None
                ),
            },
            provenance={
                "workflow": "obsidian_memory_promotion_v1",
                "agent_id": "interactive-note-taking-agent",
                "source": "durable_run_state",
                "promotion_kind": request.promotion_kind,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_artifact_ids": source_artifact_ids,
            },
            revision_history=[
                {
                    "actor": "interactive-note-taking-agent",
                    "workflow": "obsidian_memory_promotion_v1",
                    "note": (
                        "Generated a proposed wiki-memory promotion from durable "
                        "run state and review artifacts."
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
                event_type="obsidian_memory_promotion_generated",
                actor="interactive-note-taking-agent",
                payload={
                    "artifact_id": str(artifact.artifact_id),
                    "uri": uri,
                    "file_path": str(note_path),
                    "promotion_kind": request.promotion_kind,
                    "target_wiki_notes": request.target_wiki_notes,
                    "promoted_item_count": len(promoted_items),
                    "source_artifact_ids": source_artifact_ids,
                },
            )
        )
        return ObsidianMemoryPromotionResult(
            run_id=run_id,
            artifact_id=artifact.artifact_id,
            uri=uri,
            file_path=str(note_path),
            promotion_kind=request.promotion_kind,
            target_wiki_notes=request.target_wiki_notes,
            promoted_item_count=len(promoted_items),
            event_id=event.event_id,
            summary=(
                f"Wrote Obsidian memory promotion with {len(promoted_items)} "
                f"candidate item(s) for {len(request.target_wiki_notes)} wiki note(s)."
            ),
        )


def _promoted_items(
    *,
    run,
    sources,
    claims,
    artifacts,
    feedback_items,
    audits,
    pending_messages,
    latest_review_note: ArtifactRecord | None,
    latest_retrieval: ArtifactRecord | None,
    latest_claim_revision: ArtifactRecord | None,
    latest_artifact_index: ArtifactRecord | None,
    target_wiki_notes: list[str],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = [
        {
            "item_type": "run_snapshot",
            "summary": (
                f"Run status is {run.status.value} with {len(sources)} source(s), "
                f"{len(claims)} claim(s), {len(artifacts)} artifact(s), "
                f"{len(feedback_items)} open/routed feedback item(s), and "
                f"{len(pending_messages)} pending A2A task(s)."
            ),
            "target_wiki_notes": target_wiki_notes,
            "source_artifact_ids": [],
            "recommended_action": (
                "Use this as the latest run-level memory snapshot before the next "
                "autonomous pass or design review."
            ),
        }
    ]
    if latest_review_note is not None:
        items.append(
            {
                "item_type": "obsidian_review_note",
                "summary": (
                    "Latest run review note is available as the raw-to-wiki "
                    "promotion source."
                ),
                "target_wiki_notes": target_wiki_notes,
                "source_artifact_ids": [str(latest_review_note.artifact_id)],
                "recommended_action": "Review the note before applying wiki updates.",
            }
        )
    if latest_retrieval is not None:
        items.append(
            {
                "item_type": "retrieval_quality",
                "summary": (
                    "Latest retrieval quality status is "
                    f"{latest_retrieval.content.get('status')} with "
                    f"{latest_retrieval.content.get('accepted_candidate_count', 0)} "
                    "accepted candidate(s)."
                ),
                "target_wiki_notes": [
                    "02-research/Retrieval Intelligence and Knowledge Graph Research.md"
                ],
                "source_artifact_ids": [str(latest_retrieval.artifact_id)],
                "recommended_action": (
                    "Promote stable retrieval lessons into the retrieval research note "
                    "only if the result changes ranking, coverage, or source policy."
                ),
            }
        )
    if latest_claim_revision is not None:
        items.append(
            {
                "item_type": "claim_revision",
                "summary": (
                    "Latest claim revision closure status is "
                    f"{latest_claim_revision.content.get('status')} with "
                    f"{latest_claim_revision.content.get('open_held_claim_count', 0)} "
                    "open held claim(s)."
                ),
                "target_wiki_notes": ["wiki/product/agent-studio-memory-layer.md"],
                "source_artifact_ids": [str(latest_claim_revision.artifact_id)],
                "recommended_action": (
                    "Promote repeat claim-failure patterns into agent memory only "
                    "after writer/editor follow-ups close or expose a durable gap."
                ),
            }
        )
    handoff = (
        latest_artifact_index.content.get("publishing_handoff")
        if latest_artifact_index
        else None
    )
    if isinstance(handoff, dict):
        items.append(
            {
                "item_type": "publishing_handoff",
                "summary": (
                    "Latest publishing handoff status is "
                    f"{handoff.get('status')} with "
                    f"{handoff.get('publishable_artifact_count', 0)} "
                    "publishable artifact(s)."
                ),
                "target_wiki_notes": ["wiki/product/agent-studio-memory-layer.md"],
                "source_artifact_ids": [str(latest_artifact_index.artifact_id)],
                "recommended_action": (
                    "Promote handoff blockers into wiki memory if they represent a "
                    "recurring product or agent-policy constraint."
                ),
            }
        )
    if feedback_items:
        items.append(
            {
                "item_type": "human_feedback",
                "summary": (
                    f"{len(feedback_items)} open/routed feedback item(s) should be "
                    "reviewed for stable user preference or product constraint memory."
                ),
                "target_wiki_notes": [
                    "wiki/ops/codex-obsidian-working-memory.md",
                    "03-review-packets/Feedback Inbox.md",
                ],
                "source_artifact_ids": [],
                "recommended_action": (
                    "Promote durable preference changes to wiki; keep one-off requests "
                    "in raw feedback only."
                ),
            }
        )
    if audits:
        non_approved_count = sum(
            1 for audit in audits if getattr(audit.status, "value", audit.status) != "approved"
        )
        items.append(
            {
                "item_type": "guardrail_audits",
                "summary": (
                    f"{len(audits)} guardrail audit(s) exist; {non_approved_count} "
                    "are not approved."
                ),
                "target_wiki_notes": ["wiki/product/agent-studio-memory-layer.md"],
                "source_artifact_ids": [],
                "recommended_action": (
                    "Promote recurring guardrail failures into policy memory, not "
                    "one-off audit noise."
                ),
            }
        )
    return items


def _render_promotion_note(
    *,
    title: str,
    promotion_kind: str,
    run,
    events,
    promoted_items: list[dict[str, Any]],
    target_wiki_notes: list[str],
    latest_review_note: ArtifactRecord | None,
) -> str:
    lines = [
        "---",
        f"type: {promotion_kind}",
        "project: agent-studio",
        f"run_id: {run.run_id}",
        "status: proposed",
        f"updated: {datetime.now(timezone.utc).date().isoformat()}",
        "owner: interactive-note-taking-agent",
        "---",
        "",
        f"# {_clean_line(title)}",
        "",
        "Links: [[../../SCHEMA]] | [[../_index]] | [[../product/agent-studio-memory-layer]] | [[../ops/codex-obsidian-working-memory]]",
        "",
        "## Source Run",
        "",
        f"- Run id: `{run.run_id}`",
        f"- Goal: {_clean_line(run.goal)}",
        f"- Status: `{run.status.value}`",
        f"- Event sample: `{len(events)}` event(s)",
        "",
        "## Target Wiki Notes",
        "",
    ]
    for note in target_wiki_notes:
        lines.append(f"- `{note}`")
    if latest_review_note is not None:
        lines.extend(
            [
                "",
                "## Review Note Source",
                "",
                f"- Artifact id: `{latest_review_note.artifact_id}`",
                f"- URI: `{latest_review_note.uri}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Promoted Memory Candidates",
            "",
            "| Type | Summary | Target | Recommended action |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in promoted_items:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{_cell(item['item_type'])}`",
                    _cell(item["summary"]),
                    _cell(", ".join(item.get("target_wiki_notes", []))),
                    _cell(item["recommended_action"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Source Artifact Ids",
            "",
        ]
    )
    source_artifact_ids = _source_artifact_ids(promoted_items)
    if source_artifact_ids:
        for artifact_id in source_artifact_ids:
            lines.append(f"- `{artifact_id}`")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Promotion Rules",
            "",
            "- Apply to wiki only when the candidate changes durable project knowledge.",
            "- Keep one-off observations in raw notes or run review packets.",
            "- Regenerate output viewers after wiki memory changes.",
            "- Do not use this note as publishable content evidence.",
        ]
    )
    return "\n".join(lines) + "\n"


def _latest_artifact_of_type(
    artifacts: list[ArtifactRecord],
    artifact_type: ArtifactType,
) -> ArtifactRecord | None:
    candidates = [
        artifact for artifact in artifacts if artifact.artifact_type == artifact_type
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda artifact: artifact.created_at)


def _source_artifact_ids(items: list[dict[str, Any]]) -> list[str]:
    artifact_ids = []
    for item in items:
        for artifact_id in item.get("source_artifact_ids", []):
            if artifact_id and artifact_id not in artifact_ids:
                artifact_ids.append(artifact_id)
    return artifact_ids


def _slug(value: str) -> str:
    slug = "".join(char.lower() if char.isalnum() else "-" for char in value)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "memory-promotion"


def _clean_line(value: Any) -> str:
    return str(value).replace("\n", " ").strip()


def _cell(value: Any) -> str:
    return _clean_line(value).replace("|", "\\|")

