import asyncio
import json
from datetime import datetime, timezone
from uuid import UUID

from all_about_llms.config import Settings
from all_about_llms.contracts import RealtimeSessionRecord, RunEvent, RunState
from all_about_llms.orchestration.livekit_voice_timing_capture import (
    HeadlessLiveKitAgentEvent,
    HeadlessLiveKitCaptureInput,
    HeadlessLiveKitCaptureResult,
    LiveKitVoiceTimingCaptureRequest,
    LiveKitVoiceTimingCaptureWorkflow,
    _capture_pcm_frame,
    _queue_agent_text_stream_event,
    _wait_for_agent_presence,
)
from all_about_llms.cli import _livekit_voice_timing_capture_request_from_args
from all_about_llms.voice_agent.control_binding import (
    verify_livekit_control_binding_token,
)


RUN_ID = UUID("190ae2f9-a74b-4a23-b39c-aaf2d636bd8e")
SESSION_ID = UUID("ebd43531-86e3-4af1-ade0-15ac8d7184bf")


class FakeCaptureStore:
    def __init__(self, *, existing_duplicate_uid: str | None = None):
        self.run = RunState(run_id=RUN_ID, goal="Capture voice timing proof")
        self.session = RealtimeSessionRecord(
            realtime_session_id=SESSION_ID,
            run_id=RUN_ID,
            provider="openrouter_livekit",
            provider_session_id="openrouter-livekit-190ae2f9",
            voice="af_heart",
            instructions="Proof capture session",
            transport_framework="livekit",
            room_name="proof-room",
            participant_identity="creator-proof",
            agent_participant_identity="openrouter-kokoro-agent",
            has_transport_token=True,
            metadata={
                "control_binding_token_issued": True,
                "smoke_proof_status": "provider_backed",
            },
        )
        self.events: list[RunEvent] = []
        if existing_duplicate_uid:
            self.events.append(
                RunEvent(
                    event_id=1,
                    run_id=RUN_ID,
                    event_type="voice_user_speech_started",
                    actor="gemma-kokoro-livekit-agent",
                    payload={"voice_agent_event_uid": existing_duplicate_uid},
                )
            )
        self.next_event_id = len(self.events) + 1

    async def get_run(self, run_id):
        return self.run if run_id == RUN_ID else None

    async def list_realtime_sessions(self, run_id):
        return [self.session] if run_id == RUN_ID else []

    async def find_event_by_voice_agent_event_uid(
        self, run_id, event_type, voice_agent_event_uid
    ):
        for event in self.events:
            if (
                event.run_id == run_id
                and event.event_type == event_type
                and event.payload.get("voice_agent_event_uid")
                == voice_agent_event_uid
            ):
                return event
        return None

    async def append_event(self, event: RunEvent):
        event.event_id = self.next_event_id
        self.next_event_id += 1
        self.events.append(event)
        return event


class FakeHeadlessClient:
    def __init__(self, events: list[HeadlessLiveKitAgentEvent]):
        self.events = events
        self.capture_inputs = []

    async def capture(self, capture_input, on_agent_event):
        self.capture_inputs.append(capture_input)
        for event in self.events:
            await on_agent_event(event)
        return HeadlessLiveKitCaptureResult(
            connected=True,
            audio_probe_published=True,
            transcript_turn_sent=True,
            interrupt_sent=True,
            observed_agent_event_types=[event.event_type for event in self.events],
            observed_response_id="response-1",
            summary="fake capture complete",
        )


def _agent_event(event_type: str, uid: str, **payload):
    return HeadlessLiveKitAgentEvent(
        event_type=event_type,
        payload={
            "voice_agent_event_uid": uid,
            "room_name": "proof-room",
            **payload,
        },
        created_at=datetime.now(timezone.utc),
        sender_identity="openrouter-kokoro-agent",
        topic="agent.voice.event",
    )


