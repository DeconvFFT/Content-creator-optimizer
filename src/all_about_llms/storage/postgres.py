from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from all_about_llms.config import Settings
from all_about_llms.contracts import (
    AgentMessage,
    AgentMemory,
    AgentTaskStatus,
    ArtifactRecord,
    ClaimRecord,
    ConversationTurn,
    FeedbackItem,
    FeedbackStatus,
    GuardrailAuditRecord,
    GuardrailAuditStatus,
    RealtimeSessionRecord,
    RealtimeSessionStatus,
    RunCheckpoint,
    RunEvent,
    RunState,
    RunStatus,
    SourceRecord,
    WorkerProfile,
    WorkerProfileExecutionMode,
    WorkerProfileStatus,
)
from all_about_llms.orchestration.a2a_trace import (
    build_handoff_trace_entry,
    ensure_message_accepted_trace,
)


class PostgresStore:
    """Postgres-backed durable store for runs, events, and feedback.

    This class intentionally has no SQLite or file fallback. Local development
    should run Postgres with the provided pgvector Docker Compose service.
    """

    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

    @classmethod
    async def from_settings(cls, settings: Settings) -> "PostgresStore":
        pool = AsyncConnectionPool(
            conninfo=settings.database_url,
            min_size=settings.postgres_pool_min_size,
            max_size=settings.postgres_pool_max_size,
            kwargs={"row_factory": dict_row},
            open=False,
        )
        await pool.open()
        return cls(pool)

    async def close(self) -> None:
        await self._pool.close()

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[Any]:
        async with self._pool.connection() as conn:
            yield conn

    async def create_run(self, run: RunState) -> RunState:
        async with self.connection() as conn:
            await conn.execute(
                """
                insert into runs (
                    run_id, goal, status, conversation_state, active_agents,
                    source_record_ids, artifact_ids, feedback_item_ids,
                    created_at, updated_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    run.run_id,
                    run.goal,
                    run.status.value,
                    Jsonb(run.conversation_state),
                    run.active_agents,
                    run.source_record_ids,
                    run.artifact_ids,
                    run.feedback_item_ids,
                    run.created_at,
                    run.updated_at,
                ),
            )
        return run

    async def get_run(self, run_id: UUID) -> RunState | None:
        async with self.connection() as conn:
            row = await (
                await conn.execute("select * from runs where run_id = %s", (run_id,))
            ).fetchone()
        if row is None:
            return None
        return RunState(
            run_id=row["run_id"],
            goal=row["goal"],
            status=RunStatus(row["status"]),
            conversation_state=row["conversation_state"],
            active_agents=row["active_agents"],
            source_record_ids=row["source_record_ids"],
            artifact_ids=row["artifact_ids"],
            feedback_item_ids=row["feedback_item_ids"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def update_run_status(self, run_id: UUID, status: RunStatus) -> None:
        async with self.connection() as conn:
            await conn.execute(
                """
                update runs
                set status = %s, updated_at = now()
                where run_id = %s
                """,
                (status.value, run_id),
            )

    async def record_conversation_turn(
        self, turn: ConversationTurn
    ) -> ConversationTurn:
        async with self.connection() as conn:
            await conn.execute(
                """
                insert into conversation_turns (
                    turn_id, run_id, speaker, modality, transcript,
                    audio_uri, metadata, created_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    turn.turn_id,
                    turn.run_id,
                    turn.speaker,
                    turn.modality,
                    turn.transcript,
                    turn.audio_uri,
                    Jsonb(turn.metadata),
                    turn.created_at,
                ),
            )
        return turn

    async def update_conversation_turn(
        self, turn: ConversationTurn
    ) -> ConversationTurn | None:
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    """
                    update conversation_turns
                    set transcript = %s, audio_uri = %s, metadata = %s
                    where turn_id = %s and run_id = %s
                    returning *
                    """,
                    (
                        turn.transcript,
                        turn.audio_uri,
                        Jsonb(turn.metadata),
                        turn.turn_id,
                        turn.run_id,
                    ),
                )
            ).fetchone()
        return _conversation_turn_from_row(row) if row is not None else None

    async def promote_voice_user_transcript_if_pending(
        self,
        turn: ConversationTurn,
        *,
        voice_turn_id: str,
    ) -> ConversationTurn | None:
        if not voice_turn_id or turn.speaker != "user":
            return None
        transcript = turn.transcript.strip()
        if not transcript or transcript == "Live audio turn committed; transcript pending.":
            return None
        lock_key = f"voice-agent-turn:{turn.run_id}:user:{voice_turn_id}:"
        async with self.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    "select pg_advisory_xact_lock(hashtext(%s))",
                    (lock_key,),
                )
                row = await (
                    await conn.execute(
                        """
                        select * from conversation_turns
                        where run_id = %s
                          and speaker = 'user'
                          and metadata->>'voice_agent_turn_id' = %s
                        order by created_at desc
                        limit 1
                        for update
                        """,
                        (turn.run_id, voice_turn_id),
                    )
                ).fetchone()
                if row is None:
                    return None
                existing = _conversation_turn_from_row(row)
                if existing.metadata.get("transcript_status") == "final":
                    return None
                merged_metadata = dict(existing.metadata)
                merged_metadata.update(
                    {
                        key: value
                        for key, value in turn.metadata.items()
                        if value is not None
                    }
                )
                promoted_event_id = turn.metadata.get("voice_agent_event_id")
                merged_metadata.update(
                    {
                        "transcript_status": "final",
                        "transcript_promoted_from_pending": True,
                        "transcript_promoted_event_id": promoted_event_id,
                        "transcript_promoted_at": datetime.now(
                            timezone.utc
                        ).isoformat(),
                        "transcript_source": "voice_user_turn_committed",
                    }
                )
                updated = await (
                    await conn.execute(
                        """
                        update conversation_turns
                        set transcript = %s, audio_uri = %s, metadata = %s
                        where turn_id = %s and run_id = %s
                        returning *
                        """,
                        (
                            transcript,
                            turn.audio_uri or existing.audio_uri,
                            Jsonb(merged_metadata),
                            existing.turn_id,
                            turn.run_id,
                        ),
                    )
                ).fetchone()
        return _conversation_turn_from_row(updated) if updated is not None else None

    async def list_conversation_turns(
        self, run_id: UUID, limit: int = 100
    ) -> list[ConversationTurn]:
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    select * from conversation_turns
                    where run_id = %s
                    order by created_at asc
                    limit %s
                    """,
                    (run_id, limit),
                )
            ).fetchall()
        return [_conversation_turn_from_row(row) for row in rows]

    async def list_recent_conversation_turns(
        self, run_id: UUID, limit: int = 100
    ) -> list[ConversationTurn]:
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    select * from conversation_turns
                    where run_id = %s
                    order by created_at desc
                    limit %s
                    """,
                    (run_id, limit),
                )
            ).fetchall()
        return [_conversation_turn_from_row(row) for row in rows]

    async def find_voice_agent_conversation_turn(
        self,
        run_id: UUID,
        *,
        speaker: str,
        voice_turn_id: str | None = None,
        response_id: str | None = None,
    ) -> ConversationTurn | None:
        if not voice_turn_id and not response_id:
            return None
        conditions = ["run_id = %s", "speaker = %s"]
        params: list[object] = [run_id, speaker]
        id_conditions = []
        if voice_turn_id:
            id_conditions.append("metadata->>'voice_agent_turn_id' = %s")
            params.append(voice_turn_id)
        if response_id:
            id_conditions.append("metadata->>'voice_agent_response_id' = %s")
            params.append(response_id)
        conditions.append("(" + " or ".join(id_conditions) + ")")
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    f"""
                    select * from conversation_turns
                    where {' and '.join(conditions)}
                    order by created_at desc
                    limit 1
                    """,
                    tuple(params),
                )
            ).fetchone()
        return _conversation_turn_from_row(row) if row is not None else None

    async def record_voice_agent_conversation_turn_if_absent(
        self,
        turn: ConversationTurn,
        *,
        voice_turn_id: str | None = None,
        response_id: str | None = None,
    ) -> ConversationTurn | None:
        if not voice_turn_id and not response_id:
            return None
        conditions = ["run_id = %s", "speaker = %s"]
        lookup_params: list[object] = [turn.run_id, turn.speaker]
        id_conditions = []
        if voice_turn_id:
            id_conditions.append("metadata->>'voice_agent_turn_id' = %s")
            lookup_params.append(voice_turn_id)
        if response_id:
            id_conditions.append("metadata->>'voice_agent_response_id' = %s")
            lookup_params.append(response_id)
        conditions.append("(" + " or ".join(id_conditions) + ")")
        lock_key = (
            f"voice-agent-turn:{turn.run_id}:{turn.speaker}:"
            f"{voice_turn_id or ''}:{response_id or ''}"
        )
        async with self.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    "select pg_advisory_xact_lock(hashtext(%s))",
                    (lock_key,),
                )
                existing = await (
                    await conn.execute(
                        f"""
                        select * from conversation_turns
                        where {' and '.join(conditions)}
                        order by created_at desc
                        limit 1
                        """,
                        tuple(lookup_params),
                    )
                ).fetchone()
                if existing is not None:
                    return None
                row = await (
                    await conn.execute(
                        """
                        insert into conversation_turns (
                            turn_id, run_id, speaker, modality, transcript,
                            audio_uri, metadata, created_at
                        )
                        values (%s, %s, %s, %s, %s, %s, %s, %s)
                        on conflict do nothing
                        returning *
                        """,
                        (
                            turn.turn_id,
                            turn.run_id,
                            turn.speaker,
                            turn.modality,
                            turn.transcript,
                            turn.audio_uri,
                            Jsonb(turn.metadata),
                            turn.created_at,
                        ),
                    )
                ).fetchone()
        if row is not None:
            return _conversation_turn_from_row(row)
        return None

    async def record_realtime_session(
        self, session: RealtimeSessionRecord
    ) -> RealtimeSessionRecord:
        stored_metadata = _realtime_session_metadata(session)
        async with self.connection() as conn:
            await conn.execute(
                """
                insert into realtime_sessions (
                    realtime_session_id, run_id, provider, provider_session_id,
                    voice, audio_mode, instructions, has_client_secret,
                    has_websocket_url, expires_at_unix, status, metadata,
                    created_at, updated_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session.realtime_session_id,
                    session.run_id,
                    session.provider,
                    session.provider_session_id,
                    session.voice,
                    session.audio_mode,
                    session.instructions,
                    session.has_client_secret,
                    session.has_websocket_url,
                    session.expires_at_unix,
                    session.status.value,
                    Jsonb(stored_metadata),
                    session.created_at,
                    session.updated_at,
                ),
            )
        return session.model_copy(update={"metadata": stored_metadata})

    async def get_realtime_session(
        self, realtime_session_id: UUID
    ) -> RealtimeSessionRecord | None:
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    """
                    select * from realtime_sessions
                    where realtime_session_id = %s
                    """,
                    (realtime_session_id,),
                )
            ).fetchone()
        if row is None:
            return None
        return _realtime_session_from_row(row)

    async def list_realtime_sessions(
        self, run_id: UUID
    ) -> list[RealtimeSessionRecord]:
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    select * from realtime_sessions
                    where run_id = %s
                    order by created_at asc
                    """,
                    (run_id,),
                )
            ).fetchall()
        return [_realtime_session_from_row(row) for row in rows]

    async def update_realtime_session_status(
        self,
        realtime_session_id: UUID,
        status: RealtimeSessionStatus,
    ) -> RealtimeSessionRecord | None:
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    """
                    update realtime_sessions
                    set status = %s, updated_at = now()
                    where realtime_session_id = %s
                    returning *
                    """,
                    (status.value, realtime_session_id),
                )
            ).fetchone()
        if row is None:
            return None
        return _realtime_session_from_row(row)

    async def append_event(self, event: RunEvent) -> RunEvent:
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    """
                    insert into run_events (run_id, event_type, actor, payload, created_at)
                    values (%s, %s, %s, %s, %s)
                    returning event_id
                    """,
                    (
                        event.run_id,
                        event.event_type,
                        event.actor,
                        Jsonb(event.payload),
                        event.created_at,
                    ),
                )
            ).fetchone()
        event.event_id = row["event_id"]
        return event

    async def append_event_if_absent(
        self,
        event: RunEvent,
        *,
        idempotency_key: str,
    ) -> RunEvent | None:
        if not idempotency_key.strip():
            raise ValueError("idempotency_key is required")
        payload = dict(event.payload)
        payload["event_idempotency_key"] = idempotency_key
        async with self.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    "select pg_advisory_xact_lock(hashtext(%s)::bigint)",
                    (f"run_event:{idempotency_key}",),
                )
                existing = await (
                    await conn.execute(
                        """
                        select * from run_events
                        where run_id = %s
                          and event_type = %s
                          and payload->>'event_idempotency_key' = %s
                        order by event_id asc
                        limit 1
                        """,
                        (event.run_id, event.event_type, idempotency_key),
                    )
                ).fetchone()
                if existing is not None:
                    return _run_event_from_row(existing)
                row = await (
                    await conn.execute(
                        """
                        insert into run_events (
                            run_id, event_type, actor, payload, created_at
                        )
                        values (%s, %s, %s, %s, %s)
                        returning *
                        """,
                        (
                            event.run_id,
                            event.event_type,
                            event.actor,
                            Jsonb(payload),
                            event.created_at,
                        ),
                    )
                ).fetchone()
        return _run_event_from_row(row)

    async def find_event_by_voice_agent_event_uid(
        self,
        run_id: UUID,
        event_type: str,
        voice_agent_event_uid: str,
    ) -> RunEvent | None:
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    """
                    select * from run_events
                    where run_id = %s
                      and event_type = %s
                      and payload->>'voice_agent_event_uid' = %s
                    order by event_id desc
                    limit 1
                    """,
                    (run_id, event_type, voice_agent_event_uid),
                )
            ).fetchone()
        if row is None:
            return None
        return RunEvent(
            event_id=row["event_id"],
            run_id=row["run_id"],
            event_type=row["event_type"],
            actor=row["actor"],
            payload=row["payload"],
            created_at=row["created_at"],
        )

    async def list_events(
        self,
        run_id: UUID,
        limit: int = 100,
        after_event_id: int | None = None,
        latest: bool = False,
    ) -> list[RunEvent]:
        params: list[Any] = [run_id]
        cursor_clause = ""
        if after_event_id is not None:
            cursor_clause = "and event_id > %s"
            params.append(after_event_id)
        params.append(limit)
        order_clause = (
            "order by event_id desc" if latest and after_event_id is None else "order by event_id asc"
        )
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    f"""
                    select * from run_events
                    where run_id = %s
                    {cursor_clause}
                    {order_clause}
                    limit %s
                    """,
                    params,
                )
            ).fetchall()
        if latest and after_event_id is None:
            rows = list(reversed(rows))
        return [
            RunEvent(
                event_id=row["event_id"],
                run_id=row["run_id"],
                event_type=row["event_type"],
                actor=row["actor"],
                payload=row["payload"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def list_events_by_type(
        self,
        run_id: UUID,
        event_type: str,
        limit: int = 100,
        latest: bool = False,
    ) -> list[RunEvent]:
        order_clause = "order by event_id desc" if latest else "order by event_id asc"
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    f"""
                    select * from run_events
                    where run_id = %s and event_type = %s
                    {order_clause}
                    limit %s
                    """,
                    (run_id, event_type, limit),
                )
            ).fetchall()
        if latest:
            rows = list(reversed(rows))
        return [
            RunEvent(
                event_id=row["event_id"],
                run_id=row["run_id"],
                event_type=row["event_type"],
                actor=row["actor"],
                payload=row["payload"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def record_run_checkpoint(
        self, checkpoint: RunCheckpoint
    ) -> RunCheckpoint:
        async with self.connection() as conn:
            await conn.execute(
                """
                insert into run_checkpoints (
                    checkpoint_id, run_id, checkpoint_kind, status,
                    conversation_state, active_agents, source_record_ids,
                    artifact_ids, feedback_item_ids, event_cursor, state_digest,
                    created_by, notes, created_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    checkpoint.checkpoint_id,
                    checkpoint.run_id,
                    checkpoint.checkpoint_kind,
                    checkpoint.status.value,
                    Jsonb(checkpoint.conversation_state),
                    checkpoint.active_agents,
                    checkpoint.source_record_ids,
                    checkpoint.artifact_ids,
                    checkpoint.feedback_item_ids,
                    checkpoint.event_cursor,
                    Jsonb(checkpoint.state_digest),
                    checkpoint.created_by,
                    checkpoint.notes,
                    checkpoint.created_at,
                ),
            )
        return checkpoint

    async def list_run_checkpoints(
        self, run_id: UUID, limit: int = 25
    ) -> list[RunCheckpoint]:
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    select * from run_checkpoints
                    where run_id = %s
                    order by created_at desc
                    limit %s
                    """,
                    (run_id, limit),
                )
            ).fetchall()
        return [_run_checkpoint_from_row(row) for row in rows]

    async def record_agent_message(self, message: AgentMessage) -> AgentMessage:
        message = ensure_message_accepted_trace(message)
        async with self.connection() as conn:
            await conn.execute(
                """
                insert into agent_messages (
                    message_id, run_id, sender_agent_id, recipient_agent_id,
                    task_type, payload, requires_human_feedback, status,
                    claimed_by_agent_id, attempt_count, max_attempts, result,
                    depends_on_message_ids, handoff_trace, error,
                    created_at, updated_at
                )
                values (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                on conflict (message_id) do update
                set payload = excluded.payload,
                    depends_on_message_ids = excluded.depends_on_message_ids,
                    requires_human_feedback = excluded.requires_human_feedback,
                    status = excluded.status,
                    claimed_by_agent_id = excluded.claimed_by_agent_id,
                    attempt_count = excluded.attempt_count,
                    max_attempts = excluded.max_attempts,
                    result = excluded.result,
                    handoff_trace = case
                        when jsonb_array_length(excluded.handoff_trace)
                           > jsonb_array_length(
                               coalesce(agent_messages.handoff_trace, '[]'::jsonb)
                           )
                        then excluded.handoff_trace
                        else coalesce(agent_messages.handoff_trace, '[]'::jsonb)
                    end,
                    error = excluded.error,
                    updated_at = excluded.updated_at
                """,
                (
                    message.message_id,
                    message.run_id,
                    message.sender_agent_id,
                    message.recipient_agent_id,
                    message.task_type,
                    Jsonb(message.payload),
                    message.requires_human_feedback,
                    message.status.value,
                    message.claimed_by_agent_id,
                    message.attempt_count,
                    message.max_attempts,
                    Jsonb(message.result),
                    message.depends_on_message_ids,
                    Jsonb(message.handoff_trace),
                    message.error,
                    message.created_at,
                    message.updated_at,
                ),
            )
        return message

    async def record_agent_message_if_absent(
        self,
        message: AgentMessage,
    ) -> AgentMessage | None:
        message = ensure_message_accepted_trace(message)
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    """
                    insert into agent_messages (
                        message_id, run_id, sender_agent_id, recipient_agent_id,
                        task_type, payload, requires_human_feedback, status,
                        claimed_by_agent_id, attempt_count, max_attempts, result,
                        depends_on_message_ids, handoff_trace, error,
                        created_at, updated_at
                    )
                    values (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    on conflict (message_id) do nothing
                    returning *
                    """,
                    (
                        message.message_id,
                        message.run_id,
                        message.sender_agent_id,
                        message.recipient_agent_id,
                        message.task_type,
                        Jsonb(message.payload),
                        message.requires_human_feedback,
                        message.status.value,
                        message.claimed_by_agent_id,
                        message.attempt_count,
                        message.max_attempts,
                        Jsonb(message.result),
                        message.depends_on_message_ids,
                        Jsonb(message.handoff_trace),
                        message.error,
                        message.created_at,
                        message.updated_at,
                    ),
                )
            ).fetchone()
        return _agent_message_from_row(row) if row is not None else None

    async def update_agent_message_payload(
        self,
        message_id: UUID,
        payload: dict[str, Any],
        *,
        updated_at: datetime | None = None,
    ) -> AgentMessage | None:
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    """
                    update agent_messages
                    set payload = %s, updated_at = %s
                    where message_id = %s
                    returning *
                    """,
                    (
                        Jsonb(payload),
                        updated_at or datetime.now(timezone.utc),
                        message_id,
                    ),
                )
            ).fetchone()
        return _agent_message_from_row(row) if row is not None else None

    async def list_agent_messages(
        self,
        run_id: UUID,
        *,
        agent_id: str | None = None,
        direction: str = "all",
        status: AgentTaskStatus | None = None,
        limit: int = 200,
    ) -> list[AgentMessage]:
        filters = ["run_id = %s"]
        params: list[Any] = [run_id]
        if agent_id and direction == "inbox":
            filters.append("recipient_agent_id = %s")
            params.append(agent_id)
        elif agent_id and direction == "outbox":
            filters.append("sender_agent_id = %s")
            params.append(agent_id)
        elif agent_id:
            filters.append("(sender_agent_id = %s or recipient_agent_id = %s)")
            params.extend([agent_id, agent_id])
        if status:
            filters.append("status = %s")
            params.append(status.value)
        params.append(limit)
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    f"""
                    select * from agent_messages
                    where {' and '.join(filters)}
                    order by created_at asc
                    limit %s
                    """,
                    params,
                )
            ).fetchall()
        return [
            _agent_message_from_row(row)
            for row in rows
        ]

    async def get_agent_message(self, message_id: UUID) -> AgentMessage | None:
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    "select * from agent_messages where message_id = %s",
                    (message_id,),
                )
            ).fetchone()
        if row is None:
            return None
        return _agent_message_from_row(row)

    async def try_claim_agent_message(
        self,
        message_id: UUID,
        *,
        agent_id: str,
    ) -> AgentMessage | None:
        trace_entry = build_handoff_trace_entry(
            actor=agent_id,
            action="claimed",
            status=AgentTaskStatus.CLAIMED,
            notes="Worker atomically claimed task for durable execution.",
            metadata={"message_id": str(message_id)},
        )
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    """
                    update agent_messages
                    set status = %s,
                        claimed_by_agent_id = %s,
                        attempt_count = attempt_count + 1,
                        result = '{}'::jsonb,
                        handoff_trace = coalesce(handoff_trace, '[]'::jsonb)
                            || %s::jsonb,
                        error = null,
                        updated_at = now()
                    where message_id = %s
                      and recipient_agent_id = %s
                      and status = %s
                      and attempt_count < max_attempts
                      and not exists (
                          select 1
                          from unnest(depends_on_message_ids) as dependency_id
                          left join agent_messages as dependency
                            on dependency.message_id = dependency_id
                          where dependency.message_id is null
                             or dependency.status <> %s
                      )
                    returning *
                    """,
                    (
                        AgentTaskStatus.CLAIMED.value,
                        agent_id,
                        Jsonb([trace_entry]),
                        message_id,
                        agent_id,
                        AgentTaskStatus.ACCEPTED.value,
                        AgentTaskStatus.COMPLETED.value,
                    ),
                )
            ).fetchone()
        if row is None:
            return None
        return _agent_message_from_row(row)

    async def recover_stale_agent_messages(
        self,
        run_id: UUID,
        *,
        stale_before: datetime,
        statuses: list[AgentTaskStatus],
        agent_id: str | None = None,
        limit: int = 25,
        recovery_actor: str = "agent-harness-engineer",
    ) -> list[dict[str, Any]]:
        status_values = [status.value for status in statuses]
        if not status_values:
            return []
        trace_entry = build_handoff_trace_entry(
            actor=recovery_actor,
            action="stale_recovered",
            status=AgentTaskStatus.ACCEPTED,
            notes="Recovered stale claimed/in-progress task for reprocessing.",
            metadata={"stale_before": stale_before.isoformat()},
        )
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    with candidates as (
                        select
                            message_id,
                            status as previous_status,
                            claimed_by_agent_id as previous_claimed_by_agent_id,
                            updated_at as previous_updated_at
                        from agent_messages
                        where run_id = %s
                          and status = any(%s::text[])
                          and updated_at < %s
                          and (%s::text is null or recipient_agent_id = %s)
                        order by updated_at asc
                        limit %s
                        for update skip locked
                    )
                    update agent_messages as message
                    set status = %s,
                        claimed_by_agent_id = null,
                        result = coalesce(message.result, '{}'::jsonb)
                            || jsonb_build_object(
                                'stale_recovery',
                                jsonb_build_object(
                                    'recovered_by', %s::text,
                                    'previous_status', candidates.previous_status,
                                    'previous_claimed_by_agent_id',
                                        candidates.previous_claimed_by_agent_id,
                                    'previous_updated_at',
                                        candidates.previous_updated_at,
                                    'recovered_at', now()
                                )
                            ),
                        handoff_trace = coalesce(message.handoff_trace, '[]'::jsonb)
                            || %s::jsonb,
                        error = null,
                        updated_at = now()
                    from candidates
                    where message.message_id = candidates.message_id
                    returning
                        message.*,
                        candidates.previous_status,
                        candidates.previous_claimed_by_agent_id,
                        candidates.previous_updated_at
                    """,
                    (
                        run_id,
                        status_values,
                        stale_before,
                        agent_id,
                        agent_id,
                        limit,
                        AgentTaskStatus.ACCEPTED.value,
                        recovery_actor,
                        Jsonb([trace_entry]),
                    ),
                )
            ).fetchall()
        return [
            {
                "message": _agent_message_from_row(row),
                "from_status": AgentTaskStatus(row["previous_status"]),
                "previous_claimed_by_agent_id": row["previous_claimed_by_agent_id"],
                "previous_updated_at": row["previous_updated_at"],
            }
            for row in rows
        ]

    async def block_exhausted_agent_messages(
        self,
        run_id: UUID,
        *,
        agent_id: str | None = None,
        limit: int = 25,
        recovery_actor: str = "agent-harness-engineer",
    ) -> list[AgentMessage]:
        trace_entry = build_handoff_trace_entry(
            actor=recovery_actor,
            action="retry_exhausted_blocked",
            status=AgentTaskStatus.BLOCKED,
            notes="Blocked task after durable retry attempts were exhausted.",
            metadata={},
        )
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    with candidates as (
                        select message_id
                        from agent_messages
                        where run_id = %s
                          and status = %s
                          and attempt_count >= max_attempts
                          and (%s::text is null or recipient_agent_id = %s)
                        order by updated_at asc
                        limit %s
                        for update skip locked
                    )
                    update agent_messages as message
                    set status = %s,
                        claimed_by_agent_id = coalesce(
                            claimed_by_agent_id,
                            recipient_agent_id
                        ),
                        result = coalesce(message.result, '{}'::jsonb)
                            || jsonb_build_object(
                                'retry_policy',
                                jsonb_build_object(
                                    'blocked_by', %s::text,
                                    'attempt_count', attempt_count,
                                    'max_attempts', max_attempts,
                                    'blocked_at', now()
                                )
                            ),
                        handoff_trace = coalesce(message.handoff_trace, '[]'::jsonb)
                            || %s::jsonb,
                        error = %s,
                        updated_at = now()
                    from candidates
                    where message.message_id = candidates.message_id
                    returning message.*
                    """,
                    (
                        run_id,
                        AgentTaskStatus.ACCEPTED.value,
                        agent_id,
                        agent_id,
                        limit,
                        AgentTaskStatus.BLOCKED.value,
                        recovery_actor,
                        Jsonb([trace_entry]),
                        "A2A task exhausted retry attempts.",
                    ),
                )
            ).fetchall()
        return [_agent_message_from_row(row) for row in rows]

    async def authorize_agent_message_retry(
        self,
        message_id: UUID,
        *,
        agent_id: str,
        reason: str,
        reset_attempt_count: bool = True,
        max_attempts: int | None = None,
    ) -> AgentMessage | None:
        trace_entry = build_handoff_trace_entry(
            actor=agent_id,
            action="retry_authorized",
            status=AgentTaskStatus.ACCEPTED,
            notes=reason,
            metadata={
                "reset_attempt_count": reset_attempt_count,
                "authorized_max_attempts": max_attempts,
            },
        )
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    """
                    update agent_messages
                    set status = %s,
                        claimed_by_agent_id = null,
                        attempt_count = case
                            when %s then 0
                            else attempt_count
                        end,
                        max_attempts = coalesce(%s, max_attempts),
                        result = coalesce(result, '{}'::jsonb)
                            || jsonb_build_object(
                                'retry_authorization',
                                jsonb_build_object(
                                    'authorized_by', %s::text,
                                    'reason', %s::text,
                                    'reset_attempt_count', %s::boolean,
                                    'authorized_max_attempts', %s::integer,
                                    'authorized_at', now()
                                )
                            ),
                        handoff_trace = coalesce(handoff_trace, '[]'::jsonb)
                            || %s::jsonb,
                        error = null,
                        updated_at = now()
                    where message_id = %s
                    returning *
                    """,
                    (
                        AgentTaskStatus.ACCEPTED.value,
                        reset_attempt_count,
                        max_attempts,
                        agent_id,
                        reason,
                        reset_attempt_count,
                        max_attempts,
                        Jsonb([trace_entry]),
                        message_id,
                    ),
                )
            ).fetchone()
        if row is None:
            return None
        return _agent_message_from_row(row)

    async def repair_agent_message_dependencies(
        self,
        message_id: UUID,
        *,
        agent_id: str,
        remove_dependency_message_ids: list[UUID],
        reason: str,
    ) -> AgentMessage | None:
        current = await self.get_agent_message(message_id)
        if current is None:
            return None
        requested_dependency_ids = set(remove_dependency_message_ids)
        removed_dependency_ids = [
            dependency_id
            for dependency_id in current.depends_on_message_ids
            if dependency_id in requested_dependency_ids
        ]
        if not removed_dependency_ids:
            return current
        removed_dependency_id_set = set(removed_dependency_ids)
        remaining_dependency_ids = [
            dependency_id
            for dependency_id in current.depends_on_message_ids
            if dependency_id not in removed_dependency_id_set
        ]
        trace_entry = build_handoff_trace_entry(
            actor=agent_id,
            action="dependencies_repaired",
            status=current.status,
            notes=reason,
            metadata={
                "removed_dependency_message_ids": [
                    str(dependency_id) for dependency_id in removed_dependency_ids
                ],
                "remaining_dependency_message_ids": [
                    str(dependency_id) for dependency_id in remaining_dependency_ids
                ],
            },
        )
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    """
                    update agent_messages
                    set depends_on_message_ids = %s,
                        claimed_by_agent_id = case
                            when status = %s then null
                            else claimed_by_agent_id
                        end,
                        result = coalesce(result, '{}'::jsonb)
                            || jsonb_build_object(
                                'dependency_repair',
                                jsonb_build_object(
                                    'repaired_by', %s::text,
                                    'reason', %s::text,
                                    'removed_dependency_message_ids', %s::jsonb,
                                    'remaining_dependency_message_ids', %s::jsonb,
                                    'repaired_at', now()
                                )
                            ),
                        handoff_trace = coalesce(handoff_trace, '[]'::jsonb)
                            || %s::jsonb,
                        updated_at = now()
                    where message_id = %s
                    returning *
                    """,
                    (
                        remaining_dependency_ids,
                        AgentTaskStatus.ACCEPTED.value,
                        agent_id,
                        reason,
                        Jsonb([str(item) for item in removed_dependency_ids]),
                        Jsonb([str(item) for item in remaining_dependency_ids]),
                        Jsonb([trace_entry]),
                        message_id,
                    ),
                )
            ).fetchone()
        if row is None:
            return None
        return _agent_message_from_row(row)

    async def update_agent_message_status(
        self,
        *,
        message_id: UUID,
        status: AgentTaskStatus,
        agent_id: str,
        result: dict[str, Any] | None = None,
        notes: str | None = None,
        error: str | None = None,
    ) -> AgentMessage | None:
        trace_entry = build_handoff_trace_entry(
            actor=agent_id,
            action="status_updated",
            status=status,
            notes=notes or error,
            metadata={"message_id": str(message_id), "has_result": bool(result)},
        )
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    """
                    update agent_messages
                    set status = %s,
                        claimed_by_agent_id = coalesce(claimed_by_agent_id, %s),
                        result = %s::jsonb,
                        handoff_trace = coalesce(handoff_trace, '[]'::jsonb)
                            || %s::jsonb,
                        error = %s,
                        updated_at = now()
                    where message_id = %s
                    returning *
                    """,
                    (
                        status.value,
                        agent_id,
                        Jsonb(result or {}),
                        Jsonb([trace_entry]),
                        error,
                        message_id,
                    ),
                )
            ).fetchone()
        if row is None:
            return None
        return _agent_message_from_row(row)

    async def record_feedback(self, feedback: FeedbackItem) -> FeedbackItem:
        async with self.connection() as conn:
            await conn.execute(
                """
                insert into feedback_items (
                    feedback_id, run_id, author, target_agent_id,
                    feedback_text, status, metadata, resolution_notes,
                    resolved_by, resolved_at, created_at, updated_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    feedback.feedback_id,
                    feedback.run_id,
                    feedback.author,
                    feedback.target_agent_id,
                    feedback.feedback_text,
                    feedback.status.value,
                    Jsonb(feedback.metadata),
                    feedback.resolution_notes,
                    feedback.resolved_by,
                    feedback.resolved_at,
                    feedback.created_at,
                    feedback.updated_at,
                ),
            )
            await conn.execute(
                """
                update runs
                set feedback_item_ids = array_append(feedback_item_ids, %s),
                    updated_at = now()
                where run_id = %s
                """,
                (feedback.feedback_id, feedback.run_id),
            )
        return feedback

    async def record_feedback_if_absent(
        self, feedback: FeedbackItem
    ) -> FeedbackItem | None:
        async with self.connection() as conn:
            async with conn.transaction():
                row = await (
                    await conn.execute(
                        """
                        insert into feedback_items (
                            feedback_id, run_id, author, target_agent_id,
                            feedback_text, status, metadata, resolution_notes,
                            resolved_by, resolved_at, created_at, updated_at
                        )
                        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        on conflict (feedback_id) do nothing
                        returning *
                        """,
                        (
                            feedback.feedback_id,
                            feedback.run_id,
                            feedback.author,
                            feedback.target_agent_id,
                            feedback.feedback_text,
                            feedback.status.value,
                            Jsonb(feedback.metadata),
                            feedback.resolution_notes,
                            feedback.resolved_by,
                            feedback.resolved_at,
                            feedback.created_at,
                            feedback.updated_at,
                        ),
                    )
                ).fetchone()
                if row is None:
                    return None
                await conn.execute(
                    """
                    update runs
                    set feedback_item_ids = case
                            when %s = any(feedback_item_ids) then feedback_item_ids
                            else array_append(feedback_item_ids, %s)
                        end,
                        updated_at = now()
                    where run_id = %s
                    """,
                    (
                        feedback.feedback_id,
                        feedback.feedback_id,
                        feedback.run_id,
                    ),
                )
        return _feedback_from_row(row)

    async def get_feedback(self, feedback_id: UUID) -> FeedbackItem | None:
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    "select * from feedback_items where feedback_id = %s",
                    (feedback_id,),
                )
            ).fetchone()
        if row is None:
            return None
        return _feedback_from_row(row)

    async def list_feedback(
        self,
        run_id: UUID,
        status: FeedbackStatus | None = None,
    ) -> list[FeedbackItem]:
        filters = ["run_id = %s"]
        params: list[Any] = [run_id]
        if status:
            filters.append("status = %s")
            params.append(status.value)
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    f"""
                    select * from feedback_items
                    where {' and '.join(filters)}
                    order by created_at asc
                    """,
                    params,
                )
            ).fetchall()
        return [_feedback_from_row(row) for row in rows]

    async def update_feedback_status(
        self,
        *,
        feedback_id: UUID,
        status: FeedbackStatus,
        resolver: str,
        resolution_notes: str | None = None,
    ) -> FeedbackItem | None:
        resolved_at = "now()" if status in {
            FeedbackStatus.RESOLVED,
            FeedbackStatus.REJECTED,
        } else "null"
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    f"""
                    update feedback_items
                    set status = %s,
                        resolution_notes = %s,
                        resolved_by = %s,
                        resolved_at = {resolved_at},
                        updated_at = now()
                    where feedback_id = %s
                    returning *
                    """,
                    (status.value, resolution_notes, resolver, feedback_id),
                )
            ).fetchone()
        if row is None:
            return None
        return _feedback_from_row(row)

    async def record_source(self, source: SourceRecord) -> SourceRecord:
        async with self.connection() as conn:
            await conn.execute(
                """
                insert into source_records (
                    source_id, run_id, citation_id, title, url, publisher,
                    retrieved_at, published_at, metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    source.source_id,
                    source.run_id,
                    source.citation_id,
                    source.title,
                    str(source.url),
                    source.publisher,
                    source.retrieved_at,
                    source.published_at,
                    Jsonb(source.metadata),
                ),
            )
            await conn.execute(
                """
                update runs
                set source_record_ids = array_append(source_record_ids, %s),
                    updated_at = now()
                where run_id = %s
                """,
                (source.source_id, source.run_id),
            )
        return source

    async def list_sources(self, run_id: UUID) -> list[SourceRecord]:
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    select * from source_records
                    where run_id = %s
                    order by retrieved_at asc
                    """,
                    (run_id,),
                )
            ).fetchall()
        return [
            SourceRecord(
                source_id=row["source_id"],
                run_id=row["run_id"],
                citation_id=row["citation_id"],
                title=row["title"],
                url=row["url"],
                publisher=row["publisher"],
                retrieved_at=row["retrieved_at"],
                published_at=row["published_at"],
                metadata=row["metadata"],
            )
            for row in rows
        ]

    async def record_claim(self, claim: ClaimRecord) -> ClaimRecord:
        async with self.connection() as conn:
            await conn.execute(
                """
                insert into claim_records (
                    claim_id, run_id, claim_text, support_status,
                    source_ids, reviewer_agent_id, notes
                )
                values (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    claim.claim_id,
                    claim.run_id,
                    claim.claim_text,
                    claim.support_status.value,
                    claim.source_ids,
                    claim.reviewer_agent_id,
                    claim.notes,
                ),
            )
        return claim

    async def list_claims(self, run_id: UUID) -> list[ClaimRecord]:
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    select * from claim_records
                    where run_id = %s
                    order by created_at asc
                    """,
                    (run_id,),
                )
            ).fetchall()
        return [
            ClaimRecord(
                claim_id=row["claim_id"],
                run_id=row["run_id"],
                claim_text=row["claim_text"],
                support_status=row["support_status"],
                source_ids=row["source_ids"],
                reviewer_agent_id=row["reviewer_agent_id"],
                notes=row["notes"],
            )
            for row in rows
        ]

    async def update_claim(self, claim: ClaimRecord) -> ClaimRecord | None:
        async with self.connection() as conn:
            result = await conn.execute(
                """
                update claim_records
                set support_status = %s,
                    source_ids = %s,
                    reviewer_agent_id = %s,
                    notes = %s
                where claim_id = %s
                  and run_id = %s
                """,
                (
                    claim.support_status.value,
                    claim.source_ids,
                    claim.reviewer_agent_id,
                    claim.notes,
                    claim.claim_id,
                    claim.run_id,
                ),
            )
        if result.rowcount == 0:
            return None
        return claim

    async def record_artifact(self, artifact: ArtifactRecord) -> ArtifactRecord:
        async with self.connection() as conn:
            await conn.execute(
                """
                insert into artifacts (
                    artifact_id, run_id, artifact_type, title, uri, content, provenance,
                    source_ids, reviewer_decisions, revision_history, created_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    artifact.artifact_id,
                    artifact.run_id,
                    artifact.artifact_type.value,
                    artifact.title,
                    artifact.uri,
                    Jsonb(artifact.content),
                    Jsonb(artifact.provenance),
                    artifact.source_ids,
                    Jsonb(artifact.reviewer_decisions),
                    Jsonb(artifact.revision_history),
                    artifact.created_at,
                ),
            )
            await conn.execute(
                """
                update runs
                set artifact_ids = array_append(artifact_ids, %s),
                    updated_at = now()
                where run_id = %s
                """,
                (artifact.artifact_id, artifact.run_id),
            )
        return artifact

    async def record_artifact_if_absent(
        self,
        artifact: ArtifactRecord,
    ) -> ArtifactRecord | None:
        async with self.connection() as conn:
            async with conn.transaction():
                row = await (
                    await conn.execute(
                        """
                        insert into artifacts (
                            artifact_id, run_id, artifact_type, title, uri, content,
                            provenance, source_ids, reviewer_decisions,
                            revision_history, created_at
                        )
                        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        on conflict (artifact_id) do nothing
                        returning *
                        """,
                        (
                            artifact.artifact_id,
                            artifact.run_id,
                            artifact.artifact_type.value,
                            artifact.title,
                            artifact.uri,
                            Jsonb(artifact.content),
                            Jsonb(artifact.provenance),
                            artifact.source_ids,
                            Jsonb(artifact.reviewer_decisions),
                            Jsonb(artifact.revision_history),
                            artifact.created_at,
                        ),
                    )
                ).fetchone()
                if row is None:
                    await conn.execute(
                        """
                        update runs
                        set artifact_ids = case
                                when %s = any(artifact_ids) then artifact_ids
                                else array_append(artifact_ids, %s)
                            end,
                            updated_at = now()
                        where run_id = %s
                        """,
                        (
                            artifact.artifact_id,
                            artifact.artifact_id,
                            artifact.run_id,
                        ),
                    )
                    return None
                await conn.execute(
                    """
                    update runs
                    set artifact_ids = case
                            when %s = any(artifact_ids) then artifact_ids
                            else array_append(artifact_ids, %s)
                        end,
                        updated_at = now()
                    where run_id = %s
                    """,
                    (
                        artifact.artifact_id,
                        artifact.artifact_id,
                        artifact.run_id,
                    ),
                )
        return _artifact_from_row(row)

    async def list_artifacts(self, run_id: UUID) -> list[ArtifactRecord]:
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    select * from artifacts
                    where run_id = %s
                    order by created_at asc
                    """,
                    (run_id,),
                )
            ).fetchall()
        return [_artifact_from_row(row) for row in rows]

    async def update_artifact(self, artifact: ArtifactRecord) -> ArtifactRecord | None:
        async with self.connection() as conn:
            result = await conn.execute(
                """
                update artifacts
                set title = %s,
                    uri = %s,
                    content = %s,
                    provenance = %s,
                    source_ids = %s,
                    reviewer_decisions = %s,
                    revision_history = %s
                where artifact_id = %s
                  and run_id = %s
                """,
                (
                    artifact.title,
                    artifact.uri,
                    Jsonb(artifact.content),
                    Jsonb(artifact.provenance),
                    artifact.source_ids,
                    Jsonb(artifact.reviewer_decisions),
                    Jsonb(artifact.revision_history),
                    artifact.artifact_id,
                    artifact.run_id,
                ),
            )
        if result.rowcount == 0:
            return None
        return artifact

    async def record_retrieval_quality_result(self, result) -> None:
        """Persist retrieval quality rows for queryable local run evidence."""

        candidate_db_ids: dict[str, UUID] = {}
        graph_node_db_ids: dict[str, UUID] = {}
        async with self.connection() as conn:
            for candidate in result.candidates:
                candidate_db_id = uuid4()
                candidate_db_ids[candidate.candidate_id] = candidate_db_id
                await conn.execute(
                    """
                    insert into retrieval_candidates (
                        candidate_id, run_id, source_id, query, retriever,
                        rank, score, fused_rank, metadata
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        candidate_db_id,
                        result.run_id,
                        candidate.source_id,
                        candidate.query,
                        "+".join(candidate.retrievers) or "source_ledger",
                        candidate.fused_rank,
                        candidate.rerank_score,
                        candidate.fused_rank,
                        Jsonb(
                            {
                                **candidate.model_dump(mode="json"),
                                "ledger_artifact_id": (
                                    str(result.ledger_artifact_id)
                                    if result.ledger_artifact_id
                                    else None
                                ),
                            }
                        ),
                    ),
                )
                await conn.execute(
                    """
                    insert into retrieval_rerank_decisions (
                        run_id, candidate_id, reranker, rank_before,
                        rank_after, relevance_score, accepted_for_context,
                        reason, metadata
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        result.run_id,
                        candidate_db_id,
                        candidate.reranker,
                        candidate.fused_rank,
                        candidate.fused_rank,
                        candidate.rerank_score,
                        candidate.accepted_for_context,
                        candidate.rerank_reason
                        or _retrieval_candidate_decision_reason(candidate),
                        Jsonb(candidate.model_dump(mode="json")),
                    ),
                )

            for entry in result.graph_coverage:
                node_db_id = uuid4()
                graph_node_db_ids[entry.node_id] = node_db_id
                await conn.execute(
                    """
                    insert into knowledge_graph_nodes (
                        node_id, run_id, node_type, label, source_ids,
                        claim_ids, artifact_ids, metadata
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        node_db_id,
                        result.run_id,
                        entry.node_type,
                        entry.label,
                        entry.source_ids,
                        entry.claim_ids,
                        _artifact_ids_from_graph_entry(entry),
                        Jsonb(
                            {
                                **entry.model_dump(mode="json"),
                                "logical_node_id": entry.node_id,
                                "ledger_artifact_id": (
                                    str(result.ledger_artifact_id)
                                    if result.ledger_artifact_id
                                    else None
                                ),
                            }
                        ),
                    ),
                )

            for edge in _retrieval_graph_edges(result.graph_coverage):
                from_node_id = graph_node_db_ids.get(edge["from_node_id"])
                to_node_id = graph_node_db_ids.get(edge["to_node_id"])
                if from_node_id is None or to_node_id is None:
                    continue
                await conn.execute(
                    """
                    insert into knowledge_graph_edges (
                        run_id, from_node_id, to_node_id, relationship,
                        confidence, source_ids, metadata
                    )
                    values (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        result.run_id,
                        from_node_id,
                        to_node_id,
                        edge["relationship"],
                        edge["confidence"],
                        edge["source_ids"],
                        Jsonb(
                            {
                                "from_logical_node_id": edge["from_node_id"],
                                "to_logical_node_id": edge["to_node_id"],
                                "ledger_artifact_id": (
                                    str(result.ledger_artifact_id)
                                    if result.ledger_artifact_id
                                    else None
                                ),
                            }
                        ),
                    ),
                )

            await conn.execute(
                """
                insert into retrieval_evaluations (
                    run_id, topic, status, candidate_count,
                    accepted_candidate_count, precision_risk_count,
                    recall_gap_count, coverage_gap_count, recommended_queries,
                    metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    result.run_id,
                    result.topic,
                    result.status.value,
                    result.candidate_count,
                    result.accepted_candidate_count,
                    result.precision_risk_count,
                    result.recall_gap_count,
                    result.coverage_gap_count,
                    result.recommended_queries,
                    Jsonb(
                        {
                            "summary": result.summary,
                            "reranked_candidate_count": (
                                result.reranked_candidate_count
                            ),
                            "graph_node_count": result.graph_node_count,
                            "ledger_artifact_id": (
                                str(result.ledger_artifact_id)
                                if result.ledger_artifact_id
                                else None
                            ),
                        }
                    ),
                ),
            )

    async def record_guardrail_audit(
        self, audit: GuardrailAuditRecord
    ) -> GuardrailAuditRecord:
        async with self.connection() as conn:
            await conn.execute(
                """
                insert into guardrail_audits (
                    audit_id, run_id, artifact_id, status, source_coverage,
                    claim_count, supported_claim_ids, needs_review_claim_ids,
                    unsupported_claim_ids, missing_source_claim_ids,
                    blocking_issues, reviewer_agent_id, notes, created_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    audit.audit_id,
                    audit.run_id,
                    audit.artifact_id,
                    audit.status.value,
                    audit.source_coverage,
                    audit.claim_count,
                    audit.supported_claim_ids,
                    audit.needs_review_claim_ids,
                    audit.unsupported_claim_ids,
                    audit.missing_source_claim_ids,
                    audit.blocking_issues,
                    audit.reviewer_agent_id,
                    audit.notes,
                    audit.created_at,
                ),
            )
        return audit

    async def list_guardrail_audits(
        self, run_id: UUID, artifact_id: UUID | None = None
    ) -> list[GuardrailAuditRecord]:
        filters = ["run_id = %s"]
        params: list[Any] = [run_id]
        if artifact_id:
            filters.append("artifact_id = %s")
            params.append(artifact_id)
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    f"""
                    select * from guardrail_audits
                    where {' and '.join(filters)}
                    order by created_at asc
                    """,
                    params,
                )
            ).fetchall()
        return [
            GuardrailAuditRecord(
                audit_id=row["audit_id"],
                run_id=row["run_id"],
                artifact_id=row["artifact_id"],
                status=GuardrailAuditStatus(row["status"]),
                source_coverage=row["source_coverage"],
                claim_count=row["claim_count"],
                supported_claim_ids=row["supported_claim_ids"],
                needs_review_claim_ids=row["needs_review_claim_ids"],
                unsupported_claim_ids=row["unsupported_claim_ids"],
                missing_source_claim_ids=row["missing_source_claim_ids"],
                blocking_issues=row["blocking_issues"],
                reviewer_agent_id=row["reviewer_agent_id"],
                notes=row["notes"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def record_memory(self, memory: AgentMemory) -> AgentMemory:
        async with self.connection() as conn:
            await conn.execute(
                """
                insert into agent_memories (
                    memory_id, agent_id, run_id, memory_kind, content,
                    embedding, metadata, created_at
                )
                values (%s, %s, %s, %s, %s, %s::vector, %s, %s)
                """,
                (
                    memory.memory_id,
                    memory.agent_id,
                    memory.run_id,
                    memory.memory_kind,
                    memory.content,
                    _vector_literal(memory.embedding),
                    Jsonb(memory.metadata),
                    memory.created_at,
                ),
            )
        return memory

    async def list_memories(
        self, agent_id: str | None = None, run_id: UUID | None = None
    ) -> list[AgentMemory]:
        filters = []
        params: list[Any] = []
        if agent_id:
            filters.append("agent_id = %s")
            params.append(agent_id)
        if run_id:
            filters.append("run_id = %s")
            params.append(run_id)
        where = f"where {' and '.join(filters)}" if filters else ""
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    f"""
                    select memory_id, agent_id, run_id, memory_kind, content,
                           embedding::text as embedding, metadata, created_at
                    from agent_memories
                    {where}
                    order by created_at asc
                    """,
                    params,
                )
            ).fetchall()
        return [
            AgentMemory(
                memory_id=row["memory_id"],
                agent_id=row["agent_id"],
                run_id=row["run_id"],
                memory_kind=row["memory_kind"],
                content=row["content"],
                embedding=_parse_vector(row["embedding"]),
                metadata=row["metadata"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def search_memories(
        self,
        *,
        agent_id: str | None = None,
        run_id: UUID | None = None,
        include_global_memories: bool = True,
        query_embedding: list[float] | None = None,
        limit: int = 10,
    ) -> list[tuple[AgentMemory, float | None]]:
        filters = []
        params: list[Any] = []
        if agent_id:
            filters.append("agent_id = %s")
            params.append(agent_id)
        if run_id and include_global_memories:
            filters.append("(run_id = %s or run_id is null)")
            params.append(run_id)
        elif run_id:
            filters.append("run_id = %s")
            params.append(run_id)
        if query_embedding:
            filters.append("embedding is not null")

        where = f"where {' and '.join(filters)}" if filters else ""
        vector = _vector_literal(query_embedding)
        if vector:
            query = f"""
                select memory_id, agent_id, run_id, memory_kind, content,
                       embedding::text as embedding, metadata, created_at,
                       embedding <-> %s::vector as distance
                from agent_memories
                {where}
                order by embedding <-> %s::vector asc, created_at asc
                limit %s
            """
            query_params = [vector, *params, vector, limit]
        else:
            query = f"""
                select memory_id, agent_id, run_id, memory_kind, content,
                       embedding::text as embedding, metadata, created_at,
                       null::double precision as distance
                from agent_memories
                {where}
                order by created_at asc
                limit %s
            """
            query_params = [*params, limit]

        async with self.connection() as conn:
            rows = await (await conn.execute(query, query_params)).fetchall()
        return [
            (
                AgentMemory(
                    memory_id=row["memory_id"],
                    agent_id=row["agent_id"],
                    run_id=row["run_id"],
                    memory_kind=row["memory_kind"],
                    content=row["content"],
                    embedding=_parse_vector(row["embedding"]),
                    metadata=row["metadata"],
                    created_at=row["created_at"],
                ),
                row["distance"],
            )
            for row in rows
        ]

    async def record_worker_profile(self, profile: WorkerProfile) -> WorkerProfile:
        async with self.connection() as conn:
            await conn.execute(
                """
                insert into worker_profiles (
                    profile_id, run_id, name, execution_mode, agent_ids,
                    max_tasks_per_agent, max_rounds, poll_interval_seconds,
                    include_global_memories, memory_limit,
                    autonomous_auto_refresh_research_sources,
                    autonomous_block_on_research_freshness_blocked,
                    autonomous_block_on_retrieval_quality_blocked,
                    autonomous_export_memory_summary_to_obsidian,
                    autonomous_memory_summary_agent_id,
                    autonomous_memory_summary_limit,
                    use_gemma, fail_on_provider_error, status,
                    last_heartbeat_at, heartbeat_claimed_at,
                    heartbeat_claimed_by, heartbeat_lease_until,
                    created_at, updated_at
                )
                values (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    profile.profile_id,
                    profile.run_id,
                    profile.name,
                    profile.execution_mode.value,
                    profile.agent_ids,
                    profile.max_tasks_per_agent,
                    profile.max_rounds,
                    profile.poll_interval_seconds,
                    profile.include_global_memories,
                    profile.memory_limit,
                    profile.autonomous_auto_refresh_research_sources,
                    profile.autonomous_block_on_research_freshness_blocked,
                    profile.autonomous_block_on_retrieval_quality_blocked,
                    profile.autonomous_export_memory_summary_to_obsidian,
                    profile.autonomous_memory_summary_agent_id,
                    profile.autonomous_memory_summary_limit,
                    profile.use_gemma,
                    profile.fail_on_provider_error,
                    profile.status.value,
                    profile.last_heartbeat_at,
                    profile.heartbeat_claimed_at,
                    profile.heartbeat_claimed_by,
                    profile.heartbeat_lease_until,
                    profile.created_at,
                    profile.updated_at,
                ),
            )
        return profile

    async def list_worker_profiles(self, run_id: UUID) -> list[WorkerProfile]:
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    select * from worker_profiles
                    where run_id = %s
                    order by created_at asc
                    """,
                    (run_id,),
                )
            ).fetchall()
        return [_worker_profile_from_row(row) for row in rows]

    async def list_due_worker_profiles(
        self,
        limit: int = 25,
        run_id: UUID | None = None,
        execution_mode: WorkerProfileExecutionMode | None = None,
    ) -> list[WorkerProfile]:
        execution_mode_value = execution_mode.value if execution_mode else None
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    select * from worker_profiles
                    where status = %s
                      and (%s::uuid is null or run_id = %s::uuid)
                      and (%s::text is null or execution_mode = %s::text)
                      and (
                        last_heartbeat_at is null
                        or last_heartbeat_at
                            + (poll_interval_seconds * interval '1 second') <= now()
                      )
                      and (
                        heartbeat_lease_until is null
                        or heartbeat_lease_until <= now()
                      )
                    order by coalesce(last_heartbeat_at, created_at) asc
                    limit %s
                    """,
                    (
                        WorkerProfileStatus.ACTIVE.value,
                        run_id,
                        run_id,
                        execution_mode_value,
                        execution_mode_value,
                        limit,
                    ),
                )
            ).fetchall()
        return [_worker_profile_from_row(row) for row in rows]

    async def get_worker_profile(self, profile_id: UUID) -> WorkerProfile | None:
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    "select * from worker_profiles where profile_id = %s",
                    (profile_id,),
                )
            ).fetchone()
        if row is None:
            return None
        return _worker_profile_from_row(row)

    async def update_worker_profile_status(
        self,
        profile_id: UUID,
        status: WorkerProfileStatus,
    ) -> WorkerProfile | None:
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    """
                    update worker_profiles
                    set status = %s, updated_at = now()
                    where profile_id = %s
                    returning *
                    """,
                    (status.value, profile_id),
                )
            ).fetchone()
        if row is None:
            return None
        return _worker_profile_from_row(row)

    async def try_claim_worker_profile_heartbeat(
        self,
        profile_id: UUID,
        *,
        claimed_by: str,
        lease_seconds: float,
    ) -> WorkerProfile | None:
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    """
                    update worker_profiles
                    set heartbeat_claimed_at = now(),
                        heartbeat_claimed_by = %s,
                        heartbeat_lease_until = now()
                            + (%s * interval '1 second'),
                        updated_at = now()
                    where profile_id = %s
                      and status = %s
                      and (
                        heartbeat_lease_until is null
                        or heartbeat_lease_until <= now()
                      )
                    returning *
                    """,
                    (
                        claimed_by,
                        lease_seconds,
                        profile_id,
                        WorkerProfileStatus.ACTIVE.value,
                    ),
                )
            ).fetchone()
        if row is None:
            return None
        return _worker_profile_from_row(row)

    async def record_worker_profile_heartbeat(
        self,
        profile_id: UUID,
    ) -> WorkerProfile | None:
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    """
                    update worker_profiles
                    set last_heartbeat_at = now(),
                        heartbeat_claimed_at = null,
                        heartbeat_claimed_by = null,
                        heartbeat_lease_until = null,
                        updated_at = now()
                    where profile_id = %s
                    returning *
                    """,
                    (profile_id,),
                )
            ).fetchone()
        if row is None:
            return None
        return _worker_profile_from_row(row)


