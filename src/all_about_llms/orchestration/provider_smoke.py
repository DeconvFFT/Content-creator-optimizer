import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from all_about_llms.config import Settings
from all_about_llms.contracts import (
    AgentMessage,
    ArtifactRecord,
    ArtifactType,
    ProviderReadinessItem,
    ProviderReadinessResult,
    ProviderReadinessStatus,
    ProviderSmokeRunRequest,
    ProviderSmokeRunResult,
    ProviderSmokeRunStatus,
    ProviderSmokeStepResult,
    ProviderSmokeStepStatus,
    RealtimeSessionRecord,
    RunEvent,
    SourceRecord,
)
from all_about_llms.orchestration.a2a_projection import (
    public_a2a_message_event_payload,
)
from all_about_llms.orchestration.services import ContentWorkflowServices
from all_about_llms.providers.interfaces import (
    GemmaRequest,
    ProviderConfigurationError,
    RealtimeSessionRequest,
    RerankCandidate,
    RerankRequest,
    SearchRequest,
)
from all_about_llms.providers.readiness import build_provider_readiness
from all_about_llms.voice_agent.adapters import (
    HuggingFaceKokoroTTSStreamer,
    LocalKokoroTTSStreamer,
)
from all_about_llms.voice_agent.engine import VoiceAgentCancellationToken
from all_about_llms.voice_agent.gemma import (
    gemma_audio_endpoint_metadata,
    gemma_audio_endpoint_url,
)
from all_about_llms.voice_agent.reasoning import build_voice_reasoner, voice_reasoning_route
from all_about_llms.voice_agent.kokoro import kokoro_runtime_route
from all_about_llms.voice_agent.models import (
    RealtimeVoiceAgentConfig,
    RealtimeVoiceTurnInput,
)
from all_about_llms.voice_agent.control_binding import (
    verify_livekit_control_binding_token,
)


REALTIME_PROVIDER_TO_READINESS_ID = {
    "openrouter_livekit": "openrouter-livekit",
    "openrouter-livekit": "openrouter-livekit",
    "gemma4_realtime": "openrouter-livekit",
    "gemma4-realtime": "openrouter-livekit",
    "open_source_realtime": "open-source-realtime",
    "open-source-realtime": "open-source-realtime",
    "openai_realtime": "openai-realtime",
    "openai-realtime": "openai-realtime",
    "elevenlabs": "elevenlabs",
    "cartesia": "cartesia",
}

REALTIME_READINESS_ID_TO_PROVIDER = {
    "openrouter-livekit": "openrouter_livekit",
    "gemma4-realtime": "openrouter_livekit",
    "open-source-realtime": "open_source_realtime",
    "openai-realtime": "openai_realtime",
    "elevenlabs": "elevenlabs",
    "cartesia": "cartesia",
}


@dataclass(slots=True)
class VoiceAudioFixture:
    audio_pcm: bytes
    audio_ref: str | None
    source: str
    duration_ms: int
    metadata: dict[str, object]


@dataclass(slots=True)
class VoiceAudioFixtureLookup:
    fixture: VoiceAudioFixture | None = None
    stale_count: int = 0
    latest_stale_age_seconds: int | None = None
    latest_stale_turn_id: str | None = None


class ProviderSmokeRunError(RuntimeError):
    """Base error for provider smoke work."""


class ProviderSmokeRunNotFoundError(ProviderSmokeRunError):
    """Raised when a run cannot be found for provider smoke work."""


