---
type: pattern-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - "[[../../02-lectures/stanford/cs324-large-language-models]]"
  - "[[../../02-books/nlp-with-transformers/transformer-applications-production]]"
  - "[[../../02-books/nlp-with-transformers/chapters/7-question-answering]]"
  - "[[../../02-books/nlp-with-transformers/chapters/8-making-transformers-efficient-production]]"
  - "[[../../02-books/speech-language-processing/rag-dialogue-speech-ie]]"
  - "[[../../02-books/speech-language-processing/chapters/15-chatbots-dialogue-systems]]"
  - "[[../../02-books/speech-language-processing/chapters/16-asr-and-tts]]"
  - "[[../../02-books/speech-language-processing/chapters/20-information-extraction-relations-events-time]]"
  - "[[../../02-books/speech-language-processing/chapters/23-coreference-resolution-entity-linking]]"
  - "[[../../01-sources/official-open/speech-dialogue-ie-runtime-governance]]"
  - "[[../../02-books/deep-learning-book/generalization-optimization-sequence-systems]]"
  - "[[../../02-lectures/stanford/cs224n-public-llm-systems-notes]]"
  - "[[../../02-lectures/stanford/cs224n-nlp-llm-systems-source-map]]"
  - "[[../../02-lectures/stanford/cs224n-rag-agents-reasoning]]"
  - "[[../agent-systems/agent-route-architecture-canon]]"
  - "[[../evaluation/eval-design-canon]]"
  - "[[../retrieval/reranking-search-kg-patterns]]"
  - "[[../security/genai-security-canon]]"
related:
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# NLP And LLM Systems Canon

## Scope

This canon note converts CS224N public language-system coverage into Agent Studio architecture decisions. It uses the public CS224N course page, public notes, public slides, and the official public playlist pointer, without claiming gated 2026 video access.

## Canon Decision

Agent Studio language routes need explicit records for representation, tokenization, context assembly, retrieval, model family, adaptation method, decoding behavior, tool use, evaluation, and social-risk coverage.

The practical rule: a prompt/model choice is not enough metadata for a production route.

Natural Language Processing with Transformers adds the implementation-level rule: the route's task family must be explicit. Classification, extraction, QA, summarization, translation, text generation, code generation, and multimodal/document routes have different preprocessing, postprocessing, scoring, latency, and failure modes.

Natural Language Processing with Transformers Chapter 8 sharpens the serving rule: transformer route optimization is a release-managed serving change. Distillation, quantization, ONNX/runtime export, pruning, and execution-provider changes need deployment benchmarks, teacher/student lineage where applicable, precision/runtime profiles, semantic-equivalence checks, failure-slice review, and rollback targets.

CS324 adds the lifecycle rule: language routes need data provenance, contamination checks, tokenizer economics, model-objective identity, selective-computation traces, adaptation proposals, and rights constraints. A route cannot treat model behavior, retrieved knowledge, fine-tuned behavior, and legal source permission as the same kind of evidence.

Speech and Language Processing adds the interaction rule: RAG, dialogue, speech, IE, coreference, and entity linking are separate state/evidence layers. The official speech/dialogue/IE runtime cross-check tightens this into a production rule: turn detection, audio configuration, transcript confidence, SSML/voice support, entity offsets, NIL/entity-link candidates, and coreference model/version all need records before dialogue or extraction output becomes memory, retrieval evidence, graph fact, or publishable content.

Speech and Language Processing Chapter 15 sharpens the dialogue side of that rule. A conversation is a sequence of typed actions, grounding moves, repairs, side sequences, and initiative shifts. Agent Studio should version task frames, domain/intent inference, slot state, correction records, confirmation policy, dialogue retrieval turns, and dialogue quality/safety evals before a conversational route can mutate memory, execute tools, publish, or promote source canon.

Speech and Language Processing Chapter 16 sharpens the speech side of that rule. ASR/TTS routes need workload slices, audio frontend records, decoding/finalization policy, CTC/RNN-T alignment evidence, LM rescoring records, WER plus task-specific error analysis, TTS text-normalization policy, vocoder settings, listening-test evidence, wake-word privacy boundaries, diarization, speaker-identity policy, and spoken-language routing before transcript or generated audio can drive memory, tools, graph facts, or publishing.

