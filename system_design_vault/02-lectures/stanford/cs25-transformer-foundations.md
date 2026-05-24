---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
source_title: "Stanford CS25 Transformers United"
lecture_title: "Transformer Foundations: Overview, Introduction, And Attention"
speaker: "CS25 instructors, Andrej Karpathy, Ashish Vaswani"
source_status: official_public_video_pointer
updated: 2026-05-18
stores_raw_source_text: false
stores_long_excerpts: false
sources:
  - https://web.stanford.edu/class/cs25/
  - https://web.stanford.edu/class/cs25/recordings/
  - https://arxiv.org/abs/1706.03762
  - https://web.stanford.edu/class/cs224n/readings/cs224n-self-attention-transformers-2023_draft.pdf
  - https://web.stanford.edu/class/cs224n/slides_w25/cs224n-2025-lecture08-transformers.pdf
related:
  - "[[../../03-patterns/transformer-systems/cs25-transformer-systems-canon]]"
  - "[[../../03-patterns/llm-systems/nlp-llm-systems-canon]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# CS25 - Transformer Foundations

## Reading Status

Canon-ready direct-read pass over the official CS25 V6 course page and recordings page for the public lecture pointers "Overview of Transformers," "Introduction to Transformers," and "Stop Worrying and Love the Transformer," rechecked on 2026-05-18. This note cross-checks those pointers against the original Transformer paper and official Stanford CS224N self-attention/Transformer materials. It does not claim transcript-level video ingestion, does not download video, and does not store slide text, transcript text, or long excerpts.

## Core Pattern

The Transformer made sequence modeling a parallelizable attention-centered computation. The key production move was not only architectural novelty; it was changing the shape of the compute graph. Recurrent models forced serial dependencies over tokens. Self-attention turns token interaction into large matrix operations over all token pairs, which maps better to accelerators and later becomes the basis for modern LLM pretraining, long-context serving, retrieval-aware context assembly, and multimodal token mixing.

For Agent Studio, this means model behavior should be understood through three separate layers:

- architecture: attention, MLP blocks, residual paths, normalization, positional information, and decoder/encoder shape;
- runtime: context length, prefill cost, KV-cache behavior, batching, memory pressure, and parallelism;
- product contract: source grounding, tool use, artifact editing, multimodal input, and eval surfaces.

## Self-Attention As Routing

Self-attention creates contextual token representations by letting each position weight other positions. Multi-head attention gives the model multiple simultaneous interaction channels. This is useful for language, but Agent Studio should also view it as learned internal routing: the model decides which prior tokens matter for the current computation.

The production caveat is that internal attention is not an audit trail. A source-backed answer still needs external retrieval traces, accepted/rejected evidence, and claim support records. Attention can help a model use context; it cannot replace source provenance.

## Parallelism And Cost

The Transformer improves parallel training over recurrent sequence models, but it also creates the quadratic attention surface that dominates long-context costs. This is why later CS25 slices on SSMs, ultra-scale training, and production inference matter: the foundation architecture enables scale, then scale exposes memory, context, and serving bottlenecks.

Agent Studio should record route behavior at both levels:

- architecture capabilities: attention-based exact context interaction, multi-head composition, positional handling, and decoder-only generation;
- serving constraints: prefill time, decode time, context-window pressure, KV-cache reuse, batch shape, and long-document recall.

## Positional And Context Contract

Attention alone is permutation-blind without position information. Positional encoding, masking, and decoder/encoder structure decide what a token can see and how order enters the model. For Agent Studio, this maps directly to context assembly:

- source order and section hierarchy should be explicit;
- prompts should distinguish instructions, user content, retrieved context, tool outputs, and prior decisions;
- untrusted retrieved text should not be allowed to function as system instructions;
- truncation and summarization policies should be traceable because they change what the model can attend to.

## Agent Studio Datastore Implications

Add or strengthen:

| Object | Purpose |
|---|---|
| `attention_route_profile` | Captures route assumptions about attention-based context use: context length, masking, position policy, modality tokenization, and expected interaction pattern. |
| `context_assembly_order_record` | Ordered prompt/context segments with role, trust label, source refs, truncation policy, and visibility to model/tool/judge. |
| `kv_cache_observation` | Runtime observation of cache reuse, cache pressure, prefill/decode split, and privacy/scope boundaries. |
| `long_context_recall_eval` | Eval slice for whether the model uses far-context evidence instead of nearby distractors. |
| `attention_architecture_caveat` | Known route caveat for attention cost, context length, positional behavior, or architecture mismatch. |
| `transformer_context_release_gate` | Promotion gate proving that architecture/context assumptions, segment order, trust boundaries, long-context evals, and serving costs are explicit before a route relies on transformer context behavior. |

## Release Gate Contract

`transformer_context_release_gate` is required before Agent Studio promotes a route that depends on long context, complex prompt packing, multimodal token mixing, tool-output reuse, reviewer/judge context, or architecture-specific attention behavior.

The gate rejects promotion unless the release record binds:

- model architecture family, encoder/decoder shape where relevant, attention pattern, position policy, masking policy, tokenizer/modality tokenization, context window, and known architecture caveats;
- ordered context assembly with segment type, role, trust label, source refs, tool-output refs, memory refs, truncation/summarization policy, and model/tool/judge visibility;
- source-grounding boundary proving that attention is not used as evidence, with retrieval traces, accepted/rejected evidence, and claim-support records where the route makes source-backed claims;
- long-context recall and distractor evals at the target context length, including far-context evidence use and truncation failure slices;
- serving evidence for prefill, decode, KV-cache pressure/reuse, batching shape, memory pressure, retrieval latency, cache privacy/scope boundary, and rollback to a smaller-context or retrieval-first route;
- human approval for any route where changed context packing can alter source rights, safety, citation behavior, tool authority, or publication output.

## Agent Studio Design Implications

- Do not treat a long context window as proof of source grounding.
- Context assembly should be a first-class artifact, not an invisible string concatenation.
- Retrieval, citation, and claim verification remain external control systems around the model.
- Long-context routes need recall and distractor evals at target context lengths.
- Serving profiles should separate prefill, decode, KV-cache, and retrieval latency because attention-heavy workloads bottleneck differently.
- Prompt and tool surfaces should preserve segment boundaries so the model's internal attention is not asked to recover missing provenance.
- Architecture/context assumptions should be release evidence: a route that changes context order, trust labels, truncation, modality packing, or long-context strategy is changing behavior even if the model name stays fixed.

## Failure Modes

- Using model attention as if it were explanation or evidence.
- Packing source text into context without segment-level trust labels.
- Assuming far-context evidence is used just because it fits in the context window.
- Ignoring prefill and KV-cache cost when designing long-document agents.
- Mixing instructions, retrieved text, tool output, and reviewer notes without role isolation.

## Related Official Video Sources

These public Stanford Online video pointers are listed from the official CS25 recordings page and tracked in [[../../05-ingestion-runs/stanford-public-video-ingestion-status]]. They are navigation sources only until a direct full-watch pass is completed; no raw captions, transcripts, comments, or long excerpts are stored.

| Video | URL | Status |
|---|---|---|
| Stanford CS25: Transformers United V6 I Overview of Transformers | https://www.youtube.com/watch?v=bHSDPgZYie0 | candidate; not watched in full |
| Stanford CS25: V2 I Introduction to Transformers w/ Andrej Karpathy | https://www.youtube.com/watch?v=XfpMkf4rD6E | candidate; not watched in full |
| Stanford CS25: V3 I How I Learned to Stop Worrying and Love the Transformer | https://www.youtube.com/watch?v=1GbDTTK3aR4 | candidate; not watched in full |
