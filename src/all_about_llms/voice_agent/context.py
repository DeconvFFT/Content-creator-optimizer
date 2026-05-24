from dataclasses import dataclass

from all_about_llms.voice_agent.models import (
    RealtimeVoiceAgentConfig,
    VoiceConversationTurn,
)


@dataclass(slots=True)
class RealtimeContextPruneResult:
    turns: list[VoiceConversationTurn]
    pruned_turn_ids: list[str]
    raw_audio_turns_before: int
    raw_audio_turns_after: int

    @property
    def pruned(self) -> bool:
        return bool(self.pruned_turn_ids)


class RealtimeContextPruner:
    def __init__(self, config: RealtimeVoiceAgentConfig):
        self._config = config

    def prune(
        self,
        turns: list[VoiceConversationTurn],
    ) -> RealtimeContextPruneResult:
        raw_audio_turns = [turn for turn in turns if turn.audio_ref]
        keep_ids = {
            turn.turn_id for turn in raw_audio_turns[-self._config.prune_after_turns :]
        }
        pruned_ids: list[str] = []
        compacted: list[VoiceConversationTurn] = []
        for turn in turns:
            if not turn.audio_ref or turn.turn_id in keep_ids:
                compacted.append(turn)
                continue
            pruned_ids.append(turn.turn_id)
            compacted.append(
                VoiceConversationTurn(
                    turn_id=turn.turn_id,
                    role=turn.role,
                    text=turn.text,
                    audio_ref=None,
                    audio_duration_ms=0,
                    summary=turn.summary
                    or _summarize_audio_turn_for_context(turn),
                    interrupted=turn.interrupted,
                    heard_by_user=turn.heard_by_user,
                    created_at=turn.created_at,
                    metadata={
                        **turn.metadata,
                        "raw_audio_replaced": True,
                        "replacement_strategy": "transcript_plus_summary",
                        "original_audio_duration_ms": turn.audio_duration_ms,
                    },
                )
            )
        final_turns = compacted[-self._config.context_window_turns :]
        raw_audio_after = sum(1 for turn in final_turns if turn.audio_ref)
        return RealtimeContextPruneResult(
            turns=final_turns,
            pruned_turn_ids=pruned_ids,
            raw_audio_turns_before=len(raw_audio_turns),
            raw_audio_turns_after=raw_audio_after,
        )


def _summarize_audio_turn_for_context(turn: VoiceConversationTurn) -> str:
    if turn.text:
        return turn.text[:320]
    duration = round(turn.audio_duration_ms / 1000, 2)
    state = "interrupted" if turn.interrupted else "completed"
    heard = "heard" if turn.heard_by_user else "partially heard"
    return f"{state} voice turn, {duration}s, {heard}; transcript unavailable."
