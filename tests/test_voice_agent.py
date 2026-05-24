import asyncio
import hashlib
import json
import os
import sys
import types
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from all_about_llms.config import PROJECT_ROOT, Settings
from all_about_llms.contracts import VoiceAgentProcessStatus
from all_about_llms.providers.interfaces import GemmaResponse, ProviderConfigurationError
from all_about_llms.voice_agent import (
    GemmaKokoroLiveKitAgentEngine,
    RealtimeVoiceAgentConfig,
    RealtimeVoiceAgentEvent,
    RealtimeVoiceTurnInput,
    VoiceConversationTurn,
)
from all_about_llms.voice_agent.adapters import (
    BackendRealtimeVoiceEventSink,
    CompositeVoiceAgentEventSink,
    HuggingFaceGemmaAudioReasoner,
    HuggingFaceKokoroTTSStreamer,
    LiveKitDataEventSink,
    LocalKokoroTTSStreamer,
)
from all_about_llms.voice_agent.control_binding import (
    build_livekit_control_binding_token,
)
from all_about_llms.voice_agent.engine import InMemoryVoiceAgentEventSink
from all_about_llms.voice_agent.engine import VoiceAgentCancellationToken
from all_about_llms.voice_agent.edge import (
    FallbackVoiceEdgeClient,
    RustVoiceEdgeHttpClient,
    VoiceEdgeAnalysisResult,
    VoiceEdgeClient,
)
from all_about_llms.voice_agent.readiness import (
    _client_vad_metadata,
    _normalized_backend_event_sink_url,
    _preflight_backend_event_sink,
    _selected_preflight_transport,
)
from all_about_llms.voice_agent.livekit_app import (
    MAX_CANCELLED_RESPONSE_IDS,
    LiveKitVoiceAgentSessionState,
    VoiceTurnCaptureBuffer,
    _build_voice_agent_event_sink,
    _build_voice_edge_client,
    _build_kokoro_streamer,
    _build_voice_audio_turn,
    _cleanup_expired_voice_audio_artifacts,
    _emit_voice_turn_committed,
    _emit_voice_edge_events,
    _emit_startup_ready_for_bound_session,
    _handle_data_message,
    _handle_data_message_serialized,
    _handle_audio_track,
    _has_voice_edge_event,
    _latest_vad_is_speech,
    _preflight_voice_edge_client,
    _remember_cancelled_response_id,
    _register_voice_edge_cleanup,
    _should_forward_voice_edge_event,
    _voice_agent_media_bridge_payload,
)
from all_about_llms.voice_agent.supervisor import LocalVoiceAgentSupervisor


ROOT = Path(__file__).resolve().parents[1]


def test_livekit_agent_uses_dedicated_gemma_audio_endpoint_not_primary_fallback():
    source = (ROOT / "src/all_about_llms/voice_agent/livekit_app.py").read_text()

    assert "gemma_audio_endpoint_url(settings)" in source
    assert "or settings.gemma4_primary_endpoint_url" not in source


def test_backend_event_sink_url_normalization_rejects_unsafe_urls():
    assert (
        _normalized_backend_event_sink_url(" http://127.0.0.1:8000/ ")
        == "http://127.0.0.1:8000"
    )
    assert (
        _normalized_backend_event_sink_url("http://[::1]:8000/")
        == "http://[::1]:8000"
    )
    with pytest.raises(ValueError, match="credentials"):
        _normalized_backend_event_sink_url("http://user:pass@127.0.0.1:8000")
    with pytest.raises(ValueError, match="path"):
        _normalized_backend_event_sink_url("http://127.0.0.1:8000/api")
    with pytest.raises(ValueError, match="query"):
        _normalized_backend_event_sink_url("http://127.0.0.1:8000?token=secret")
    with pytest.raises(ValueError, match="port"):
        _normalized_backend_event_sink_url("http://127.0.0.1:bad")
    with pytest.raises(ValueError, match="http"):
        _normalized_backend_event_sink_url("ws://127.0.0.1:8000")


def test_backend_event_sink_timeout_settings_are_bounded():
    assert Settings(voice_agent_backend_event_sink_timeout_seconds="2").voice_agent_backend_event_sink_timeout_seconds == 2
    with pytest.raises(ValueError, match="positive"):
        Settings(voice_agent_backend_event_sink_timeout_seconds=0)
    with pytest.raises(ValueError, match="<= 30"):
        Settings(voice_agent_backend_event_sink_timeout_seconds=60)


def test_backend_event_sink_preflight_reports_health_metadata():
    asyncio.run(_assert_backend_event_sink_preflight_reports_health_metadata())


async def _assert_backend_event_sink_preflight_reports_health_metadata():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/health"
        return httpx.Response(
            200,
            json={"status": "ok", "database": "postgres", "vector_store": "pgvector"},
            request=request,
        )

    result = await _preflight_backend_event_sink(
        base_url="http://127.0.0.1:8000",
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )

    assert result["ok"] is True
    assert result["metadata"]["health_status"] == "ok"
    assert result["metadata"]["database"] == "postgres"
    assert result["metadata"]["vector_store"] == "pgvector"


@pytest.mark.asyncio
async def test_local_voice_agent_supervisor_redacts_secret_log_tail():
    supervisor = LocalVoiceAgentSupervisor(
        Settings(
            hf_token="hf-secret-token",
            livekit_api_key="livekit-key",
            livekit_api_secret="livekit-secret",
        )
    )

    supervisor._append_log(
        "startup failed with hf-secret-token livekit-key livekit-secret"
    )

    status = await supervisor.status()
    assert status.log_tail == "startup failed with [redacted] [redacted] [redacted]".splitlines()
    assert "secret" not in str(status.log_tail).lower()


class FakeSupervisorProcess:
    pid = 9876
    stdout = None

    def __init__(self):
        self.returncode = None
        self.terminated = False
        self.killed = False

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9

    async def wait(self):
        return self.returncode


class FakeSupervisorRaceProcess(FakeSupervisorProcess):
    def terminate(self):
        self.terminated = True
        raise ProcessLookupError("already exited")

    async def wait(self):
        self.returncode = 0
        return self.returncode


class FakeUnstoppableSupervisorProcess(FakeSupervisorProcess):
    def terminate(self):
        self.terminated = True

    async def wait(self):
        raise asyncio.TimeoutError

    def kill(self):
        self.killed = True
        raise OSError("permission denied")


@pytest.mark.asyncio
async def test_local_voice_agent_supervisor_stop_is_not_reported_as_failure():
    supervisor = LocalVoiceAgentSupervisor(Settings())
    process = FakeSupervisorProcess()
    supervisor._process = process

    status = await supervisor.stop()

    assert process.terminated is True
    assert process.killed is False
    assert status.status == VoiceAgentProcessStatus.STOPPED
    assert status.running is False
    assert status.returncode == -15
    assert "failed" not in status.summary.lower()


@pytest.mark.asyncio
async def test_local_voice_agent_supervisor_stop_handles_exit_race():
    supervisor = LocalVoiceAgentSupervisor(Settings())
    process = FakeSupervisorRaceProcess()
    supervisor._process = process

    status = await supervisor.stop()

    assert process.terminated is True
    assert status.status == VoiceAgentProcessStatus.STOPPED
    assert status.running is False
    assert status.returncode == 0
    assert "already exited" not in str(status.log_tail).lower()


@pytest.mark.asyncio
async def test_local_voice_agent_supervisor_stop_race_keeps_running_state():
    supervisor = LocalVoiceAgentSupervisor(Settings())
    process = FakeUnstoppableSupervisorProcess()
    supervisor._process = process

    status = await supervisor.stop()

    assert process.terminated is True
    assert process.killed is True
    assert status.status == VoiceAgentProcessStatus.RUNNING
    assert status.running is True
    assert status.returncode is None
    assert status.last_error is not None
    assert "permission denied" in status.last_error
    assert "Retry Stop agent." in status.next_actions


class FakeGemmaReasoner:
    def __init__(self, deltas: list[str]):
        self.deltas = deltas
        self.context_turns: list[VoiceConversationTurn] = []

    async def stream_text(self, turn, context_turns, cancellation):
        self.context_turns = context_turns
        for delta in self.deltas:
            cancellation.throw_if_cancelled()
            yield delta


class FakeGemmaProvider:
    def __init__(self, content: str = "fallback answer"):
        self.content = content
        self.requests = []

    async def complete(self, request):
        self.requests.append(request)
        return GemmaResponse(
            model_id=request.model_id,
            agent_id=request.agent_id,
            content=self.content,
        )


class BlockingGemmaReasoner:
    def __init__(self):
        self.started = asyncio.Event()

    async def stream_text(self, turn, context_turns, cancellation):
        self.started.set()
        yield "partial response that should be cancelled"
        while not cancellation.canceled:
            await asyncio.sleep(0.01)
        cancellation.throw_if_cancelled()


class FailingGemmaReasoner:
    async def stream_text(self, turn, context_turns, cancellation):
        del turn, context_turns, cancellation
        raise ProviderConfigurationError("Gemma 4 streaming request failed.")
        yield


class FakeKokoroStreamer:
    def __init__(self):
        self.fragments: list[str] = []

    async def stream_audio(self, *, response_id, text, voice, cancellation):
        self.fragments.append(text)
        cancellation.throw_if_cancelled()
        yield f"pcm:{voice}:{text}".encode("utf-8")


class FailingKokoroStreamer:
    async def stream_audio(self, *, response_id, text, voice, cancellation):
        del response_id, text, voice, cancellation
        raise ProviderConfigurationError("Kokoro TTS request failed.")
        yield


class FakeLiveKitPublisher:
    def __init__(self):
        self.chunks = []
        self.cleared: list[str] = []
        self.stopped: list[str] = []

    async def publish_audio_chunk(self, chunk):
        self.chunks.append(chunk)

    async def clear_output_buffer(self, response_id: str):
        self.cleared.append(response_id)

    async def stop_response_audio(self, response_id: str):
        self.stopped.append(response_id)


class FakeShutdownContext:
    def __init__(self):
        self.callbacks = []

    def add_shutdown_callback(self, callback):
        self.callbacks.append(callback)


class FakeClosableVoiceEdgeClient:
    transport = "fake"

    def __init__(self):
        self.closed_count = 0

    async def aclose(self):
        self.closed_count += 1


class FakeAvailableVoiceEdgeClient(VoiceEdgeClient):
    transport = "persistent_jsonl"

    def __init__(self):
        super().__init__()
        self.health_checks = 0

    async def health_check(self):
        self.health_checks += 1
        return {"status": "ok", "transport": self.transport}

    async def _run(self, payload):
        raise AssertionError("preflight should not execute fallback requests")


class FailingHealthHttpVoiceEdgeClient(RustVoiceEdgeHttpClient):
    def __init__(self):
        super().__init__(base_url="http://127.0.0.1:7071", timeout_seconds=1.0)
        self.closed = False

    async def health_check(self):
        raise RuntimeError("sidecar unavailable")

    async def aclose(self):
        self.closed = True


class HealthyHealthHttpVoiceEdgeClient(RustVoiceEdgeHttpClient):
    def __init__(self, **kwargs):
        super().__init__(base_url="http://127.0.0.1:7071", timeout_seconds=1.0, **kwargs)
        self.health_checks = 0

    async def health_check(self):
        self.health_checks += 1
        return {"status": "ok", "transport": self.transport}


