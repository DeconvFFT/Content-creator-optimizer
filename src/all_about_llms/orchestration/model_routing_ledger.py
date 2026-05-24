from uuid import UUID

from all_about_llms.agents import AGENT_ROSTER
from all_about_llms.contracts import (
    ArtifactRecord,
    ArtifactType,
    ModelRoutingBoundaryCheck,
    ModelRoutingLedgerEntry,
    ModelRoutingLedgerRequest,
    ModelRoutingLedgerResult,
    RunEvent,
)
from all_about_llms.model_routing import list_model_routes
from all_about_llms.orchestration.artifact_provenance import (
    artifact_expert_model_issues,
)


GEMMA_GENERATION_EVENTS = {
    "gemma_synthesis_completed",
    "gemma_revision_completed",
    "gemma_worker_completed",
    "gemma_multimodal_review_completed",
}
MODEL_POLICY_EVENTS = {
    "agent_model_use_approved",
    "agent_model_use_denied",
}
REALTIME_EVENTS = {
    "realtime_session_created",
    "realtime_session_configuration_failed",
    "realtime_session_status_updated",
    "realtime_turn_routed",
}


class ModelRoutingLedgerError(RuntimeError):
    """Base error for model routing ledger generation."""


class ModelRoutingLedgerRunNotFoundError(ModelRoutingLedgerError):
    """Raised when a run cannot be found for model routing ledger work."""


class ModelRoutingLedgerWorkflow:
    """Build a durable ledger proving model/tool routing boundaries for a run."""

    def __init__(self, store):
        self._store = store

    async def build(
        self, run_id: UUID, request: ModelRoutingLedgerRequest
    ) -> ModelRoutingLedgerResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise ModelRoutingLedgerRunNotFoundError(f"Run not found: {run_id}")

        events = await self._store.list_events(run_id, limit=request.event_limit)
        artifacts = (
            await self._store.list_artifacts(run_id)
            if request.include_artifact_provenance
            else []
        )
        entries = _route_entries()
        if request.include_agent_matrix:
            entries.extend(_agent_entries())
        entries.extend(_event_entries(events))
        entries.extend(_artifact_entries(artifacts))
        boundary_checks = _boundary_checks(events, artifacts)
        boundary_violation_count = sum(
            len(check.violations) for check in boundary_checks
        )
        policy_event_count = sum(
            1 for event in events if event.event_type in MODEL_POLICY_EVENTS
        )
        gemma_generation_event_count = sum(
            1 for event in events if event.event_type in GEMMA_GENERATION_EVENTS
        )
        artifact_model_provenance_count = sum(
            1
            for artifact in artifacts
            if artifact.provenance.get("model_id")
            or artifact.provenance.get("model_provider")
        )
        result = ModelRoutingLedgerResult(
            run_id=run_id,
            route_count=len(list_model_routes()),
            agent_count=len(AGENT_ROSTER),
            gemma_capable_agent_count=sum(
                1 for agent in AGENT_ROSTER if _agent_allows_gemma(agent)
            ),
            realtime_agent_count=sum(
                1
                for agent in AGENT_ROSTER
                if "realtime-audio-provider" in agent.allowed_models
            ),
            imagegen_tool_agent_count=sum(
                1 for agent in AGENT_ROSTER if "imagegen" in agent.allowed_tools
            ),
            policy_event_count=policy_event_count,
            gemma_generation_event_count=gemma_generation_event_count,
            artifact_model_provenance_count=artifact_model_provenance_count,
            boundary_violation_count=boundary_violation_count,
            entries=entries,
            boundary_checks=boundary_checks,
            summary=(
                "Model routing ledger captured "
                f"{len(list_model_routes())} route contract(s), "
                f"{policy_event_count} model policy event(s), "
                f"{gemma_generation_event_count} Gemma generation event(s), and "
                f"{boundary_violation_count} boundary violation(s)."
            ),
        )

        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.MODEL_ROUTING_LEDGER,
                title="Model routing ledger",
                uri=f"artifact://runs/{run_id}/model-routing-ledger",
                content=result.model_dump(
                    mode="json", exclude={"ledger_artifact_id", "event_id"}
                ),
                provenance={
                    "workflow": "model_routing_ledger_v1",
                    "agent_id": "agent-harness-engineer",
                    "event_limit": request.event_limit,
                    "include_agent_matrix": request.include_agent_matrix,
                    "include_artifact_provenance": (
                        request.include_artifact_provenance
                    ),
                },
                revision_history=[
                    {
                        "actor": "agent-harness-engineer",
                        "note": (
                            "Captured Gemma, realtime audio, web search, and "
                            "imagegen routing boundaries for a durable run."
                        ),
                    }
                ],
            )
            result.ledger_artifact_id = artifact.artifact_id
            artifact.content["ledger_artifact_id"] = str(artifact.artifact_id)
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
                event_type="model_routing_ledger_built",
                actor="agent-harness-engineer",
                payload={
                    "route_count": result.route_count,
                    "agent_count": result.agent_count,
                    "gemma_capable_agent_count": (
                        result.gemma_capable_agent_count
                    ),
                    "realtime_agent_count": result.realtime_agent_count,
                    "imagegen_tool_agent_count": result.imagegen_tool_agent_count,
                    "policy_event_count": result.policy_event_count,
                    "gemma_generation_event_count": (
                        result.gemma_generation_event_count
                    ),
                    "artifact_model_provenance_count": (
                        result.artifact_model_provenance_count
                    ),
                    "boundary_violation_count": result.boundary_violation_count,
                    "ledger_artifact_id": (
                        str(result.ledger_artifact_id)
                        if result.ledger_artifact_id
                        else None
                    ),
                },
            )
        )
        result.event_id = event.event_id
        return result


