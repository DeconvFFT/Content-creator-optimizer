import asyncio
import re
from collections.abc import AsyncIterator
from typing import Protocol
from uuid import uuid4

from all_about_llms.providers.interfaces import ProviderConfigurationError
from all_about_llms.voice_agent.context import RealtimeContextPruner
from all_about_llms.voice_agent.models import (
    AssistantAudioChunk,
    RealtimeVoiceAgentConfig,
    RealtimeVoiceAgentEvent,
    RealtimeVoiceAgentResult,
    RealtimeVoiceTurnInput,
    VoiceConversationTurn,
)


class VoiceAgentCancelledError(asyncio.CancelledError):
    pass


class VoiceAgentCancellationToken:
    def __init__(self, response_id: str):
        self.response_id = response_id
        self._event = asyncio.Event()
        self.reason: str | None = None

    @property
    def canceled(self) -> bool:
        return self._event.is_set()

    def cancel(self, reason: str) -> None:
        self.reason = reason
        self._event.set()

    def throw_if_cancelled(self) -> None:
        if self.canceled:
            raise VoiceAgentCancelledError(self.reason or "voice turn canceled")


class GemmaAudioReasoner(Protocol):
    async def stream_text(
        self,
        turn: RealtimeVoiceTurnInput,
        context_turns: list[VoiceConversationTurn],
        cancellation: VoiceAgentCancellationToken,
    ) -> AsyncIterator[str]:
        """Stream Gemma 4 E4B text deltas from native audio/text input."""


class KokoroTTSStreamer(Protocol):
    async def stream_audio(
        self,
        *,
        response_id: str,
        text: str,
        voice: str | None,
        cancellation: VoiceAgentCancellationToken,
    ) -> AsyncIterator[bytes]:
        """Stream Kokoro PCM chunks for a text fragment."""


class LiveKitAudioPublisher(Protocol):
    async def publish_audio_chunk(self, chunk: AssistantAudioChunk) -> None:
        """Publish one PCM chunk to the active LiveKit output track."""

    async def clear_output_buffer(self, response_id: str) -> None:
        """Drop queued output audio for a response."""

    async def stop_response_audio(self, response_id: str) -> None:
        """Stop active LiveKit playback for a response."""


class VoiceAgentEventSink(Protocol):
    async def emit(self, event: RealtimeVoiceAgentEvent) -> None:
        """Persist or forward a durable-safe voice-agent event."""


class InMemoryVoiceAgentEventSink:
    def __init__(self):
        self.events: list[RealtimeVoiceAgentEvent] = []

    async def emit(self, event: RealtimeVoiceAgentEvent) -> None:
        self.events.append(event)


