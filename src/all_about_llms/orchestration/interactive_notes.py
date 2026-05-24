import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any
from uuid import UUID

from all_about_llms.contracts import (
    ArtifactRecord,
    ArtifactType,
    InteractiveRunNoteRequest,
    InteractiveRunNoteResult,
    RunEvent,
)
from all_about_llms.realtime_safety import (
    redact_realtime_string,
    safe_realtime_metadata_value,
)


class InteractiveRunNoteRunNotFoundError(RuntimeError):
    """Raised when an interactive note is requested for a missing run."""


class InteractiveRunNoteWorkflow:
    """Create an interactive HTML knowledge surface for a durable run."""

    def __init__(self, store, artifacts_root: Path):
        self._store = store
        self._artifacts_root = artifacts_root

    async def generate(
        self,
        run_id: UUID,
        request: InteractiveRunNoteRequest,
    ) -> InteractiveRunNoteResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise InteractiveRunNoteRunNotFoundError(f"Run not found: {run_id}")

        state = {
            "run": run.model_dump(mode="json"),
            "conversation_turns": [
                turn.model_dump(mode="json")
                for turn in await self._store.list_conversation_turns(run_id)
            ],
            "agent_messages": [
                message.model_dump(mode="json")
                for message in await self._store.list_agent_messages(run_id)
            ],
            "sources": [
                source.model_dump(mode="json")
                for source in await self._store.list_sources(run_id)
            ],
            "claims": [
                claim.model_dump(mode="json")
                for claim in await self._store.list_claims(run_id)
            ],
            "artifacts": [
                artifact.model_dump(mode="json")
                for artifact in await self._store.list_artifacts(run_id)
            ],
            "feedback": [
                feedback.model_dump(mode="json")
                for feedback in await self._store.list_feedback(run_id)
            ],
            "guardrail_audits": [
                audit.model_dump(mode="json")
                for audit in await self._store.list_guardrail_audits(run_id)
            ],
        }
        events = await self._store.list_events(run_id)
        state["events"] = [
            _event_payload(event.model_dump(mode="json"), request.include_event_payloads)
            for event in events
        ]
        summary = {
            "turns": len(state["conversation_turns"]),
            "tasks": len(state["agent_messages"]),
            "sources": len(state["sources"]),
            "claims": len(state["claims"]),
            "artifacts": len(state["artifacts"]),
            "feedback": len(state["feedback"]),
            "events": len(state["events"]),
            "guardrail_audits": len(state["guardrail_audits"]),
        }
        content_readiness = _content_readiness_packet(state)
        summary.update(
            {
                "content_status": content_readiness["status"],
                "publishable_artifacts": content_readiness["metrics"][
                    "publishable_artifact_count"
                ],
                "open_feedback_gates": content_readiness["metrics"][
                    "open_feedback_count"
                ],
                "unsupported_claims": content_readiness["metrics"][
                    "unsupported_claim_count"
                ],
            }
        )
        state["summary"] = summary
        state["content_readiness"] = content_readiness
        embedded_state = _safe_embedded_note_state(state)

        note_title = redact_realtime_string(
            request.title or f"Interactive run note: {run.goal}"
        )
        note_dir = self._artifacts_root / "runs" / str(run_id) / "notes"
        note_dir.mkdir(parents=True, exist_ok=True)
        note_path = note_dir / "interactive-run-note.html"
        note_path.write_text(
            _render_note_html(note_title, embedded_state), encoding="utf-8"
        )

        uri = f"/artifacts/runs/{run_id}/notes/interactive-run-note.html"
        artifact = ArtifactRecord(
            run_id=run_id,
            artifact_type=ArtifactType.HTML_NOTE,
            title=note_title,
            uri=uri,
            content={
                "summary": summary,
                "html_sections": [
                    "overview",
                    "content_readiness",
                    "timeline",
                    "conversation",
                    "sources",
                    "tasks",
                    "feedback",
                    "artifacts",
                ],
            },
            provenance={
                "workflow": "interactive_run_note_v1",
                "agent_id": "interactive-note-taking-agent",
                "source": "durable_run_state",
                "include_event_payloads": request.include_event_payloads,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
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
                event_type="interactive_note_generated",
                actor="interactive-note-taking-agent",
                payload={
                    "artifact_id": str(artifact.artifact_id),
                    "uri": uri,
                    "summary": summary,
                    "content_readiness_status": content_readiness["status"],
                    "content_readiness_issue_count": len(
                        [
                            check
                            for check in content_readiness["checks"]
                            if check["status"] != "pass"
                        ]
                    ),
                },
            )
        )
        return InteractiveRunNoteResult(
            run_id=run_id,
            artifact_id=artifact.artifact_id,
            uri=uri,
            file_path=str(note_path),
            event_id=event.event_id,
            summary=(
                f"Generated interactive HTML run note with {summary['events']} "
                f"event(s), {summary['tasks']} task(s), and "
                f"{summary['artifacts']} prior artifact(s)."
            ),
        )