class ProviderSmokeWorkflow:
    """Execute and record provider smoke evidence for a durable run."""

    def __init__(
        self,
        store,
        settings: Settings,
        services: ContentWorkflowServices,
        realtime_provider_factory=None,
    ):
        self._store = store
        self._settings = settings
        self._services = services
        self._realtime_provider_factory = realtime_provider_factory

    async def build(
        self, run_id: UUID, request: ProviderSmokeRunRequest
    ) -> ProviderSmokeRunResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise ProviderSmokeRunNotFoundError(f"Run not found: {run_id}")

        events = await self._store.list_events(run_id, limit=request.event_limit)
        readiness = build_provider_readiness(self._settings)
        provider_by_id = {
            provider.provider_id: provider for provider in readiness.providers
        }

        steps = [
            _local_store_step(run_id),
            _provider_free_demo_step(events),
        ]
        if request.include_gemma:
            steps.append(
                await self._run_gemma_step(
                    run_id=run_id,
                    request=request,
                    readiness=readiness,
                    provider=provider_by_id["gemma4-primary"],
                )
            )
        if request.include_realtime:
            realtime_provider_id = _selected_realtime_provider_id(
                request,
                self._settings,
            )
            realtime_step = await self._run_realtime_step(
                run_id=run_id,
                request=request,
                provider_by_id=provider_by_id,
            )
            steps.append(realtime_step)
            selected_realtime_session_id = (
                realtime_step.realtime_session_ids[0]
                if realtime_step.realtime_session_ids
                else None
            )
            if realtime_provider_id in {"openrouter-livekit", "gemma4-realtime"}:
                streaming_provider = provider_by_id.get(realtime_provider_id)
                if streaming_provider is None and realtime_provider_id == "gemma4-realtime":
                    streaming_provider = provider_by_id.get("openrouter-livekit")
                if streaming_provider is None:
                    streaming_provider = provider_by_id.get("gemma4-realtime")
                if streaming_provider is not None:
                    steps.append(
                        await self._run_gemma_kokoro_streaming_step(
                            run_id=run_id,
                            request=request,
                            provider=streaming_provider,
                            events=events,
                            bound_realtime_session_id=selected_realtime_session_id,
                        )
                    )
        if request.include_web_search:
            steps.append(
                await self._run_web_search_step(
                    run_id=run_id,
                    request=request,
                    readiness=readiness,
                    provider_by_id=provider_by_id,
                )
            )
        if request.include_reranker:
            steps.append(await self._run_reranker_step(run_id, request))
        if request.include_imagegen_boundary:
            steps.append(_imagegen_boundary_step())

        result = _build_result(
            run_id=run_id,
            request=request,
            readiness=readiness,
            steps=steps,
        )
        configuration_blockers = _provider_configuration_blocker_steps(result)

        artifact: ArtifactRecord | None = None
        if request.record_artifact:
            artifact_id = _provider_smoke_ledger_artifact_id(
                run_id=run_id,
                request=request,
                result=result,
                blocked_steps=configuration_blockers,
            )
            artifact_kwargs = {"artifact_id": artifact_id} if artifact_id else {}
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.PROVIDER_SMOKE_LEDGER,
                title="Provider smoke ledger",
                uri=f"artifact://runs/{run_id}/provider-smoke-ledger",
                content={},
                provenance={
                    "workflow": "provider_smoke_ledger_v1",
                    "agent_id": "observability-agent",
                    "execute_live_calls": request.execute_live_calls,
                    "topic": request.topic,
                    "realtime_provider": request.realtime_provider,
                    "realtime_session_id": (
                        str(request.realtime_session_id)
                        if request.realtime_session_id
                        else None
                    ),
                    "require_voice_agent_presence": (
                        request.require_voice_agent_presence
                    ),
                },
                source_ids=result.source_ids,
                revision_history=[
                    {
                        "actor": "observability-agent",
                        "note": "Captured provider smoke readiness, live-call status, local reranker proof, source ids, and realtime session ids.",
                    }
                ],
                **artifact_kwargs,
            )
            result.ledger_artifact_id = artifact.artifact_id

        result.provider_configuration_followup_message_ids = (
            await self._record_provider_configuration_followup(
                run_id=run_id,
                request=request,
                result=result,
                blocked_steps=configuration_blockers,
            )
        )

        if artifact is not None:
            artifact.content = result.model_dump(
                mode="json", exclude={"ledger_artifact_id", "event_id"}
            )
            artifact.content["ledger_artifact_id"] = str(artifact.artifact_id)
            await _record_provider_smoke_artifact(self._store, artifact)
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
                event_type="provider_smoke_ledger_built",
                actor="observability-agent",
                payload={
                    "status": result.status,
                    "execute_live_calls": result.execute_live_calls,
                    "step_count": result.step_count,
                    "passed_count": result.passed_count,
                    "blocked_count": result.blocked_count,
                    "failed_count": result.failed_count,
                    "not_run_count": result.not_run_count,
                    "tool_boundary_count": result.tool_boundary_count,
                    "source_ids": [str(source_id) for source_id in result.source_ids],
                    "realtime_session_ids": [
                        str(session_id) for session_id in result.realtime_session_ids
                    ],
                    "provider_configuration_followup_message_ids": [
                        str(message_id)
                        for message_id in (
                            result.provider_configuration_followup_message_ids
                        )
                    ],
                    "requested_realtime_session_id": (
                        str(request.realtime_session_id)
                        if request.realtime_session_id
                        else None
                    ),
                    "require_voice_agent_presence": (
                        request.require_voice_agent_presence
                    ),
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

    async def _record_provider_configuration_followup(
        self,
        *,
        run_id: UUID,
        request: ProviderSmokeRunRequest,
        result: ProviderSmokeRunResult,
        blocked_steps: list[ProviderSmokeStepResult],
    ) -> list[UUID]:
        if not blocked_steps:
            return []
        message = _provider_configuration_followup_message(
            run_id=run_id,
            request=request,
            result=result,
            blocked_steps=blocked_steps,
        )
        recorded = await _record_agent_message_if_absent(self._store, message)
        if recorded is None:
            getter = getattr(self._store, "get_agent_message", None)
            existing = await getter(message.message_id) if callable(getter) else None
            recorded = existing
        if recorded is None:
            await self._store.record_agent_message(message)
            recorded = message
        await _append_provider_smoke_event_if_absent(
            self._store,
            RunEvent(
                run_id=run_id,
                event_type="agent_message_accepted",
                actor=recorded.sender_agent_id,
                payload=public_a2a_message_event_payload(recorded),
            ),
            idempotency_key=_provider_configuration_event_key(
                run_id=run_id,
                event_type="agent_message_accepted",
                message_id=recorded.message_id,
            ),
        )
        await _append_provider_smoke_event_if_absent(
            self._store,
            RunEvent(
                run_id=run_id,
                event_type="provider_smoke_configuration_followup_task_created",
                actor="observability-agent",
                payload={
                    "message_id": str(recorded.message_id),
                    "recipient_agent_id": recorded.recipient_agent_id,
                    "task_type": recorded.task_type,
                    "provider_smoke_status": result.status,
                    "blocked_step_count": len(blocked_steps),
                    "ledger_artifact_id": (
                        str(result.ledger_artifact_id)
                        if result.ledger_artifact_id
                        else None
                    ),
                    "recommended_worker_agent_ids": recorded.payload.get(
                        "recommended_worker_agent_ids", []
                    ),
                    "recommended_worker_use_gemma": False,
                },
            ),
            idempotency_key=_provider_configuration_event_key(
                run_id=run_id,
                event_type="provider_smoke_configuration_followup_task_created",
                message_id=recorded.message_id,
            ),
        )
        return [recorded.message_id]

    async def _run_gemma_step(
        self,
        *,
        run_id: UUID,
        request: ProviderSmokeRunRequest,
        readiness: ProviderReadinessResult,
        provider: ProviderReadinessItem,
    ) -> ProviderSmokeStepResult:
        blocked = _blocked_provider_step(
            step_id="gemma-primary-smoke",
            provider=provider,
            title="Run Gemma 4 primary expert synthesis smoke",
            live_call=True,
            latency_class="long_synthesis",
        )
        if blocked is not None:
            return blocked
        if not request.execute_live_calls:
            return _not_run_provider_step(
                step_id="gemma-primary-smoke",
                provider=provider,
                title="Run Gemma 4 primary expert synthesis smoke",
                live_call=True,
                latency_class="long_synthesis",
                evidence=[
                    "Gemma 4 primary readiness is configured.",
                    "Live Hugging Face endpoint call was skipped by request.",
                ],
            )
        if self._services.gemma_provider is None:
            return _missing_service_step(
                step_id="gemma-primary-smoke",
                provider=provider,
                title="Run Gemma 4 primary expert synthesis smoke",
                live_call=True,
                latency_class="long_synthesis",
                service_name="Gemma provider",
            )

        started = time.perf_counter()
        model_id = (
            provider.model_ids[0]
            if provider.model_ids
            else self._settings.gemma4_primary_model_id
        )
        try:
            response = await self._services.gemma_provider.complete(
                GemmaRequest(
                    model_id=model_id,
                    agent_id="observability-agent",
                    system_context=(
                        "You are running a provider smoke test. Reply with one "
                        "short sentence confirming Gemma 4 expert synthesis is live."
                    ),
                    user_input=request.topic,
                    metadata={"workflow": "provider_smoke_ledger_v1"},
                )
            )
            provider_latency_ms = _elapsed_ms(started)
        except ProviderConfigurationError as exc:
            return _exception_step(
                step_id="gemma-primary-smoke",
                provider=provider,
                title="Run Gemma 4 primary expert synthesis smoke",
                status=ProviderSmokeStepStatus.BLOCKED,
                live_call=True,
                latency_class="long_synthesis",
                started=started,
                error=str(exc),
            )
        except Exception as exc:  # pragma: no cover - provider/network dependent
            return _exception_step(
                step_id="gemma-primary-smoke",
                provider=provider,
                title="Run Gemma 4 primary expert synthesis smoke",
                status=ProviderSmokeStepStatus.FAILED,
                live_call=True,
                latency_class="long_synthesis",
                started=started,
                error=str(exc),
            )

        event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="provider_smoke_gemma_completed",
                actor="observability-agent",
                payload={
                    "provider": "huggingface",
                    "provider_id": provider.provider_id,
                    "model_id": response.model_id,
                    "agent_id": response.agent_id,
                    "latency_class": "long_synthesis",
                    "provider_latency_ms": provider_latency_ms,
                    "smoke_proof_status": "provider_backed",
                    "usage": response.usage,
                },
            )
        )
        return ProviderSmokeStepResult(
            step_id="gemma-primary-smoke",
            provider_id=provider.provider_id,
            provider_type=provider.provider_type,
            title="Run Gemma 4 primary expert synthesis smoke",
            status=ProviderSmokeStepStatus.PASSED,
            required=True,
            live_call=True,
            latency_class="long_synthesis",
            provider_latency_ms=provider_latency_ms,
            end_to_end_latency_ms=provider_latency_ms,
            smoke_proof_status="provider_backed",
            evidence=[
                f"Hugging Face Gemma endpoint returned model_id={response.model_id}.",
                f"Response preview: {response.content[:160]}",
            ],
            next_actions=[
                "Build the provider operations ledger to correlate this smoke result with later model/tool operations."
            ],
            event_ids=_event_ids(event),
            details={"usage": response.usage},
        )

    async def _run_realtime_step(
        self,
        *,
        run_id: UUID,
        request: ProviderSmokeRunRequest,
        provider_by_id: dict[str, ProviderReadinessItem],
    ) -> ProviderSmokeStepResult:
        provider_key = request.realtime_provider or self._settings.realtime_default_provider
        provider_id = REALTIME_PROVIDER_TO_READINESS_ID.get(provider_key, provider_key)
        provider = provider_by_id.get(provider_id)
        title = "Create selected realtime audio session"
        if provider is None:
            return ProviderSmokeStepResult(
                step_id="selected-realtime-smoke",
                provider_id=provider_id,
                provider_type="realtime_audio",
                title=title,
                status=ProviderSmokeStepStatus.BLOCKED,
                required=True,
                live_call=True,
                latency_class="realtime_interrupt",
                smoke_proof_status="configuration_failed",
                blockers=[
                    f"Selected realtime provider {provider_id} is not recognized."
                ],
                next_actions=[
                    "Set realtime_provider to openrouter_livekit for the default LiveKit + OpenRouter/Kokoro path, or configure an explicit optional provider."
                ],
            )
        blocked = _blocked_provider_step(
            step_id="selected-realtime-smoke",
            provider=provider,
            title=title,
            live_call=True,
            latency_class="realtime_interrupt",
        )
        if blocked is not None:
            return blocked
        if not request.execute_live_calls:
            return _not_run_provider_step(
                step_id="selected-realtime-smoke",
                provider=provider,
                title=title,
                live_call=True,
                latency_class="realtime_interrupt",
                evidence=[
                    f"{provider.display_name} readiness is configured.",
                    "Live realtime session creation was skipped by request.",
                ],
            )
        if request.realtime_session_id is not None:
            return await self._existing_realtime_session_step(
                run_id=run_id,
                request=request,
                provider=provider,
                provider_id=provider_id,
                title=title,
            )
        if self._realtime_provider_factory is None:
            return _missing_service_step(
                step_id="selected-realtime-smoke",
                provider=provider,
                title=title,
                live_call=True,
                latency_class="realtime_interrupt",
                service_name="Realtime provider factory",
            )

        factory_key = REALTIME_READINESS_ID_TO_PROVIDER.get(provider.provider_id)
        realtime_session_id = uuid4()
        started = time.perf_counter()
        try:
            realtime_provider = self._realtime_provider_factory(factory_key)
            provider_response = await realtime_provider.create_session(
                RealtimeSessionRequest(
                    provider=factory_key or provider.provider_id,
                    run_id=str(run_id),
                    voice=request.voice,
                    instructions=(
                        "Provider smoke test for the realtime conversation host. "
                        "Keep the session interruptible and do not expose secrets."
                    ),
                    metadata={
                        "workflow": "provider_smoke_ledger_v1",
                        "topic": request.topic,
                        "realtime_session_id": str(realtime_session_id),
                    },
                )
            )
            provider_latency_ms = _elapsed_ms(started)
        except (ValueError, ProviderConfigurationError) as exc:
            return _exception_step(
                step_id="selected-realtime-smoke",
                provider=provider,
                title=title,
                status=ProviderSmokeStepStatus.BLOCKED,
                live_call=True,
                latency_class="realtime_interrupt",
                started=started,
                error=str(exc),
            )
        except Exception as exc:  # pragma: no cover - provider/network dependent
            return _exception_step(
                step_id="selected-realtime-smoke",
                provider=provider,
                title=title,
                status=ProviderSmokeStepStatus.FAILED,
                live_call=True,
                latency_class="realtime_interrupt",
                started=started,
                error=str(exc),
            )

        control_binding_failure = _control_binding_validation_failure(
            provider_response,
            self._settings,
            run_id=run_id,
            realtime_session_id=realtime_session_id,
        )
        if control_binding_failure is not None:
            return ProviderSmokeStepResult(
                step_id="selected-realtime-smoke",
                provider_id=provider.provider_id,
                provider_type=provider.provider_type,
                title=title,
                status=ProviderSmokeStepStatus.BLOCKED,
                required=True,
                live_call=True,
                latency_class="realtime_interrupt",
                provider_latency_ms=provider_latency_ms,
                smoke_proof_status=control_binding_failure["status"],
                blockers=[control_binding_failure["blocker"]],
                next_actions=[
                    "Create the realtime session through the backend so it can preallocate a durable realtime_session_id and mint the control binding proof."
                ],
                details={
                    "provider": provider_response.provider,
                    "provider_session_id": provider_response.session_id,
                    "realtime_session_id": str(realtime_session_id),
                    **control_binding_failure["details"],
                },
            )

        transport = _provider_transport_payload(provider_response)
        realtime_metadata = _safe_provider_metadata(
            {
                **provider_response.metadata,
                "control_binding_token_issued": (
                    True
                    if _provider_requires_control_binding(provider_response.provider)
                    else bool(
                        provider_response.metadata.get(
                            "control_binding_token_issued"
                        )
                    )
                ),
                "transport": transport,
                "transport_framework": (
                    transport.get("framework") if transport else None
                ),
                "room_name": transport.get("room_name") if transport else None,
                "participant_identity": (
                    transport.get("participant_identity") if transport else None
                ),
                "agent_participant_identity": (
                    transport.get("agent_identity") if transport else None
                ),
                "has_transport_token": bool(
                    transport.get("has_token") if transport else False
                ),
                "workflow": "provider_smoke_ledger_v1",
                "latency_class": "realtime_interrupt",
                "provider_latency_ms": provider_latency_ms,
                "smoke_proof_status": "provider_backed",
            }
        )
        session = RealtimeSessionRecord(
            realtime_session_id=realtime_session_id,
            run_id=run_id,
            provider=provider_response.provider,
            provider_session_id=provider_response.session_id,
            voice=request.voice,
            audio_mode="speech_to_speech",
            instructions=(
                "Provider smoke test for the realtime conversation host. "
                "Keep the session interruptible and do not expose secrets."
            ),
            has_client_secret=provider_response.client_secret is not None,
            has_websocket_url=provider_response.websocket_url is not None,
            transport_framework=(
                str(transport.get("framework")) if transport else None
            ),
            room_name=str(transport.get("room_name")) if transport else None,
            participant_identity=(
                str(transport.get("participant_identity")) if transport else None
            ),
            agent_participant_identity=(
                str(transport.get("agent_identity")) if transport else None
            ),
            has_transport_token=bool(
                transport.get("has_token") if transport else False
            ),
            expires_at_unix=provider_response.expires_at_unix,
            metadata=realtime_metadata,
        )
        await self._store.record_realtime_session(session)
        event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="realtime_session_created",
                actor="realtime-conversation-host",
                payload={
                    "realtime_session_id": str(session.realtime_session_id),
                    "provider": session.provider,
                    "session_id": session.provider_session_id,
                    "voice": request.voice,
                    "audio_mode": session.audio_mode,
                    "has_client_secret": session.has_client_secret,
                    "has_websocket_url": session.has_websocket_url,
                    "transport": transport,
                    "expires_at_unix": session.expires_at_unix,
                    "latency_class": "realtime_interrupt",
                    "provider_latency_ms": provider_latency_ms,
                    "smoke_proof_status": "provider_backed",
                    "metadata": realtime_metadata,
                },
            )
        )
        return ProviderSmokeStepResult(
            step_id="selected-realtime-smoke",
            provider_id=provider.provider_id,
            provider_type=provider.provider_type,
            title=title,
            status=ProviderSmokeStepStatus.PASSED,
            required=True,
            live_call=True,
            latency_class="realtime_interrupt",
            provider_latency_ms=provider_latency_ms,
            end_to_end_latency_ms=provider_latency_ms,
            smoke_proof_status="provider_backed",
            evidence=[
                f"Recorded realtime session {session.realtime_session_id}.",
                f"Provider returned provider={session.provider}.",
            ],
            next_actions=[
                "Route one realtime turn and rebuild the realtime dialogue ledger for full voice-loop proof."
            ],
            realtime_session_ids=[session.realtime_session_id],
            event_ids=_event_ids(event),
            details={
                "has_client_secret": session.has_client_secret,
                "has_websocket_url": session.has_websocket_url,
            },
        )

    async def _existing_realtime_session_step(
        self,
        *,
        run_id: UUID,
        request: ProviderSmokeRunRequest,
        provider: ProviderReadinessItem,
        provider_id: str,
        title: str,
    ) -> ProviderSmokeStepResult:
        session = await self._store.get_realtime_session(request.realtime_session_id)
        if session is None or session.run_id != run_id:
            return ProviderSmokeStepResult(
                step_id="selected-realtime-smoke",
                provider_id=provider.provider_id,
                provider_type=provider.provider_type,
                title=title,
                status=ProviderSmokeStepStatus.BLOCKED,
                required=True,
                live_call=False,
                latency_class="realtime_interrupt",
                smoke_proof_status="missing_realtime_session",
                blockers=[
                    "The requested realtime_session_id does not belong to this run."
                ],
                next_actions=[
                    "Join an OpenRouter/Kokoro LiveKit voice room before running session-bound voice smoke."
                ],
                details={
                    "requested_realtime_session_id": str(request.realtime_session_id),
                },
            )
        expected_provider = REALTIME_READINESS_ID_TO_PROVIDER.get(provider_id, provider_id)
        if not _realtime_provider_matches_session(
            expected_provider=expected_provider,
            session_provider=session.provider,
        ):
            return ProviderSmokeStepResult(
                step_id="selected-realtime-smoke",
                provider_id=provider.provider_id,
                provider_type=provider.provider_type,
                title=title,
                status=ProviderSmokeStepStatus.BLOCKED,
                required=True,
                live_call=False,
                latency_class="realtime_interrupt",
                smoke_proof_status="realtime_session_provider_mismatch",
                blockers=[
                    f"Session provider {session.provider} does not match selected provider {expected_provider}."
                ],
                next_actions=[
                    "Select the matching realtime runtime or start a fresh OpenRouter/Kokoro LiveKit session."
                ],
                realtime_session_ids=[session.realtime_session_id],
                details={
                    "requested_realtime_session_id": str(session.realtime_session_id),
                    "session_provider": session.provider,
                    "selected_provider": expected_provider,
                },
            )
        if not _session_has_control_binding_proof(session):
            return ProviderSmokeStepResult(
                step_id="selected-realtime-smoke",
                provider_id=provider.provider_id,
                provider_type=provider.provider_type,
                title=title,
                status=ProviderSmokeStepStatus.BLOCKED,
                required=True,
                live_call=False,
                latency_class="realtime_interrupt",
                smoke_proof_status="control_binding_missing",
                blockers=[
                    "The existing OpenRouter/Kokoro LiveKit session is missing signed control binding proof."
                ],
                next_actions=[
                    "Start a fresh backend-created OpenRouter/Kokoro LiveKit session before running session-bound voice smoke."
                ],
                realtime_session_ids=[session.realtime_session_id],
                details={
                    "requested_realtime_session_id": str(session.realtime_session_id),
                    "session_provider": session.provider,
                    "transport_framework": session.transport_framework,
                    "room_name": session.room_name,
                    "participant_identity": session.participant_identity,
                    "agent_participant_identity": session.agent_participant_identity,
                    "control_binding_token_issued": bool(
                        session.metadata.get("control_binding_token_issued")
                    ),
                },
            )
        return ProviderSmokeStepResult(
            step_id="selected-realtime-smoke",
            provider_id=provider.provider_id,
            provider_type=provider.provider_type,
            title="Use existing realtime audio session",
            status=ProviderSmokeStepStatus.PASSED,
            required=True,
            live_call=False,
            latency_class="realtime_interrupt",
            smoke_proof_status="existing_provider_session",
            evidence=[
                f"Using existing realtime session {session.realtime_session_id}.",
                f"Session provider is {session.provider}.",
            ],
            next_actions=[
                "Require fresh OpenRouter/Kokoro participant presence before claiming session-bound voice smoke."
            ],
            realtime_session_ids=[session.realtime_session_id],
            details={
                "realtime_session_id": str(session.realtime_session_id),
                "provider_session_id": session.provider_session_id,
                "transport_framework": session.transport_framework,
                "room_name": session.room_name,
                "participant_identity": session.participant_identity,
                "agent_participant_identity": session.agent_participant_identity,
                "has_transport_token": session.has_transport_token,
            },
        )

    async def _run_gemma_kokoro_streaming_step(
        self,
        *,
        run_id: UUID,
        request: ProviderSmokeRunRequest,
        provider: ProviderReadinessItem,
        events: list[RunEvent],
        bound_realtime_session_id: UUID | None = None,
    ) -> ProviderSmokeStepResult:
        title = "Measure OpenRouter DeepSeek streaming and Kokoro first-audio smoke"
        presence_blocker, presence_metadata = await self._voice_agent_presence_gate(
            run_id=run_id,
            request=request,
            provider=provider,
            events=events,
            title=title,
        )
        if presence_blocker is not None:
            return presence_blocker
        blockers = _voice_streaming_blockers(self._settings)
        if blockers:
            kokoro_route = kokoro_runtime_route(self._settings)
            return ProviderSmokeStepResult(
                step_id="gemma-kokoro-voice-streaming-smoke",
                provider_id=provider.provider_id,
                provider_type=provider.provider_type,
                title=title,
                status=ProviderSmokeStepStatus.BLOCKED,
                required=True,
                live_call=True,
                latency_class="realtime_interrupt",
                smoke_proof_status="configuration_failed",
                blockers=blockers,
                next_actions=[
                    "Configure OPENROUTER_API_KEY, LiveKit, and hosted or local Kokoro TTS before claiming first-audio readiness."
                ],
                details={
                    "reasoning_streaming_enabled": self._settings.gemma4_realtime_stream_gemma,
                    "openrouter_api_key_configured": bool(
                        self._settings.openrouter_api_key
                    ),
                    **presence_metadata,
                    **kokoro_route.metadata(),
                },
            )
        if not request.execute_live_calls:
            return _not_run_provider_step(
                step_id="gemma-kokoro-voice-streaming-smoke",
                provider=provider,
                title=title,
                live_call=True,
                latency_class="realtime_interrupt",
                evidence=[
                    "OpenRouter streaming and Kokoro TTS configuration are present.",
                    "Live OpenRouter TTFT / Kokoro first-audio call was skipped by request.",
                ],
                next_actions=[
                    "Run provider smoke with execute_live_calls=true to measure OpenRouter TTFT and Kokoro first-audio latency."
                ],
            )

        config = _realtime_voice_config(self._settings)
        reasoner = build_voice_reasoner(
            self._settings,
            config,
            provider=self._services.gemma_provider or _StreamingOnlyGemmaProvider(),
        )
        kokoro, kokoro_metadata = _build_kokoro_smoke_streamer(
            self._settings,
            config,
        )
        effective_realtime_session_id = (
            request.realtime_session_id or bound_realtime_session_id
        )
        require_session_audio = (
            presence_metadata.get("voice_agent_presence_status") == "ready"
            and effective_realtime_session_id is not None
        )
        fixture_lookup = await _lookup_voice_audio_fixture(
            self._store,
            self._settings,
            run_id,
            realtime_session_id=(
                effective_realtime_session_id if require_session_audio else None
            ),
            max_age_seconds=request.max_voice_audio_artifact_age_seconds,
        )
        fixture = fixture_lookup.fixture
        if require_session_audio and fixture is None:
            if fixture_lookup.stale_count > 0:
                return ProviderSmokeStepResult(
                    step_id="gemma-kokoro-voice-streaming-smoke",
                    provider_id=provider.provider_id,
                    provider_type=provider.provider_type,
                    title=title,
                    status=ProviderSmokeStepStatus.BLOCKED,
                    required=True,
                    live_call=True,
                    latency_class="realtime_interrupt",
                    smoke_proof_status="session_audio_artifact_stale",
                    blockers=[
                        "The latest captured voice-audio artifact for the requested LiveKit session is stale; live smoke needs a fresh voice-audio artifact."
                    ],
                    next_actions=[
                        "Speak into the active LiveKit room again, wait for a fresh user voice turn to materialize with a local audio artifact, then rerun session-bound live smoke."
                    ],
                    realtime_session_ids=[effective_realtime_session_id],
                    details={
                        **presence_metadata,
                        "audio_fixture_source": "stale_session_voice_audio_artifact",
                        "audio_artifact_used": False,
                        "stale_audio_artifact_count": fixture_lookup.stale_count,
                        "latest_stale_audio_artifact_age_seconds": (
                            fixture_lookup.latest_stale_age_seconds
                        ),
                        "latest_stale_audio_fixture_turn_id": (
                            fixture_lookup.latest_stale_turn_id
                        ),
                        "max_voice_audio_artifact_age_seconds": (
                            request.max_voice_audio_artifact_age_seconds
                        ),
                    },
                )
            return ProviderSmokeStepResult(
                step_id="gemma-kokoro-voice-streaming-smoke",
                provider_id=provider.provider_id,
                provider_type=provider.provider_type,
                title=title,
                status=ProviderSmokeStepStatus.BLOCKED,
                required=True,
                live_call=True,
                latency_class="realtime_interrupt",
                smoke_proof_status="session_audio_artifact_missing",
                blockers=[
                    "No captured voice-audio artifact is available for the requested LiveKit session."
                ],
                next_actions=[
                    "Speak into the active LiveKit room, wait for the user voice turn to materialize with a local audio artifact, then rerun session-bound live smoke."
                ],
                realtime_session_ids=[effective_realtime_session_id],
                details={
                    **presence_metadata,
                    "audio_fixture_source": "missing_session_voice_audio_artifact",
                    "audio_artifact_used": False,
                    "max_voice_audio_artifact_age_seconds": (
                        request.max_voice_audio_artifact_age_seconds
                    ),
                },
            )
        audio_pcm = fixture.audio_pcm if fixture else _probe_pcm(config)
        audio_ref = fixture.audio_ref if fixture else None
        audio_duration_ms = (
            fixture.duration_ms if fixture else self._settings.rust_voice_edge_frame_ms
        )
        fixture_metadata = fixture.metadata if fixture else {
            "audio_fixture_source": "synthetic_silence_probe",
            "audio_artifact_used": False,
        }
        turn_realtime_session_id = effective_realtime_session_id or UUID(
            "00000000-0000-0000-0000-000000000001"
        )
        turn_room_name = (
            _optional_str(presence_metadata.get("room_name"))
            or "provider-smoke-voice-streaming"
        )
        turn_participant_identity = (
            _optional_str(presence_metadata.get("participant_identity"))
            or "provider-smoke-creator"
        )
        turn_metadata = {
            "workflow": "provider_smoke_ledger_v1",
            "session_bound_voice_smoke": (
                presence_metadata.get("voice_agent_presence_status") == "ready"
            ),
            **presence_metadata,
            **fixture_metadata,
        }
        turn = RealtimeVoiceTurnInput(
            run_id=run_id,
            realtime_session_id=turn_realtime_session_id,
            room_name=turn_room_name,
            participant_identity=turn_participant_identity,
            audio_ref=audio_ref,
            audio_pcm=audio_pcm,
            audio_duration_ms=audio_duration_ms,
            metadata=turn_metadata,
        )
        response_id = "provider-smoke-voice-response"
        cancellation = VoiceAgentCancellationToken(response_id)
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        try:
            first_delta = None
            async for delta in reasoner.stream_text(turn, [], cancellation):
                if delta:
                    first_delta = delta
                    break
            if not first_delta:
                return _exception_step(
                    step_id="gemma-kokoro-voice-streaming-smoke",
                    provider=provider,
                    title=title,
                    status=ProviderSmokeStepStatus.FAILED,
                    live_call=True,
                    latency_class="realtime_interrupt",
                    started=started,
                    error="OpenRouter streaming endpoint returned no text delta.",
                )
            reasoning_ttft_ms = _elapsed_ms(started)
            kokoro_started = time.perf_counter()
            first_audio = None
            async for audio in kokoro.stream_audio(
                response_id=response_id,
                text=first_delta,
                voice=request.voice or self._settings.gemma4_realtime_default_voice,
                cancellation=cancellation,
            ):
                if audio:
                    first_audio = audio
                    break
            if not first_audio:
                return _exception_step(
                    step_id="gemma-kokoro-voice-streaming-smoke",
                    provider=provider,
                    title=title,
                    status=ProviderSmokeStepStatus.FAILED,
                    live_call=True,
                    latency_class="realtime_interrupt",
                    started=started,
                    error="Kokoro TTS returned no audio bytes.",
                )
            kokoro_first_audio_ms = _elapsed_ms(kokoro_started)
            first_audio_end_to_end_ms = _elapsed_ms(started)
        except ProviderConfigurationError as exc:
            return _exception_step(
                step_id="gemma-kokoro-voice-streaming-smoke",
                provider=provider,
                title=title,
                status=ProviderSmokeStepStatus.BLOCKED,
                live_call=True,
                latency_class="realtime_interrupt",
                started=started,
                error=str(exc),
            )
        except Exception as exc:  # pragma: no cover - provider/network dependent
            return _exception_step(
                step_id="gemma-kokoro-voice-streaming-smoke",
                provider=provider,
                title=title,
                status=ProviderSmokeStepStatus.FAILED,
                live_call=True,
                latency_class="realtime_interrupt",
                started=started,
                error=str(exc),
            )

        timing_events = await _record_provider_smoke_voice_timing_events(
            self._store,
            run_id=run_id,
            provider_id=provider.provider_id,
            realtime_provider=(
                request.realtime_provider or self._settings.realtime_default_provider
            ),
            turn=turn,
            response_id=response_id,
            reasoning_model_id=config.reasoning_model,
            started_at=started_at,
            first_delta=first_delta,
            first_audio=first_audio,
            reasoning_ttft_ms=reasoning_ttft_ms,
            first_audio_end_to_end_ms=first_audio_end_to_end_ms,
            fixture_metadata=fixture_metadata,
        )
        event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="provider_smoke_voice_streaming_completed",
                actor="observability-agent",
                payload={
                    "provider": kokoro_metadata["kokoro_provider"],
                    "voice_runtime_provider": request.realtime_provider
                    or self._settings.realtime_default_provider,
                    "provider_id": provider.provider_id,
                    "latency_class": "realtime_interrupt",
                    "smoke_proof_status": "provider_backed",
                    "reasoning_model_id": config.reasoning_model,
                    "kokoro_model_id": config.audio_output_model,
                    **kokoro_metadata,
                    "reasoning_streaming_enabled": config.gemma_streaming_enabled,
                    "reasoning_ttft_ms": reasoning_ttft_ms,
                    "kokoro_first_audio_ms": kokoro_first_audio_ms,
                    "first_audio_end_to_end_ms": first_audio_end_to_end_ms,
                    "first_delta_chars": len(first_delta),
                    "first_audio_bytes": len(first_audio),
                    "smoke_turn_realtime_session_id": str(turn.realtime_session_id),
                    "smoke_turn_room_name": turn.room_name,
                    "smoke_turn_participant_identity": turn.participant_identity,
                    **presence_metadata,
                    **fixture_metadata,
                },
            )
        )
        return ProviderSmokeStepResult(
            step_id="gemma-kokoro-voice-streaming-smoke",
            provider_id=provider.provider_id,
            provider_type=provider.provider_type,
            title=title,
            status=ProviderSmokeStepStatus.PASSED,
            required=True,
            live_call=True,
            latency_class="realtime_interrupt",
            provider_latency_ms=first_audio_end_to_end_ms,
            end_to_end_latency_ms=first_audio_end_to_end_ms,
            smoke_proof_status="provider_backed",
            evidence=[
                f"OpenRouter stream produced first text delta in {reasoning_ttft_ms} ms.",
                f"Kokoro produced first audio chunk in {kokoro_first_audio_ms} ms.",
                f"End-to-end first audio latency was {first_audio_end_to_end_ms} ms.",
                *(
                    [
                        "Fresh OpenRouter/Kokoro LiveKit participant presence was bound to this smoke run."
                    ]
                    if presence_metadata.get("voice_agent_presence_status")
                    == "ready"
                    else []
                ),
            ],
            next_actions=[
                "Compare OpenRouter time-to-first-token and Kokoro first-audio latency against the realtime voice SLO before claiming provider-backed voice readiness."
            ],
            event_ids=_event_ids(*timing_events, event),
            realtime_session_ids=(
                [turn.realtime_session_id]
                if effective_realtime_session_id is not None
                else []
            ),
            details={
                "reasoning_ttft_ms": reasoning_ttft_ms,
                "kokoro_first_audio_ms": kokoro_first_audio_ms,
                "first_audio_end_to_end_ms": first_audio_end_to_end_ms,
                "reasoning_streaming_enabled": config.gemma_streaming_enabled,
                "reasoning_model_id": config.reasoning_model,
                "kokoro_model_id": config.audio_output_model,
                "smoke_turn_realtime_session_id": str(turn.realtime_session_id),
                "smoke_turn_room_name": turn.room_name,
                "smoke_turn_participant_identity": turn.participant_identity,
                **presence_metadata,
                **kokoro_metadata,
                **fixture_metadata,
            },
        )

    async def _voice_agent_presence_gate(
        self,
        *,
        run_id: UUID,
        request: ProviderSmokeRunRequest,
        provider: ProviderReadinessItem,
        events: list[RunEvent],
        title: str,
    ) -> tuple[ProviderSmokeStepResult | None, dict[str, object]]:
        if not request.execute_live_calls or not request.require_voice_agent_presence:
            return None, {
                "voice_agent_presence_required": False,
            }
        if request.realtime_session_id is None:
            return _voice_agent_presence_blocked_step(
                provider=provider,
                title=title,
                blocker="Session-bound voice smoke requires a realtime_session_id.",
                next_action=(
                    "Join an OpenRouter/Kokoro LiveKit voice room before running "
                    "session-bound live smoke."
                ),
                details={
                    "voice_agent_presence_required": True,
                    "voice_agent_presence_status": "missing_session_id",
                },
            ), {}
        session = await self._store.get_realtime_session(request.realtime_session_id)
        if session is None or session.run_id != run_id:
            return _voice_agent_presence_blocked_step(
                provider=provider,
                title=title,
                blocker="The requested realtime_session_id does not belong to this run.",
                next_action=(
                    "Start or restore the active OpenRouter/Kokoro LiveKit session "
                    "before running session-bound live smoke."
                ),
                details={
                    "voice_agent_presence_required": True,
                    "voice_agent_presence_status": "missing_session",
                    "realtime_session_id": str(request.realtime_session_id),
                },
            ), {}
        if not _session_has_control_binding_proof(session):
            return _voice_agent_presence_blocked_step(
                provider=provider,
                title=title,
                blocker=(
                    "The requested OpenRouter/Kokoro LiveKit session is missing signed control binding proof."
                ),
                next_action=(
                    "Start a fresh backend-created OpenRouter/Kokoro LiveKit session "
                    "before running session-bound live smoke."
                ),
                details={
                    "voice_agent_presence_required": True,
                    "voice_agent_presence_status": "control_binding_missing",
                    "realtime_session_id": str(session.realtime_session_id),
                    "room_name": session.room_name,
                    "participant_identity": session.participant_identity,
                    "agent_participant_identity": session.agent_participant_identity,
                    "control_binding_token_issued": bool(
                        session.metadata.get("control_binding_token_issued")
                    ),
                },
                smoke_proof_status="control_binding_missing",
            ), {}
        presence_events = await _list_voice_agent_ready_events(
            self._store,
            run_id,
            limit=1000,
        )
        latest_event = _latest_voice_agent_ready_event(
            presence_events or events,
            realtime_session_id=request.realtime_session_id,
        )
        if latest_event is None:
            return _voice_agent_presence_blocked_step(
                provider=provider,
                title=title,
                blocker=(
                    "No fresh gemma_kokoro_voice_agent_ready event is bound to "
                    "the requested LiveKit session."
                ),
                next_action=(
                    "Join the LiveKit room, start the OpenRouter/Kokoro agent, send "
                    "the frontend presence probe, then rerun live smoke."
                ),
                details={
                    "voice_agent_presence_required": True,
                    "voice_agent_presence_status": "missing",
                    "realtime_session_id": str(session.realtime_session_id),
                    "room_name": session.room_name,
                    "agent_participant_identity": session.agent_participant_identity,
                },
            ), {}
        event_age_seconds = max(
            0.0,
            (
                datetime.now(timezone.utc) - _aware_utc(latest_event.created_at)
            ).total_seconds(),
        )
        if event_age_seconds > request.voice_agent_presence_stale_after_seconds:
            return _voice_agent_presence_blocked_step(
                provider=provider,
                title=title,
                blocker=(
                    "The latest gemma_kokoro_voice_agent_ready event for this "
                    "session is stale."
                ),
                next_action=(
                    "Send a fresh LiveKit presence probe and rerun session-bound "
                    "live smoke."
                ),
                details={
                    "voice_agent_presence_required": True,
                    "voice_agent_presence_status": "stale",
                    "realtime_session_id": str(session.realtime_session_id),
                    "voice_agent_presence_event_id": latest_event.event_id,
                    "voice_agent_presence_age_seconds": round(event_age_seconds, 3),
                    "voice_agent_presence_stale_after_seconds": (
                        request.voice_agent_presence_stale_after_seconds
                    ),
                },
            ), {}
        return None, {
            "voice_agent_presence_required": True,
            "voice_agent_presence_status": "ready",
            "realtime_session_id": str(session.realtime_session_id),
            "voice_agent_presence_event_id": latest_event.event_id,
            "voice_agent_presence_age_seconds": round(event_age_seconds, 3),
            "voice_agent_presence_stale_after_seconds": (
                request.voice_agent_presence_stale_after_seconds
            ),
            "livekit_sender_identity": _optional_str(
                latest_event.payload.get("livekit_sender_identity")
            ),
            "provider_session_id": session.provider_session_id,
            "transport_framework": session.transport_framework,
            "participant_identity": session.participant_identity,
            "agent_participant_identity": (
                _optional_str(latest_event.payload.get("agent_participant_identity"))
                or session.agent_participant_identity
            ),
            "room_name": _optional_str(latest_event.payload.get("room_name"))
            or session.room_name,
        }

    async def _run_web_search_step(
        self,
        *,
        run_id: UUID,
        request: ProviderSmokeRunRequest,
        readiness: ProviderReadinessResult,
        provider_by_id: dict[str, ProviderReadinessItem],
    ) -> ProviderSmokeStepResult:
        provider_id = {
            "tavily": "tavily-search",
            "serpapi": "serpapi-search",
        }.get(readiness.selected_web_search_provider, readiness.selected_web_search_provider)
        provider = provider_by_id.get(provider_id)
        title = "Run selected web-search grounding smoke"
        if provider is None:
            return ProviderSmokeStepResult(
                step_id="selected-web-search-smoke",
                provider_id=provider_id,
                provider_type="web_search",
                title=title,
                status=ProviderSmokeStepStatus.BLOCKED,
                required=True,
                live_call=True,
                latency_class="background_research",
                smoke_proof_status="configuration_failed",
                blockers=[f"Selected web-search provider {provider_id} is not recognized."],
                next_actions=["Set WEB_SEARCH_PROVIDER to tavily or serpapi."],
            )
        blocked = _blocked_provider_step(
            step_id="selected-web-search-smoke",
            provider=provider,
            title=title,
            live_call=True,
            latency_class="background_research",
        )
        if blocked is not None:
            return blocked
        if not request.execute_live_calls:
            return _not_run_provider_step(
                step_id="selected-web-search-smoke",
                provider=provider,
                title=title,
                live_call=True,
                latency_class="background_research",
                evidence=[
                    f"{provider.display_name} readiness is configured.",
                    "Live web-search query was skipped by request.",
                ],
            )
        if self._services.search_provider is None:
            return _missing_service_step(
                step_id="selected-web-search-smoke",
                provider=provider,
                title=title,
                live_call=True,
                latency_class="background_research",
                service_name="Web-search provider",
            )

        query = request.search_query or request.topic
        started = time.perf_counter()
        try:
            search_results = await self._services.search_provider.search(
                SearchRequest(query=query, max_results=3)
            )
            provider_latency_ms = _elapsed_ms(started)
        except ProviderConfigurationError as exc:
            return _exception_step(
                step_id="selected-web-search-smoke",
                provider=provider,
                title=title,
                status=ProviderSmokeStepStatus.BLOCKED,
                live_call=True,
                latency_class="background_research",
                started=started,
                error=str(exc),
            )
        except Exception as exc:  # pragma: no cover - provider/network dependent
            return _exception_step(
                step_id="selected-web-search-smoke",
                provider=provider,
                title=title,
                status=ProviderSmokeStepStatus.FAILED,
                live_call=True,
                latency_class="background_research",
                started=started,
                error=str(exc),
            )

        sources = []
        for index, result in enumerate(search_results, start=1):
            source = SourceRecord(
                run_id=run_id,
                citation_id=f"SMOKE-{index}",
                title=result.title,
                url=result.url,
                publisher=result.publisher,
                metadata={
                    "source_type": "web_search_result",
                    "search_query": query,
                    "search_rank": index,
                    "snippet": result.snippet,
                    "published_at": result.published_at,
                    "retrieved_at": result.retrieved_at,
                    "provider_smoke": True,
                    "provider_id": provider.provider_id,
                },
            )
            await self._store.record_source(source)
            sources.append(source)

        event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="provider_smoke_web_search_completed",
                actor="web-research-agent",
                payload={
                    "provider": provider.provider_id,
                    "query": query,
                    "result_count": len(search_results),
                    "source_ids": [str(source.source_id) for source in sources],
                    "latency_class": "background_research",
                    "provider_latency_ms": provider_latency_ms,
                    "smoke_proof_status": "provider_backed",
                },
            )
        )
        return ProviderSmokeStepResult(
            step_id="selected-web-search-smoke",
            provider_id=provider.provider_id,
            provider_type=provider.provider_type,
            title=title,
            status=(
                ProviderSmokeStepStatus.PASSED
                if search_results
                else ProviderSmokeStepStatus.FAILED
            ),
            required=True,
            live_call=True,
            latency_class="background_research",
            provider_latency_ms=provider_latency_ms,
            end_to_end_latency_ms=provider_latency_ms,
            smoke_proof_status="provider_backed" if search_results else "no_results",
            evidence=[
                f"Search returned {len(search_results)} result(s) for query: {query}.",
                *[f"{source.citation_id}: {source.title}" for source in sources[:3]],
            ],
            blockers=[] if search_results else ["Provider returned zero search results."],
            next_actions=[
                "Build retrieval quality and source ledger artifacts after search-backed drafting."
            ],
            source_ids=[source.source_id for source in sources],
            event_ids=_event_ids(event),
            details={"query": query, "result_count": len(search_results)},
        )

    async def _run_reranker_step(
        self, run_id: UUID, request: ProviderSmokeRunRequest
    ) -> ProviderSmokeStepResult:
        provider = self._services.reranker_provider
        if provider is None:
            return ProviderSmokeStepResult(
                step_id="local-reranker-smoke",
                provider_id="deterministic-reranker",
                provider_type="reranker",
                title="Build retrieval-quality reranker smoke",
                status=ProviderSmokeStepStatus.BLOCKED,
                required=True,
                live_call=False,
                latency_class="quick_critique",
                smoke_proof_status="configuration_failed",
                blockers=["Reranker provider service is not configured."],
                next_actions=["Configure RERANKER_PROVIDER=deterministic for local runs."],
            )

        started = time.perf_counter()
        results = await provider.rerank(
            RerankRequest(
                query=request.topic,
                top_k=2,
                candidates=[
                    RerankCandidate(
                        candidate_id="strong-current-source",
                        title="Provider smoke strong source",
                        url="https://example.com/provider-smoke-strong",
                        snippet="A current source with enough context for reranking.",
                        query=request.topic,
                        retrievers=["provider_smoke"],
                        rank=1,
                        metadata={
                            "quality_status": "strong",
                            "freshness_status": "current",
                            "search_rank": 1,
                            "has_published_at": True,
                        },
                    ),
                    RerankCandidate(
                        candidate_id="weak-stale-source",
                        title="Provider smoke weak source",
                        url="https://example.com/provider-smoke-weak",
                        snippet=None,
                        query=request.topic,
                        retrievers=["provider_smoke"],
                        rank=2,
                        metadata={
                            "quality_status": "weak",
                            "freshness_status": "stale",
                            "search_rank": 2,
                        },
                    ),
                ],
            )
        )
        provider_latency_ms = _elapsed_ms(started)
        passed = bool(results) and results[0].candidate_id == "strong-current-source"
        event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="provider_smoke_reranker_completed",
                actor="context-engineering-agent",
                payload={
                    "provider": "deterministic-reranker",
                    "result_count": len(results),
                    "top_candidate_id": results[0].candidate_id if results else None,
                    "latency_class": "quick_critique",
                    "provider_latency_ms": provider_latency_ms,
                    "smoke_proof_status": "local_deterministic_provider",
                },
            )
        )
        return ProviderSmokeStepResult(
            step_id="local-reranker-smoke",
            provider_id="deterministic-reranker",
            provider_type="reranker",
            title="Build retrieval-quality reranker smoke",
            status=(
                ProviderSmokeStepStatus.PASSED
                if passed
                else ProviderSmokeStepStatus.FAILED
            ),
            required=True,
            live_call=False,
            latency_class="quick_critique",
            provider_latency_ms=provider_latency_ms,
            end_to_end_latency_ms=provider_latency_ms,
            smoke_proof_status="local_deterministic_provider",
            evidence=[
                f"Reranker returned {len(results)} scored candidate(s).",
                f"Top candidate: {results[0].candidate_id if results else 'none'}",
            ],
            blockers=[] if passed else ["Reranker did not rank the strong current source first."],
            next_actions=[
                "Use this local provider as the deterministic baseline before adding cloud rerankers."
            ],
            event_ids=_event_ids(event),
            details={"results": [result.model_dump(mode="json") for result in results]},
        )


