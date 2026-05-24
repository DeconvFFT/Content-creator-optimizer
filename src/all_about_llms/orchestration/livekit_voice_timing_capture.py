import asyncio
import json
import math
import struct
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from all_about_llms.config import Settings, get_settings
from all_about_llms.contracts import RealtimeSessionRecord, RunEvent
from all_about_llms.providers.realtime import _mint_livekit_join_token
from all_about_llms.realtime_safety import safe_realtime_metadata
from all_about_llms.voice_agent.control_binding import (
    build_livekit_control_binding_token,
)


AGENT_EVENT_TOPIC = "agent.voice.event"
AGENT_CONTROL_TOPIC = "agent.voice.control"


class LiveKitVoiceTimingCaptureRequest(BaseModel):
    realtime_session_id: UUID | None = None
    timeout_seconds: float = Field(default=45.0, gt=0)
    audio_probe_duration_ms: int = Field(default=1200, ge=0)
    post_speech_silence_ms: int = Field(default=900, ge=0)
    interrupt_on_first_output: bool = True
    transcript: str | None = None
    voice: str | None = None


class LiveKitVoiceTimingCaptureResult(BaseModel):
    run_id: UUID
    realtime_session_id: UUID | None = None
    status: str
    captured_event_count: int = 0
    skipped_duplicate_event_count: int = 0
    captured_event_ids: list[int] = Field(default_factory=list)
    captured_event_types: list[str] = Field(default_factory=list)
    observed_agent_event_types: list[str] = Field(default_factory=list)
    audio_probe_published: bool = False
    transcript_turn_sent: bool = False
    interrupt_sent: bool = False
    blocked_reason: str | None = None
    summary: str


class HeadlessLiveKitAgentEvent(BaseModel):
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    sender_identity: str | None = None
    topic: str | None = None


class HeadlessLiveKitCaptureInput(BaseModel):
    run_id: UUID
    realtime_session_id: UUID
    livekit_url: str
    livekit_token: str
    control_binding_token: str | None = None
    room_name: str
    participant_identity: str
    agent_identity: str
    voice: str | None = None
    transcript: str | None = None
    timeout_seconds: float
    audio_probe_duration_ms: int
    post_speech_silence_ms: int
    interrupt_on_first_output: bool
    sample_rate: int
    frame_ms: int


class HeadlessLiveKitCaptureResult(BaseModel):
    connected: bool = False
    audio_probe_published: bool = False
    transcript_turn_sent: bool = False
    interrupt_sent: bool = False
    observed_agent_event_types: list[str] = Field(default_factory=list)
    observed_response_id: str | None = None
    summary: str = ""


