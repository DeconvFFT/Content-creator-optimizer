---
type: book-synthesis-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source:
  local_path: /Users/saumyamehta/DS interview prep/books/NLPbook.pdf
  title: "Speech and Language Processing: An Introduction to Natural Language Processing, Computational Linguistics, and Speech Recognition with Language Models"
  authors: "Daniel Jurafsky and James H. Martin"
  edition: "Third Edition draft, January 12, 2025"
coverage:
  - "Chapter 14: Question Answering, Information Retrieval, and RAG"
  - "Chapter 15: Chatbots and Dialogue Systems"
  - "Chapter 16: Automatic Speech Recognition and Text-to-Speech"
  - "Chapter 20: Information Extraction: Relations, Events, and Time"
  - "Chapter 23: Coreference Resolution and Entity Linking"
related:
  - "[[./chapters/14-question-answering-ir-rag]]"
  - "[[./chapters/15-chatbots-dialogue-systems]]"
  - "[[./chapters/16-asr-and-tts]]"
  - "[[./chapters/20-information-extraction-relations-events-time]]"
  - "[[./chapters/23-coreference-resolution-entity-linking]]"
  - "[[../../01-sources/official-open/speech-dialogue-ie-runtime-governance]]"
  - "[[../../03-patterns/retrieval/reranking-search-kg-patterns]]"
  - "[[../../03-patterns/llm-systems/nlp-llm-systems-canon]]"
  - "[[../../03-patterns/inference/realtime-and-inference-patterns]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Speech And Language Processing: RAG, Dialogue, Speech, And IE

## Reading Scope

This note is a direct-read synthesis of the local Jurafsky and Martin draft sections that affect Agent Studio architecture: retrieval-based QA/RAG, dialogue systems, ASR/TTS, information extraction, time/event templates, coreference, and entity linking.

It is not a replacement for the book. It stores only original system-design synthesis and Agent Studio implications.

It is promoted to `canon_ready` after cross-check against official OpenAI Realtime, Google Cloud Speech-to-Text/Text-to-Speech/Natural Language, spaCy EntityLinker, and Stanford CoreNLP docs in [[../../01-sources/official-open/speech-dialogue-ie-runtime-governance]].

The Chapter 14 retrieval/QA/RAG pass is now split into [[./chapters/14-question-answering-ir-rag]] so retrieval collection releases, sparse/dense retrieval profiles, RAG reader prompts, ANN recall checks, and QA eval surfaces can be tracked without overloading this broader synthesis note.

The Chapter 15 dialogue pass is now split into [[./chapters/15-chatbots-dialogue-systems]] so turn-taking, dialogue acts, grounding, frame/slot state, correction detection, confirmation policy, dialogue retrieval, quality/safety evals, and Wizard-of-Oz design evidence can be tracked at chapter level.

The Chapter 16 speech pass is now split into [[./chapters/16-asr-and-tts]] so ASR task slices, audio frontend contracts, CTC/RNN-T streaming policy, WER/significance evidence, TTS normalization, vocoding, listening tests, wake-word privacy, diarization, speaker recognition, and language identification can be tracked at chapter level.

The Chapter 20 information-extraction pass is now split into [[./chapters/20-information-extraction-relations-events-time]] so relation candidates, extraction patterns, bootstrapping/distant-supervision provenance, Open IE triples, relation eval samples, event mentions, temporal links, temporal normalization, and template filling can be tracked at chapter level.

The Chapter 23 coreference/entity-linking pass is now split into [[./chapters/23-coreference-resolution-entity-linking]] so mention candidates, referentiality decisions, coreference merge decisions, discourse-entity chains, entity candidates, NIL decisions, entity canonicalization, and bias eval slices can be tracked at chapter level.

## Core Design Takeaways

RAG is a two-system contract, not a single generation trick. The retriever owns candidate evidence and ranking behavior; the reader/generator owns answer synthesis conditioned on accepted evidence. Hallucination, stale knowledge, proprietary knowledge, and uncalibrated confidence are separate failure modes, so Agent Studio should not let an answer route report only the final text.

Dialogue systems add a second contract: the system must track turn structure, speech/dialogue acts, grounding, subdialogues, initiative, and implied user intent. For Agent Studio, a chat run is not just messages. It is an evolving state machine with user goals, frame slots, clarification branches, accepted assumptions, interruptions, and safety/privacy boundaries.

Speech routes add a third contract: realtime voice quality depends on channel, sampling rate, speaker/accent coverage, noise, endpointing, ASR error rate, TTS quality, and human listening tests. A text route promoted to voice without audio-specific traces is not production-ready.

Information extraction and coreference provide the memory/graph bridge. Named entities, relations, events, temporal expressions, templates, coreference chains, and entity links are the units that let a source-backed agent remember who did what, when, to whom, and where the claim came from.

## RAG And QA Implications

Agent Studio should treat lexical retrieval, dense retrieval, reranking, and generation as distinct stages:

- lexical retrieval and BM25-style scoring remain useful for exact terms, rare entities, filenames, source titles, and quoted phrases;
- dense retrieval is useful for semantic match but requires approximate nearest-neighbor infrastructure and evals against missed evidence;
- cross-encoder or full-interaction reranking is more accurate but belongs after broad first-stage retrieval;
- ColBERT-style late interaction shows why token-level relevance can outperform a single pooled embedding when exact alignment matters;
- multi-hop retrieval should be an explicit route mode when the first evidence set is needed to construct the second query.

