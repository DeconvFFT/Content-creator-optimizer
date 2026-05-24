---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
source_title: "Stanford CS25 Transformers United V6"
lecture_title: "From Next-Token Prediction to Next-Generation Intelligence: The Future of Pretraining"
speaker: "Shrimai Prabhumoye, Mistral AI"
source_status: official_public_listing_plus_open_papers
updated: 2026-05-18
sources:
  - https://web.stanford.edu/class/cs25/
  - https://web.stanford.edu/class/cs25/recordings/
  - https://arxiv.org/abs/2604.00715
  - https://arxiv.org/abs/2506.11389
  - https://arxiv.org/abs/2512.21577
related:
  - "[[cs25-parameters-context-generalization]]"
  - "[[cs25-ultra-scale-training]]"
  - "[[../../03-patterns/transformer-systems/cs25-transformer-systems-canon]]"
  - "[[../../04-agent-studio-implications/Capacity Estimation - Adaptation and Serving Decisions]]"
  - "[[../../03-patterns/evaluation/eval-design-canon]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# CS25 - Future Of Pretraining

## Reading Status

Canon-ready direct read of the official Stanford CS25 V6 listing for the April 30 talk, the CS25 recordings page, and linked/open primary papers on RAG-considerate pretraining, curriculum-guided layer scaling, and hallucination as world-model error, rechecked on 2026-05-18. The public recordings page does not currently expose this lecture as a selected public recording in the visible page text, so this note does not claim video-level coverage and stores no transcript, slide text, or long excerpts.

## Why This Matters

Agent Studio mostly needs retrieval, routing, evals, and application architecture, not model pretraining. The pretraining lecture still matters because it affects a core design decision: what should be learned into model weights, what should stay in external retrieval, and what should be represented as route policy, examples, or tools.

The main product lesson is that pretraining is not just "more tokens." Data order, data mixture, reasoning-focused data, retrieval-aware allocation, model growth schedule, and objective choice can shape what the model can do later. Agent Studio should therefore treat model provenance and pretraining assumptions as route metadata, especially when comparing models or deciding whether to adapt them.

## Pretraining As Data Allocation

The CS25 listing frames future pretraining around data selection, blending, sequencing, reasoning-centric data, and reinforcement-style objectives during pretraining. The RAG-considerate pretraining paper adds a complementary point: under fixed data budgets, there is a tradeoff between data learned parametrically during pretraining and data kept in an external retrieval store.

Agent Studio implication: route design should not assume that the largest or most pretrained model is always the best use of data. For source-backed workflows, an external source ledger can be the better place for factual, changing, rights-sensitive, or citation-critical knowledge. Model weights should carry general behavior and reusable capability; retrieval should carry updateable evidence.

## Reasoning Data In Pretraining

The CS25 listing says the lecture covers reasoning-rich data and reinforcement during pretraining. For Agent Studio, that suggests a distinction between three different reasoning improvements:

- better base-model reasoning from pretraining data and objectives;
- better route reasoning from context assembly, tools, graph structure, and verifier loops;
- better product behavior from evals, preference signals, and human feedback.

Do not attribute all reasoning failures to the base model. A route can fail because it lacked the right source, used the wrong retrieval policy, stopped too early, failed to verify, or optimized for style over grounded reasoning.

## Retrieval-Aware Pretraining And Source-Ledger Design

The RAG-considerate pretraining paper studies performance as a function of model scale, pretraining corpus size, and retrieval corpus size. Its useful design implication is not that Agent Studio should pretrain a model, but that retrieval is part of capacity planning. Retrieval can complement parametric knowledge, and its marginal value depends on model scale, task type, and how saturated pretraining already is.

Agent Studio should store:

- whether a route's knowledge is parametric or retrieved;
- the retrieval corpus size and coverage relevant to the route;
- source recall and citation-validity evals;
- model scale and context limits;
- task slices where retrieval helps or hurts;
- fallback behavior when retrieval cannot find enough evidence.

## Curriculum And Model Growth

The curriculum-guided layer-scaling paper studies progressive model-depth growth aligned with sample difficulty. For Agent Studio, the immediate lesson is about staged capability rollout. Production route complexity should grow with evidence:

- start with simple prompts, retrieval, and tools;
- add reranking, graph traversal, or critique loops when evals justify them;
- add adapters or fine-tuning only after smaller route changes fail;
- add self-hosted or specialized serving only after capacity estimates justify it.

