from uuid import UUID

from all_about_llms.contracts import (
    AgentTaskStatus,
    ArtifactRecord,
    ArtifactType,
    FeedbackStatus,
    RealtimeDialogueFollowupEntry,
    RealtimeDialogueControlEntry,
    RealtimeDialogueLedgerRequest,
    RealtimeDialogueLedgerResult,
    RealtimeDialogueSessionEntry,
    RealtimeDialogueSpokenResponseEntry,
    RealtimeDialogueTurnEntry,
    RealtimeSessionStatus,
    RunEvent,
)


class RealtimeDialogueLedgerError(RuntimeError):
    """Base error for realtime dialogue ledger generation."""


class RealtimeDialogueLedgerRunNotFoundError(RealtimeDialogueLedgerError):
    """Raised when a run cannot be found for realtime dialogue work."""


class RealtimeDialogueLedgerWorkflow:
    """Build a durable ledger for voice/text dialogue continuity."""

    def __init__(self, store):
        self._store = store

    async def build(
        self, run_id: UUID, request: RealtimeDialogueLedgerRequest
    ) -> RealtimeDialogueLedgerResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise RealtimeDialogueLedgerRunNotFoundError(f"Run not found: {run_id}")

        sessions = await self._store.list_realtime_sessions(run_id)
        turns = await self._store.list_conversation_turns(run_id)
        messages = await self._store.list_agent_messages(run_id, limit=500)
        feedback_items = await self._store.list_feedback(run_id)
        events = await self._store.list_events(run_id, limit=request.event_limit)

        followup_entries = _followup_entries(messages)
        pending_followup_task_ids = [
            entry.message_id
            for entry in followup_entries
            if entry.status
            in {
                AgentTaskStatus.ACCEPTED,
                AgentTaskStatus.CLAIMED,
                AgentTaskStatus.IN_PROGRESS,
                AgentTaskStatus.WAITING_FOR_HUMAN,
            }
        ]
        response_turn_ids = _response_turn_ids(turns)
        response_source_turn_ids = _response_source_turn_ids(turns)
        followup_source_turn_ids = {
            entry.source_turn_id for entry in followup_entries if entry.source_turn_id
        }
        user_turns = [turn for turn in turns if turn.speaker == "user"]
        assistant_turns = [turn for turn in turns if turn.speaker == "assistant"]
        voice_turns = [turn for turn in turns if turn.modality == "voice"]
        interrupted_turns = [
            turn for turn in turns if _truthy(turn.metadata.get("interrupted"))
        ]
        unanswered_user_turn_ids = [
            turn.turn_id
            for turn in user_turns
            if turn.turn_id not in response_source_turn_ids
            and turn.turn_id not in followup_source_turn_ids
        ]
        unacknowledged_interruption_turn_ids = [
            turn.turn_id
            for turn in interrupted_turns
            if turn.speaker == "user" and turn.turn_id not in response_source_turn_ids
        ]
        open_feedback_count = sum(
            1 for feedback in feedback_items if feedback.status == FeedbackStatus.OPEN
        )
        control_entries = _control_entries(events, turns)
        spoken_response_entries = _spoken_response_entries(events)
        unresolved_control_event_ids = [
            entry.event_id
            for entry in control_entries
            if entry.action.value == "interrupt"
            and entry.resolved_by_turn_id is None
            and entry.event_id is not None
        ]

        turn_entries = [
            _turn_entry(
                turn,
                include_transcript_preview=request.include_transcript_preview,
                response_turn_ids=response_turn_ids,
            )
            for turn in turns[-request.turn_limit :]
        ]
        session_entries = [
            _session_entry(session, turns)
            for session in sessions
        ]
        recommended_next_actions = _recommended_next_actions(
            sessions=sessions,
            turns=turns,
            unanswered_user_turn_ids=unanswered_user_turn_ids,
            unacknowledged_interruption_turn_ids=unacknowledged_interruption_turn_ids,
            pending_followup_task_ids=pending_followup_task_ids,
            unresolved_control_event_ids=unresolved_control_event_ids,
            open_feedback_count=open_feedback_count,
        )
        status = _ledger_status(
            sessions=sessions,
            turns=turns,
            unanswered_user_turn_ids=unanswered_user_turn_ids,
            unacknowledged_interruption_turn_ids=unacknowledged_interruption_turn_ids,
            pending_followup_task_ids=pending_followup_task_ids,
            unresolved_control_event_ids=unresolved_control_event_ids,
            open_feedback_count=open_feedback_count,
        )

        result = RealtimeDialogueLedgerResult(
            run_id=run_id,
            status=status,
            session_count=len(sessions),
            active_session_count=sum(
                1 for session in sessions if session.status == RealtimeSessionStatus.ACTIVE
            ),
            turn_count=len(turns),
            user_turn_count=len(user_turns),
            assistant_turn_count=len(assistant_turns),
            voice_turn_count=len(voice_turns),
            interrupted_turn_count=len(interrupted_turns),
            assistant_response_turn_count=len(response_source_turn_ids),
            unanswered_user_turn_ids=unanswered_user_turn_ids,
            unacknowledged_interruption_turn_ids=unacknowledged_interruption_turn_ids,
            pending_followup_task_ids=pending_followup_task_ids,
            open_feedback_count=open_feedback_count,
            control_event_count=len(control_entries),
            unresolved_control_event_ids=unresolved_control_event_ids,
            control_action_counts=_value_counts(
                entry.action.value for entry in control_entries
            ),
            spoken_response_plan_count=len(spoken_response_entries),
            sessions=session_entries,
            turns=turn_entries,
            followup_tasks=followup_entries,
            control_events=control_entries,
            spoken_responses=spoken_response_entries,
            recommended_next_actions=recommended_next_actions,
            summary=(
                f"Realtime dialogue ledger is {status}: {len(sessions)} session(s), "
                f"{len(turns)} turn(s), {len(interrupted_turns)} interruption(s), "
                f"{len(pending_followup_task_ids)} pending host follow-up(s), "
                f"{len(unresolved_control_event_ids)} unresolved control event(s), "
                f"and {len(spoken_response_entries)} spoken response plan(s)."
            ),
        )

        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.REALTIME_DIALOGUE_LEDGER,
                title="Realtime dialogue ledger",
                uri=f"artifact://runs/{run_id}/realtime-dialogue-ledger",
                content={
                    **result.model_dump(
                        mode="json", exclude={"ledger_artifact_id", "event_id"}
                    ),
                    "event_type_counts": _event_counts(events),
                },
                provenance={
                    "workflow": "realtime_dialogue_ledger_v1",
                    "agent_id": "realtime-conversation-host",
                    "event_limit": request.event_limit,
                    "turn_limit": request.turn_limit,
                    "source_event_ids": [
                        event.event_id for event in events if event.event_id is not None
                    ],
                },
                reviewer_decisions=[
                    {
                        "reviewer_agent_id": "realtime-conversation-host",
                        "status": "approved_with_notes"
                        if status != "blocked"
                        else "needs_revision",
                        "notes": "Dialogue ledger preserves turn-taking, interruption, and follow-up state.",
                    }
                ],
                revision_history=[
                    {
                        "actor": "realtime-conversation-host",
                        "note": "Built a durable dialogue continuity ledger from sessions, turns, events, feedback, and host follow-up tasks.",
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
                event_type="realtime_dialogue_ledger_built",
                actor="realtime-conversation-host",
                payload={
                    "status": result.status,
                    "session_count": result.session_count,
                    "turn_count": result.turn_count,
                    "voice_turn_count": result.voice_turn_count,
                    "interrupted_turn_count": result.interrupted_turn_count,
                    "unanswered_user_turn_count": len(result.unanswered_user_turn_ids),
                    "unacknowledged_interruption_count": len(
                        result.unacknowledged_interruption_turn_ids
                    ),
                    "pending_followup_task_count": len(
                        result.pending_followup_task_ids
                    ),
                    "control_event_count": result.control_event_count,
                    "spoken_response_plan_count": (
                        result.spoken_response_plan_count
                    ),
                    "unresolved_control_event_count": len(
                        result.unresolved_control_event_ids
                    ),
                    "open_feedback_count": result.open_feedback_count,
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


def _turn_entry(
    turn,
    *,
    include_transcript_preview: bool,
    response_turn_ids: dict[UUID, UUID],
) -> RealtimeDialogueTurnEntry:
    return RealtimeDialogueTurnEntry(
        turn_id=turn.turn_id,
        speaker=turn.speaker,
        modality=turn.modality,
        realtime_session_id=_uuid_or_none(turn.metadata.get("realtime_session_id")),
        transcript_preview=turn.transcript[:240] if include_transcript_preview else None,
        interrupted=_truthy(turn.metadata.get("interrupted")),
        has_audio=bool(turn.audio_uri),
        responds_to_turn_id=_uuid_or_none(turn.metadata.get("responds_to_turn_id")),
        response_turn_id=response_turn_ids.get(turn.turn_id),
        created_at=turn.created_at,
        metadata_keys=sorted(turn.metadata.keys()),
    )


def _session_entry(session, turns) -> RealtimeDialogueSessionEntry:
    session_turns = [
        turn
        for turn in turns
        if _uuid_or_none(turn.metadata.get("realtime_session_id"))
        == session.realtime_session_id
    ]
    last_turn_at = max((turn.created_at for turn in session_turns), default=None)
    return RealtimeDialogueSessionEntry(
        realtime_session_id=session.realtime_session_id,
        provider=session.provider,
        status=session.status,
        voice=session.voice,
        audio_mode=session.audio_mode,
        has_client_secret=session.has_client_secret,
        has_websocket_url=session.has_websocket_url,
        transport_framework=session.transport_framework,
        room_name=session.room_name,
        participant_identity=session.participant_identity,
        agent_participant_identity=session.agent_participant_identity,
        has_transport_token=session.has_transport_token,
        context_window_turns=session.context_window_turns,
        summarize_after_turns=session.summarize_after_turns,
        turn_count=len(session_turns),
        voice_turn_count=sum(1 for turn in session_turns if turn.modality == "voice"),
        interrupted_turn_count=sum(
            1 for turn in session_turns if _truthy(turn.metadata.get("interrupted"))
        ),
        assistant_response_turn_count=sum(
            1
            for turn in session_turns
            if turn.speaker == "assistant"
            and _uuid_or_none(turn.metadata.get("responds_to_turn_id"))
        ),
        last_turn_at=last_turn_at,
    )


def _followup_entries(messages) -> list[RealtimeDialogueFollowupEntry]:
    entries = []
    for message in messages:
        if (
            message.payload.get("workflow") != "realtime_turn_followup_v1"
            and message.payload.get("workflow") != "realtime_session_control_v1"
            and message.task_type != "summarize_realtime_turn_context"
            and message.task_type != "handle_realtime_session_control"
        ):
            continue
        entries.append(
            RealtimeDialogueFollowupEntry(
                message_id=message.message_id,
                sender_agent_id=message.sender_agent_id,
                recipient_agent_id=message.recipient_agent_id,
                task_type=message.task_type,
                status=message.status,
                requires_human_feedback=message.requires_human_feedback,
                source_turn_id=_uuid_or_none(message.payload.get("source_turn_id")),
                response_turn_id=_uuid_or_none(message.payload.get("response_turn_id")),
                interrupted=_truthy(message.payload.get("interrupted")),
            )
        )
    return entries


def _control_entries(
    events: list[RunEvent], turns
) -> list[RealtimeDialogueControlEntry]:
    resolved_turn_by_event_id = {
        int(event_id): turn.turn_id
        for turn in turns
        for event_id in [turn.metadata.get("interruption_control_event_id")]
        if _int_or_none(event_id) is not None
    }
    entries = []
    for event in events:
        if event.event_type != "realtime_session_control_recorded":
            continue
        payload = event.payload or {}
        session_id = _uuid_or_none(payload.get("realtime_session_id"))
        if session_id is None:
            continue
        action = payload.get("action") or "interrupt"
        try:
            entry = RealtimeDialogueControlEntry(
                event_id=event.event_id,
                realtime_session_id=session_id,
                action=action,
                reason=payload.get("reason"),
                followup_task_message_id=_uuid_or_none(
                    payload.get("followup_task_message_id")
                ),
                resolved_by_turn_id=resolved_turn_by_event_id.get(
                    event.event_id or -1
                ),
                created_at=event.created_at,
            )
        except ValueError:
            continue
        entries.append(entry)
    return entries


def _spoken_response_entries(
    events: list[RunEvent],
) -> list[RealtimeDialogueSpokenResponseEntry]:
    entries = []
    for event in events:
        if event.event_type != "realtime_spoken_response_planned":
            continue
        payload = event.payload or {}
        session_id = _uuid_or_none(payload.get("realtime_session_id"))
        source_turn_id = _uuid_or_none(payload.get("source_turn_id"))
        if session_id is None or source_turn_id is None:
            continue
        entries.append(
            RealtimeDialogueSpokenResponseEntry(
                event_id=event.event_id,
                realtime_session_id=session_id,
                provider=str(payload.get("provider") or "unknown"),
                voice=payload.get("voice"),
                output_channel=str(payload.get("output_channel") or "unknown"),
                source_turn_id=source_turn_id,
                response_turn_id=_uuid_or_none(payload.get("response_turn_id")),
                text_preview=str(payload.get("text") or "")[:240] or None,
                interrupt_previous=_truthy(payload.get("interrupt_previous")),
                created_at=event.created_at,
            )
        )
    return entries


def _response_source_turn_ids(turns) -> set[UUID]:
    return {
        source_turn_id
        for turn in turns
        if turn.speaker == "assistant"
        for source_turn_id in [_uuid_or_none(turn.metadata.get("responds_to_turn_id"))]
        if source_turn_id is not None
    }


def _response_turn_ids(turns) -> dict[UUID, UUID]:
    return {
        source_turn_id: turn.turn_id
        for turn in turns
        if turn.speaker == "assistant"
        for source_turn_id in [_uuid_or_none(turn.metadata.get("responds_to_turn_id"))]
        if source_turn_id is not None
    }


def _ledger_status(
    *,
    sessions,
    turns,
    unanswered_user_turn_ids: list[UUID],
    unacknowledged_interruption_turn_ids: list[UUID],
    pending_followup_task_ids: list[UUID],
    unresolved_control_event_ids: list[int],
    open_feedback_count: int,
) -> str:
    if unacknowledged_interruption_turn_ids:
        return "blocked"
    if (
        not sessions
        or not turns
        or unanswered_user_turn_ids
        or pending_followup_task_ids
        or unresolved_control_event_ids
        or open_feedback_count
    ):
        return "needs_attention"
    return "ready"


def _recommended_next_actions(
    *,
    sessions,
    turns,
    unanswered_user_turn_ids: list[UUID],
    unacknowledged_interruption_turn_ids: list[UUID],
    pending_followup_task_ids: list[UUID],
    unresolved_control_event_ids: list[int],
    open_feedback_count: int,
) -> list[str]:
    actions: list[str] = []
    if not sessions:
        actions.append("Start a realtime session before relying on voice dialogue.")
    if not turns:
        actions.append("Record at least one user turn and one assistant reply.")
    if unanswered_user_turn_ids:
        actions.append("Acknowledge or route unanswered user turns before continuing.")
    if unacknowledged_interruption_turn_ids:
        actions.append("Resolve interrupted speech with an explicit resume or stop action.")
    if pending_followup_task_ids:
        actions.append("Run the Realtime Conversation Host worker on pending follow-up tasks.")
    if unresolved_control_event_ids:
        actions.append("Resolve pending realtime control events with a resumed or routed voice turn.")
    if open_feedback_count:
        actions.append("Resolve open feedback gates before treating the dialogue as approved.")
    if not actions:
        actions.append("Dialogue continuity is ready for the next natural turn.")
    return actions


def _event_counts(events: list[RunEvent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        counts[event.event_type] = counts.get(event.event_type, 0) + 1
    return counts


def _value_counts(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _int_or_none(value) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _uuid_or_none(value) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if value is None:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).lower() in {"1", "true", "yes", "y"}
