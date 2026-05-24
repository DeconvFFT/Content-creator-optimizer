from pathlib import Path
from uuid import UUID

from all_about_llms.agents import AGENT_ROSTER, SKILL_CARDS
from all_about_llms.config import Settings, get_settings
from all_about_llms.contracts import (
    ArtifactRecord,
    ArtifactType,
    ClaimSupportStatus,
    FeedbackStatus,
    FoundationAuditCheck,
    FoundationAuditRequest,
    FoundationAuditResult,
    FoundationAuditStatus,
    RunEvent,
    WorkerProfileStatus,
)
from all_about_llms.foundation_references import list_foundation_references
from all_about_llms.model_routing import list_model_routes
from all_about_llms.orchestration.artifact_provenance import (
    artifact_provenance_issues,
)
from all_about_llms.orchestration.skill_usage import build_skill_source_contracts
from all_about_llms.providers.readiness import build_provider_readiness


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REQUIRED_FOUNDATION_PUBLISHERS = {
    "Google Developers Blog",
    "LangChain",
    "pgvector",
    "Hugging Face",
    "OpenAI",
    "ElevenLabs",
    "Cartesia",
    "Anthropic",
    "Martin Kleppmann",
    "O'Reilly",
    "Baseten",
    "AWS",
    "Google Cloud",
    "Uber Engineering",
    "Metaflow/Netflix",
    "LiveKit",
    "Pipecat",
}
PUBLISHABLE_ARTIFACT_TYPES = {
    ArtifactType.POST,
    ArtifactType.REEL_SCRIPT,
    ArtifactType.SUBSTACK_ARTICLE,
    ArtifactType.SOCIAL_PACKAGE,
}


class FoundationAuditError(RuntimeError):
    """Base error for foundation audit generation."""


class FoundationAuditRunNotFoundError(FoundationAuditError):
    """Raised when a run cannot be found for foundation audit work."""


class FoundationAuditWorkflow:
    """Audit foundation requirements against static contracts and run evidence."""

    def __init__(
        self,
        store,
        *,
        settings: Settings | None = None,
        project_root: Path | None = None,
    ):
        self._store = store
        self._settings = settings or get_settings()
        self._project_root = project_root or PROJECT_ROOT

    async def build(
        self, run_id: UUID, request: FoundationAuditRequest
    ) -> FoundationAuditResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise FoundationAuditRunNotFoundError(f"Run not found: {run_id}")

        events = await self._store.list_events(run_id, limit=request.event_limit)
        artifacts = await self._store.list_artifacts(run_id)
        sources = await self._store.list_sources(run_id)
        claims = await self._store.list_claims(run_id)
        feedback_items = await self._store.list_feedback(run_id)
        messages = await self._list_agent_messages(run_id)
        checkpoints = await self._list_run_checkpoints(run_id)
        realtime_sessions = await self._list_realtime_sessions(run_id)
        worker_profiles = await self._list_worker_profiles(run_id)

        checks = [
            _agent_roster_check(),
            _skill_coverage_check(),
            _skill_source_contract_check(self._project_root)
            if request.include_static_surface_checks
            else _skipped_check(
                "agent-skill-source-contracts",
                "Project skill source contracts",
                "agent-harness-engineer",
                "Static skill source inspection was skipped by request.",
            ),
            _model_routing_check(),
            _provider_contract_check(self._settings),
            _foundation_reference_check(),
            _persistence_schema_check(self._project_root)
            if request.include_static_surface_checks
            else _skipped_check(
                "durable-postgres-pgvector",
                "Durable Postgres and pgvector schema",
                "principal-software-engineer",
                "Static schema inspection was skipped by request.",
            ),
            _product_planning_boundary_check(self._project_root)
            if request.include_static_surface_checks
            else _skipped_check(
                "product-planning-boundary",
                "Product and planning surface boundary",
                "lead-ui-ux-designer",
                "Static HTML boundary inspection was skipped by request.",
            ),
            _runtime_event_log_check(events),
            _realtime_dialogue_check(realtime_sessions, artifacts, events),
            _source_grounding_check(artifacts, sources, claims),
            _research_freshness_check(artifacts, events),
            _feedback_gate_check(feedback_items, messages, artifacts, events),
            _model_routing_ledger_check(artifacts, events),
            _provider_ops_check(artifacts, events),
            _long_running_harness_check(
                checkpoints, worker_profiles, artifacts, events
            ),
            _worker_profile_heartbeat_evidence_check(
                worker_profiles, artifacts, events
            ),
            _context_and_notes_check(artifacts, events),
            _post_audit_coordination_loop_check(artifacts, messages, events),
        ]

        pass_count = sum(
            1 for check in checks if check.status == FoundationAuditStatus.PASS
        )
        needs_attention_count = sum(
            1
            for check in checks
            if check.status == FoundationAuditStatus.NEEDS_ATTENTION
        )
        fail_count = sum(
            1 for check in checks if check.status == FoundationAuditStatus.FAIL
        )
        remediation_items = _remediation_items(checks)
        status = _overall_status(fail_count, needs_attention_count)
        result = FoundationAuditResult(
            run_id=run_id,
            status=status,
            check_count=len(checks),
            pass_count=pass_count,
            needs_attention_count=needs_attention_count,
            fail_count=fail_count,
            completion_score=round(pass_count / len(checks), 3),
            checks=checks,
            remediation_items=remediation_items,
            remediation_count=len(remediation_items),
            blocking_remediation_count=sum(
                1 for item in remediation_items if item["blocking"]
            ),
            summary=(
                f"Foundation audit: {pass_count}/{len(checks)} checks pass, "
                f"{needs_attention_count} need attention, {fail_count} fail."
            ),
        )

        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.FOUNDATION_AUDIT,
                title="Foundation requirements audit",
                uri=f"artifact://runs/{run_id}/foundation-audit",
                content=result.model_dump(
                    mode="json", exclude={"audit_artifact_id", "event_id"}
                ),
                provenance={
                    "workflow": "foundation_audit_v1",
                    "agent_id": "product-manager",
                    "event_limit": request.event_limit,
                    "include_static_surface_checks": (
                        request.include_static_surface_checks
                    ),
                },
                revision_history=[
                    {
                        "actor": "product-manager",
                        "note": "Audited the foundation spec against static contracts and durable run evidence.",
                    }
                ],
            )
            result.audit_artifact_id = artifact.artifact_id
            artifact.content["audit_artifact_id"] = str(artifact.artifact_id)
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
                event_type="foundation_audit_built",
                actor="product-manager",
                payload={
                    "status": result.status.value,
                    "check_count": result.check_count,
                    "pass_count": result.pass_count,
                    "needs_attention_count": result.needs_attention_count,
                    "fail_count": result.fail_count,
                    "completion_score": result.completion_score,
                    "remediation_count": result.remediation_count,
                    "blocking_remediation_count": (
                        result.blocking_remediation_count
                    ),
                    "remediation_owner_agent_ids": sorted(
                        {
                            item["owner_agent_id"]
                            for item in result.remediation_items
                        }
                    ),
                    "audit_artifact_id": (
                        str(result.audit_artifact_id)
                        if result.audit_artifact_id
                        else None
                    ),
                },
            )
        )
        result.event_id = event.event_id
        return result

    async def _list_agent_messages(self, run_id: UUID):
        if not hasattr(self._store, "list_agent_messages"):
            return []
        return await self._store.list_agent_messages(run_id, limit=500)

    async def _list_run_checkpoints(self, run_id: UUID):
        if not hasattr(self._store, "list_run_checkpoints"):
            return []
        return await self._store.list_run_checkpoints(run_id, limit=50)

    async def _list_realtime_sessions(self, run_id: UUID):
        if not hasattr(self._store, "list_realtime_sessions"):
            return []
        return await self._store.list_realtime_sessions(run_id)

    async def _list_worker_profiles(self, run_id: UUID):
        if not hasattr(self._store, "list_worker_profiles"):
            return []
        return await self._store.list_worker_profiles(run_id)