async def _record_provider_smoke_voice_timing_events(
    store,
    *,
    run_id: UUID,
    provider_id: str,
    realtime_provider: str | None,
    turn: RealtimeVoiceTurnInput,
    response_id: str,
    reasoning_model_id: str,
    started_at: datetime,
    first_delta: str,
    first_audio: bytes,
    reasoning_ttft_ms: float,
    first_audio_end_to_end_ms: float,
    fixture_metadata: dict[str, object],
) -> list[RunEvent]:
    turn_id = f"provider-smoke-turn-{turn.realtime_session_id}"
    common_payload = {
        "workflow": "provider_smoke_ledger_v1",
        "provider_id": provider_id,
        "voice_runtime_provider": realtime_provider,
        "realtime_session_id": str(turn.realtime_session_id),
        "room_name": turn.room_name,
        "participant_identity": turn.participant_identity,
        "turn_id": turn_id,
        "response_id": response_id,
        "latency_class": "realtime_interrupt",
        "smoke_proof_status": "provider_backed",
        "timing_source": "provider_smoke_openrouter_kokoro_stream",
        **fixture_metadata,
    }
    event_specs = [
        (
            "gemma_kokoro_voice_turn_started",
            started_at,
            {
                "stage": "provider_smoke_turn_started",
            },
        ),
        (
            "gemma_generation_started",
            started_at,
            {
                "stage": "openrouter_generation_started",
                "reasoning_model_id": reasoning_model_id,
            },
        ),
        (
            "assistant_text_delta",
            started_at + timedelta(milliseconds=reasoning_ttft_ms),
            {
                "stage": "openrouter_first_text_delta",
                "delta_chars": len(first_delta),
                "reasoning_ttft_ms": reasoning_ttft_ms,
            },
        ),
        (
            "assistant_audio_chunk_published",
            started_at + timedelta(milliseconds=first_audio_end_to_end_ms),
            {
                "stage": "kokoro_first_audio_chunk",
                "bytes": len(first_audio),
                "first_audio_end_to_end_ms": first_audio_end_to_end_ms,
            },
        ),
    ]
    events = []
    for event_type, created_at, payload in event_specs:
        events.append(
            await store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type=event_type,
                    actor="observability-agent",
                    payload={**common_payload, **payload},
                    created_at=created_at,
                )
            )
        )
    return events