def test_capture_pcm_frame_writes_raw_pcm_bytes_into_livekit_audio_frame():
    class FakeAudioSource:
        def __init__(self):
            self.frames = []

        async def capture_frame(self, frame):
            self.frames.append(bytes(frame.data.cast("B")))

    source = FakeAudioSource()
    payload = b"\x01\x00" * 160

    asyncio.run(
        _capture_pcm_frame(
            source,
            payload,
            sample_rate=16_000,
            frame_ms=10,
        )
    )

    assert source.frames[0][: len(payload)] == payload


def test_headless_capture_reads_livekit_text_stream_agent_events():
    class FakeStreamInfo:
        topic = "agent.voice.event"

    class FakeTextReader:
        info = FakeStreamInfo()

        async def read_all(self):
            return json.dumps(
                {
                    "event_type": "gemma_kokoro_voice_agent_ready",
                    "voice_agent_event_uid": "uid-ready",
                    "payload": {
                        "room_name": "proof-room",
                    },
                    "created_at": "2026-05-24T00:00:00+00:00",
                }
            )

    async def run():
        queue = asyncio.Queue()
        await _queue_agent_text_stream_event(
            FakeTextReader(),
            participant_identity="openrouter-kokoro-agent",
            queue=queue,
        )
        return await queue.get()

    event = asyncio.run(run())

    assert event.event_type == "gemma_kokoro_voice_agent_ready"
    assert event.payload["voice_agent_event_uid"] == "uid-ready"
    assert event.sender_identity == "openrouter-kokoro-agent"
    assert event.topic == "agent.voice.event"


def test_wait_for_agent_presence_retries_until_agent_event_arrives():
    queue = asyncio.Queue()

    class FakeLocalParticipant:
        def __init__(self):
            self.payloads = []

        async def publish_data(self, data, *, reliable, topic):
            self.payloads.append(
                {
                    "payload": json.loads(data.decode("utf-8")),
                    "reliable": reliable,
                    "topic": topic,
                }
            )
            if len(self.payloads) == 2:
                queue.put_nowait(
                    _agent_event("gemma_kokoro_voice_agent_ready", "uid-ready")
                )

    class FakeRoom:
        def __init__(self):
            self.local_participant = FakeLocalParticipant()

    capture_input = HeadlessLiveKitCaptureInput(
        run_id=RUN_ID,
        realtime_session_id=SESSION_ID,
        livekit_url="ws://127.0.0.1:7880",
        livekit_token="token",
        control_binding_token="binding",
        room_name="proof-room",
        participant_identity="creator-proof",
        agent_identity="openrouter-kokoro-agent",
        agent_name="openrouter-kokoro-agent",
        timeout_seconds=1.0,
        audio_probe_duration_ms=0,
        post_speech_silence_ms=0,
        interrupt_on_first_output=True,
        sample_rate=16_000,
        frame_ms=10,
    )
    room = FakeRoom()

    asyncio.run(
        _wait_for_agent_presence(
            room,
            capture_input,
            queue,
            timeout_seconds=0.2,
            interval_seconds=0.01,
        )
    )

    assert len(room.local_participant.payloads) == 2
    assert all(
        published["payload"]["type"] == "voice_agent_presence_probe"
        for published in room.local_participant.payloads
    )
    assert queue.get_nowait().event_type == "gemma_kokoro_voice_agent_ready"