def _agent_roster_check() -> FoundationAuditCheck:
    missing = []
    if len(AGENT_ROSTER) != 38:
        missing.append(f"Expected 38 foundation agents, found {len(AGENT_ROSTER)}.")
    agents_missing_skills = [agent.id for agent in AGENT_ROSTER if not agent.skill_ids]
    if agents_missing_skills:
        missing.append(
            "Agents missing project skill ids: " + ", ".join(agents_missing_skills)
        )
    agents_missing_tools = [
        agent.id
        for agent in AGENT_ROSTER
        if agent.id == "image-generation-agent"
        and agent.allowed_tools != ["imagegen"]
    ]
    if agents_missing_tools:
        missing.append("Image Generation Agent must be restricted to imagegen.")
    return FoundationAuditCheck(
        check_id="agent-roster-a2a-cards",
        title="A2A agent roster",
        status=_status(missing, hard_fail=True),
        owner_agent_id="a2a-protocol-agent",
        requirement=(
            "Every specialist has an A2A-style agent card with capabilities, "
            "allowed models, allowed tools, handoff rules, guardrails, and skill ids."
        ),
        evidence=[
            f"{len(AGENT_ROSTER)} agent cards registered.",
            "All cards are pydantic AgentCard contracts.",
        ],
        missing=missing,
    )


def _skill_coverage_check() -> FoundationAuditCheck:
    roster_ids = {agent.id for agent in AGENT_ROSTER}
    covered_agent_ids = {
        agent_id for skill in SKILL_CARDS for agent_id in skill.applies_to_agents
    }
    missing = []
    if len(SKILL_CARDS) != 9:
        missing.append(f"Expected 9 project skill cards, found {len(SKILL_CARDS)}.")
    uncovered = sorted(roster_ids - covered_agent_ids)
    extra = sorted(covered_agent_ids - roster_ids)
    if uncovered:
        missing.append("Agents without skill coverage: " + ", ".join(uncovered))
    if extra:
        missing.append("Skill cards reference unknown agents: " + ", ".join(extra))
    return FoundationAuditCheck(
        check_id="agent-skill-coverage",
        title="Project skill coverage",
        status=_status(missing, hard_fail=True),
        owner_agent_id="agent-harness-engineer",
        requirement=(
            "All agents receive project-owned skills that define workflows, "
            "required inputs, outputs, and guardrails."
        ),
        evidence=[
            f"{len(SKILL_CARDS)} skill cards registered.",
            f"{len(covered_agent_ids & roster_ids)} agent ids covered by skills.",
        ],
        missing=missing,
    )


def _skill_source_contract_check(project_root: Path) -> FoundationAuditCheck:
    source_contracts = build_skill_source_contracts(project_root)
    issue_count = sum(entry.issue_count for entry in source_contracts)
    missing = [
        f"{entry.skill_id}: " + "; ".join(entry.issues)
        for entry in source_contracts
        if entry.issue_count
    ]
    return FoundationAuditCheck(
        check_id="agent-skill-source-contracts",
        title="Project skill source contracts",
        status=_status(missing, hard_fail=True),
        owner_agent_id="agent-harness-engineer",
        requirement=(
            "Advertised project skill cards must have matching SKILL.md source "
            "files, frontmatter ids, descriptions, agents/openai manifests, and "
            "known agent mappings before they can be treated as executable "
            "specialist workflows."
        ),
        evidence=[
            f"{len(source_contracts)} skill source contract(s) audited.",
            f"{issue_count} issue(s) detected.",
        ],
        missing=missing,
    )