class FailingCloseHealthHttpVoiceEdgeClient(FailingHealthHttpVoiceEdgeClient):
    async def aclose(self):
        raise RuntimeError("close failed")


class FailingHealthPersistentVoiceEdgeClient(VoiceEdgeClient):
    transport = "persistent_jsonl"

    def __init__(self):
        super().__init__()
        self.closed = False

    async def health_check(self):
        raise RuntimeError("jsonl preflight failed")

    async def aclose(self):
        self.closed = True

    async def _run(self, payload):
        raise AssertionError("preflight should not run payloads in this fake")


class FlakyClosableVoiceEdgeClient:
    transport = "fake"

    def __init__(self):
        self.close_attempts = 0

    async def aclose(self):
        self.close_attempts += 1
        if self.close_attempts == 1:
            raise RuntimeError("cleanup failed")


class FakeSSEStreamResponse:
    def __init__(self, lines: list[str]):
        self.lines = lines
        self.raise_called = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def raise_for_status(self):
        self.raise_called = True

    async def aiter_lines(self):
        for line in self.lines:
            yield line


class FakeStreamingHttpClient:
    requests = []
    lines = [
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        'data: {"choices":[{"delta":{"content":" world"}}]}',
        "data: [DONE]",
    ]

    def __init__(self, timeout):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def stream(self, method, url, headers, json):
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": self.timeout,
            }
        )
        return FakeSSEStreamResponse(self.lines)


def _streaming_reasoner_with_transport(
    transport: httpx.AsyncBaseTransport,
) -> HuggingFaceGemmaAudioReasoner:
    return HuggingFaceGemmaAudioReasoner(
        provider=FakeGemmaProvider(content="should not be used"),
        config=RealtimeVoiceAgentConfig(gemma_stream_timeout_seconds=12.5),
        endpoint_url="https://hf.example/v1/chat/completions",
        token="hf-test-token",
        transport=transport,
    )


def _voice_turn() -> RealtimeVoiceTurnInput:
    return RealtimeVoiceTurnInput(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity="creator",
        transcript="Create a quick source-backed answer.",
    )


def _control_binding_token(
    *,
    run_id,
    realtime_session_id,
    room_name: str = "agent-studio-room",
    participant_identity: str = "creator-bound",
    agent_identity: str = "agent-runtime-identity",
    secret: str = "livekit-secret",
) -> str:
    token = build_livekit_control_binding_token(
        secret,
        run_id=str(run_id),
        realtime_session_id=str(realtime_session_id),
        room_name=room_name,
        participant_identity=participant_identity,
        agent_identity=agent_identity,
    )
    assert token is not None
    return token


async def _drain_active_turn_tasks(state: LiveKitVoiceAgentSessionState) -> None:
    tasks = list(state.active_turn_tasks)
    if tasks:
        await asyncio.wait_for(asyncio.gather(*tasks), timeout=1.0)


class CapturingVoiceEventSink:
    def __init__(self):
        self.events: list[RealtimeVoiceAgentEvent] = []

    async def emit(self, event):
        self.events.append(event)


class FailingVoiceEventSink:
    async def emit(self, event):
        del event
        raise RuntimeError("backend sink unavailable")


HF_SECRET = "hf_" + ("A" * 40)
TAVILY_SECRET = "tvly-dev-" + ("B" * 40)
BEARER_SECRET = "Bearer " + ("C" * 40)


def test_backend_voice_event_sink_posts_stable_uid_without_raw_secrets():
    asyncio.run(_assert_backend_voice_event_sink_posts_stable_uid_without_raw_secrets())


async def _assert_backend_voice_event_sink_posts_stable_uid_without_raw_secrets():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"event_id": 42}, request=request)

    event = RealtimeVoiceAgentEvent(
        event_type="assistant_text_delta",
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        payload={
            "turn_id": "turn-1",
            "response_id": "response-1",
            "text_delta": "Hello",
        },
        voice_agent_event_uid="voice-event-stable-1",
    )
    sink = BackendRealtimeVoiceEventSink(
        base_url="http://127.0.0.1:8000/",
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )

    await sink.emit(event)

    assert len(requests) == 1
    request = requests[0]
    assert request.url.path == (
        f"/api/realtime-sessions/{event.realtime_session_id}/voice-events"
    )
    body = json.loads(request.content)
    assert body["event_type"] == "assistant_text_delta"
    assert body["voice_agent_event_uid"] == "voice-event-stable-1"
    assert body["source"] == "livekit_agent_http_sink"
    assert body["payload"]["voice_agent_event_uid"] == "voice-event-stable-1"
    assert "Authorization" not in request.headers


def test_backend_voice_event_sink_redacts_runtime_secrets_before_posting():
    asyncio.run(_assert_backend_voice_event_sink_redacts_runtime_secrets_before_posting())


async def _assert_backend_voice_event_sink_redacts_runtime_secrets_before_posting():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"event_id": 42}, request=request)

    event = RealtimeVoiceAgentEvent(
        event_type="voice_edge_transport_fallback",
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        payload={
            "error": f"primary failed with {BEARER_SECRET} {HF_SECRET}",
            "apiKey": "raw-api-key-value",
            "nested": {
                "clientSecret": "raw-client-secret-value",
                "safe_error": f"search failed with {TAVILY_SECRET}",
            },
            "events": [
                {
                    "authorization": BEARER_SECRET,
                    "safe_error": f"provider returned {HF_SECRET}",
                }
            ],
            "has_token": True,
            "token": None,
        },
        voice_agent_event_uid="voice-event-stable-secret-1",
    )
    sink = BackendRealtimeVoiceEventSink(
        base_url="http://127.0.0.1:8000/",
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )

    await sink.emit(event)

    body = json.loads(requests[0].content)
    serialized = json.dumps(body)
    assert HF_SECRET not in serialized
    assert TAVILY_SECRET not in serialized
    assert BEARER_SECRET not in serialized
    assert "raw-api-key-value" not in serialized
    assert "raw-client-secret-value" not in serialized
    assert "Bearer [redacted]" in serialized
    assert "hf_[redacted]" in serialized
    assert "tvly-[redacted]" in serialized
    assert "apiKey" not in body["payload"]
    assert "clientSecret" not in body["payload"]["nested"]
    assert "authorization" not in body["payload"]["events"][0]
    assert body["payload"]["has_token"] is True
    assert body["payload"]["token"] is None


def test_livekit_data_event_sink_redacts_runtime_secrets_before_broadcast():
    asyncio.run(_assert_livekit_data_event_sink_redacts_runtime_secrets_before_broadcast())


async def _assert_livekit_data_event_sink_redacts_runtime_secrets_before_broadcast():
    class FakeLocalParticipant:
        def __init__(self):
            self.messages: list[tuple[str, str]] = []

        async def send_text(self, payload, *, topic):
            self.messages.append((payload, topic))

    class FakeRoom:
        def __init__(self):
            self.local_participant = FakeLocalParticipant()

    room = FakeRoom()
    sink = LiveKitDataEventSink(room=room, topic="agent.voice.event")
    event = RealtimeVoiceAgentEvent(
        event_type="voice_runtime_error",
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        payload={
            "error": f"provider rejected {BEARER_SECRET}",
            "signedUrl": "https://example.test/audio?token=raw-token",
            "nested": {"safe_error": f"hf failed: {HF_SECRET}"},
        },
        voice_agent_event_uid="voice-event-stable-secret-2",
    )

    await sink.emit(event)

    assert len(room.local_participant.messages) == 1
    message, topic = room.local_participant.messages[0]
    assert topic == "agent.voice.event"
    serialized = json.dumps(json.loads(message))
    assert HF_SECRET not in serialized
    assert BEARER_SECRET not in serialized
    assert "raw-token" not in serialized
    assert "Bearer [redacted]" in serialized
    assert "hf_[redacted]" in serialized
    payload = json.loads(message)["payload"]
    assert "signedUrl" not in payload


def test_backend_voice_event_sink_rejects_unsafe_base_url():
    with pytest.raises(ValueError, match="credentials"):
        BackendRealtimeVoiceEventSink(
            base_url="http://user:pass@127.0.0.1:8000",
            timeout_seconds=1.0,
        )


def test_livekit_event_sink_falls_back_when_backend_sink_url_is_invalid():
    sink = _build_voice_agent_event_sink(
        room=object(),
        settings=Settings(
            voice_agent_backend_event_sink_enabled=True,
            voice_agent_backend_event_sink_url="http://user:pass@127.0.0.1:8000",
        ),
    )

    assert isinstance(sink, LiveKitDataEventSink)


def test_composite_voice_event_sink_keeps_livekit_path_when_backend_fails():
    asyncio.run(_assert_composite_voice_event_sink_keeps_livekit_path_when_backend_fails())


async def _assert_composite_voice_event_sink_keeps_livekit_path_when_backend_fails():
    livekit_sink = CapturingVoiceEventSink()
    event = RealtimeVoiceAgentEvent(
        event_type="gemma_generation_started",
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        payload={"turn_id": "turn-1", "response_id": "response-1"},
    )
    sink = CompositeVoiceAgentEventSink(
        required=[livekit_sink],
        best_effort=[FailingVoiceEventSink()],
    )

    await sink.emit(event)

    assert livekit_sink.events == [event]


def test_gemma_kokoro_engine_prunes_old_raw_audio_and_streams_audio():
    asyncio.run(_assert_gemma_kokoro_engine_prunes_old_raw_audio_and_streams_audio())


async def _assert_gemma_kokoro_engine_prunes_old_raw_audio_and_streams_audio():
    gemma = FakeGemmaReasoner(["Here is the answer."])
    kokoro = FakeKokoroStreamer()
    publisher = FakeLiveKitPublisher()
    sink = InMemoryVoiceAgentEventSink()
    config = RealtimeVoiceAgentConfig(
        context_window_turns=6,
        prune_after_turns=3,
        tts_flush_chars=60,
    )
    engine = GemmaKokoroLiveKitAgentEngine(
        config=config,
        gemma=gemma,
        kokoro=kokoro,
        publisher=publisher,
        event_sink=sink,
    )
    history = [
        VoiceConversationTurn(
            turn_id=f"old-{index}",
            role="user",
            text=f"old transcript {index}",
            audio_ref=f"s3://raw-audio/{index}.pcm",
            audio_duration_ms=1000,
        )
        for index in range(5)
    ]
    turn = RealtimeVoiceTurnInput(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity="creator",
        transcript="fresh user turn",
        audio_ref="livekit://turn/current",
        audio_pcm=b"raw-audio-bytes-must-not-enter-events",
        audio_duration_ms=900,
    )

    result = await engine.handle_turn(turn, history, voice="af_heart")

    assert result.context_pruned is True
    assert result.raw_audio_turns_before == 6
    assert result.raw_audio_turns_after == 3
    assert result.assistant_text == "Here is the answer."
    assert result.audio_chunk_count == 1
    assert publisher.chunks[0].sample_rate == 16000
    assert kokoro.fragments == ["Here is the answer."]
    assert sum(1 for item in gemma.context_turns if item.audio_ref) == 3
    assert all(item.audio_ref is None for item in gemma.context_turns[:3])
    assert "voice_context_pruned" in {event.event_type for event in sink.events}
    completed_event = next(
        event for event in sink.events if event.event_type == "assistant_response_completed"
    )
    delta_event = next(
        event for event in sink.events if event.event_type == "assistant_text_delta"
    )
    assert delta_event.payload["text_delta"] == "Here is the answer."
    assert delta_event.payload["delta_chars"] == len("Here is the answer.")
    assert completed_event.payload["assistant_text"] == "Here is the answer."
    assert completed_event.payload["assistant_text_chars"] == len("Here is the answer.")
    pruned_event = next(
        event for event in sink.events if event.event_type == "voice_context_pruned"
    )
    assert pruned_event.payload["replacement_strategy"] == "transcript_plus_summary"
    assert "raw-audio-bytes-must-not-enter-events" not in str(
        [event.payload for event in sink.events]
    )


