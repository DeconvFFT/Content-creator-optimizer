import asyncio
from datetime import datetime, timedelta, timezone

from all_about_llms.contracts import (
    ArtifactType,
    RealtimeSessionRecord,
    RealtimeVoiceTimingLedgerRequest,
    RunEvent,
    RunState,
)
from all_about_llms.orchestration import RealtimeVoiceTimingLedgerWorkflow


class TimingFakeStore:
    def __init__(self):
        self.run = RunState(goal="Measure Gemma/Kokoro realtime voice")
        self.events: list[RunEvent] = []
        self.artifacts = []
        self.realtime_sessions = []

    async def get_run(self, run_id):
        if run_id == self.run.run_id:
            return self.run
        return None

    async def list_realtime_sessions(self, run_id):
        return [
            session for session in self.realtime_sessions if session.run_id == run_id
        ]

    async def list_events(self, run_id, limit=100, after_event_id=None):
        events = [event for event in self.events if event.run_id == run_id]
        if after_event_id is not None:
            events = [
                event
                for event in events
                if event.event_id is not None and event.event_id > after_event_id
            ]
        return events[:limit]

    async def record_artifact(self, artifact):
        self.artifacts.append(artifact)
        self.run.artifact_ids.append(artifact.artifact_id)
        return artifact

    async def append_event(self, event):
        event.event_id = len(self.events) + 1
        self.events.append(event)
        return event

    async def record_realtime_session(self, session):
        self.realtime_sessions.append(session)
        return session


def test_realtime_voice_timing_ledger_measures_complete_voice_loop():
    store = TimingFakeStore()
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)

    async def run():
        session = await store.record_realtime_session(
            RealtimeSessionRecord(
                run_id=store.run.run_id,
                provider="gemma4_realtime",
                provider_session_id="gemma4-livekit-complete",
                voice="af_heart",
                instructions="Use Gemma 4 audio understanding and Kokoro speech.",
                transport_framework="livekit",
                room_name="voice-measurement-room",
                agent_participant_identity="gemma-kokoro-agent",
            )
        )
        event_specs = [
            (
                "gemma_kokoro_voice_agent_ready",
                0,
                {"realtime_session_id": str(session.realtime_session_id)},
            ),
            (
                "voice_agent_media_bridge_ready",
                20,
                {
                    "realtime_session_id": str(session.realtime_session_id),
                    "participant_identity": "creator",
                    "media_bridge": "livekit_audio_track_to_rust_voice_edge",
                    "voice_edge_enabled": True,
                    "voice_edge_process_mode": "persistent_jsonl",
                },
            ),
            (
                "voice_user_speech_started",
                50,
                {"realtime_session_id": str(session.realtime_session_id)},
            ),
            (
                "voice_user_turn_committed",
                400,
                {
                    "realtime_session_id": str(session.realtime_session_id),
                    "turn_id": "turn-1",
                    "audio_duration_ms": 350,
                    "windowing": "rust_voice_edge_vad_silence",
                },
            ),
            (
                "gemma_kokoro_voice_turn_started",
                420,
                {
                    "realtime_session_id": str(session.realtime_session_id),
                    "turn_id": "turn-1",
                    "response_id": "response-1",
                },
            ),
            (
                "gemma_generation_started",
                500,
                {
                    "realtime_session_id": str(session.realtime_session_id),
                    "turn_id": "turn-1",
                    "response_id": "response-1",
                },
            ),
            (
                "assistant_text_delta",
                620,
                {
                    "realtime_session_id": str(session.realtime_session_id),
                    "turn_id": "turn-1",
                    "response_id": "response-1",
                    "text": "Here",
                },
            ),
            (
                "assistant_audio_chunk_published",
                880,
                {
                    "realtime_session_id": str(session.realtime_session_id),
                    "turn_id": "turn-1",
                    "response_id": "response-1",
                    "pcm_bytes": 6400,
                },
            ),
            (
                "voice_edge_cancellation_acknowledged",
                1000,
                {
                    "realtime_session_id": str(session.realtime_session_id),
                    "turn_id": "turn-1",
                    "response_id": "response-1",
                },
            ),
            (
                "gemma_kokoro_voice_turn_cancelled",
                1038,
                {
                    "realtime_session_id": str(session.realtime_session_id),
                    "turn_id": "turn-1",
                    "response_id": "response-1",
                },
            ),
        ]
        for event_type, offset_ms, payload in event_specs:
            await store.append_event(
                RunEvent(
                    run_id=store.run.run_id,
                    event_type=event_type,
                    actor="gemma-kokoro-livekit-agent",
                    payload=payload,
                    created_at=now + timedelta(milliseconds=offset_ms),
                )
            )
        return await RealtimeVoiceTimingLedgerWorkflow(store).build(
            store.run.run_id,
            RealtimeVoiceTimingLedgerRequest(record_artifact=True),
        )

    result = asyncio.run(run())

    assert result.status == "ready"
    assert result.session_count == 1
    assert result.measured_stage_count == 8
    assert result.missing_stage_count == 0
    stages = {stage.stage_id: stage for stage in result.stages}
    assert stages["livekit_audio_track_bridge"].status == "measured"
    assert stages["end_of_turn_to_agent_turn"].latency_ms == 20
    assert stages["gemma_response_start"].latency_ms == 80
    assert stages["first_audio_out"].latency_ms == 380
    assert stages["barge_in_to_audio_stop"].latency_ms == 38
    assert len(result.turns) == 1
    turn = result.turns[0]
    assert turn.speech_start_to_turn_commit_ms == 350
    assert turn.turn_commit_to_agent_turn_ms == 20
    assert turn.speech_start_to_turn_start_ms == 370
    assert turn.turn_start_to_first_audio_ms == 460
    assert turn.barge_in_to_cancelled_ms == 38
    assert result.ledger_artifact_id is not None
    assert store.artifacts[-1].artifact_type == ArtifactType.REALTIME_VOICE_TIMING_LEDGER
    assert store.artifacts[-1].provenance["workflow"] == (
        "realtime_voice_timing_ledger_v1"
    )
    assert store.events[-1].event_type == "realtime_voice_timing_ledger_built"