class LiveKitVoiceTimingCaptureWorkflow:
    """Capture durable LiveKit voice timing events without relying on the browser."""

    def __init__(
        self,
        store,
        *,
        settings: Settings | None = None,
        client_factory: Callable[[], Any] | None = None,
    ):
        self._store = store
        self._settings = settings or get_settings()
        self._client_factory = client_factory or LiveKitHeadlessVoiceTimingClient

    async def capture(
        self,
        run_id: UUID,
        request: LiveKitVoiceTimingCaptureRequest,
    ) -> LiveKitVoiceTimingCaptureResult:
        run = await self._store.get_run(run_id)
        if run is None:
            return _blocked_result(run_id, "run_not_found", "Run not found.")

        sessions = await self._store.list_realtime_sessions(run_id)
        session = _select_session(sessions, request.realtime_session_id)
        if session is None:
            return _blocked_result(
                run_id,
                "livekit_session_not_found",
                "No matching provider-backed LiveKit realtime session was found.",
            )

        grant = _build_capture_input(
            settings=self._settings,
            run_id=run_id,
            session=session,
            request=request,
        )
        if isinstance(grant, str):
            return _blocked_result(run_id, grant, grant, session=session)

        captured_event_ids: list[int] = []
        captured_event_types: list[str] = []
        skipped_duplicate_event_count = 0

        async def on_agent_event(agent_event: HeadlessLiveKitAgentEvent) -> None:
            nonlocal skipped_duplicate_event_count
            event_id = await self._persist_agent_event(
                session=session,
                agent_event=agent_event,
            )
            if event_id is None:
                skipped_duplicate_event_count += 1
                return
            captured_event_ids.append(event_id)
            captured_event_types.append(agent_event.event_type)

        client = self._client_factory()
        capture_result = await client.capture(grant, on_agent_event)
        status = "captured" if captured_event_ids else "needs_more_evidence"
        return LiveKitVoiceTimingCaptureResult(
            run_id=run_id,
            realtime_session_id=session.realtime_session_id,
            status=status,
            captured_event_count=len(captured_event_ids),
            skipped_duplicate_event_count=skipped_duplicate_event_count,
            captured_event_ids=captured_event_ids,
            captured_event_types=captured_event_types,
            observed_agent_event_types=capture_result.observed_agent_event_types,
            audio_probe_published=capture_result.audio_probe_published,
            transcript_turn_sent=capture_result.transcript_turn_sent,
            interrupt_sent=capture_result.interrupt_sent,
            summary=(
                "Captured LiveKit voice timing events from the agent data channel."
                if captured_event_ids
                else "No new LiveKit voice timing events were captured."
            ),
        )

    async def _persist_agent_event(
        self,
        *,
        session: RealtimeSessionRecord,
        agent_event: HeadlessLiveKitAgentEvent,
    ) -> int | None:
        safe_payload = safe_realtime_metadata(agent_event.payload)
        voice_agent_event_uid = _optional_str(
            safe_payload.get("voice_agent_event_uid")
        )
        if voice_agent_event_uid:
            safe_payload["voice_agent_event_uid"] = voice_agent_event_uid
            finder = getattr(self._store, "find_event_by_voice_agent_event_uid", None)
            if callable(finder):
                duplicate = await finder(
                    session.run_id,
                    agent_event.event_type,
                    voice_agent_event_uid,
                )
                if duplicate is not None:
                    return None
        if agent_event.created_at is not None:
            safe_payload["agent_created_at"] = agent_event.created_at.isoformat()
        safe_payload.update(
            {
                "realtime_session_id": str(session.realtime_session_id),
                "provider": session.provider,
                "provider_session_id": session.provider_session_id,
                "transport_framework": session.transport_framework,
                "room_name": session.room_name,
                "voice_agent_event_source": "livekit_headless_capture",
                "livekit_sender_identity": agent_event.sender_identity,
                "livekit_topic": agent_event.topic,
                "latency_class": "realtime_interrupt",
                "smoke_proof_status": (
                    "rehearsal_only"
                    if session.metadata.get("not_provider_backed")
                    else "provider_backed"
                ),
            }
        )
        event = await self._store.append_event(
            RunEvent(
                run_id=session.run_id,
                event_type=agent_event.event_type,
                actor="gemma-kokoro-livekit-agent",
                payload=safe_payload,
            )
        )
        return event.event_id or 0


class LiveKitHeadlessVoiceTimingClient:
    async def capture(
        self,
        capture_input: HeadlessLiveKitCaptureInput,
        on_agent_event: Callable[[HeadlessLiveKitAgentEvent], Awaitable[None]],
    ) -> HeadlessLiveKitCaptureResult:
        from livekit import rtc

        room = rtc.Room()
        queue: asyncio.Queue[HeadlessLiveKitAgentEvent] = asyncio.Queue()
        observed_event_types: list[str] = []
        observed_response_id: str | None = None
        interrupt_sent = False
        audio_probe_published = False
        transcript_turn_sent = False

        @room.on("data_received")
        def on_data_received(data: bytes, participant, *_args):
            event = _parse_agent_data_event(
                data,
                participant_identity=_participant_identity(participant),
                topic=_livekit_data_topic(_args),
            )
            if event is not None:
                queue.put_nowait(event)

        await room.connect(capture_input.livekit_url, capture_input.livekit_token)
        try:
            await _publish_control_payload(
                room,
                _presence_probe_payload(capture_input),
            )
            if capture_input.transcript:
                transcript_turn_sent = True
                await _publish_control_payload(
                    room,
                    _transcript_turn_payload(capture_input),
                )
            if capture_input.audio_probe_duration_ms:
                audio_probe_published = True
                await _publish_audio_probe(room, capture_input)

            deadline = time.monotonic() + capture_input.timeout_seconds
            while time.monotonic() < deadline:
                timeout = max(0.05, min(0.5, deadline - time.monotonic()))
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=timeout)
                except asyncio.TimeoutError:
                    continue
                observed_event_types.append(event.event_type)
                response_id = _optional_str(event.payload.get("response_id"))
                if response_id:
                    observed_response_id = response_id
                await on_agent_event(event)
                if (
                    capture_input.interrupt_on_first_output
                    and not interrupt_sent
                    and event.event_type
                    in {"assistant_audio_chunk_published", "assistant_text_delta"}
                ):
                    interrupt_sent = True
                    await _publish_control_payload(
                        room,
                        _interrupt_payload(
                            capture_input,
                            response_id=observed_response_id,
                        ),
                    )
                if event.event_type == "gemma_kokoro_voice_turn_cancelled":
                    break
        finally:
            await room.disconnect()

        return HeadlessLiveKitCaptureResult(
            connected=True,
            audio_probe_published=audio_probe_published,
            transcript_turn_sent=transcript_turn_sent,
            interrupt_sent=interrupt_sent,
            observed_agent_event_types=observed_event_types,
            observed_response_id=observed_response_id,
            summary=(
                "Observed "
                f"{len(observed_event_types)} agent voice event(s) over LiveKit."
            ),
        )