PUBLISHABLE_ARTIFACT_TYPES = {
    "post",
    "reel_script",
    "substack_article",
    "social_package",
    "visual_brief",
    "image",
    "audio",
    "video",
}


def _event_payload(event: dict, include_payload: bool) -> dict:
    if include_payload:
        return event
    return {
        "event_id": event["event_id"],
        "event_type": event["event_type"],
        "actor": event["actor"],
        "created_at": event["created_at"],
    }


def _safe_embedded_note_state(state: dict[str, Any]) -> dict[str, Any]:
    return safe_realtime_metadata_value(state)


def _content_readiness_packet(state: dict[str, Any]) -> dict[str, Any]:
    artifacts = state["artifacts"]
    publishable = [
        artifact
        for artifact in artifacts
        if artifact.get("artifact_type") in PUBLISHABLE_ARTIFACT_TYPES
    ]
    missing_source_artifacts = [
        artifact
        for artifact in publishable
        if not _artifact_has_source_dependencies(artifact)
    ]
    missing_claim_artifacts = [
        artifact
        for artifact in publishable
        if not _artifact_claim_ids(artifact)
    ]
    missing_reviewer_artifacts = [
        artifact for artifact in publishable if not artifact.get("reviewer_decisions")
    ]
    unsupported_claims = [
        claim
        for claim in state["claims"]
        if claim.get("support_status") == "unsupported"
    ]
    needs_review_claims = [
        claim
        for claim in state["claims"]
        if claim.get("support_status") == "needs_review"
    ]
    open_feedback = [
        feedback
        for feedback in state["feedback"]
        if feedback.get("status") in {"open", "routed"}
    ]
    gated_tasks = [
        message
        for message in state["agent_messages"]
        if message.get("requires_human_feedback")
        and message.get("status") not in {"completed", "canceled"}
    ]
    gate_events = [
        event
        for event in state["events"]
        if event.get("event_type") == "human_feedback_gate_opened"
    ]
    feedback_gate_count = max(len(open_feedback), len(gated_tasks), len(gate_events))
    guardrail_status_counts = _value_counts(
        str(audit.get("status") or "unknown") for audit in state["guardrail_audits"]
    )
    checks = [
        _readiness_check(
            check_id="publishable-artifacts",
            title="Publishable artifacts exist",
            status="pass" if publishable else "needs_attention",
            owner_agent_id="content-strategist",
            detail=f"{len(publishable)} publishable artifact(s) found.",
        ),
        _readiness_check(
            check_id="source-dependencies",
            title="Artifacts carry source dependencies",
            status="pass" if not missing_source_artifacts else "blocked",
            owner_agent_id="source-ledger-agent",
            detail=(
                f"{len(missing_source_artifacts)} publishable artifact(s) lack source dependency evidence."
            ),
            artifact_ids=[
                str(artifact.get("artifact_id"))
                for artifact in missing_source_artifacts
            ],
        ),
        _readiness_check(
            check_id="claim-traceability",
            title="Artifacts carry claim traces",
            status="pass" if not missing_claim_artifacts else "blocked",
            owner_agent_id="claim-verification-agent",
            detail=(
                f"{len(missing_claim_artifacts)} publishable artifact(s) lack claim traceability."
            ),
            artifact_ids=[
                str(artifact.get("artifact_id"))
                for artifact in missing_claim_artifacts
            ],
        ),
        _readiness_check(
            check_id="claim-support",
            title="Claims are supported or ready for review",
            status="pass" if not unsupported_claims else "blocked",
            owner_agent_id="claim-verification-agent",
            detail=(
                f"{len(unsupported_claims)} unsupported claim(s), "
                f"{len(needs_review_claims)} claim(s) need review."
            ),
            claim_ids=[str(claim.get("claim_id")) for claim in unsupported_claims],
        ),
        _readiness_check(
            check_id="reviewer-decisions",
            title="Artifacts have reviewer decisions",
            status="pass" if not missing_reviewer_artifacts else "needs_attention",
            owner_agent_id="editor-in-chief",
            detail=(
                f"{len(missing_reviewer_artifacts)} publishable artifact(s) lack reviewer decisions."
            ),
            artifact_ids=[
                str(artifact.get("artifact_id"))
                for artifact in missing_reviewer_artifacts
            ],
        ),
        _readiness_check(
            check_id="feedback-gates",
            title="Human feedback gates are clear",
            status="pass" if feedback_gate_count == 0 else "needs_attention",
            owner_agent_id="forward-deployed-engineer",
            detail=f"{feedback_gate_count} open feedback gate signal(s).",
            feedback_ids=[
                str(feedback.get("feedback_id")) for feedback in open_feedback
            ],
            gated_task_ids=[
                str(message.get("message_id")) for message in gated_tasks
            ],
        ),
        _readiness_check(
            check_id="guardrail-audits",
            title="Guardrail audits are present",
            status="pass" if state["guardrail_audits"] else "needs_attention",
            owner_agent_id="guardrails-agent",
            detail=f"{len(state['guardrail_audits'])} guardrail audit record(s).",
            status_counts=guardrail_status_counts,
        ),
    ]
    status = _readiness_status(checks)
    next_actions = _readiness_next_actions(checks)
    return {
        "status": status,
        "metrics": {
            "publishable_artifact_count": len(publishable),
            "source_backed_artifact_count": len(publishable)
            - len(missing_source_artifacts),
            "claim_linked_artifact_count": len(publishable)
            - len(missing_claim_artifacts),
            "unsupported_claim_count": len(unsupported_claims),
            "needs_review_claim_count": len(needs_review_claims),
            "open_feedback_count": feedback_gate_count,
            "guardrail_audit_count": len(state["guardrail_audits"]),
        },
        "checks": checks,
        "next_actions": next_actions,
    }