def _retrieval_candidate_decision_reason(candidate) -> str:
    if candidate.accepted_for_context:
        return "accepted_for_context"
    risks = candidate.precision_risks or candidate.recall_risks
    return ", ".join(risks) if risks else "not_selected_for_context"


def _artifact_ids_from_graph_entry(entry) -> list[UUID]:
    prefix = "artifact:"
    if entry.node_type != "artifact" or not entry.node_id.startswith(prefix):
        return []
    try:
        return [UUID(entry.node_id.removeprefix(prefix))]
    except ValueError:
        return []


def _retrieval_graph_edges(entries) -> list[dict[str, Any]]:
    entry_by_node_id = {entry.node_id: entry for entry in entries}
    edges: list[dict[str, Any]] = []
    for entry in entries:
        if entry.node_type == "claim":
            for source_id in entry.source_ids:
                source_node_id = f"source:{source_id}"
                if source_node_id not in entry_by_node_id:
                    continue
                supported = entry.coverage_status == "covered"
                edges.append(
                    {
                        "from_node_id": entry.node_id,
                        "to_node_id": source_node_id,
                        "relationship": (
                            "supported_by" if supported else "candidate_evidence"
                        ),
                        "confidence": 1.0 if supported else 0.35,
                        "source_ids": [source_id],
                    }
                )
        if entry.node_type == "artifact":
            for source_id in entry.source_ids:
                source_node_id = f"source:{source_id}"
                if source_node_id not in entry_by_node_id:
                    continue
                edges.append(
                    {
                        "from_node_id": entry.node_id,
                        "to_node_id": source_node_id,
                        "relationship": "uses_source",
                        "confidence": (
                            1.0 if entry.coverage_status == "covered" else 0.35
                        ),
                        "source_ids": [source_id],
                    }
                )
            for claim_id in entry.claim_ids:
                claim_node_id = f"claim:{claim_id}"
                if claim_node_id not in entry_by_node_id:
                    continue
                edges.append(
                    {
                        "from_node_id": entry.node_id,
                        "to_node_id": claim_node_id,
                        "relationship": "depends_on_claim",
                        "confidence": (
                            1.0 if entry.coverage_status == "covered" else 0.35
                        ),
                        "source_ids": entry.source_ids,
                    }
                )
    return edges