def _build_capture_input(
    *,
    settings: Settings,
    run_id: UUID,
    session: RealtimeSessionRecord,
    request: LiveKitVoiceTimingCaptureRequest,
) -> HeadlessLiveKitCaptureInput | str:
    livekit_url = settings.realtime_livekit_url()
    if not livekit_url:
        return "livekit_url_not_configured"
    if not settings.livekit_api_key:
        return "livekit_api_key_not_configured"
    if not settings.livekit_api_secret:
        return "livekit_api_secret_not_configured"
    if session.transport_framework != "livekit":
        return "session_is_not_livekit"
    if not session.room_name or not session.participant_identity:
        return "session_missing_room_or_participant_identity"
    if not session.agent_participant_identity:
        return "session_missing_agent_identity"

    livekit_token, _expires_at = _mint_livekit_join_token(
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
        room_name=session.room_name,
        participant_identity=session.participant_identity,
        agent_identity=session.agent_participant_identity,
        ttl_seconds=settings.gemma4_realtime_livekit_token_ttl_seconds,
        metadata={
            "provider": session.provider,
            "run_id": str(run_id),
            "voice": request.voice or session.voice or "",
            "proof_capture": "headless_livekit_voice_timing",
        },
    )
    control_binding_token = build_livekit_control_binding_token(
        settings.livekit_api_secret,
        run_id=str(run_id),
        realtime_session_id=str(session.realtime_session_id),
        room_name=session.room_name,
        participant_identity=session.participant_identity,
        agent_identity=session.agent_participant_identity,
    )
    return HeadlessLiveKitCaptureInput(
        run_id=run_id,
        realtime_session_id=session.realtime_session_id,
        livekit_url=livekit_url,
        livekit_token=livekit_token,
        control_binding_token=control_binding_token,
        room_name=session.room_name,
        participant_identity=session.participant_identity,
        agent_identity=session.agent_participant_identity,
        voice=request.voice or session.voice,
        transcript=request.transcript,
        timeout_seconds=request.timeout_seconds,
        audio_probe_duration_ms=request.audio_probe_duration_ms,
        post_speech_silence_ms=request.post_speech_silence_ms,
        interrupt_on_first_output=request.interrupt_on_first_output,
        sample_rate=settings.gemma4_realtime_sample_rate,
        frame_ms=settings.rust_voice_edge_frame_ms,
    )


def _select_session(
    sessions: list[RealtimeSessionRecord],
    realtime_session_id: UUID | None,
) -> RealtimeSessionRecord | None:
    if realtime_session_id is not None:
        return next(
            (
                session
                for session in sessions
                if session.realtime_session_id == realtime_session_id
            ),
            None,
        )
    candidates = [
        session
        for session in sessions
        if session.transport_framework == "livekit"
        and not session.metadata.get("not_provider_backed")
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda session: session.created_at)[-1]


def _blocked_result(
    run_id: UUID,
    blocked_reason: str,
    summary: str,
    *,
    session: RealtimeSessionRecord | None = None,
) -> LiveKitVoiceTimingCaptureResult:
    return LiveKitVoiceTimingCaptureResult(
        run_id=run_id,
        realtime_session_id=session.realtime_session_id if session else None,
        status="blocked",
        blocked_reason=blocked_reason,
        summary=summary,
    )


def _parse_agent_data_event(
    data: bytes,
    *,
    participant_identity: str | None,
    topic: str | None,
) -> HeadlessLiveKitAgentEvent | None:
    if topic and topic != AGENT_EVENT_TOPIC:
        return None
    try:
        raw = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    event_type = _optional_str(raw.get("event_type"))
    if not event_type:
        return None
    raw_payload = raw.get("payload")
    payload = dict(raw_payload) if isinstance(raw_payload, dict) else {}
    uid = _optional_str(raw.get("voice_agent_event_uid")) or _optional_str(
        payload.get("voice_agent_event_uid")
    )
    if uid:
        payload["voice_agent_event_uid"] = uid
    created_at = _parse_datetime(raw.get("created_at"))
    return HeadlessLiveKitAgentEvent(
        event_type=event_type,
        payload=payload,
        created_at=created_at,
        sender_identity=participant_identity,
        topic=topic or AGENT_EVENT_TOPIC,
    )


async def _publish_control_payload(room: object, payload: dict[str, object]) -> None:
    data = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
    await room.local_participant.publish_data(
        data,
        reliable=True,
        topic=AGENT_CONTROL_TOPIC,
    )


