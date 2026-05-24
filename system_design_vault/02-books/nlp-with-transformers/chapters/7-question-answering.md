---
type: book-chapter-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source:
  local_path: /Users/saumyamehta/DS interview prep/books/NLP with Transformer models.pdf
  title: "Natural Language Processing with Transformers"
  authors: "Lewis Tunstall, Leandro von Werra, Thomas Wolf"
  edition: "Revised Edition, 2022"
chapter:
  number: 7
  title: "Question Answering"
extraction:
  method: pdftotext
  physical_pages: "189-232"
  temp_extract: "/private/tmp/nlp_transformers_ch7_question_answering.txt"
stores_raw_source_text: false
related:
  - "[[../transformer-applications-production]]"
  - "[[../../../03-patterns/retrieval/reranking-search-kg-patterns]]"
  - "[[../../../03-patterns/llm-systems/nlp-llm-systems-canon]]"
  - "[[../../../03-patterns/evaluation/eval-design-canon]]"
  - "[[../../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Chapter 7 - Question Answering

## Reading Scope

This is a direct-read chapter synthesis from the local official/user-provided Natural Language Processing with Transformers PDF. It covers Chapter 7 only: extractive QA, review-based QA over SubjQA, answer-span modeling, impossible answers, long-context windowing, Haystack document stores, sparse and dense retrieval, retriever/reader/pipeline evaluation, domain adaptation, and generative RAG.

This note stores original Agent Studio synthesis only. It does not store copied chapter text, figures, code listings, formulas as a reference dump, or long excerpts.

## Why This Chapter Matters

Chapter 7 turns source-backed answering into an explicit production pipeline. A user only supplies a question; the system must select candidate evidence, run a reader or generator over that evidence, score the components separately, and preserve enough trace detail to debug whether the failure came from missing retrieval, bad windowing, a reader span error, or unsupported generation.

For Agent Studio, this is directly relevant to source-grounded drafts, lecture/book QA, claim verification, and content research. RAG should not be treated as one model call. It is a routed system with document stores, metadata filters, retrievers, readers/generators, answer support, evaluation, and release gates.

## QA Task Contract

The chapter uses review-based QA as the running example. The task shape is:

- a bounded corpus of documents or passages;
- user questions that may be informal, subjective, or partially mismatched with corpus wording;
- answer labels with text spans and source character offsets;
- unanswerable questions where the correct behavior is no answer;
- product/domain metadata used to restrict retrieval.

The Agent Studio contract should therefore store the question, corpus scope, document metadata filters, answerability policy, accepted evidence, rejected evidence, and answer-support mapping. A source-backed route that answers from the wrong product, book, chapter, lecture, or workspace namespace is a retrieval-policy failure, not a writing-style issue.

## Extractive Reader Semantics

Extractive QA frames the answer as a start-token and end-token prediction over the context. The answer is not a free-form claim; it is a span selected from source text, with offsets that should map back to the original document.

Important production details:

- the model receives question and context as a paired input;
- start and end logits are produced for each token;
- the selected span must be in the context, not accidentally in the question;
- the start index must precede the end index;
- impossible-answer handling maps high no-answer confidence to an empty answer;
- score semantics differ by implementation.

The chapter's score caveat is critical. Some reader pipelines normalize scores within each passage, which makes comparison across passages unsafe without calibration. Agent Studio should not choose between two retrieved passages by blindly comparing reader probabilities unless the route records the reader implementation and score-normalization policy.

## Long Context And Passage Windows

Long contexts cannot simply be truncated for QA because the answer may live near the end. The standard solution is a sliding window over the context with overlap controlled by maximum sequence length and stride.

Agent Studio implication: every source-backed QA trace should record:

- tokenizer/model context limit;
- window size and stride;
- source document and passage-window IDs;
- window-to-source offset mapping;
- whether the predicted span crossed or duplicated overlapping windows;
- truncation or dropped-window flags;
- final answer offsets in the original source.

Without offset and window metadata, the system cannot reliably cite a source, deduplicate answers, audit hallucination, or reproduce reader behavior after route changes.

## Retriever-Reader Architecture

The chapter's end-to-end system uses a retriever-reader architecture:

| Component | Responsibility | Agent Studio record |
|---|---|---|
| Document store | Stores documents plus metadata for filtering. | `qa_corpus_document_record` |
| Sparse retriever | Lexical search such as BM25, useful for exact wording and efficient filtering. | `sparse_retrieval_profile` or `qa_retriever_eval_record` |
| Dense retriever | Embedding search such as DPR, useful for semantic mismatch but not automatically better. | `dense_retrieval_profile` or `qa_retriever_eval_record` |
| Reader | Extracts answer spans from retrieved documents. | `qa_reader_span_record` |
| Pipeline | Combines retrieval, reading/generation, filters, top-K settings, and postprocessing. | `qa_pipeline_record` |