The route ledger needs `qa_pipeline_record`, `retriever_eval_result`, and `answer_support_record` objects so an answer can be audited by retriever recall, reranker precision, context selection, reader/generator prompt, and final claim support.

QA evals should not collapse into one number. Multiple-choice exact match, free-text token overlap, MRR for ranked answers, MAP/precision-recall for retrieval, and groundedness/citation validity measure different surfaces.

## Dialogue State Implications

A production dialogue route needs to store more than message history:

- `dialogue_turn_record`: speaker, timestamp, channel, source transcript, normalized text, interruption status, and turn boundary evidence;
- `dialogue_act_record`: question, answer, request, confirmation, denial, plan, acknowledgement, correction, or safety refusal;
- `dialogue_state_record`: current task frame, filled slots, candidate values, user goal hypothesis, pending clarification, and grounding status;
- `frame_slot_record`: slot name, value candidates, provenance, confidence, correction history, and downstream action dependency;
- `subdialogue_record`: clarification, correction, repair, side question, or plan change with parent-turn linkage;
- `initiative_state_record`: system-led, user-led, mixed initiative, or handoff state.

This matters for Agent Studio because content creation conversations often contain partial briefs, later corrections, side questions, and implicit constraints. The system should preserve the difference between what the user said, what the agent inferred, what was confirmed, and what still needs grounding.

Safety and privacy are route requirements for dialogue, not afterthoughts. If a chatbot surface invites personal disclosure, the datastore should record consent posture, retention policy, redaction, human-review rules, and route-specific unsafe-response filters.

## Speech And Realtime Implications

Speech routes need explicit audio contracts:

- `speech_io_trace`: input/output channel, sample rate, codec/format, ASR provider, TTS provider, endpointing policy, and transcript alignment;
- `asr_eval_result`: WER/CER, domain, channel, speaker/accent slice, noise condition, and transcript-review status;
- `tts_eval_result`: MOS or pairwise preference result, voice/model, text-normalization policy, latency, and human-listener setup;
- `endpointing_event`: start, pause, barge-in, interruption, silence timeout, and final-turn decision;
- `voice_privacy_record`: capture scope, transmission boundary, retention rule, and redaction policy.

CTC-style streaming friendliness and encoder-decoder accuracy trade off differently. Agent Studio should separate streaming partial transcripts from final transcript evidence, and it should preserve transcript confidence before a transcript is used for memory, task execution, or source-grounded claims.

## IE, Time, And Template Implications

Information extraction should feed a typed graph, but the graph must preserve extraction method, source span, confidence, and review status.

Minimum records:

- `named_entity_mention`: text hash, type, source chunk, offsets, extractor, confidence, and review status;
- `relation_extraction_record`: argument refs, relation type or open relation phrase, extraction method, confidence, and source evidence;
- `event_record`: trigger, participants, roles, temporal anchors, source evidence, and merge status;
- `temporal_expression_record`: raw expression hash, normalized time, anchor event/time, uncertainty, and timezone assumptions;
- `template_fill_record`: template type, slot fillers, evidence spans, inferred fillers, and merge decisions.

Bootstrapping and distant supervision are useful but noisy. Any semi-supervised or Open IE graph population should have semantic-drift checks, confidence thresholds, sample-based precision review, and human correction loops before graph facts drive product behavior.

## Coreference And Entity Linking Implications

Coreference resolution is needed before a source-backed agent can safely summarize long documents, support claims, or build a knowledge graph. Mentions, discourse entities, coreference chains, and real-world entity links must remain separate:

- `mention_record`: mention span, mention type, source chunk, surface form, and nested-mention relation;
- `referentiality_decision_record`: accepted, rejected, generic, expletive, appositive, predicate, or uncertain span status;
- `coreference_merge_decision_record`: scored merge/no-merge decision with rejected alternatives;
- `coreference_chain_record`: discourse entity, mention refs, algorithm/version, confidence, and bias-risk notes;
- `entity_candidate_record`: candidate KB targets with prior, coherence, embedding, or search scores;
- `entity_link_record`: mention or chain ref, ontology/KB target, candidate set, NIL policy, prior/coherence scores, embedding route, and review status;
- `entity_canonicalization_record`: alias, redirect, merge, ontology-version, and deduplication decision;
- `coreference_eval_record`: metric protocol such as MUC, B3, CEAF, BLANC, LEA, or task-specific named-entity-chain metric;
- `coreference_bias_eval_slice`: gender, dialect, language, name, occupation, or hard-reasoning slice where coreference/linking errors may change product behavior.

For Agent Studio, this prevents common failures: linking a pronoun to the wrong source/person, merging two companies, failing to connect aliases, or treating a generated summary as the source of a graph fact.

## Agent Studio Design Implications

- Split source-backed QA into retriever, reranker, reader/generator, and claim-verifier traces.
- Keep dialogue frames and grounded user commitments separate from raw chat history.
- Treat realtime speech as a governed provider route with ASR/TTS metrics, not a wrapper around text chat.
- Build the knowledge graph from reviewed mentions, relations, events, time expressions, templates, coreference chains, and entity links.
- Require extraction provenance and confidence before graph facts affect retrieval, planning, or publishing.
- Add bias and privacy review for dialogue, ASR, coreference, and entity linking surfaces.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../02-lectures/stanford/cs25-whole-part-hierarchies]] - Stanford CS25, "Whole-Part Hierarchies in a Neural Network" ([YouTube](https://www.youtube.com/watch?v=CYaju6aCMoQ)).
- [[../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
