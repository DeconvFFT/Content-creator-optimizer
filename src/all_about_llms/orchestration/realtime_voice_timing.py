from datetime import datetime
from dataclasses import dataclass
from uuid import UUID

from all_about_llms.contracts import (
    ArtifactRecord,
    ArtifactType,
    RealtimeSessionStatus,
    RealtimeVoiceTimingLedgerRequest,
    RealtimeVoiceTimingLedgerResult,
    RealtimeVoiceTimingStageEntry,
    RealtimeVoiceTimingTurnEntry,
    RunEvent,
)


class RealtimeVoiceTimingLedgerError(RuntimeError):
    """Base error for realtime voice timing ledger generation."""


class RealtimeVoiceTimingLedgerRunNotFoundError(RealtimeVoiceTimingLedgerError):
    """Raised when a run cannot be found for realtime voice timing work."""


@dataclass(slots=True)
class TurnTimingChain:
    speech_start: RunEvent | None = None
    turn_commit: RunEvent | None = None
    turn_start: RunEvent | None = None
    gemma_start: RunEvent | None = None
    first_text: RunEvent | None = None
    first_audio: RunEvent | None = None
    cancel_ack: RunEvent | None = None
    cancelled: RunEvent | None = None
    failed: RunEvent | None = None


CORE_EVENT_TYPES = {
    "gemma_kokoro_voice_agent_ready",
    "voice_agent_media_bridge_ready",
    "voice_user_speech_started",
    "voice_user_turn_committed",
    "voice_barge_in_detected",
    "voice_edge_cancellation_acknowledged",
    "gemma_kokoro_voice_turn_started",
    "gemma_generation_started",
    "assistant_text_delta",
    "kokoro_tts_fragment_started",
    "assistant_audio_chunk_published",
    "assistant_response_completed",
    "gemma_kokoro_voice_turn_cancelled",
    "gemma_kokoro_voice_turn_failed",
    "realtime_session_created",
    "realtime_turn_recorded",
    "realtime_turn_routed",
    "realtime_session_control_recorded",
}


