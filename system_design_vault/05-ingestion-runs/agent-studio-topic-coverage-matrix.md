---
type: topic-coverage-matrix
project: agent-studio-system-design
status: active
updated: 2026-05-19
manifest: agent-studio-topic-coverage-matrix.json
---

# Agent Studio Topic Coverage Matrix

## Purpose

`agent-studio-topic-coverage-matrix.json` maps Agent Studio architecture domains to canon notes, source families, release gates, and concrete design uses. It is a control-plane map for retrieval and planning agents; it does not replace the source notes or prove source freshness by itself.

## Coverage Domains

| Topic | Status | Primary use |
|---|---|---|
| Agent orchestration and long-running workflows | `canon_ready` | Route topology, task-environment and agent-architecture contracts, partial-observability and online-search controls, adversarial-search/game-surface controls, checkpoint/resume, handoffs, memory boundaries, tool contracts, approval edges, sequential and multiagent decision policy, world-model rollout/receding-horizon planning controls, governed feedback-to-learning updates, dialogue state, confirmation policy, route graph semantics, factor edges, conditional-independence claims, message-passing traces, and loopy-loop caveats. |
| Retrieval, reranking, graph search, and knowledge graph routes | `canon_ready` | Source-backed context assembly, retrieval collection releases, sparse/dense profiles, ANN recall checks, graph-index releases, extraction candidates, reranker policies, citation validity. |
| Evaluation, release gates, and route governance | `canon_ready` | Candidate promotion, held-out assessment, trace grading, grader calibration, classifier label contracts, threshold policies, metric targets, simple baselines, bottleneck diagnosis, debug fixtures, worst-error reviews, graph-route release gates, rare-class failure slices, reviewer overrides, rollback. |
| Inference, realtime voice, and serving systems | `canon_ready` | Workload class, p50/p95/p99 latency, prefill/decode/KV/cache policy, route budgets, rate-limit headroom, admission, fallback, realtime turns, ASR/TTS workload slices, and voice evaluation. |
| MLOps, data quality, lineage, and platform reliability | `canon_ready` | Dataset promotion, lineage, validation contracts, monitoring, train-serve parity. |
| Distributed state, queues, events, storage, and schema evolution | `canon_ready` | Durable state, consistency contracts, persistent-versus-ephemeral event separation, replay, idempotency, object-level partition keys, stale projections, cross-entity transactions/sagas, artifact retention, migrations. |
| Security, privacy, retention, policy, and external side effects | `canon_ready` | Tool authority, trace redaction, privacy boundaries, publishing approvals, disclosure. |
| Alignment, feedback loops, memory, and adaptation | `canon_ready_with_current_cs336_2026_lecture15_and_lecture16_17_pending` | Feedback provenance, reward boundaries, preference bias audits, midtraining mixtures, CS234 PPO policy-distance controls, world-model error budgets, memory promotion, post-training decisions. |
| Transformer/model systems, pretraining, architecture, and capacity | `canon_ready` | Context architecture, tokenizer/architecture assumptions, pretraining claims, capacity, methodology gates, metric targets, baselines, bottleneck diagnosis, debug fixtures before model/route complexity increases. |
| Vision, multimodal evidence, generated media, and video routes | `canon_ready` | Visual evidence, VQA/captioning, clip windows, generated media provenance. |
| Local corpus foundations and math/statistical prerequisites | `canon_ready_for_targeted_slices_with_deep_learning_islp_prml_and_ml_math_chapter_deepening` | Statistical validation, classifier thresholds/confusion matrices, practical methodology, probabilistic graph semantics, factor graphs, optimization objectives and constraints, stochastic evidence batches, convergence diagnostics, tradeoff records, Markov blankets, message-passing traces, uncertainty, math assumptions, AIMA foundations, speech/dialogue/IE, and extraction-backed graph prerequisites for route release gates. |
| Source governance, ingestion operations, and Obsidian control plane | `active_control_plane` | Blocked/future/gated source tracking, source-claim support states, accepted/rejected evidence ledgers, reference-world policy, source freshness and invalidation, no-raw-text enforcement, ingestion queues. |

## Operating Rule

Use the matrix for routing and retrieval. Use the linked notes and manifests for evidence. A topic marked `canon_ready` still inherits source-specific caveats from the deep-reading ledger, local-book granularity audit, official URL manifest, and Stanford availability checks.

## Agent Studio Implication

Agent Studio should treat every design decision as belonging to one or more topic domains. A route change that touches several domains should collect release-gate evidence from each relevant domain instead of relying on a single generic eval.
