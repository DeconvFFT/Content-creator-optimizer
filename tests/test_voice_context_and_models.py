"""Unit tests for the voice_agent context pruner and models."""

from datetime import timezone


from all_about_llms.voice_agent.context import (
    RealtimeContextPruneResult,
    RealtimeContextPruner,
    _summarize_audio_turn_for_context,
)
from all_about_llms.voice_agent.models import (
    RealtimeVoiceAgentConfig,
    RealtimeVoiceAgentEvent,
    RealtimeVoiceTurnInput,
    VoiceConversationTurn,
)
from uuid import uuid4


# ─── VoiceConversationTurn.compact_text ──────────────────────────────────────


class TestVoiceConversationTurnCompactText:
    def test_returns_text_when_available(self):
        turn = VoiceConversationTurn(turn_id="t1", role="user", text="Hello world")
        assert turn.compact_text() == "Hello world"

    def test_returns_summary_when_no_text(self):
        turn = VoiceConversationTurn(
            turn_id="t1", role="assistant", text=None, summary="A brief summary"
        )
        assert turn.compact_text() == "A brief summary"

    def test_returns_audio_ref_label_when_no_text_or_summary(self):
        turn = VoiceConversationTurn(
            turn_id="t1", role="user", text=None, summary=None, audio_ref="audio://ref1"
        )
        assert turn.compact_text() == "[audio turn t1]"

    def test_returns_empty_voice_turn_when_nothing(self):
        turn = VoiceConversationTurn(turn_id="t1", role="user")
        assert turn.compact_text() == "[empty voice turn]"

    def test_text_takes_precedence_over_summary(self):
        turn = VoiceConversationTurn(
            turn_id="t1", role="user", text="Text", summary="Summary"
        )
        assert turn.compact_text() == "Text"


# ─── _summarize_audio_turn_for_context ───────────────────────────────────────


class TestSummarizeAudioTurnForContext:
    def test_returns_truncated_text_if_available(self):
        turn = VoiceConversationTurn(
            turn_id="t1", role="user", text="X" * 500, audio_ref="audio://ref"
        )
        result = _summarize_audio_turn_for_context(turn)
        assert len(result) == 320
        assert result == "X" * 320

    def test_no_text_generates_description(self):
        turn = VoiceConversationTurn(
            turn_id="t1",
            role="assistant",
            audio_ref="audio://ref",
            audio_duration_ms=5500,
            interrupted=False,
            heard_by_user=True,
        )
        result = _summarize_audio_turn_for_context(turn)
        assert "completed" in result
        assert "5.5s" in result
        assert "heard" in result

    def test_interrupted_turn_description(self):
        turn = VoiceConversationTurn(
            turn_id="t1",
            role="assistant",
            audio_ref="audio://ref",
            audio_duration_ms=3000,
            interrupted=True,
            heard_by_user=False,
        )
        result = _summarize_audio_turn_for_context(turn)
        assert "interrupted" in result
        assert "partially heard" in result

    def test_transcript_unavailable_mentioned(self):
        turn = VoiceConversationTurn(
            turn_id="t1",
            role="user",
            audio_ref="audio://ref",
            audio_duration_ms=2000,
        )
        result = _summarize_audio_turn_for_context(turn)
        assert "transcript unavailable" in result


# ─── RealtimeContextPruner ───────────────────────────────────────────────────


