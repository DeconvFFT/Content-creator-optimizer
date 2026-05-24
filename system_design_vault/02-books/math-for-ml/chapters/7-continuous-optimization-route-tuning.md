---
type: book-chapter-note
project: agent-studio-system-design
status: canon_ready
source_id: local_books.ml_math.chapter_7_continuous_optimization
parent_source_id: local_books.ml_math
source_title: "Mathematics for Machine Learning"
chapter: "7"
chapter_title: "Continuous Optimization"
updated: 2026-05-19
local_source: "/Users/saumyamehta/DS interview prep/books/ML Math.pdf"
official_source:
  - https://mml-book.github.io/
extraction_method: pdftotext
extraction_cache: "/private/tmp/agent_studio_ingestion/ml_math.txt"
line_span: "12734-14080"
stores_raw_source_text: false
stores_long_excerpts: false
related:
  - "[[../math-foundations-for-agent-studio]]"
  - "[[../../../03-patterns/evaluation/eval-design-canon]]"
  - "[[../../../04-agent-studio-implications/Capacity Estimation - Adaptation and Serving Decisions]]"
  - "[[../../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# ML Math Chapter 7 - Continuous Optimization For Route Tuning

## Reading Status

Direct local PDF read of Chapter 7, `Continuous Optimization`, from the user-provided official/free Mathematics for Machine Learning PDF. This note covers gradient descent, step size, momentum, stochastic gradients, constrained optimization, Lagrange multipliers, convexity, linear/quadratic programs, duality, and convex conjugates. It stores compact original synthesis only, not formulas, proofs, exercises, or long excerpts.

## Core Lesson

An optimized route is only as good as the objective and constraints it optimizes. Chapter 7 makes this concrete: optimization is not a generic "make it better" step. It requires:

- an objective function;
- a feasible set or constraint policy;
- an update rule;
- step-size or search policy;
- convergence and stopping criteria;
- awareness of local minima, conditioning, and approximation noise;
- evidence about whether the problem has convex structure or only local guarantees.

Agent Studio implication: prompt tuning, reranker tuning, reward-model updates, provider routing, cost/latency tradeoffs, critique loops, and learned workflow policies must store optimization metadata before their outputs can become release evidence.

## Gradient Descent As Route Improvement Discipline

Gradient descent updates parameters by moving opposite the local gradient. Product translation: a route improvement loop should know which local signal is allowed to move the route and how large the move can be.

For Agent Studio:

- a prompt or route optimizer needs a named objective, not a vague "quality" score;
- the direction of improvement must come from an eval signal, user feedback signal, reward signal, or cost/latency metric with provenance;
- the step-size policy should be explicit: small conservative edits, larger rewrites, automated sweeps, or learned updates;
- each update should record whether the objective improved, regressed, or became unstable.

The danger is over-trusting a local signal. A local gradient can point toward a nearby basin, not the globally best route. That is exactly how a route can over-optimize style while losing source grounding, or reduce latency while hurting rare safety slices.

## Step Size And Rollback

Chapter 7 emphasizes step-size failure modes: too small is slow; too large can overshoot or diverge. This maps cleanly onto route changes.

Agent Studio should classify route changes by step size:

- micro step: wording, threshold, or reranker-weight adjustment;
- moderate step: prompt-template restructure, new retrieval filter, new eval slice, new cache policy;
- large step: model/provider swap, tool-graph rewrite, learned router, fine-tuned model, or optimization objective change.

Large steps need stronger rollback and shadow evidence. If a candidate worsens the objective or violates a constraint, the system should undo or quarantine the change instead of continuing the optimization run.

## Momentum And Noisy Signals

Momentum smooths noisy or oscillating gradients by remembering previous direction. Product analogue: repeated user feedback, reviewer edits, or eval traces should not whipsaw route configuration on every single observation.

Useful policy:

- store rolling feedback summaries separately from individual incidents;
- dampen route updates when signals conflict across slices;
- keep change momentum bounded so repeated local wins do not override safety or source-grounding constraints;
- reset momentum after distribution shift, source refresh, model swap, or objective change.

## Stochastic Gradient Descent And Mini-Batch Evidence

SGD uses noisy but cheaper gradient estimates. The chapter's systems lesson is that approximate evidence can still be useful if its sampling policy is explicit and bias is controlled.