def _model_routing_check() -> FoundationAuditCheck:
    routes = {route.task: route for route in list_model_routes()}
    required_tasks = {
        "live_conversation",
        "deep_reasoning_and_planning",
        "fast_routing_and_triage",
        "vision_and_multimodal_review",
        "raster_visual_generation",
    }
    missing = []
    missing_tasks = sorted(required_tasks - set(routes))
    if missing_tasks:
        missing.append("Missing model routes: " + ", ".join(missing_tasks))
    live_route = routes.get("live_conversation")
    if live_route and "Gemma" in live_route.primary_model:
        missing.append("Live conversation must not route through Gemma 4 directly.")
    deep_route = routes.get("deep_reasoning_and_planning")
    if deep_route and "gemma-4" not in deep_route.primary_model:
        missing.append("Deep reasoning route must use a Gemma 4 expert endpoint.")
    image_route = routes.get("raster_visual_generation")
    if image_route and "imagegen" not in image_route.primary_model:
        missing.append("Raster visual generation must stay on the imagegen boundary.")
    return FoundationAuditCheck(
        check_id="model-routing-boundaries",
        title="Model routing boundaries",
        status=_status(missing, hard_fail=True),
        owner_agent_id="principal-software-engineer",
        requirement=(
            "Realtime voice providers handle dialogue transport, Gemma 4 handles "
            "expert reasoning, and imagegen is used only for raster visuals."
        ),
        evidence=[f"{len(routes)} model route contracts registered."],
        missing=missing,
    )


def _provider_contract_check(settings: Settings) -> FoundationAuditCheck:
    readiness = build_provider_readiness(settings)
    provider_types = {provider.provider_type for provider in readiness.providers}
    provider_ids = {provider.provider_id for provider in readiness.providers}
    missing = []
    if "gemma4_hf_endpoint" not in provider_types:
        missing.append("Gemma 4 Hugging Face endpoint readiness is not represented.")
    if "gemma4-realtime" not in provider_ids:
        missing.append("Gemma/Kokoro realtime provider missing from readiness.")
    if "open-source-realtime" not in provider_ids:
        missing.append("Open-source realtime fallback provider missing from readiness.")
    if not {"tavily-search", "serpapi-search"} & provider_ids:
        missing.append("At least one web-search readiness provider must be present.")
    if "imagegen" not in provider_ids:
        missing.append("Imagegen tool boundary is not represented.")
    return FoundationAuditCheck(
        check_id="provider-readiness-contract",
        title="Provider readiness contract",
        status=_status(missing, hard_fail=True),
        owner_agent_id="observability-agent",
        requirement=(
            "Gemma 4 HF endpoints, Gemma/Kokoro realtime audio, web search, and "
            "imagegen boundaries are visible through non-secret readiness metadata."
        ),
        evidence=[
            readiness.summary,
            f"Provider ids: {', '.join(sorted(provider_ids))}.",
        ],
        missing=missing,
    )


def _foundation_reference_check() -> FoundationAuditCheck:
    references = list_foundation_references()
    publishers = set(references.required_publishers)
    missing_publishers = sorted(REQUIRED_FOUNDATION_PUBLISHERS - publishers)
    missing = []
    if missing_publishers:
        missing.append(
            "Missing official foundation publishers: "
            + ", ".join(missing_publishers)
        )
    if len(references.references) < 18:
        missing.append(
            f"Expected at least 18 official references, found {len(references.references)}."
        )
    return FoundationAuditCheck(
        check_id="foundation-reference-ledger",
        title="Foundation reference ledger",
        status=_status(missing, hard_fail=True),
        owner_agent_id="context-engineering-agent",
        requirement=(
            "Official Google, LangGraph/LangChain, pgvector, Hugging Face, "
            "LiveKit transport guidance, optional Pipecat pipeline guidance, OpenAI agent guidance, Anthropic, data-systems, "
            "ML-systems, inference, and reliability guidance is mapped to "
            "architecture decisions."
        ),
        evidence=[
            f"{len(references.references)} reference records registered.",
            references.summary,
        ],
        missing=missing,
    )


def _persistence_schema_check(project_root: Path) -> FoundationAuditCheck:
    schema_path = project_root / "infra" / "postgres" / "001_foundation.sql"
    schema = _read_text(schema_path)
    missing = []
    if schema is None:
        missing.append(f"Missing schema file: {schema_path}")
    else:
        required_tokens = [
            "create extension if not exists vector",
            "create table if not exists runs",
            "create table if not exists run_events",
            "create table if not exists run_checkpoints",
            "create table if not exists agent_memories",
            "embedding vector",
        ]
        for token in required_tokens:
            if token not in schema.lower():
                missing.append(f"Schema missing token: {token}")
        if "sqlite" in schema.lower():
            missing.append("Schema must not contain SQLite fallback references.")
    return FoundationAuditCheck(
        check_id="durable-postgres-pgvector",
        title="Durable Postgres and pgvector schema",
        status=_status(missing, hard_fail=True),
        owner_agent_id="principal-software-engineer",
        requirement=(
            "Postgres plus pgvector is the v1 durable store for runs, events, "
            "checkpoints, artifacts, feedback, memories, and semantic retrieval."
        ),
        evidence=[
            "infra/postgres/001_foundation.sql is the local-first durable schema."
            if schema
            else "Schema file was not readable."
        ],
        missing=missing,
    )