def test_realtime_voice_timing_ledger_requires_media_bridge_proof():
    store = TimingFakeStore()
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)

    async def run():
        session = await store.record_realtime_session(
            RealtimeSessionRecord(
                run_id=store.run.run_id,
                provider="gemma4_realtime",
                provider_session_id="gemma4-livekit-without-media-bridge",
                voice="af_heart",
                instructions="Use Gemma 4 audio understanding and Kokoro speech.",
                transport_framework="livekit",
                room_name="voice-measurement-room",
                agent_participant_identity="gemma-kokoro-agent",
            )
        )
        event_specs = [
            ("gemma_kokoro_voice_agent_ready", 0, {}),
            ("voice_user_speech_started", 50, {}),
            (
                "voice_user_turn_committed",
                400,
                {"turn_id": "turn-1", "audio_duration_ms": 350},
            ),
            (
                "gemma_kokoro_voice_turn_started",
                420,
                {"turn_id": "turn-1", "response_id": "response-1"},
            ),
            (
                "gemma_generation_started",
                500,
                {"turn_id": "turn-1", "response_id": "response-1"},
            ),
            (
                "assistant_audio_chunk_published",
                880,
                {"turn_id": "turn-1", "response_id": "response-1"},
            ),
            (
                "voice_edge_cancellation_acknowledged",
                1000,
                {"turn_id": "turn-1", "response_id": "response-1"},
            ),
            (
                "gemma_kokoro_voice_turn_cancelled",
                1038,
                {"turn_id": "turn-1", "response_id": "response-1"},
            ),
        ]
        for event_type, offset_ms, payload in event_specs:
            await store.append_event(
                RunEvent(
                    run_id=store.run.run_id,
                    event_type=event_type,
                    actor="gemma-kokoro-livekit-agent",
                    payload={
                        "realtime_session_id": str(session.realtime_session_id),
                        **payload,
                    },
                    created_at=now + timedelta(milliseconds=offset_ms),
                )
            )
        return await RealtimeVoiceTimingLedgerWorkflow(store).build(
            store.run.run_id,
            RealtimeVoiceTimingLedgerRequest(record_artifact=False),
        )

    result = asyncio.run(run())

    stages = {stage.stage_id: stage for stage in result.stages}
    assert result.status == "needs_more_evidence"
    assert stages["livekit_audio_track_bridge"].status == "missing"
    assert any(
        "voice_agent_media_bridge_ready" in action
        for action in result.recommended_next_actions
    )


