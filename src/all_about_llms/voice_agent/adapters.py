import base64
import binascii
import json
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx
import numpy as np

from all_about_llms.providers.interfaces import (
    GemmaExpertProvider,
    GemmaRequest,
    ProviderConfigurationError,
)
from all_about_llms.realtime_safety import safe_realtime_metadata
from all_about_llms.voice_agent.models import (
    AssistantAudioChunk,
    RealtimeVoiceAgentConfig,
    RealtimeVoiceAgentEvent,
    RealtimeVoiceTurnInput,
    VoiceConversationTurn,
)


class HuggingFaceGemmaAudioReasoner:
    def __init__(
        self,
        *,
        provider: GemmaExpertProvider,
        config: RealtimeVoiceAgentConfig,
        endpoint_url: str | None = None,
        token: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        include_audio_attachments: bool = True,
        provider_label: str = "gemma",
    ):
        self._provider = provider
        self._config = config
        self._endpoint_url = endpoint_url
        self._token = token
        self._transport = transport
        self._include_audio_attachments = include_audio_attachments
        self._provider_label = provider_label

    async def stream_text(
        self,
        turn: RealtimeVoiceTurnInput,
        context_turns: list[VoiceConversationTurn],
        cancellation,
    ) -> AsyncIterator[str]:
        if (
            self._config.gemma_streaming_enabled
            and self._endpoint_url
            and self._token
        ):
            usable_text_seen = False
            user_input = _turn_user_input(turn)
            if (
                not self._include_audio_attachments
                and turn.audio_pcm
                and not (turn.transcript or "").strip()
            ):
                user_input = (
                    "The user spoke through the LiveKit microphone, but this runtime "
                    "routes dialogue reasoning through OpenRouter text chat. Ask them "
                    "to repeat the request with the Live text turn composer."
                )
            async for delta in _stream_gemma_chat_deltas(
                endpoint_url=self._endpoint_url,
                token=self._token,
                model_id=self._config.reasoning_model,
                system_context=_voice_system_context(context_turns, self._config),
                user_input=user_input,
                attachments=(
                    _audio_attachments(turn, self._config)
                    if self._include_audio_attachments
                    else []
                ),
                timeout_seconds=self._config.gemma_stream_timeout_seconds,
                transport=self._transport,
                cancellation=cancellation,
                provider_label=self._provider_label,
            ):
                if delta.strip():
                    usable_text_seen = True
                yield delta
            if not usable_text_seen:
                raise ProviderConfigurationError(
                    "Gemma 4 streaming provider returned no usable text."
                )
            return

        cancellation.throw_if_cancelled()
        response = await self._provider.complete(
            GemmaRequest(
                model_id=self._config.reasoning_model,
                agent_id="realtime-conversation-host",
                system_context=_voice_system_context(context_turns, self._config),
                user_input=_turn_user_input(turn),
                attachments=(
                    _audio_attachments(turn, self._config)
                    if self._include_audio_attachments
                    else []
                ),
                metadata={
                    "endpoint_url": self._endpoint_url,
                    "disable_default_endpoint": self._endpoint_url is None,
                    "audio_input_model": self._config.audio_input_model,
                    "reasoning_model": self._config.reasoning_model,
                    "source": "gemma_kokoro_livekit_voice_agent",
                },
            )
        )
        cancellation.throw_if_cancelled()
        yield response.content