For Agent Studio:

- a route optimizer may use a mini-batch of eval tasks, user edits, source claims, or candidate artifacts;
- the mini-batch must preserve the slices that matter for the release decision;
- small batches can explore quickly but produce unstable deltas;
- large batches are more stable but cost more and can slow iteration;
- optimizer evidence should record which examples were sampled and which slices were underrepresented.

Do not treat a tiny improvement on a convenient mini-batch as release proof.

## Constraints Are Product Requirements

Constrained optimization turns requirements into feasible sets. For Agent Studio, constraints include:

- source-grounding minimums;
- citation validity;
- privacy and retention policy;
- public-publishing approval;
- latency and cost ceilings;
- reviewer capacity;
- platform policy;
- rights/provenance boundaries;
- protected safety slices.

These are not after-the-fact checks. They define the feasible region for route optimization. A candidate route that improves the objective while violating constraints is not a better route.

## Convexity And Local Guarantees

Convex problems have stronger global guarantees than nonconvex problems. Most Agent Studio optimization surfaces are not convex: user value, factuality, style, source coverage, latency, cost, and safety interact in messy ways.

The design implication is conservative:

- do not claim global optimality for prompt, route, graph, or reward optimization;
- record whether a route objective is convex-like, heuristic, black-box, or learned;
- preserve multiple baselines and rejected candidates;
- require held-out or shadow assessment before promotion;
- track local-minimum caveats for iterative critique and self-improvement loops.

## Duality And Tradeoff Visibility

The Lagrange/duality material gives a useful product lens: constraints can be surfaced as tradeoff prices. If lowering latency sharply raises source-grounding loss, the system should expose that tradeoff instead of hiding it inside a single blended score.

Agent Studio should show:

- which constraints are active for a candidate;
- which constraints are nearly binding;
- which objective improvements depend on relaxing a constraint;
- whether the candidate is trading off quality, cost, latency, privacy, or reviewer burden.

This is especially important for optimization dashboards and release review.

## Datastore Additions

Add or strengthen:

| Object | Purpose |
|---|---|
| `route_optimization_run` | Records optimization target, route version, objective refs, sampled evidence, update policy, and outcome. |
| `optimization_step_record` | One route/prompt/model/threshold update with direction signal, step size, before/after metric deltas, and rollback status. |
| `optimization_signal_batch` | Mini-batch or sampled evidence used for one optimizer step, including slice coverage and bias caveats. |
| `optimization_constraint_record` | Product, policy, safety, source, latency, cost, or reviewer-capacity constraint used to define the feasible route region. |
| `constraint_violation_record` | Candidate behavior that improves an objective but violates a declared constraint. |
| `optimization_convergence_record` | Stop reason, convergence diagnostic, oscillation/instability flags, and local-minimum caveats. |
| `optimization_tradeoff_record` | Active or nearly active constraint tradeoffs, including objective gain versus quality, cost, latency, safety, or review burden. |
| `route_optimization_release_gate` | Promotion gate proving objective, constraints, sampled evidence, step policy, convergence, tradeoffs, fallback, and rollback. |

## Agent Studio Design Implications

- Route optimization must be an auditable release workflow, not a hidden loop inside an agent.
- The UI should show objective deltas beside constraint status.
- Automated optimization should default to shadow mode until held-out assessment and constraint checks pass.
- A candidate can win the objective and still fail release if it violates source, safety, rights, latency, or review constraints.
- Step size should be visible in route-change proposals because large steps need stronger evidence.
- Mini-batch evals are iteration evidence; final release needs broader assessment.
- Self-improvement loops should record convergence, oscillation, and rollback instead of only final output quality.

## Related Official Video Sources

No chapter-specific official Stanford optimization video has been watched or ingested for this note. Existing Stanford alignment, RL, inference, and systems notes can cross-check optimization ideas where they already have official public material. Future official video links should remain navigation candidates until a direct full-watch pass is explicitly recorded in the video ledger.

## Canon Decision

Agent Studio should treat route optimization as a constrained experiment-management surface. A route candidate is not release-ready just because an optimizer improved a scalar. It needs objective provenance, step policy, sampled-evidence coverage, constraint compliance, convergence diagnostics, tradeoff visibility, fallback, and rollback.