def test_realtime_voice_timing_ledger_rejects_stale_or_late_media_bridge_proof():
    store = TimingFakeStore()
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)

    async def run():
        older_session = await store.record_realtime_session(
            RealtimeSessionRecord(
                run_id=store.run.run_id,
                provider="gemma4_realtime",
                provider_session_id="older-complete-session",
                voice="af_heart",
                instructions="Use Gemma 4 audio understanding and Kokoro speech.",
                transport_framework="livekit",
                room_name="older-room",
                agent_participant_identity="gemma-kokoro-agent",
                created_at=now,
            )
        )
        current_session = await store.record_realtime_session(
            RealtimeSessionRecord(
                run_id=store.run.run_id,
                provider="gemma4_realtime",
                provider_session_id="current-session",
                voice="af_heart",
                instructions="Use Gemma 4 audio understanding and Kokoro speech.",
                transport_framework="livekit",
                room_name="current-room",
                agent_participant_identity="gemma-kokoro-agent",
                created_at=now + timedelta(seconds=10),
            )
        )

        def payload(session, extra=None):
            return {
                "realtime_session_id": str(session.realtime_session_id),
                **(extra or {}),
            }

        old_specs = [
            ("gemma_kokoro_voice_agent_ready", 0, {}),
            ("voice_agent_media_bridge_ready", 20, {}),
            ("voice_user_speech_started", 50, {}),
            ("voice_user_turn_committed", 400, {"turn_id": "old-turn"}),
            (
                "gemma_kokoro_voice_turn_started",
                420,
                {"turn_id": "old-turn", "response_id": "old-response"},
            ),
            (
                "gemma_generation_started",
                500,
                {"turn_id": "old-turn", "response_id": "old-response"},
            ),
            (
                "assistant_audio_chunk_published",
                880,
                {"turn_id": "old-turn", "response_id": "old-response"},
            ),
            (
                "voice_edge_cancellation_acknowledged",
                1000,
                {"turn_id": "old-turn", "response_id": "old-response"},
            ),
            (
                "gemma_kokoro_voice_turn_cancelled",
                1038,
                {"turn_id": "old-turn", "response_id": "old-response"},
            ),
        ]
        current_specs = [
            ("gemma_kokoro_voice_agent_ready", 10_000, {}),
            ("voice_user_speech_started", 10_050, {}),
            ("voice_user_turn_committed", 10_400, {"turn_id": "current-turn"}),
            (
                "gemma_kokoro_voice_turn_started",
                10_420,
                {"turn_id": "current-turn", "response_id": "current-response"},
            ),
            (
                "gemma_generation_started",
                10_500,
                {"turn_id": "current-turn", "response_id": "current-response"},
            ),
            (
                "assistant_audio_chunk_published",
                10_880,
                {"turn_id": "current-turn", "response_id": "current-response"},
            ),
            (
                "voice_edge_cancellation_acknowledged",
                11_000,
                {"turn_id": "current-turn", "response_id": "current-response"},
            ),
            (
                "gemma_kokoro_voice_turn_cancelled",
                11_038,
                {"turn_id": "current-turn", "response_id": "current-response"},
            ),
            (
                "voice_agent_media_bridge_ready",
                11_100,
                {"media_bridge": "late_after_speech"},
            ),
        ]
        for event_type, offset_ms, extra in old_specs:
            await store.append_event(
                RunEvent(
                    run_id=store.run.run_id,
                    event_type=event_type,
                    actor="gemma-kokoro-livekit-agent",
                    payload=payload(older_session, extra),
                    created_at=now + timedelta(milliseconds=offset_ms),
                )
            )
        for event_type, offset_ms, extra in current_specs:
            await store.append_event(
                RunEvent(
                    run_id=store.run.run_id,
                    event_type=event_type,
                    actor="gemma-kokoro-livekit-agent",
                    payload=payload(current_session, extra),
                    created_at=now + timedelta(milliseconds=offset_ms),
                )
            )
        return await RealtimeVoiceTimingLedgerWorkflow(store).build(
            store.run.run_id,
            RealtimeVoiceTimingLedgerRequest(record_artifact=False),
        )

    result = asyncio.run(run())

    stages = {stage.stage_id: stage for stage in result.stages}
    assert result.status == "needs_more_evidence"
    assert stages["livekit_audio_track_bridge"].status == "missing"
    assert result.turns[0].realtime_session_id == store.realtime_sessions[-1].realtime_session_id
    assert any(
        "voice_agent_media_bridge_ready" in action
        for action in result.recommended_next_actions
    )


