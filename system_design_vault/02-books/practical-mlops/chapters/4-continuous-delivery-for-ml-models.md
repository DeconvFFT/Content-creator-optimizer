---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Practical MLOps"
authors: "Noah Gift; Alfredo Deza"
chapter: "4"
chapter_title: "Continuous Delivery for Machine Learning Models"
source_path: "/Users/saumyamehta/DS interview prep/books/Practical MLOps_ Operationalizing Machine Learning Models.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# Practical MLOps - Chapter 4: Continuous Delivery for Machine Learning Models

## Source Reading Scope

Direct-read extraction span: `/tmp/practical_mlops_text.txt` lines 3934-4854.

This note is original synthesis only. It does not preserve raw source text.

## Core Takeaways

Continuous delivery for ML is less about pushing a model file and more about making model-serving behavior reproducible, testable, and reversible. The chapter frames CI/CD as a feedback system: each change should be evaluated quickly, packaged consistently, and promoted only through explicit deployment gates.

The most reusable pattern is artifact discipline. A trained model should be a registered artifact, the serving surface should be a packaged application, and the deployment unit should be reconstructible from source, configuration, and registry references. Containers are valuable because they collapse local and cloud differences into a single runtime contract.

Pipeline decomposition is a reliability tool. Preparing data, training, evaluation, registration, image build, image push, and deployment should be separable steps with visible failures. A monolithic deployment script hides the exact boundary where the system broke.

Rollout strategy matters for ML because behavior failures are often discovered under live traffic. Blue-green deployments reduce cutover risk. Canary deployments are better when the team needs to compare a new model, prompt, tool route, or retrieval index under partial traffic before full promotion.

Testing should cover the service contract, not just model accuracy. The chapter's deployment testing logic maps naturally to HTTP checks, port checks, request-shape checks, model-runtime checks, output-type checks, and end-to-end response checks.

## Agent Studio Design Implications

- Treat every model, prompt bundle, retrieval index, tool registry, and evaluator as a versioned deployable artifact.
- Build deployment pipelines as named stages: extract, validate, chunk, embed, index, evaluate, register, canary, promote, rollback.
- Require contract tests for API payloads, response schemas, citation schemas, tool-call JSON, extraction manifests, and evaluator outputs.
- Use canary or blue-green rollout for changes to model routing, retrieval strategy, rerankers, prompt templates, tool schemas, and agent orchestration policies.
- Keep registry credentials, provider credentials, and deploy secrets explicit in pipeline configuration; do not let local shell state become part of the deployment contract.
- Prefer reconstructible containers or equivalent locked runtimes for any inference or ingestion component that production depends on.

## Architecture Pattern

```text
source change
  -> CI lint/unit/contract tests
  -> build serving or ingestion artifact
  -> register model/index/prompt/tool bundle
  -> deploy to shadow or canary route
  -> compare telemetry and evaluator results
  -> promote or rollback
```

## Failure Modes To Guard Against

- Local-only model paths that cannot be rebuilt in CI.
- Pipeline steps that mix training, serving, registry mutation, and deployment in one script.
- Accuracy-only promotion without service-contract tests.
- Canary deployments without metrics that can decide promotion.
- Manual verification as the primary deployment gate.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