def test_gemma_kokoro_engine_records_gemma_provider_failure_without_crashing():
    asyncio.run(
        _assert_gemma_kokoro_engine_records_gemma_provider_failure_without_crashing()
    )


async def _assert_gemma_kokoro_engine_records_gemma_provider_failure_without_crashing():
    publisher = FakeLiveKitPublisher()
    sink = InMemoryVoiceAgentEventSink()
    engine = GemmaKokoroLiveKitAgentEngine(
        config=RealtimeVoiceAgentConfig(),
        gemma=FailingGemmaReasoner(),
        kokoro=FakeKokoroStreamer(),
        publisher=publisher,
        event_sink=sink,
    )
    turn = _voice_turn()

    result = await engine.handle_turn(turn, [], voice="af_heart")

    assert result.failed is True
    assert result.failure_stage == "gemma_generation"
    assert result.assistant_text == ""
    assert result.audio_chunk_count == 0
    assert publisher.chunks == []
    assert publisher.cleared == [result.response_id]
    assert publisher.stopped == [result.response_id]
    event_types = {item.event_type for item in sink.events}
    assert "assistant_response_completed" not in event_types
    event = next(
        item
        for item in sink.events
        if item.event_type == "gemma_kokoro_voice_turn_failed"
    )
    assert event.payload["failure_stage"] == "gemma_generation"
    assert event.payload["assistant_text_chars"] == 0
    assert event.payload["audio_chunk_count"] == 0
    assert event.payload["clear_kokoro_buffers"] is True
    assert event.payload["stop_livekit_audio"] is True
    assert event.payload["failure_reason"] == "Gemma 4 streaming request failed."


def test_gemma_kokoro_engine_records_kokoro_provider_failure_without_publishing_audio():
    asyncio.run(
        _assert_gemma_kokoro_engine_records_kokoro_provider_failure_without_publishing_audio()
    )


async def _assert_gemma_kokoro_engine_records_kokoro_provider_failure_without_publishing_audio():
    publisher = FakeLiveKitPublisher()
    sink = InMemoryVoiceAgentEventSink()
    engine = GemmaKokoroLiveKitAgentEngine(
        config=RealtimeVoiceAgentConfig(tts_flush_chars=10),
        gemma=FakeGemmaReasoner(["Hello there."]),
        kokoro=FailingKokoroStreamer(),
        publisher=publisher,
        event_sink=sink,
    )
    turn = _voice_turn()

    result = await engine.handle_turn(turn, [], voice="af_heart")

    assert result.failed is True
    assert result.failure_stage == "kokoro_tts"
    assert result.assistant_text == "Hello there."
    assert result.audio_chunk_count == 0
    assert publisher.chunks == []
    assert publisher.cleared == [result.response_id]
    assert publisher.stopped == [result.response_id]
    event_types = {item.event_type for item in sink.events}
    assert "assistant_response_completed" not in event_types
    event = next(
        item
        for item in sink.events
        if item.event_type == "gemma_kokoro_voice_turn_failed"
    )
    assert event.payload["failure_stage"] == "kokoro_tts"
    assert event.payload["assistant_text_chars"] == len("Hello there.")
    assert event.payload["audio_chunk_count"] == 0
    assert event.payload["failure_reason"] == "Kokoro TTS request failed."


def test_hf_gemma_audio_reasoner_streams_sse_deltas_to_kokoro(monkeypatch):
    asyncio.run(_assert_hf_gemma_audio_reasoner_streams_sse_deltas(monkeypatch))


async def _assert_hf_gemma_audio_reasoner_streams_sse_deltas(monkeypatch):
    from all_about_llms.voice_agent import adapters

    FakeStreamingHttpClient.requests = []
    monkeypatch.setattr(adapters.httpx, "AsyncClient", FakeStreamingHttpClient)
    provider = FakeGemmaProvider(content="should not be used")
    reasoner = HuggingFaceGemmaAudioReasoner(
        provider=provider,
        config=RealtimeVoiceAgentConfig(gemma_stream_timeout_seconds=12.5),
        endpoint_url="https://hf.example/v1/chat/completions",
        token="hf-test-token",
    )
    turn = RealtimeVoiceTurnInput(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity="creator",
        audio_ref="artifact://voice-audio/run/session/turn.pcm",
        audio_pcm=b"audio",
        audio_duration_ms=32,
    )

    deltas = [
        delta
        async for delta in reasoner.stream_text(
            turn,
            [],
            VoiceAgentCancellationToken("response-1"),
        )
    ]

    assert deltas == ["Hello", " world"]
    assert provider.requests == []
    request = FakeStreamingHttpClient.requests[0]
    assert request["method"] == "POST"
    assert request["url"] == "https://hf.example/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer hf-test-token"
    assert request["headers"]["Accept"] == "text/event-stream"
    assert request["timeout"] == 12.5
    assert request["json"]["stream"] is True
    assert request["json"]["model"] == "google/gemma-4-E4B-it"
    user_content = request["json"]["messages"][1]["content"]
    assert user_content[0]["type"] == "audio"
    assert user_content[0]["audio_base64"] == "YXVkaW8="
    assert "audio" not in user_content[0]
    assert user_content[-1]["type"] == "text"


def test_hf_gemma_audio_reasoner_wraps_stream_http_failures():
    asyncio.run(_assert_hf_gemma_audio_reasoner_wraps_stream_http_failures())


async def _assert_hf_gemma_audio_reasoner_wraps_stream_http_failures():
    reasoner = _streaming_reasoner_with_transport(
        httpx.MockTransport(lambda request: httpx.Response(503, request=request))
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="Gemma 4 streaming request failed",
    ):
        [
            delta
            async for delta in reasoner.stream_text(
                _voice_turn(),
                [],
                VoiceAgentCancellationToken("response-1"),
            )
        ]


def test_hf_gemma_audio_reasoner_wraps_stream_network_failures_without_secret_leak():
    asyncio.run(
        _assert_hf_gemma_audio_reasoner_wraps_stream_network_failures_without_secret_leak()
    )


async def _assert_hf_gemma_audio_reasoner_wraps_stream_network_failures_without_secret_leak():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    reasoner = _streaming_reasoner_with_transport(httpx.MockTransport(handler))

    with pytest.raises(
        ProviderConfigurationError,
        match="Gemma 4 streaming request failed",
    ) as exc:
        [
            delta
            async for delta in reasoner.stream_text(
                _voice_turn(),
                [],
                VoiceAgentCancellationToken("response-1"),
            )
        ]

    assert "hf-test-token" not in str(exc.value)


def test_hf_gemma_audio_reasoner_blocks_empty_streaming_payloads():
    asyncio.run(_assert_hf_gemma_audio_reasoner_blocks_empty_streaming_payloads())


async def _assert_hf_gemma_audio_reasoner_blocks_empty_streaming_payloads():
    reasoner = _streaming_reasoner_with_transport(
        httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=b"data: {\"choices\":[{\"delta\":{}}]}\n\ndata: [DONE]\n\n",
                headers={"content-type": "text/event-stream"},
                request=request,
            )
        )
    )

    with pytest.raises(ProviderConfigurationError, match="no usable text"):
        [
            delta
            async for delta in reasoner.stream_text(
                _voice_turn(),
                [],
                VoiceAgentCancellationToken("response-1"),
            )
        ]


def test_hf_gemma_audio_reasoner_blocks_whitespace_only_streaming_payloads():
    asyncio.run(
        _assert_hf_gemma_audio_reasoner_blocks_whitespace_only_streaming_payloads()
    )


async def _assert_hf_gemma_audio_reasoner_blocks_whitespace_only_streaming_payloads():
    reasoner = _streaming_reasoner_with_transport(
        httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=(
                    b"data: {\"choices\":[{\"delta\":{\"content\":\"   \"}}]}\n\n"
                    b"data: [DONE]\n\n"
                ),
                headers={"content-type": "text/event-stream"},
                request=request,
            )
        )
    )

    with pytest.raises(ProviderConfigurationError, match="no usable text"):
        [
            delta
            async for delta in reasoner.stream_text(
                _voice_turn(),
                [],
                VoiceAgentCancellationToken("response-1"),
            )
        ]


def test_hf_gemma_audio_reasoner_falls_back_when_streaming_disabled():
    asyncio.run(_assert_hf_gemma_audio_reasoner_falls_back_when_streaming_disabled())


async def _assert_hf_gemma_audio_reasoner_falls_back_when_streaming_disabled():
    provider = FakeGemmaProvider(content="completed fallback")
    reasoner = HuggingFaceGemmaAudioReasoner(
        provider=provider,
        config=RealtimeVoiceAgentConfig(gemma_streaming_enabled=False),
        endpoint_url="https://hf.example/v1/chat/completions",
        token="hf-test-token",
    )
    turn = RealtimeVoiceTurnInput(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity="creator",
        transcript="Use the normal provider path.",
    )

    deltas = [
        delta
        async for delta in reasoner.stream_text(
            turn,
            [],
            VoiceAgentCancellationToken("response-1"),
        )
    ]

    assert deltas == ["completed fallback"]
    assert len(provider.requests) == 1
    assert provider.requests[0].metadata["source"] == (
        "gemma_kokoro_livekit_voice_agent"
    )


def test_hf_kokoro_tts_streamer_maps_hosted_audio_payload_without_network():
    asyncio.run(_assert_hf_kokoro_tts_streamer_maps_hosted_audio_payload_without_network())


async def _assert_hf_kokoro_tts_streamer_maps_hosted_audio_payload_without_network():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer hf-test-token"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["model"] == "hexgrad/Kokoro-82M"
        assert payload["inputs"] == "Speak this."
        assert payload["parameters"]["voice"] == "af_heart"
        return httpx.Response(
            200,
            json={"audio_base64": "cGNt"},
            request=request,
        )

    streamer = HuggingFaceKokoroTTSStreamer(
        token="hf-test-token",
        endpoint_url="https://hf.test/kokoro",
        chunk_bytes=8,
        transport=httpx.MockTransport(handler),
    )

    chunks = [
        chunk
        async for chunk in streamer.stream_audio(
            response_id="response-1",
            text="Speak this.",
            voice=None,
            cancellation=VoiceAgentCancellationToken("response-1"),
        )
    ]

    assert chunks == [b"pcm"]


def test_hf_kokoro_tts_streamer_wraps_http_failures():
    asyncio.run(_assert_hf_kokoro_tts_streamer_wraps_http_failures())


async def _assert_hf_kokoro_tts_streamer_wraps_http_failures():
    streamer = HuggingFaceKokoroTTSStreamer(
        token="hf-test-token",
        endpoint_url="https://hf.test/kokoro",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(500, request=request)
        ),
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="Kokoro TTS request failed",
    ):
        [
            chunk
            async for chunk in streamer.stream_audio(
                response_id="response-1",
                text="Speak this.",
                voice=None,
                cancellation=VoiceAgentCancellationToken("response-1"),
            )
        ]


