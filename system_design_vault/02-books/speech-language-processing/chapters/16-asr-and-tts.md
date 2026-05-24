---
type: book-chapter-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source:
  local_path: /Users/saumyamehta/DS interview prep/books/NLPbook.pdf
  title: "Speech and Language Processing"
  authors: "Daniel Jurafsky and James H. Martin"
  edition: "Third Edition draft, January 12, 2025"
chapter:
  number: 16
  title: "Automatic Speech Recognition and Text-to-Speech"
extraction:
  method: pdftotext
  physical_pages: "339-365"
  temp_extract: "/private/tmp/slp_ch16_asr_tts.txt"
stores_raw_source_text: false
related:
  - "[[../rag-dialogue-speech-ie]]"
  - "[[../../../01-sources/official-open/speech-dialogue-ie-runtime-governance]]"
  - "[[../../../01-sources/official-open/gemma4-and-realtime-sources]]"
  - "[[../../../03-patterns/inference/realtime-and-inference-patterns]]"
  - "[[../../../03-patterns/llm-systems/nlp-llm-systems-canon]]"
  - "[[../../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Chapter 16 - Automatic Speech Recognition And Text-To-Speech

## Reading Scope

This is a direct-read chapter synthesis from the local official/user-provided Speech and Language Processing PDF. It covers Chapter 16 only: ASR task variation, audio feature extraction, encoder-decoder ASR, CTC, RNN-T streaming, WER and ASR significance testing, TTS text normalization, spectrogram prediction, neural vocoding, TTS listening evaluation, wake words, diarization, speaker recognition, and language identification.

This note stores original system-design synthesis only. It does not store copied chapter text, figures, equations as a reference dump, exercises, audio examples, or long excerpts.

## Why This Chapter Matters

Realtime Agent Studio routes cannot treat speech as just chat with a microphone. Chapter 16 makes speech a separate production subsystem with its own capture format, task slice, model family, latency profile, metric protocol, and human evaluation surface.

The design rule: a voice route is not ready unless it can prove:

- what audio format and channel it accepts;
- what speech task slice it targets;
- whether it needs streaming partials or offline accuracy;
- which decoding and language-model policy produced the transcript;
- how transcript errors affect dialogue state, tools, memory, and publishing;
- how TTS text is normalized before speech is generated;
- how the voice output was evaluated by listeners or pairwise preference tests.

## ASR Task Slice Is The First Release Decision

ASR difficulty changes sharply by vocabulary size, interaction type, channel, noise, speaker population, accent/dialect, and age. Read speech, dictated commands, human-machine dialogue, telephone conversations, multiparty meetings, and noisy distant-microphone dinner-table speech are not interchangeable workloads.

Agent Studio should record every speech route against a `speech_corpus_slice_record` rather than reporting one aggregate "speech quality" number. A route for clean single-speaker narration does not prove readiness for meetings, livestream critique, phone audio, accented speech, child speech, or code-switched social content review.

Useful route dimensions:

| Dimension | Agent Studio implication |
|---|---|
| Vocabulary and domain | A command route can use narrow grammars; open transcription needs broad lexical and entity handling. |
| Human-machine vs human-human speech | User-directed commands are cleaner; meetings and natural dialogue need repair and diarization evidence. |
| Channel and noise | Microphone, telephone, distant room audio, body microphones, compression, and noise require separate eval slices. |
| Speaker/dialect slice | Accuracy should be tracked by accent, dialect, age group, and other speaker classes where errors can cause product harm. |
| Multilingual slice | WER, CER, language identification, and tokenization choices may differ by language and script. |

## Audio Frontend Contract

The chapter's feature pipeline starts before the model. Sampling rate, quantization, channel count, compression, frame/window parameters, DFT/FFT features, mel filtering, and log scaling are all part of the input contract.

Agent Studio should not let an ASR provider or local model hide this behind a single `audio_file` field. The datastore should retain:

- sample rate and whether resampling occurred;
- bit depth or compression;
- mono/stereo/channel separation policy;
- window size, stride, and feature representation when local processing is used;
- noise profile and capture device;
- transcript finalization policy before downstream use.

This matters because training and test audio must be comparable. A route trained or tuned for 16 kHz microphone speech should not be evaluated only on downsampled telephone audio unless that is the actual product target.

## ASR Architecture And Decoding Policy

Encoder-decoder ASR maps acoustic feature sequences to characters or subword units and can use attention and beam search. It often benefits from a separate language model because paired speech-transcript data is scarcer than plain text.

CTC uses a blank-aware alignment/collapse policy to map long acoustic frames to shorter transcripts. It is attractive for streaming because it can emit left-to-right, but its independence assumptions mean decoder policy and language-model interpolation matter.

RNN-T adds output-history conditioning for streaming by pairing an acoustic encoder with a predictor network. For Agent Studio, that turns model choice into an operational tradeoff:

| Model/decode choice | Product implication |
|---|---|
| Attention encoder-decoder | Strong offline accuracy path, but less natural for low-latency partial transcripts. |
| CTC | Streaming-friendly and simpler to emit incrementally, but needs careful blank/collapse handling and often LM support. |
| CTC plus encoder-decoder | Useful hybrid when a route needs both alignment pressure and decoder accuracy. |
| RNN-T | Stronger streaming route when partial transcripts and output-history conditioning both matter. |
| Beam/n-best plus LM rescoring | Useful for domain terms, names, and source titles, but must record LM version, length policy, and reranking weights. |

The route ledger should store `asr_decoder_policy_record`, `ctc_alignment_record`, and `asr_lm_rescore_record` so a transcript can be traced back to the decoding method, not only the final text.

## ASR Evaluation And Error Analysis

WER is edit distance over words: insertions, substitutions, and deletions divided by reference words. It is useful but blunt. Chapter 16 also emphasizes sentence-level error rates, confusion analysis, per-speaker rates, and significance testing across paired segments.

Agent Studio should use WER as a gate only with slice metadata:

- read speech versus conversational speech;
- clean versus noisy audio;
- dialect/accent and speaker class;
- channel/microphone type;
- domain vocabulary;
- whether punctuation, casing, disfluencies, or normalization are included;
- whether downstream task success depends on exact words or semantic slots.

For dialogue and tool routes, WER must be paired with slot/concept error rate, correction burden, and downstream action-error analysis. A low WER transcript can still corrupt a route if it misses a proper noun, date, source title, negative instruction, or publish constraint.

## TTS Pipeline Contract

TTS is the reverse direction but not a mirror-image API. Modern systems commonly split into text preprocessing, spectrogram prediction, and vocoding. Text normalization is release-critical because numbers, dates, abbreviations, currency, times, measures, acronyms, and URLs can be spoken in multiple valid or invalid ways.

Agent Studio should store a `tts_text_normalization_record` before generating voice output. The same written artifact can need different spoken forms depending on locale, platform, audience, style, and safety constraints.

TTS quality also depends on voice identity, speaker dependence, training data, vocoder behavior, latency, sample rate, output encoding, and rights. A route that generates text well is not automatically voice-ready.

## TTS Evaluation

The chapter treats TTS evaluation as a human-listening problem. MOS and AB preference tests remain core because automatic metrics do not fully replace human perception.

Agent Studio should require `tts_eval_result` for public or brand-sensitive voice routes:

- listener setup and sample count;
- sentence set and content domain;
- MOS or AB preference result;
- latency and streaming behavior;
- pronunciation and normalization failures;
- voice identity and rights review;
- known failures by language, accent, or specialized terms.

## Other Speech Tasks

Wake-word detection, speaker diarization, speaker verification/identification, and language identification are separate tasks, not optional labels on ASR.

For Agent Studio:

- wake-word or push-to-talk routes need edge/privacy records and false accept/false reject thresholds;
- diarization is required before multiparty meeting notes, critique attribution, or participant-specific memory;
- speaker verification must be handled as a security-sensitive identity signal, not just metadata;
- language identification should route transcripts to language-specific ASR/TTS and eval policies.

## Datastore Additions

| Object | Purpose |
|---|---|
| `speech_corpus_slice_record` | Declares the ASR/TTS workload slice: channel, speaker class, dialect/accent, noise, domain, language, and interaction type. |
| `audio_frontend_record` | Captures sample rate, bit depth/compression, channels, window/stride, feature representation, resampling, and noise profile. |
| `asr_decoder_policy_record` | Records model family, unit type, beam/n-best settings, streaming/finalization policy, and decoding constraints. |
| `ctc_alignment_record` | Captures CTC blank/collapse alignment evidence, confidence, and transcript segment linkage. |
| `asr_lm_rescore_record` | Records language-model rescoring, interpolation weights, length policy, n-best input, and domain vocabulary policy. |
| `asr_significance_test_record` | Stores paired WER comparison setup, segment policy, test type, and decision. |
| `tts_text_normalization_record` | Versioned policy for verbalizing numbers, dates, abbreviations, currency, times, URLs, and domain terms. |
| `vocoder_config_record` | Records waveform generation model, spectrogram input, sample representation, autoregressive/parallel mode, and latency risk. |
| `wake_word_policy_record` | Edge/privacy wake-word detector contract with false accept/reject targets and capture boundary. |
| `speaker_diarization_record` | Speaker-turn segmentation, VAD policy, speaker embeddings/clusters, and review status. |

## Agent Studio Design Implications

- Require a speech workload slice before comparing ASR providers or local models.
- Store audio frontend evidence, not only final transcripts.
- Separate streaming partial transcripts from final transcript records and from dialogue-state updates.
- Record decoder, CTC/RNN-T, LM rescoring, and finalization policy so ASR errors can be debugged.
- Evaluate ASR by WER plus task-specific slot/action errors, speaker slices, and significance evidence.
- Treat TTS text normalization as a versioned policy before voice generation.
- Require human-listening evidence for public, brand, or high-volume TTS routes.
- Keep wake-word, diarization, speaker recognition, and language identification as separate governed route components.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-whole-part-hierarchies]] - Stanford CS25, "Whole-Part Hierarchies in a Neural Network" ([YouTube](https://www.youtube.com/watch?v=CYaju6aCMoQ)).
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