def _local_store_step(run_id: UUID) -> ProviderSmokeStepResult:
    return ProviderSmokeStepResult(
        step_id="local-postgres-pgvector",
        provider_id="postgres-pgvector",
        provider_type="durable_store",
        title="Confirm run-scoped durable store access",
        status=ProviderSmokeStepStatus.PASSED,
        required=True,
        live_call=False,
        latency_class="durable_local",
        smoke_proof_status="durable_run_loaded",
        evidence=[f"Run {run_id} loaded through the configured durable store."],
        next_actions=[
            "Build the runtime health ledger for detailed Postgres + pgvector proof."
        ],
    )


class _StreamingOnlyGemmaProvider:
    async def complete(self, _request):
        raise ProviderConfigurationError(
            "Gemma provider-complete fallback is unavailable for voice streaming smoke."
        )


def _selected_realtime_provider_id(
    request: ProviderSmokeRunRequest,
    settings: Settings,
) -> str:
    provider_key = request.realtime_provider or settings.realtime_default_provider
    return REALTIME_PROVIDER_TO_READINESS_ID.get(provider_key, provider_key)


def _voice_streaming_blockers(settings: Settings) -> list[str]:
    blockers = []
    if not settings.gemma4_realtime_stream_gemma:
        blockers.append(
            "Realtime reasoning streaming must be enabled for low-latency voice smoke."
        )
    route = voice_reasoning_route(settings)
    if route.provider == "openrouter":
        if route.missing_env:
            blockers.append(
                "OPENROUTER_API_KEY is required for OpenRouter live dialogue streaming smoke."
            )
    else:
        if not settings.hf_token:
            blockers.append("HF_TOKEN is required for legacy Gemma/Kokoro voice streaming smoke.")
        endpoint_metadata = gemma_audio_endpoint_metadata(settings)
        if not gemma_audio_endpoint_url(settings):
            if endpoint_metadata["gemma_audio_endpoint_error"]:
                blockers.append(
                    "GEMMA4_MULTIMODAL_ENDPOINT_URL must be a valid HTTP(S) URL for Gemma 4 E4B native-audio streaming smoke."
                )
            elif endpoint_metadata["gemma_primary_endpoint_configured"]:
                blockers.append(
                    "GEMMA4_MULTIMODAL_ENDPOINT_URL is required for Gemma 4 E4B native-audio streaming smoke; "
                    "GEMMA4_PRIMARY_ENDPOINT_URL is text/chat expert routing only."
                )
            elif endpoint_metadata["hf_router_chat_completions_configured"]:
                blockers.append(
                    "HF router chat-completions is text/chat only and does not satisfy native audio smoke; "
                    "GEMMA4_MULTIMODAL_ENDPOINT_URL must point to an audio-capable Gemma endpoint."
                )
            else:
                blockers.append(
                    "GEMMA4_MULTIMODAL_ENDPOINT_URL is required for Gemma 4 E4B native-audio streaming smoke."
                )
    if not _kokoro_tts_available(settings):
        blockers.append(
            "KOKORO_TTS_ENDPOINT_URL or the local Kokoro package is required to measure Kokoro first-audio latency."
        )
    return blockers