@pytest.mark.parametrize(
    ("response", "match"),
    [
        (
            httpx.Response(
                200,
                content=b"not json",
                headers={"content-type": "application/json"},
            ),
            "invalid JSON",
        ),
        (
            httpx.Response(200, json={"audio_base64": "not-valid-base64"}),
            "invalid base64",
        ),
        (
            httpx.Response(
                200,
                content=b"",
                headers={"content-type": "audio/wav"},
            ),
            "did not return audio bytes",
        ),
    ],
)
def test_hf_kokoro_tts_streamer_blocks_malformed_audio_payloads(response, match):
    asyncio.run(
        _assert_hf_kokoro_tts_streamer_blocks_malformed_audio_payloads(
            response,
            match,
        )
    )


async def _assert_hf_kokoro_tts_streamer_blocks_malformed_audio_payloads(
    response: httpx.Response,
    match: str,
):
    streamer = HuggingFaceKokoroTTSStreamer(
        token="hf-test-token",
        endpoint_url="https://hf.test/kokoro",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                response.status_code,
                content=response.content,
                headers=response.headers,
                request=request,
            )
        ),
    )

    with pytest.raises(ProviderConfigurationError, match=match):
        [
            chunk
            async for chunk in streamer.stream_audio(
                response_id="response-1",
                text="Speak this.",
                voice=None,
                cancellation=VoiceAgentCancellationToken("response-1"),
            )
        ]


def test_livekit_voice_agent_presence_probe_emits_ready_ack():
    asyncio.run(_assert_livekit_voice_agent_presence_probe_emits_ready_ack())


def test_livekit_voice_agent_presence_probe_binds_uninitialized_session_state():
    asyncio.run(_assert_livekit_voice_agent_presence_probe_binds_uninitialized_session_state())


async def _assert_livekit_voice_agent_presence_probe_binds_uninitialized_session_state():
    sink = InMemoryVoiceAgentEventSink()
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity=None,
    )
    expected_run_id = uuid4()
    expected_session_id = uuid4()
    config = RealtimeVoiceAgentConfig()
    engine = GemmaKokoroLiveKitAgentEngine(
        config=config,
        gemma=FakeGemmaReasoner(["unused"]),
        kokoro=FakeKokoroStreamer(),
        publisher=FakeLiveKitPublisher(),
        event_sink=sink,
    )

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(
            {
                "type": "voice_agent_presence_probe",
                "probe_id": "probe-bind",
                "run_id": str(expected_run_id),
                "realtime_session_id": str(expected_session_id),
                "room_name": "agent-studio-room",
                "expected_agent_identity": "agent-runtime-identity",
                "control_binding_token": _control_binding_token(
                    run_id=expected_run_id,
                    realtime_session_id=expected_session_id,
                ),
            }
        ).encode("utf-8"),
        participant_identity="creator-bound",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(
            livekit_agent_name="gemma4-kokoro-agent",
            livekit_api_secret="livekit-secret",
        ),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )

    assert state.run_id == expected_run_id
    assert state.realtime_session_id == expected_session_id
    assert state.participant_identity == "creator-bound"
    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.event_type == "gemma_kokoro_voice_agent_ready"
    assert event.run_id == expected_run_id
    assert event.realtime_session_id == expected_session_id
    assert event.payload["presence_probe_ack"] is True
    assert event.payload["source"] == "presence_probe"


def test_livekit_voice_agent_rejects_uninitialized_binding_without_trust_proof():
    asyncio.run(_assert_livekit_voice_agent_rejects_uninitialized_binding_without_trust_proof())


async def _assert_livekit_voice_agent_rejects_uninitialized_binding_without_trust_proof():
    sink = InMemoryVoiceAgentEventSink()
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity=None,
    )
    original_run_id = state.run_id
    original_session_id = state.realtime_session_id
    config = RealtimeVoiceAgentConfig()
    engine = GemmaKokoroLiveKitAgentEngine(
        config=config,
        gemma=FakeGemmaReasoner(["unused"]),
        kokoro=FakeKokoroStreamer(),
        publisher=FakeLiveKitPublisher(),
        event_sink=sink,
    )
    expected_run_id = uuid4()
    expected_session_id = uuid4()
    base_payload = {
        "type": "voice_agent_presence_probe",
        "probe_id": "probe-rejected",
        "run_id": str(expected_run_id),
        "realtime_session_id": str(expected_session_id),
        "room_name": "agent-studio-room",
        "control_binding_token": _control_binding_token(
            run_id=expected_run_id,
            realtime_session_id=expected_session_id,
        ),
    }

    for payload in [
        {key: value for key, value in base_payload.items() if key != "control_binding_token"},
        {**base_payload, "expected_agent_identity": "wrong-agent"},
        {**base_payload, "expected_agent_identity": "agent-runtime-identity", "room_name": "other-room"},
        {**base_payload, "expected_agent_identity": "agent-runtime-identity", "run_id": "not-a-uuid"},
        {**base_payload, "expected_agent_identity": "agent-runtime-identity", "realtime_session_id": "not-a-uuid"},
        {
            **base_payload,
            "expected_agent_identity": "agent-runtime-identity",
            "control_binding_token": _control_binding_token(
                run_id=uuid4(),
                realtime_session_id=expected_session_id,
            ),
        },
    ]:
        await _handle_data_message(
            engine=engine,
            state=state,
            payload=json.dumps(payload).encode("utf-8"),
            participant_identity="creator-bound",
            topic="agent.voice.control",
            event_sink=sink,
            config=config,
            settings=Settings(
                livekit_agent_name="gemma4-kokoro-agent",
                livekit_api_secret="livekit-secret",
            ),
            voice_edge=None,
            agent_participant_identity="agent-runtime-identity",
        )

    valid_payload = {**base_payload, "expected_agent_identity": "agent-runtime-identity"}
    for bad_identity in ["", "unknown", "other-participant"]:
        await _handle_data_message(
            engine=engine,
            state=state,
            payload=json.dumps(valid_payload).encode("utf-8"),
            participant_identity=bad_identity,
            topic="agent.voice.control",
            event_sink=sink,
            config=config,
            settings=Settings(
                livekit_agent_name="gemma4-kokoro-agent",
                livekit_api_secret="livekit-secret",
            ),
            voice_edge=None,
            agent_participant_identity="agent-runtime-identity",
        )

    assert state.run_id == original_run_id
    assert state.realtime_session_id == original_session_id
    assert state.participant_identity is None
    assert sink.events == []


def test_livekit_transcript_turn_binds_uninitialized_session_state():
    asyncio.run(_assert_livekit_transcript_turn_binds_uninitialized_session_state())


async def _assert_livekit_transcript_turn_binds_uninitialized_session_state():
    sink = InMemoryVoiceAgentEventSink()
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity=None,
    )
    expected_run_id = uuid4()
    expected_session_id = uuid4()
    turn_id = str(uuid4())
    config = RealtimeVoiceAgentConfig(tts_flush_chars=8)
    engine = GemmaKokoroLiveKitAgentEngine(
        config=config,
        gemma=FakeGemmaReasoner(["Bound answer."]),
        kokoro=FakeKokoroStreamer(),
        publisher=FakeLiveKitPublisher(),
        event_sink=sink,
    )

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(
            {
                "type": "transcript_turn",
                "turn_id": turn_id,
                "run_id": str(expected_run_id),
                "realtime_session_id": str(expected_session_id),
                "room_name": "agent-studio-room",
                "expected_agent_identity": "agent-runtime-identity",
                "control_binding_token": _control_binding_token(
                    run_id=expected_run_id,
                    realtime_session_id=expected_session_id,
                ),
                "transcript": "Use this live text turn to bind the session.",
                "voice": "af_heart",
            }
        ).encode("utf-8"),
        participant_identity="creator-bound",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(
            livekit_agent_name="gemma4-kokoro-agent",
            livekit_api_secret="livekit-secret",
        ),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    await _drain_active_turn_tasks(state)

    assert state.run_id == expected_run_id
    assert state.realtime_session_id == expected_session_id
    assert state.participant_identity == "creator-bound"
    assert state.voice == "af_heart"
    assert state.history[0].turn_id == turn_id
    assert state.history[0].text == "Use this live text turn to bind the session."
    assert state.history[1].text == "Bound answer."
    assert "voice_user_turn_committed" in {event.event_type for event in sink.events}
    assert "assistant_response_completed" in {event.event_type for event in sink.events}


async def _assert_livekit_voice_agent_presence_probe_emits_ready_ack():
    sink = InMemoryVoiceAgentEventSink()
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity="creator",
    )
    config = RealtimeVoiceAgentConfig()
    engine = GemmaKokoroLiveKitAgentEngine(
        config=config,
        gemma=FakeGemmaReasoner(["unused"]),
        kokoro=FakeKokoroStreamer(),
        publisher=FakeLiveKitPublisher(),
        event_sink=sink,
    )

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(
            {
                "type": "voice_agent_presence_probe",
                "probe_id": "probe-1",
                "run_id": str(state.run_id),
                "realtime_session_id": str(state.realtime_session_id),
            }
        ).encode("utf-8"),
        participant_identity="creator",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.event_type == "gemma_kokoro_voice_agent_ready"
    assert event.run_id == state.run_id
    assert event.realtime_session_id == state.realtime_session_id
    assert event.payload["presence_probe_ack"] is True
    assert event.payload["probe_id"] == "probe-1"
    assert event.payload["agent_name"] == "gemma4-kokoro-agent"
    assert event.payload["agent_participant_identity"] == "agent-runtime-identity"
    assert event.payload["audio_input_model"] == "deepseek/deepseek-v4-flash"

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(
            {
                "type": "voice_agent_presence_probe",
                "probe_id": "missing-target",
            }
        ).encode("utf-8"),
        participant_identity="creator",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    assert len(sink.events) == 1

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(
            {
                "type": "voice_agent_presence_probe",
                "probe_id": "wrong-topic",
                "run_id": str(state.run_id),
                "realtime_session_id": str(state.realtime_session_id),
            }
        ).encode("utf-8"),
        participant_identity="creator",
        topic="untrusted.topic",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    assert len(sink.events) == 1

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(
            {
                "type": "voice_agent_presence_probe",
                "probe_id": "wrong-sender",
                "run_id": str(state.run_id),
                "realtime_session_id": str(state.realtime_session_id),
            }
        ).encode("utf-8"),
        participant_identity="other-participant",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    assert len(sink.events) == 1

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(
            {
                "type": "voice_agent_presence_probe",
                "probe_id": "wrong-session",
                "run_id": str(uuid4()),
                "realtime_session_id": str(state.realtime_session_id),
            }
        ).encode("utf-8"),
        participant_identity="creator",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    assert len(sink.events) == 1


def test_gemma_kokoro_engine_cancels_gemma_and_clears_kokoro_audio():
    asyncio.run(_assert_gemma_kokoro_engine_cancels_gemma_and_clears_kokoro_audio())