def _run_event_from_row(row: dict[str, Any]) -> RunEvent:
    return RunEvent(
        event_id=row["event_id"],
        run_id=row["run_id"],
        event_type=row["event_type"],
        actor=row["actor"],
        payload=row["payload"],
        created_at=row["created_at"],
    )


def _feedback_from_row(row: dict[str, Any]) -> FeedbackItem:
    return FeedbackItem(
        feedback_id=row["feedback_id"],
        run_id=row["run_id"],
        author=row["author"],
        target_agent_id=row["target_agent_id"],
        feedback_text=row["feedback_text"],
        status=FeedbackStatus(row["status"]),
        metadata=row["metadata"],
        resolution_notes=row["resolution_notes"],
        resolved_by=row["resolved_by"],
        resolved_at=row["resolved_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _run_checkpoint_from_row(row: dict[str, Any]) -> RunCheckpoint:
    return RunCheckpoint(
        checkpoint_id=row["checkpoint_id"],
        run_id=row["run_id"],
        checkpoint_kind=row["checkpoint_kind"],
        status=RunStatus(row["status"]),
        conversation_state=row["conversation_state"],
        active_agents=row["active_agents"],
        source_record_ids=row["source_record_ids"],
        artifact_ids=row["artifact_ids"],
        feedback_item_ids=row["feedback_item_ids"],
        event_cursor=row["event_cursor"],
        state_digest=row["state_digest"],
        created_by=row["created_by"],
        notes=row["notes"],
        created_at=row["created_at"],
    )


def _conversation_turn_from_row(row: dict[str, Any]) -> ConversationTurn:
    return ConversationTurn(
        turn_id=row["turn_id"],
        run_id=row["run_id"],
        speaker=row["speaker"],
        modality=row["modality"],
        transcript=row["transcript"],
        audio_uri=row["audio_uri"],
        metadata=row["metadata"],
        created_at=row["created_at"],
    )


def _agent_message_from_row(row: dict[str, Any]) -> AgentMessage:
    return AgentMessage(
        message_id=row["message_id"],
        run_id=row["run_id"],
        sender_agent_id=row["sender_agent_id"],
        recipient_agent_id=row["recipient_agent_id"],
        task_type=row["task_type"],
        payload=row["payload"],
        depends_on_message_ids=row.get("depends_on_message_ids") or [],
        requires_human_feedback=row["requires_human_feedback"],
        status=AgentTaskStatus(row["status"]),
        claimed_by_agent_id=row["claimed_by_agent_id"],
        attempt_count=row.get("attempt_count", 0),
        max_attempts=row.get("max_attempts", 3),
        result=row["result"],
        handoff_trace=row.get("handoff_trace") or [],
        error=row["error"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _artifact_from_row(row: dict[str, Any]) -> ArtifactRecord:
    return ArtifactRecord(
        artifact_id=row["artifact_id"],
        run_id=row["run_id"],
        artifact_type=row["artifact_type"],
        title=row["title"],
        uri=row["uri"],
        content=row["content"],
        provenance=row["provenance"],
        source_ids=row["source_ids"],
        reviewer_decisions=row["reviewer_decisions"],
        revision_history=row["revision_history"],
        created_at=row["created_at"],
    )


def _realtime_session_from_row(row: dict[str, Any]) -> RealtimeSessionRecord:
    metadata = row["metadata"] or {}
    return RealtimeSessionRecord(
        realtime_session_id=row["realtime_session_id"],
        run_id=row["run_id"],
        provider=row["provider"],
        provider_session_id=row["provider_session_id"],
        voice=row["voice"],
        audio_mode=row["audio_mode"],
        instructions=row["instructions"],
        has_client_secret=row["has_client_secret"],
        has_websocket_url=row["has_websocket_url"],
        transport_framework=metadata.get("transport_framework"),
        room_name=metadata.get("room_name"),
        participant_identity=metadata.get("participant_identity"),
        agent_participant_identity=metadata.get("agent_participant_identity"),
        has_transport_token=bool(metadata.get("has_transport_token")),
        context_window_turns=int(metadata.get("context_window_turns") or 4),
        summarize_after_turns=int(metadata.get("summarize_after_turns") or 3),
        expires_at_unix=row["expires_at_unix"],
        status=RealtimeSessionStatus(row["status"]),
        metadata=metadata,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _realtime_session_metadata(session: RealtimeSessionRecord) -> dict[str, Any]:
    metadata = dict(session.metadata or {})
    metadata.update(
        {
            "transport_framework": session.transport_framework,
            "room_name": session.room_name,
            "participant_identity": session.participant_identity,
            "agent_participant_identity": session.agent_participant_identity,
            "has_transport_token": session.has_transport_token,
            "context_window_turns": session.context_window_turns,
            "summarize_after_turns": session.summarize_after_turns,
        }
    )
    return metadata


def _vector_literal(embedding: list[float] | None) -> str | None:
    if embedding is None:
        return None
    return "[" + ",".join(str(float(value)) for value in embedding) + "]"


def _parse_vector(value: str | None) -> list[float] | None:
    if not value:
        return None
    stripped = value.strip("[]")
    if not stripped:
        return []
    return [float(part) for part in stripped.split(",")]


def _worker_profile_from_row(row: dict[str, Any]) -> WorkerProfile:
    return WorkerProfile(
        profile_id=row["profile_id"],
        run_id=row["run_id"],
        name=row["name"],
        execution_mode=WorkerProfileExecutionMode(
            row.get("execution_mode") or WorkerProfileExecutionMode.WORKER_CYCLE.value
        ),
        agent_ids=row["agent_ids"],
        max_tasks_per_agent=row["max_tasks_per_agent"],
        max_rounds=row["max_rounds"],
        poll_interval_seconds=row["poll_interval_seconds"],
        include_global_memories=row["include_global_memories"],
        memory_limit=row["memory_limit"],
        autonomous_auto_refresh_research_sources=row.get(
            "autonomous_auto_refresh_research_sources",
            True,
        ),
        autonomous_block_on_research_freshness_blocked=row.get(
            "autonomous_block_on_research_freshness_blocked",
            True,
        ),
        autonomous_block_on_retrieval_quality_blocked=row.get(
            "autonomous_block_on_retrieval_quality_blocked",
            True,
        ),
        autonomous_export_memory_summary_to_obsidian=row.get(
            "autonomous_export_memory_summary_to_obsidian",
            False,
        ),
        autonomous_memory_summary_agent_id=row.get(
            "autonomous_memory_summary_agent_id"
        ),
        autonomous_memory_summary_limit=row.get(
            "autonomous_memory_summary_limit",
            8,
        ),
        use_gemma=row["use_gemma"],
        fail_on_provider_error=row["fail_on_provider_error"],
        status=WorkerProfileStatus(row["status"]),
        last_heartbeat_at=row["last_heartbeat_at"],
        heartbeat_claimed_at=row.get("heartbeat_claimed_at"),
        heartbeat_claimed_by=row.get("heartbeat_claimed_by"),
        heartbeat_lease_until=row.get("heartbeat_lease_until"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