class RealtimeVoiceTimingLedgerWorkflow:
    """Build a measured ledger for the LiveKit/OpenRouter/Kokoro voice loop."""

    def __init__(self, store):
        self._store = store

    async def build(
        self,
        run_id: UUID,
        request: RealtimeVoiceTimingLedgerRequest,
    ) -> RealtimeVoiceTimingLedgerResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise RealtimeVoiceTimingLedgerRunNotFoundError(
                f"Run not found: {run_id}"
            )

        sessions = await self._store.list_realtime_sessions(run_id)
        events = sorted(
            await self._store.list_events(run_id, limit=request.event_limit),
            key=_event_time,
        )
        timing_events = [event for event in events if event.event_type in CORE_EVENT_TYPES]
        target_session_id = _target_livekit_session_id(sessions, timing_events)
        timing_events = _session_scoped_timing_events(
            timing_events,
            target_session_id=target_session_id,
        )
        stages = _stage_entries(
            sessions,
            timing_events,
            target_session_id=target_session_id,
        )
        turns = _turn_entries(timing_events)
        measured_stage_count = sum(1 for stage in stages if stage.status == "measured")
        missing_stage_count = sum(
            1 for stage in stages if stage.status in {"missing", "partial"}
        )
        status = _ledger_status(sessions, stages)
        recommended_next_actions = _recommended_next_actions(stages, sessions)
        result = RealtimeVoiceTimingLedgerResult(
            run_id=run_id,
            status=status,
            session_count=len(sessions),
            event_count=len(timing_events),
            measured_stage_count=measured_stage_count,
            missing_stage_count=missing_stage_count,
            stages=stages,
            turns=turns,
            recommended_next_actions=recommended_next_actions,
            summary=(
                f"Realtime voice timing ledger is {status}: "
                f"{measured_stage_count}/{len(stages)} stage(s) measured from "
                f"{len(timing_events)} voice/runtime event(s)."
            ),
        )

        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.REALTIME_VOICE_TIMING_LEDGER,
                title="Realtime voice timing ledger",
                uri=f"artifact://runs/{run_id}/realtime-voice-timing-ledger",
                content=result.model_dump(
                    mode="json", exclude={"ledger_artifact_id", "event_id"}
                ),
                provenance={
                    "workflow": "realtime_voice_timing_ledger_v1",
                    "agent_id": "observability-agent",
                    "event_limit": request.event_limit,
                    "source_event_ids": [
                        event.event_id
                        for event in timing_events
                        if event.event_id is not None
                    ],
                },
                reviewer_decisions=[
                    {
                        "reviewer_agent_id": "inference-systems-engineer",
                        "status": (
                            "approved_with_notes"
                            if status == "ready"
                            else "needs_revision"
                        ),
                        "notes": (
                            "Voice timing readiness requires measured LiveKit, "
                            "OpenRouter, Kokoro, and barge-in stages from durable events."
                        ),
                    }
                ],
                revision_history=[
                    {
                        "actor": "observability-agent",
                        "note": (
                            "Measured or blocked LiveKit/OpenRouter/Kokoro voice timing "
                            "from durable runtime events."
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
                event_type="realtime_voice_timing_ledger_built",
                actor="observability-agent",
                payload={
                    "status": result.status,
                    "session_count": result.session_count,
                    "event_count": result.event_count,
                    "measured_stage_count": result.measured_stage_count,
                    "missing_stage_count": result.missing_stage_count,
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


def _stage_entries(
    sessions,
    events: list[RunEvent],
    *,
    target_session_id: UUID | None = None,
) -> list[RealtimeVoiceTimingStageEntry]:
    livekit_session = _livekit_session_event(
        sessions,
        events,
        target_session_id=target_session_id,
    )
    chain = _best_turn_chain(events)
    media_bridge = _media_bridge_event(
        events,
        target_session_id=target_session_id,
        livekit_session=livekit_session,
        chain=chain,
    )
    speech_start = (
        chain.speech_start
        if chain
        else _first(events, "voice_user_speech_started")
    )
    turn_commit = chain.turn_commit if chain else None
    turn_start = chain.turn_start if chain else None
    gemma_start = chain.gemma_start if chain else None
    first_text = chain.first_text if chain else None
    first_audio = chain.first_audio if chain else None
    cancellation_ack = chain.cancel_ack if chain else None
    cancelled = chain.cancelled if chain else None
    failed = _latest(events, "gemma_kokoro_voice_turn_failed")
    control_interrupt = _first_interrupt_control(events)

    stages = [
        _stage(
            "livekit_session_ready",
            "LiveKit room/session is ready",
            livekit_session,
            evidence_text=(
                "Found a LiveKit realtime session or voice-agent-ready event."
                if livekit_session
                else None
            ),
            missing="No provider-backed LiveKit session or voice-agent-ready event was found.",
        ),
        _stage(
            "livekit_audio_track_bridge",
            "LiveKit audio track is bridged to Rust VAD",
            media_bridge,
            evidence_text=(
                "Found voice_agent_media_bridge_ready from the OpenRouter/Kokoro "
                "participant after subscribing to a LiveKit audio track."
            ),
            missing=(
                "No voice_agent_media_bridge_ready event was found. The timing "
                "ledger needs proof that the backend participant subscribed to "
                "the creator audio track and connected it to the Rust VAD path."
            ),
        ),
        _stage(
            "speech_start_detected",
            "User speech start detected",
            speech_start,
            evidence_text="Found voice_user_speech_started from the Rust edge.",
            missing="No voice_user_speech_started event has been persisted.",
        ),
        _paired_stage(
            "end_of_turn_to_agent_turn",
            "End of user turn reaches the agent engine",
            turn_commit,
            turn_start,
            evidence_text=(
                "Found voice_user_turn_committed followed by the same "
                "OpenRouter/Kokoro turn entering the agent engine."
            ),
            missing=(
                "No correlated voice_user_turn_committed and "
                "OpenRouter/Kokoro turn-start event pair was found "
                "(legacy persisted event type: gemma_kokoro_voice_turn_started)."
            ),
        ),
        _paired_stage(
            "gemma_response_start",
            "OpenRouter response generation starts",
            turn_start,
            gemma_start,
            evidence_text=(
                "Found OpenRouter generation-start evidence for the same response "
                "(legacy persisted event type: gemma_generation_started)."
            ),
            missing=(
                "No correlated OpenRouter/Kokoro turn-start and generation-start "
                "event pair was found (legacy persisted event types: "
                "gemma_kokoro_voice_turn_started and gemma_generation_started)."
            ),
        ),
        _paired_stage(
            "first_text_delta",
            "First OpenRouter text delta arrives",
            gemma_start,
            first_text,
            evidence_text="Found assistant_text_delta for the same response.",
            missing=(
                "No correlated OpenRouter generation-start and assistant_text_delta "
                "event pair was found (legacy persisted generation event type: "
                "gemma_generation_started)."
            ),
        ),
        _paired_stage(
            "first_audio_out",
            "First Kokoro audio reaches LiveKit output",
            gemma_start,
            first_audio,
            evidence_text=(
                "Found assistant_audio_chunk_published for the same OpenRouter/Kokoro "
                "response."
            ),
            missing=(
                "No correlated OpenRouter generation-start and "
                "assistant_audio_chunk_published event pair was found "
                "(legacy persisted generation event type: gemma_generation_started)."
            ),
        ),
        _barge_in_stage(cancellation_ack, cancelled, control_interrupt),
    ]
    if failed is not None:
        stages.append(_voice_turn_failure_stage(failed))
    return stages


def _barge_in_stage(
    cancellation_ack: RunEvent | None,
    cancelled: RunEvent | None,
    control_interrupt: RunEvent | None,
) -> RealtimeVoiceTimingStageEntry:
    if cancellation_ack is not None and cancelled is not None:
        return _stage(
            "barge_in_to_audio_stop",
            "Barge-in stops OpenRouter/Kokoro/LiveKit output",
            cancelled,
            latency_ms=_ms_between(cancellation_ack, cancelled),
            evidence_text=(
                "Found voice_edge_cancellation_acknowledged and "
                "gemma_kokoro_voice_turn_cancelled."
            ),
            missing="",
            extra_event=cancellation_ack,
        )
    if cancellation_ack is not None or control_interrupt is not None:
        event = cancellation_ack or control_interrupt
        event_ids = [event.event_id] if event and event.event_id is not None else []
        return RealtimeVoiceTimingStageEntry(
            stage_id="barge_in_to_audio_stop",
            title="Barge-in stops OpenRouter/Kokoro/LiveKit output",
            status="partial",
            evidence=[
                "Found an interrupt or cancellation acknowledgement, but no durable voice-turn-cancelled event."
            ],
            missing_evidence=[
                "Persist gemma_kokoro_voice_turn_cancelled after OpenRouter is canceled, Kokoro buffers are cleared, and LiveKit output is stopped."
            ],
            event_ids=event_ids,
        )
    return RealtimeVoiceTimingStageEntry(
        stage_id="barge_in_to_audio_stop",
        title="Barge-in stops OpenRouter/Kokoro/LiveKit output",
        status="missing",
        missing_evidence=[
            "No interrupt/cancellation acknowledgement and voice-turn-cancelled event pair was found."
        ],
    )


def _voice_turn_failure_stage(failed: RunEvent) -> RealtimeVoiceTimingStageEntry:
    stage = _payload_str(failed.payload, "failure_stage") or "provider"
    reason = _payload_str(failed.payload, "failure_reason") or _payload_str(
        failed.payload,
        "reason",
    )
    detail = f"OpenRouter/Kokoro voice turn failed during {stage}."
    if reason:
        detail = f"{detail} {reason}"
    event_ids = [failed.event_id] if failed.event_id is not None else []
    return RealtimeVoiceTimingStageEntry(
        stage_id="voice_turn_failed",
        title="OpenRouter/Kokoro voice turn failed",
        status="failed",
        evidence=[detail],
        missing_evidence=[
            "Fix the OpenRouter/Kokoro provider route and rerun live provider smoke before treating this voice session as ready."
        ],
        event_ids=event_ids,
    )


def _stage(
    stage_id: str,
    title: str,
    event: RunEvent | None,
    *,
    latency_ms: float | None = None,
    evidence_text: str | None,
    missing: str,
    extra_event: RunEvent | None = None,
) -> RealtimeVoiceTimingStageEntry:
    if event is None:
        return RealtimeVoiceTimingStageEntry(
            stage_id=stage_id,
            title=title,
            status="missing",
            missing_evidence=[missing],
        )
    event_ids = [
        candidate.event_id
        for candidate in [extra_event, event]
        if candidate is not None and candidate.event_id is not None
    ]
    evidence = [evidence_text or f"Found {event.event_type}."]
    if latency_ms is not None:
        evidence.append(f"Measured latency: {latency_ms} ms.")
    return RealtimeVoiceTimingStageEntry(
        stage_id=stage_id,
        title=title,
        status="measured",
        latency_ms=latency_ms,
        evidence=evidence,
        event_ids=event_ids,
    )


def _paired_stage(
    stage_id: str,
    title: str,
    start: RunEvent | None,
    end: RunEvent | None,
    *,
    evidence_text: str,
    missing: str,
) -> RealtimeVoiceTimingStageEntry:
    event_ids = [
        event.event_id
        for event in [start, end]
        if event is not None and event.event_id is not None
    ]
    if start is not None and end is not None:
        latency_ms = _ms_between(start, end)
        evidence = [evidence_text]
        if latency_ms is not None:
            evidence.append(f"Measured latency: {latency_ms} ms.")
        return RealtimeVoiceTimingStageEntry(
            stage_id=stage_id,
            title=title,
            status="measured",
            latency_ms=latency_ms,
            evidence=evidence,
            event_ids=event_ids,
        )
    if start is not None or end is not None:
        return RealtimeVoiceTimingStageEntry(
            stage_id=stage_id,
            title=title,
            status="partial",
            evidence=["Found one side of the timing pair, but not both."],
            missing_evidence=[missing],
            event_ids=event_ids,
        )
    return RealtimeVoiceTimingStageEntry(
        stage_id=stage_id,
        title=title,
        status="missing",
        missing_evidence=[missing],
    )


def _best_turn_chain(events: list[RunEvent]) -> TurnTimingChain | None:
    turn_starts = [
        event for event in events if event.event_type == "gemma_kokoro_voice_turn_started"
    ]
    if not turn_starts:
        return None
    speech_starts = [
        event for event in events if event.event_type == "voice_user_speech_started"
    ]
    turn_commits = [
        event for event in events if event.event_type == "voice_user_turn_committed"
    ]
    chains = []
    for turn_start in turn_starts:
        turn_id = _payload_str(turn_start.payload, "turn_id")
        response_id = _payload_response_id(turn_start.payload)
        session_id = _event_session_id(turn_start)
        matching = _events_for_turn(
            events,
            turn_id=turn_id,
            response_id=response_id,
            realtime_session_id=session_id,
        )
        turn_commit = _first(matching, "voice_user_turn_committed")
        if turn_commit is None:
            turn_commit = _nearest_before(
                turn_commits,
                turn_start,
                realtime_session_id=session_id,
            )
        speech_start = _nearest_before(
            speech_starts,
            turn_commit or turn_start,
            realtime_session_id=session_id,
        )
        gemma_start = _first(matching, "gemma_generation_started")
        first_text = _first(matching, "assistant_text_delta")
        first_audio = _first(matching, "assistant_audio_chunk_published")
        cancel_ack = _first(matching, "voice_edge_cancellation_acknowledged")
        cancelled = _first(matching, "gemma_kokoro_voice_turn_cancelled")
        failed = _first(matching, "gemma_kokoro_voice_turn_failed")
        chain = TurnTimingChain(
            speech_start=speech_start,
            turn_commit=turn_commit,
            turn_start=turn_start,
            gemma_start=gemma_start,
            first_text=first_text,
            first_audio=first_audio,
            cancel_ack=cancel_ack,
            cancelled=cancelled,
            failed=failed,
        )
        chains.append(chain)
    return max(chains, key=_chain_score)


def _chain_score(chain: TurnTimingChain) -> tuple[int, int]:
    required = [
        chain.speech_start,
        chain.turn_commit,
        chain.turn_start,
        chain.gemma_start,
        chain.first_audio,
        chain.cancel_ack,
        chain.cancelled,
    ]
    optional = [chain.first_text]
    return (
        sum(event is not None for event in required),
        sum(event is not None for event in optional),
    )


def _turn_entries(events: list[RunEvent]) -> list[RealtimeVoiceTimingTurnEntry]:
    turn_starts = [
        event for event in events if event.event_type == "gemma_kokoro_voice_turn_started"
    ]
    speech_starts = [
        event for event in events if event.event_type == "voice_user_speech_started"
    ]
    turn_commits = [
        event for event in events if event.event_type == "voice_user_turn_committed"
    ]
    entries = []
    for turn_start in turn_starts:
        payload = turn_start.payload
        turn_id = _payload_str(payload, "turn_id")
        response_id = _payload_response_id(payload)
        session_id = _event_session_id(turn_start)
        matching = _events_for_turn(
            events,
            turn_id=turn_id,
            response_id=response_id,
            realtime_session_id=session_id,
        )
        turn_commit = _first(matching, "voice_user_turn_committed")
        if turn_commit is None:
            turn_commit = _nearest_before(
                turn_commits,
                turn_start,
                realtime_session_id=session_id,
            )
        gemma_start = _first(matching, "gemma_generation_started")
        first_text = _first(matching, "assistant_text_delta")
        first_audio = _first(matching, "assistant_audio_chunk_published")
        cancel_ack = _first(matching, "voice_edge_cancellation_acknowledged")
        cancelled = _first(matching, "gemma_kokoro_voice_turn_cancelled")
        failed = _first(matching, "gemma_kokoro_voice_turn_failed")
        speech_start = _nearest_before(
            speech_starts,
            turn_commit or turn_start,
            realtime_session_id=session_id,
        )
        entries.append(
            RealtimeVoiceTimingTurnEntry(
                turn_id=turn_id,
                response_id=response_id,
                realtime_session_id=session_id,
                speech_start_to_turn_commit_ms=_ms_between(speech_start, turn_commit),
                turn_commit_to_agent_turn_ms=_ms_between(turn_commit, turn_start),
                speech_start_to_turn_start_ms=_ms_between(speech_start, turn_start),
                turn_start_to_gemma_start_ms=_ms_between(turn_start, gemma_start),
                gemma_start_to_first_text_ms=_ms_between(gemma_start, first_text),
                gemma_start_to_first_audio_ms=_ms_between(gemma_start, first_audio),
                turn_start_to_first_audio_ms=_ms_between(turn_start, first_audio),
                barge_in_to_cancelled_ms=_ms_between(cancel_ack, cancelled),
                failure_stage=(
                    _payload_str(failed.payload, "failure_stage")
                    if failed is not None
                    else None
                ),
                failure_reason=(
                    _payload_str(failed.payload, "failure_reason")
                    or _payload_str(failed.payload, "reason")
                    if failed is not None
                    else None
                ),
                failed_at_ms=_ms_between(turn_start, failed),
                event_ids=[
                    event.event_id
                    for event in [
                        speech_start,
                        turn_commit,
                        turn_start,
                        gemma_start,
                        first_audio,
                        cancel_ack,
                        cancelled,
                        failed,
                    ]
                    if event is not None and event.event_id is not None
                ],
            )
        )
    return entries


def _events_for_turn(
    events: list[RunEvent],
    *,
    turn_id: str | None,
    response_id: str | None,
    realtime_session_id: UUID | None,
) -> list[RunEvent]:
    matching = []
    for event in events:
        event_session_id = _event_session_id(event)
        if (
            realtime_session_id is not None
            and event_session_id is not None
            and event_session_id != realtime_session_id
        ):
            continue
        if turn_id is not None and _payload_str(event.payload, "turn_id") == turn_id:
            matching.append(event)
            continue
        if response_id is not None and _payload_response_id(event.payload) == response_id:
            matching.append(event)
    return matching


def _target_livekit_session_id(sessions, events: list[RunEvent]) -> UUID | None:
    livekit_sessions = [
        session
        for session in sessions
        if getattr(session, "transport_framework", None) == "livekit"
    ]
    active_sessions = [
        session
        for session in livekit_sessions
        if getattr(session, "status", None) == RealtimeSessionStatus.ACTIVE
        or str(getattr(session, "status", "")) == RealtimeSessionStatus.ACTIVE.value
    ]
    session_candidates = active_sessions or livekit_sessions
    if session_candidates:
        return max(session_candidates, key=lambda session: session.created_at).realtime_session_id
    for event in reversed(events):
        if event.event_type == "realtime_session_created":
            transport = event.payload.get("transport")
            framework = None
            if isinstance(transport, dict):
                framework = transport.get("framework")
            framework = framework or event.payload.get("transport_framework")
            if framework == "livekit":
                session_id = _event_session_id(event)
                if session_id is not None:
                    return session_id
        if event.event_type == "gemma_kokoro_voice_agent_ready":
            session_id = _event_session_id(event)
            if session_id is not None:
                return session_id
    return None


def _session_scoped_timing_events(
    events: list[RunEvent],
    *,
    target_session_id: UUID | None,
) -> list[RunEvent]:
    if target_session_id is None:
        return events
    return [
        event
        for event in events
        if _event_session_id(event) == target_session_id
    ]


def _livekit_session_event(
    sessions,
    events: list[RunEvent],
    *,
    target_session_id: UUID | None = None,
) -> RunEvent | None:
    ready = _first_session_event(
        events,
        "gemma_kokoro_voice_agent_ready",
        target_session_id=target_session_id,
    )
    if ready is not None:
        return ready
    for event in events:
        if event.event_type != "realtime_session_created":
            continue
        if target_session_id is not None and _event_session_id(event) != target_session_id:
            continue
        payload = event.payload
        transport = payload.get("transport")
        framework = None
        if isinstance(transport, dict):
            framework = transport.get("framework")
        framework = framework or payload.get("transport_framework")
        if framework == "livekit":
            return event
    for session in sessions:
        if (
            target_session_id is not None
            and session.realtime_session_id != target_session_id
        ):
            continue
        if (
            session.transport_framework == "livekit"
            and session.status == RealtimeSessionStatus.ACTIVE
        ):
            return RunEvent(
                event_id=None,
                run_id=session.run_id,
                event_type="realtime_session_record",
                actor="realtime-conversation-host",
                payload={
                    "realtime_session_id": str(session.realtime_session_id),
                    "transport_framework": session.transport_framework,
                },
                created_at=session.created_at,
            )
    return None


def _media_bridge_event(
    events: list[RunEvent],
    *,
    target_session_id: UUID | None,
    livekit_session: RunEvent | None,
    chain: TurnTimingChain | None,
) -> RunEvent | None:
    media_events = [
        event for event in events if event.event_type == "voice_agent_media_bridge_ready"
    ]
    if not media_events:
        return None
    if target_session_id is None and chain and chain.turn_start is not None:
        target_session_id = _event_session_id(chain.turn_start)
    if target_session_id is None and livekit_session is not None:
        target_session_id = _event_session_id(livekit_session)
    proof_deadline = _media_bridge_proof_deadline(chain)
    for event in media_events:
        event_session_id = _event_session_id(event)
        if target_session_id is not None and event_session_id != target_session_id:
            continue
        if proof_deadline is not None and _event_time(event) > _event_time(proof_deadline):
            continue
        return event
    return None


def _media_bridge_proof_deadline(chain: TurnTimingChain | None) -> RunEvent | None:
    if chain is None:
        return None
    return chain.speech_start or chain.turn_commit or chain.turn_start


def _first(events: list[RunEvent], event_type: str) -> RunEvent | None:
    return next((event for event in events if event.event_type == event_type), None)


def _first_session_event(
    events: list[RunEvent],
    event_type: str,
    *,
    target_session_id: UUID | None,
) -> RunEvent | None:
    return next(
        (
            event
            for event in events
            if event.event_type == event_type
            and (
                target_session_id is None
                or _event_session_id(event) == target_session_id
            )
        ),
        None,
    )


def _latest(events: list[RunEvent], event_type: str) -> RunEvent | None:
    matching = [event for event in events if event.event_type == event_type]
    return matching[-1] if matching else None


def _first_any(events: list[RunEvent], event_types: set[str]) -> RunEvent | None:
    return next((event for event in events if event.event_type in event_types), None)


def _first_interrupt_control(events: list[RunEvent]) -> RunEvent | None:
    return next(
        (
            event
            for event in events
            if event.event_type == "realtime_session_control_recorded"
            and event.payload.get("action") == "interrupt"
        ),
        None,
    )


def _nearest_before(
    events: list[RunEvent],
    target: RunEvent,
    *,
    realtime_session_id: UUID | None,
) -> RunEvent | None:
    candidates = [
        event
        for event in events
        if _event_time(event) <= _event_time(target)
        and (
            realtime_session_id is None
            or _payload_uuid(event.payload, "realtime_session_id")
            in {None, realtime_session_id}
        )
    ]
    return candidates[-1] if candidates else None


def _nearest_response_event(
    events: list[RunEvent],
    event_type: str,
    response_id: str,
) -> RunEvent | None:
    return next(
        (
            event
            for event in events
            if event.event_type == event_type
            and _payload_response_id(event.payload) == response_id
        ),
        None,
    )


def _payload_response_id(payload: dict) -> str | None:
    direct = _payload_str(payload, "response_id")
    if direct:
        return direct
    interrupted = _payload_str(payload, "interrupted_response_id")
    if interrupted:
        return interrupted
    edge_event = payload.get("voice_edge_event")
    if isinstance(edge_event, dict):
        value = edge_event.get("response_id")
        return str(value) if value is not None else None
    cancellation = payload.get("cancellation")
    if isinstance(cancellation, dict) and cancellation.get("response_id") is not None:
        return str(cancellation["response_id"])
    return None


def _event_session_id(event: RunEvent) -> UUID | None:
    return _payload_uuid(event.payload, "realtime_session_id")


def _payload_str(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    return str(value) if value is not None else None


def _payload_uuid(payload: dict, key: str) -> UUID | None:
    value = payload.get(key)
    if value is None:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _event_time(event: RunEvent) -> datetime:
    value = event.payload.get("agent_created_at")
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return event.created_at


def _ms_between(start: RunEvent | None, end: RunEvent | None) -> float | None:
    if start is None or end is None:
        return None
    delta = (_event_time(end) - _event_time(start)).total_seconds() * 1000
    return round(max(0.0, delta), 3)


def _ledger_status(sessions, stages: list[RealtimeVoiceTimingStageEntry]) -> str:
    if not sessions:
        return "blocked"
    if any(stage.status == "failed" for stage in stages):
        return "failed"
    required = {
        "livekit_session_ready",
        "livekit_audio_track_bridge",
        "speech_start_detected",
        "end_of_turn_to_agent_turn",
        "gemma_response_start",
        "first_audio_out",
        "barge_in_to_audio_stop",
    }
    statuses = {stage.stage_id: stage.status for stage in stages}
    if all(statuses.get(stage_id) == "measured" for stage_id in required):
        return "ready"
    if statuses.get("livekit_session_ready") == "measured":
        return "needs_more_evidence"
    return "blocked"


def _recommended_next_actions(
    stages: list[RealtimeVoiceTimingStageEntry],
    sessions,
) -> list[str]:
    actions = []
    if not sessions:
        actions.append("Create a provider-backed OpenRouter/Kokoro LiveKit session.")
    for stage in stages:
        if stage.status == "measured":
            continue
        actions.extend(stage.missing_evidence)
    if not actions:
        actions.append("Use the timing ledger as the baseline before replacing deterministic VAD with Silero.")
    return actions