def _product_planning_boundary_check(project_root: Path) -> FoundationAuditCheck:
    cockpit = _read_text(project_root / "frontend" / "cockpit" / "index.html")
    planning = _read_text(project_root / "planning" / "foundation-system-design.html")
    banned_board_term = "Kan" + "ban"
    missing = []
    if cockpit is None:
        missing.append("Product cockpit HTML is missing.")
    else:
        if 'data-product-boundary="live-conversational-studio"' not in cockpit:
            missing.append("Cockpit missing live conversational studio boundary marker.")
        if "foundation-data" in cockpit:
            missing.append("Cockpit must not embed planning foundation-data JSON.")
        if banned_board_term in cockpit:
            missing.append("Cockpit must not expose project-management board UI.")
    if planning is None:
        missing.append("Separate planning HTML artifact is missing.")
    else:
        if "foundation-data" not in planning:
            missing.append("Planning HTML missing embedded foundation-data JSON.")
        if "This is the separate planning workspace" not in planning:
            missing.append("Planning HTML missing explicit separate-workspace marker.")
        if banned_board_term in planning:
            missing.append("Planning HTML must not use project-board language.")
    return FoundationAuditCheck(
        check_id="product-planning-boundary",
        title="Product and planning surface boundary",
        status=_status(missing, hard_fail=True),
        owner_agent_id="lead-ui-ux-designer",
        requirement=(
            "The product app is a live conversational studio, while the animated "
            "architecture workspace remains a separate planning artifact."
        ),
        evidence=[
            "Cockpit and planning HTML boundary markers were inspected."
            if cockpit and planning
            else "One or more HTML surfaces could not be read."
        ],
        missing=missing,
    )


def _runtime_event_log_check(events: list[RunEvent]) -> FoundationAuditCheck:
    missing = []
    if not events:
        missing.append("No run events have been recorded yet.")
    event_types = {event.event_type for event in events}
    return FoundationAuditCheck(
        check_id="runtime-event-log",
        title="Durable run event log",
        status=_status(missing),
        owner_agent_id="agent-harness-engineer",
        requirement=(
            "Every run keeps an inspectable event history for time travel, "
            "debugging, feedback loops, and fault recovery."
        ),
        evidence=[
            f"{len(events)} event(s) inspected.",
            "Event types: " + ", ".join(sorted(event_types)[:12]) + "."
            if event_types
            else "No event types available.",
        ],
        missing=missing,
    )


def _realtime_dialogue_check(realtime_sessions, artifacts, events: list[RunEvent]):
    event_types = {event.event_type for event in events}
    has_dialogue_ledger = any(
        artifact.artifact_type == ArtifactType.REALTIME_DIALOGUE_LEDGER
        for artifact in artifacts
    ) or "realtime_dialogue_ledger_built" in event_types
    missing = []
    if not realtime_sessions and not (
        {"realtime_session_created", "realtime_turn_routed"} & event_types
    ):
        missing.append("No realtime session or realtime routed turn evidence yet.")
    if realtime_sessions and not has_dialogue_ledger:
        missing.append("Realtime session evidence exists without a dialogue ledger.")
    return FoundationAuditCheck(
        check_id="realtime-dialogue-loop",
        title="Realtime dialogue loop",
        status=_status(missing),
        owner_agent_id="realtime-conversation-host",
        requirement=(
            "The system supports natural back-and-forth voice/text dialogue, "
            "turn routing, interruptions, and durable session metadata."
        ),
        evidence=[
            f"{len(realtime_sessions)} realtime session record(s) inspected.",
            f"Realtime dialogue ledger present={has_dialogue_ledger}.",
            "Realtime events present."
            if {"realtime_session_created", "realtime_turn_routed"} & event_types
            else "Realtime events not present in this run yet.",
        ],
        missing=missing,
    )


def _source_grounding_check(artifacts, sources, claims) -> FoundationAuditCheck:
    publishable = [
        artifact
        for artifact in artifacts
        if artifact.artifact_type in PUBLISHABLE_ARTIFACT_TYPES
    ]
    missing = []
    if not publishable:
        missing.append("No publishable content artifacts in this run yet.")
    if publishable and not sources:
        missing.append("Publishable artifacts exist without source records.")
    if publishable and not claims:
        missing.append("Publishable artifacts exist without claim records.")
    for artifact in publishable:
        content = artifact.content or {}
        provenance = artifact.provenance or {}
        if not artifact.source_ids and not content.get("source_citations"):
            missing.append(f"{artifact.title} has no source dependency evidence.")
        if not content.get("claim_trace") and not provenance.get("claim_trace"):
            missing.append(f"{artifact.title} has no claim trace evidence.")
        for issue in artifact_provenance_issues(artifact):
            missing.append(f"{artifact.title} provenance issue: {issue}.")
    unsupported_claims = [
        claim.claim_id
        for claim in claims
        if claim.support_status == ClaimSupportStatus.UNSUPPORTED
    ]
    if unsupported_claims:
        missing.append(f"{len(unsupported_claims)} unsupported claim(s) remain.")
    return FoundationAuditCheck(
        check_id="source-grounded-artifacts",
        title="Source-grounded content artifacts",
        status=_status(missing),
        owner_agent_id="source-ledger-agent",
        requirement=(
            "Every generated content artifact stores source dependencies, claim "
            "traceability, provenance, reviewer decisions, and revision history."
        ),
        evidence=[
            f"{len(publishable)} publishable artifact(s), {len(sources)} source(s), "
            f"{len(claims)} claim(s) inspected."
        ],
        missing=missing,
    )