async def _assert_gemma_kokoro_engine_cancels_gemma_and_clears_kokoro_audio():
    gemma = BlockingGemmaReasoner()
    kokoro = FakeKokoroStreamer()
    publisher = FakeLiveKitPublisher()
    sink = InMemoryVoiceAgentEventSink()
    engine = GemmaKokoroLiveKitAgentEngine(
        config=RealtimeVoiceAgentConfig(tts_flush_chars=8),
        gemma=gemma,
        kokoro=kokoro,
        publisher=publisher,
        event_sink=sink,
    )
    turn = RealtimeVoiceTurnInput(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity="creator",
        transcript="please stop quickly",
    )

    task = asyncio.create_task(engine.handle_turn(turn, [], voice="af_heart"))
    await asyncio.wait_for(gemma.started.wait(), timeout=1.0)
    response_id = sink.events[0].payload["response_id"]
    canceled = await engine.cancel_response(str(response_id), "barge-in detected")
    result = await asyncio.wait_for(task, timeout=1.0)

    assert canceled is True
    assert result.canceled is True
    assert result.cancellation_reason == "barge-in detected"
    assert str(response_id) in publisher.cleared
    assert str(response_id) in publisher.stopped
    event_types = {event.event_type for event in sink.events}
    assert "gemma_kokoro_voice_turn_cancelled" in event_types
    cancel_event = next(
        event
        for event in sink.events
        if event.event_type == "gemma_kokoro_voice_turn_cancelled"
    )
    assert cancel_event.payload["cancel_gemma"] is True
    assert cancel_event.payload["clear_kokoro_buffers"] is True
    assert cancel_event.payload["stop_livekit_audio"] is True


def test_livekit_interrupt_message_cancels_active_gemma_kokoro_response():
    asyncio.run(_assert_livekit_interrupt_message_cancels_active_response())


async def _assert_livekit_interrupt_message_cancels_active_response():
    gemma = BlockingGemmaReasoner()
    kokoro = FakeKokoroStreamer()
    publisher = FakeLiveKitPublisher()
    sink = InMemoryVoiceAgentEventSink()
    config = RealtimeVoiceAgentConfig(tts_flush_chars=8)
    engine = GemmaKokoroLiveKitAgentEngine(
        config=config,
        gemma=gemma,
        kokoro=kokoro,
        publisher=publisher,
        event_sink=sink,
    )
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity="creator",
    )
    turn = RealtimeVoiceTurnInput(
        run_id=state.run_id,
        realtime_session_id=state.realtime_session_id,
        room_name=state.room_name,
        participant_identity="creator",
        transcript="please stop the current spoken output",
    )

    task = asyncio.create_task(engine.handle_turn(turn, [], voice="af_heart"))
    await asyncio.wait_for(gemma.started.wait(), timeout=1.0)
    response_id = engine.active_response_id
    assert response_id is not None

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(
            {
                "type": "voice_interrupt",
                "interrupt_id": "voice-interrupt-test",
                "run_id": str(state.run_id),
                "realtime_session_id": str(state.realtime_session_id),
                "response_id": response_id,
                "reason": "manual creator interrupt",
                "drop_outbound_audio_packets": True,
                "required_runtime_actions": [
                    "drop_outbound_audio_packets",
                    "cancel_gemma_inference",
                    "clear_kokoro_tts_buffer",
                    "stop_livekit_audio",
                ],
            }
        ).encode("utf-8"),
        participant_identity="creator",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    result = await asyncio.wait_for(task, timeout=1.0)

    assert result.canceled is True
    assert result.cancellation_reason == "manual creator interrupt"
    assert response_id in publisher.cleared
    assert response_id in publisher.stopped
    manual_event = next(
        event for event in sink.events if event.event_type == "voice_manual_interrupt_received"
    )
    assert manual_event.payload["interrupt_id"] == "voice-interrupt-test"
    assert manual_event.payload["response_id"] == response_id
    assert manual_event.payload["drop_outbound_audio_packets"] is True
    assert manual_event.payload["cancel_gemma"] is True
    assert manual_event.payload["clear_kokoro_buffers"] is True
    assert manual_event.payload["stop_livekit_audio"] is True
    assert manual_event.payload["canceled"] is True
    assert "gemma_kokoro_voice_turn_cancelled" in {
        event.event_type for event in sink.events
    }


def test_livekit_interrupt_message_ignores_wrong_session_and_reports_no_active_response():
    asyncio.run(_assert_livekit_interrupt_message_session_guards())


async def _assert_livekit_interrupt_message_session_guards():
    sink = InMemoryVoiceAgentEventSink()
    config = RealtimeVoiceAgentConfig()
    engine = GemmaKokoroLiveKitAgentEngine(
        config=config,
        gemma=FakeGemmaReasoner(["unused"]),
        kokoro=FakeKokoroStreamer(),
        publisher=FakeLiveKitPublisher(),
        event_sink=sink,
    )
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity="creator",
    )
    common = {
        "type": "voice_interrupt",
        "interrupt_id": "voice-interrupt-ignored",
        "reason": "manual creator interrupt",
    }

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(common).encode("utf-8"),
        participant_identity="creator",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    assert sink.events == []

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(
            {
                **common,
                "run_id": str(state.run_id),
                "realtime_session_id": str(state.realtime_session_id),
            }
        ).encode("utf-8"),
        participant_identity="creator",
        topic="untrusted.topic",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    assert sink.events == []

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(
            {
                **common,
                "run_id": str(state.run_id),
                "realtime_session_id": str(state.realtime_session_id),
            }
        ).encode("utf-8"),
        participant_identity="other-participant",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    assert sink.events == []

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(
            {
                **common,
                "run_id": str(uuid4()),
                "realtime_session_id": str(state.realtime_session_id),
            }
        ).encode("utf-8"),
        participant_identity="creator",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    assert sink.events == []

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(
            {
                **common,
                "run_id": str(state.run_id),
                "realtime_session_id": str(state.realtime_session_id),
                "drop_outbound_audio_packets": True,
            }
        ).encode("utf-8"),
        participant_identity="creator",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.event_type == "voice_interrupt_no_active_response"
    assert event.payload["interrupt_id"] == "voice-interrupt-ignored"
    assert event.payload["drop_outbound_audio_packets"] is True
    assert event.payload["cancel_gemma"] is False
    assert event.payload["clear_kokoro_buffers"] is False
    assert event.payload["stop_livekit_audio"] is False
    assert event.payload["canceled"] is False


def test_livekit_transcript_turn_is_session_guarded_and_committed():
    asyncio.run(_assert_livekit_transcript_turn_is_session_guarded_and_committed())


def test_livekit_session_history_compacts_old_audio_turns_after_response():
    asyncio.run(_assert_livekit_session_history_compacts_old_audio_turns_after_response())


def test_livekit_session_history_pruned_count_matches_retained_history():
    asyncio.run(_assert_livekit_session_history_pruned_count_matches_retained_history())


async def _assert_livekit_session_history_compacts_old_audio_turns_after_response():
    sink = InMemoryVoiceAgentEventSink()
    config = RealtimeVoiceAgentConfig(
        context_window_turns=6,
        prune_after_turns=1,
        tts_flush_chars=80,
    )
    engine = GemmaKokoroLiveKitAgentEngine(
        config=config,
        gemma=FakeGemmaReasoner(["Compacted answer."]),
        kokoro=FakeKokoroStreamer(),
        publisher=FakeLiveKitPublisher(),
        event_sink=sink,
    )
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity="creator",
        voice="af_heart",
        history=[
            VoiceConversationTurn(
                turn_id="old-audio-1",
                role="user",
                text="Old audio transcript one",
                audio_ref="artifact://voice-audio/old-1.pcm",
                audio_duration_ms=10_000,
            ),
            VoiceConversationTurn(
                turn_id="old-audio-2",
                role="user",
                text="Old audio transcript two",
                audio_ref="artifact://voice-audio/old-2.pcm",
                audio_duration_ms=9_000,
            ),
            VoiceConversationTurn(
                turn_id="recent-audio",
                role="user",
                text="Recent audio transcript",
                audio_ref="artifact://voice-audio/recent.pcm",
                audio_duration_ms=8_000,
            ),
            VoiceConversationTurn(
                turn_id="assistant-prior",
                role="assistant",
                text="Prior assistant response.",
            ),
        ],
    )
    typed_turn_id = str(uuid4())

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(
            {
                "type": "transcript_turn",
                "turn_id": typed_turn_id,
                "run_id": str(state.run_id),
                "realtime_session_id": str(state.realtime_session_id),
                "room_name": state.room_name,
                "transcript": "Keep the session history small after several voice turns.",
                "voice": "af_heart",
            }
        ).encode("utf-8"),
        participant_identity="creator",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    await _drain_active_turn_tasks(state)

    by_turn_id = {turn.turn_id: turn for turn in state.history}
    assert by_turn_id["old-audio-1"].audio_ref is None
    assert by_turn_id["old-audio-2"].audio_ref is None
    assert by_turn_id["old-audio-1"].metadata["raw_audio_replaced"] is True
    assert by_turn_id["old-audio-2"].metadata["raw_audio_replaced"] is True
    assert by_turn_id["recent-audio"].audio_ref == "artifact://voice-audio/recent.pcm"
    assert state.history[-2].turn_id == typed_turn_id
    assert state.history[-1].text == "Compacted answer."
    assert len([turn for turn in state.history if turn.audio_ref]) == 1

    session_prune_event = next(
        event for event in sink.events if event.event_type == "voice_session_history_pruned"
    )
    assert session_prune_event.payload["pruned_turn_ids"] == [
        "old-audio-1",
        "old-audio-2",
    ]
    assert session_prune_event.payload["raw_audio_turns_before"] == 3
    assert session_prune_event.payload["raw_audio_turns_after"] == 1
    assert session_prune_event.payload["session_history_turn_count"] == len(
        state.history
    )


async def _assert_livekit_session_history_pruned_count_matches_retained_history():
    sink = InMemoryVoiceAgentEventSink()
    config = RealtimeVoiceAgentConfig(
        context_window_turns=4,
        prune_after_turns=3,
        tts_flush_chars=80,
    )
    engine = GemmaKokoroLiveKitAgentEngine(
        config=config,
        gemma=FakeGemmaReasoner(["Windowed answer."]),
        kokoro=FakeKokoroStreamer(),
        publisher=FakeLiveKitPublisher(),
        event_sink=sink,
    )
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity="creator",
        voice="af_heart",
        history=[
            VoiceConversationTurn(
                turn_id="audio-1",
                role="user",
                text="Audio one",
                audio_ref="artifact://voice-audio/1.pcm",
                audio_duration_ms=10_000,
            ),
            VoiceConversationTurn(
                turn_id="assistant-1",
                role="assistant",
                text="Assistant one",
            ),
            VoiceConversationTurn(
                turn_id="audio-2",
                role="user",
                text="Audio two",
                audio_ref="artifact://voice-audio/2.pcm",
                audio_duration_ms=9_000,
            ),
            VoiceConversationTurn(
                turn_id="assistant-2",
                role="assistant",
                text="Assistant two",
            ),
            VoiceConversationTurn(
                turn_id="audio-3",
                role="user",
                text="Audio three",
                audio_ref="artifact://voice-audio/3.pcm",
                audio_duration_ms=8_000,
            ),
            VoiceConversationTurn(
                turn_id="assistant-3",
                role="assistant",
                text="Assistant three",
            ),
            VoiceConversationTurn(
                turn_id="audio-4",
                role="user",
                text="Audio four",
                audio_ref="artifact://voice-audio/4.pcm",
                audio_duration_ms=7_000,
            ),
            VoiceConversationTurn(
                turn_id="assistant-4",
                role="assistant",
                text="Assistant four",
            ),
        ],
    )

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(
            {
                "type": "transcript_turn",
                "turn_id": str(uuid4()),
                "run_id": str(state.run_id),
                "realtime_session_id": str(state.realtime_session_id),
                "room_name": state.room_name,
                "transcript": "Use the default voice context window.",
                "voice": "af_heart",
            }
        ).encode("utf-8"),
        participant_identity="creator",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    await _drain_active_turn_tasks(state)

    session_prune_event = next(
        event for event in sink.events if event.event_type == "voice_session_history_pruned"
    )
    retained_raw_audio_count = sum(1 for turn in state.history if turn.audio_ref)
    assert len(state.history) == config.context_window_turns
    assert retained_raw_audio_count == 1
    assert session_prune_event.payload["raw_audio_turns_after"] == retained_raw_audio_count
    assert session_prune_event.payload["session_history_turn_count"] == len(
        state.history
    )