def _presence_probe_payload(capture_input: HeadlessLiveKitCaptureInput) -> dict[str, object]:
    return {
        "type": "voice_agent_presence_probe",
        "probe_id": f"headless-presence-{uuid4()}",
        "run_id": str(capture_input.run_id),
        "realtime_session_id": str(capture_input.realtime_session_id),
        "room_name": capture_input.room_name,
        "expected_agent_identity": capture_input.agent_identity,
        "control_binding_token": capture_input.control_binding_token,
        "voice": capture_input.voice,
    }


def _transcript_turn_payload(capture_input: HeadlessLiveKitCaptureInput) -> dict[str, object]:
    return {
        "type": "transcript_turn",
        "turn_id": f"headless-text-turn-{uuid4()}",
        "run_id": str(capture_input.run_id),
        "realtime_session_id": str(capture_input.realtime_session_id),
        "room_name": capture_input.room_name,
        "expected_agent_identity": capture_input.agent_identity,
        "control_binding_token": capture_input.control_binding_token,
        "transcript": capture_input.transcript,
        "voice": capture_input.voice,
    }


def _interrupt_payload(
    capture_input: HeadlessLiveKitCaptureInput,
    *,
    response_id: str | None,
) -> dict[str, object]:
    return {
        "type": "voice_interrupt",
        "interrupt_id": f"headless-interrupt-{uuid4()}",
        "run_id": str(capture_input.run_id),
        "realtime_session_id": str(capture_input.realtime_session_id),
        "room_name": capture_input.room_name,
        "expected_agent_identity": capture_input.agent_identity,
        "control_binding_token": capture_input.control_binding_token,
        "reason": "Headless proof capture requested barge-in cancellation.",
        "response_id": response_id,
        "interrupted_response_id": response_id,
        "drop_outbound_audio_packets": True,
        "cancel_gemma": True,
        "clear_kokoro_buffers": True,
        "stop_livekit_audio": True,
        "required_runtime_actions": [
            "drop_outbound_audio_packets",
            "cancel_gemma_inference",
            "clear_kokoro_tts_buffer",
            "stop_livekit_audio",
        ],
    }


async def _publish_audio_probe(
    room: object,
    capture_input: HeadlessLiveKitCaptureInput,
) -> None:
    from livekit import rtc

    source = rtc.AudioSource(capture_input.sample_rate, 1)
    track = rtc.LocalAudioTrack.create_audio_track(
        "headless-proof-microphone",
        source,
    )
    options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
    await room.local_participant.publish_track(track, options)

    frame_ms = max(10, capture_input.frame_ms)
    speech_frames = max(1, capture_input.audio_probe_duration_ms // frame_ms)
    silence_frames = max(1, capture_input.post_speech_silence_ms // frame_ms)
    for index in range(speech_frames):
        await _capture_pcm_frame(
            source,
            _sine_pcm16_frame(
                sample_rate=capture_input.sample_rate,
                frame_ms=frame_ms,
                frame_index=index,
            ),
            sample_rate=capture_input.sample_rate,
            frame_ms=frame_ms,
        )
    silence = _silence_pcm16_frame(
        sample_rate=capture_input.sample_rate,
        frame_ms=frame_ms,
    )
    for _ in range(silence_frames):
        await _capture_pcm_frame(
            source,
            silence,
            sample_rate=capture_input.sample_rate,
            frame_ms=frame_ms,
        )


async def _capture_pcm_frame(
    source: object,
    payload: bytes,
    *,
    sample_rate: int,
    frame_ms: int,
) -> None:
    from livekit import rtc

    samples_per_channel = max(1, int(sample_rate * frame_ms / 1000))
    frame = rtc.AudioFrame.create(sample_rate, 1, samples_per_channel)
    frame.data[: len(payload)] = payload
    await source.capture_frame(frame)


def _sine_pcm16_frame(*, sample_rate: int, frame_ms: int, frame_index: int) -> bytes:
    samples = max(1, int(sample_rate * frame_ms / 1000))
    start = frame_index * samples
    return b"".join(
        struct.pack(
            "<h",
            int(9000 * math.sin(2 * math.pi * 440 * ((start + offset) / sample_rate))),
        )
        for offset in range(samples)
    )


def _silence_pcm16_frame(*, sample_rate: int, frame_ms: int) -> bytes:
    samples = max(1, int(sample_rate * frame_ms / 1000))
    return b"\x00\x00" * samples


def _participant_identity(participant: object) -> str | None:
    identity = getattr(participant, "identity", None)
    return str(identity) if identity else None


def _livekit_data_topic(args: tuple[object, ...]) -> str | None:
    for item in reversed(args):
        if isinstance(item, str):
            return item
        topic = getattr(item, "topic", None)
        if isinstance(topic, str):
            return topic
    return None


def _optional_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