def _research_freshness_check(artifacts, events: list[RunEvent]) -> FoundationAuditCheck:
    publishable = [
        artifact
        for artifact in artifacts
        if artifact.artifact_type in PUBLISHABLE_ARTIFACT_TYPES
    ]
    has_ledger = any(
        artifact.artifact_type == ArtifactType.RESEARCH_FRESHNESS_LEDGER
        for artifact in artifacts
    )
    has_event = any(
        event.event_type == "research_freshness_ledger_built" for event in events
    )
    missing = []
    if publishable and not (has_ledger or has_event):
        missing.append(
            "Publishable content exists without a research freshness ledger."
        )
    return FoundationAuditCheck(
        check_id="research-freshness-ledger",
        title="Research freshness ledger",
        status=_status(missing),
        owner_agent_id="web-research-agent",
        requirement=(
            "Source-backed content needs a durable record of search queries, "
            "accepted sources, placeholder seeds, and source freshness risks."
        ),
        evidence=[
            "Research freshness ledger artifact/event present."
            if has_ledger or has_event
            else "No research freshness ledger artifact/event present yet."
        ],
        missing=missing,
    )


def _feedback_gate_check(feedback_items, messages, artifacts, events: list[RunEvent]):
    event_types = {event.event_type for event in events}
    has_resolution_ledger = any(
        artifact.artifact_type == ArtifactType.FEEDBACK_RESOLUTION_LEDGER
        for artifact in artifacts
    ) or "feedback_resolution_ledger_built" in event_types
    gated_messages = [
        message for message in messages if getattr(message, "requires_human_feedback", False)
    ]
    open_feedback = [
        item for item in feedback_items if item.status == FeedbackStatus.OPEN
    ]
    missing = []
    if not feedback_items and not gated_messages and "human_feedback_gate_opened" not in event_types:
        missing.append("No human feedback gate or feedback item evidence yet.")
    if feedback_items and not has_resolution_ledger:
        missing.append("Feedback exists without a feedback resolution ledger.")
    return FoundationAuditCheck(
        check_id="human-feedback-gates",
        title="Human feedback gates",
        status=_status(missing),
        owner_agent_id="forward-deployed-engineer",
        requirement=(
            "Human feedback is structured, durable, routed to the right agent, "
            "and able to pause or resume specialist work."
        ),
        evidence=[
            f"{len(feedback_items)} feedback item(s), "
            f"{len(open_feedback)} open item(s), "
            f"{len(gated_messages)} gated message(s) inspected."
            f" Feedback resolution ledger present={has_resolution_ledger}."
        ],
        missing=missing,
    )


def _provider_ops_check(artifacts, events: list[RunEvent]) -> FoundationAuditCheck:
    has_artifact = any(
        artifact.artifact_type == ArtifactType.PROVIDER_OPERATIONS_LEDGER
        for artifact in artifacts
    )
    has_event = any(
        event.event_type == "provider_operations_ledger_built" for event in events
    )
    missing = []
    if not has_artifact and not has_event:
        missing.append("Provider operations ledger has not been built for this run.")
    return FoundationAuditCheck(
        check_id="provider-operations-ledger",
        title="Provider operations ledger",
        status=_status(missing),
        owner_agent_id="observability-agent",
        requirement=(
            "Model/tool policy decisions, provider fallbacks, realtime sessions, "
            "and artifact model provenance are inspectable as a durable ledger."
        ),
        evidence=[
            "Provider operations ledger artifact/event present."
            if has_artifact or has_event
            else "No provider operations ledger artifact/event present yet."
        ],
        missing=missing,
    )


def _model_routing_ledger_check(artifacts, events: list[RunEvent]) -> FoundationAuditCheck:
    has_artifact = any(
        artifact.artifact_type == ArtifactType.MODEL_ROUTING_LEDGER
        for artifact in artifacts
    )
    has_event = any(
        event.event_type == "model_routing_ledger_built" for event in events
    )
    missing = []
    if not has_artifact and not has_event:
        missing.append("Model routing ledger has not been built for this run.")
    return FoundationAuditCheck(
        check_id="model-routing-ledger",
        title="Model routing ledger",
        status=_status(missing),
        owner_agent_id="agent-harness-engineer",
        requirement=(
            "Gemma/HF expert use, realtime audio transport, web-search tooling, "
            "and imagegen raster boundaries are inspectable as a durable run ledger."
        ),
        evidence=[
            "Model routing ledger artifact/event present."
            if has_artifact or has_event
            else "No model routing ledger artifact/event present yet."
        ],
        missing=missing,
    )


def _long_running_harness_check(
    checkpoints, worker_profiles, artifacts, events: list[RunEvent]
):
    event_types = {event.event_type for event in events}
    worker_events = {
        "agent_worker_cycle_completed",
        "worker_profile_heartbeat",
        "worker_scheduler_pass_completed",
        "run_resume_completed",
        "run_checkpoint_recorded",
    }
    has_replay_ledger = any(
        artifact.artifact_type == ArtifactType.RUN_REPLAY_LEDGER
        for artifact in artifacts
    ) or "run_replay_ledger_built" in event_types
    missing = []
    if not checkpoints and not worker_profiles and not (worker_events & event_types):
        missing.append(
            "No checkpoint, worker profile, scheduler, or resume evidence yet."
        )
    if checkpoints and not has_replay_ledger:
        missing.append(
            "Checkpoint evidence exists without a run replay ledger for time-travel debug."
        )
    return FoundationAuditCheck(
        check_id="long-running-agent-harness",
        title="Long-running agent harness",
        status=_status(missing),
        owner_agent_id="agent-harness-engineer",
        requirement=(
            "Runs can checkpoint, resume, execute worker cycles, heartbeat "
            "always-on profiles, replay event deltas, and recover work through "
            "event cursors."
        ),
        evidence=[
            f"{len(checkpoints)} checkpoint(s), "
            f"{len(worker_profiles)} worker profile(s), "
            f"replay ledger present={has_replay_ledger}."
        ],
        missing=missing,
    )


