---
type: pattern-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
sources:
  - "[[../../02-lectures/stanford/cs25-transformer-foundations]]"
  - "[[../../02-lectures/stanford/cs25-retrieval-augmented-language-models]]"
  - "[[../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]]"
  - "[[../../02-lectures/stanford/cs224r-reward-reasoning-world-models]]"
  - "[[../../02-lectures/stanford/cs25-world-modeling-jepa]]"
  - "[[../../02-lectures/stanford/cs25-aligning-open-language-models]]"
  - "[[../../02-lectures/stanford/cs25-future-of-pretraining]]"
  - "[[../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]]"
  - "[[../../02-lectures/stanford/cs25-ultra-scale-training]]"
  - "[[../../02-lectures/stanford/cs25-production-inference]]"
  - "[[../../02-lectures/stanford/cs25-lm-intuition-future-ai]]"
  - "[[../../02-lectures/stanford/cs25-whole-part-hierarchies]]"
  - "[[../../02-lectures/stanford/cs349d-ai-inference-infrastructure]]"
  - https://web.stanford.edu/class/cs25/recordings/
  - https://web.stanford.edu/class/cs25/past/cs25-v3/index.html
  - https://web.stanford.edu/class/cs25/index.html
related:
  - "[[../retrieval/reranking-search-kg-patterns]]"
  - "[[../agent-systems/agent-route-architecture-canon]]"
  - "[[../llm-systems/nlp-llm-systems-canon]]"
  - "[[../inference/realtime-and-inference-patterns]]"
  - "[[../../04-agent-studio-implications/Capacity Estimation - Adaptation and Serving Decisions]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# CS25 Transformer Systems Canon

## Scope

This canon note consolidates current CS25 public-source coverage that is already direct-read in the vault: transformer foundations, retrieval-augmented language models, generalist agents in open-ended worlds, world modeling through JEPA, aligning open language models, future-of-pretraining, state-space/Transformer tradeoffs, ultra-scale training, production inference, LM intuition/future-AI capability behavior, and whole-part hierarchy representation. It also uses the official CS25 V3/V6 source pages and recordings page as source-map evidence. It stores original synthesis only and does not store transcripts, slide text, or long excerpts.

## Canon Decision

Agent Studio should treat Transformer-era systems as a set of routed capabilities, not a single model endpoint. The core production choices are external memory versus model memory, general agent environment versus prompt-only task, attention versus compressed-state architectures, and retrieval/tool/serving/adaptation capacity.

The practical rule: route design must bind knowledge source, agent environment, architecture class, serving profile, and evaluation surface together.

## Four System Axes

| Axis | CS25 signal | Agent Studio decision |
|---|---|---|
| Knowledge | RAG separates parametric model memory from inspectable external memory. | Facts, book knowledge, official docs, and source-grounded claims live in source/index/graph infrastructure before model weights. |
| Context | Self-attention gives models learned internal routing over token context, but it is not provenance. | Context assembly, segment order, trust labels, retrieval traces, and claim checks remain explicit datastore artifacts. |
| Agency | Generalist agents need environment, tools, memory, feedback, and skill libraries. | The studio workspace is an environment with typed observations, actions, artifacts, approvals, and feedback records. |
| World state | Predictive representations preserve decision-relevant latent state instead of reconstructing every surface detail. | Store typed source/artifact/workflow state, object relations, transition predictions, and stale-dependency records. |
| Architecture | Transformers, SSMs, and hybrids have different recall, streaming, memory, and tokenization tradeoffs. | Route registry records architecture class and memory profile; exact-source tasks keep retrieval/citation outside hidden state. |
| Capacity | Ultra-scale training and serving are constrained by memory, compute, communication, parallelism, and runtime details. | Fine-tuning, distillation, long-context routes, and self-hosting require capacity estimates and release evals. |
| Pretraining | Future pretraining work changes data allocation, reasoning capability, and hallucination/reference-world behavior. | Store knowledge allocation, pretraining assumptions, and reference-world evals before trusting model behavior as source-grounded. |
| Post-training | Open alignment recipes separate base models, data, SFT, preference tuning, verifiable rewards, evals, decontamination, and negative results. | Route changes that alter behavior need recipe, artifact, eval, and decontamination records even when no model checkpoint is trained. |
| Test-time compute | Reasoning systems can scale by spending more inference-time search, verification, and parallel candidate generation. | Route releases need explicit compute budgets, score-vs-cost curves, and long-horizon safety/capability evals. |
| Inference | Production serving splits into throughput, low-latency, and bursty workload classes. | Serving profiles record workload class, runtime engine, GPU, phase latency, cold-start policy, endpoint contract, and serving regression evals. |
| Capability behavior | LM reasoning, instruction following, and emergent abilities depend on scale, prompt/instruction recipe, task mixture, and metric. | Capability claims live in route-slice records with exact model, prompt, examples, tools, evals, verifier, latency, and cost evidence. |
| Composition | Whole-part hierarchy work highlights that fixed architectures need explicit compositional structure for variable input scenes. | Media, claims, edits, sources, regions, frames, and approvals should form an evidence graph rather than one flat caption or embedding. |

