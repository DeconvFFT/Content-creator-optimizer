import asyncio
import hashlib
import json
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid4

from all_about_llms.config import Settings, get_settings
from all_about_llms.providers.interfaces import ProviderConfigurationError
from all_about_llms.realtime_safety import safe_realtime_metadata
from all_about_llms.voice_agent.adapters import (
    BackendRealtimeVoiceEventSink,
    CompositeVoiceAgentEventSink,
    HuggingFaceKokoroTTSStreamer,
    LiveKitAudioTrackPublisher,
    LiveKitDataEventSink,
    LocalKokoroTTSStreamer,
)
from all_about_llms.voice_agent.control_binding import (
    verify_livekit_control_binding_token,
)
from all_about_llms.voice_agent.edge import (
    FallbackVoiceEdgeClient,
    PersistentRustVoiceEdgeClient,
    RustVoiceEdgeHttpClient,
    VoiceEdgeAnalysisResult,
    VoiceEdgeClient,
)
from all_about_llms.voice_agent.engine import GemmaKokoroLiveKitAgentEngine
from all_about_llms.voice_agent.engine import VoiceAgentEventSink
from all_about_llms.voice_agent.context import RealtimeContextPruner
from all_about_llms.voice_agent.reasoning import build_voice_reasoner
from all_about_llms.voice_agent.kokoro import kokoro_runtime_route
from all_about_llms.voice_agent.models import (
    RealtimeVoiceAgentConfig,
    RealtimeVoiceAgentEvent,
    RealtimeVoiceTurnInput,
    VoiceConversationTurn,
)


MAX_CANCELLED_RESPONSE_IDS = 512
_LAST_AUDIO_ARTIFACT_CLEANUP_MONOTONIC = -float("inf")


@dataclass(slots=True)
class VoiceAudioArtifact:
    uri: str
    relative_path: str
    sha256: str
    byte_count: int


@dataclass(slots=True)
class LiveKitVoiceAgentSessionState:
    run_id: UUID
    realtime_session_id: UUID
    room_name: str
    participant_identity: str | None = None
    voice: str = "af_heart"
    history: list[VoiceConversationTurn] = field(default_factory=list)
    active_turn_tasks: set[asyncio.Task] = field(default_factory=set)
    cancelled_response_ids: set[str] = field(default_factory=set)
    cancelled_response_id_order: deque[str] = field(default_factory=deque)
    data_message_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class VoiceTurnCaptureBuffer:
    def __init__(self, *, min_silence_frames: int, pre_roll_frames: int):
        self.min_silence_frames = max(1, min_silence_frames)
        self.pre_roll = deque(maxlen=max(0, pre_roll_frames))
        self.buffer = bytearray()
        self.speech_started = False
        self.silence_frames = 0
        self.started_monotonic: float | None = None
        self.last_flushed_started_monotonic: float | None = None

    @property
    def byte_count(self) -> int:
        return len(self.buffer)

    def ingest(
        self,
        pcm: bytes,
        *,
        speech_started_event: bool,
        is_speech: bool | None,
        now: float,
    ) -> bytes | None:
        if not self.speech_started:
            self.pre_roll.append(pcm)
            if not speech_started_event:
                return None
            self.speech_started = True
            self.started_monotonic = now
            self.buffer.clear()
            for frame in self.pre_roll:
                self.buffer.extend(frame)
            self.silence_frames = 0
        else:
            self.buffer.extend(pcm)

        if is_speech is True:
            self.silence_frames = 0
        elif is_speech is False:
            self.silence_frames += 1

        if self.silence_frames >= self.min_silence_frames:
            return self.flush()
        return None

    def flush(self) -> bytes | None:
        if not self.buffer:
            self.reset()
            return None
        payload = bytes(self.buffer)
        self.last_flushed_started_monotonic = self.started_monotonic
        self.reset()
        return payload

    def reset(self) -> None:
        self.pre_roll.clear()
        self.buffer.clear()
        self.speech_started = False
        self.silence_frames = 0
        self.started_monotonic = None


