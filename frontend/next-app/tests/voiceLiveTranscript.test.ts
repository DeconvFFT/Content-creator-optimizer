import assert from "node:assert/strict";
import test from "node:test";

import {
  EMPTY_LIVE_VOICE_TRANSCRIPT,
  liveVoiceTranscriptFromAgentEvent
} from "../lib/voice/liveTranscript";

test("live voice transcript tracks committed user audio and Gemma deltas", () => {
  const committed = liveVoiceTranscriptFromAgentEvent(
    EMPTY_LIVE_VOICE_TRANSCRIPT,
    "voice_user_turn_committed",
    {
      turn_id: "turn-1",
      transcript: "Make a reel about inference engineering."
    }
  );

  assert.equal(committed.userStatus, "committed");
  assert.equal(committed.userCaption, "Make a reel about inference engineering.");
  assert.equal(committed.assistantStatus, "thinking");
  assert.equal(committed.assistantCaption, "Gemma is thinking...");

  const firstDelta = liveVoiceTranscriptFromAgentEvent(
    committed,
    "assistant_text_delta",
    {
      turn_id: "turn-1",
      response_id: "response-1",
      text_delta: "Think of inference"
    }
  );
  const secondDelta = liveVoiceTranscriptFromAgentEvent(
    firstDelta,
    "assistant_text_delta",
    {
      turn_id: "turn-1",
      response_id: "response-1",
      text_delta: " "
    }
  );
  const thirdDelta = liveVoiceTranscriptFromAgentEvent(
    secondDelta,
    "assistant_text_delta",
    {
      turn_id: "turn-1",
      response_id: "response-1",
      text_delta: "like a kitchen."
    }
  );

  assert.equal(thirdDelta.assistantStatus, "thinking");
  assert.equal(thirdDelta.assistantCaption, "Think of inference like a kitchen.");
  assert.equal(thirdDelta.responseId, "response-1");
});

test("live voice transcript moves to speaking and completed states", () => {
  const drafting = liveVoiceTranscriptFromAgentEvent(
    EMPTY_LIVE_VOICE_TRANSCRIPT,
    "assistant_text_delta",
    {
      response_id: "response-2",
      text_delta: "Here is the short answer."
    }
  );
  const speaking = liveVoiceTranscriptFromAgentEvent(
    drafting,
    "assistant_audio_chunk_published",
    {
      response_id: "response-2"
    }
  );
  const completed = liveVoiceTranscriptFromAgentEvent(
    speaking,
    "assistant_response_completed",
    {
      response_id: "response-2",
      assistant_text: "Here is the final answer."
    }
  );

  assert.equal(speaking.assistantStatus, "speaking");
  assert.equal(speaking.assistantCaption, "Here is the short answer.");
  assert.equal(completed.assistantStatus, "completed");
  assert.equal(completed.assistantCaption, "Here is the final answer.");
});

test("live voice transcript handles pending transcripts and interruption states", () => {
  const pending = liveVoiceTranscriptFromAgentEvent(
    EMPTY_LIVE_VOICE_TRANSCRIPT,
    "voice_user_turn_committed",
    {
      turn_id: "turn-3"
    }
  );
  const cancelled = liveVoiceTranscriptFromAgentEvent(
    pending,
    "gemma_kokoro_voice_turn_cancelled",
    {
      turn_id: "turn-3",
      response_id: "response-3"
    }
  );
  const noActive = liveVoiceTranscriptFromAgentEvent(
    cancelled,
    "voice_interrupt_no_active_response",
    {}
  );

  assert.equal(pending.userCaption, "Audio turn committed; transcript pending.");
  assert.equal(cancelled.assistantStatus, "cancelled");
  assert.equal(cancelled.assistantCaption, "Response stopped.");
  assert.equal(noActive.assistantCaption, "No active response to stop.");
});

test("live voice transcript promotes a pending user caption without wiping assistant output", () => {
  const pending = liveVoiceTranscriptFromAgentEvent(
    EMPTY_LIVE_VOICE_TRANSCRIPT,
    "voice_user_turn_committed",
    {
      turn_id: "turn-promote"
    }
  );
  const drafting = liveVoiceTranscriptFromAgentEvent(
    pending,
    "assistant_text_delta",
    {
      turn_id: "turn-promote",
      response_id: "response-promote",
      text_delta: "I will make this concrete."
    }
  );
  const promoted = liveVoiceTranscriptFromAgentEvent(
    drafting,
    "voice_user_turn_committed",
    {
      turn_id: "turn-promote",
      transcript: "Create an inference engineering reel."
    }
  );

  assert.equal(promoted.userCaption, "Create an inference engineering reel.");
  assert.equal(promoted.assistantStatus, "thinking");
  assert.equal(promoted.assistantCaption, "I will make this concrete.");
  assert.equal(promoted.assistantText, "I will make this concrete.");
  assert.equal(promoted.responseId, "response-promote");
});

