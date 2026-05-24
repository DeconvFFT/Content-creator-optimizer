---
type: official-source-cross-check
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-19
cross_checks:
  - source_title: "Python NLP Cookbook (Antic, Chakravarty)"
    scope: "Concrete NLP adapter recipes, pipeline components, tokenization"
anchor_note: "02-books/python-nlp-cookbook/source-ingestion-nlp-recipes.md"
sources:
  - https://spacy.io/usage/processing-pipelines
  - https://huggingface.co/docs/tokenizers/index
  - https://spacy.io/api/annotation#ner
  - https://huggingface.co/docs/transformers/main/en/task_summary#named-entity-recognition
  - https://arxiv.org/abs/2107.07511
related:
  - "[[../../02-books/python-nlp-cookbook/source-ingestion-nlp-recipes]]"
  - "[[../../02-books/nlp-with-transformers/transformer-applications-production]]"
  - "[[../../03-patterns/llm-systems/nlp-llm-systems-canon]]"
  - "[[../../01-sources/official-open/document-layout-ocr-ingestion-runtime]]"
---

# NLP Adapter Recipes - Official Cross-Check

## Scope

This cross-check deepens the existing Python NLP Cookbook anchor note's coverage of concrete NLP adapter patterns, pipeline architectures, and tokenization recipes. The anchor covers tokenization, sentence splitting, POS tagging, lemmatization, embeddings, and RAG conceptually. This cross-check adds specific primary-source depth from the spaCy 3.x pipeline architecture, HuggingFace tokenizers library, and modern NER approaches that materially sharpen the adapter contracts the anchor defines.

## Cross-Check Result

The anchor note's design rules (adapter profiles, boundary records, normalization policies, embedding compatibility) are strongly reinforced by the official sources. The cross-check adds three specific material deepening points: (1) spaCy 3.x's config-driven pipeline architecture with trainable components and custom extension attributes provides a concrete implementation model for the anchor's `nlp_adapter_profile`, (2) HuggingFace tokenizers' four-stage pipeline (normalization, pre-tokenization, model, post-processing) provides a concrete decomposition of the tokenization adapter contract, and (3) modern NER has moved beyond sequence-labeling to span-based and prompt-based approaches that the 2024 cookbook partially covers but needs explicit architectural framing.

## Confirmation Matrix