async def _assert_livekit_transcript_turn_is_session_guarded_and_committed():
    sink = InMemoryVoiceAgentEventSink()
    config = RealtimeVoiceAgentConfig(tts_flush_chars=80)
    engine = GemmaKokoroLiveKitAgentEngine(
        config=config,
        gemma=FakeGemmaReasoner(["Typed answer."]),
        kokoro=FakeKokoroStreamer(),
        publisher=FakeLiveKitPublisher(),
        event_sink=sink,
    )
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity="creator",
        voice="af_heart",
    )
    typed_turn_id = str(uuid4())
    transcript_payload = {
        "type": "transcript_turn",
        "turn_id": typed_turn_id,
        "run_id": str(state.run_id),
        "realtime_session_id": str(state.realtime_session_id),
        "room_name": state.room_name,
        "transcript": "Use typed input in the same live voice session.",
        "voice": "af_heart",
    }

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps({**transcript_payload, "run_id": str(uuid4())}).encode(
            "utf-8"
        ),
        participant_identity="creator",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(transcript_payload).encode("utf-8"),
        participant_identity="creator",
        topic="untrusted.topic",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    assert sink.events == []

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps({**transcript_payload, "transcript": "   "}).encode(
            "utf-8"
        ),
        participant_identity="creator",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    assert len(sink.events) == 1
    assert sink.events[0].event_type == "voice_text_turn_rejected"
    assert sink.events[0].payload["reason"] == "empty_transcript"
    sink.events.clear()

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(transcript_payload).encode("utf-8"),
        participant_identity="creator",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    await _drain_active_turn_tasks(state)

    event_types = [event.event_type for event in sink.events]
    assert event_types[0] == "voice_user_turn_committed"
    assert "assistant_response_completed" in event_types
    committed = sink.events[0]
    assert committed.payload["turn_id"] == typed_turn_id
    assert committed.payload["transcript"] == (
        "Use typed input in the same live voice session."
    )
    assert committed.payload["input_modality"] == "text"
    assert committed.payload["windowing"] == "livekit_data_transcript"
    completed = next(
        event for event in sink.events if event.event_type == "assistant_response_completed"
    )
    assert completed.payload["assistant_text"] == "Typed answer."
    assert state.history[0].text == "Use typed input in the same live voice session."
    assert state.history[1].text == "Typed answer."


def test_livekit_transcript_turn_provider_failure_records_history_without_assistant():
    asyncio.run(
        _assert_livekit_transcript_turn_provider_failure_records_history_without_assistant()
    )


async def _assert_livekit_transcript_turn_provider_failure_records_history_without_assistant():
    sink = InMemoryVoiceAgentEventSink()
    config = RealtimeVoiceAgentConfig()
    engine = GemmaKokoroLiveKitAgentEngine(
        config=config,
        gemma=FailingGemmaReasoner(),
        kokoro=FakeKokoroStreamer(),
        publisher=FakeLiveKitPublisher(),
        event_sink=sink,
    )
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity="creator",
        voice="af_heart",
    )
    typed_turn_id = str(uuid4())

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(
            {
                "type": "transcript_turn",
                "turn_id": typed_turn_id,
                "run_id": str(state.run_id),
                "realtime_session_id": str(state.realtime_session_id),
                "room_name": state.room_name,
                "transcript": "Use typed input in the same live voice session.",
            }
        ).encode("utf-8"),
        participant_identity="creator",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    await _drain_active_turn_tasks(state)

    event_types = [event.event_type for event in sink.events]
    assert "gemma_kokoro_voice_turn_failed" in event_types
    assert "assistant_response_completed" not in event_types
    assert len(state.history) == 1
    assert state.history[0].turn_id == typed_turn_id
    assert state.history[0].metadata["voice_turn_failed"] is True
    assert state.history[0].metadata["failure_stage"] == "gemma_generation"


def test_livekit_data_message_rejects_non_object_json_without_crashing():
    asyncio.run(_assert_livekit_data_message_rejects_non_object_json_without_crashing())


async def _assert_livekit_data_message_rejects_non_object_json_without_crashing():
    sink = InMemoryVoiceAgentEventSink()
    config = RealtimeVoiceAgentConfig()
    engine = GemmaKokoroLiveKitAgentEngine(
        config=config,
        gemma=FakeGemmaReasoner(["unused"]),
        kokoro=FakeKokoroStreamer(),
        publisher=FakeLiveKitPublisher(),
        event_sink=sink,
    )
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity="creator",
    )

    await _handle_data_message(
        engine=engine,
        state=state,
        payload=json.dumps(["not", "an", "object"]).encode("utf-8"),
        participant_identity="creator",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )

    assert sink.events == []
    assert state.history == []


def test_livekit_control_topic_data_messages_are_session_serialized():
    asyncio.run(_assert_livekit_control_topic_data_messages_are_session_serialized())


async def _assert_livekit_control_topic_data_messages_are_session_serialized():
    sink = InMemoryVoiceAgentEventSink()
    config = RealtimeVoiceAgentConfig()
    engine = GemmaKokoroLiveKitAgentEngine(
        config=config,
        gemma=FakeGemmaReasoner(["serialized answer"]),
        kokoro=FakeKokoroStreamer(),
        publisher=FakeLiveKitPublisher(),
        event_sink=sink,
    )
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity="creator",
    )
    transcript_payload = {
        "type": "transcript_turn",
        "turn_id": str(uuid4()),
        "run_id": str(state.run_id),
        "realtime_session_id": str(state.realtime_session_id),
        "transcript": "This should wait behind the session data-message lock.",
    }

    await state.data_message_lock.acquire()
    task = asyncio.create_task(
        _handle_data_message_serialized(
            engine=engine,
            state=state,
            payload=json.dumps(transcript_payload).encode("utf-8"),
            participant_identity="creator",
            topic="agent.voice.control",
            event_sink=sink,
            config=config,
            settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
            voice_edge=None,
            agent_participant_identity="agent-runtime-identity",
        )
    )
    await asyncio.sleep(0)
    assert sink.events == []

    state.data_message_lock.release()
    await asyncio.wait_for(task, timeout=1.0)
    await _drain_active_turn_tasks(state)

    assert sink.events[0].event_type == "voice_user_turn_committed"
    assert state.history[0].text == (
        "This should wait behind the session data-message lock."
    )


def test_livekit_serialized_interrupt_cancels_running_transcript_turn():
    asyncio.run(_assert_livekit_serialized_interrupt_cancels_running_transcript_turn())