class TestRealtimeContextPruner:
    def _make_turn(self, turn_id, audio_ref=None, text=None, **kwargs):
        return VoiceConversationTurn(
            turn_id=turn_id,
            role="user",
            text=text,
            audio_ref=audio_ref,
            audio_duration_ms=1000 if audio_ref else 0,
            **kwargs,
        )

    def test_no_pruning_when_under_limit(self):
        config = RealtimeVoiceAgentConfig(prune_after_turns=5, context_window_turns=10)
        pruner = RealtimeContextPruner(config)
        turns = [self._make_turn(f"t{i}", audio_ref=f"ref{i}") for i in range(3)]
        result = pruner.prune(turns)
        assert not result.pruned
        assert result.pruned_turn_ids == []
        assert len(result.turns) == 3

    def test_prunes_oldest_audio_turns(self):
        config = RealtimeVoiceAgentConfig(prune_after_turns=2, context_window_turns=10)
        pruner = RealtimeContextPruner(config)
        turns = [self._make_turn(f"t{i}", audio_ref=f"ref{i}") for i in range(5)]
        result = pruner.prune(turns)
        assert result.pruned
        # Should prune turns 0, 1, 2 (keeping last 2: t3, t4)
        assert "t0" in result.pruned_turn_ids
        assert "t1" in result.pruned_turn_ids
        assert "t2" in result.pruned_turn_ids
        assert "t3" not in result.pruned_turn_ids
        assert "t4" not in result.pruned_turn_ids

    def test_pruned_turns_lose_audio_ref(self):
        config = RealtimeVoiceAgentConfig(prune_after_turns=1, context_window_turns=10)
        pruner = RealtimeContextPruner(config)
        turns = [self._make_turn(f"t{i}", audio_ref=f"ref{i}", text=f"text{i}") for i in range(3)]
        result = pruner.prune(turns)
        # t0 and t1 should have audio_ref removed
        pruned_turns = [t for t in result.turns if t.turn_id in result.pruned_turn_ids]
        for turn in pruned_turns:
            assert turn.audio_ref is None
            assert turn.metadata.get("raw_audio_replaced") is True

    def test_text_only_turns_not_pruned(self):
        config = RealtimeVoiceAgentConfig(prune_after_turns=1, context_window_turns=10)
        pruner = RealtimeContextPruner(config)
        turns = [
            self._make_turn("text_turn", text="Just text"),
            self._make_turn("audio1", audio_ref="ref1"),
            self._make_turn("audio2", audio_ref="ref2"),
        ]
        result = pruner.prune(turns)
        # text_turn should not be in pruned_turn_ids
        assert "text_turn" not in result.pruned_turn_ids

    def test_context_window_truncates_final_result(self):
        config = RealtimeVoiceAgentConfig(prune_after_turns=10, context_window_turns=3)
        pruner = RealtimeContextPruner(config)
        turns = [self._make_turn(f"t{i}", text=f"text{i}") for i in range(10)]
        result = pruner.prune(turns)
        assert len(result.turns) == 3
        # Should keep the last 3
        assert result.turns[0].turn_id == "t7"
        assert result.turns[2].turn_id == "t9"

    def test_raw_audio_turns_before_after_counts(self):
        config = RealtimeVoiceAgentConfig(prune_after_turns=2, context_window_turns=10)
        pruner = RealtimeContextPruner(config)
        turns = [self._make_turn(f"t{i}", audio_ref=f"ref{i}") for i in range(4)]
        result = pruner.prune(turns)
        assert result.raw_audio_turns_before == 4
        assert result.raw_audio_turns_after == 2

    def test_empty_turns_list(self):
        config = RealtimeVoiceAgentConfig(prune_after_turns=3, context_window_turns=10)
        pruner = RealtimeContextPruner(config)
        result = pruner.prune([])
        assert result.turns == []
        assert not result.pruned
        assert result.raw_audio_turns_before == 0
        assert result.raw_audio_turns_after == 0


# ─── RealtimeContextPruneResult ──────────────────────────────────────────────


class TestRealtimeContextPruneResult:
    def test_pruned_property_true_when_ids_present(self):
        result = RealtimeContextPruneResult(
            turns=[], pruned_turn_ids=["t1"], raw_audio_turns_before=1, raw_audio_turns_after=0
        )
        assert result.pruned is True

    def test_pruned_property_false_when_no_ids(self):
        result = RealtimeContextPruneResult(
            turns=[], pruned_turn_ids=[], raw_audio_turns_before=0, raw_audio_turns_after=0
        )
        assert result.pruned is False


# ─── RealtimeVoiceAgentConfig defaults ───────────────────────────────────────


class TestRealtimeVoiceAgentConfig:
    def test_default_values(self):
        config = RealtimeVoiceAgentConfig()
        assert config.sample_rate == 16000
        assert config.audio_format == "pcm_s16le"
        assert config.context_window_turns == 4
        assert config.prune_after_turns == 3
        assert config.tts_flush_chars == 180
        assert config.gemma_streaming_enabled is True


# ─── RealtimeVoiceTurnInput ──────────────────────────────────────────────────


class TestRealtimeVoiceTurnInput:
    def test_creates_with_uuid_defaults(self):
        run_id = uuid4()
        session_id = uuid4()
        turn = RealtimeVoiceTurnInput(
            run_id=run_id,
            realtime_session_id=session_id,
            room_name="test-room",
            participant_identity="user1",
        )
        assert turn.run_id == run_id
        assert turn.turn_id  # auto-generated
        assert turn.audio_pcm is None
        assert turn.transcript is None


# ─── RealtimeVoiceAgentEvent ─────────────────────────────────────────────────


class TestRealtimeVoiceAgentEvent:
    def test_event_uid_auto_generated(self):
        event = RealtimeVoiceAgentEvent(
            event_type="test_event",
            run_id=uuid4(),
            realtime_session_id=uuid4(),
            payload={"key": "value"},
        )
        assert event.voice_agent_event_uid.startswith("voice-event-")

    def test_created_at_auto_set(self):
        event = RealtimeVoiceAgentEvent(
            event_type="test",
            run_id=uuid4(),
            realtime_session_id=uuid4(),
            payload={},
        )
        assert event.created_at is not None
        assert event.created_at.tzinfo == timezone.utc