def _kokoro_tts_available(settings: Settings) -> bool:
    return kokoro_runtime_route(settings).ready


def _voice_agent_presence_blocked_step(
    *,
    provider: ProviderReadinessItem,
    title: str,
    blocker: str,
    next_action: str,
    details: dict[str, object],
    smoke_proof_status: str = "voice_agent_presence_missing",
) -> ProviderSmokeStepResult:
    return ProviderSmokeStepResult(
        step_id="gemma-kokoro-voice-streaming-smoke",
        provider_id=provider.provider_id,
        provider_type=provider.provider_type,
        title=title,
        status=ProviderSmokeStepStatus.BLOCKED,
        required=True,
        live_call=True,
        latency_class="realtime_interrupt",
        smoke_proof_status=smoke_proof_status,
        blockers=[blocker],
        next_actions=[next_action],
        details=details,
    )


async def _list_voice_agent_ready_events(
    store,
    run_id: UUID,
    *,
    limit: int,
) -> list[RunEvent]:
    if hasattr(store, "list_events_by_type"):
        return await store.list_events_by_type(
            run_id,
            "gemma_kokoro_voice_agent_ready",
            limit=limit,
            latest=True,
        )
    return await store.list_events(run_id, limit=max(limit, 5000), latest=True)


def _latest_voice_agent_ready_event(
    events: list[RunEvent],
    *,
    realtime_session_id: UUID,
) -> RunEvent | None:
    candidates = [
        event
        for event in events
        if event.event_type == "gemma_kokoro_voice_agent_ready"
        and _event_realtime_session_id(event) == realtime_session_id
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda event: (_aware_utc(event.created_at), event.event_id or 0),
    )