def _worker_profile_heartbeat_evidence_check(
    worker_profiles, artifacts, events: list[RunEvent]
) -> FoundationAuditCheck:
    active_profiles = [
        profile
        for profile in worker_profiles
        if getattr(profile, "status", None) == WorkerProfileStatus.ACTIVE
    ]
    heartbeat_events = [
        event
        for event in events
        if event.event_type in {
            "worker_profile_heartbeat",
            "worker_profile_heartbeat_blocked",
        }
    ]
    scheduler_events = [
        event
        for event in events
        if event.event_type == "worker_scheduler_pass_completed"
    ]
    artifact_ids_by_type = _artifact_ids_by_type(artifacts)
    missing = []
    if active_profiles and not heartbeat_events and not scheduler_events:
        missing.append(
            f"{len(active_profiles)} active worker profile(s) have no heartbeat "
            "or scheduler event evidence yet."
        )
    for event in heartbeat_events:
        _require_heartbeat_artifact_id(
            missing,
            event,
            "context_packet_artifact_id",
            ArtifactType.CONTEXT_PACKET,
            artifact_ids_by_type,
            "heartbeat context packet",
        )
        _require_heartbeat_artifact_id(
            missing,
            event,
            "realtime_dialogue_artifact_id",
            ArtifactType.REALTIME_DIALOGUE_LEDGER,
            artifact_ids_by_type,
            "realtime dialogue ledger",
        )
        _require_heartbeat_artifact_id(
            missing,
            event,
            "feedback_resolution_artifact_id",
            ArtifactType.FEEDBACK_RESOLUTION_LEDGER,
            artifact_ids_by_type,
            "feedback resolution ledger",
        )
        _require_heartbeat_artifact_id(
            missing,
            event,
            "heartbeat_ledger_artifact_id",
            ArtifactType.WORKER_PROFILE_HEARTBEAT_LEDGER,
            artifact_ids_by_type,
            "worker profile heartbeat ledger",
        )
    for event in scheduler_events:
        _require_scheduler_artifact_ids(
            missing,
            event,
            "context_packet_artifact_ids",
            ArtifactType.CONTEXT_PACKET,
            artifact_ids_by_type,
            "heartbeat context packet",
        )
        _require_scheduler_artifact_ids(
            missing,
            event,
            "realtime_dialogue_artifact_ids",
            ArtifactType.REALTIME_DIALOGUE_LEDGER,
            artifact_ids_by_type,
            "realtime dialogue ledger",
        )
        _require_scheduler_artifact_ids(
            missing,
            event,
            "feedback_resolution_artifact_ids",
            ArtifactType.FEEDBACK_RESOLUTION_LEDGER,
            artifact_ids_by_type,
            "feedback resolution ledger",
        )
        _require_scheduler_artifact_ids(
            missing,
            event,
            "heartbeat_ledger_artifact_ids",
            ArtifactType.WORKER_PROFILE_HEARTBEAT_LEDGER,
            artifact_ids_by_type,
            "worker profile heartbeat ledger",
        )
    return FoundationAuditCheck(
        check_id="worker-profile-heartbeat-evidence",
        title="Worker profile heartbeat evidence",
        status=_status(missing),
        owner_agent_id="agent-harness-engineer",
        requirement=(
            "Always-on worker profiles leave durable heartbeat, loop-ledger, "
            "scheduler, and context-packet evidence for resumable long-running work."
        ),
        evidence=[
            f"{len(active_profiles)} active profile(s), "
            f"{len(heartbeat_events)} heartbeat event(s), "
            f"{len(scheduler_events)} scheduler event(s) inspected.",
            "Heartbeat context packets, realtime dialogue ledgers, and feedback "
            "resolution ledgers, plus compact heartbeat ledgers, are "
            "cross-checked against recorded artifacts."
            if heartbeat_events
            else "No heartbeat event payloads required cross-checking yet.",
        ],
        missing=missing,
    )


def _context_and_notes_check(artifacts, events: list[RunEvent]) -> FoundationAuditCheck:
    event_types = {event.event_type for event in events}
    artifact_types = {artifact.artifact_type for artifact in artifacts}
    missing = []
    if ArtifactType.CONTEXT_PACKET not in artifact_types and "context_packet_built" not in event_types:
        missing.append("No context packet evidence yet.")
    if ArtifactType.HTML_NOTE not in artifact_types and "interactive_note_generated" not in event_types:
        missing.append("No interactive HTML note evidence yet.")
    return FoundationAuditCheck(
        check_id="context-and-interactive-notes",
        title="Context packets and interactive notes",
        status=_status(missing),
        owner_agent_id="interactive-note-taking-agent",
        requirement=(
            "Long-running agents receive compact context packets, and notes are "
            "kept as interactive HTML artifacts instead of Markdown plans."
        ),
        evidence=[
            "Context or note artifacts/events present."
            if not missing
            else "Context/note evidence is still pending for this run."
        ],
        missing=missing,
    )


