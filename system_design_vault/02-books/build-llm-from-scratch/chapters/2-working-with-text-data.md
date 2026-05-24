---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Build a Large Language Model (From Scratch)"
authors: "Sebastian Raschka"
chapter: "2"
chapter_title: "Working with Text Data"
source_path: "/Users/saumyamehta/DS interview prep/books/Build a Large Language Model (From Scratch).pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 2 - Working With Text Data

## Reading Status

Direct source reading pass completed for chapter 2 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied code listings, copied figures, and long excerpts.

## Core Idea

The chapter makes the LLM input pipeline concrete: text must become tokens, token IDs, token embeddings, and positional embeddings before a decoder-only transformer can process it. The details are not incidental. Tokenization, special tokens, context windows, stride, batching, and position encoding shape what the model can learn and what an application can safely send at inference time.

Agent Studio implication: ingestion and retrieval cannot treat "text" as an opaque blob. Source chunks, prompts, tool outputs, conversation memory, and retrieved evidence need token-aware formatting, context-window budgeting, and boundary markers.

## Embeddings As Interface

Neural networks consume numeric tensors, not raw words. The chapter starts from embeddings as the bridge from discrete text to continuous vectors. For GPT-style training, token embeddings are learned as part of the model rather than borrowed from a static external embedding model.

Important distinction:

- token embeddings serve next-token generation;
- sentence or document embeddings serve retrieval and semantic search;
- these are related concepts but not interchangeable artifacts.

Agent Studio implication: the datastore should distinguish generation-tokenization metadata from retrieval-embedding metadata. A source chunk's vector embedding does not replace the tokenized context that will actually be sent to a model.

## Tokenization

The chapter walks from a simple regex tokenizer to a practical BPE tokenizer. The simple tokenizer is useful pedagogically because it exposes the pipeline: split text, build vocabulary, assign token IDs, and decode IDs back to text. It also exposes why naive tokenizers fail: unknown words, punctuation, whitespace sensitivity, capitalization, and source boundaries all matter.

BPE matters because GPT-style models can represent unknown words as subword pieces rather than falling back to a single unknown token. That makes the model more robust to names, rare terms, identifiers, typos, code-like strings, and domain vocabulary, but it also means token counts can grow unexpectedly for unusual text.

Agent Studio implication:

- token budgeting should measure actual provider tokenizer output, not word counts;
- rare entities, code identifiers, URLs, tables, OCR noise, and multilingual text may consume more context than expected;
- chunking strategy should be tokenizer-aware and should preserve semantic boundaries when possible;
- eval slices should include tokenization-hostile inputs such as unusual names, IDs, filenames, citations, and code symbols.

## Special Tokens And Boundaries

The chapter uses special tokens to handle unknown words and unrelated text boundaries, then notes that GPT-style tokenizers commonly rely on an end-of-text token rather than an unknown-token path. The systems lesson is that model input is not just content; it is structured content with boundary signals.

Agent Studio implication:

- source packs should preserve document, section, chunk, and tool-output boundaries;
- unrelated retrieved chunks should not be concatenated as if they were one continuous source;
- tool results, system instructions, user content, retrieved evidence, and model scratch outputs need separate channels or explicit delimiters;
- prompt templates should define boundary policy as part of the route contract.

## Sliding Windows And Training Pairs

The chapter shows how next-token training examples are produced from tokenized text by shifting input and target sequences. The stride controls overlap between windows. Small stride produces more overlapping examples but can increase redundancy and overfitting; larger stride reduces overlap and changes data coverage.

For Agent Studio, this maps directly to chunking and retrieval:

- chunk size controls how much local context travels together;
- overlap controls continuity across chunk boundaries;
- stride-like choices affect duplication, storage cost, retrieval recall, and prompt budget;
- context length is a hard input contract, not a UI suggestion.

Agent Studio implication: ingestion runs should record chunk length, chunk overlap, tokenizer, boundary rules, dropped text, and source checksum. Retrieval evals should test whether overlap is sufficient for answers whose evidence crosses section boundaries.

## Embedding And Position Encoding

Token embeddings alone do not encode order. GPT-style models add positional embeddings so the same token can be interpreted differently depending on its position in the sequence. The chapter contrasts absolute and relative position strategies and notes that GPT-style models use learned absolute positional embeddings.

Agent Studio implication:

- long-context routing needs more than "the model supports N tokens"; positional behavior and attention quality can degrade across long inputs;
- context packing order matters because models are position-sensitive;
- system instructions, developer policy, task request, retrieval evidence, examples, and tool outputs should have stable placement rules;
- evals should test relevant-position sensitivity, including answerable evidence near the beginning, middle, and end of packed context.

## Datastore Requirements

Agent Studio should store token-aware ingestion metadata:

- `tokenizer_profile`: provider/model tokenizer, version, special-token policy, encoding name, and measurement method.
- `chunking_policy`: max tokens, overlap tokens, stride, boundary preference, table/code handling, and truncation policy.
- `source_boundary`: document, page, section, heading, chunk, tool result, and retrieved-evidence delimiters.
- `context_pack`: ordered prompt segments, token counts, route template version, truncation decisions, and omitted evidence.
- `retrieval_chunk`: source id, chunk id, tokenizer, token span, char span, embedding model, boundary metadata, and checksum.
- `position_eval_slice`: tests for evidence position, long-context truncation, cross-boundary evidence, and prompt packing regressions.

## Failure Modes

- Estimating context with words or characters instead of tokenizer-specific token counts.
- Splitting chunks in the middle of code, tables, citations, or entity definitions.
- Concatenating unrelated documents without boundary markers.
- Losing source provenance when converting text into chunks and embeddings.
- Assuming vector similarity chunks are automatically good generation context.
- Overlapping chunks so aggressively that retrieval returns redundant context and hides missing coverage.
- Packing retrieved evidence after too much boilerplate and then blaming the model for weak grounding.
- Changing tokenizer/model/provider without rerunning token-budget and retrieval evals.

## Agent Studio Design Implications

- Make tokenizer-aware ingestion mandatory for source-ledger records.
- Store chunking and context-packing policies as versioned artifacts.
- Treat retrieval chunks, prompt segments, and model input context as distinct datastore objects.
- Add token-count and truncation telemetry to every run trace.
- Include context-boundary and position-sensitivity evals before promoting a retrieval or long-context route.
- Preserve document boundaries when converting local books, docs, lecture notes, and tool outputs into source packs.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "How I Learned to Stop Worrying and Love the Transformer" ([YouTube](https://www.youtube.com/watch?v=1GbDTTK3aR4)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
