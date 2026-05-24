---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
source_title: "Stanford CS25 Transformers United"
lecture_title: "On the Tradeoffs of State Space Models and Transformers"
speaker: "Albert Gu, CMU and Cartesia AI"
source_status: official_public
updated: 2026-05-18
sources:
  - https://web.stanford.edu/class/cs25/recordings/
  - https://web.stanford.edu/class/cs25/index.html
  - https://www.youtube.com/watch?index=44&list=PLoROMvodv4rNiJRchCzutFw5ItR_Z27CM&v=OyimE74UMF8
  - https://arxiv.org/abs/2312.00752
  - https://arxiv.org/abs/2111.00396
  - https://arxiv.org/abs/2212.14052
  - https://arxiv.org/abs/2403.19887
  - https://goombalab.github.io/blog/2025/tradeoffs/
---

# CS25 - State Space Model And Transformer Tradeoffs

## Reading Status

Canon-ready direct read of the official Stanford CS25 recordings page, the official CS25 V6 lecture description, and adjacent primary/open materials on S4, H3, Mamba, Jamba, and Albert Gu's tradeoff essay, rechecked on 2026-05-18. The official YouTube video is linked from the Stanford recordings page and is visibly listed there; this note records source availability but does not claim a transcript-level or timestamp-by-timestamp video watch pass.

## Public Video Availability Refresh

The Stanford CS25 recordings page now visibly lists this lecture under selected videos and links it to the official course playlist. That makes the video an eligible public source pointer for future timestamped note passes. This update only records availability and source linkage; it does not claim a transcript-level or timestamp-by-timestamp watch pass.

Agent Studio implication: the vault needs to preserve this distinction. A public video URL can satisfy source availability, while a deep video note still requires a separate watch/transcript pass with compact original synthesis and no raw transcript storage.

## Why This Matters

Agent Studio will run different workload classes: realtime voice, long source reading, batch ingestion, retrieval/reranking, background critique, and source-backed generation. The lecture topic matters because model architecture is not one-dimensional. Transformers, state-space models, and hybrid architectures have different memory, latency, throughput, and modeling tradeoffs.

The product design lesson is not "replace Transformers." It is to choose serving routes by workload characteristics: context length, token resolution, memory budget, latency target, streaming need, and required exact recall.

## Core Idea

The official CS25 V6 description frames the talk as a high-level overview of state-space models as a subquadratic alternative to Transformers, with emphasis on modeling tradeoffs, strengths and weaknesses across application areas, tokenization/resolution effects, and recent tokenizer-free directions.

Primary SSM work supports that framing:

- S4 makes structured state-space models practical for long-range sequence tasks.
- H3 identifies gaps in SSM language modeling around recall and token comparison, then explores hybrid attention/SSM designs.
- Mamba adds input-selective state updates and hardware-aware recurrent computation to improve long-sequence efficiency.
- Jamba shows that hybrid Transformer-Mamba-MoE architectures can combine attention and SSM strengths.

## Transformer-Like Memory

Attention behaves like an explicit context store. Each token can interact with prior tokens, which is powerful for exact recall, in-context learning, citation-like lookup, and cross-token comparison. The cost is that attention has expensive sequence-length scaling and a growing KV-cache at inference.

Agent Studio implication:

- Use Transformer-style models where exact context use and source-grounded cross-reference matter.
- Treat KV-cache memory as a serving constraint, especially for long book/source contexts.
- Measure prefill and decode separately for long-context routes.

## SSM-Like Memory

State-space models summarize past inputs into a fixed or compact evolving state. This can give strong streaming and long-sequence efficiency, but the compression can make exact recall and arbitrary lookup harder than attention.

Agent Studio implication:

- SSM-like routes are attractive for streaming, low-latency, long-signal, and audio-like workloads.
- Do not assume an efficient long-context architecture will preserve exact source evidence.
- Pair compressed-state models with external retrieval when factual traceability is required.

## Hybrid Architectures

H3 and Jamba both reinforce the practical lesson that hybrids can be better than pure architectural ideology. A small amount of attention can recover behaviors that pure SSMs struggle with, while SSM layers can reduce memory or improve long-context efficiency.

Agent Studio implication:

- Route registry should capture architecture class, not only model name.
- For a candidate model, record whether it is attention-only, SSM-like, hybrid, MoE, multimodal, or specialized runtime.
- Evaluate candidate models by workload slice rather than global leaderboard score.

## Tokenization And Resolution

The official lecture description highlights resolution and tokenization. This is important for Agent Studio because different modalities and source types have different natural units:

- text tokens for prose;
- sections and claims for books/docs;
- frames and segments for video;
- waveform chunks for audio;
- tool events for agent traces;
- graph nodes/edges for knowledge graphs.

If the tokenization or unit of memory is wrong, the architecture will look worse than it is. A Transformer over the wrong abstraction can be wasteful; an SSM over the wrong abstraction can compress away what matters.

Agent Studio implication:

- Choose chunking/tokenization by source type and task.
- Preserve section/claim/table boundaries before embedding or model context packing.
- Do not flatten agent traces into undifferentiated text if the model needs action/state structure.

## Serving Implications

Architecture choice shows up operationally:

- attention-heavy models need KV-cache capacity and careful batching;
- SSM-like models can support more efficient streaming over long sequences;
- hybrid models may offer better quality/efficiency balance;
- tokenizer-free or byte/segment-level approaches may help some modalities but need their own evals.

Agent Studio implication:

- Add `architecture_class` and `memory_profile` to `serving_profile`.
- Track context length, cache memory, prefill latency, decode latency, throughput, and recall quality per route.
- Keep retrieval and citation systems external even when a route supports long context.
- Require an `architecture_memory_release_gate` before a route switches architecture class, memory profile, tokenizer/resolution policy, or source-recall expectations.

## Agent Studio Design Decisions

- Do not choose one model family for all routes.
- Use attention/long-context routes for citation-heavy synthesis and exact source work.
- Use efficient streaming routes for voice, monitoring, and long signal processing when exact recall is less central.
- Evaluate SSM/hybrid candidates on Agent Studio tasks: source-grounded Q&A, long document synthesis, realtime turn-taking, background critique, and tool-trace reasoning.
- Keep architecture metadata in the route registry and serving profile.
- Treat retrieval as the audit layer for factual claims, independent of base architecture.
- Promote architecture changes only after workload-slice evals prove the selected architecture fits source-grounded Q&A, long document synthesis, realtime turn-taking, background critique, or tool-trace reasoning better than the previous serving route.

## Release Gate Contract

`architecture_memory_release_gate` is required before Agent Studio promotes a route to a new model architecture class, memory profile, tokenizer/resolution policy, context strategy, or SSM/hybrid/attention-only serving profile.

The gate rejects promotion unless the release record binds:

- selected architecture class and rejected alternatives: attention-only, SSM-like, hybrid, MoE, multimodal, tokenizer-free, or specialized runtime;
- memory profile evidence for explicit attention/KV-cache, compressed recurrent state, hybrid memory, external retrieval, graph memory, or tool/event memory;
- workload-slice rationale for source-grounded Q&A, long document synthesis, realtime turn-taking, background critique, tool-trace reasoning, batch ingestion, or streaming media;
- tokenization/resolution policy for text, sections, claims, tables, frames, waveform chunks, tool events, and graph nodes/edges;
- prefill, decode, throughput, cache-memory, latency, and cost measurements under the target route shape;
- source-recall, citation-faithfulness, long-context distractor, tool-trace, and realtime-turn evals appropriate to the route;
- retrieval/citation fallback for factual claims when model memory is compressed or exact recall is not proven;
- rollback target and incident feedback path for missed evidence, stale citations, latency regressions, or cost overruns.

## Failure Modes

- Selecting a model solely by benchmark score without matching workload.
- Assuming long sequence length equals faithful source use.
- Compressing source evidence into hidden state and losing citation traceability.
- Using attention-heavy models for low-value streaming tasks where latency/cost dominate.
- Using SSM-like models for exact lookup tasks without retrieval support.
- Ignoring tokenization and chunking as architecture-level decisions.
- Mixing latency-sensitive and throughput-oriented workloads in one serving route.

## Follow-Ups

- Cross-check future video-level notes against this release gate if timestamped coverage becomes available.
- Cross-check with CS336 inference/resource-accounting notes and Inference Engineering canon before model-route decisions.
- Later, if full official video captions become available through Stanford/YouTube tooling, add timestamped original notes without storing transcript text.

## Related Official Video Sources

This public Stanford Online video pointer is listed from the official CS25 recordings page and tracked in [[../../05-ingestion-runs/stanford-public-video-ingestion-status]]. It is a navigation source only until a direct full-watch pass is completed; no raw captions, transcripts, comments, or long excerpts are stored.

| Video | URL | Status |
|---|---|---|
| Stanford CS25: Transformers United V6 I On the Tradeoffs of State Space Models and Transformers | https://www.youtube.com/watch?v=OyimE74UMF8 | candidate; not watched in full |