def _route_entries() -> list[ModelRoutingLedgerEntry]:
    return [
        ModelRoutingLedgerEntry(
            entry_type="route_contract",
            route_task=route.task,
            provider=_provider_for_model_or_boundary(
                route.primary_model,
                route.provider_boundary,
            ),
            model_id=route.primary_model,
            status="configured",
            details={
                "primary_model": route.primary_model,
                "fallback_model": route.fallback_model,
                "rationale": route.rationale,
                "provider_boundary": route.provider_boundary,
            },
        )
        for route in list_model_routes()
    ]


def _agent_entries() -> list[ModelRoutingLedgerEntry]:
    entries = []
    for agent in AGENT_ROSTER:
        if _agent_allows_gemma(agent):
            status = "gemma_expert_allowed"
        elif "realtime-audio-provider" in agent.allowed_models:
            status = "realtime_audio_boundary"
        elif "imagegen" in agent.allowed_tools:
            status = "imagegen_tool_boundary"
        else:
            status = "non_gemma_or_deterministic_boundary"
        entries.append(
            ModelRoutingLedgerEntry(
                entry_type="agent_model_boundary",
                agent_id=agent.id,
                provider=_agent_provider_boundary(agent),
                status=status,
                details={
                    "name": agent.name,
                    "allowed_models": agent.allowed_models,
                    "allowed_tools": agent.allowed_tools,
                    "capabilities": agent.capabilities,
                },
            )
        )
    return entries


def _event_entries(events: list[RunEvent]) -> list[ModelRoutingLedgerEntry]:
    entries = []
    for event in events:
        payload = event.payload or {}
        if event.event_type in MODEL_POLICY_EVENTS:
            model_id = payload.get("model_id")
            entries.append(
                ModelRoutingLedgerEntry(
                    entry_type="model_policy_event",
                    agent_id=payload.get("agent_id"),
                    provider=_provider_for_model(model_id),
                    model_id=model_id,
                    status=(
                        "approved"
                        if event.event_type == "agent_model_use_approved"
                        else "denied"
                    ),
                    source_event_id=event.event_id,
                    details={
                        "allowed_models": payload.get("allowed_models", []),
                        "reason": payload.get("reason"),
                        "message_id": payload.get("message_id"),
                        "metadata": payload.get("metadata", {}),
                    },
                )
            )
        elif event.event_type in GEMMA_GENERATION_EVENTS:
            model_id = payload.get("model_id")
            entries.append(
                ModelRoutingLedgerEntry(
                    entry_type="gemma_generation_event",
                    agent_id=payload.get("agent_id") or event.actor,
                    provider="huggingface",
                    model_id=model_id,
                    status="completed",
                    source_event_id=event.event_id,
                    details={
                        "event_type": event.event_type,
                        "usage": payload.get("usage", {}),
                    },
                )
            )
        elif event.event_type in REALTIME_EVENTS:
            entries.append(
                ModelRoutingLedgerEntry(
                    entry_type="realtime_boundary_event",
                    agent_id=event.actor,
                    provider=payload.get("provider") or "realtime_audio",
                    model_id=payload.get("model_id"),
                    status="recorded",
                    source_event_id=event.event_id,
                    details=payload,
                )
            )
    return entries


def _artifact_entries(artifacts) -> list[ModelRoutingLedgerEntry]:
    entries = []
    for artifact in artifacts:
        provenance = artifact.provenance or {}
        model_id = provenance.get("model_id")
        model_provider = provenance.get("model_provider")
        if not model_id and not model_provider:
            continue
        entries.append(
            ModelRoutingLedgerEntry(
                entry_type="artifact_model_provenance",
                agent_id=provenance.get("agent_id"),
                provider=model_provider or _provider_for_model(model_id),
                model_id=model_id,
                status="recorded",
                source_artifact_id=artifact.artifact_id,
                details={
                    "artifact_type": artifact.artifact_type.value,
                    "title": artifact.title,
                    "generation_mode": provenance.get("generation_mode"),
                    "workflow": provenance.get("workflow"),
                },
            )
        )
    return entries


