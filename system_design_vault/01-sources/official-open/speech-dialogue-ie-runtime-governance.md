---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_source_note
rights_status: official_public_docs
sources:
  - https://developers.openai.com/api/reference/resources/realtime
  - https://docs.cloud.google.com/speech-to-text/docs/v1/best-practices
  - https://docs.cloud.google.com/speech-to-text/docs/v1/transcribe-streaming-audio
  - https://docs.cloud.google.com/text-to-speech/docs
  - https://docs.cloud.google.com/text-to-speech/docs/ssml
  - https://docs.cloud.google.com/natural-language/docs/basics
  - https://spacy.io/api/entitylinker/
  - https://spacy.io/usage/linguistic-features
  - https://stanfordnlp.github.io/CoreNLP/coref.html
  - https://stanfordnlp.github.io/corenlp-docs-dev/annotators.html
related:
  - "[[../../02-books/speech-language-processing/rag-dialogue-speech-ie]]"
  - "[[../../03-patterns/llm-systems/nlp-llm-systems-canon]]"
  - "[[../../03-patterns/inference/realtime-and-inference-patterns]]"
  - "[[../../03-patterns/retrieval/reranking-search-kg-patterns]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Speech, Dialogue, And IE Runtime Governance

## Direct-Read Scope

Direct-read pass over official OpenAI Realtime API reference material, Google Cloud Speech-to-Text and Text-to-Speech docs, Google Cloud Natural Language entity-analysis docs, spaCy entity-linking docs, and Stanford CoreNLP coreference/relation/OpenIE docs.

This note cross-checks the local Speech and Language Processing synthesis for production Agent Studio design. It stores no raw book text, transcripts, code samples, or long source excerpts.

Current-doc check on 2026-05-18: OpenAI Realtime remains a typed session/event surface and now exposes richer tool and remote MCP controls in the realtime schema. Google Cloud Speech-to-Text V1 docs explicitly point new users to V2 while still documenting best practices and gRPC streaming behavior, including realtime stream results and single-utterance behavior. Google TTS still separates voice, language, SSML, audio config, long-audio operations, and streaming synthesis types. Google Natural Language still exposes entity analysis as a managed annotation method, while spaCy and CoreNLP continue to separate entity linking/coreference from mention detection and other annotators.

## Source Signals

OpenAI Realtime treats live conversation as a typed event and session surface, not just audio bytes. Turn detection can be server VAD, semantic VAD, or client-managed; semantic VAD improves natural turn-taking but adds latency tradeoffs. This supports the SLP rule that dialogue turn boundaries are product state, not incidental UI behavior.

Google Speech-to-Text best-practice docs make audio configuration part of correctness. Sampling rate, codec choice, channel/speaker setup, frame size, language code, hints, and streaming method affect accuracy, latency, and billing. The streaming docs also draw a hard line between batch-style transcription and realtime bidirectional streams.

Google Text-to-Speech docs separate voice selection, SSML support, device profile, supported voices/languages, quotas, and regional endpoints. The SSML page also makes support partial rather than universal, which means Agent Studio cannot assume every markup or voice-control instruction is portable across providers.

Google Natural Language entity analysis exposes entities, mentions, offsets, salience, types, and metadata. It is useful as a managed extraction baseline, but it should not become unreviewed truth: offsets depend on encoding, sentiment is coarse, and entity detection/linkage must preserve source text provenance and confidence.

spaCy separates entity recognition from entity linking. The EntityLinker predicts KB identifiers, can emit NIL, and updates a linking model/context encoder from examples. This matches the SLP boundary between mention detection, discourse coreference, and real-world entity identity.

Stanford CoreNLP exposes coreference as an annotator over mention chains and exposes relation extraction/OpenIE as separate annotators. Its docs make speed/accuracy tradeoffs visible through model and distance settings, reinforcing that graph construction needs pipeline versioning and evaluation rather than one generic "NLP extraction" flag.

## Canon Lessons

- Realtime voice routes need three state planes: audio transport, dialogue state, and task/source state. A final transcript alone is not enough evidence.
- Turn-taking is a release parameter. Server VAD, semantic VAD, manual turn control, barge-in behavior, silence timeouts, and interruption handling need route-level config and eval.
- Speech quality is input-sensitive. Audio format, sampling rate, channel layout, speaker/noise conditions, hints, language code, and frame size must be captured before ASR output can drive memory or external action.
- TTS quality is provider- and voice-specific. SSML, voice choice, device profile, supported language, output format, latency, and listener evaluation must be explicit.
- Entity extraction should produce candidates, not facts. Mention offsets, entity type, salience, metadata, KB ID, NIL state, relation triple, temporal anchor, and source span must stay attached until review/promotion.
- Coreference and entity linking are separate risks. A correct mention span can still be linked to the wrong entity or merged into the wrong discourse chain.
- Managed NLP APIs and open-source pipelines are interchangeable only behind a typed adapter that records model/version, language, offset encoding, confidence, and unsupported cases.

## Agent Studio Design Implications

Promote the local Speech and Language Processing note to canon-ready only with these runtime constraints:

- voice routes require `turn_policy_record`, `speech_io_trace`, `transcript_delta_record`, `asr_eval_result`, `tts_eval_result`, `endpointing_event`, and `voice_privacy_record`;
- dialogue routes require `dialogue_turn_record`, `dialogue_act_record`, `dialogue_state_record`, `frame_slot_record`, and `subdialogue_record`;
- extraction routes require `named_entity_mention`, `relation_extraction_record`, `event_record`, `temporal_expression_record`, `template_fill_record`, `coreference_chain_record`, and `entity_link_record`;
- every extraction-backed graph fact needs source span, extractor version, confidence, candidate set, review status, and downstream-use policy;
- realtime voice cannot be enabled for publishing or external tool actions until transcript confidence, endpointing behavior, and user confirmation policy are visible.

## Speech, Dialogue, And IE Release Gate

A dialogue/speech/IE route cannot be promoted unless a `speech_dialogue_ie_release_gate` is approved. The gate should bind route ID, realtime session type, provider/API version, region, credential boundary, audio sample rate, codec, channel policy, language policy, frame-size policy, turn detection mode, interruption/barge-in policy, transcript-finalization policy, partial-transcript handling, ASR eval slices, TTS voice/config/SSML support, first-transcript and first-audio timing, tool/MCP availability for realtime routes, dialogue state policy, extraction pipeline version, offset encoding, candidate entity/link/coreference sets, graph-write confidence/review policy, privacy/retention policy, bias slice checks, fallback mode, and rollback target.

Minimum evidence:

- audio sample rate, codec, language, channel policy, and frame-size policy are captured;
- turn detection and interruption behavior are tested with short commands, trailing speech, pauses, corrections, and background noise;
- partial transcripts are separated from final transcript evidence;
- TTS voice, SSML support, output format, and first-audio latency are recorded;
- entity/coreference/linking outputs preserve offsets and candidate IDs;
- graph writes require review or confidence thresholds appropriate to the route;
- bias/privacy checks cover accent, dialect, name, gender, language, and sensitive-entity slices when those outputs affect memory, retrieval, or publishing.

## Open Caveats

Provider docs and model behavior change. Agent Studio should version-pin provider API version, model/voice, language support, region, quota, and adapter behavior for every promoted route. Official docs provide runtime boundaries; route-specific evals are still required before production use.