async def _assert_livekit_serialized_interrupt_cancels_running_transcript_turn():
    gemma = BlockingGemmaReasoner()
    publisher = FakeLiveKitPublisher()
    sink = InMemoryVoiceAgentEventSink()
    config = RealtimeVoiceAgentConfig(tts_flush_chars=8)
    engine = GemmaKokoroLiveKitAgentEngine(
        config=config,
        gemma=gemma,
        kokoro=FakeKokoroStreamer(),
        publisher=publisher,
        event_sink=sink,
    )
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="agent-studio-room",
        participant_identity="creator",
    )

    await _handle_data_message_serialized(
        engine=engine,
        state=state,
        payload=json.dumps(
            {
                "type": "transcript_turn",
                "turn_id": str(uuid4()),
                "run_id": str(state.run_id),
                "realtime_session_id": str(state.realtime_session_id),
                "transcript": "Start a typed turn that should remain interruptible.",
            }
        ).encode("utf-8"),
        participant_identity="creator",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    await asyncio.wait_for(gemma.started.wait(), timeout=1.0)
    response_id = engine.active_response_id
    assert response_id is not None

    await _handle_data_message_serialized(
        engine=engine,
        state=state,
        payload=json.dumps(
            {
                "type": "voice_interrupt",
                "interrupt_id": "typed-turn-interrupt",
                "run_id": str(state.run_id),
                "realtime_session_id": str(state.realtime_session_id),
                "response_id": response_id,
                "reason": "typed follow-up interrupted active output",
            }
        ).encode("utf-8"),
        participant_identity="creator",
        topic="agent.voice.control",
        event_sink=sink,
        config=config,
        settings=Settings(livekit_agent_name="gemma4-kokoro-agent"),
        voice_edge=None,
        agent_participant_identity="agent-runtime-identity",
    )
    await _drain_active_turn_tasks(state)

    assert response_id in publisher.cleared
    assert response_id in publisher.stopped
    event_types = [event.event_type for event in sink.events]
    assert "voice_manual_interrupt_received" in event_types
    assert "gemma_kokoro_voice_turn_cancelled" in event_types
    assert state.history[-1].interrupted is True


def test_voice_agent_runtime_exposes_livekit_and_adapter_entrypoints():
    livekit_app = (ROOT / "src/all_about_llms/voice_agent/livekit_app.py").read_text()
    adapters = (ROOT / "src/all_about_llms/voice_agent/adapters.py").read_text()
    edge = (ROOT / "src/all_about_llms/voice_agent/edge.py").read_text()
    engine = (ROOT / "src/all_about_llms/voice_agent/engine.py").read_text()
    cli = (ROOT / "src/all_about_llms/cli.py").read_text()
    pyproject = (ROOT / "pyproject.toml").read_text()
    package_json = json.loads((ROOT / "frontend/next-app/package.json").read_text())

    assert "AgentServer" in livekit_app
    assert "@server.rtc_session" in livekit_app
    assert "AutoSubscribe.AUDIO_ONLY" in livekit_app
    assert "rtc.AudioStream" in livekit_app
    assert "RustVoiceEdgeClient" in livekit_app
    assert "PersistentRustVoiceEdgeClient" in livekit_app
    assert "analyze_pcm_frame" in livekit_app
    assert "rust_voice_edge_vad_silence" in livekit_app
    assert "voice_barge_in_detected" in edge
    assert "voice_edge_cancellation_acknowledged" in edge
    assert "active_response_id" in engine
    assert "LiveKitAudioTrackPublisher" in livekit_app
    assert "HuggingFaceGemmaAudioReasoner" in adapters
    assert "HuggingFaceKokoroTTSStreamer" in adapters
    assert "LocalKokoroTTSStreamer" in adapters
    assert "rtc.AudioSource" in adapters
    assert "LocalAudioTrack.create_audio_track" in adapters
    assert "run-voice-agent" in cli
    assert "run_livekit_voice_agent_server" in cli
    assert "livekit-agents" in pyproject
    assert "kokoro>=0.9.2" in pyproject
    assert "livekit-client" in package_json["dependencies"]


def test_build_kokoro_streamer_trims_endpoint_before_runtime_selection(monkeypatch):
    monkeypatch.setattr(
        "all_about_llms.voice_agent.kokoro.kokoro_local_package_available",
        lambda: True,
    )

    hosted = _build_kokoro_streamer(
        Settings(
            hf_token="secret-hf-token",
            kokoro_tts_endpoint_url="  https://hf.example/kokoro  ",
        )
    )
    local = _build_kokoro_streamer(Settings(kokoro_tts_endpoint_url="   "))
    malformed = _build_kokoro_streamer(Settings(kokoro_tts_endpoint_url="not-a-url"))

    assert isinstance(hosted, HuggingFaceKokoroTTSStreamer)
    assert hosted._endpoint_url == "https://hf.example/kokoro"
    assert isinstance(local, LocalKokoroTTSStreamer)
    assert isinstance(malformed, LocalKokoroTTSStreamer)


def test_local_kokoro_streamer_passes_repo_id_to_suppress_stdout_warning(monkeypatch):
    calls: list[dict[str, object]] = []

    class FakeKPipeline:
        def __init__(self, *, lang_code, repo_id=None, **kwargs):
            calls.append({"lang_code": lang_code, "repo_id": repo_id, **kwargs})

        def __call__(self, text, voice):
            return [(None, None, [0.0, 0.1, -0.1])]

    monkeypatch.setitem(
        sys.modules,
        "kokoro",
        types.SimpleNamespace(KPipeline=FakeKPipeline),
    )

    async def collect_chunks() -> list[bytes]:
        streamer = LocalKokoroTTSStreamer(lang_code="a", voice="af_heart")
        return [
            chunk
            async for chunk in streamer.stream_audio(
                response_id="kokoro-warning-regression",
                text="short smoke",
                voice=None,
                cancellation=VoiceAgentCancellationToken(
                    "kokoro-warning-regression"
                ),
            )
        ]

    chunks = asyncio.run(collect_chunks())

    assert calls == [{"lang_code": "a", "repo_id": "hexgrad/Kokoro-82M"}]
    assert chunks


def test_build_kokoro_streamer_fails_fast_without_ready_route(monkeypatch):
    monkeypatch.setattr(
        "all_about_llms.voice_agent.kokoro.kokoro_local_package_available",
        lambda: False,
    )

    with pytest.raises(ProviderConfigurationError, match="KOKORO_TTS_ENDPOINT_URL"):
        _build_kokoro_streamer(Settings(kokoro_tts_endpoint_url="   "))
    with pytest.raises(ProviderConfigurationError, match="http\\(s\\) URL"):
        _build_kokoro_streamer(Settings(kokoro_tts_endpoint_url="not-a-url"))


def test_build_voice_edge_client_prefers_configured_http_sidecar(tmp_path):
    client = _build_voice_edge_client(
        Settings(
            rust_voice_edge_http_url="http://127.0.0.1:7071",
            rust_voice_edge_binary_path=tmp_path / "missing-voice-edge",
            rust_voice_edge_vad_backend="silero_onnx",
            rust_voice_edge_vad_model_path=tmp_path / "silero.onnx",
        )
    )

    assert isinstance(client, RustVoiceEdgeHttpClient)
    assert client.base_url == "http://127.0.0.1:7071"
    assert client.available is True
    assert client.vad_backend == "silero_onnx"
    assert client.vad_model_path == str(tmp_path / "silero.onnx")


def test_build_voice_edge_client_adds_jsonl_fallback_when_binary_exists(tmp_path):
    fake_binary = tmp_path / "voice-edge"
    fake_binary.write_text("#!/bin/sh\n", encoding="utf-8")
    fake_binary.chmod(0o755)
    client = _build_voice_edge_client(
        Settings(
            rust_voice_edge_http_url="http://127.0.0.1:7071",
            rust_voice_edge_binary_path=fake_binary,
        )
    )

    assert isinstance(client, FallbackVoiceEdgeClient)
    assert client.transport == "http_sidecar_with_persistent_jsonl_fallback"
    assert client.base_url == "http://127.0.0.1:7071"
    assert str(client.binary_path) == str(fake_binary)


def test_fallback_voice_edge_client_preserves_primary_vad_config():
    primary = HealthyHealthHttpVoiceEdgeClient(
        vad_backend="silero_onnx",
        target_vad_model="silero-vad-rust",
        vad_model_path="/models/silero.onnx",
        allow_vad_fallback=True,
    )
    fallback = FakeAvailableVoiceEdgeClient()
    client = FallbackVoiceEdgeClient(primary=primary, fallback=fallback)

    assert client.vad_backend == "silero_onnx"
    assert client.target_vad_model == "silero-vad-rust"
    assert client.vad_model_path == "/models/silero.onnx"
    assert client.vad_backend_effective == "silero_onnx_with_deterministic_fallback"
    assert client.vad_model_effective == "silero_onnx_bundled_or_configured_model"
    assert client.vad_fallback_reason is None


def test_settings_resolve_project_relative_local_binary_paths():
    settings = Settings(
        rust_voice_edge_binary_path=Path("tmp/voice-edge"),
        rust_reranker_binary_path=Path("tmp/retrieval-ranker"),
        rust_voice_edge_vad_model_path=Path("tmp/silero.onnx"),
    )
    home_settings = Settings(
        rust_voice_edge_binary_path=Path("~/voice-edge"),
        rust_reranker_binary_path=Path("~/retrieval-ranker"),
    )

    assert settings.rust_voice_edge_binary_path == PROJECT_ROOT / "tmp/voice-edge"
    assert settings.rust_reranker_binary_path == PROJECT_ROOT / "tmp/retrieval-ranker"
    assert settings.rust_voice_edge_vad_model_path == PROJECT_ROOT / "tmp/silero.onnx"
    assert home_settings.rust_voice_edge_binary_path == Path.home() / "voice-edge"
    assert home_settings.rust_reranker_binary_path == Path.home() / "retrieval-ranker"


def test_preflight_voice_edge_client_uses_jsonl_when_http_health_fails():
    primary = FailingHealthHttpVoiceEdgeClient()
    fallback = FakeAvailableVoiceEdgeClient()
    client = FallbackVoiceEdgeClient(primary=primary, fallback=fallback)

    selected = asyncio.run(_preflight_voice_edge_client(client))

    assert selected is fallback
    assert primary.closed is True
    assert fallback.health_checks == 1


def test_preflight_voice_edge_client_reports_http_primary_for_healthy_fallback_wrapper():
    primary = HealthyHealthHttpVoiceEdgeClient(vad_backend="silero_onnx")
    fallback = FakeAvailableVoiceEdgeClient()
    client = FallbackVoiceEdgeClient(primary=primary, fallback=fallback)

    selected = asyncio.run(_preflight_voice_edge_client(client))

    assert selected is client
    assert _selected_preflight_transport(selected) == "http_sidecar"
    assert _client_vad_metadata(selected)["vad_backend_requested"] == "silero_onnx"
    assert (
        _client_vad_metadata(selected)["vad_model_effective"]
        == "silero_onnx_bundled_or_configured_model"
    )
    assert fallback.health_checks == 0


def test_preflight_voice_edge_client_keeps_fallback_when_http_cleanup_fails():
    async def run_preflight():
        primary = FailingCloseHealthHttpVoiceEdgeClient()
        fallback = FakeAvailableVoiceEdgeClient()
        client = FallbackVoiceEdgeClient(primary=primary, fallback=fallback)
        loop = asyncio.get_running_loop()
        captured_errors = []
        previous_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda _loop, context: captured_errors.append(context))
        try:
            selected = await _preflight_voice_edge_client(client)
        finally:
            loop.set_exception_handler(previous_handler)
        return selected, fallback, captured_errors

    selected, fallback, captured_errors = asyncio.run(run_preflight())

    assert selected is fallback
    assert fallback.health_checks == 1
    assert captured_errors[0]["message"] == (
        "voice edge cleanup after failed preflight failed"
    )


def test_preflight_voice_edge_client_raises_when_http_health_fails_without_fallback():
    primary = FailingHealthHttpVoiceEdgeClient()

    with pytest.raises(RuntimeError, match="HTTP sidecar health check failed"):
        asyncio.run(_preflight_voice_edge_client(primary))

    assert primary.closed is True


def test_preflight_voice_edge_client_closes_jsonl_when_health_fails():
    client = FailingHealthPersistentVoiceEdgeClient()

    with pytest.raises(RuntimeError, match="Rust voice-edge health check failed"):
        asyncio.run(_preflight_voice_edge_client(client))

    assert client.closed is True


def test_cancelled_response_ids_are_bounded():
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="voice-room",
    )

    for index in range(MAX_CANCELLED_RESPONSE_IDS + 10):
        _remember_cancelled_response_id(state, f"response-{index}")

    assert len(state.cancelled_response_ids) == MAX_CANCELLED_RESPONSE_IDS
    assert "response-0" not in state.cancelled_response_ids
    assert f"response-{MAX_CANCELLED_RESPONSE_IDS + 9}" in state.cancelled_response_ids

    _remember_cancelled_response_id(state, f"response-{MAX_CANCELLED_RESPONSE_IDS + 9}")

    assert len(state.cancelled_response_ids) == MAX_CANCELLED_RESPONSE_IDS


def test_voice_edge_client_is_registered_for_session_shutdown():
    ctx = FakeShutdownContext()
    voice_edge = FakeClosableVoiceEdgeClient()

    _register_voice_edge_cleanup(ctx, voice_edge)

    assert len(ctx.callbacks) == 1
    asyncio.run(ctx.callbacks[0]("room shutdown"))
    asyncio.run(ctx.callbacks[0]("duplicate shutdown"))
    assert voice_edge.closed_count == 1


def test_voice_edge_cleanup_requires_shutdown_callback():
    with pytest.raises(RuntimeError, match="add_shutdown_callback"):
        _register_voice_edge_cleanup(object(), FakeClosableVoiceEdgeClient())


def test_voice_edge_cleanup_exception_is_reported_and_can_retry():
    async def run_cleanup():
        ctx = FakeShutdownContext()
        voice_edge = FlakyClosableVoiceEdgeClient()
        loop = asyncio.get_running_loop()
        captured_errors = []
        previous_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda _loop, context: captured_errors.append(context))
        try:
            _register_voice_edge_cleanup(ctx, voice_edge)
            await ctx.callbacks[0]("room shutdown")
            await ctx.callbacks[0]("retry shutdown")
        finally:
            loop.set_exception_handler(previous_handler)
        return voice_edge.close_attempts, captured_errors

    close_attempts, captured_errors = asyncio.run(run_cleanup())

    assert close_attempts == 2
    assert captured_errors[0]["message"] == "voice edge cleanup failed"


def test_voice_turn_capture_buffer_commits_after_vad_silence_with_pre_roll():
    capture = VoiceTurnCaptureBuffer(min_silence_frames=2, pre_roll_frames=2)

    assert (
        capture.ingest(
            b"silence-1",
            speech_started_event=False,
            is_speech=False,
            now=0.0,
        )
        is None
    )
    assert (
        capture.ingest(
            b"speech-1",
            speech_started_event=True,
            is_speech=True,
            now=0.1,
        )
        is None
    )
    assert (
        capture.ingest(
            b"speech-2",
            speech_started_event=False,
            is_speech=True,
            now=0.2,
        )
        is None
    )
    assert (
        capture.ingest(
            b"gap-1",
            speech_started_event=False,
            is_speech=False,
            now=0.3,
        )
        is None
    )
    payload = capture.ingest(
        b"gap-2",
        speech_started_event=False,
        is_speech=False,
        now=0.4,
    )

    assert payload == b"silence-1speech-1speech-2gap-1gap-2"
    assert capture.speech_started is False
    assert capture.byte_count == 0