def test_realtime_voice_timing_ledger_regresses_incomplete_audio_and_barge_in():
    store = TimingFakeStore()
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)

    async def run():
        session = await store.record_realtime_session(
            RealtimeSessionRecord(
                run_id=store.run.run_id,
                provider="gemma4_realtime",
                provider_session_id="gemma4-livekit-incomplete",
                voice="af_heart",
                instructions="Use Gemma 4 audio understanding and Kokoro speech.",
                transport_framework="livekit",
                room_name="voice-measurement-room",
            )
        )
        for event_type, offset_ms, payload in [
            (
                "gemma_kokoro_voice_agent_ready",
                0,
                {"realtime_session_id": str(session.realtime_session_id)},
            ),
            (
                "voice_user_speech_started",
                50,
                {"realtime_session_id": str(session.realtime_session_id)},
            ),
            (
                "voice_user_turn_committed",
                400,
                {
                    "realtime_session_id": str(session.realtime_session_id),
                    "turn_id": "turn-1",
                    "audio_duration_ms": 350,
                    "windowing": "rust_voice_edge_vad_silence",
                },
            ),
            (
                "gemma_kokoro_voice_turn_started",
                420,
                {
                    "realtime_session_id": str(session.realtime_session_id),
                    "turn_id": "turn-1",
                    "response_id": "response-1",
                },
            ),
            (
                "gemma_generation_started",
                500,
                {
                    "realtime_session_id": str(session.realtime_session_id),
                    "turn_id": "turn-1",
                    "response_id": "response-1",
                },
            ),
        ]:
            await store.append_event(
                RunEvent(
                    run_id=store.run.run_id,
                    event_type=event_type,
                    actor="gemma-kokoro-livekit-agent",
                    payload=payload,
                    created_at=now + timedelta(milliseconds=offset_ms),
                )
            )
        return await RealtimeVoiceTimingLedgerWorkflow(store).build(
            store.run.run_id,
            RealtimeVoiceTimingLedgerRequest(record_artifact=False),
        )

    result = asyncio.run(run())

    assert result.status == "needs_more_evidence"
    stages = {stage.stage_id: stage for stage in result.stages}
    assert stages["first_audio_out"].status == "partial"
    assert stages["barge_in_to_audio_stop"].status == "missing"
    assert any(
        "assistant_audio_chunk_published" in action
        for action in result.recommended_next_actions
    )
    assert any(
        "voice-turn-cancelled" in action or "cancellation" in action
        for action in result.recommended_next_actions
    )
    assert not store.artifacts
    assert store.events[-1].event_type == "realtime_voice_timing_ledger_built"