def _boundary_checks(events: list[RunEvent], artifacts) -> list[ModelRoutingBoundaryCheck]:
    return [
        _live_conversation_check(),
        _gemma_hf_route_check(),
        _imagegen_boundary_check(),
        _model_policy_event_check(events),
        _artifact_provenance_check(artifacts),
        _realtime_event_check(events),
    ]


def _live_conversation_check() -> ModelRoutingBoundaryCheck:
    routes = {route.task: route for route in list_model_routes()}
    host = _agent_by_id("realtime-conversation-host")
    route = routes.get("live_conversation")
    violations = []
    if host is None:
        violations.append("Realtime Conversation Host agent card is missing.")
    elif _agent_allows_gemma(host):
        violations.append("Realtime Conversation Host must not allow Gemma models.")
    if route is None:
        violations.append("Live conversation route contract is missing.")
    elif _is_gemma_model(route.primary_model) and not _is_gemma_voice_runtime(route):
        violations.append(
            "Live conversation Gemma use must be limited to the LiveKit/Kokoro voice runtime."
        )
    return ModelRoutingBoundaryCheck(
        check_id="live-dialogue-stays-on-realtime-provider",
        status=_check_status(violations),
        owner_agent_id="realtime-conversation-host",
        requirement=(
            "Natural dialogue, interruptions, and spoken output stay on the "
            "LiveKit voice transport; Gemma may handle audio understanding and "
            "reasoning only inside the bounded Gemma/Kokoro voice runtime."
        ),
        evidence=[
            f"Host allowed models: {host.allowed_models if host else []}.",
            f"Live route primary model: {route.primary_model if route else None}.",
        ],
        violations=violations,
    )


def _is_gemma_voice_runtime(route) -> bool:
    primary = route.primary_model.lower()
    boundary = route.provider_boundary.lower()
    return (
        "livekit" in primary
        and "kokoro" in primary
        and "livekit" in boundary
        and "kokoro" in boundary
        and "audio understanding" in boundary
    )


def _gemma_hf_route_check() -> ModelRoutingBoundaryCheck:
    violations = []
    for route in list_model_routes():
        models = [route.primary_model, route.fallback_model or ""]
        if any(_is_gemma_model(model) for model in models) and "Hugging Face" not in (
            route.provider_boundary
        ):
            violations.append(
                f"{route.task} uses Gemma but is not bound to Hugging Face."
            )
    return ModelRoutingBoundaryCheck(
        check_id="gemma-experts-use-hf-cloud-boundary",
        status=_check_status(violations),
        owner_agent_id="principal-software-engineer",
        requirement=(
            "Gemma 4 is the expert-agent model family through Hugging Face cloud "
            "endpoints, not the whole app runtime."
        ),
        evidence=[
            f"{len([agent for agent in AGENT_ROSTER if _agent_allows_gemma(agent)])} Gemma-capable agent card(s).",
            "Gemma model routes are static contracts from /api/model-routing.",
        ],
        violations=violations,
    )


def _imagegen_boundary_check() -> ModelRoutingBoundaryCheck:
    image_agent = _agent_by_id("image-generation-agent")
    routes = {route.task: route for route in list_model_routes()}
    image_route = routes.get("raster_visual_generation")
    violations = []
    if image_agent is None:
        violations.append("Image Generation Agent card is missing.")
    else:
        if "imagegen" not in image_agent.allowed_tools:
            violations.append("Image Generation Agent must allow the imagegen tool.")
        if image_agent.allowed_tools != ["imagegen"]:
            violations.append("Image Generation Agent should expose only imagegen.")
    if image_route is None:
        violations.append("Raster visual generation route is missing.")
    elif "imagegen" not in image_route.primary_model:
        violations.append("Raster visual generation must stay on imagegen.")
    return ModelRoutingBoundaryCheck(
        check_id="raster-visuals-stay-on-imagegen-boundary",
        status=_check_status(violations),
        owner_agent_id="image-generation-agent",
        requirement=(
            "Imagegen is the raster generation/editing boundary; Gemma may plan "
            "prompts but does not silently generate product images."
        ),
        evidence=[
            f"Image agent tools: {image_agent.allowed_tools if image_agent else []}.",
            f"Raster route model: {image_route.primary_model if image_route else None}.",
        ],
        violations=violations,
    )