| NLP Cookbook anchor theme | Official/open-source confirmation | Agent Studio design implication |
|---|---|---|
| Text boundaries are source-ledger decisions | spaCy 3.x processing pipelines tokenize text into a Doc object, then pass it through a configurable sequence of components (tagger, parser, NER, lemmatizer, textcat, custom). The pipeline is declared in config.cfg, making the component order and model versions explicit and reproducible. The tokenizer is special: it runs first and is not a pipeline component but part of the nlp object itself. | The anchor's `nlp_adapter_profile` should include the spaCy pipeline config (component names, model versions, order) as a reproducible contract. The tokenizer/sentence-splitter is the first boundary decision and should be recorded separately from downstream pipeline components. |
| Normalization needs provenance | HuggingFace tokenizers implements a four-stage pipeline: (1) Normalizer (lowercase, strip, NFD/NFKC Unicode normalization), (2) Pre-tokenizer (split on whitespace/punctuation/Moses), (3) Model (BPE, WordPiece, Unigram, SentencePiece), (4) Post-processor (add [CLS]/[SEP], pair sequences, trim). Each stage is independently configurable and serializable. This is the concrete decomposition the anchor's `normalization_policy_record` needs. | The anchor's normalization policy should decompose into four stages: (1) Unicode/text normalization, (2) pre-tokenization/splitting, (3) subword tokenization model and merge rules, (4) post-processing (special tokens, pairing, truncation). Each stage should be versioned and its impact on retrieval and embedding recorded. |
| Grammar and extraction signals | spaCy 3.x NER (EntityRecognizer) is a transition-based parser that assigns IOB labels and entity types. It writes to Doc.ents, Token.ent_iob, and Token.ent_type. The parser model version, training data, and supported entity types are all part of the pipeline config. Modern alternatives include span-based NER (predicting start/end spans directly) and few-shot/prompt-based NER using LLMs. | The anchor's `grammar_extraction_candidate` should record the NER approach: (1) transition-based (spaCy), (2) span-based (transformer token classification), (3) prompt-based (LLM extraction). Each has different confidence characteristics, coverage, and failure modes. Record approach, model version, entity types, and confidence calibration. |
| Embeddings and RAG recipes | HuggingFace tokenizers are the same tokenizers used in Transformers. The tokenizer determines the embedding input: different tokenizers produce different subword segmentations, which change the embedding input hash. BPE, WordPiece, Unigram, and SentencePiece have different handling of rare words, multilingual text, and code. | The anchor's `embedding_profile_compatibility` must include tokenizer type (BPE | WordPiece | Unigram | SentencePiece), vocabulary size, merge rules version, special token handling, and whether the tokenizer matches the embedding model's training tokenizer. Mismatched tokenizer/embedding pairs produce degraded retrieval. |
| Runtime and recipe reproducibility | spaCy 3.x uses config.cfg for full pipeline specification, including model paths, hyperparameters, and component settings. HuggingFace tokenizers serialize to JSON with all normalizer, pre-tokenizer, model, and post-processor settings. Both support version-locked reproducibility. | The anchor's `recipe_runtime_profile` should pin: (1) spaCy model version and config.cfg hash, (2) HuggingFace tokenizer version and serialized JSON hash, (3) Python/package version lock, (4) input/output schema. This matches the anchor's existing design but adds concrete pinning points. |

## Canon Decisions

- The Python NLP Cookbook anchor note remains canon_ready. Its design rules are confirmed and sharpened.
- Expand `nlp_adapter_profile` to include: pipeline config reference (spaCy config.cfg or equivalent), component list with model versions, tokenizer specification, and trainable component flag.
- Expand `normalization_policy_record` to decompose into four stages: (1) Unicode/text normalization, (2) pre-tokenization/splitting, (3) subword tokenization model, (4) post-processing/special tokens. Each stage gets a version and impact record.
- Expand `grammar_extraction_candidate` to include NER approach type (transition-based | span-based | prompt-based), with different confidence and coverage characteristics for each.
- Expand `embedding_profile_compatibility` to include tokenizer type, vocabulary size, merge rules, special token handling, and tokenizer-embedding model alignment check.
- Expand `recipe_runtime_profile` to pin spaCy config hash, HuggingFace tokenizer JSON hash, package versions, and input/output schemas.

## New Agent Studio Design Rules

1. **Pipeline config is a first-class contract.** The spaCy config.cfg pattern means the full pipeline specification (components, models, order, settings) is a versioned artifact. Every ingestion adapter should reference its pipeline config.
2. **Tokenization is a four-stage pipeline.** HuggingFace's decomposition (normalize, pre-tokenize, model, post-process) is the right granularity for recording how text turns into tokens. Each stage changes retrieval and embedding behavior.
3. **NER approach determines confidence semantics.** Transition-based, span-based, and prompt-based NER produce different kinds of confidence scores and different failure modes. Record the approach, not just the model name.
4. **Tokenizer-embedding alignment is a compatibility gate.** A tokenizer mismatch between ingestion and query time silently degrades retrieval. Check and record tokenizer type and version alignment in the embedding profile.

## Remaining Refinement

- The anchor does not yet cover few-shot or prompt-based NER as an extraction approach. When the vault's LLM extraction coverage deepens, add prompt-based NER as a third extraction family with its own confidence and coverage characteristics.
- spaCy's new agentic NLP development tool (currently in beta) may affect the pipeline architecture patterns. Monitor for official release.