def _readiness_check(
    *,
    check_id: str,
    title: str,
    status: str,
    owner_agent_id: str,
    detail: str,
    **metadata: Any,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "title": title,
        "status": status,
        "owner_agent_id": owner_agent_id,
        "detail": detail,
        "metadata": {key: value for key, value in metadata.items() if value},
    }


def _artifact_has_source_dependencies(artifact: dict[str, Any]) -> bool:
    content = artifact.get("content") or {}
    return bool(artifact.get("source_ids") or content.get("source_citations"))


def _artifact_claim_ids(artifact: dict[str, Any]) -> list[str]:
    content = artifact.get("content") or {}
    provenance = artifact.get("provenance") or {}
    raw_claim_ids = [
        *content.get("claim_ids", []),
        *provenance.get("claim_ids", []),
    ]
    claim_trace = content.get("claim_trace") or provenance.get("claim_trace") or []
    if isinstance(claim_trace, list):
        for item in claim_trace:
            if isinstance(item, dict):
                raw_claim_ids.append(item.get("claim_id"))
            else:
                raw_claim_ids.append(item)
    return [str(claim_id) for claim_id in raw_claim_ids if claim_id]


def _readiness_status(checks: list[dict[str, Any]]) -> str:
    statuses = {check["status"] for check in checks}
    if "blocked" in statuses:
        return "blocked"
    if "needs_attention" in statuses:
        return "needs_attention"
    return "ready_for_publish_readiness"


def _readiness_next_actions(checks: list[dict[str, Any]]) -> list[dict[str, str]]:
    action_by_check = {
        "publishable-artifacts": "Generate source-backed post, reel, and Substack drafts.",
        "source-dependencies": "Run Web Research and Source Ledger repair before publishing.",
        "claim-traceability": "Run Claim Verification so every major claim maps to SourceRecord evidence.",
        "claim-support": "Remove, rewrite, or explicitly mark unsupported claims before publishing.",
        "reviewer-decisions": "Route drafts through Editor-in-Chief and Critic/Reviewer review.",
        "feedback-gates": "Resolve or route open human feedback before autonomous continuation.",
        "guardrail-audits": "Run Guardrails Agent and publish-readiness gates.",
    }
    actions = []
    for check in checks:
        if check["status"] == "pass":
            continue
        actions.append(
            {
                "type": "next_action",
                "status": check["status"],
                "owner_agent_id": check["owner_agent_id"],
                "title": action_by_check.get(
                    check["check_id"], f"Resolve {check['title']}."
                ),
                "reason": check["detail"],
            }
        )
    if not actions:
        actions.append(
            {
                "type": "next_action",
                "status": "pass",
                "owner_agent_id": "guardrails-agent",
                "title": "Run final publish readiness or continue with platform packaging.",
                "reason": "The interactive note did not find source, claim, feedback, or guardrail blockers.",
            }
        )
    return actions