This mirrors curriculum: do not start with maximum route complexity before the data and evals can support it.

## Hallucination As Reference-World Error

The hallucination paper linked from the CS25 overview argues for defining hallucination relative to a reference world model and conflict policy. That is directly useful for Agent Studio. A source-backed artifact should specify which reference world governs correctness:

- the cited source snapshot;
- the current official docs;
- user-provided local material;
- a product policy;
- a structured database;
- a human-approved brief.

Without a reference world, "hallucination" becomes an imprecise label. A model can be factually wrong relative to public reality, unsupported relative to the retrieved source, inconsistent with policy, or correct but unverified. These need different eval cases and mitigation.

## Failure Modes

- Pretraining gains are mistaken for source-grounded correctness without citation checks.
- A model memorizes knowledge that should remain updateable, inspectable, or rights-constrained in the source ledger.
- Reasoning failures are blamed on model capacity when the route lacked evidence, tool calls, verifier loops, or stop policies.
- Retrieval is added without measuring source recall, citation validity, and task-specific benefit.
- Route complexity grows before evals can prove each added component earns its cost.
- Hallucination evals fail to name the reference world or conflict policy.
- Benchmark improvements hide regressions on Agent Studio's actual source-backed content tasks.

## Agent Studio Design Implications

1. Treat retrieval as a capacity allocation mechanism, not only a factuality patch.
2. Keep volatile and citeable knowledge outside model weights by default.
3. Attach model provenance and pretraining assumptions to route comparisons when available.
4. Require a reference-world field for hallucination and grounding eval cases.
5. Grow route complexity in stages, with eval evidence for each added component.
6. Evaluate reasoning failures across source recall, context use, tool use, verifier behavior, and model output.
7. Use capacity estimates before any proposal to train, fine-tune, distill, or self-host.
8. Require a `pretraining_assumption_release_gate` before trusting pretrained capability claims as a reason to reduce retrieval, citation, verifier, or human-review controls.

## Datastore Implications

Add or strengthen these records:

- `knowledge_allocation_record`: route knowledge split across model weights, retrieval store, graph memory, prompt examples, tools, and human policy.
- `retrieval_budget_record`: retrieval corpus size, source coverage, index version, top-k policy, latency/cost budget, and task slices.
- `reference_world_record`: correctness reference for an eval or artifact: source snapshot, official docs, database, policy, user brief, or reviewer decision.
- `hallucination_eval_case`: reference world, conflict policy, input, expected support behavior, unsupported/factually wrong behaviors, and mitigation path.
- `route_complexity_stage`: route component added, evidence for adding it, cost/latency impact, eval delta, and rollback policy.
- `pretraining_assumption_record`: model/source provenance, claimed pretraining capability, known data/objective caveats, and route relevance.
- `reasoning_failure_diagnosis`: failure slice, missing evidence, context-use issue, tool/verifier gap, model-capacity gap, and recommended next intervention.
- `pretraining_assumption_release_gate`: promotion gate binding model provenance, claimed pretraining/reasoning capability, data/objective caveats, retrieval budget, reference-world evals, contamination/rights checks, simpler route interventions, and rollback before route policy relies on pretraining assumptions.

## Release Gate Contract

`pretraining_assumption_release_gate` is required before Agent Studio promotes a model, route, or adaptation proposal on the basis of pretraining claims, reasoning-centric pretraining, retrieval-aware pretraining, curriculum growth, or hallucination/reference-world behavior.

The gate rejects promotion unless the release record binds:

- exact model/provider/source record and pretraining assumption being relied on;
- data allocation rationale across weights, retrieval store, graph memory, prompt examples, tools, and human policy;
- retrieval budget and source-ledger coverage evidence before reducing retrieval, citation, verifier, or reviewer controls;
- reference-world records for grounding, hallucination, freshness, policy, and user-provided local-material correctness;
- objective/data caveats, known benchmark scope, contamination checks, and rights policy for any data used in adaptation or route evaluation;
- route complexity stage evidence showing simpler prompt, retrieval, reranking, tool, verifier, and policy repairs tried before training or adaptation;
- reasoning-failure diagnosis separating missing evidence, context-use errors, tool/verifier gaps, and model-capacity limits;
- source-recall, citation-validity, reasoning, grounding, latency, cost, and regression evals on Agent Studio workload slices;
- fallback route, rollback target, and incident feedback path when pretrained capability does not transfer to the product route.