def _model_policy_event_check(events: list[RunEvent]) -> ModelRoutingBoundaryCheck:
    violations = []
    for event in events:
        if event.event_type != "agent_model_use_approved":
            continue
        payload = event.payload or {}
        agent = _agent_by_id(payload.get("agent_id"))
        model_id = payload.get("model_id")
        if agent is None:
            violations.append(
                f"Approved model event {event.event_id} references unknown agent."
            )
        elif not _model_allowed_for_agent(model_id, agent.allowed_models):
            violations.append(
                f"Approved model event {event.event_id} exceeds {agent.id} card policy."
            )
    return ModelRoutingBoundaryCheck(
        check_id="approved-model-events-match-agent-cards",
        status=_check_status(violations),
        owner_agent_id="agent-harness-engineer",
        requirement=(
            "Every approved model use event must match the recipient agent card "
            "before provider-backed execution."
        ),
        evidence=[
            f"{sum(1 for event in events if event.event_type in MODEL_POLICY_EVENTS)} model policy event(s) inspected."
        ],
        violations=violations,
    )


def _artifact_provenance_check(artifacts) -> ModelRoutingBoundaryCheck:
    violations = []
    for artifact in artifacts:
        provenance = artifact.provenance or {}
        model_id = provenance.get("model_id")
        provider = provenance.get("model_provider")
        if _is_gemma_model(model_id) and provider != "huggingface":
            violations.append(
                f"{artifact.title} records Gemma model provenance without Hugging Face provider."
            )
        for issue in artifact_expert_model_issues(artifact):
            violations.append(f"{artifact.title} routing issue: {issue}.")
    return ModelRoutingBoundaryCheck(
        check_id="gemma-artifacts-record-hf-provenance",
        status=_check_status(violations),
        owner_agent_id="artifact-librarian",
        requirement=(
            "Artifacts produced with Gemma must store Hugging Face provider "
            "provenance, model id, generation mode, and source dependencies."
        ),
        evidence=[
            f"{len(artifacts)} artifact(s) inspected for model provenance."
        ],
        violations=violations,
    )


def _realtime_event_check(events: list[RunEvent]) -> ModelRoutingBoundaryCheck:
    violations = []
    for event in events:
        if event.event_type not in REALTIME_EVENTS:
            continue
        model_id = (event.payload or {}).get("model_id")
        if _is_gemma_model(model_id):
            violations.append(
                f"Realtime event {event.event_id} recorded Gemma as transport model."
            )
    return ModelRoutingBoundaryCheck(
        check_id="realtime-events-do-not-claim-gemma-transport",
        status=_check_status(violations),
        owner_agent_id="observability-agent",
        requirement=(
            "Realtime session and turn events may name realtime providers, but "
            "must not present Gemma as the live audio transport."
        ),
        evidence=[
            f"{sum(1 for event in events if event.event_type in REALTIME_EVENTS)} realtime event(s) inspected."
        ],
        violations=violations,
    )


def _agent_by_id(agent_id: str | None):
    if agent_id is None:
        return None
    for agent in AGENT_ROSTER:
        if agent.id == agent_id:
            return agent
    return None


def _agent_allows_gemma(agent) -> bool:
    return any(_is_gemma_model(model) for model in agent.allowed_models)


def _agent_provider_boundary(agent) -> str:
    if _agent_allows_gemma(agent):
        return "huggingface"
    if "realtime-audio-provider" in agent.allowed_models:
        return "realtime_audio"
    if "imagegen" in agent.allowed_tools:
        return "imagegen"
    if "web_search" in agent.allowed_tools:
        return "web_search"
    return "deterministic_or_artifact_store"


def _provider_for_model_or_boundary(model_id: str | None, boundary: str) -> str | None:
    provider = _provider_for_model(model_id)
    if provider:
        return provider
    normalized = boundary.lower()
    if "realtime" in normalized:
        return "realtime_audio"
    if "imagegen" in normalized:
        return "imagegen"
    if "web search" in normalized:
        return "web_search"
    return None


def _provider_for_model(model_id: str | None) -> str | None:
    if model_id is None:
        return None
    normalized = model_id.lower()
    if "gemma" in normalized:
        return "huggingface"
    if "realtime" in normalized or "speech-to-speech" in normalized:
        return "realtime_audio"
    return None


def _is_gemma_model(model_id: str | None) -> bool:
    if not model_id:
        return False
    return "gemma-4" in model_id.lower()


def _model_allowed_for_agent(model_id: str | None, allowed_models: list[str]) -> bool:
    if model_id is None:
        return False
    normalized_model = model_id.removeprefix("google/")
    return any(
        model_id == allowed_model
        or normalized_model == allowed_model.removeprefix("google/")
        for allowed_model in allowed_models
    )


def _check_status(violations: list[str]) -> str:
    return "blocked" if violations else "ready"