def _event_realtime_session_id(event: RunEvent) -> UUID | None:
    value = _optional_str(event.payload.get("realtime_session_id"))
    if value is None:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _build_kokoro_smoke_streamer(
    settings: Settings,
    config: RealtimeVoiceAgentConfig,
) -> tuple[Any, dict[str, object]]:
    route = kokoro_runtime_route(settings)
    endpoint_url = route.endpoint_url
    if endpoint_url:
        return HuggingFaceKokoroTTSStreamer(
            token=settings.hf_token,
            endpoint_url=endpoint_url,
            model_id=settings.gemma4_realtime_audio_output_model,
            chunk_bytes=settings.kokoro_tts_chunk_bytes,
            timeout_seconds=settings.kokoro_tts_timeout_seconds,
        ), {
            **route.metadata(),
        }
    if not route.ready:
        raise ProviderConfigurationError(route.configuration_error())
    return LocalKokoroTTSStreamer(
        voice=settings.gemma4_realtime_default_voice,
        chunk_bytes=settings.kokoro_tts_chunk_bytes,
    ), {
        **route.metadata(),
        "kokoro_audio_output_model": config.audio_output_model,
    }


def _realtime_voice_config(settings: Settings) -> RealtimeVoiceAgentConfig:
    return RealtimeVoiceAgentConfig(
        audio_input_model=settings.gemma4_realtime_audio_input_model,
        reasoning_model=settings.gemma4_realtime_reasoning_model,
        audio_output_model=settings.gemma4_realtime_audio_output_model,
        sample_rate=settings.gemma4_realtime_sample_rate,
        audio_format=settings.gemma4_realtime_audio_format,
        context_window_turns=settings.gemma4_realtime_context_window_turns,
        prune_after_turns=settings.gemma4_realtime_context_prune_after_turns,
        max_raw_audio_seconds_per_turn=(
            settings.gemma4_realtime_max_audio_seconds_per_turn
        ),
        tts_flush_chars=settings.gemma4_realtime_tts_flush_chars,
        gemma_streaming_enabled=settings.gemma4_realtime_stream_gemma,
        gemma_stream_timeout_seconds=(
            settings.gemma4_realtime_gemma_stream_timeout_seconds
        ),
    )


def _probe_pcm(config: RealtimeVoiceAgentConfig) -> bytes:
    frame_ms = 32
    samples = int(config.sample_rate * frame_ms / 1000)
    return b"\0\0" * samples


async def _latest_voice_audio_fixture(
    store,
    settings: Settings,
    run_id: UUID,
    realtime_session_id: UUID | None = None,
    max_age_seconds: int | None = None,
) -> VoiceAudioFixture | None:
    lookup = await _lookup_voice_audio_fixture(
        store,
        settings,
        run_id,
        realtime_session_id=realtime_session_id,
        max_age_seconds=max_age_seconds,
    )
    return lookup.fixture


async def _lookup_voice_audio_fixture(
    store,
    settings: Settings,
    run_id: UUID,
    realtime_session_id: UUID | None = None,
    max_age_seconds: int | None = None,
) -> VoiceAudioFixtureLookup:
    if hasattr(store, "list_recent_conversation_turns"):
        turns = await store.list_recent_conversation_turns(run_id, limit=5000)
    else:
        turns = sorted(
            await store.list_conversation_turns(run_id, limit=5000),
            key=lambda turn: turn.created_at,
            reverse=True,
        )
    lookup = VoiceAudioFixtureLookup()
    now = datetime.now(timezone.utc)
    for turn in turns:
        if turn.speaker != "user" or turn.modality != "voice":
            continue
        metadata = turn.metadata or {}
        artifact_uri = _optional_str(metadata.get("audio_artifact_uri")) or turn.audio_uri
        relative_path = _optional_str(metadata.get("audio_artifact_relative_path"))
        turn_session_id = _voice_fixture_session_id(
            metadata=metadata,
            artifact_uri=artifact_uri,
            relative_path=relative_path,
            expected_realtime_session_id=realtime_session_id,
        )
        if realtime_session_id is not None and turn_session_id != realtime_session_id:
            continue
        path = _voice_audio_artifact_path(
            settings=settings,
            artifact_uri=artifact_uri,
            relative_path=relative_path,
        )
        if path is None or not path.exists() or not path.is_file():
            continue
        try:
            if path.stat().st_size > settings.voice_agent_audio_artifact_max_bytes:
                continue
            audio_pcm = path.read_bytes()
        except OSError:
            continue
        expected_sha = _optional_str(metadata.get("audio_artifact_sha256"))
        actual_sha = _sha256(audio_pcm)
        if expected_sha and expected_sha != actual_sha:
            continue
        age_seconds = _turn_age_seconds(turn.created_at, now)
        if max_age_seconds is not None and age_seconds > max_age_seconds:
            lookup.stale_count += 1
            if (
                lookup.latest_stale_age_seconds is None
                or age_seconds < lookup.latest_stale_age_seconds
            ):
                lookup.latest_stale_age_seconds = age_seconds
                lookup.latest_stale_turn_id = str(turn.turn_id)
            continue
        lookup.fixture = VoiceAudioFixture(
            audio_pcm=audio_pcm,
            audio_ref=artifact_uri,
            source="captured_voice_audio_artifact",
            duration_ms=int(metadata.get("audio_duration_ms") or 0),
            metadata={
                "audio_fixture_source": "captured_voice_audio_artifact",
                "audio_artifact_used": True,
                "audio_artifact_uri": artifact_uri,
                "audio_artifact_relative_path": _relative_artifact_path_for_details(
                    path,
                    settings.artifacts_root,
                ),
                "audio_artifact_sha256": actual_sha,
                "audio_artifact_bytes": len(audio_pcm),
                "audio_fixture_turn_id": str(turn.turn_id),
                "audio_fixture_realtime_session_id": (
                    str(turn_session_id) if turn_session_id is not None else None
                ),
                "audio_fixture_age_seconds": age_seconds,
                "max_voice_audio_artifact_age_seconds": max_age_seconds,
            },
        )
        return lookup
    return lookup


def _turn_age_seconds(created_at: datetime, now: datetime) -> int:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return max(0, int((now - created_at.astimezone(timezone.utc)).total_seconds()))


def _voice_fixture_session_id(
    *,
    metadata: dict[str, object],
    artifact_uri: str | None,
    relative_path: str | None,
    expected_realtime_session_id: UUID | None,
) -> UUID | None:
    metadata_session_id = _uuid_or_none(
        _optional_str(metadata.get("realtime_session_id"))
    )
    if metadata_session_id is not None or expected_realtime_session_id is None:
        return metadata_session_id
    for value in (relative_path, artifact_uri):
        if value and _path_has_session_segment(value, expected_realtime_session_id):
            return expected_realtime_session_id
    return None


