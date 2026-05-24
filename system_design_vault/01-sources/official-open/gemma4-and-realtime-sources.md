---
type: source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_urls:
  - https://huggingface.co/docs/transformers/model_doc/gemma4
  - https://developers.openai.com/api/docs/guides/realtime
  - https://docs.livekit.io/agents/logic/turns/
  - https://docs.livekit.io/transport/data/packets/
  - https://huggingface.co/hexgrad/Kokoro-82M
  - https://elevenlabs.io/docs/api-reference/text-to-speech/v-1-text-to-speech-voice-id-stream-input
  - https://docs.cartesia.ai/api-reference/tts/websocket
source_status: official_public
---

# Gemma 4 And Realtime Voice Sources

## Direct-Read Scope

This pass read Hugging Face's Gemma 4 Transformers documentation, OpenAI's current Realtime guide, LiveKit turn-management and data-packet docs, the Kokoro-82M model card, and current ElevenLabs/Cartesia streaming TTS WebSocket docs. It records original synthesis only and stores no raw source text or long excerpts.

Current-source check on 2026-05-18: Hugging Face's Gemma 4 Transformers docs still list Gemma 4 as multimodal with E2B, E4B, 31B, and 26B-A4B MoE variants, configurable reasoning/thinking, system-role support, function calling, 128K or 256K context windows, image patch/soft-token constraints, and audio support only for E2B/E4B input understanding. OpenAI's Realtime guide still separates realtime voice, transcription, translation, and speech-generation session patterns with WebRTC, WebSocket, and telephony-style connection choices. LiveKit still treats turn-taking as an explicit subsystem with VAD, STT endpointing, realtime-provider turn detection, manual controls, interruption handling, and topic-scoped data packets. ElevenLabs, Cartesia, and Kokoro sources still support the conclusion that TTS requires its own voice, format, alignment, rights, cancellation, and latency evidence.

## Layering Decision

Gemma 4 and realtime voice should be separate route layers:

- Gemma 4 is the expert reasoning and multimodal understanding family.
- Realtime providers own live session transport, turn lifecycle, streaming audio, interruptions, and low-latency event flow.
- TTS providers own waveform generation, alignment/timestamps, voice settings, cancellation, and audio format contracts.
- LiveKit owns the product WebRTC room and frontend/backend audio event surface when Agent Studio uses a provider-pluggable voice stack.

This prevents the product from forcing a long-context expert model to act as a telephony/audio runtime.

## Gemma 4 Read

Hugging Face's Gemma 4 page frames the family as multimodal and agent-capable:

- E2B/E4B, 31B, and 26B-A4B MoE variants serve different latency/capacity roles.
- All models handle text and image; E2B/E4B add native video/audio support.
- Smaller models support 128K context and larger models support 256K context.
- Function calling and native system-role support make the family plausible for tool-using expert routes.
- Vision input has explicit patch/soft-token constraints; visual routes should store token budget, resolution/aspect assumptions, and preprocessing policy.
- Audio on E2B/E4B is an input-understanding path, not a guarantee of low-latency speech waveform output.

Agent Studio should treat Gemma 4 model selection as a serving/profile decision, not a brand-level toggle.

## Realtime Session Read

OpenAI's Realtime guide separates voice-agent, translation, transcription, and speech-generation sessions. That distinction matters even when Agent Studio uses other providers:

- voice-agent sessions keep conversation state and can respond, call tools, and emit events;
- translation sessions stream continuously and do not follow the same assistant turn lifecycle;
- transcription sessions produce streaming transcript deltas without model-generated spoken responses;
- browser/mobile capture should prefer WebRTC, while server-side media pipelines can use WebSockets and telephony uses SIP-style integration;
- every realtime session should carry a privacy-preserving safety/user identifier when supported.

The design implication is that "realtime" is not one provider adapter. Agent Studio needs session type, connection type, event schema, turn lifecycle, safety identifier, and transcript/output policy per route.

## LiveKit Turn And Event Read

LiveKit's turn docs make turn-taking an explicit subsystem:

- VAD, STT endpointing, provider-side realtime turn detection, and manual turn control are different modes.
- Interruption behavior changes depending on whether the realtime model owns server-side turn detection.
- Manual turn control needs explicit start, end, cancel, clear, commit, and interrupt operations.
- Dynamic endpointing, noise cancellation, and adaptive interruption handling are product-quality levers, not afterthoughts.
- Session events and interruption/turn-taking events should be captured for readiness and debugging.

LiveKit data packets add a practical transport for topic-scoped timing and control messages. Agent Studio should use reliable packets for critical control/timing ledgers and lossy packets only for non-critical UI hints.

## TTS Provider Read

Streaming TTS is not interchangeable final-audio generation:

- ElevenLabs WebSocket TTS is useful when input text arrives in chunks and word/audio alignment is needed.
- ElevenLabs also exposes final/partial audio messages and alignment fields that can support transcript-to-audio timing ledgers.
- Cartesia's WebSocket API uses context IDs, explicit output format, timestamps, chunk responses, flush completion, done events, and context cancellation.
- Kokoro-82M is an open local TTS option with a documented model card, 24 kHz examples, architecture references, and permissive/non-copyrighted training-data claims, but local deployment still needs its own latency, voice, language, rights, and quality evidence.

Agent Studio should store text-to-speech as a provider route with voice identity, sample rate, encoding, alignment policy, cancellation contract, rights/consent status, latency, and quality evals.