def test_realtime_voice_timing_ledger_surfaces_provider_failed_turn():
    store = TimingFakeStore()
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)

    async def run():
        session = await store.record_realtime_session(
            RealtimeSessionRecord(
                run_id=store.run.run_id,
                provider="gemma4_realtime",
                provider_session_id="gemma4-livekit-failed",
                voice="af_heart",
                instructions="Use Gemma 4 audio understanding and Kokoro speech.",
                transport_framework="livekit",
                room_name="voice-measurement-room",
            )
        )
        event_specs = [
            (
                "gemma_kokoro_voice_agent_ready",
                0,
                {"realtime_session_id": str(session.realtime_session_id)},
            ),
            (
                "voice_user_turn_committed",
                200,
                {
                    "realtime_session_id": str(session.realtime_session_id),
                    "turn_id": "turn-failed",
                    "windowing": "livekit_data_transcript",
                },
            ),
            (
                "gemma_kokoro_voice_turn_started",
                220,
                {
                    "realtime_session_id": str(session.realtime_session_id),
                    "turn_id": "turn-failed",
                    "response_id": "response-failed",
                },
            ),
            (
                "gemma_generation_started",
                250,
                {
                    "realtime_session_id": str(session.realtime_session_id),
                    "turn_id": "turn-failed",
                    "response_id": "response-failed",
                },
            ),
            (
                "gemma_kokoro_voice_turn_failed",
                330,
                {
                    "realtime_session_id": str(session.realtime_session_id),
                    "turn_id": "turn-failed",
                    "response_id": "response-failed",
                    "failure_stage": "gemma_generation",
                    "failure_reason": "Gemma 4 streaming request failed.",
                    "assistant_text_chars": 0,
                    "audio_chunk_count": 0,
                },
            ),
        ]
        for event_type, offset_ms, payload in event_specs:
            await store.append_event(
                RunEvent(
                    run_id=store.run.run_id,
                    event_type=event_type,
                    actor="gemma-kokoro-livekit-agent",
                    payload=payload,
                    created_at=now + timedelta(milliseconds=offset_ms),
                )
            )
        return await RealtimeVoiceTimingLedgerWorkflow(store).build(
            store.run.run_id,
            RealtimeVoiceTimingLedgerRequest(record_artifact=False),
        )

    result = asyncio.run(run())

    assert result.status == "failed"
    stages = {stage.stage_id: stage for stage in result.stages}
    assert stages["voice_turn_failed"].status == "failed"
    assert "Gemma 4 streaming request failed." in stages["voice_turn_failed"].evidence[0]
    assert any("Fix the OpenRouter/Kokoro provider route" in action for action in result.recommended_next_actions)
    assert result.turns[0].failure_stage == "gemma_generation"
    assert result.turns[0].failure_reason == "Gemma 4 streaming request failed."


def test_realtime_voice_timing_ledger_rejects_mismatched_barge_in_response_ids():
    store = TimingFakeStore()
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)

    async def run():
        session = await store.record_realtime_session(
            RealtimeSessionRecord(
                run_id=store.run.run_id,
                provider="gemma4_realtime",
                provider_session_id="gemma4-livekit-mismatch",
                voice="af_heart",
                instructions="Use Gemma 4 audio understanding and Kokoro speech.",
                transport_framework="livekit",
                room_name="voice-measurement-room",
            )
        )
        event_specs = [
            ("gemma_kokoro_voice_agent_ready", 0, {}),
            ("voice_user_speech_started", 50, {}),
            (
                "voice_user_turn_committed",
                400,
                {"turn_id": "turn-1", "audio_duration_ms": 350},
            ),
            (
                "gemma_kokoro_voice_turn_started",
                420,
                {"turn_id": "turn-1", "response_id": "response-1"},
            ),
            (
                "gemma_generation_started",
                500,
                {"turn_id": "turn-1", "response_id": "response-1"},
            ),
            (
                "assistant_text_delta",
                620,
                {"turn_id": "turn-1", "response_id": "response-1"},
            ),
            (
                "assistant_audio_chunk_published",
                880,
                {"turn_id": "turn-1", "response_id": "response-1"},
            ),
            (
                "voice_edge_cancellation_acknowledged",
                1000,
                {"turn_id": "turn-2", "response_id": "response-2"},
            ),
            (
                "gemma_kokoro_voice_turn_cancelled",
                1038,
                {"turn_id": "turn-3", "response_id": "response-3"},
            ),
        ]
        for event_type, offset_ms, payload in event_specs:
            await store.append_event(
                RunEvent(
                    run_id=store.run.run_id,
                    event_type=event_type,
                    actor="gemma-kokoro-livekit-agent",
                    payload={
                        "realtime_session_id": str(session.realtime_session_id),
                        **payload,
                    },
                    created_at=now + timedelta(milliseconds=offset_ms),
                )
            )
        return await RealtimeVoiceTimingLedgerWorkflow(store).build(
            store.run.run_id,
            RealtimeVoiceTimingLedgerRequest(record_artifact=False),
        )

    result = asyncio.run(run())

    stages = {stage.stage_id: stage for stage in result.stages}
    assert result.status == "needs_more_evidence"
    assert stages["first_audio_out"].status == "measured"
    assert stages["barge_in_to_audio_stop"].status == "missing"
