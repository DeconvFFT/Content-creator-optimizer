from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(slots=True)
class RealtimeVoiceAgentConfig:
    """Runtime policy for the OpenRouter/Kokoro voice agent participant."""

    audio_input_model: str = "deepseek/deepseek-v4-flash"
    reasoning_model: str = "deepseek/deepseek-v4-flash"
    audio_output_model: str = "hexgrad/Kokoro-82M"
    sample_rate: int = 16000
    audio_format: str = "pcm_s16le"
    context_window_turns: int = 4
    prune_after_turns: int = 3
    max_raw_audio_seconds_per_turn: int = 30
    tts_flush_chars: int = 180
    gemma_streaming_enabled: bool = True
    gemma_stream_timeout_seconds: float = 120.0


@dataclass(slots=True)
class VoiceConversationTurn:
    turn_id: str
    role: str
    text: str | None = None
    audio_ref: str | None = None
    audio_duration_ms: int = 0
    summary: str | None = None
    interrupted: bool = False
    heard_by_user: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, object] = field(default_factory=dict)

    def compact_text(self) -> str:
        if self.text:
            return self.text
        if self.summary:
            return self.summary
        if self.audio_ref:
            return f"[audio turn {self.turn_id}]"
        return "[empty voice turn]"


@dataclass(slots=True)
class RealtimeVoiceTurnInput:
    run_id: UUID
    realtime_session_id: UUID
    room_name: str
    participant_identity: str
    turn_id: str = field(default_factory=lambda: str(uuid4()))
    audio_ref: str | None = None
    audio_pcm: bytes | None = None
    transcript: str | None = None
    audio_duration_ms: int = 0
    interrupted: bool = False
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class AssistantAudioChunk:
    response_id: str
    sequence: int
    pcm: bytes
    sample_rate: int
    audio_format: str
    text_fragment: str


@dataclass(slots=True)
class RealtimeVoiceAgentEvent:
    event_type: str
    run_id: UUID
    realtime_session_id: UUID
    payload: dict[str, object]
    voice_agent_event_uid: str = field(
        default_factory=lambda: f"voice-event-{uuid4()}"
    )
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class RealtimeVoiceAgentResult:
    run_id: UUID
    realtime_session_id: UUID
    turn_id: str
    response_id: str
    transcript: str
    assistant_text: str
    audio_chunk_count: int
    context_pruned: bool
    raw_audio_turns_before: int
    raw_audio_turns_after: int
    canceled: bool = False
    cancellation_reason: str | None = None
    failed: bool = False
    failure_reason: str | None = None
    failure_stage: str | None = None
    events: list[RealtimeVoiceAgentEvent] = field(default_factory=list)