def _post_audit_coordination_loop_check(
    artifacts, messages, events: list[RunEvent]
) -> FoundationAuditCheck:
    latest_audit = _latest_artifact_of_type(artifacts, ArtifactType.FOUNDATION_AUDIT)
    latest_audit_event = _latest_event(events, {"foundation_audit_built"})
    if latest_audit is None and latest_audit_event is None:
        return FoundationAuditCheck(
            check_id="post-audit-coordination-loop",
            title="Post-audit coordination loop",
            status=FoundationAuditStatus.PASS,
            owner_agent_id="product-manager",
            requirement=(
                "Foundation audits feed refreshed Sprint/Progress plans, "
                "Product Manager sync pulses, and context packets so remediation "
                "is routed and resumable."
            ),
            evidence=[
                "No prior foundation audit evidence yet; this audit will seed the post-audit coordination loop."
            ],
            missing=[],
        )

    latest_work_plan = _latest_artifact_with_workflow(
        artifacts, "run_work_plan_v1"
    )
    latest_sync_pulse = _latest_artifact_with_workflow(
        artifacts, "run_sync_pulse_v1"
    )
    latest_context_packet = _latest_artifact_of_type(
        artifacts, ArtifactType.CONTEXT_PACKET
    )
    has_work_plan_refresh = _artifact_has_refresh_reason(
        latest_work_plan, "foundation_audit_completed"
    ) or _event_has_refresh_reason(
        events,
        "run_work_plan_built",
        "foundation_audit_completed",
        payload_keys={"refresh_reason", "work_plan_refresh_reason"},
    ) or _event_has_refresh_reason(
        events,
        "autonomous_studio_pass_completed",
        "foundation_audit_completed",
        payload_keys={"work_plan_refresh_reason"},
    )
    has_sync_pulse_refresh = _artifact_has_refresh_reason(
        latest_sync_pulse, "foundation_audit_completed"
    ) or _event_has_refresh_reason(
        events,
        "multi_agent_sync_pulse_recorded",
        "foundation_audit_completed",
        payload_keys={"refresh_reason", "sync_pulse_refresh_reason"},
    ) or _event_has_refresh_reason(
        events,
        "autonomous_studio_pass_completed",
        "foundation_audit_completed",
        payload_keys={"sync_pulse_refresh_reason"},
    )
    has_context_packet_refresh = _artifact_has_refresh_reason(
        latest_context_packet, "foundation_audit_completed"
    ) or _event_has_refresh_reason(
        events,
        "context_packet_artifact_created",
        "foundation_audit_completed",
        payload_keys={"refresh_reason", "context_packet_refresh_reason"},
    ) or _event_has_refresh_reason(
        events,
        "autonomous_studio_pass_completed",
        "foundation_audit_completed",
        payload_keys={"context_packet_refresh_reason"},
    )
    remediation_count = _latest_foundation_remediation_count(
        latest_audit, latest_audit_event
    )
    work_plan_remediation_count = _work_plan_foundation_remediation_count(
        latest_work_plan
    )
    remediation_task_count = _foundation_remediation_task_count(
        messages,
        audit_artifact_id=str(latest_audit.artifact_id) if latest_audit else None,
    )

    missing = []
    if not has_work_plan_refresh:
        missing.append("No post-audit work-plan refresh evidence yet.")
    if not has_sync_pulse_refresh:
        missing.append("No post-audit manager sync pulse evidence yet.")
    if not has_context_packet_refresh:
        missing.append("No post-audit context packet refresh evidence yet.")
    if remediation_count > 0 and work_plan_remediation_count == 0:
        missing.append(
            "Latest foundation audit has remediation but no refreshed work-plan remediation item."
        )
    if remediation_count > 0 and remediation_task_count == 0:
        missing.append(
            "Latest foundation audit has remediation but no `resolve_foundation_audit_finding` A2A task."
        )

    return FoundationAuditCheck(
        check_id="post-audit-coordination-loop",
        title="Post-audit coordination loop",
        status=_status(missing),
        owner_agent_id="product-manager",
        requirement=(
            "Foundation audits feed refreshed Sprint/Progress plans, Product "
            "Manager sync pulses, and context packets so remediation is routed "
            "and resumable."
        ),
        evidence=[
            f"Prior foundation audit present; remediation_count={remediation_count}.",
            f"Post-audit work-plan refresh present={has_work_plan_refresh}; "
            f"foundation remediation items={work_plan_remediation_count}.",
            f"Post-audit manager sync refresh present={has_sync_pulse_refresh}.",
            f"Post-audit context packet refresh present={has_context_packet_refresh}.",
            f"Foundation remediation A2A task count={remediation_task_count}.",
        ],
        missing=missing,
    )


def _skipped_check(
    check_id: str, title: str, owner_agent_id: str, detail: str
) -> FoundationAuditCheck:
    return FoundationAuditCheck(
        check_id=check_id,
        title=title,
        status=FoundationAuditStatus.NEEDS_ATTENTION,
        owner_agent_id=owner_agent_id,
        requirement=detail,
        evidence=[],
        missing=[detail],
    )


def _remediation_items(checks: list[FoundationAuditCheck]) -> list[dict]:
    items = []
    for check in checks:
        if check.status == FoundationAuditStatus.PASS:
            continue
        missing = list(check.missing)
        blocking = check.status == FoundationAuditStatus.FAIL
        items.append(
            {
                "check_id": check.check_id,
                "title": check.title,
                "status": check.status.value,
                "owner_agent_id": check.owner_agent_id,
                "priority": "high" if blocking else "normal",
                "blocking": blocking,
                "missing": missing,
                "recommended_action": _remediation_action(check, missing),
                "requirement": check.requirement,
            }
        )
    return items


def _remediation_action(
    check: FoundationAuditCheck, missing: list[str]
) -> str:
    if missing:
        return "Resolve: " + "; ".join(missing[:3])
    return f"Review and repair foundation check `{check.check_id}`."


def _status(
    missing: list[str], *, hard_fail: bool = False
) -> FoundationAuditStatus:
    if not missing:
        return FoundationAuditStatus.PASS
    if hard_fail:
        return FoundationAuditStatus.FAIL
    return FoundationAuditStatus.NEEDS_ATTENTION