def build_livekit_voice_agent_server(settings: Settings | None = None):
    settings = settings or get_settings()
    try:
        from livekit import rtc
        from livekit.agents import (
            AgentServer,
            AutoSubscribe,
            JobContext,
            JobExecutorType,
            cli,
        )
    except ImportError as exc:
        raise ProviderConfigurationError(
            "Install the voice extra to run the LiveKit OpenRouter/Kokoro agent: "
            "uv pip install -e '.[voice]'"
        ) from exc

    server = AgentServer(
        job_executor_type=JobExecutorType.THREAD,
        ws_url=settings.realtime_livekit_url(),
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
        log_level=settings.livekit_agent_log_level,
    )

    @server.rtc_session(
        agent_name=settings.livekit_agent_name,
        on_request=_build_livekit_job_request_acceptor(settings),
    )
    async def gemma_kokoro_voice_agent(ctx: JobContext):
        state = _state_from_job_context(ctx, settings)
        ctx.log_context_fields = {
            "agent": settings.livekit_agent_name,
            "run_id": str(state.run_id),
            "realtime_session_id": str(state.realtime_session_id),
            "room_name": state.room_name,
        }
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

        config = RealtimeVoiceAgentConfig(
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
        publisher = LiveKitAudioTrackPublisher(
            room=ctx.room,
            participant=ctx.room.local_participant,
            sample_rate=config.sample_rate,
            audio_format=config.audio_format,
        )
        event_sink = _build_voice_agent_event_sink(room=ctx.room, settings=settings)
        voice_edge = await _preflight_voice_edge_client(
            _build_voice_edge_client(settings)
        )
        _register_voice_edge_cleanup(ctx, voice_edge)
        engine = GemmaKokoroLiveKitAgentEngine(
            config=config,
            gemma=build_voice_reasoner(settings, config),
            kokoro=_build_kokoro_streamer(settings),
            publisher=publisher,
            event_sink=event_sink,
        )

        @ctx.room.on("data_received")
        def on_data_received(data_or_packet, participant=None, *_args):
            data, participant_identity, topic = _livekit_data_message_parts(
                data_or_packet,
                participant=participant,
                args=_args,
            )
            asyncio.create_task(
                _handle_data_message_serialized(
                    engine=engine,
                    state=state,
                    payload=data,
                    participant_identity=participant_identity or "",
                    topic=topic,
                    event_sink=event_sink,
                    config=config,
                    settings=settings,
                    voice_edge=voice_edge,
                    agent_participant_identity=str(
                        getattr(
                            ctx.room.local_participant,
                            "identity",
                            settings.livekit_agent_name,
                        )
                    ),
                )
            )

        @ctx.room.on("track_subscribed")
        def on_track_subscribed(track: rtc.Track, _publication, participant):
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                asyncio.create_task(
                    _handle_audio_track(
                        rtc=rtc,
                        engine=engine,
                        state=state,
                        track=track,
                        participant_identity=_livekit_participant_identity(participant),
                        settings=settings,
                        config=config,
                        voice_edge=voice_edge,
                        event_sink=event_sink,
                    )
                )

        for participant in ctx.room.remote_participants.values():
            for publication in participant.track_publications.values():
                track = getattr(publication, "track", None)
                if track is not None and track.kind == rtc.TrackKind.KIND_AUDIO:
                    asyncio.create_task(
                        _handle_audio_track(
                            rtc=rtc,
                            engine=engine,
                            state=state,
                            track=track,
                            participant_identity=participant.identity,
                            settings=settings,
                            config=config,
                            voice_edge=voice_edge,
                            event_sink=event_sink,
                        )
                    )

        if _emit_startup_ready_for_bound_session(state):
            await event_sink.emit(
                RealtimeVoiceAgentEvent(
                    event_type="gemma_kokoro_voice_agent_ready",
                    run_id=state.run_id,
                    realtime_session_id=state.realtime_session_id,
                    payload=_voice_agent_ready_payload(
                        state=state,
                        config=config,
                        settings=settings,
                        voice_edge=voice_edge,
                        agent_participant_identity=str(
                            getattr(
                                ctx.room.local_participant,
                                "identity",
                                settings.livekit_agent_name,
                            )
                        ),
                        source="startup",
                    ),
                )
            )

    return server, cli


async def run_livekit_voice_agent_server(
    *,
    devmode: bool = False,
    unregistered: bool = False,
    settings: Settings | None = None,
) -> None:
    server, _cli = build_livekit_voice_agent_server(settings)
    await server.run(devmode=devmode, unregistered=unregistered)


def run_livekit_voice_agent_cli(settings: Settings | None = None) -> None:
    server, cli = build_livekit_voice_agent_server(settings)
    cli.run_app(server)


def _build_livekit_job_request_acceptor(settings: Settings):
    async def accept_livekit_job_request(job_request) -> None:
        metadata = _livekit_job_metadata(getattr(job_request, "job", None))
        agent_identity = (
            _metadata_str(metadata.get("agent_participant_identity"))
            or _metadata_str(metadata.get("agent_identity"))
            or settings.livekit_agent_name
        )
        participant_metadata = {
            "agent_name": settings.livekit_agent_name,
        }
        room_name = _metadata_str(metadata.get("room_name"))
        if room_name:
            participant_metadata["room_name"] = room_name
        await job_request.accept(
            identity=agent_identity,
            name=settings.livekit_agent_name,
            metadata=json.dumps(participant_metadata, separators=(",", ":")),
        )

    return accept_livekit_job_request


def _livekit_job_metadata(job: object | None) -> dict[str, object]:
    raw_metadata = getattr(job, "metadata", None)
    if not raw_metadata:
        return {}
    try:
        parsed = json.loads(str(raw_metadata))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _metadata_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _build_voice_agent_event_sink(*, room: object, settings: Settings):
    livekit_sink = LiveKitDataEventSink(room=room)
    if (
        not settings.voice_agent_backend_event_sink_enabled
        or not settings.voice_agent_backend_event_sink_url
    ):
        return livekit_sink
    try:
        backend_sink = BackendRealtimeVoiceEventSink(
            base_url=settings.voice_agent_backend_event_sink_url,
            timeout_seconds=(
                settings.voice_agent_backend_event_sink_timeout_seconds
            ),
        )
    except ValueError:
        return livekit_sink
    return CompositeVoiceAgentEventSink(
        required=[livekit_sink],
        best_effort=[backend_sink],
    )


def _register_voice_edge_cleanup(ctx: object, voice_edge: VoiceEdgeClient | None) -> None:
    if voice_edge is None:
        return
    add_shutdown_callback = getattr(ctx, "add_shutdown_callback", None)
    if not callable(add_shutdown_callback):
        raise RuntimeError(
            "LiveKit JobContext must expose add_shutdown_callback to clean up "
            "voice-edge transports"
        )
    closed = False
    closing = False

    async def close_voice_edge(_reason: str | None = None) -> None:
        nonlocal closed, closing
        if closed or closing:
            return
        closing = True
        try:
            await voice_edge.aclose()
        except Exception as exc:
            asyncio.get_running_loop().call_exception_handler(
                {
                    "message": "voice edge cleanup failed",
                    "exception": exc,
                }
            )
        else:
            closed = True
        finally:
            closing = False

    add_shutdown_callback(close_voice_edge)


async def _preflight_voice_edge_client(
    voice_edge: VoiceEdgeClient | None,
) -> VoiceEdgeClient | None:
    if isinstance(voice_edge, FallbackVoiceEdgeClient):
        try:
            await voice_edge.primary.health_check()
        except Exception as exc:
            await _close_voice_edge_after_failed_preflight(voice_edge.primary)
            if voice_edge.fallback.available:
                return await _preflight_voice_edge_client(voice_edge.fallback)
            raise RuntimeError(
                "Rust voice-edge HTTP sidecar health check failed and JSONL "
                "fallback is unavailable"
            ) from exc
        return voice_edge
    if voice_edge is not None:
        try:
            await voice_edge.health_check()
        except Exception as exc:
            await _close_voice_edge_after_failed_preflight(voice_edge)
            if isinstance(voice_edge, RustVoiceEdgeHttpClient):
                raise RuntimeError(
                    "Rust voice-edge HTTP sidecar health check failed"
                ) from exc
            raise RuntimeError("Rust voice-edge health check failed") from exc
    return voice_edge


async def _close_voice_edge_after_failed_preflight(voice_edge: VoiceEdgeClient) -> None:
    try:
        await voice_edge.aclose()
    except Exception as close_exc:
        asyncio.get_running_loop().call_exception_handler(
            {
                "message": "voice edge cleanup after failed preflight failed",
                "exception": close_exc,
            }
        )


def _livekit_participant_identity(participant) -> str:
    identity = getattr(participant, "identity", None)
    return str(identity).strip() if identity else ""


def _is_livekit_creator_identity(participant_identity: str | None) -> bool:
    identity = str(participant_identity or "").strip()
    return bool(identity) and identity != "unknown"


def _audio_track_targets_current_session(
    state: LiveKitVoiceAgentSessionState,
    *,
    participant_identity: str,
) -> bool:
    if not state.participant_identity:
        return False
    if not _is_livekit_creator_identity(participant_identity):
        return False
    return participant_identity == state.participant_identity


def _emit_startup_ready_for_bound_session(
    state: LiveKitVoiceAgentSessionState,
) -> bool:
    return _is_livekit_creator_identity(state.participant_identity)


async def _handle_data_message(
    *,
    engine: GemmaKokoroLiveKitAgentEngine,
    state: LiveKitVoiceAgentSessionState,
    payload: bytes,
    participant_identity: str,
    event_sink: VoiceAgentEventSink,
    config: RealtimeVoiceAgentConfig,
    settings: Settings,
    voice_edge: VoiceEdgeClient | None,
    agent_participant_identity: str,
    topic: str | None = None,
) -> None:
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raw = {"transcript": payload.decode("utf-8", errors="replace")}
    if not isinstance(raw, dict):
        return
    if raw.get("type") == "voice_agent_presence_probe":
        if _data_message_targets_current_session(
            raw,
            state,
            participant_identity=participant_identity,
            topic=topic,
            agent_participant_identity=agent_participant_identity,
            settings=settings,
        ):
            await event_sink.emit(
                RealtimeVoiceAgentEvent(
                    event_type="gemma_kokoro_voice_agent_ready",
                    run_id=state.run_id,
                    realtime_session_id=state.realtime_session_id,
                    payload=_voice_agent_ready_payload(
                        state=state,
                        config=config,
                        settings=settings,
                        voice_edge=voice_edge,
                        agent_participant_identity=agent_participant_identity,
                        source="presence_probe",
                        probe_id=(
                            str(raw["probe_id"]) if raw.get("probe_id") else None
                        ),
                    ),
                )
            )
        return
    if raw.get("type") == "voice_interrupt":
        if _data_message_targets_current_session(
            raw,
            state,
            participant_identity=participant_identity,
            topic=topic,
            agent_participant_identity=agent_participant_identity,
            settings=settings,
        ):
            await _handle_interrupt_message(
                engine=engine,
                state=state,
                raw=raw,
                participant_identity=participant_identity,
                event_sink=event_sink,
            )
        return
    message_type = raw.get("type")
    if message_type not in {None, "voice_turn", "transcript_turn"}:
        return
    if not _data_message_targets_current_session(
        raw,
        state,
        participant_identity=participant_identity,
        topic=topic,
        agent_participant_identity=agent_participant_identity,
        settings=settings,
    ):
        return
    transcript = raw.get("transcript")
    if message_type == "transcript_turn":
        if not isinstance(transcript, str) or not transcript.strip():
            await event_sink.emit(
                RealtimeVoiceAgentEvent(
                    event_type="voice_text_turn_rejected",
                    run_id=state.run_id,
                    realtime_session_id=state.realtime_session_id,
                    payload={
                        "turn_id": str(raw.get("turn_id") or ""),
                        "room_name": state.room_name,
                        "participant_identity": participant_identity,
                        "reason": "empty_transcript",
                    },
                )
            )
            return
        transcript = transcript.strip()
    elif transcript is not None and not isinstance(transcript, str):
        transcript = str(transcript)
    turn = RealtimeVoiceTurnInput(
        run_id=state.run_id,
        realtime_session_id=state.realtime_session_id,
        room_name=state.room_name,
        participant_identity=participant_identity,
        turn_id=str(raw.get("turn_id") or uuid4()),
        transcript=transcript,
        audio_ref=raw.get("audio_ref"),
        audio_duration_ms=int(raw.get("audio_duration_ms") or 0),
        interrupted=bool(raw.get("interrupted") or False),
        metadata={
            "source": "livekit_data_message",
            "topic": raw.get("topic"),
            "message_type": message_type or "raw_transcript",
            "input_modality": "text" if message_type == "transcript_turn" else "voice",
        },
    )
    await _emit_voice_turn_committed(
        event_sink=event_sink,
        state=state,
        turn=turn,
        windowing=(
            "livekit_data_transcript"
            if message_type == "transcript_turn"
            else "livekit_data_message"
        ),
    )
    _schedule_turn(
        engine=engine,
        state=state,
        turn=turn,
        voice=str(raw.get("voice") or state.voice),
        config=config,
        event_sink=event_sink,
    )


async def _handle_data_message_serialized(
    *,
    engine: GemmaKokoroLiveKitAgentEngine,
    state: LiveKitVoiceAgentSessionState,
    payload: bytes,
    participant_identity: str,
    event_sink: VoiceAgentEventSink,
    config: RealtimeVoiceAgentConfig,
    settings: Settings,
    voice_edge: VoiceEdgeClient | None,
    agent_participant_identity: str,
    topic: str | None = None,
) -> None:
    async with state.data_message_lock:
        await _handle_data_message(
            engine=engine,
            state=state,
            payload=payload,
            participant_identity=participant_identity,
            event_sink=event_sink,
            config=config,
            settings=settings,
            voice_edge=voice_edge,
            agent_participant_identity=agent_participant_identity,
            topic=topic,
        )


async def _handle_interrupt_message(
    *,
    engine: GemmaKokoroLiveKitAgentEngine,
    state: LiveKitVoiceAgentSessionState,
    raw: dict[str, object],
    participant_identity: str,
    event_sink: VoiceAgentEventSink,
) -> None:
    active_response_id = engine.active_response_id
    raw_response_id = raw.get("interrupted_response_id") or raw.get("response_id")
    interrupted_response_id = (
        str(raw_response_id)
        if raw_response_id
        else active_response_id
    )
    reason = str(raw.get("reason") or "creator interrupt")
    interrupt_id = str(raw.get("interrupt_id") or "") or None
    required_runtime_actions = raw.get("required_runtime_actions")
    if not interrupted_response_id:
        await event_sink.emit(
            RealtimeVoiceAgentEvent(
                event_type="voice_interrupt_no_active_response",
                run_id=state.run_id,
                realtime_session_id=state.realtime_session_id,
                payload={
                    "room_name": state.room_name,
                    "participant_identity": participant_identity,
                    "interrupt_id": interrupt_id,
                    "reason": reason,
                    "control_event_id": raw.get("control_event_id"),
                    "expected_agent_identity": raw.get("expected_agent_identity"),
                    "required_runtime_actions": required_runtime_actions,
                    "drop_outbound_audio_packets": bool(
                        raw.get("drop_outbound_audio_packets") or False
                    ),
                    "cancel_gemma": False,
                    "clear_kokoro_buffers": False,
                    "stop_livekit_audio": False,
                    "canceled": False,
                },
            )
        )
        return
    _remember_cancelled_response_id(state, interrupted_response_id)
    canceled = await engine.cancel_response(interrupted_response_id, reason)
    await event_sink.emit(
        RealtimeVoiceAgentEvent(
            event_type="voice_manual_interrupt_received",
            run_id=state.run_id,
            realtime_session_id=state.realtime_session_id,
            payload={
                "room_name": state.room_name,
                "participant_identity": participant_identity,
                "interrupt_id": interrupt_id,
                "response_id": interrupted_response_id,
                "reason": reason,
                "control_event_id": raw.get("control_event_id"),
                "expected_agent_identity": raw.get("expected_agent_identity"),
                "required_runtime_actions": required_runtime_actions,
                "drop_outbound_audio_packets": bool(
                    raw.get("drop_outbound_audio_packets") or False
                ),
                "cancel_gemma": True,
                "clear_kokoro_buffers": True,
                "stop_livekit_audio": True,
                "canceled": canceled,
            },
        )
    )


def _data_message_targets_current_session(
    raw: dict[str, object],
    state: LiveKitVoiceAgentSessionState,
    *,
    participant_identity: str,
    topic: str | None,
    agent_participant_identity: str | None = None,
    settings: Settings | None = None,
) -> bool:
    raw_run_id = raw.get("run_id")
    raw_session_id = raw.get("realtime_session_id")
    if topic != "agent.voice.control":
        return False
    if raw_run_id is None or raw_session_id is None:
        return False
    if not state.participant_identity:
        return _bind_state_from_trusted_control_message(
            raw,
            state,
            participant_identity=participant_identity,
            agent_participant_identity=agent_participant_identity,
            settings=settings,
        )
    if str(raw_run_id) != str(state.run_id):
        return False
    if str(raw_session_id) != str(state.realtime_session_id):
        return False
    if not state.participant_identity:
        return False
    if participant_identity != state.participant_identity:
        return False
    return True


def _bind_state_from_trusted_control_message(
    raw: dict[str, object],
    state: LiveKitVoiceAgentSessionState,
    *,
    participant_identity: str,
    agent_participant_identity: str | None,
    settings: Settings | None,
) -> bool:
    if not _is_livekit_creator_identity(participant_identity):
        return False
    expected_agent_identity = raw.get("expected_agent_identity")
    if (
        not expected_agent_identity
        or not agent_participant_identity
        or str(expected_agent_identity) != str(agent_participant_identity)
    ):
        return False
    if str(raw.get("room_name") or "") != state.room_name:
        return False
    try:
        run_id = UUID(str(raw["run_id"]))
        realtime_session_id = UUID(str(raw["realtime_session_id"]))
    except (KeyError, TypeError, ValueError):
        return False
    if not verify_livekit_control_binding_token(
        raw.get("control_binding_token"),
        settings.livekit_api_secret if settings is not None else None,
        run_id=str(run_id),
        realtime_session_id=str(realtime_session_id),
        room_name=state.room_name,
        participant_identity=participant_identity,
        agent_identity=str(agent_participant_identity),
    ):
        return False

    state.run_id = run_id
    state.realtime_session_id = realtime_session_id
    state.participant_identity = participant_identity
    raw_voice = raw.get("voice")
    if isinstance(raw_voice, str) and raw_voice.strip():
        state.voice = raw_voice.strip()
    return True


def _livekit_data_message_topic(args: tuple[object, ...]) -> str | None:
    for item in reversed(args):
        if isinstance(item, str):
            return item
        topic = getattr(item, "topic", None)
        if isinstance(topic, str):
            return topic
    return None


def _livekit_data_message_parts(
    data_or_packet: object,
    *,
    participant: object | None,
    args: tuple[object, ...],
) -> tuple[bytes, str | None, str | None]:
    raw_data = getattr(data_or_packet, "data", data_or_packet)
    if isinstance(raw_data, bytes):
        data = raw_data
    else:
        data = bytes(raw_data)
    packet_participant = participant or getattr(data_or_packet, "participant", None)
    participant_identity = _livekit_participant_identity(packet_participant)
    if participant_identity is None:
        participant_identity = _metadata_str(
            getattr(data_or_packet, "participant_identity", None)
        )
    topic = _metadata_str(getattr(data_or_packet, "topic", None))
    if topic is None:
        topic = _livekit_data_message_topic(args)
    return data, participant_identity, topic


def _voice_agent_ready_payload(
    *,
    state: LiveKitVoiceAgentSessionState,
    config: RealtimeVoiceAgentConfig,
    settings: Settings,
    voice_edge: VoiceEdgeClient | None,
    agent_participant_identity: str,
    source: str,
    probe_id: str | None = None,
) -> dict[str, object]:
    return {
        "run_id": str(state.run_id),
        "realtime_session_id": str(state.realtime_session_id),
        "room_name": state.room_name,
        "agent_name": settings.livekit_agent_name,
        "agent_participant_identity": agent_participant_identity,
        "presence_probe_ack": source == "presence_probe",
        "probe_id": probe_id,
        "source": source,
        "audio_input_model": config.audio_input_model,
        "reasoning_model": config.reasoning_model,
        "audio_output_model": config.audio_output_model,
        "voice_edge_enabled": voice_edge is not None,
        "voice_edge_binary_path": (
            str(getattr(voice_edge, "binary_path", ""))
            if voice_edge is not None
            and getattr(voice_edge, "binary_path", None) is not None
            else None
        ),
        "voice_edge_http_url": (
            getattr(voice_edge, "base_url", None) if voice_edge is not None else None
        ),
        "voice_edge_process_mode": (
            voice_edge.transport if voice_edge is not None else None
        ),
        "vad_backend_requested": (
            voice_edge.vad_backend if voice_edge is not None else None
        ),
        "vad_backend_effective": (
            voice_edge.vad_backend_effective if voice_edge is not None else None
        ),
        "vad_model_effective": (
            voice_edge.vad_model_effective if voice_edge is not None else None
        ),
        "vad_model_target": settings.gemma4_realtime_rust_vad_model,
        "vad_model_path_configured": bool(settings.rust_voice_edge_vad_model_path),
        "vad_fallback_allowed": settings.rust_voice_edge_allow_vad_fallback,
        "vad_fallback_reason": (
            voice_edge.vad_fallback_reason if voice_edge is not None else None
        ),
    }


async def _handle_audio_track(
    *,
    rtc,
    engine: GemmaKokoroLiveKitAgentEngine,
    state: LiveKitVoiceAgentSessionState,
    track,
    participant_identity: str,
    settings: Settings,
    config: RealtimeVoiceAgentConfig,
    voice_edge: VoiceEdgeClient | None,
    event_sink: VoiceAgentEventSink,
) -> None:
    if not _audio_track_targets_current_session(
        state,
        participant_identity=participant_identity,
    ):
        return
    audio_stream = rtc.AudioStream(
        track,
        sample_rate=settings.gemma4_realtime_sample_rate,
        num_channels=1,
    )
    max_seconds = settings.gemma4_realtime_max_audio_seconds_per_turn
    max_bytes = settings.gemma4_realtime_sample_rate * 2 * max_seconds
    buffer = bytearray()
    started = time.monotonic()
    capture = VoiceTurnCaptureBuffer(
        min_silence_frames=settings.rust_voice_edge_min_silence_frames,
        pre_roll_frames=settings.rust_voice_edge_turn_pre_roll_frames,
    )
    sequence = 0
    try:
        await _emit_voice_agent_media_bridge_ready(
            event_sink=event_sink,
            state=state,
            participant_identity=participant_identity,
            settings=settings,
            voice_edge=voice_edge,
        )
        async for frame_event in audio_stream:
            frame = frame_event.frame
            sequence += 1
            pcm = bytes(frame.data)
            active_response_id = engine.active_response_id
            if voice_edge is not None:
                now = time.monotonic()
                try:
                    edge_result = await voice_edge.analyze_pcm_frame(
                        session_id=str(state.realtime_session_id),
                        response_id=active_response_id,
                        agent_speaking=active_response_id is not None,
                        sequence=sequence,
                        pcm_s16le=pcm,
                        timestamp_ms=int((now - started) * 1000),
                    )
                    await _emit_voice_edge_events(
                        event_sink=event_sink,
                        state=state,
                        participant_identity=participant_identity,
                        result=edge_result,
                    )
                except Exception as exc:
                    await event_sink.emit(
                        RealtimeVoiceAgentEvent(
                            event_type="voice_edge_error",
                            run_id=state.run_id,
                            realtime_session_id=state.realtime_session_id,
                            payload={
                                "room_name": state.room_name,
                                "participant_identity": participant_identity,
                                "response_id": active_response_id,
                                "error": str(exc),
                            },
                        )
                    )
                else:
                    if (
                        edge_result.cancellation_ack is not None
                        and edge_result.cancellation_ack.response_id
                        not in state.cancelled_response_ids
                    ):
                        _remember_cancelled_response_id(
                            state,
                            edge_result.cancellation_ack.response_id
                        )
                        await engine.cancel_response(
                            edge_result.cancellation_ack.response_id,
                            edge_result.cancellation_ack.reason,
                        )
                    captured = capture.ingest(
                        pcm,
                        speech_started_event=_has_voice_edge_event(
                            edge_result,
                            "voice_user_speech_started",
                        )
                        or edge_result.cancellation_ack is not None,
                        is_speech=_latest_vad_is_speech(edge_result),
                        now=now,
                    )
                    if captured is not None:
                        turn = _build_voice_audio_turn(
                            settings=settings,
                            state=state,
                            participant_identity=participant_identity,
                            audio_pcm=captured,
                            duration_ms=_capture_duration_ms(capture, now),
                            windowing="rust_voice_edge_vad_silence",
                        )
                        await _emit_voice_turn_committed(
                            event_sink=event_sink,
                            state=state,
                            turn=turn,
                            windowing="rust_voice_edge_vad_silence",
                        )
                        _schedule_turn(
                            engine=engine,
                            state=state,
                            turn=turn,
                            voice=state.voice,
                            config=config,
                            event_sink=event_sink,
                        )
                        started = time.monotonic()
                    elif capture.byte_count >= max_bytes:
                        captured = capture.flush()
                        if captured is not None:
                            turn = _build_voice_audio_turn(
                                settings=settings,
                                state=state,
                                participant_identity=participant_identity,
                                audio_pcm=captured[:max_bytes],
                                duration_ms=max_seconds * 1000,
                                windowing="rust_voice_edge_max_audio_seconds",
                            )
                            await _emit_voice_turn_committed(
                                event_sink=event_sink,
                                state=state,
                                turn=turn,
                                windowing="rust_voice_edge_max_audio_seconds",
                            )
                            _schedule_turn(
                                engine=engine,
                                state=state,
                                turn=turn,
                                voice=state.voice,
                                config=config,
                                event_sink=event_sink,
                            )
                            started = time.monotonic()
                continue

            buffer.extend(pcm)
            if len(buffer) >= max_bytes:
                duration_ms = int((time.monotonic() - started) * 1000)
                turn = _build_voice_audio_turn(
                    settings=settings,
                    state=state,
                    participant_identity=participant_identity,
                    audio_pcm=bytes(buffer[:max_bytes]),
                    duration_ms=min(duration_ms, max_seconds * 1000),
                    windowing="max_audio_seconds_per_turn",
                )
                await _emit_voice_turn_committed(
                    event_sink=event_sink,
                    state=state,
                    turn=turn,
                    windowing="max_audio_seconds_per_turn",
                )
                _schedule_turn(
                    engine=engine,
                    state=state,
                    turn=turn,
                    voice=state.voice,
                    config=config,
                    event_sink=event_sink,
                )
                buffer.clear()
                started = time.monotonic()
    finally:
        await audio_stream.aclose()


async def _emit_voice_agent_media_bridge_ready(
    *,
    event_sink: VoiceAgentEventSink,
    state: LiveKitVoiceAgentSessionState,
    participant_identity: str,
    settings: Settings,
    voice_edge: VoiceEdgeClient | None,
) -> None:
    try:
        await event_sink.emit(
            RealtimeVoiceAgentEvent(
                event_type="voice_agent_media_bridge_ready",
                run_id=state.run_id,
                realtime_session_id=state.realtime_session_id,
                payload=_voice_agent_media_bridge_payload(
                    state=state,
                    participant_identity=participant_identity,
                    settings=settings,
                    voice_edge=voice_edge,
                ),
            )
        )
    except Exception as exc:
        asyncio.get_running_loop().call_exception_handler(
            {
                "message": "voice-agent media bridge proof emit failed",
                "exception": exc,
            }
        )


def _voice_agent_media_bridge_payload(
    *,
    state: LiveKitVoiceAgentSessionState,
    participant_identity: str,
    settings: Settings,
    voice_edge: VoiceEdgeClient | None,
) -> dict[str, object]:
    return {
        "run_id": str(state.run_id),
        "realtime_session_id": str(state.realtime_session_id),
        "room_name": state.room_name,
        "participant_identity": participant_identity,
        "media_bridge": "livekit_audio_track_to_rust_voice_edge",
        "livekit_track_kind": "audio",
        "sample_rate": settings.gemma4_realtime_sample_rate,
        "frame_ms": settings.rust_voice_edge_frame_ms,
        "voice_edge_enabled": voice_edge is not None,
        "voice_edge_process_mode": (
            voice_edge.transport if voice_edge is not None else None
        ),
        "vad_backend_requested": (
            voice_edge.vad_backend if voice_edge is not None else None
        ),
        "vad_backend_effective": (
            voice_edge.vad_backend_effective if voice_edge is not None else None
        ),
        "vad_model_effective": (
            voice_edge.vad_model_effective if voice_edge is not None else None
        ),
        "audio_windowing": (
            "rust_voice_edge_vad_silence"
            if voice_edge is not None
            else "max_audio_seconds_per_turn"
        ),
    }


async def _emit_voice_edge_events(
    *,
    event_sink: VoiceAgentEventSink,
    state: LiveKitVoiceAgentSessionState,
    participant_identity: str,
    result: VoiceEdgeAnalysisResult,
) -> None:
    for event in result.events:
        if not _should_forward_voice_edge_event(event):
            continue
        safe_event = safe_realtime_metadata(event)
        safe_final_state = safe_realtime_metadata(result.final_state)
        await event_sink.emit(
            RealtimeVoiceAgentEvent(
                event_type=str(event.get("event_type") or "voice_edge_event"),
                run_id=state.run_id,
                realtime_session_id=state.realtime_session_id,
                payload={
                    "room_name": state.room_name,
                    "participant_identity": participant_identity,
                    "voice_edge_session_id": result.session_id,
                    "voice_edge_request_id": result.request_id,
                    "voice_edge_event": safe_event,
                    "voice_edge_final_state": safe_final_state,
                },
            )
        )


def _should_forward_voice_edge_event(event: dict[str, object]) -> bool:
    return event.get("event_type") != "voice_vad_frame_analyzed"


def _latest_vad_is_speech(result: VoiceEdgeAnalysisResult) -> bool | None:
    for event in reversed(result.events):
        if event.get("event_type") == "voice_vad_frame_analyzed":
            value = event.get("is_speech")
            return bool(value) if value is not None else None
    return None


def _has_voice_edge_event(result: VoiceEdgeAnalysisResult, event_type: str) -> bool:
    return any(event.get("event_type") == event_type for event in result.events)


def _remember_cancelled_response_id(
    state: LiveKitVoiceAgentSessionState, response_id: str
) -> None:
    if response_id in state.cancelled_response_ids:
        return
    state.cancelled_response_ids.add(response_id)
    state.cancelled_response_id_order.append(response_id)
    while len(state.cancelled_response_ids) > MAX_CANCELLED_RESPONSE_IDS:
        expired_response_id = state.cancelled_response_id_order.popleft()
        state.cancelled_response_ids.discard(expired_response_id)


def _capture_duration_ms(capture: VoiceTurnCaptureBuffer, now: float) -> int:
    started = capture.last_flushed_started_monotonic or now
    return max(0, int((now - started) * 1000))


def _build_voice_audio_turn(
    *,
    settings: Settings,
    state: LiveKitVoiceAgentSessionState,
    participant_identity: str,
    audio_pcm: bytes,
    duration_ms: int,
    windowing: str,
) -> RealtimeVoiceTurnInput:
    turn_id = str(uuid4())
    artifact, artifact_skip_reason = _persist_voice_audio_artifact(
        settings=settings,
        state=state,
        turn_id=turn_id,
        audio_pcm=audio_pcm,
    )
    metadata: dict[str, object] = {
        "source": "livekit_audio_window",
        "windowing": windowing,
        "input_modality": "voice",
        "audio_artifact_persisted": artifact is not None,
    }
    audio_ref: str | None = None
    if artifact is not None:
        audio_ref = artifact.uri
        metadata.update(
            {
                "audio_artifact_uri": artifact.uri,
                "audio_artifact_relative_path": artifact.relative_path,
                "audio_artifact_sha256": artifact.sha256,
                "audio_artifact_bytes": artifact.byte_count,
            }
        )
    elif artifact_skip_reason:
        metadata["audio_artifact_skip_reason"] = artifact_skip_reason
    return RealtimeVoiceTurnInput(
        run_id=state.run_id,
        realtime_session_id=state.realtime_session_id,
        room_name=state.room_name,
        participant_identity=participant_identity,
        turn_id=turn_id,
        audio_ref=audio_ref,
        audio_pcm=audio_pcm,
        audio_duration_ms=duration_ms,
        metadata=metadata,
    )


def _persist_voice_audio_artifact(
    *,
    settings: Settings,
    state: LiveKitVoiceAgentSessionState,
    turn_id: str,
    audio_pcm: bytes,
) -> tuple[VoiceAudioArtifact | None, str | None]:
    if not settings.voice_agent_persist_audio_artifacts:
        return None, "disabled"
    if not audio_pcm:
        return None, "empty_audio"
    if len(audio_pcm) > settings.voice_agent_audio_artifact_max_bytes:
        return None, "audio_exceeds_max_bytes"

    relative_path = (
        Path("voice-audio")
        / str(state.run_id)
        / str(state.realtime_session_id)
        / f"{turn_id}.pcm"
    )
    target = settings.artifacts_root / relative_path
    try:
        _maybe_cleanup_expired_voice_audio_artifacts(settings)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_target = target.with_name(f"{target.name}.tmp")
        temp_target.write_bytes(audio_pcm)
        temp_target.replace(target)
    except OSError as exc:
        return None, f"write_failed:{type(exc).__name__}"

    return (
        VoiceAudioArtifact(
            uri=f"artifact://{relative_path.as_posix()}",
            relative_path=relative_path.as_posix(),
            sha256=hashlib.sha256(audio_pcm).hexdigest(),
            byte_count=len(audio_pcm),
        ),
        None,
    )


def _maybe_cleanup_expired_voice_audio_artifacts(settings: Settings) -> None:
    global _LAST_AUDIO_ARTIFACT_CLEANUP_MONOTONIC
    now = time.monotonic()
    if (
        now - _LAST_AUDIO_ARTIFACT_CLEANUP_MONOTONIC
        < settings.voice_agent_audio_artifact_cleanup_interval_seconds
    ):
        return
    _LAST_AUDIO_ARTIFACT_CLEANUP_MONOTONIC = now
    _cleanup_expired_voice_audio_artifacts(settings)


def _cleanup_expired_voice_audio_artifacts(
    settings: Settings,
    *,
    wall_time: float | None = None,
) -> int:
    root = settings.artifacts_root / "voice-audio"
    if not root.exists():
        return 0
    cutoff = (wall_time if wall_time is not None else time.time()) - (
        settings.voice_agent_audio_artifact_retention_days * 24 * 60 * 60
    )
    removed = 0
    for path in root.rglob("*.pcm"):
        try:
            if path.stat().st_mtime >= cutoff:
                continue
            path.unlink()
            removed += 1
        except OSError:
            continue
    _remove_empty_voice_audio_dirs(root)
    return removed


def _remove_empty_voice_audio_dirs(root: Path) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        if not path.is_dir():
            continue
        try:
            path.rmdir()
        except OSError:
            continue


async def _emit_voice_turn_committed(
    *,
    event_sink: VoiceAgentEventSink,
    state: LiveKitVoiceAgentSessionState,
    turn: RealtimeVoiceTurnInput,
    windowing: str,
) -> None:
    await event_sink.emit(
        RealtimeVoiceAgentEvent(
            event_type="voice_user_turn_committed",
            run_id=state.run_id,
            realtime_session_id=state.realtime_session_id,
            payload={
                "turn_id": str(turn.turn_id),
                "room_name": state.room_name,
                "participant_identity": turn.participant_identity,
                "transcript": turn.transcript,
                "input_modality": turn.metadata.get("input_modality") or "voice",
                "audio_duration_ms": turn.audio_duration_ms,
                "audio_bytes": len(turn.audio_pcm or b""),
                "audio_ref": turn.audio_ref,
                "audio_artifact_uri": turn.metadata.get("audio_artifact_uri"),
                "audio_artifact_relative_path": turn.metadata.get(
                    "audio_artifact_relative_path"
                ),
                "audio_artifact_sha256": turn.metadata.get("audio_artifact_sha256"),
                "audio_artifact_bytes": turn.metadata.get("audio_artifact_bytes"),
                "audio_artifact_persisted": turn.metadata.get(
                    "audio_artifact_persisted"
                ),
                "audio_artifact_skip_reason": turn.metadata.get(
                    "audio_artifact_skip_reason"
                ),
                "windowing": windowing,
            },
        )
    )


def _schedule_turn(
    *,
    engine: GemmaKokoroLiveKitAgentEngine,
    state: LiveKitVoiceAgentSessionState,
    turn: RealtimeVoiceTurnInput,
    voice: str,
    config: RealtimeVoiceAgentConfig,
    event_sink: VoiceAgentEventSink,
) -> None:
    loop = asyncio.get_running_loop()
    task = asyncio.create_task(
        _handle_turn(
            engine=engine,
            state=state,
            turn=turn,
            voice=voice,
            config=config,
            event_sink=event_sink,
        )
    )
    state.active_turn_tasks.add(task)

    def _on_done(done_task: asyncio.Task) -> None:
        state.active_turn_tasks.discard(done_task)
        try:
            done_task.result()
        except Exception as exc:
            loop.call_exception_handler(
                {
                    "message": "voice turn task failed",
                    "exception": exc,
                    "task": done_task,
                }
            )

    task.add_done_callback(_on_done)


async def _handle_turn(
    *,
    engine: GemmaKokoroLiveKitAgentEngine,
    state: LiveKitVoiceAgentSessionState,
    turn: RealtimeVoiceTurnInput,
    voice: str,
    config: RealtimeVoiceAgentConfig,
    event_sink: VoiceAgentEventSink,
) -> None:
    result = await engine.handle_turn(turn, state.history, voice=voice)
    if result.canceled or result.failed:
        state.history.append(
            VoiceConversationTurn(
                turn_id=turn.turn_id,
                role="user",
                text=turn.transcript,
                audio_ref=turn.audio_ref,
                audio_duration_ms=turn.audio_duration_ms,
                interrupted=result.canceled,
                heard_by_user=False,
                metadata={
                    "voice_turn_failed": result.failed,
                    "failure_stage": result.failure_stage,
                    "failure_reason": result.failure_reason,
                },
            )
        )
        await _compact_session_history(
            state=state,
            config=config,
            event_sink=event_sink,
        )
        return
    state.history.extend(
        [
            VoiceConversationTurn(
                turn_id=turn.turn_id,
                role="user",
                text=result.transcript or turn.transcript,
                audio_ref=turn.audio_ref,
                audio_duration_ms=turn.audio_duration_ms,
                interrupted=turn.interrupted,
            ),
            VoiceConversationTurn(
                turn_id=result.response_id,
                role="assistant",
                text=result.assistant_text,
                interrupted=False,
                heard_by_user=True,
                metadata={"audio_chunk_count": result.audio_chunk_count},
            ),
        ]
    )
    await _compact_session_history(
        state=state,
        config=config,
        event_sink=event_sink,
    )


async def _compact_session_history(
    *,
    state: LiveKitVoiceAgentSessionState,
    config: RealtimeVoiceAgentConfig,
    event_sink: VoiceAgentEventSink,
) -> None:
    pruned = RealtimeContextPruner(config).prune(state.history)
    state.history = pruned.turns
    if not pruned.pruned:
        return
    await event_sink.emit(
        RealtimeVoiceAgentEvent(
            event_type="voice_session_history_pruned",
            run_id=state.run_id,
            realtime_session_id=state.realtime_session_id,
            payload={
                "room_name": state.room_name,
                "pruned_turn_ids": pruned.pruned_turn_ids,
                "raw_audio_turns_before": pruned.raw_audio_turns_before,
                "raw_audio_turns_after": pruned.raw_audio_turns_after,
                "session_history_turn_count": len(state.history),
                "context_window_turns": config.context_window_turns,
                "prune_after_turns": config.prune_after_turns,
                "replacement_strategy": "transcript_plus_summary",
                "max_raw_audio_seconds_per_turn": (
                    config.max_raw_audio_seconds_per_turn
                ),
            },
        )
    )


def _state_from_job_context(
    ctx,
    settings: Settings,
) -> LiveKitVoiceAgentSessionState:
    metadata: dict[str, object] = {}
    if getattr(ctx.job, "metadata", None):
        try:
            metadata = json.loads(ctx.job.metadata)
        except json.JSONDecodeError:
            metadata = {}
    room_name = getattr(getattr(ctx.job, "room", None), "name", None) or getattr(
        ctx.room,
        "name",
        "unknown-room",
    )
    return LiveKitVoiceAgentSessionState(
        run_id=_uuid_from_metadata(metadata.get("run_id")) or uuid4(),
        realtime_session_id=(
            _uuid_from_metadata(metadata.get("realtime_session_id")) or uuid4()
        ),
        room_name=str(metadata.get("room_name") or room_name),
        participant_identity=(
            str(metadata["participant_identity"])
            if metadata.get("participant_identity")
            else None
        ),
        voice=str(metadata.get("voice") or settings.gemma4_realtime_default_voice),
    )


def _uuid_from_metadata(value: object) -> UUID | None:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _build_kokoro_streamer(settings: Settings):
    route = kokoro_runtime_route(settings)
    endpoint_url = route.endpoint_url
    if endpoint_url:
        return HuggingFaceKokoroTTSStreamer(
            token=settings.hf_token,
            endpoint_url=endpoint_url,
            model_id=settings.gemma4_realtime_audio_output_model,
            chunk_bytes=settings.kokoro_tts_chunk_bytes,
            timeout_seconds=settings.kokoro_tts_timeout_seconds,
        )
    if not route.ready:
        raise ProviderConfigurationError(route.configuration_error())
    return LocalKokoroTTSStreamer(
        voice=settings.gemma4_realtime_default_voice,
        chunk_bytes=settings.kokoro_tts_chunk_bytes,
    )


def _build_voice_edge_client(settings: Settings) -> VoiceEdgeClient | None:
    client_kwargs = {
        "timeout_seconds": settings.rust_voice_edge_timeout_seconds,
        "sample_rate": settings.gemma4_realtime_sample_rate,
        "frame_ms": settings.rust_voice_edge_frame_ms,
        "vad_backend": settings.rust_voice_edge_vad_backend,
        "target_vad_model": settings.gemma4_realtime_rust_vad_model,
        "vad_model_path": settings.rust_voice_edge_vad_model_path,
        "allow_vad_fallback": settings.rust_voice_edge_allow_vad_fallback,
        "vad_threshold": settings.rust_voice_edge_vad_threshold,
        "vad_probability_threshold": settings.rust_voice_edge_vad_probability_threshold,
        "vad_session_pool_size": settings.rust_voice_edge_vad_session_pool_size,
        "vad_stream_state_cache_size": settings.rust_voice_edge_vad_stream_state_cache_size,
        "min_speech_frames": settings.rust_voice_edge_min_speech_frames,
        "max_inbound_buffer_bytes": settings.rust_voice_edge_max_inbound_buffer_bytes,
        "max_outbound_buffer_bytes": settings.rust_voice_edge_max_outbound_buffer_bytes,
    }
    fallback = PersistentRustVoiceEdgeClient(
        binary_path=settings.rust_voice_edge_binary_path,
        **client_kwargs,
    )
    if settings.rust_voice_edge_http_url:
        primary = RustVoiceEdgeHttpClient(
            base_url=settings.rust_voice_edge_http_url,
            **client_kwargs,
        )
        if fallback.available:
            return FallbackVoiceEdgeClient(primary=primary, fallback=fallback)
        return primary
    return fallback if fallback.available else None