Metadata filtering is not optional. In the chapter's product-review example, the retriever must be restricted to the product being asked about. In Agent Studio, equivalent filters include workspace, source set, book, chapter, project, rights class, freshness class, privacy label, and user authorization.

## Evaluation Split

The chapter separates evaluation by component:

- Retriever: recall@K asks whether answer-bearing documents appear in the candidate set. MAP-style ranking metrics matter when relevant evidence must appear early.
- Reader: exact match and token F1 measure span extraction against labels, with EM stricter and F1 more forgiving.
- Whole pipeline: combined evaluation reveals degradation when the reader receives multiple retrieved documents rather than the gold context.

The design rule is to evaluate retrieval before blaming the reader or generator. A perfect reader cannot answer from evidence that was never retrieved, and a high-recall retriever can still overload the reader with noisy candidates.

## Domain Adaptation

The baseline reader is fine-tuned on a large QA dataset, then adapted to the domain-specific SubjQA training set. The chapter shows why this matters: review language and subjective questions differ from Wikipedia-style factual QA. Small domain datasets can improve performance, but they also introduce overfitting risk and should use careful validation.

Agent Studio should store `qa_domain_adaptation_record` with:

- base reader model and prior QA dataset;
- domain dataset and split policy;
- SQuAD-style conversion/version if used;
- answerable versus unanswerable label policy;
- windowing/tokenization settings;
- train/dev/test evidence;
- before/after reader metrics;
- overfitting checks or cross-validation plan;
- route rollback target.

Domain adaptation is a route behavior change, not a private notebook improvement.

## Generative RAG

The chapter introduces generative QA by replacing the reader with a generator over retrieved documents. RAG-Sequence uses one retrieved document for the answer sequence, while RAG-Token can draw from different documents while generating different tokens.

For Agent Studio, generative RAG should add synthesis only after search and extractive evidence handling are strong. A generator can produce better phrasing and combine evidence, but it also creates unsupported-claim risk. The trace must therefore keep retrieved evidence, accepted support, generation settings, citation mapping, and abstention behavior separate.

## QA Hierarchy For Agent Studio

The chapter's practical order is useful:

1. Provide high-quality search first.
2. Add extractive QA when users need direct answer spans.
3. Add domain adaptation when the reader fails on the target corpus.
4. Add generative QA only after retrieval and extractive support are strong enough to constrain synthesis.

Agent Studio should follow this hierarchy for book, lecture, and official-doc answers. Do not compensate for weak retrieval by making the generator more fluent.

## Agent Studio Design Implications

- Store QA as a pipeline with separate corpus, label, passage-window, retriever, reader/generator, answer-support, and evaluation records.
- Keep retrieval scores, reader scores, generator likelihoods, reranker scores, and citation-support scores in separate namespaces unless explicitly calibrated.
- Require metadata filters for source-backed QA routes so answers cannot cross workspace, product, book, chapter, rights, or freshness boundaries.
- Preserve character/token offsets from source document to passage window to reader span to final citation.
- Record no-answer policy and threshold so abstention is a first-class outcome.
- Evaluate retriever recall@K and ranking quality before tuning reader prompts or generator style.
- Evaluate whole-pipeline behavior because gold-context reader scores can overstate production performance.
- Treat domain adaptation and generative RAG as release-managed changes with before/after metrics and rollback.

## Datastore Objects Promoted By This Chapter

| Object | Role |
|---|---|
| `qa_corpus_document_record` | Source document or passage stored for QA, with metadata filters and source ledger refs. |
| `qa_label_record` | Question, answer spans, no-answer labels, offsets, split, and annotation provenance. |
| `qa_passage_window_record` | Sliding-window chunk with tokenizer, max length, stride, source offsets, and truncation flags. |
| `qa_reader_span_record` | Reader prediction with start/end logits or scores, span offsets, no-answer score, and score-normalization policy. |
| `qa_no_answer_policy_record` | Threshold and behavior contract for impossible or unsupported questions. |
| `qa_retriever_eval_record` | Retriever recall@K, MAP/MRR where useful, filters, corpus snapshot, and latency. |
| `qa_reader_eval_record` | EM/F1 and no-answer metrics against gold contexts and production-like retrieved contexts. |
| `qa_pipeline_eval_record` | End-to-end retriever-reader/generator metrics with top-K settings, source filters, and failure attribution. |
| `qa_domain_adaptation_record` | Fine-tuning/adaptation run, dataset conversion, splits, overfitting checks, and metric deltas. |
| `generative_rag_answer_record` | Generated answer with retrieved docs, accepted evidence, generation settings, citation/support mapping, and unsupported-claim flags. |
| `transformer_application_route_release_gate` | Gate binding QA/RAG component records, evals, source filters, answer support, no-answer policy, privacy/rights, fallback, and rollback. |

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "How I Learned to Stop Worrying and Love the Transformer" ([YouTube](https://www.youtube.com/watch?v=1GbDTTK3aR4)).