def test_headless_livekit_capture_persists_data_channel_events_without_backend():
    events = [
        _agent_event("voice_agent_media_bridge_ready", "uid-bridge"),
        _agent_event("voice_user_speech_started", "uid-speech", turn_id="turn-1"),
        _agent_event(
            "voice_user_turn_committed",
            "uid-commit",
            turn_id="turn-1",
            transcript="Synthetic speech probe.",
        ),
        _agent_event(
            "gemma_kokoro_voice_turn_cancelled",
            "uid-cancel",
            turn_id="turn-1",
            response_id="response-1",
        ),
    ]
    store = FakeCaptureStore()
    client = FakeHeadlessClient(events)
    settings = Settings(
        livekit_api_key="devkey",
        livekit_api_secret="livekit-secret",
        openrouter_livekit_url="ws://127.0.0.1:7880",
    )
    workflow = LiveKitVoiceTimingCaptureWorkflow(
        store,
        settings=settings,
        client_factory=lambda: client,
    )

    result = asyncio.run(
        workflow.capture(
            RUN_ID,
            LiveKitVoiceTimingCaptureRequest(realtime_session_id=SESSION_ID),
        )
    )

    assert result.status == "captured"
    assert result.realtime_session_id == SESSION_ID
    assert result.captured_event_count == 4
    assert result.skipped_duplicate_event_count == 0
    assert result.captured_event_types == [
        "voice_agent_media_bridge_ready",
        "voice_user_speech_started",
        "voice_user_turn_committed",
        "gemma_kokoro_voice_turn_cancelled",
    ]
    assert [event.event_type for event in store.events] == result.captured_event_types
    assert all(
        event.payload["voice_agent_event_source"] == "livekit_headless_capture"
        for event in store.events
    )
    assert all(
        event.payload["realtime_session_id"] == str(SESSION_ID)
        for event in store.events
    )
    capture_input = client.capture_inputs[0]
    assert capture_input.room_name == "proof-room"
    assert capture_input.participant_identity == "creator-proof"
    assert capture_input.agent_identity == "openrouter-kokoro-agent"
    assert capture_input.livekit_url == "ws://127.0.0.1:7880"
    assert capture_input.livekit_token
    assert verify_livekit_control_binding_token(
        capture_input.control_binding_token,
        "livekit-secret",
        run_id=str(RUN_ID),
        realtime_session_id=str(SESSION_ID),
        room_name="proof-room",
        participant_identity="creator-proof",
        agent_identity="openrouter-kokoro-agent",
    )
    serialized = result.model_dump_json()
    assert "livekit-secret" not in serialized
    assert "livekit_token" not in serialized
    assert capture_input.livekit_token not in serialized


def test_headless_livekit_capture_deduplicates_agent_event_uids():
    duplicate = _agent_event("voice_user_speech_started", "uid-speech")
    fresh = _agent_event("voice_user_turn_committed", "uid-commit", turn_id="turn-1")
    store = FakeCaptureStore(existing_duplicate_uid="uid-speech")
    client = FakeHeadlessClient([duplicate, fresh])
    workflow = LiveKitVoiceTimingCaptureWorkflow(
        store,
        settings=Settings(
            livekit_api_key="devkey",
            livekit_api_secret="livekit-secret",
            openrouter_livekit_url="ws://127.0.0.1:7880",
        ),
        client_factory=lambda: client,
    )

    result = asyncio.run(
        workflow.capture(
            RUN_ID,
            LiveKitVoiceTimingCaptureRequest(realtime_session_id=SESSION_ID),
        )
    )

    assert result.status == "captured"
    assert result.captured_event_types == ["voice_user_turn_committed"]
    assert result.captured_event_count == 1
    assert result.skipped_duplicate_event_count == 1
    assert [event.event_type for event in store.events] == [
        "voice_user_speech_started",
        "voice_user_turn_committed",
    ]


def test_livekit_voice_timing_capture_cli_builds_operator_request():
    class Args:
        realtime_session_id = str(SESSION_ID)
        timeout_seconds = 12.5
        audio_probe_duration_ms = 1600
        post_speech_silence_ms = 700
        no_interrupt = True
        transcript = "Operator supplied proof transcript."
        voice = "af_heart"

    request = _livekit_voice_timing_capture_request_from_args(Args())

    assert request == LiveKitVoiceTimingCaptureRequest(
        realtime_session_id=SESSION_ID,
        timeout_seconds=12.5,
        audio_probe_duration_ms=1600,
        post_speech_silence_ms=700,
        interrupt_on_first_output=False,
        transcript="Operator supplied proof transcript.",
        voice="af_heart",
    )