## Agent Studio Design Implications

- Use a provider-neutral `RealtimeSession` contract with session type: voice agent, transcription, translation, or TTS-only.
- Use a separate `TurnPolicy` contract for VAD, STT endpointing, realtime-model turn detection, manual push-to-talk, endpointing delays, interruption behavior, and noise cancellation.
- Keep Gemma 4 expert synthesis outside the live audio critical path unless the selected Gemma 4 model and provider path have measured TTFT/TPOT and turn-latency proof.
- Treat E2B/E4B audio as multimodal understanding; do not claim it replaces ASR/TTS transport or a low-latency speech pipeline without provider-backed evidence.
- Record realtime timing with session ID, turn ID, response ID, transcript deltas, audio deltas, interrupt events, endpointing events, provider events, and frontend playback state.
- Provider-free dry smoke validates contracts only. Production readiness requires provider-backed WebRTC/WebSocket/SIP evidence, real transcript deltas, first audio timing, cancellation, and recovery from interruption.
- Local/open TTS routes need explicit model card, voice rights, sample-rate/encoding, G2P/text-normalization, alignment, and benchmark records.

## Datastore Requirements

- `realtime_session_record`: provider, session type, connection type, model/voice refs, safety identifier hash, start/end, tool support, transcript policy, and status.
- `turn_policy_record`: VAD/STT/realtime/manual mode, endpointing delays, interruption mode, noise cancellation, provider-side settings, and route applicability.
- `turn_timing_event`: session ID, turn ID, response ID, event type, provider timestamp, client timestamp, server timestamp, payload hash, and ordering status.
- `transcript_delta_record`: session/turn refs, delta type, text hash, finality, confidence/source provider, alignment refs, and correction lineage.
- `audio_delta_record`: session/response refs, codec/container, sample rate, duration, byte hash, playback status, and alignment refs.
- `tts_stream_record`: provider, voice ref, context ID, transcript hash, output format, chunk refs, flush/done status, cancel status, and latency.
- `voice_provider_smoke`: provider/model/voice refs, connection type, first transcript delta, first audio delta, interrupt proof, cancellation proof, fallback path, and blocker summary.
- `multimodal_input_budget`: model ref, modality, token/patch/audio constraints, preprocessing policy, context budget, and truncation risk.
- `voice_rights_record`: voice/model source, license or consent basis, allowed uses, blocked uses, attribution requirement, expiry, and review status.

## Realtime Voice Stack Release Gate

`realtime_voice_stack_release_gate` is the promotion gate for any route that combines expert reasoning, realtime session transport, turn-taking, speech recognition, TTS, LiveKit/WebRTC-style media, or local/open voice models. It prevents a route from claiming "voice ready" when only one layer has been tested.

Required evidence:

- `gate_id`, `route_id`, `candidate_release_id`, `session_type`, `connection_type`, `expert_model_ref`, `realtime_provider_ref`, `transport_provider_ref`, `asr_provider_ref`, `tts_provider_ref`, `local_tts_model_ref`, and `fallback_route_ref`;
- `gemma_model_profile_ref`, `multimodal_input_budget_refs`, `context_window_policy_ref`, `vision_patch_policy_ref`, `audio_input_understanding_policy_ref`, and `function_calling_policy_ref`;
- `realtime_session_refs`, `realtime_credential_refs`, `realtime_control_channel_refs`, `turn_policy_refs`, `turn_timing_event_refs`, `transcript_delta_refs`, `audio_delta_refs`, and `speech_io_trace_refs`;
- `tts_stream_refs`, `voice_provider_smoke_refs`, `first_transcript_delta_ref`, `first_audio_delta_ref`, `endpointing_proof_ref`, `interrupt_proof_ref`, `cancel_proof_ref`, `reconnect_or_recovery_ref`, and `playback_state_refs`;
- `voice_rights_refs`, `voice_consent_refs`, `sample_rate_or_codec_refs`, `alignment_policy_ref`, `text_normalization_policy_ref`, `provider_privacy_boundary_ref`, `retention_cleanup_policy_ref`, `latency_slo_ref`, `quality_eval_refs`, `fallback_mode_refs`, `rollback_target_ref`, `decision`, and `reviewed_at`.

Do not promote a realtime voice route when:

- Gemma 4 audio input support is treated as proof of low-latency spoken output;
- a dry smoke test is used as provider readiness without first transcript, first audio, interruption, cancellation, and recovery evidence;
- realtime voice, transcription, translation, and TTS-only sessions share one adapter without explicit session type and event schema;
- media/control channels, ephemeral credentials, and sideband server authority are not separated;
- partial transcript/audio deltas are overwritten by final text without timing and correction lineage;
- turn policy is unspecified, making VAD, STT endpointing, realtime-provider turn detection, and manual push-to-talk incomparable;
- a TTS voice or local/open voice model lacks rights, consent, format, alignment, language/accent, quality, latency, and retention evidence.

## Failure Modes

- Treating a realtime voice provider, a TTS provider, and a long-context reasoning model as one route.
- Reporting readiness from dry smoke when credentials, provider connection, first audio, and cancellation were never exercised.
- Losing partial transcript/audio evidence by overwriting deltas with final text.
- Using a TTS voice without a recorded rights or consent policy.
- Ignoring turn-taking mode when comparing latency; VAD-only, STT endpointing, server-side realtime VAD, and manual push-to-talk are not equivalent.
- Allowing deep expert synthesis to block barge-in, endpointing, or first audio.