class GemmaKokoroLiveKitAgentEngine:
    def __init__(
        self,
        *,
        config: RealtimeVoiceAgentConfig,
        gemma: GemmaAudioReasoner,
        kokoro: KokoroTTSStreamer,
        publisher: LiveKitAudioPublisher,
        event_sink: VoiceAgentEventSink | None = None,
    ):
        self._config = config
        self._gemma = gemma
        self._kokoro = kokoro
        self._publisher = publisher
        self._event_sink = event_sink or InMemoryVoiceAgentEventSink()
        self._pruner = RealtimeContextPruner(config)
        self._active: dict[str, VoiceAgentCancellationToken] = {}

    @property
    def active_response_id(self) -> str | None:
        return next(reversed(self._active), None)

    async def handle_turn(
        self,
        turn: RealtimeVoiceTurnInput,
        history: list[VoiceConversationTurn],
        *,
        voice: str | None = None,
    ) -> RealtimeVoiceAgentResult:
        response_id = f"voice-response-{uuid4()}"
        cancellation = VoiceAgentCancellationToken(response_id)
        self._active[response_id] = cancellation
        events: list[RealtimeVoiceAgentEvent] = []
        transcript = turn.transcript or ""

        def make_event(event_type: str, payload: dict[str, object]):
            event = RealtimeVoiceAgentEvent(
                event_type=event_type,
                run_id=turn.run_id,
                realtime_session_id=turn.realtime_session_id,
                payload={
                    "turn_id": turn.turn_id,
                    "response_id": response_id,
                    "room_name": turn.room_name,
                    **payload,
                },
            )
            events.append(event)
            return event

        async def emit(event_type: str, payload: dict[str, object]) -> None:
            await self._event_sink.emit(make_event(event_type, payload))

        try:
            await emit(
                "gemma_kokoro_voice_turn_started",
                {
                    "audio_input_model": self._config.audio_input_model,
                    "reasoning_model": self._config.reasoning_model,
                    "audio_output_model": self._config.audio_output_model,
                    "audio_format": self._config.audio_format,
                    "sample_rate": self._config.sample_rate,
                    "has_audio_ref": turn.audio_ref is not None,
                    "has_audio_pcm": turn.audio_pcm is not None,
                    "audio_duration_ms": turn.audio_duration_ms,
                },
            )
            pruned = self._pruner.prune(
                [
                    *history,
                    VoiceConversationTurn(
                        turn_id=turn.turn_id,
                        role="user",
                        text=transcript or None,
                        audio_ref=turn.audio_ref,
                        audio_duration_ms=turn.audio_duration_ms,
                        interrupted=turn.interrupted,
                        metadata={"livekit_participant": turn.participant_identity},
                    ),
                ]
            )
            if pruned.pruned:
                await emit(
                    "voice_context_pruned",
                    {
                        "raw_audio_turns_before": pruned.raw_audio_turns_before,
                        "raw_audio_turns_after": pruned.raw_audio_turns_after,
                        "pruned_turn_ids": pruned.pruned_turn_ids,
                        "replacement_strategy": "transcript_plus_summary",
                        "max_raw_audio_seconds_per_turn": (
                            self._config.max_raw_audio_seconds_per_turn
                        ),
                    },
                )

            text_buffer = ""
            pending_tts = ""
            audio_chunk_count = 0
            sequence = 0
            provider_stage = "gemma_generation"

            async def flush_tts(fragment: str) -> None:
                nonlocal audio_chunk_count, provider_stage, sequence
                if not fragment.strip():
                    return
                await emit(
                    "kokoro_tts_fragment_started",
                    {
                        "kokoro_buffer_id": f"kokoro-{response_id}",
                        "fragment_chars": len(fragment),
                    },
                )
                provider_stage = "kokoro_tts"
                async for pcm in self._kokoro.stream_audio(
                    response_id=response_id,
                    text=fragment,
                    voice=voice,
                    cancellation=cancellation,
                ):
                    cancellation.throw_if_cancelled()
                    sequence += 1
                    chunk = AssistantAudioChunk(
                        response_id=response_id,
                        sequence=sequence,
                        pcm=pcm,
                        sample_rate=self._config.sample_rate,
                        audio_format=self._config.audio_format,
                        text_fragment=fragment,
                    )
                    await self._publisher.publish_audio_chunk(chunk)
                    audio_chunk_count += 1
                    await emit(
                        "assistant_audio_chunk_published",
                        {
                            "sequence": sequence,
                            "bytes": len(pcm),
                            "kokoro_buffer_id": f"kokoro-{response_id}",
                        },
                    )
                provider_stage = "gemma_generation"

            await emit(
                "gemma_generation_started",
                {"gemma_generation_id": f"gemma-{response_id}"},
            )
            async for delta in self._gemma.stream_text(
                turn,
                pruned.turns,
                cancellation,
            ):
                cancellation.throw_if_cancelled()
                text_buffer += delta
                pending_tts += delta
                await emit(
                    "assistant_text_delta",
                    {
                        "gemma_generation_id": f"gemma-{response_id}",
                        "delta_chars": len(delta),
                        "text_delta": delta,
                    },
                )
                if _should_flush_tts(pending_tts, self._config.tts_flush_chars):
                    fragment = pending_tts
                    pending_tts = ""
                    await flush_tts(fragment)

            if pending_tts:
                await flush_tts(pending_tts)

            await emit(
                "assistant_response_completed",
                {
                    "audio_chunk_count": audio_chunk_count,
                    "assistant_text_chars": len(text_buffer),
                    "assistant_text": text_buffer,
                    "livekit_audio_track_id": f"livekit-audio-{turn.realtime_session_id}",
                },
            )
            return RealtimeVoiceAgentResult(
                run_id=turn.run_id,
                realtime_session_id=turn.realtime_session_id,
                turn_id=turn.turn_id,
                response_id=response_id,
                transcript=transcript,
                assistant_text=text_buffer,
                audio_chunk_count=audio_chunk_count,
                context_pruned=pruned.pruned,
                raw_audio_turns_before=pruned.raw_audio_turns_before,
                raw_audio_turns_after=pruned.raw_audio_turns_after,
                events=events,
            )
        except ProviderConfigurationError as exc:
            await self._publisher.clear_output_buffer(response_id)
            await self._publisher.stop_response_audio(response_id)
            safe_reason = _safe_provider_failure_reason(exc)
            await emit(
                "gemma_kokoro_voice_turn_failed",
                {
                    "reason": safe_reason,
                    "failure_reason": safe_reason,
                    "failure_stage": provider_stage,
                    "provider_boundary": "gemma_kokoro_voice_agent",
                    "cancel_gemma": provider_stage == "gemma_generation",
                    "clear_kokoro_buffers": True,
                    "stop_livekit_audio": True,
                    "assistant_text_chars": len(text_buffer),
                    "audio_chunk_count": audio_chunk_count,
                },
            )
            return RealtimeVoiceAgentResult(
                run_id=turn.run_id,
                realtime_session_id=turn.realtime_session_id,
                turn_id=turn.turn_id,
                response_id=response_id,
                transcript=transcript,
                assistant_text=text_buffer,
                audio_chunk_count=audio_chunk_count,
                context_pruned=pruned.pruned,
                raw_audio_turns_before=pruned.raw_audio_turns_before,
                raw_audio_turns_after=pruned.raw_audio_turns_after,
                failed=True,
                failure_reason=safe_reason,
                failure_stage=provider_stage,
                events=events,
            )
        except VoiceAgentCancelledError as exc:
            await self._publisher.clear_output_buffer(response_id)
            await self._publisher.stop_response_audio(response_id)
            await emit(
                "gemma_kokoro_voice_turn_cancelled",
                {
                    "reason": str(exc),
                    "cancel_gemma": True,
                    "clear_kokoro_buffers": True,
                    "stop_livekit_audio": True,
                },
            )
            return RealtimeVoiceAgentResult(
                run_id=turn.run_id,
                realtime_session_id=turn.realtime_session_id,
                turn_id=turn.turn_id,
                response_id=response_id,
                transcript=transcript,
                assistant_text="",
                audio_chunk_count=0,
                context_pruned=False,
                raw_audio_turns_before=0,
                raw_audio_turns_after=0,
                canceled=True,
                cancellation_reason=str(exc),
                events=events,
            )
        finally:
            self._active.pop(response_id, None)

    async def cancel_response(self, response_id: str, reason: str) -> bool:
        token = self._active.get(response_id)
        if token is None:
            return False
        token.cancel(reason)
        await self._publisher.clear_output_buffer(response_id)
        await self._publisher.stop_response_audio(response_id)
        return True


def _should_flush_tts(buffer: str, flush_chars: int) -> bool:
    if len(buffer) >= flush_chars:
        return True
    stripped = buffer.rstrip()
    return bool(stripped) and stripped[-1:] in {".", "?", "!", "\n"}


def _safe_provider_failure_reason(exc: ProviderConfigurationError) -> str:
    reason = str(exc) or exc.__class__.__name__
    reason = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [redacted]", reason)
    reason = re.sub(r"hf_[A-Za-z0-9]{20,}", "hf_[redacted]", reason)
    reason = re.sub(r"tvly-[A-Za-z0-9-]{20,}", "tvly-[redacted]", reason)
    return reason[:500]
