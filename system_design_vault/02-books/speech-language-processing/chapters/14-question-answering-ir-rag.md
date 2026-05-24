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
  number: 14
  title: "Question Answering, Information Retrieval, and Retrieval-Augmented Generation"
extraction:
  method: pdftotext
  physical_pages: "297-316"
  temp_extract: "/private/tmp/slp_ch14_rag_qa_ir.txt"
stores_raw_source_text: false
related:
  - "[[../rag-dialogue-speech-ie]]"
  - "[[../../../03-patterns/retrieval/reranking-search-kg-patterns]]"
  - "[[../../../03-patterns/llm-systems/nlp-llm-systems-canon]]"
  - "[[../../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Chapter 14 - QA, IR, And RAG

## Reading Scope

This is a direct-read chapter synthesis from the local official/user-provided Speech and Language Processing PDF. It covers Chapter 14 only: question answering, information retrieval, sparse and dense retrieval, retrieval-augmented generation, QA datasets, and QA evaluation.

This note stores original system-design synthesis only. It does not store copied chapter text, formulas as a reference dump, exercises, figures, or long excerpts.

## Why This Chapter Matters

The chapter makes RAG a response to three concrete failures of plain LLM prompting: factual hallucination, poor calibration, and missing access to proprietary or fresh information. For Agent Studio, this means RAG is not an optional enhancement. It is the route pattern used whenever the answer must be grounded in a changing or private source collection.

The useful design split is:

- the retriever expresses the user's information need against a bounded collection;
- the index stores the searchable representation of the collection;
- the reader or generator turns accepted evidence into an answer;
- the evaluator checks retrieval quality, answer correctness, and rank behavior separately.

If a route only stores the final generated answer, it loses the evidence needed to debug all four stages.

## Retrieval Unit And Collection Boundaries

The chapter's IR framing starts with ad hoc retrieval: a query returns a ranked list from a defined document collection. The important Agent Studio implication is that "document" is a system choice, not a natural law. A document can be a web page, PDF, section, paragraph, chunk, lecture note, transcript window, source record, or claim record.

Agent Studio should therefore store a retrieval collection release before treating retrieval results as evidence:

- collection identity and rights boundary;
- document-unit policy;
- chunk/window policy;
- index build input snapshot;
- query-processing policy;
- ranking policy;
- freshness and rebuild policy.

Without those fields, a retrieval score is not comparable across route releases.

## Sparse Retrieval Controls

The sparse retrieval sections explain why raw token counts are insufficient: terms need frequency weighting, collection-level rarity weighting, document-length normalization, and an efficient inverted index. BM25 is the practical baseline because it keeps exact-term and rare-entity matching strong while avoiding naive raw-count behavior.

Agent Studio should preserve sparse retrieval as a first-class route lane, especially for:

- source names, filenames, API fields, model names, citations, section titles, and rare entities;
- debugging questions where exact terms matter more than semantic paraphrase;
- hybrid retrieval where dense vectors miss lexical constraints;
- legal/provenance/security routes where exact source references are release-blocking.

Stop-word and analyzer choices should be auditable. Removing common terms can improve efficiency, but it can also damage phrase queries or field-specific searches. Treat analyzer profiles as versioned index behavior, not as backend defaults.

## Dense Retrieval Controls

The dense retrieval sections distinguish cross-encoder scoring, bi-encoder retrieval, late-interaction retrieval, and approximate nearest-neighbor vector search.

The architecture rule:

- cross-encoders can score query-document relevance strongly but do not scale as a first-stage full-corpus search;
- bi-encoders scale because documents can be embedded in advance, but compress each query/document into a single vector and may miss token-level alignment;
- late-interaction retrieval keeps more token-level evidence but costs more storage and scoring work;
- ANN/vector database search is a serving approximation and needs recall measurement against exact or trusted baselines.

For Agent Studio, every dense index release should record the embedding model, query encoder, document encoder, chunk size, vector dimension, normalization, ANN algorithm/provider, recall benchmark, and index rebuild trigger.

## RAG Reader Contract

The chapter's RAG framing separates retrieval from reading/generation. The retrieved documents are not the answer; they are the evidence pack passed into a reader or generator. This matters because hallucination can still happen after retrieval if:

- the retriever misses the needed evidence;
- the context pack includes relevant and irrelevant passages without a reliable ordering;
- the prompt does not require evidence-grounded answering;
- the generator invents unsupported details;
- citations point to retrieved text that does not actually support the claim.

Agent Studio should make the reader/generator prompt a governed artifact and should store answer-support records at claim level. A route should be able to show which retrieved items were accepted, which were ignored, which claims are unsupported, and whether the answer should abstain.

## Evaluation Implications

The chapter separates IR evaluation from QA evaluation. Retrieval needs precision, recall, precision-recall curves, average precision, and MAP-style ranking evidence. QA needs exact match for constrained answers, token-level F1 for free-text answers, and MRR when the system returns ranked answers or passages.

Agent Studio should not use one aggregate "RAG score". It should keep these surfaces separate:

| Layer | Required evidence |
|---|---|
| Collection/index | source snapshot, document-unit policy, index build, analyzer/embedding config |
| Retriever | Recall@K, Precision@K, MAP/MRR where appropriate, lexical/dense/hybrid lane results |
| Reader/generator | prompt version, packed evidence, answer format, abstention behavior |
| Claim support | accepted source refs, unsupported claim flags, citation validity |
| Release decision | latency/cost, freshness, privacy/rights, rollback index and route |

The chapter also shows why QA datasets vary by question source, answer format, and open-book versus closed-book setup. A test set used for closed-book model recall should not be reused as proof that a RAG route can retrieve and cite evidence from a private source collection.

## Datastore Additions

| Object | Purpose |
|---|---|
| `retrieval_collection_release` | Versioned searchable collection with rights, document-unit, chunking, index-input snapshot, and freshness policy. |
| `sparse_retrieval_profile` | BM25/tf-idf/analyzer behavior for exact-term retrieval and hybrid search. |
| `dense_retrieval_profile` | Embedding/encoder/vector-index behavior for dense first-stage retrieval. |
| `ann_recall_benchmark` | Approximate vector-search quality check against exact or trusted retrieval baselines. |
| `rag_reader_prompt_record` | Reader/generator prompt version, evidence-pack format, abstention policy, citation policy, and answer schema. |
| `qa_eval_surface_record` | Declares whether the eval is closed-book QA, open-book QA, retrieval ranking, generated answer quality, or claim support. |

## Agent Studio Design Implications

- Treat RAG as a multi-stage route with independently versioned collection, index, retriever, reader, and support-check artifacts.
- Keep sparse retrieval in production even when dense retrieval is available; exact names and rare source identifiers are too important for architecture evidence.
- Store dense retrieval approximation evidence; ANN index speed is not enough without recall checks.
- Require claim-level support records before source-backed answers become notes, graph facts, memory, or published content.
- Keep QA evals matched to the product surface: closed-book factual recall, open-book retrieval QA, ranked answer selection, and grounded generated answers are different tests.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-whole-part-hierarchies]] - Stanford CS25, "Whole-Part Hierarchies in a Neural Network" ([YouTube](https://www.youtube.com/watch?v=CYaju6aCMoQ)).
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