Speech and Language Processing Chapter 20 sharpens the extraction side of that rule. Relation, event, temporal, and template output must be treated as candidates with method, schema, evidence span, confidence, temporal anchor, and review status. Bootstrapping, distant supervision, and Open IE improve recall but need drift/noise/canonicalization checks before graph writes or memory promotion.

Speech and Language Processing Chapter 23 sharpens the entity-memory side of that rule. Mention detection, referentiality, coreference clustering, and entity linking are separate decisions. Agent Studio should preserve mention candidates, referentiality decisions, merge/no-merge scores, discourse-entity chains, entity candidate sets, NIL decisions, ontology versions, canonicalization decisions, and bias/hard-reasoning slices before pronoun, alias, or organization resolution can affect graph memory.

Speech/dialogue/IE promotion needs an explicit release gate. A realtime transcript, dialogue state update, or extracted graph fact can affect memory, retrieval, publishing, and external tools only after the route proves provider/API version, credential boundary, audio configuration, turn/interruption policy, transcript-finalization policy, ASR/TTS quality slices, realtime tool/MCP exposure, dialogue-state policy, extractor version, offset encoding, entity/coreference candidate policy, graph-write review policy, privacy/retention posture, bias slice checks, fallback mode, and rollback target.

The CS224N RAG/agents/reasoning slice adds the serving-policy rule: agent behavior depends on retrieval evidence, tool action, environment state, reasoning/decoding policy, verifier choice, and test-time compute budget. These are release metadata, not hidden prompt details.

Natural Language Processing with Transformers Chapter 7 sharpens the QA/RAG implementation boundary: document stores, metadata filters, top-K retrieval, passage windows, source offsets, no-answer policy, retriever recall, reader EM/F1, whole-pipeline eval, domain adaptation, and generative RAG each need independent records. A source-backed answer route cannot be certified by final-answer quality alone because retrieval, reader span selection, score normalization, and unsupported synthesis can fail separately.

## Route Design Ladder

| Decision | Default posture | Escalate when |
|---|---|---|
| Prompt/context change | First option for controllable behavior or formatting failures | The failure is stable across prompt variants and has enough eval coverage. |
| Retrieval/reranking/graph change | First option for missing or stale knowledge | The system needs behavior change rather than better evidence. |
| Tool/workflow change | Use when external state, deterministic computation, or source inspection is needed | Tool calls need side effects, credentials, or human approval. |
| PEFT/fine-tune | Use only with owned/approved data and strong eval gates | Prompt/RAG/tool changes cannot fix the target behavior. |
| Preference tuning | Use for style, ranking, and reviewer-alignment behavior | Preference pairs are representative, rights-cleared, and contrastive. |
| Distillation/self-hosting | Use for latency/cost/privacy constraints | Serving profile and quality regression budgets justify the operational cost. |

## Required Records