test("live voice transcript exposes Gemma/Kokoro provider failures", () => {
  const pending = liveVoiceTranscriptFromAgentEvent(
    EMPTY_LIVE_VOICE_TRANSCRIPT,
    "voice_user_turn_committed",
    {
      turn_id: "turn-failed",
      transcript: "Try the live provider path."
    }
  );
  const failed = liveVoiceTranscriptFromAgentEvent(
    pending,
    "gemma_kokoro_voice_turn_failed",
    {
      turn_id: "turn-failed",
      response_id: "response-failed",
      failure_stage: "gemma_generation",
      failure_reason: "Gemma 4 streaming request failed."
    }
  );

  assert.equal(failed.assistantStatus, "failed");
  assert.equal(
    failed.assistantCaption,
    "gemma_generation failed: Gemma 4 streaming request failed."
  );
  assert.equal(failed.responseId, "response-failed");
});

test("live voice transcript ignores stale old-response events after a new turn starts", () => {
  const firstTurn = liveVoiceTranscriptFromAgentEvent(
    EMPTY_LIVE_VOICE_TRANSCRIPT,
    "voice_user_turn_committed",
    {
      turn_id: "turn-1",
      transcript: "First turn"
    }
  );
  const firstDraft = liveVoiceTranscriptFromAgentEvent(
    firstTurn,
    "assistant_text_delta",
    {
      turn_id: "turn-1",
      response_id: "response-1",
      text_delta: "Old answer"
    }
  );
  const secondTurn = liveVoiceTranscriptFromAgentEvent(
    firstDraft,
    "voice_user_turn_committed",
    {
      turn_id: "turn-2",
      transcript: "Second turn"
    }
  );

  assert.equal(secondTurn.responseId, null);
  assert.equal(secondTurn.assistantCaption, "Gemma is thinking...");

  const staleCompletion = liveVoiceTranscriptFromAgentEvent(
    secondTurn,
    "assistant_response_completed",
    {
      turn_id: "turn-1",
      response_id: "response-1",
      assistant_text: "Old answer should not repaint"
    }
  );
  const secondDraft = liveVoiceTranscriptFromAgentEvent(
    staleCompletion,
    "assistant_text_delta",
    {
      turn_id: "turn-2",
      response_id: "response-2",
      text_delta: "Fresh answer"
    }
  );
  const staleDelta = liveVoiceTranscriptFromAgentEvent(
    secondDraft,
    "assistant_text_delta",
    {
      turn_id: "turn-1",
      response_id: "response-1",
      text_delta: " stale"
    }
  );

  assert.equal(staleCompletion.assistantCaption, "Gemma is thinking...");
  assert.equal(secondDraft.responseId, "response-2");
  assert.equal(secondDraft.assistantCaption, "Fresh answer");
  assert.equal(staleDelta.assistantCaption, "Fresh answer");

  const staleSpeechStart = liveVoiceTranscriptFromAgentEvent(
    secondDraft,
    "voice_user_speech_started",
    {
      turn_id: "turn-1"
    }
  );
  const staleUserCommit = liveVoiceTranscriptFromAgentEvent(
    staleSpeechStart,
    "voice_user_turn_committed",
    {
      turn_id: "turn-1",
      transcript: "Late first-turn transcript"
    }
  );

  assert.equal(staleSpeechStart.turnId, "turn-2");
  assert.equal(staleSpeechStart.userCaption, "Second turn");
  assert.equal(staleSpeechStart.assistantCaption, "Fresh answer");
  assert.equal(staleSpeechStart.responseId, "response-2");
  assert.equal(staleUserCommit.turnId, "turn-2");
  assert.equal(staleUserCommit.userCaption, "Second turn");
  assert.equal(staleUserCommit.assistantCaption, "Fresh answer");
  assert.equal(staleUserCommit.responseId, "response-2");
});