class HuggingFaceKokoroTTSStreamer:
    def __init__(
        self,
        *,
        token: str | None,
        endpoint_url: str | None,
        model_id: str = "hexgrad/Kokoro-82M",
        chunk_bytes: int = 6400,
        timeout_seconds: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._token = token
        self._endpoint_url = endpoint_url
        self._model_id = model_id
        self._chunk_bytes = chunk_bytes
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def stream_audio(
        self,
        *,
        response_id: str,
        text: str,
        voice: str | None,
        cancellation,
    ) -> AsyncIterator[bytes]:
        if not self._endpoint_url:
            raise ProviderConfigurationError("Kokoro TTS endpoint URL is not configured.")
        if not self._token:
            raise ProviderConfigurationError("HF_TOKEN is not configured.")
        cancellation.throw_if_cancelled()
        client_kwargs: dict[str, Any] = {"timeout": self._timeout_seconds}
        if self._transport is not None:
            client_kwargs["transport"] = self._transport
        try:
            async with httpx.AsyncClient(**client_kwargs) as client:
                response = await client.post(
                    self._endpoint_url,
                    headers={"Authorization": f"Bearer {self._token}"},
                    json={
                        "model": self._model_id,
                        "inputs": text,
                        "parameters": {
                            "voice": voice or "af_heart",
                            "response_id": response_id,
                        },
                    },
                )
                response.raise_for_status()
                audio = _extract_audio_bytes(response)
        except httpx.HTTPStatusError as exc:
            raise ProviderConfigurationError(
                "Kokoro TTS request failed with provider HTTP status "
                f"{exc.response.status_code}."
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderConfigurationError("Kokoro TTS request failed.") from exc

        for offset in range(0, len(audio), self._chunk_bytes):
            cancellation.throw_if_cancelled()
            yield audio[offset : offset + self._chunk_bytes]


class LocalKokoroTTSStreamer:
    def __init__(
        self,
        *,
        lang_code: str = "a",
        voice: str = "af_heart",
        chunk_bytes: int = 6400,
    ):
        self._lang_code = lang_code
        self._voice = voice
        self._chunk_bytes = chunk_bytes
        self._pipeline = None

    async def stream_audio(
        self,
        *,
        response_id: str,
        text: str,
        voice: str | None,
        cancellation,
    ) -> AsyncIterator[bytes]:
        del response_id
        cancellation.throw_if_cancelled()
        if self._pipeline is None:
            try:
                from kokoro import KPipeline
            except ImportError as exc:
                raise ProviderConfigurationError(
                    "Install the voice extra and espeak-ng to use local Kokoro TTS."
                ) from exc
            self._pipeline = KPipeline(
                lang_code=self._lang_code,
                repo_id="hexgrad/Kokoro-82M",
            )

        for _, _, audio in self._pipeline(text, voice=voice or self._voice):
            cancellation.throw_if_cancelled()
            pcm = _float_audio_to_pcm16(audio)
            for offset in range(0, len(pcm), self._chunk_bytes):
                yield pcm[offset : offset + self._chunk_bytes]


class LiveKitAudioTrackPublisher:
    def __init__(
        self,
        *,
        room: Any,
        participant: Any,
        sample_rate: int,
        audio_format: str,
        track_name: str = "gemma-kokoro-output",
        num_channels: int = 1,
        frame_ms: int = 20,
    ):
        self._room = room
        self._participant = participant
        self._sample_rate = sample_rate
        self._audio_format = audio_format
        self._track_name = track_name
        self._num_channels = num_channels
        self._frame_ms = frame_ms
        self._source = None
        self._publication = None
        self._buffer = bytearray()
        self._stopped_response_ids: set[str] = set()

    async def publish_audio_chunk(self, chunk: AssistantAudioChunk) -> None:
        if chunk.response_id in self._stopped_response_ids:
            return
        if self._audio_format != "pcm_s16le":
            raise ProviderConfigurationError(
                f"Unsupported LiveKit publisher format: {self._audio_format}"
            )
        await self._ensure_track()
        self._buffer.extend(chunk.pcm)
        frame_bytes = self._frame_byte_count()
        while len(self._buffer) >= frame_bytes:
            payload = bytes(self._buffer[:frame_bytes])
            del self._buffer[:frame_bytes]
            await self._capture_pcm_frame(payload)

    async def clear_output_buffer(self, response_id: str) -> None:
        self._stopped_response_ids.add(response_id)
        self._buffer.clear()

    async def stop_response_audio(self, response_id: str) -> None:
        self._stopped_response_ids.add(response_id)
        self._buffer.clear()

    async def _ensure_track(self) -> None:
        if self._source is not None:
            return
        try:
            from livekit import rtc
        except ImportError as exc:
            raise ProviderConfigurationError(
                "Install the voice extra to publish LiveKit agent audio."
            ) from exc
        self._source = rtc.AudioSource(self._sample_rate, self._num_channels)
        track = rtc.LocalAudioTrack.create_audio_track(self._track_name, self._source)
        options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
        self._publication = await self._participant.publish_track(track, options)

    async def _capture_pcm_frame(self, payload: bytes) -> None:
        from livekit import rtc

        samples_per_channel = int(self._sample_rate * self._frame_ms / 1000)
        frame = rtc.AudioFrame.create(
            self._sample_rate,
            self._num_channels,
            samples_per_channel,
        )
        frame.data[: len(payload)] = payload
        await self._source.capture_frame(frame)

    def _frame_byte_count(self) -> int:
        samples = int(self._sample_rate * self._frame_ms / 1000)
        bytes_per_sample = 2
        return samples * self._num_channels * bytes_per_sample


class LiveKitDataEventSink:
    def __init__(self, *, room: Any, topic: str = "agent.voice.event"):
        self._room = room
        self._topic = topic

    async def emit(self, event: RealtimeVoiceAgentEvent) -> None:
        payload = {
            **safe_realtime_metadata(event.payload),
            "voice_agent_event_uid": event.voice_agent_event_uid,
        }
        payload = json.dumps(
            {
                "event_type": event.event_type,
                "voice_agent_event_uid": event.voice_agent_event_uid,
                "run_id": str(event.run_id),
                "realtime_session_id": str(event.realtime_session_id),
                "payload": payload,
                "created_at": event.created_at.isoformat(),
            },
            default=str,
            separators=(",", ":"),
        )
        await self._room.local_participant.send_text(payload, topic=self._topic)


class BackendRealtimeVoiceEventSink:
    """Best-effort direct persistence path for always-on voice-agent events."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 2.0,
        source: str = "livekit_agent_http_sink",
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._base_url = normalize_backend_event_sink_base_url(base_url)
        self._timeout_seconds = timeout_seconds
        self._source = source
        self._transport = transport

    async def emit(self, event: RealtimeVoiceAgentEvent) -> None:
        payload = {
            **safe_realtime_metadata(event.payload),
            "voice_agent_event_uid": event.voice_agent_event_uid,
        }
        client_kwargs: dict[str, Any] = {"timeout": self._timeout_seconds}
        if self._transport is not None:
            client_kwargs["transport"] = self._transport
        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.post(
                (
                    f"{self._base_url}/api/realtime-sessions/"
                    f"{event.realtime_session_id}/voice-events"
                ),
                json={
                    "event_type": event.event_type,
                    "voice_agent_event_uid": event.voice_agent_event_uid,
                    "payload": payload,
                    "agent_created_at": event.created_at.isoformat(),
                    "source": self._source,
                },
            )
            response.raise_for_status()


def normalize_backend_event_sink_base_url(value: str | None) -> str:
    if not value or not value.strip():
        raise ValueError("VOICE_AGENT_BACKEND_EVENT_SINK_URL is not configured.")
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL must use http(s) and include a host.")
    if parsed.username or parsed.password:
        raise ValueError("URL must not include credentials.")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("URL port is not valid.") from exc
    if parsed.path not in {"", "/"}:
        raise ValueError("URL must be the FastAPI backend origin without a path.")
    if parsed.query or parsed.fragment:
        raise ValueError("URL must not include query strings or fragments.")
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


class CompositeVoiceAgentEventSink:
    def __init__(
        self,
        *,
        required: list[Any],
        best_effort: list[Any] | None = None,
    ):
        self._required = required
        self._best_effort = best_effort or []

    async def emit(self, event: RealtimeVoiceAgentEvent) -> None:
        for sink in self._required:
            await sink.emit(event)
        for sink in self._best_effort:
            try:
                await sink.emit(event)
            except Exception:
                continue


def _voice_system_context(
    context_turns: list[VoiceConversationTurn],
    config: RealtimeVoiceAgentConfig,
) -> str:
    compact_turns = "\n".join(
        f"{turn.role}: {turn.compact_text()}" for turn in context_turns
    )
    return (
        "You are the realtime conversation host for a source-backed content "
        "studio. Understand the user's current audio/text turn with Gemma 4, "
        "answer naturally and briefly, and stay interruptible. Older raw audio "
        "has already been pruned into transcripts or summaries.\n\n"
        f"Models: audio input={config.audio_input_model}; reasoning={config.reasoning_model}; "
        f"TTS={config.audio_output_model}.\n\n"
        f"Recent context:\n{compact_turns}"
    )


def _turn_user_input(turn: RealtimeVoiceTurnInput) -> str:
    if turn.transcript:
        return turn.transcript
    if turn.audio_ref:
        return f"Analyze the attached audio turn from {turn.audio_ref}."
    if turn.audio_pcm:
        return "Analyze the attached raw PCM audio turn."
    return "The user submitted an empty realtime audio turn."


def _audio_attachments(
    turn: RealtimeVoiceTurnInput,
    config: RealtimeVoiceAgentConfig,
) -> list[dict[str, object]]:
    if turn.audio_pcm:
        return [
            {
                "type": "audio",
                "uri": turn.audio_ref,
                "content_base64": base64.b64encode(turn.audio_pcm).decode("ascii"),
                "audio_format": config.audio_format,
                "sample_rate": config.sample_rate,
                "duration_ms": turn.audio_duration_ms,
                "transient": True,
            }
        ]
    if turn.audio_ref:
        return [
            {
                "type": "audio",
                "uri": turn.audio_ref,
                "audio_format": config.audio_format,
                "sample_rate": config.sample_rate,
                "duration_ms": turn.audio_duration_ms,
            }
        ]
    return []


async def _stream_gemma_chat_deltas(
    *,
    endpoint_url: str,
    token: str,
    model_id: str,
    system_context: str,
    user_input: str,
    attachments: list[dict[str, object]],
    timeout_seconds: float,
    transport: httpx.AsyncBaseTransport | None,
    cancellation,
    provider_label: str = "gemma",
) -> AsyncIterator[str]:
    cancellation.throw_if_cancelled()
    payload = _gemma_chat_payload(
        model_id=model_id,
        system_context=system_context,
        user_input=user_input,
        attachments=attachments,
        stream=True,
    )
    client_kwargs: dict[str, Any] = {"timeout": timeout_seconds}
    if transport is not None:
        client_kwargs["transport"] = transport
    try:
        async with httpx.AsyncClient(**client_kwargs) as client:
            async with client.stream(
                "POST",
                endpoint_url,
                headers=_chat_stream_headers(
                    token=token,
                    provider_label=provider_label,
                ),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    cancellation.throw_if_cancelled()
                    delta = _extract_stream_delta(line)
                    if delta is None:
                        continue
                    if delta == "[DONE]":
                        break
                    if delta:
                        yield delta
                cancellation.throw_if_cancelled()
    except httpx.HTTPStatusError as exc:
        provider_name = "OpenRouter" if provider_label == "openrouter" else "Gemma 4"
        raise ProviderConfigurationError(
            f"{provider_name} streaming request failed with provider HTTP status "
            f"{exc.response.status_code}."
        ) from exc
    except httpx.RequestError as exc:
        provider_name = "OpenRouter" if provider_label == "openrouter" else "Gemma 4"
        raise ProviderConfigurationError(
            f"{provider_name} streaming request failed."
        ) from exc


def _chat_stream_headers(*, token: str, provider_label: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }
    if provider_label == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/all-about-llms"
        headers["X-Title"] = "all-about-llms live voice"
    return headers


def _gemma_chat_payload(
    *,
    model_id: str,
    system_context: str,
    user_input: str,
    attachments: list[dict[str, object]],
    stream: bool,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_context},
            {
                "role": "user",
                "content": _build_user_content(user_input, attachments),
            },
        ],
        "stream": stream,
    }
    if attachments:
        payload["attachments"] = attachments
    return payload


def _build_user_content(
    user_input: str,
    attachments: list[dict[str, object]],
) -> str | list[dict[str, object]]:
    multimodal_parts = [
        part
        for attachment in attachments
        if (part := _attachment_to_message_part(attachment)) is not None
    ]
    if not multimodal_parts:
        return user_input
    return [*multimodal_parts, {"type": "text", "text": user_input}]


def _attachment_to_message_part(
    attachment: dict[str, object],
) -> dict[str, object] | None:
    attachment_type = attachment.get("type") or attachment.get("modality")
    if attachment_type == "audio":
        if attachment.get("content_base64"):
            return {
                "type": "audio",
                "audio_base64": attachment["content_base64"],
                "audio_format": attachment.get("audio_format"),
                "sample_rate": attachment.get("sample_rate"),
            }
        if attachment.get("uri"):
            return {"type": "audio", "audio": attachment["uri"]}
    if attachment_type == "image":
        image_uri = attachment.get("uri") or attachment.get("asset_uri")
        if image_uri:
            return {"type": "image_url", "image_url": {"url": image_uri}}
    return None


def _extract_stream_delta(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith(":"):
        return None
    if stripped.startswith("data:"):
        stripped = stripped.removeprefix("data:").strip()
    if stripped == "[DONE]":
        return "[DONE]"
    try:
        raw = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if isinstance(raw, dict):
        openai_delta = _extract_openai_chat_delta(raw)
        if openai_delta is not None:
            return openai_delta
        token = raw.get("token")
        if isinstance(token, dict) and isinstance(token.get("text"), str):
            return token["text"]
        if isinstance(raw.get("generated_text"), str):
            return raw["generated_text"]
        if isinstance(raw.get("text"), str):
            return raw["text"]
    return None


def _extract_openai_chat_delta(raw: dict[str, Any]) -> str | None:
    choices = raw.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    choice = choices[0]
    if not isinstance(choice, dict):
        return None
    delta = choice.get("delta") or choice.get("message")
    if not isinstance(delta, dict):
        return None
    content = delta.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(part.get("text"))
            for part in content
            if isinstance(part, dict) and part.get("text") is not None
        )
    return None


def _extract_audio_bytes(response: httpx.Response) -> bytes:
    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        if response.content:
            return response.content
        raise ProviderConfigurationError("Kokoro endpoint did not return audio bytes.")
    try:
        raw = response.json()
    except ValueError as exc:
        raise ProviderConfigurationError(
            "Kokoro endpoint returned invalid JSON."
        ) from exc
    if isinstance(raw, dict):
        for key in ("audio", "audio_base64", "generated_audio"):
            if isinstance(raw.get(key), str):
                return _decode_audio_base64(raw[key])
        if isinstance(raw.get("data"), list) and raw["data"]:
            first = raw["data"][0]
            if isinstance(first, dict) and isinstance(first.get("audio"), str):
                return _decode_audio_base64(first["audio"])
    raise ProviderConfigurationError("Kokoro endpoint did not return audio bytes.")


def _decode_audio_base64(value: str) -> bytes:
    try:
        audio = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ProviderConfigurationError(
            "Kokoro endpoint returned invalid base64 audio."
        ) from exc
    if not audio:
        raise ProviderConfigurationError("Kokoro endpoint did not return audio bytes.")
    return audio


def _float_audio_to_pcm16(audio) -> bytes:
    if hasattr(audio, "detach"):
        audio = audio.detach().cpu().numpy()
    array = np.asarray(audio, dtype=np.float32)
    array = np.clip(array, -1.0, 1.0)
    return (array * 32767.0).astype("<i2").tobytes()