| Object | Why it matters |
|---|---|
| `tokenizer_profile` | Tokenization changes cost, context length, multilingual behavior, rare-word handling, and glitch-token risk. |
| `context_assembly_trace` | Attention-based models are sensitive to context order, truncation, source labels, and prompt boundaries. |
| `long_context_memory_record` | Long inputs need explicit source-span, compression, truncation, and memory policies; long context is not reliable memory by itself. |
| `adaptation_candidate` | Route changes need a ranked decision ladder before training or PEFT is attempted. |
| `preference_pair` | Post-training and preference learning need chosen/rejected artifacts with provenance and rubric. |
| `reasoning_trace` | Reasoning routes need decoding settings, loop detection, verifier calls, and test-time compute budgets. |
| `verification_strategy_record` | Verifier, judge, ORM, or PRM dependency with calibration, route scope, and failure caveats. |
| `test_time_compute_policy` | Sample count, revision count, verifier-call budget, latency budget, and cost ceiling for reasoning routes. |
| `benchmark_context` | External benchmark results are context, not production release proof. |
| `language_coverage_slice` | Multilingual public content needs language/dialect coverage, token cost, evaluator coverage, and known risks. |
| `task_pipeline_record` | NLP route task family, input/output schema, preprocessing, postprocessing, model head or route class, scorer, and deployment surface. |
| `tokenization_eval_record` | Corpus-specific tokenizer evidence: vocab, token inflation, fragmentation/OOV risk, and downstream quality impact. |
| `serving_profile_record` | Model/runtime/hardware/thread/execution-provider profile used for route benchmarks and deployment. |
| `deployment_benchmark_record` | Quality, latency, model-size, memory, warmup, hardware, runtime, and workload-slice evidence for serving changes. |
| `distillation_run_record` | Teacher/student lineage, temperature, loss weighting, hyperparameter search, and behavior-divergence evidence. |
| `quantization_profile_record` | Precision, layer scope, calibration data, backend, unsupported operators, and quality/latency/memory deltas. |
| `runtime_export_record` | ONNX or runtime-export artifact, opset, dynamic axes, execution provider, fallback, and equivalence checks. |
| `pruning_profile_record` | Sparsity method, schedule, mask policy, sparse artifact format, hardware support, and benchmark deltas. |
| `compression_record` | Distillation, quantization, pruning, or runtime-export decision with lineage, quality/latency/memory deltas, and rollback trigger. |
| `few_label_strategy_record` | Zero-shot, few-shot, augmentation, embedding lookup, and domain-adaptation choices with label wording, validation, and leakage caveats. |
| `pretraining_run_record` | Objective, corpus refs, tokenizer refs, model config, packed sequence policy, distributed setup, logs, and eval plan for any from-scratch or domain pretraining work. |
| `dataset_documentation_record` | Included/excluded data, authorship class, coverage, filters, contamination risk, and documentation owner. |
| `training_contamination_check` | Possible overlap between eval/source material and model training, retrieval index, prompt examples, or generated training data. |
| `model_objective_record` | Decoder-only, encoder-only, encoder-decoder, embedding, reranker, classifier, or transformation objective and route fit. |
| `selective_computation_trace` | Experts, retrieved data, graph communities, or tools selected/rejected for a run, with selection policy and capacity used. |
| `dialogue_state_record` | Current task frame, filled slots, grounding state, clarification status, and user-goal hypothesis for conversational routes. |
| `dialogue_domain_intent_record` | Domain and intent inferred for a turn or subdialogue. |
| `task_frame_record` | Versioned task frame with required slots and action dependency rules. |
| `dialogue_state_delta` | State change produced by a turn, correction, confirmation, or subdialogue. |
| `dialogue_correction_record` | User correction target, replacement value, trigger evidence, confidence, and applied state delta. |
| `confirmation_policy_record` | Explicit/implicit/reject/no-confirm thresholds by confidence and action risk. |
| `dialogue_retrieval_turn` | Search/query action generated inside a conversation with returned evidence and support refs. |
| `dialogue_quality_safety_eval` | Turn or conversation-level quality, safety, coherence, privacy, and user-burden scores. |
| `speech_io_trace` | ASR/TTS provider, channel, sampling, endpointing, transcript alignment, and audio confidence before speech drives memory or actions. |
| `speech_corpus_slice_record` | Speech workload class, channel, speaker/accent/dialect/noise/domain/language slice before comparing ASR/TTS results. |
| `audio_frontend_record` | Sample rate, quantization/compression, channels, window/stride, feature representation, resampling, and noise profile. |
| `asr_decoder_policy_record` | Model family, output unit, streaming mode, beam/n-best, blank/EOS, punctuation, and finalization policy. |
| `ctc_alignment_record` | Blank-aware CTC/RNN-T alignment evidence for transcript deltas and segments. |
| `asr_lm_rescore_record` | LM rescoring, interpolation weight, length policy, domain vocabulary, and selected hypothesis. |
| `asr_significance_test_record` | Paired WER comparison method and decision before accepting speech quality regressions or gains. |
| `tts_text_normalization_record` | Verbalization policy for numbers, dates, abbreviations, currency, URLs, and domain terms. |
| `vocoder_config_record` | Waveform generation model and latency/quality profile for TTS output. |
| `wake_word_policy_record` | Edge/privacy wake-word contract and false accept/reject targets. |
| `speaker_diarization_record` | Who-spoke-when segmentation before multiparty transcript memory or attribution. |
| `relation_candidate_record` | Relation label or Open IE phrase with argument refs, source evidence, method, confidence, and review status before graph promotion. |
| `extraction_pattern_record` | Versioned pattern/rule evidence for high-precision extraction routes. |
| `bootstrapping_iteration_record` | Seed-to-pattern-to-tuple expansion with thresholds, accepted/rejected candidates, and drift audit. |
| `distant_supervision_bag_record` | Noisy database-derived training bag with entity-pair sentences and noise assumptions. |
| `openie_triple_record` | Open relation phrase triple with normalization and canonicalization status. |
| `relation_eval_sample_record` | Sampled precision and precision-at-yield evidence for large extraction routes. |
| `event_mention_record` | Event/state mention with tense, aspect, modality, factuality, and source evidence. |
| `temporal_link_record` | Event-time, event-event, time-time, document-time, aspectual, or factuality link. |
| `template_schema_record` | Versioned event/script template with slot policy. |
| `template_slot_fill_record` | Extracted or inferred slot value with evidence and confidence. |
| `mention_detection_candidate_record` | High-recall span proposal before filtering or acceptance as a source mention. |
| `referentiality_decision_record` | Accepted, rejected, generic, expletive, appositive, predicate, or uncertain span status. |
| `coreference_merge_decision_record` | Scored merge/no-merge decision with rejected alternatives and rollback/review status. |
| `coreference_chain_record` | Mentions clustered into discourse entities with source evidence, confidence, and bias-review status. |
| `entity_candidate_record` | Candidate ontology or KB targets with prior, coherence, embedding, or search scores. |
| `entity_link_record` | Mention or coreference chain linked to an ontology/KB target with candidate set and provenance. |
| `nil_entity_record` | Explicit unlinkable/new-entity decision for mentions or chains with no safe KB target. |
| `entity_canonicalization_record` | Alias, redirect, merge, ontology-version, and de-duplication decision. |
| `coreference_bias_eval_slice` | Gender, name, language, occupation, and hard-reasoning checks for coreference/linking routes. |
| `qa_corpus_document_record` | QA source document or passage with source ledger refs, metadata filters, and authorization/freshness boundaries. |
| `qa_label_record` | Question, answer span, no-answer label, offset, split, and annotation provenance. |
| `qa_passage_window_record` | Sliding-window chunk with tokenizer/model limit, stride, source offsets, overlap, and truncation flags. |
| `qa_reader_span_record` | Reader prediction with span offsets, no-answer score, and score-normalization policy. |
| `qa_retriever_eval_record` | Recall@K, MAP/MRR where useful, filters, corpus snapshot, and latency for the retriever. |
| `qa_reader_eval_record` | EM/F1 and no-answer metrics against gold contexts and retrieved contexts. |
| `qa_pipeline_eval_record` | End-to-end retriever-reader/generator metrics with failure attribution. |
| `qa_domain_adaptation_record` | Domain QA conversion, split policy, adaptation run, overfitting checks, and before/after metrics. |
| `generative_rag_answer_record` | Generated answer with retrieved docs, accepted support, generation settings, citation map, and unsupported-claim flags. |

