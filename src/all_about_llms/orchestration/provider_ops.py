from uuid import UUID

from all_about_llms.contracts import (
    ArtifactRecord,
    ArtifactType,
    ProviderOperationEntry,
    ProviderOperationsLedgerRequest,
    ProviderOperationsLedgerResult,
    RunEvent,
)


class ProviderOperationsLedgerError(RuntimeError):
    """Base error for provider operations ledger generation."""


class ProviderOperationsLedgerRunNotFoundError(ProviderOperationsLedgerError):
    """Raised when a run cannot be found for provider operations work."""


class ProviderOperationsLedgerWorkflow:
    """Build an inspectable ledger of provider, tool, and model operations."""

    def __init__(self, store):
        self._store = store

    async def build(
        self, run_id: UUID, request: ProviderOperationsLedgerRequest
    ) -> ProviderOperationsLedgerResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise ProviderOperationsLedgerRunNotFoundError(f"Run not found: {run_id}")

        events = await self._store.list_events(run_id, limit=request.event_limit)
        realtime_sessions = await self._store.list_realtime_sessions(run_id)
        artifacts = await self._store.list_artifacts(run_id)
        operations = [
            *_operations_from_events(events),
            *_operations_from_realtime_sessions(realtime_sessions),
        ]
        if request.include_artifact_provenance:
            operations.extend(_operations_from_artifacts(artifacts))

        provider_counts = _count_by_provider(operations)
        operation_type_counts = _value_counts(
            operation.operation_type for operation in operations
        )
        provider_fallback_count = operation_type_counts.get("provider_fallback", 0)
        policy_denial_count = sum(
            1
            for operation in operations
            if operation.operation_type in {"model_policy", "tool_policy"}
            and operation.status == "denied"
        )
        model_operation_count = sum(
            1
            for operation in operations
            if operation.model_id
            or operation.operation_type in {"model_policy", "model_generation"}
        )
        tool_operation_count = sum(
            1
            for operation in operations
            if operation.tool_name or operation.operation_type == "tool_policy"
        )

        result = ProviderOperationsLedgerResult(
            run_id=run_id,
            event_count=len(events),
            realtime_session_count=len(realtime_sessions),
            provider_operation_count=len(operations),
            model_operation_count=model_operation_count,
            tool_operation_count=tool_operation_count,
            provider_fallback_count=provider_fallback_count,
            policy_denial_count=policy_denial_count,
            provider_counts=provider_counts,
            operation_type_counts=operation_type_counts,
            operations=operations,
            summary=(
                f"Provider operations ledger captured {len(operations)} "
                f"operation(s), {provider_fallback_count} fallback(s), and "
                f"{policy_denial_count} policy denial(s)."
            ),
        )

        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.PROVIDER_OPERATIONS_LEDGER,
                title="Provider operations ledger",
                uri=f"artifact://runs/{run_id}/provider-operations-ledger",
                content=result.model_dump(
                    mode="json", exclude={"ledger_artifact_id", "event_id"}
                ),
                provenance={
                    "workflow": "provider_operations_ledger_v1",
                    "agent_id": "observability-agent",
                    "event_limit": request.event_limit,
                    "include_artifact_provenance": request.include_artifact_provenance,
                },
                revision_history=[
                    {
                        "actor": "observability-agent",
                        "note": "Captured provider, model, tool, realtime, fallback, and artifact provenance operations.",
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
                event_type="provider_operations_ledger_built",
                actor="observability-agent",
                payload={
                    "provider_operation_count": result.provider_operation_count,
                    "model_operation_count": result.model_operation_count,
                    "tool_operation_count": result.tool_operation_count,
                    "provider_fallback_count": result.provider_fallback_count,
                    "policy_denial_count": result.policy_denial_count,
                    "realtime_session_count": result.realtime_session_count,
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


def _operations_from_events(events) -> list[ProviderOperationEntry]:
    operations = []
    for event in events:
        payload = event.payload or {}
        if event.event_type in {"agent_model_use_approved", "agent_model_use_denied"}:
            operations.append(
                ProviderOperationEntry(
                    operation_type="model_policy",
                    provider=_provider_from_model(payload.get("model_id")),
                    agent_id=payload.get("agent_id"),
                    model_id=payload.get("model_id"),
                    latency_class=_latency_class(payload, "quick_critique"),
                    end_to_end_latency_ms=_latency_ms(
                        payload, "end_to_end_latency_ms"
                    ),
                    provider_latency_ms=_latency_ms(payload, "provider_latency_ms"),
                    fallback_reason=_fallback_reason(payload),
                    smoke_proof_status=_smoke_proof_status(payload),
                    status="approved" if event.event_type.endswith("approved") else "denied",
                    source_event_id=event.event_id,
                    details={
                        "allowed_models": payload.get("allowed_models", []),
                        "reason": payload.get("reason"),
                        "message_id": payload.get("message_id"),
                        "metadata": payload.get("metadata", {}),
                    },
                )
            )
        elif event.event_type in {"agent_tool_use_approved", "agent_tool_use_denied"}:
            operations.append(
                ProviderOperationEntry(
                    operation_type="tool_policy",
                    provider=_provider_from_tool(payload.get("tool_name")),
                    agent_id=payload.get("agent_id"),
                    tool_name=payload.get("tool_name"),
                    latency_class=_latency_class(payload, "quick_critique"),
                    end_to_end_latency_ms=_latency_ms(
                        payload, "end_to_end_latency_ms"
                    ),
                    provider_latency_ms=_latency_ms(payload, "provider_latency_ms"),
                    fallback_reason=_fallback_reason(payload),
                    smoke_proof_status=_smoke_proof_status(payload),
                    status="approved" if event.event_type.endswith("approved") else "denied",
                    source_event_id=event.event_id,
                    details={
                        "allowed_tools": payload.get("allowed_tools", []),
                        "reason": payload.get("reason"),
                        "message_id": payload.get("message_id"),
                        "metadata": payload.get("metadata", {}),
                    },
                )
            )
        elif event.event_type == "provider_fallback":
            operations.append(
                ProviderOperationEntry(
                    operation_type="provider_fallback",
                    provider=payload.get("provider"),
                    agent_id=event.actor,
                    latency_class=_latency_class(payload, "background_research"),
                    end_to_end_latency_ms=_latency_ms(
                        payload, "end_to_end_latency_ms"
                    ),
                    provider_latency_ms=_latency_ms(payload, "provider_latency_ms"),
                    fallback_reason=_fallback_reason(payload)
                    or str(payload.get("reason")),
                    smoke_proof_status=_smoke_proof_status(payload),
                    status="fallback",
                    source_event_id=event.event_id,
                    details={"reason": payload.get("reason"), **payload},
                )
            )
        elif event.event_type in {
            "gemma_synthesis_completed",
            "gemma_revision_completed",
            "gemma_worker_completed",
            "gemma_multimodal_review_completed",
            "provider_smoke_gemma_completed",
        }:
            operations.append(
                ProviderOperationEntry(
                    operation_type="model_generation",
                    provider="huggingface",
                    agent_id=payload.get("agent_id") or event.actor,
                    model_id=payload.get("model_id"),
                    latency_class=_latency_class(payload, "long_synthesis"),
                    end_to_end_latency_ms=_latency_ms(
                        payload, "end_to_end_latency_ms"
                    ),
                    provider_latency_ms=_latency_ms(payload, "provider_latency_ms"),
                    fallback_reason=_fallback_reason(payload),
                    smoke_proof_status=_smoke_proof_status(
                        payload, default="provider_backed"
                    ),
                    status="completed",
                    source_event_id=event.event_id,
                    details={
                        "usage": payload.get("usage", {}),
                        "event_type": event.event_type,
                    },
                )
            )
        elif event.event_type in {
            "provider_smoke_web_search_completed",
            "provider_smoke_reranker_completed",
        }:
            operations.append(
                ProviderOperationEntry(
                    operation_type="provider_smoke",
                    provider=payload.get("provider"),
                    agent_id=event.actor,
                    latency_class=_latency_class(payload, "background_research"),
                    end_to_end_latency_ms=_latency_ms(
                        payload, "end_to_end_latency_ms"
                    ),
                    provider_latency_ms=_latency_ms(payload, "provider_latency_ms"),
                    fallback_reason=_fallback_reason(payload),
                    smoke_proof_status=_smoke_proof_status(payload),
                    status="completed",
                    source_event_id=event.event_id,
                    details=payload,
                )
            )
        elif event.event_type in {
            "realtime_session_created",
            "realtime_rehearsal_session_created",
            "realtime_session_configuration_failed",
            "realtime_session_status_updated",
            "realtime_turn_routed",
            "realtime_turn_recorded",
        }:
            operations.append(
                ProviderOperationEntry(
                    operation_type="realtime_event",
                    provider=payload.get("provider"),
                    agent_id=event.actor,
                    latency_class=_latency_class(payload, "realtime_interrupt"),
                    end_to_end_latency_ms=_latency_ms(
                        payload, "end_to_end_latency_ms"
                    ),
                    provider_latency_ms=_latency_ms(payload, "provider_latency_ms"),
                    fallback_reason=_fallback_reason(payload),
                    smoke_proof_status=_smoke_proof_status(
                        payload,
                        default=(
                            "rehearsal_only"
                            if event.event_type == "realtime_rehearsal_session_created"
                            else None
                        ),
                    ),
                    status=_realtime_event_status(event.event_type, payload),
                    source_event_id=event.event_id,
                    details=payload,
                )
            )
    return operations


def _operations_from_realtime_sessions(sessions) -> list[ProviderOperationEntry]:
    return [
        ProviderOperationEntry(
            operation_type="realtime_session",
            provider=session.provider,
            agent_id="realtime-conversation-host",
            latency_class=_latency_class(session.metadata, "realtime_interrupt"),
            end_to_end_latency_ms=_latency_ms(
                session.metadata, "end_to_end_latency_ms"
            ),
            provider_latency_ms=_latency_ms(session.metadata, "provider_latency_ms"),
            fallback_reason=_fallback_reason(session.metadata),
            smoke_proof_status=_session_smoke_proof_status(session),
            status=session.status.value,
            source_session_id=session.realtime_session_id,
            details={
                "provider_session_id": session.provider_session_id,
                "voice": session.voice,
                "audio_mode": session.audio_mode,
                "has_client_secret": session.has_client_secret,
                "has_websocket_url": session.has_websocket_url,
                "expires_at_unix": session.expires_at_unix,
                "metadata": session.metadata,
            },
        )
        for session in sessions
    ]


def _operations_from_artifacts(artifacts) -> list[ProviderOperationEntry]:
    operations = []
    for artifact in artifacts:
        provenance = artifact.provenance or {}
        model_provider = provenance.get("model_provider")
        model_id = provenance.get("model_id")
        if model_provider or model_id:
            operations.append(
                ProviderOperationEntry(
                    operation_type="artifact_model_provenance",
                    provider=model_provider,
                    agent_id=provenance.get("agent_id"),
                    model_id=model_id,
                    latency_class=_latency_class(provenance, "long_synthesis"),
                    end_to_end_latency_ms=_latency_ms(
                        provenance, "end_to_end_latency_ms"
                    ),
                    provider_latency_ms=_latency_ms(
                        provenance, "provider_latency_ms"
                    ),
                    fallback_reason=_fallback_reason(provenance),
                    smoke_proof_status=_artifact_smoke_proof_status(provenance),
                    status="recorded",
                    source_artifact_id=artifact.artifact_id,
                    details={
                        "artifact_type": artifact.artifact_type.value,
                        "title": artifact.title,
                        "generation_mode": provenance.get("generation_mode"),
                        "provider_usage": provenance.get("provider_usage", {}),
                    },
                )
            )
        if artifact.artifact_type in {
            ArtifactType.IMAGE,
            ArtifactType.AUDIO,
            ArtifactType.VIDEO,
        }:
            operations.append(
                ProviderOperationEntry(
                    operation_type="media_provider_boundary",
                    provider=_media_provider(artifact),
                    agent_id=provenance.get("agent_id"),
                    latency_class=_latency_class(provenance, "media_generation"),
                    end_to_end_latency_ms=_latency_ms(
                        provenance, "end_to_end_latency_ms"
                    ),
                    provider_latency_ms=_latency_ms(
                        provenance, "provider_latency_ms"
                    ),
                    fallback_reason=_fallback_reason(provenance),
                    smoke_proof_status=_smoke_proof_status(provenance),
                    status="planned",
                    source_artifact_id=artifact.artifact_id,
                    details={
                        "artifact_type": artifact.artifact_type.value,
                        "title": artifact.title,
                        "workflow": provenance.get("workflow"),
                    },
                )
            )
    return operations


def _provider_from_model(model_id: str | None) -> str | None:
    if not model_id:
        return None
    normalized = model_id.lower()
    if "gemma" in normalized:
        return "huggingface"
    if "realtime" in normalized:
        return "realtime_audio"
    return None


def _provider_from_tool(tool_name: str | None) -> str | None:
    if tool_name == "web_search":
        return "web_search"
    if tool_name == "imagegen":
        return "imagegen"
    if tool_name in {"realtime_audio_provider", "tts_provider", "voice_session"}:
        return "realtime_audio"
    return tool_name


def _realtime_event_status(event_type: str, payload: dict) -> str:
    if event_type == "realtime_session_configuration_failed":
        return "failed"
    if event_type == "realtime_rehearsal_session_created":
        return "rehearsal"
    if event_type == "realtime_session_status_updated":
        return str(payload.get("status") or "updated")
    if event_type == "realtime_turn_routed":
        return "routed"
    return "created"


def _media_provider(artifact: ArtifactRecord) -> str:
    if artifact.artifact_type == ArtifactType.IMAGE:
        return "imagegen"
    if artifact.artifact_type == ArtifactType.AUDIO:
        return "realtime_audio"
    if artifact.artifact_type == ArtifactType.VIDEO:
        return "video_planning"
    return "artifact_store"


def _latency_class(payload: dict, default: str | None = None) -> str | None:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    value = payload.get("latency_class") or metadata.get("latency_class") or default
    return str(value) if value else None


def _latency_ms(payload: dict, key: str) -> float | None:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    value = payload.get(key, metadata.get(key))
    if value is None and key == "end_to_end_latency_ms":
        value = payload.get("latency_ms", metadata.get("latency_ms"))
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fallback_reason(payload: dict) -> str | None:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    value = payload.get("fallback_reason") or metadata.get("fallback_reason")
    return str(value) if value else None


def _smoke_proof_status(payload: dict, default: str | None = None) -> str | None:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    value = payload.get("smoke_proof_status") or metadata.get("smoke_proof_status")
    if value:
        return str(value)
    if payload.get("dry_run") or payload.get("not_provider_backed"):
        return "rehearsal_only"
    return default


def _artifact_smoke_proof_status(provenance: dict) -> str | None:
    explicit = _smoke_proof_status(provenance)
    if explicit:
        return explicit
    provider = str(provenance.get("model_provider") or "").lower()
    generation_mode = str(provenance.get("generation_mode") or "").lower()
    source = str(provenance.get("source") or "").lower()
    if provider in {"seeded_local_demo", "deterministic_local", "local"}:
        return "local_demo_not_provider_backed"
    if "fallback" in generation_mode or "deterministic" in generation_mode:
        return "fallback_not_provider_backed"
    if source == "cockpit_demo":
        return "local_demo_not_provider_backed"
    if provider == "huggingface":
        return "provider_backed"
    return None


def _session_smoke_proof_status(session) -> str:
    explicit = _smoke_proof_status(session.metadata)
    if explicit:
        return explicit
    if session.metadata.get("not_provider_backed") or session.metadata.get("dry_run"):
        return "rehearsal_only"
    if session.has_client_secret or session.has_websocket_url:
        return "provider_backed"
    return "configured_without_client_transport"


def _count_by_provider(operations: list[ProviderOperationEntry]) -> dict[str, int]:
    return _value_counts(
        operation.provider or "unspecified" for operation in operations
    )


def _value_counts(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return counts