def _overall_status(
    fail_count: int, needs_attention_count: int
) -> FoundationAuditStatus:
    if fail_count:
        return FoundationAuditStatus.FAIL
    if needs_attention_count:
        return FoundationAuditStatus.NEEDS_ATTENTION
    return FoundationAuditStatus.PASS


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text()
    except OSError:
        return None


def _latest_artifact_of_type(artifacts, artifact_type: ArtifactType):
    typed_artifacts = [
        artifact for artifact in artifacts if artifact.artifact_type == artifact_type
    ]
    if not typed_artifacts:
        return None
    return max(typed_artifacts, key=lambda artifact: artifact.created_at)


def _latest_artifact_with_workflow(artifacts, workflow: str):
    workflow_artifacts = [
        artifact
        for artifact in artifacts
        if (artifact.provenance or {}).get("workflow") == workflow
        or (artifact.content or {}).get("workflow") == workflow
    ]
    if not workflow_artifacts:
        return None
    return max(workflow_artifacts, key=lambda artifact: artifact.created_at)


def _latest_event(events: list[RunEvent], event_types: set[str]) -> RunEvent | None:
    matched_events = [event for event in events if event.event_type in event_types]
    if not matched_events:
        return None
    return max(
        matched_events,
        key=lambda event: (
            event.event_id if event.event_id is not None else -1,
            event.created_at,
        ),
    )


def _artifact_has_refresh_reason(artifact, refresh_reason: str) -> bool:
    if artifact is None:
        return False
    content = artifact.content or {}
    provenance = artifact.provenance or {}
    return (
        content.get("refresh_reason") == refresh_reason
        or provenance.get("refresh_reason") == refresh_reason
    )


def _event_has_refresh_reason(
    events: list[RunEvent],
    event_type: str,
    refresh_reason: str,
    *,
    payload_keys: set[str],
) -> bool:
    for event in events:
        if event.event_type != event_type:
            continue
        payload = event.payload or {}
        if any(payload.get(key) == refresh_reason for key in payload_keys):
            return True
    return False


def _latest_foundation_remediation_count(
    audit_artifact, audit_event: RunEvent | None
) -> int:
    if audit_artifact is not None:
        content = audit_artifact.content or {}
        value = content.get("remediation_count")
        if isinstance(value, int):
            return value
        remediation_items = _foundation_audit_remediation_items(audit_artifact)
        if remediation_items:
            return len(remediation_items)
        checks = content.get("checks", [])
        if isinstance(checks, list):
            return sum(
                1
                for check in checks
                if isinstance(check, dict) and check.get("status") != "pass"
            )
        return 0
    if audit_event is None:
        return 0
    value = (audit_event.payload or {}).get("remediation_count")
    return value if isinstance(value, int) else 0


def _foundation_audit_remediation_items(audit_artifact) -> list[dict]:
    if audit_artifact is None:
        return []
    items = (audit_artifact.content or {}).get("remediation_items", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _work_plan_foundation_remediation_count(work_plan_artifact) -> int:
    if work_plan_artifact is None:
        return 0
    plan_items = (work_plan_artifact.content or {}).get("plan_items", [])
    if not isinstance(plan_items, list):
        return 0
    return sum(
        1
        for item in plan_items
        if isinstance(item, dict)
        and item.get("item_type") == "foundation_audit_remediation"
    )


def _foundation_remediation_task_count(
    messages, *, audit_artifact_id: str | None = None
) -> int:
    count = 0
    for message in messages:
        if getattr(message, "task_type", None) != "resolve_foundation_audit_finding":
            continue
        if audit_artifact_id is not None and not _message_targets_foundation_audit(
            message, audit_artifact_id
        ):
            continue
        count += 1
    return count


def _message_targets_foundation_audit(message, audit_artifact_id: str) -> bool:
    payload = getattr(message, "payload", {}) or {}
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        if str(metadata.get("foundation_audit_artifact_id")) == audit_artifact_id:
            return True
    return str(payload.get("foundation_audit_artifact_id")) == audit_artifact_id


def _artifact_ids_by_type(artifacts) -> dict[ArtifactType, set[str]]:
    ids_by_type: dict[ArtifactType, set[str]] = {}
    for artifact in artifacts:
        ids_by_type.setdefault(artifact.artifact_type, set()).add(
            str(artifact.artifact_id)
        )
    return ids_by_type


def _require_heartbeat_artifact_id(
    missing: list[str],
    event: RunEvent,
    payload_key: str,
    artifact_type: ArtifactType,
    artifact_ids_by_type: dict[ArtifactType, set[str]],
    label: str,
) -> None:
    artifact_id = (event.payload or {}).get(payload_key)
    if not artifact_id:
        missing.append(f"{_event_label(event)} missing {label} artifact id.")
        return
    if str(artifact_id) not in artifact_ids_by_type.get(artifact_type, set()):
        missing.append(
            f"{_event_label(event)} references {label} artifact {artifact_id} "
            "that is not recorded on the run."
        )


def _require_scheduler_artifact_ids(
    missing: list[str],
    event: RunEvent,
    payload_key: str,
    artifact_type: ArtifactType,
    artifact_ids_by_type: dict[ArtifactType, set[str]],
    label: str,
) -> None:
    artifact_ids = (event.payload or {}).get(payload_key)
    if not artifact_ids:
        missing.append(f"{_event_label(event)} missing {label} ids.")
        return
    recorded_ids = artifact_ids_by_type.get(artifact_type, set())
    for artifact_id in artifact_ids:
        if str(artifact_id) not in recorded_ids:
            missing.append(
                f"{_event_label(event)} references {label} artifact "
                f"{artifact_id} that is not recorded on the run."
            )


def _event_label(event: RunEvent) -> str:
    event_id = event.event_id if event.event_id is not None else "unrecorded"
    return f"{event.event_type} event {event_id}"