def test_build_voice_audio_turn_persists_local_audio_artifact(tmp_path):
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="voice-room",
    )
    audio = b"\x01\x02creator-audio"

    turn = _build_voice_audio_turn(
        settings=Settings(artifacts_root=tmp_path),
        state=state,
        participant_identity="creator",
        audio_pcm=audio,
        duration_ms=32,
        windowing="rust_voice_edge_vad_silence",
    )

    assert turn.audio_ref is not None
    assert turn.audio_ref.startswith("artifact://voice-audio/")
    assert turn.audio_pcm == audio
    assert turn.metadata["audio_artifact_persisted"] is True
    assert turn.metadata["audio_artifact_uri"] == turn.audio_ref
    assert turn.metadata["audio_artifact_sha256"] == hashlib.sha256(audio).hexdigest()
    relative_path = Path(str(turn.metadata["audio_artifact_relative_path"]))
    assert (tmp_path / relative_path).read_bytes() == audio
    assert str(tmp_path) not in str(turn.metadata)
    assert "creator-audio" not in str(turn.metadata)


def test_voice_turn_committed_event_carries_audio_artifact_metadata(tmp_path):
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="voice-room",
    )
    turn = _build_voice_audio_turn(
        settings=Settings(artifacts_root=tmp_path),
        state=state,
        participant_identity="creator",
        audio_pcm=b"\x01\x02creator-audio",
        duration_ms=32,
        windowing="rust_voice_edge_vad_silence",
    )
    sink = InMemoryVoiceAgentEventSink()

    asyncio.run(
        _emit_voice_turn_committed(
            event_sink=sink,
            state=state,
            turn=turn,
            windowing="rust_voice_edge_vad_silence",
        )
    )

    payload = sink.events[0].payload
    assert "transcript" in payload
    assert payload["input_modality"] == "voice"
    assert payload["audio_artifact_uri"] == turn.metadata["audio_artifact_uri"]
    assert payload["audio_artifact_relative_path"] == turn.metadata[
        "audio_artifact_relative_path"
    ]
    assert payload["audio_artifact_sha256"] == turn.metadata["audio_artifact_sha256"]
    assert payload["audio_artifact_bytes"] == turn.metadata["audio_artifact_bytes"]
    assert payload["audio_artifact_persisted"] is True
    assert "creator-audio" not in str(payload)


def test_build_voice_audio_turn_skips_oversized_local_audio_artifact(tmp_path):
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="voice-room",
    )

    turn = _build_voice_audio_turn(
        settings=Settings(
            artifacts_root=tmp_path,
            voice_agent_audio_artifact_max_bytes=4,
        ),
        state=state,
        participant_identity="creator",
        audio_pcm=b"too-large",
        duration_ms=32,
        windowing="rust_voice_edge_vad_silence",
    )

    assert turn.audio_ref is None
    assert turn.metadata["audio_artifact_persisted"] is False
    assert turn.metadata["audio_artifact_skip_reason"] == "audio_exceeds_max_bytes"
    assert list(tmp_path.rglob("*.pcm")) == []


def test_voice_audio_artifact_cleanup_removes_expired_pcm_files(tmp_path):
    old_audio = tmp_path / "voice-audio" / "run" / "session" / "old.pcm"
    fresh_audio = tmp_path / "voice-audio" / "run" / "session" / "fresh.pcm"
    old_audio.parent.mkdir(parents=True)
    old_audio.write_bytes(b"old")
    fresh_audio.write_bytes(b"fresh")
    old_time = 1_000_000.0
    fresh_time = old_time + (6 * 24 * 60 * 60)
    cleanup_time = old_time + (8 * 24 * 60 * 60)
    old_audio.touch()
    fresh_audio.touch()
    os.utime(old_audio, (old_time, old_time))
    os.utime(fresh_audio, (fresh_time, fresh_time))

    removed = _cleanup_expired_voice_audio_artifacts(
        Settings(artifacts_root=tmp_path, voice_agent_audio_artifact_retention_days=7),
        wall_time=cleanup_time,
    )

    assert removed == 1
    assert not old_audio.exists()
    assert fresh_audio.exists()


def test_voice_edge_event_helpers_extract_vad_without_forwarding_frame_noise():
    result = type(
        "EdgeResult",
        (),
        {
            "events": [
                {"event_type": "voice_vad_frame_analyzed", "is_speech": False},
                {"event_type": "voice_vad_frame_analyzed", "is_speech": True},
                {"event_type": "voice_user_speech_started"},
            ]
        },
    )()

    assert _latest_vad_is_speech(result) is True
    assert _has_voice_edge_event(result, "voice_user_speech_started") is True
    assert (
        _should_forward_voice_edge_event({"event_type": "voice_vad_frame_analyzed"})
        is False
    )
    assert _should_forward_voice_edge_event({"event_type": "voice_user_speech_started"})


def test_voice_edge_events_are_redacted_before_sink_emit():
    asyncio.run(_assert_voice_edge_events_are_redacted_before_sink_emit())


async def _assert_voice_edge_events_are_redacted_before_sink_emit():
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="voice-room",
    )
    result = VoiceEdgeAnalysisResult(
        request_id="voice-edge-request-1",
        session_id="voice-edge-session-1",
        events=[
            {
                "event_type": "voice_edge_transport_fallback",
                "metadata": {
                    "error": f"fallback after {BEARER_SECRET}",
                    "api_key": "raw-edge-api-key",
                    "safe_nested": [f"retry with {TAVILY_SECRET}"],
                },
            }
        ],
        final_state={
            "provider_error": f"native audio failed with {HF_SECRET}",
            "clientSecret": "raw-edge-client-secret",
        },
        cancellation_ack=None,
    )
    sink = CapturingVoiceEventSink()

    await _emit_voice_edge_events(
        event_sink=sink,
        state=state,
        participant_identity="creator",
        result=result,
    )

    assert len(sink.events) == 1
    payload = sink.events[0].payload
    serialized = json.dumps(payload)
    assert HF_SECRET not in serialized
    assert TAVILY_SECRET not in serialized
    assert BEARER_SECRET not in serialized
    assert "raw-edge-api-key" not in serialized
    assert "raw-edge-client-secret" not in serialized
    assert "Bearer [redacted]" in serialized
    assert "hf_[redacted]" in serialized
    assert "tvly-[redacted]" in serialized
    assert "api_key" not in payload["voice_edge_event"]["metadata"]
    assert "clientSecret" not in payload["voice_edge_final_state"]


def test_voice_agent_media_bridge_payload_marks_livekit_to_rust_audio_path():
    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="voice-room",
    )
    voice_edge = FakeAvailableVoiceEdgeClient()

    payload = _voice_agent_media_bridge_payload(
        state=state,
        participant_identity="creator",
        settings=Settings(
            gemma4_realtime_sample_rate=16000,
            rust_voice_edge_frame_ms=32,
        ),
        voice_edge=voice_edge,
    )

    assert payload["run_id"] == str(state.run_id)
    assert payload["realtime_session_id"] == str(state.realtime_session_id)
    assert payload["media_bridge"] == "livekit_audio_track_to_rust_voice_edge"
    assert payload["livekit_track_kind"] == "audio"
    assert payload["participant_identity"] == "creator"
    assert payload["voice_edge_enabled"] is True
    assert payload["voice_edge_process_mode"] == "persistent_jsonl"
    assert payload["sample_rate"] == 16000
    assert payload["frame_ms"] == 32


def test_handle_audio_track_ignores_unbound_or_wrong_participant_audio():
    asyncio.run(_assert_audio_track_ignores_unbound_or_wrong_participant_audio())


async def _assert_audio_track_ignores_unbound_or_wrong_participant_audio():
    class CountingAudioStream:
        instances = []

        def __init__(self, track, *, sample_rate, num_channels):
            del track, sample_rate, num_channels
            CountingAudioStream.instances.append(self)

        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

        async def aclose(self):
            pass

    class FakeRtc:
        AudioStream = CountingAudioStream

    config = RealtimeVoiceAgentConfig()
    engine = GemmaKokoroLiveKitAgentEngine(
        config=config,
        gemma=FakeGemmaReasoner(["unused"]),
        kokoro=FakeKokoroStreamer(),
        publisher=FakeLiveKitPublisher(),
        event_sink=InMemoryVoiceAgentEventSink(),
    )
    settings = Settings()
    sink = InMemoryVoiceAgentEventSink()

    unbound_state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="voice-room",
        participant_identity=None,
    )
    await _handle_audio_track(
        rtc=FakeRtc,
        engine=engine,
        state=unbound_state,
        track=object(),
        participant_identity="creator",
        settings=settings,
        config=config,
        voice_edge=None,
        event_sink=sink,
    )

    bound_state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="voice-room",
        participant_identity="creator",
    )
    await _handle_audio_track(
        rtc=FakeRtc,
        engine=engine,
        state=bound_state,
        track=object(),
        participant_identity="other-participant",
        settings=settings,
        config=config,
        voice_edge=None,
        event_sink=sink,
    )

    assert CountingAudioStream.instances == []
    assert sink.events == []


def test_startup_ready_is_suppressed_until_session_identity_is_bound():
    assert (
        _emit_startup_ready_for_bound_session(
            LiveKitVoiceAgentSessionState(
                run_id=uuid4(),
                realtime_session_id=uuid4(),
                room_name="voice-room",
                participant_identity=None,
            )
        )
        is False
    )
    assert (
        _emit_startup_ready_for_bound_session(
            LiveKitVoiceAgentSessionState(
                run_id=uuid4(),
                realtime_session_id=uuid4(),
                room_name="voice-room",
                participant_identity="creator",
            )
        )
        is True
    )


def test_handle_audio_track_closes_stream_when_media_bridge_emit_fails():
    asyncio.run(_assert_audio_track_closes_stream_when_media_bridge_emit_fails())


async def _assert_audio_track_closes_stream_when_media_bridge_emit_fails():
    class EmptyAudioStream:
        instances = []

        def __init__(self, track, *, sample_rate, num_channels):
            del track, sample_rate, num_channels
            self.closed = False
            EmptyAudioStream.instances.append(self)

        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

        async def aclose(self):
            self.closed = True

    class FakeRtc:
        AudioStream = EmptyAudioStream

    class FailingBridgeEventSink:
        async def emit(self, event):
            if event.event_type == "voice_agent_media_bridge_ready":
                raise RuntimeError("bridge proof sink failed")

    state = LiveKitVoiceAgentSessionState(
        run_id=uuid4(),
        realtime_session_id=uuid4(),
        room_name="voice-room",
        participant_identity="creator",
    )
    config = RealtimeVoiceAgentConfig()
    engine = GemmaKokoroLiveKitAgentEngine(
        config=config,
        gemma=FakeGemmaReasoner(["unused"]),
        kokoro=FakeKokoroStreamer(),
        publisher=FakeLiveKitPublisher(),
        event_sink=InMemoryVoiceAgentEventSink(),
    )

    await _handle_audio_track(
        rtc=FakeRtc,
        engine=engine,
        state=state,
        track=object(),
        participant_identity="creator",
        settings=Settings(),
        config=config,
        voice_edge=None,
        event_sink=FailingBridgeEventSink(),
    )

    assert EmptyAudioStream.instances
    assert EmptyAudioStream.instances[-1].closed is True
