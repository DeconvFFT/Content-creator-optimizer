from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from all_about_llms.contracts import (
    AgentTaskStatus,
    ArtifactRecord,
    ArtifactType,
    FeedbackStatus,
    ObsidianReviewNoteRequest,
    ObsidianReviewNoteResult,
    RunEvent,
)
from all_about_llms.orchestration.source_quality import evaluate_source_quality


class ObsidianReviewNoteRunNotFoundError(RuntimeError):
    """Raised when an Obsidian note is requested for a missing run."""


class ObsidianReviewNoteWorkflow:
    """Write vault-native review notes from durable run state."""

    def __init__(self, store, vault_path: Path):
        self._store = store
        self._vault_path = vault_path

    async def generate(
        self,
        run_id: UUID,
        request: ObsidianReviewNoteRequest,
    ) -> ObsidianReviewNoteResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise ObsidianReviewNoteRunNotFoundError(f"Run not found: {run_id}")

        events = await self._store.list_events(run_id, limit=request.event_limit)
        messages = await self._store.list_agent_messages(run_id)
        sources = await self._store.list_sources(run_id)
        claims = await self._store.list_claims(run_id)
        artifacts = await self._store.list_artifacts(run_id)
        feedback_items = await self._store.list_feedback(run_id)
        audits = await self._store.list_guardrail_audits(run_id)

        latest_retrieval = _latest_artifact_of_type(
            artifacts,
            ArtifactType.RETRIEVAL_QUALITY_LEDGER,
        )
        latest_context_packet = _latest_artifact_of_type(
            artifacts,
            ArtifactType.CONTEXT_PACKET,
        )
        open_feedback = [
            item
            for item in feedback_items
            if item.status in {FeedbackStatus.OPEN, FeedbackStatus.ROUTED}
        ]
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
        summary = {
            "run_status": run.status.value,
            "events": len(events),
            "agent_messages": len(messages),
            "pending_agent_messages": len(pending_messages),
            "sources": len(sources),
            "claims": len(claims),
            "artifacts": len(artifacts),
            "open_feedback": len(open_feedback),
            "guardrail_audits": len(audits),
            "latest_retrieval_quality_status": (
                latest_retrieval.content.get("status") if latest_retrieval else None
            ),
            "latest_context_packet_id": (
                str(latest_context_packet.artifact_id)
                if latest_context_packet
                else None
            ),
        }

        note_title = request.title or f"Run review - {run.goal[:80]}"
        note_dir = self._vault_path / "03-review-packets" / "runs" / str(run_id)
        note_dir.mkdir(parents=True, exist_ok=True)
        note_path = note_dir / f"{_slug(request.note_kind)}.md"
        note_body = _render_obsidian_note(
            title=note_title,
            note_kind=request.note_kind,
            run=run,
            summary=summary,
            events=events if request.include_event_tail else [],
            messages=pending_messages,
            sources=sources,
            claims=claims,
            artifacts=artifacts,
            feedback_items=open_feedback,
            latest_retrieval=latest_retrieval,
            latest_context_packet=latest_context_packet,
        )
        note_path.write_text(note_body, encoding="utf-8")

        relative_note_path = note_path.relative_to(self._vault_path)
        uri = f"obsidian://agent-studio/{relative_note_path.as_posix()}"
        artifact = ArtifactRecord(
            run_id=run_id,
            artifact_type=ArtifactType.OBSIDIAN_NOTE,
            title=note_title,
            uri=uri,
            content={
                "note_kind": request.note_kind,
                "vault_path": str(self._vault_path),
                "relative_path": relative_note_path.as_posix(),
                "summary": summary,
                "sections": [
                    "run_snapshot",
                    "retrieval_quality",
                    "source_evidence",
                    "open_feedback",
                    "pending_a2a_work",
                    "recommended_next_actions",
                    "event_tail",
                ],
            },
            provenance={
                "workflow": "obsidian_review_note_v1",
                "agent_id": "interactive-note-taking-agent",
                "source": "durable_run_state",
                "note_kind": request.note_kind,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            revision_history=[
                {
                    "actor": "interactive-note-taking-agent",
                    "workflow": "obsidian_review_note_v1",
                    "note": "Wrote an Obsidian-native review note linked to durable run state.",
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
                event_type="obsidian_review_note_generated",
                actor="interactive-note-taking-agent",
                payload={
                    "artifact_id": str(artifact.artifact_id),
                    "uri": uri,
                    "file_path": str(note_path),
                    "note_kind": request.note_kind,
                    "summary": summary,
                },
            )
        )
        return ObsidianReviewNoteResult(
            run_id=run_id,
            artifact_id=artifact.artifact_id,
            uri=uri,
            file_path=str(note_path),
            note_kind=request.note_kind,
            event_id=event.event_id,
            summary=(
                f"Wrote Obsidian {request.note_kind} note with "
                f"{summary['sources']} source(s), {summary['claims']} claim(s), "
                f"and {summary['pending_agent_messages']} pending A2A task(s)."
            ),
        )


def _render_obsidian_note(
    *,
    title: str,
    note_kind: str,
    run,
    summary: dict[str, Any],
    events,
    messages,
    sources,
    claims,
    artifacts,
    feedback_items,
    latest_retrieval: ArtifactRecord | None,
    latest_context_packet: ArtifactRecord | None,
) -> str:
    lines = [
        "---",
        f"type: {note_kind}",
        "project: agent-studio",
        f"run_id: {run.run_id}",
        f"status: {run.status.value}",
        f"updated: {datetime.now(timezone.utc).date().isoformat()}",
        "owner: interactive-note-taking-agent",
        "---",
        "",
        f"# {_clean_line(title)}",
        "",
        "Links: [[Agent Studio MOC]] | [[00-system-design/HLD - Agent Studio]] | [[00-system-design/LLD - Agent Studio]] | [[01-work-tracking/Current Sprint]]",
        "",
        "## Run Snapshot",
        "",
        f"- Goal: {_clean_line(run.goal)}",
        f"- Status: `{run.status.value}`",
        f"- Sources: `{summary['sources']}`",
        f"- Claims: `{summary['claims']}`",
        f"- Artifacts: `{summary['artifacts']}`",
        f"- Open feedback: `{summary['open_feedback']}`",
        f"- Pending A2A tasks: `{summary['pending_agent_messages']}`",
        "",
        "## Retrieval Quality",
        "",
    ]
    lines.extend(_retrieval_quality_lines(latest_retrieval))
    lines.extend(
        [
            "",
            "## Source Evidence",
            "",
            "| Citation | Quality | Freshness | Title |",
            "| --- | --- | --- | --- |",
        ]
    )
    if sources:
        for source in sources[:12]:
            quality = evaluate_source_quality(source)
            lines.append(
                "| "
                + " | ".join(
                    [
                        _cell(source.citation_id),
                        f"`{quality.quality_status.value}`",
                        f"`{quality.freshness_status.value}`",
                        _cell(source.title),
                    ]
                )
                + " |"
            )
    else:
        lines.append("| none | n/a | n/a | No sources recorded yet. |")

    lines.extend(
        [
            "",
            "## Claim State",
            "",
            "| Status | Claim | Source Count |",
            "| --- | --- | --- |",
        ]
    )
    if claims:
        for claim in claims[:12]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{claim.support_status.value}`",
                        _cell(claim.claim_text[:140]),
                        str(len(claim.source_ids)),
                    ]
                )
                + " |"
            )
    else:
        lines.append("| n/a | No claims recorded yet. | 0 |")

    lines.extend(
        [
            "",
            "## Open Feedback",
            "",
        ]
    )
    if feedback_items:
        for feedback in feedback_items[:8]:
            lines.append(
                f"- `{feedback.status.value}` for `{feedback.target_agent_id or 'unassigned'}`: {_clean_line(feedback.feedback_text)}"
            )
    else:
        lines.append("- No open or routed feedback.")

    lines.extend(
        [
            "",
            "## Pending A2A Work",
            "",
        ]
    )
    if messages:
        for message in messages[:12]:
            lines.append(
                f"- `{message.status.value}` `{message.recipient_agent_id}`: `{message.task_type}`"
            )
    else:
        lines.append("- No pending A2A tasks.")

    lines.extend(
        [
            "",
            "## Latest Context Packet",
            "",
        ]
    )
    if latest_context_packet:
        packet_summary = latest_context_packet.content.get("summary", {})
        lines.extend(
            [
                f"- Artifact: `{latest_context_packet.artifact_id}`",
                f"- Context risks: `{packet_summary.get('context_risk_count', 0)}`",
                f"- Manifest items: `{packet_summary.get('context_manifest_items', 0)}`",
            ]
        )
    else:
        lines.append("- No context packet recorded yet.")

    lines.extend(
        [
            "",
            "## Recommended Next Actions",
            "",
        ]
    )
    lines.extend(_recommended_action_lines(latest_retrieval, feedback_items, messages))

    lines.extend(
        [
            "",
            "## Event Tail",
            "",
        ]
    )
    if events:
        for event in events[-12:]:
            lines.append(
                f"- `{event.event_id or 0}` `{event.event_type}` by `{event.actor}`"
            )
    else:
        lines.append("- Event tail omitted or empty.")

    lines.extend(
        [
            "",
            "## Artifact Index",
            "",
        ]
    )
    if artifacts:
        for artifact in artifacts[-12:]:
            lines.append(
                f"- `{artifact.artifact_type.value}` `{artifact.artifact_id}`: {_clean_line(artifact.title)}"
            )
    else:
        lines.append("- No artifacts recorded yet.")
    lines.append("")
    return "\n".join(lines)


def _retrieval_quality_lines(artifact: ArtifactRecord | None) -> list[str]:
    if artifact is None:
        return ["- No retrieval quality ledger recorded yet."]
    content = artifact.content
    lines = [
        f"- Artifact: `{artifact.artifact_id}`",
        f"- Status: `{content.get('status') or 'unknown'}`",
        f"- Topic: {_clean_line(str(content.get('topic') or 'unknown'))}",
        f"- Accepted candidates: `{content.get('accepted_candidate_count', 0)}/{content.get('candidate_count', 0)}`",
        f"- Precision risks: `{content.get('precision_risk_count', 0)}`",
        f"- Recall gaps: `{content.get('recall_gap_count', 0)}`",
        f"- Coverage gaps: `{content.get('coverage_gap_count', 0)}`",
    ]
    queries = content.get("recommended_queries") or []
    if queries:
        lines.append("- Recommended retrieval queries:")
        lines.extend(f"  - {_clean_line(str(query))}" for query in queries[:5])
    return lines


def _recommended_action_lines(
    latest_retrieval: ArtifactRecord | None,
    feedback_items,
    messages,
) -> list[str]:
    actions: list[str] = []
    if latest_retrieval is None:
        actions.append("Build the retrieval quality ledger before final synthesis.")
    elif latest_retrieval.content.get("status") not in {None, "ready"}:
        actions.append(
            "Review retrieval precision, recall, reranking, and graph coverage gaps."
        )
    if feedback_items:
        actions.append("Resolve open or routed feedback before autonomous publishing.")
    if messages:
        actions.append("Run or inspect pending A2A work before claiming completion.")
    if not actions:
        actions.append("Continue with provider-backed drafting or publishing readiness.")
    return [f"- {action}" for action in actions]


def _latest_artifact_of_type(
    artifacts: list[ArtifactRecord],
    artifact_type: ArtifactType,
) -> ArtifactRecord | None:
    for artifact in reversed(artifacts):
        if artifact.artifact_type == artifact_type:
            return artifact
    return None


def _slug(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum():
            allowed.append(char)
        elif char in {" ", "-", "_"}:
            allowed.append("-")
    slug = "".join(allowed).strip("-")
    return slug or "run-review"


def _clean_line(value: str) -> str:
    return " ".join(str(value).replace("|", "/").split())


def _cell(value: str) -> str:
    return _clean_line(value) or "n/a"