def _value_counts(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _render_note_html(title: str, state: dict) -> str:
    json_blob = json.dumps(state, ensure_ascii=True).replace("</", "<\\/")
    escaped_title = escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>{escaped_title}</title>
  <style>
    :root {{
      --ink: #141820;
      --muted: #5d6875;
      --line: #d7e0e8;
      --paper: #f6f8fb;
      --panel: #ffffff;
      --teal: #11776f;
      --blue: #2d65c9;
      --amber: #a86600;
      --rose: #bf3f63;
      --green: #2f7a45;
      --shadow: 0 12px 32px rgba(18, 28, 40, 0.1);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--paper);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    header {{
      padding: 34px clamp(16px, 4vw, 56px) 20px;
      background: #ffffff;
      border-bottom: 1px solid var(--line);
      display: grid;
      gap: 12px;
    }}
    h1, h2, h3 {{ margin: 0; letter-spacing: 0; }}
    h1 {{ font-size: clamp(1.8rem, 4vw, 3.8rem); line-height: 0.98; }}
    h2 {{ font-size: 1.12rem; }}
    h3 {{ font-size: 0.92rem; }}
    p {{ margin: 0; color: var(--muted); line-height: 1.5; }}
    main {{
      padding: 18px clamp(12px, 3vw, 42px) 40px;
      display: grid;
      gap: 16px;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
      gap: 10px;
    }}
    .metric, .panel, .item {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: var(--shadow);
    }}
    .metric {{ padding: 14px; display: grid; gap: 6px; }}
    .metric strong {{ font-size: 1.7rem; color: var(--teal); }}
    .tabs, .filters {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    button {{
      border: 1px solid var(--line);
      background: #ffffff;
      color: var(--ink);
      border-radius: 8px;
      padding: 9px 11px;
      cursor: pointer;
      font: inherit;
    }}
    button.active {{ border-color: var(--blue); background: #edf4ff; }}
    .panel {{ padding: 16px; display: grid; gap: 12px; }}
    .readiness {{
      border-left: 5px solid var(--teal);
    }}
    .readiness-grid {{
      display: grid;
      grid-template-columns: minmax(180px, 0.8fr) minmax(220px, 1.2fr);
      gap: 12px;
    }}
    .status-box {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: #f9fbfd;
      display: grid;
      gap: 8px;
      align-content: start;
    }}
    .status-box strong {{
      font-size: 1.2rem;
      color: var(--teal);
      overflow-wrap: anywhere;
    }}
    .action-list {{
      display: grid;
      gap: 8px;
    }}
    .action {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #ffffff;
      display: grid;
      gap: 5px;
    }}
    .list {{ display: grid; gap: 10px; }}
    .item {{ padding: 12px; display: grid; gap: 7px; box-shadow: none; }}
    .tag {{
      width: fit-content;
      border-radius: 999px;
      padding: 5px 8px;
      background: #eef6f3;
      color: #0f655f;
      font-size: 0.76rem;
      font-weight: 700;
    }}
    code {{
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      color: #2f3b47;
      font-size: 0.78rem;
    }}
    .empty {{
      border: 1px dashed #c9d4df;
      border-radius: 8px;
      padding: 18px;
      text-align: center;
      color: var(--muted);
      background: #fbfdff;
    }}
    @media (max-width: 720px) {{
      header {{ padding-top: 24px; }}
      .readiness-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <span class="tag">Interactive Note-Taking Agent</span>
    <h1>{escaped_title}</h1>
    <p id="run-goal"></p>
  </header>
  <main>
    <section class="metrics" id="metrics"></section>
    <section class="panel readiness" id="readiness-panel"></section>
    <section class="panel">
      <div class="tabs" id="tabs"></div>
      <div class="filters" id="filters"></div>
      <div class="list" id="content"></div>
    </section>
  </main>
  <script id="run-note-data" type="application/json">{json_blob}</script>
  <script>
    const data = JSON.parse(document.getElementById("run-note-data").textContent);
    const sections = [
      ["content_readiness", "Readiness"],
      ["events", "Timeline"],
      ["conversation_turns", "Conversation"],
      ["agent_messages", "Agent Tasks"],
      ["sources", "Sources"],
      ["claims", "Claims"],
      ["feedback", "Feedback"],
      ["artifacts", "Artifacts"],
      ["guardrail_audits", "Guardrails"]
    ];
    let activeSection = "content_readiness";
    let activeFilter = "all";
    document.getElementById("run-goal").textContent = data.run.goal;

    function renderMetrics() {{
      const mount = document.getElementById("metrics");
      mount.replaceChildren();
      Object.entries(data.summary).forEach(([label, value]) => {{
        const card = document.createElement("article");
        card.className = "metric";
        card.innerHTML = `<strong>${{value}}</strong><span>${{label.replaceAll("_", " ")}}</span>`;
        mount.appendChild(card);
      }});
    }}

    function renderReadinessPanel() {{
      const readiness = data.content_readiness || {{}};
      const metrics = readiness.metrics || {{}};
      const actions = readiness.next_actions || [];
      const mount = document.getElementById("readiness-panel");
      const actionCards = actions.map((action) => `
        <article class="action">
          <span class="tag">${{escapeHtml(action.status || "next_action")}}</span>
          <h3>${{escapeHtml(action.title || "Next action")}}</h3>
          <p>${{escapeHtml(action.reason || "")}}</p>
          <code>${{escapeHtml(action.owner_agent_id || "product-manager")}}</code>
        </article>
      `).join("");
      mount.innerHTML = `
        <h2>Content readiness packet</h2>
        <div class="readiness-grid">
          <div class="status-box">
            <span class="tag">status</span>
            <strong>${{escapeHtml(readiness.status || "unknown")}}</strong>
            <p>${{metrics.publishable_artifact_count || 0}} publishable artifact(s), ${{metrics.open_feedback_count || 0}} open feedback gate(s), ${{metrics.unsupported_claim_count || 0}} unsupported claim(s).</p>
          </div>
          <div class="action-list">
            ${{actionCards || '<div class="empty">No next actions recorded.</div>'}}
          </div>
        </div>
      `;
    }}

    function renderTabs() {{
      const mount = document.getElementById("tabs");
      mount.replaceChildren();
      sections.forEach(([key, label]) => {{
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = label;
        button.className = key === activeSection ? "active" : "";
        button.addEventListener("click", () => {{
          activeSection = key;
          activeFilter = "all";
          renderTabs();
          renderFilters();
          renderContent();
        }});
        mount.appendChild(button);
      }});
    }}

    function renderFilters() {{
      const mount = document.getElementById("filters");
      mount.replaceChildren();
      const rows = sectionRows();
      const values = new Set(["all"]);
      rows.forEach((row) => values.add(row.status || row.event_type || row.artifact_type || row.modality || row.type || "record"));
      values.forEach((value) => {{
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = value;
        button.className = value === activeFilter ? "active" : "";
        button.addEventListener("click", () => {{
          activeFilter = value;
          renderFilters();
          renderContent();
        }});
        mount.appendChild(button);
      }});
    }}

    function renderContent() {{
      const mount = document.getElementById("content");
      mount.replaceChildren();
      const rows = sectionRows().filter((row) => {{
        if (activeFilter === "all") return true;
        return [row.status, row.event_type, row.artifact_type, row.modality, row.type, "record"].includes(activeFilter);
      }});
      if (!rows.length) {{
        const empty = document.createElement("div");
        empty.className = "empty";
        empty.textContent = "No records in this section.";
        mount.appendChild(empty);
        return;
      }}
      rows.forEach((row) => {{
        const item = document.createElement("article");
        item.className = "item";
        const title = row.event_type || row.task_type || row.title || row.feedback_text || row.claim_text || row.transcript || row.citation_id || row.status || "record";
        const tag = row.actor || row.status || row.artifact_type || row.modality || row.publisher || row.recipient_agent_id || row.owner_agent_id || "record";
        item.innerHTML = `
          <span class="tag">${{escapeHtml(tag)}}</span>
          <h3>${{escapeHtml(title)}}</h3>
          <code>${{escapeHtml(JSON.stringify(row, null, 2))}}</code>
        `;
        mount.appendChild(item);
      }});
    }}

    function sectionRows() {{
      if (activeSection !== "content_readiness") {{
        return data[activeSection] || [];
      }}
      const readiness = data.content_readiness || {{}};
      const checks = (readiness.checks || []).map((check) => ({{
        ...check,
        type: "readiness_check"
      }}));
      const actions = (readiness.next_actions || []).map((action) => ({{
        ...action,
        type: action.type || "next_action"
      }}));
      return [...checks, ...actions];
    }}

    function escapeHtml(value) {{
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }}

    renderMetrics();
    renderReadinessPanel();
    renderTabs();
    renderFilters();
    renderContent();
  </script>
</body>
</html>
"""