## Release Gates

A language route cannot be promoted unless:

- source/retrieval dependencies are versioned;
- tokenizer and context-window assumptions are recorded;
- source data documentation, rights policy, and contamination checks are recorded when a route relies on source-backed behavior or model adaptation;
- long-context compression, truncation, and explicit memory behavior are recorded for source-heavy routes;
- decoding settings and reasoning budgets are fixed;
- task-family-specific preprocessing, postprocessing, and metric caveats are recorded;
- route-specific evals beat baseline within regression budgets;
- tool and RAG traces are inspectable for agentic routes;
- reasoning/test-time compute policy and verifier dependency are recorded for multi-sample, revision, or self-consistency routes;
- adaptation/fine-tuning decisions have data provenance and rollback;
- transformer task-pipeline, tokenizer/context assembly, QA/RAG split, passage windows, no-answer policy, retriever/reader/pipeline evals, generated-text metric caveats, serving profile, deployment benchmark, distillation/quantization/runtime-export/pruning evidence, few-label strategy, pretraining plan, rights/privacy, fallback, and rollback are bound in a `transformer_application_route_release_gate` before transformer application changes affect production;
- multilingual or public-facing routes include language and social-risk slices.

## Agent Studio Implications

- Separate model capability, route behavior, and product workflow behavior in the ledger.
- Treat test-time compute, speculative decoding, and long-context changes as serving-profile changes.
- Keep benchmark numbers out of release gates unless they are tied to a route-specific eval dataset.
- Treat tokenizer changes, zero-shot label wording, and few-label augmentation as route behavior changes with eval evidence.
- Require preference-pair provenance before using user/editor feedback for tuning.
- Make tokenization and multilingual cost visible in capacity estimates for social content.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.

- [[../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
- [[../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "How I Learned to Stop Worrying and Love the Transformer" ([YouTube](https://www.youtube.com/watch?v=1GbDTTK3aR4)).
- [[../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