## RAG Canon

RAG is not an answer-generation trick. It is a governed memory subsystem with parsing, source records, chunking, indexing, retrieval, reranking, context assembly, generation, citation, and eval. Long context does not replace RAG when the product needs freshness, access control, provenance, or auditability.

Agent Studio commitments:

- every grounded answer has a `retrieval_trace`;
- source records and chunks carry rights, authority, freshness, and hierarchy metadata;
- accepted and rejected evidence are both stored;
- retrieval quality is evaluated before final-answer quality;
- index/source refresh is the default path for factual updates.

Future-pretraining coverage adds a capacity-allocation rule: some knowledge belongs in model weights, some belongs in retrieval, and some belongs in policy, tools, or human approval. A route should state this split explicitly instead of treating larger pretraining as a substitute for source-ledger design.

Pretraining assumptions are release evidence, not marketing context. Before a route trusts a pretrained model enough to reduce retrieval, citation, verifier, reviewer, or human-policy controls, a `pretraining_assumption_release_gate` should bind the exact model/source assumption, retrieval budget, source-ledger coverage, reference-world evals, contamination and rights checks, simpler interventions tried, reasoning-failure diagnosis, regressions, fallback, and rollback.

## Generalist Agent Canon

Open-ended agents are built from an environment, knowledge base, architecture, skill/memory system, and feedback loop. For Agent Studio, the environment is the project workspace: sources, notes, artifacts, tools, previews, publishing surfaces, review decisions, and evals.

Agent Studio commitments:

- agents operate over typed observations and actions, not hidden prompt context alone;
- procedural skill memory is separate from factual source memory and preference memory;
- reusable skills have trigger conditions, inputs, outputs, owner, success evidence, failure modes, and rollback path;
- rejected actions and drafts are retained as eval/preference material;
- autonomous actions leave trace records with next-state evidence.

## Architecture And Memory Canon

Attention-heavy Transformers are strong for exact context interaction, in-context learning, and citation-like lookup, but KV-cache and prefill costs become serving constraints. SSM-like architectures compress history into compact state, which can help streaming and long-signal workloads but can lose exact recall. Hybrids are production-relevant because they mix quality and efficiency behaviors.

Agent Studio commitments:

- `route_registry_entry` and `serving_profile` record `architecture_class` and `memory_profile`;
- source-grounded synthesis and citations use retrieval/citation systems even when the model has long context;
- SSM/hybrid candidates are evaluated on Agent Studio slices: long document synthesis, realtime turn-taking, source-grounded Q&A, tool-trace reasoning, and background critique;
- context length, tokenizer/resolution, and source chunking are architecture decisions.

## Capacity Canon

Training and adaptation are not generic improvements. Ultra-scale training exposes memory, compute, communication, parallelism, and stability constraints. For application engineering, the most important outcome is capacity realism: do not fine-tune when the actual problem is stale retrieval, missing provenance, weak evals, or bad tool routing.

Agent Studio commitments:

- every fine-tune, PEFT, distillation, long-context adaptation, or self-hosting proposal starts with a `capacity_estimate`;
- model-route metadata records dense/MoE/hybrid class, context length, quantization, runtime, batching, cache behavior, and measured throughput;
- serving evals include latency, cost, recall, grounding, and quality by workload slice;
- training feasibility, adaptation feasibility, and serving feasibility are separate decisions.

## Datastore Objects

Add or strengthen:

| Object | Purpose |
|---|---|
| `agent_environment` | Workspace state surface available to an agent: sources, artifacts, tools, observations, approvals, and feedback channels. |
| `skill_record` | Reusable procedural memory with trigger, inputs, outputs, owner, success evidence, failure modes, and rollback policy. |
| `model_architecture_profile` | Architecture class, memory behavior, context limits, MoE/hybrid flags, tokenizer/resolution assumptions, and known task strengths. |
| `attention_route_profile` | Attention/context assumptions for a route: context window, position policy, masking, modality tokenization, and expected interaction pattern. |
| `context_assembly_order_record` | Ordered prompt/context segments with role, trust label, source refs, truncation policy, and model/tool/judge visibility. |
| `transformer_context_release_gate` | Promotion gate for architecture/context assumptions, segment order, trust labels, source-grounding boundary, long-context evals, KV/cache observations, serving costs, fallback, and rollback. |
| `long_context_recall_eval` | Target-length eval for far-context recall, distractor resistance, and source support. |
| `capacity_estimate` | Training/adaptation/serving feasibility record with memory, compute, communication, runtime, cost, latency, and fallback path. |
| `model_route_measurement` | Observed route performance by workload slice: prefill, decode, retrieval, rerank, tool latency, cost, throughput, recall, and failures. |
| `knowledge_allocation_record` | Declares whether route knowledge lives in weights, retrieval, graph memory, prompt examples, tools, or human policy. |
| `knowledge_allocation_release_gate` | Promotion gate proving memory placement, generalization need, lighter interventions, latent evals, serving impact, fallback, and rollback before moving knowledge between weights/context/tools/policy. |
| `reference_world_record` | Defines the source snapshot, official docs, database, policy, user brief, or reviewer decision that makes an answer correct. |
| `route_complexity_stage` | Tracks each added route component, evidence for adding it, cost/latency impact, eval delta, and rollback policy. |
| `serving_workload_profile` | Workload class, interaction mode, concurrency, input/output length distribution, streaming support, and SLOs. |
| `inference_phase_measurement` | Prefill, decode, retrieval, rerank, tool, queue, cold-start, and end-to-end latency by route and workload slice. |
| `runtime_engine_record` | Engine/provider, version, precision, quantization, batching, cache behavior, supported modalities, and caveats. |
| `serving_feature_compatibility_matrix` | Compatibility status for parallelism, batching, PagedAttention, context caching, chunked prefill, speculation, hierarchical caching, and disaggregation. |
| `serving_optimization_gate` | Baseline versus candidate optimization, workload slice, performance delta, quality delta, memory delta, compatibility result, and rollback condition. |
| `world_state_record` | Typed source/artifact/workflow/route state relevant to an agent run. |
| `state_transition_record` | Predicted and observed consequences of an agent action, including stale approvals/evals and rollback. |
| `artifact_dependency_graph` | Dependency graph connecting sources, claims, artifacts, media regions, evals, approvals, and published outputs. |
| `state_transition_release_gate` | Promotion gate proving state-mutating routes predict affected objects, invalidated approvals/evals, stale dependencies, forbidden side effects, observed outcomes, rollback, and incident feedback. |
| `capability_slice_record` | Route-local capability claim with task family, model/provider, prompt recipe, examples, tools, source memory, eval set, and observed behavior. |
| `reasoning_mode_policy` | Route policy for decomposition, hidden or visible reasoning artifacts, verifier use, token budget, latency budget, and fallback. |
| `instruction_recipe_record` | Versioned instruction source, task mixture, examples, grounding/safety clauses, owner, and release history for route behavior. |
| `part_whole_evidence_graph` | Graph connecting artifact wholes to regions, frames, tracks, source snippets, claims, prompts, edits, and approvals. |
| `hierarchical_consistency_eval` | Eval slice checking whether local parts and global artifact claims agree. |

## Release Gates

A route cannot be promoted when:

- source-grounded behavior lacks retrieval traces and citation evidence;
- autonomous behavior lacks typed environment/actions and skill ownership;
- model route metadata lacks architecture and memory profile;
- long-context or SSM/hybrid route has no source-recall eval;
- training/adaptation proposal lacks capacity estimate and rollback plan;
- serving route lacks workload-slice measurements.
- batch, interactive, and bursty workloads share one untyped serving profile.
- runtime, GPU, precision, or batching changes lack route-specific quality and latency regression evals.
- hallucination or grounding evals lack a reference-world record.
- route complexity grows without evidence that the previous stage failed.
- reasoning, instruction following, or emergent-capability claims lack route-slice measurements under the exact prompt/tool/source context.
- media or multimodal decisions flatten part-level evidence into one whole-artifact verdict without region/frame/source lineage.

## Agent Studio Implications

- Keep RAG, agent memory, and skill memory as separate datastore lanes.
- Treat CS25 as the systems bridge between CS224N language modeling, CS231N multimodality, and CS336/inference infrastructure.
- Use capacity estimates to prevent expensive training work from masking simpler retrieval, eval, or workflow fixes.
- Promote public CS25 video notes only after direct full-video watching; current canon rests on public source pages and already-read primary/open materials.
- Treat reasoning behavior and instruction-following behavior as versioned route recipes with eval evidence, not as generic model traits.
- Store part-whole evidence graphs for multimodal artifacts so edits, captions, claims, approvals, and source links can be invalidated when a part changes.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.

- [[../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
- [[../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
- [[../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "How I Learned to Stop Worrying and Love the Transformer" ([YouTube](https://www.youtube.com/watch?v=1GbDTTK3aR4)).
- [[../../02-lectures/stanford/cs25-aligning-open-language-models]] - Stanford CS25, "Aligning Open Language Models" ([YouTube](https://www.youtube.com/watch?v=AdLgPmcrXwQ)).
- [[../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../02-lectures/stanford/cs25-whole-part-hierarchies]] - Stanford CS25, "Whole-Part Hierarchies in a Neural Network" ([YouTube](https://www.youtube.com/watch?v=CYaju6aCMoQ)).