def _path_has_session_segment(value: str, realtime_session_id: UUID) -> bool:
    path_value = value.removeprefix("artifact://").lstrip("/")
    return str(realtime_session_id) in PurePosixPath(path_value).parts


def _uuid_or_none(value: str | None) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _voice_audio_artifact_path(
    *,
    settings: Settings,
    artifact_uri: str | None,
    relative_path: str | None,
) -> Path | None:
    relative = relative_path or _relative_path_from_artifact_uri(artifact_uri)
    if not relative:
        return None
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    root = settings.artifacts_root.resolve()
    target = (settings.artifacts_root / candidate).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target


def _relative_path_from_artifact_uri(artifact_uri: str | None) -> str | None:
    if not artifact_uri or not artifact_uri.startswith("artifact://"):
        return None
    return artifact_uri.removeprefix("artifact://").lstrip("/")


def _relative_artifact_path_for_details(path: Path, artifacts_root: Path) -> str:
    try:
        return path.resolve().relative_to(artifacts_root.resolve()).as_posix()
    except ValueError:
        return path.name


def _optional_str(value: object) -> str | None:
    return str(value) if value not in {None, ""} else None


def _sha256(payload: bytes) -> str:
    import hashlib

    return hashlib.sha256(payload).hexdigest()


def _provider_free_demo_step(events) -> ProviderSmokeStepResult:
    demo_event_ids = [
        event.event_id
        for event in events
        if event.event_type == "cockpit_demo_run_seeded" and event.event_id is not None
    ]
    seeded = bool(demo_event_ids)
    return ProviderSmokeStepResult(
        step_id="provider-free-cockpit-demo",
        provider_id="local-demo",
        provider_type="cockpit_demo",
        title="Check provider-free cockpit demo evidence",
        status=(
            ProviderSmokeStepStatus.PASSED
            if seeded
            else ProviderSmokeStepStatus.NOT_RUN
        ),
        required=False,
        live_call=False,
        latency_class="local_demo",
        smoke_proof_status=(
            "seeded_local_demo" if seeded else "local_demo_not_executed"
        ),
        evidence=(
            ["This run has cockpit_demo_run_seeded event evidence."]
            if seeded
            else ["This run is not a provider-free seeded demo run."]
        ),
        next_actions=[
            "Use POST /api/demo/cockpit-run when you want a provider-free UI walkthrough."
        ],
        event_ids=demo_event_ids,
    )


def _blocked_provider_step(
    *,
    step_id: str,
    provider: ProviderReadinessItem,
    title: str,
    live_call: bool,
    latency_class: str,
) -> ProviderSmokeStepResult | None:
    if provider.status != ProviderReadinessStatus.MISSING_CONFIG:
        return None
    return ProviderSmokeStepResult(
        step_id=step_id,
        provider_id=provider.provider_id,
        provider_type=provider.provider_type,
        title=title,
        status=ProviderSmokeStepStatus.BLOCKED,
        required=True,
        live_call=live_call,
        latency_class=latency_class,
        smoke_proof_status="configuration_failed",
        blockers=[
            f"Missing required environment variable: {env_name}"
            for env_name in provider.missing_env
        ],
        next_actions=provider.next_actions,
        details={
            "required_env": provider.required_env,
            "missing_env": provider.missing_env,
        },
    )


def _not_run_provider_step(
    *,
    step_id: str,
    provider: ProviderReadinessItem,
    title: str,
    live_call: bool,
    latency_class: str,
    evidence: list[str],
    next_actions: list[str] | None = None,
) -> ProviderSmokeStepResult:
    return ProviderSmokeStepResult(
        step_id=step_id,
        provider_id=provider.provider_id,
        provider_type=provider.provider_type,
        title=title,
        status=ProviderSmokeStepStatus.NOT_RUN,
        required=True,
        live_call=live_call,
        latency_class=latency_class,
        smoke_proof_status="ready_not_executed",
        evidence=evidence,
        next_actions=next_actions
        or [
            "Re-run provider smoke with execute_live_calls=true after confirming credentials and cost."
        ],
    )


def _missing_service_step(
    *,
    step_id: str,
    provider: ProviderReadinessItem,
    title: str,
    live_call: bool,
    latency_class: str,
    service_name: str,
) -> ProviderSmokeStepResult:
    return ProviderSmokeStepResult(
        step_id=step_id,
        provider_id=provider.provider_id,
        provider_type=provider.provider_type,
        title=title,
        status=ProviderSmokeStepStatus.BLOCKED,
        required=True,
        live_call=live_call,
        latency_class=latency_class,
        smoke_proof_status="configuration_failed",
        blockers=[f"{service_name} is not available in workflow services."],
        next_actions=["Check FastAPI dependency wiring for provider services."],
    )


def _exception_step(
    *,
    step_id: str,
    provider: ProviderReadinessItem,
    title: str,
    status: ProviderSmokeStepStatus,
    live_call: bool,
    latency_class: str,
    started: float,
    error: str,
) -> ProviderSmokeStepResult:
    safe_error = _redact_provider_failure_text(error)
    return ProviderSmokeStepResult(
        step_id=step_id,
        provider_id=provider.provider_id,
        provider_type=provider.provider_type,
        title=title,
        status=status,
        required=True,
        live_call=live_call,
        latency_class=latency_class,
        provider_latency_ms=_elapsed_ms(started),
        end_to_end_latency_ms=_elapsed_ms(started),
        smoke_proof_status=(
            "configuration_failed"
            if status == ProviderSmokeStepStatus.BLOCKED
            else "provider_error"
        ),
        blockers=[safe_error],
        next_actions=provider.next_actions,
        error=safe_error,
    )


def _imagegen_boundary_step() -> ProviderSmokeStepResult:
    return ProviderSmokeStepResult(
        step_id="imagegen-boundary-smoke",
        provider_id="imagegen",
        provider_type="raster_visual_generation",
        title="Verify imagegen remains a tool boundary",
        status=ProviderSmokeStepStatus.TOOL_BOUNDARY,
        required=False,
        live_call=False,
        latency_class="tool_boundary",
        smoke_proof_status="codex_tool_boundary",
        evidence=[
            "FastAPI stores image prompt packs and provenance.",
            "Raster generation remains outside the app through the Codex imagegen tool.",
        ],
        next_actions=[
            "Invoke imagegen from Codex only when a run requires real raster social assets."
        ],
    )


def _build_result(
    *,
    run_id: UUID,
    request: ProviderSmokeRunRequest,
    readiness: ProviderReadinessResult,
    steps: list[ProviderSmokeStepResult],
) -> ProviderSmokeRunResult:
    required_steps = [step for step in steps if step.required]
    source_ids = list(
        dict.fromkeys(source_id for step in steps for source_id in step.source_ids)
    )
    realtime_session_ids = list(
        dict.fromkeys(
            session_id for step in steps for session_id in step.realtime_session_ids
        )
    )
    status = _overall_status(required_steps)
    passed_count = sum(
        1 for step in steps if step.status == ProviderSmokeStepStatus.PASSED
    )
    blocked_count = sum(
        1 for step in steps if step.status == ProviderSmokeStepStatus.BLOCKED
    )
    failed_count = sum(
        1 for step in steps if step.status == ProviderSmokeStepStatus.FAILED
    )
    not_run_count = sum(
        1 for step in steps if step.status == ProviderSmokeStepStatus.NOT_RUN
    )
    tool_boundary_count = sum(
        1 for step in steps if step.status == ProviderSmokeStepStatus.TOOL_BOUNDARY
    )
    return ProviderSmokeRunResult(
        run_id=run_id,
        status=status,
        execute_live_calls=request.execute_live_calls,
        provider_readiness=readiness,
        step_count=len(steps),
        passed_count=passed_count,
        blocked_count=blocked_count,
        failed_count=failed_count,
        not_run_count=not_run_count,
        tool_boundary_count=tool_boundary_count,
        source_ids=source_ids,
        realtime_session_ids=realtime_session_ids,
        steps=steps,
        summary=(
            f"Provider smoke is {status}: {len(steps)} step(s), "
            f"{passed_count} passed, "
            f"{blocked_count} blocked, "
            f"{failed_count} failed, "
            f"{not_run_count} not run."
        ),
    )


def _provider_configuration_blocker_steps(
    result: ProviderSmokeRunResult,
) -> list[ProviderSmokeStepResult]:
    return [
        step
        for step in result.steps
        if step.status == ProviderSmokeStepStatus.BLOCKED
        and step.smoke_proof_status == "configuration_failed"
    ]


def _provider_configuration_followup_message(
    *,
    run_id: UUID,
    request: ProviderSmokeRunRequest,
    result: ProviderSmokeRunResult,
    blocked_steps: list[ProviderSmokeStepResult],
) -> AgentMessage:
    blocked_payloads = _provider_configuration_blocker_payloads(
        result,
        blocked_steps,
    )
    recipient_agent_id = _provider_configuration_recipient(blocked_steps)
    recommended_worker_agent_ids = _provider_configuration_recommended_agents(
        blocked_steps
    )
    return AgentMessage(
        message_id=_provider_configuration_message_id(
            run_id=run_id,
            blocked_payloads=blocked_payloads,
        ),
        run_id=run_id,
        sender_agent_id="observability-agent",
        recipient_agent_id=recipient_agent_id,
        task_type="review_provider_configuration_blockers",
        payload={
            "workflow": "provider_smoke_configuration_followup_v1",
            "topic": request.topic,
            "provider_smoke_status": result.status,
            "execute_live_calls": result.execute_live_calls,
            "ledger_artifact_id": (
                str(result.ledger_artifact_id) if result.ledger_artifact_id else None
            ),
            "provider_smoke_event_id": result.event_id,
            "blocked_step_count": len(blocked_payloads),
            "blocked_steps": blocked_payloads,
            "required_action": (
                "Review local provider configuration, endpoint readiness, and "
                "smoke rerun steps. Do not request, echo, or persist secret values; "
                "only use non-secret env names, file paths, readiness statuses, "
                "and operator setup actions."
            ),
            "recommended_worker_agent_ids": recommended_worker_agent_ids,
            "recommended_worker_use_gemma": False,
        },
    )


def _provider_configuration_blocker_payloads(
    result: ProviderSmokeRunResult,
    blocked_steps: list[ProviderSmokeStepResult],
) -> list[dict[str, Any]]:
    providers = {
        provider.provider_id: provider
        for provider in result.provider_readiness.providers
    }
    payloads: list[dict[str, Any]] = []
    for step in blocked_steps:
        provider = providers.get(step.provider_id)
        payloads.append(
            {
                "step_id": step.step_id,
                "provider_id": step.provider_id,
                "provider_type": step.provider_type,
                "title": step.title,
                "live_call": step.live_call,
                "latency_class": step.latency_class,
                "smoke_proof_status": step.smoke_proof_status,
                "blockers": list(step.blockers),
                "next_actions": list(step.next_actions),
                "required_env": list(provider.required_env if provider else []),
                "missing_env": list(
                    _step_missing_env(step)
                    or (provider.missing_env if provider else [])
                ),
                "secret_files": [
                    secret_file.model_dump(mode="json")
                    for secret_file in (provider.secret_files if provider else [])
                    if not provider
                    or not provider.missing_env
                    or secret_file.env_name in provider.missing_env
                ],
                "details": _safe_provider_metadata(step.details),
            }
        )
    return payloads


def _step_missing_env(step: ProviderSmokeStepResult) -> list[str]:
    missing_env = step.details.get("missing_env")
    if isinstance(missing_env, list):
        return [str(env_name) for env_name in missing_env]
    return []


def _provider_configuration_recipient(
    blocked_steps: list[ProviderSmokeStepResult],
) -> str:
    if any(
        step.provider_type in {"gemma4_hf_endpoint", "realtime_audio", "reranker"}
        or step.step_id == "gemma-kokoro-voice-streaming-smoke"
        for step in blocked_steps
    ):
        return "inference-systems-engineer"
    return "agent-harness-engineer"


def _provider_configuration_recommended_agents(
    blocked_steps: list[ProviderSmokeStepResult],
) -> list[str]:
    agents = [
        "inference-systems-engineer",
        "agent-harness-engineer",
        "observability-agent",
    ]
    if any(step.provider_type == "web_search" for step in blocked_steps):
        agents.extend(["web-research-agent", "retrieval-intelligence-agent"])
    return list(dict.fromkeys(agents))


def _provider_configuration_message_id(
    *,
    run_id: UUID,
    blocked_payloads: list[dict[str, Any]],
) -> UUID:
    signature_payload = _provider_configuration_signature_payload(blocked_payloads)
    signature = json.dumps(signature_payload, sort_keys=True, separators=(",", ":"))
    return uuid5(
        NAMESPACE_URL,
        f"all-about-llms:provider_smoke_configuration_followup:{run_id}:{signature}",
    )


def _provider_smoke_ledger_artifact_id(
    *,
    run_id: UUID,
    request: ProviderSmokeRunRequest,
    result: ProviderSmokeRunResult,
    blocked_steps: list[ProviderSmokeStepResult],
) -> UUID | None:
    if not blocked_steps:
        return None
    blocked_payloads = _provider_configuration_blocker_payloads(
        result,
        blocked_steps,
    )
    signature_payload = {
        "request": {
            "execute_live_calls": request.execute_live_calls,
            "topic": request.topic,
            "realtime_provider": request.realtime_provider,
            "realtime_session_id": (
                str(request.realtime_session_id)
                if request.realtime_session_id
                else None
            ),
            "require_voice_agent_presence": request.require_voice_agent_presence,
            "search_query": request.search_query,
            "include_gemma": request.include_gemma,
            "include_realtime": request.include_realtime,
            "include_web_search": request.include_web_search,
            "include_reranker": request.include_reranker,
            "include_imagegen_boundary": request.include_imagegen_boundary,
        },
        "blockers": _provider_configuration_signature_payload(blocked_payloads),
    }
    signature = json.dumps(signature_payload, sort_keys=True, separators=(",", ":"))
    return uuid5(
        NAMESPACE_URL,
        f"all-about-llms:provider_smoke_ledger:{run_id}:{signature}",
    )


def _provider_configuration_signature_payload(
    blocked_payloads: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "step_id": payload["step_id"],
            "provider_id": payload["provider_id"],
            "provider_type": payload["provider_type"],
            "blockers": payload["blockers"],
            "missing_env": payload["missing_env"],
            "secret_files": [
                {
                    "env_name": secret_file["env_name"],
                    "file_env_name": secret_file["file_env_name"],
                    "status": secret_file["status"],
                    "configured": secret_file["configured"],
                    "path": secret_file["path"],
                }
                for secret_file in payload["secret_files"]
            ],
        }
        for payload in blocked_payloads
    ]


def _provider_configuration_event_key(
    *,
    run_id: UUID,
    event_type: str,
    message_id: UUID,
) -> str:
    return f"provider_smoke_configuration_followup_v1:{run_id}:{event_type}:{message_id}"


async def _record_agent_message_if_absent(store, message: AgentMessage):
    recorder = getattr(store, "record_agent_message_if_absent", None)
    if callable(recorder):
        return await recorder(message)
    return None


async def _record_provider_smoke_artifact(store, artifact: ArtifactRecord):
    recorder = getattr(store, "record_artifact_if_absent", None)
    if callable(recorder):
        recorded = await recorder(artifact)
        if recorded is None:
            updater = getattr(store, "update_artifact", None)
            if callable(updater):
                await updater(artifact)
        return recorded or artifact
    return await store.record_artifact(artifact)


async def _append_provider_smoke_event_if_absent(
    store,
    event: RunEvent,
    *,
    idempotency_key: str,
) -> RunEvent | None:
    appender = getattr(store, "append_event_if_absent", None)
    if callable(appender):
        return await appender(event, idempotency_key=idempotency_key)
    event.payload = {
        **event.payload,
        "event_idempotency_key": idempotency_key,
    }
    return await store.append_event(event)


def _overall_status(
    required_steps: list[ProviderSmokeStepResult],
) -> ProviderSmokeRunStatus:
    if any(step.status == ProviderSmokeStepStatus.FAILED for step in required_steps):
        return ProviderSmokeRunStatus.FAILED
    if any(step.status == ProviderSmokeStepStatus.BLOCKED for step in required_steps):
        return ProviderSmokeRunStatus.BLOCKED
    if any(
        step.status == ProviderSmokeStepStatus.NOT_RUN and step.live_call
        for step in required_steps
    ):
        return ProviderSmokeRunStatus.NEEDS_LIVE_SMOKE
    if any(step.status == ProviderSmokeStepStatus.NOT_RUN for step in required_steps):
        return ProviderSmokeRunStatus.NEEDS_REVIEW
    return ProviderSmokeRunStatus.PASSED


def _provider_requires_control_binding(provider: str | None) -> bool:
    return provider in {
        "openrouter_livekit",
        "openrouter-livekit",
        "gemma4_realtime",
        "gemma4-realtime",
    }


def _realtime_provider_matches_session(
    *,
    expected_provider: str,
    session_provider: str,
) -> bool:
    if session_provider == expected_provider:
        return True
    openrouter_aliases = {
        "openrouter_livekit",
        "openrouter-livekit",
        "gemma4_realtime",
        "gemma4-realtime",
    }
    return expected_provider in openrouter_aliases and session_provider in openrouter_aliases


def _session_has_control_binding_proof(session: RealtimeSessionRecord) -> bool:
    if not _provider_requires_control_binding(session.provider):
        return True
    return bool(session.metadata.get("control_binding_token_issued"))


def _control_binding_validation_failure(
    provider_response,
    settings: Settings,
    *,
    run_id: UUID,
    realtime_session_id: UUID,
) -> dict[str, Any] | None:
    if not _provider_requires_control_binding(provider_response.provider):
        return None
    transport = (
        provider_response.transport
        if isinstance(provider_response.transport, dict)
        else {}
    )
    transport_metadata = (
        transport.get("metadata") if isinstance(transport.get("metadata"), dict) else {}
    )
    room_name = _optional_str(transport.get("room_name"))
    participant_identity = _optional_str(transport.get("participant_identity"))
    agent_identity = _optional_str(transport.get("agent_identity")) or _optional_str(
        transport.get("agent_participant_identity")
    )
    token = transport_metadata.get("control_binding_token")
    details = {
        "control_binding_token_issued": False,
        "control_binding_token_verified": False,
        "room_name": room_name,
        "participant_identity": participant_identity,
        "agent_participant_identity": agent_identity,
    }
    if not token:
        return {
            "status": "control_binding_missing",
            "blocker": (
                "OpenRouter/Kokoro LiveKit realtime sessions must include a signed control binding proof before they can be used for voice smoke."
            ),
            "details": details,
        }
    if not all([room_name, participant_identity, agent_identity]):
        return {
            "status": "control_binding_missing",
            "blocker": (
                "OpenRouter/Kokoro LiveKit realtime sessions must include room, participant, and agent identities for control binding verification."
            ),
            "details": details,
        }
    verified = verify_livekit_control_binding_token(
        token,
        settings.livekit_api_secret,
        run_id=str(run_id),
        realtime_session_id=str(realtime_session_id),
        room_name=room_name,
        participant_identity=participant_identity,
        agent_identity=agent_identity,
    )
    if not verified:
        return {
            "status": "control_binding_invalid",
            "blocker": (
                "The OpenRouter/Kokoro LiveKit control binding proof does not match the recorded run, session, room, participant, and agent identities."
            ),
            "details": {
                **details,
                "control_binding_token_issued": True,
            },
        }
    return None


def _safe_provider_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    safe_metadata: dict[str, Any] = {}
    for key, value in metadata.items():
        if _provider_metadata_key_is_sensitive(key):
            if _normalize_provider_metadata_key(key) == "token" and value is None:
                safe_metadata[key] = None
            continue
        safe_metadata[key] = _safe_provider_metadata_value(value)
    return safe_metadata


def _safe_provider_metadata_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _safe_provider_metadata(value)
    if isinstance(value, list):
        return [_safe_provider_metadata_value(item) for item in value]
    if isinstance(value, str):
        return _redact_provider_failure_text(value)
    return value


def _provider_metadata_key_is_sensitive(key: Any) -> bool:
    if not isinstance(key, str) or not key.strip():
        return False
    normalized = _normalize_provider_metadata_key(key)
    safe_exact = {
        "control_binding_required",
        "control_binding_token_issued",
        "has_token",
        "has_transport_token",
        "livekit_token_expires_at_unix",
        "token_persisted",
    }
    if normalized in safe_exact:
        return False
    compact = normalized.replace("_", "")
    sensitive_exact = {
        "access_token",
        "api_key",
        "api_secret",
        "authorization",
        "binding_signature",
        "binding_token",
        "client_secret",
        "control_binding_signature",
        "control_binding_token",
        "livekit_token",
        "private_key",
        "raw_request",
        "raw_response",
        "refresh_token",
        "session_token",
        "signed_url",
        "token",
        "websocket_url",
    }
    sensitive_compact = {item.replace("_", "") for item in sensitive_exact}
    if normalized in sensitive_exact or compact in sensitive_compact:
        return True
    if (
        "authorization" in compact
        or "bearer" in compact
        or "credential" in compact
    ):
        return True
    return normalized.endswith(("_key", "_secret", "_token", "_password"))


def _normalize_provider_metadata_key(key: str) -> str:
    camel_split = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key.strip())
    return re.sub(r"[^a-z0-9]+", "_", camel_split.lower()).strip("_")


def _redact_provider_failure_text(value: str) -> str:
    redacted = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [redacted]", value)
    redacted = re.sub(r"hf_[A-Za-z0-9]{20,}", "hf_[redacted]", redacted)
    redacted = re.sub(r"tvly-[A-Za-z0-9-]{20,}", "tvly-[redacted]", redacted)
    return redacted


def _provider_transport_payload(provider_response) -> dict[str, Any] | None:
    if not provider_response.transport:
        return None
    transport = dict(provider_response.transport)
    transport["token"] = None
    transport["token_persisted"] = False
    safe_transport = _safe_provider_metadata(transport)
    safe_transport["token"] = None
    safe_transport["token_persisted"] = False
    return safe_transport


def _event_ids(*events) -> list[int]:
    return [event.event_id for event in events if event.event_id is not None]


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)
