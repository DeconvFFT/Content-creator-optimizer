---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_status: official_google_cloud_docs
sources:
  - https://docs.cloud.google.com/architecture/deploy-operate-generative-ai-applications
  - https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning
  - https://docs.cloud.google.com/architecture/gen-ai-rag-vertex-ai-vector-search
  - https://docs.cloud.google.com/architecture/gen-ai-graphrag-spanner
  - https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-overview
  - https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/eval-python-sdk/determine-eval
  - https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/eval-python-sdk/run-evaluation
  - https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-agents
---

# Google Cloud GenAI Operations And Evaluation

## Reading Scope

This note covers Google Cloud's official Architecture Center guidance for operating generative AI applications, MLOps automation, RAG and GraphRAG reference architectures, and Vertex AI Gen AI evaluation guidance. It is original synthesis only; it stores no raw docs text, diagrams, code samples, or copied checklists.

## Core Thesis

Production GenAI is not a single model endpoint. It is a versioned application system made of prompts, chains, model choices, retrieval stores, grounding data, adapters, evaluation datasets, infrastructure, security controls, and monitoring loops.

For Agent Studio, the direct implication is that every route release must version the full prompted model component and its surrounding orchestration. A model switch, prompt edit, retrieval-index rebuild, graph traversal change, adapter update, safety setting, or hosting topology change is a deployable artifact change, not an informal tweak.

## Current-Source Cross-Check

The current Google Cloud GenAI operations page still frames production work as DevOps/MLOps plus continuous improvement over prompts, model swaps, composition, cost, latency, and feedback loops. The current MLOps automation guidance still requires CI/CD over pipeline components, tests, registries, metadata, orchestration, and deployment targets.

The current RAG architecture still separates data ingestion from serving: source intake, parsing, chunking, embeddings, index updates, and serving-time query embedding/search/model calls are different subsystems. The current GraphRAG architecture adds graph extraction/storage, graph/vector association, Spanner Graph operational concerns, throughput/caching/batch choices, and graph-schema/query tuning. The current Vertex evaluation docs still distinguish dataset/metric/evaluation-run workflow, model-based and computation-based metrics, repeatable task evaluation, experiment tracking, and agent trajectory metrics including exact match, in-order match, any-order match, precision, recall, and single-tool checks.

## Lifecycle Implications

Google's GenAI lifecycle separates discovery, development/experimentation, deployment, and continuous improvement. The useful Agent Studio translation is:

- discovery chooses provider/model/infrastructure fit against capability, latency, cost, safety, and rights constraints;
- experimentation tests prompts, chains, grounding, examples, adapters, and model choices together;
- deployment promotes all mutable components through version control and release gates;
- continuous improvement turns logs, human feedback, failures, and new source data into eval cases and candidate releases.

The main warning is that GenAI prototypes can launch with little data, but production quality depends on managing many heterogeneous data surfaces: prompts, few-shot examples, grounding data, task datasets, synthetic data, retrieval stores, and model/provider behavior.

## Prompted Component Boundary

Google's "prompted model component" framing matters because the prompt is part of the application, not a runtime parameter lost in logs. In Agent Studio, a prompted component should include:

- model/provider route;
- prompt template and rendered prompt hash;
- system/developer instructions;
- few-shot examples;
- grounding source snapshot;
- tool and chain definition;
- safety and output-structure policy;
- eval suite and release gate.

This avoids a common failure where teams version code but not the actual instruction/context bundle that determines behavior.

## Chain And Orchestration Risk

Google emphasizes that chained GenAI systems differ from traditional ML pipelines because inputs and outputs are open-ended, components are hard to evaluate in isolation, and end-to-end behavior changes when prompts, model choices, tools, or APIs shift.

Agent Studio should therefore evaluate both:

- component behavior, such as a retriever, reranker, tool-call formatter, or source summarizer;
- route behavior, such as the full content-production, review, publishing, or ingestion workflow.

A chain can pass component tests while failing the user job because context was lost, tool output was misread, a retrieval source was stale, or a handoff changed the task definition.

## Evaluation Discipline

Google's evaluation guidance reinforces several route rules already present in the vault:

- define evaluation criteria and metrics early enough that experiment comparisons are stable;
- build custom datasets that represent essential, average, edge, and adversarial cases;
- use synthetic data only as provisional or reviewed support when real ground truth is scarce;
- align automated evaluators with human judgment before they become release gates;
- include adversarial prompting, leakage checks, and robustness cases;
- separate final-response evaluation from trajectory evaluation for agents.

Vertex's agent-evaluation split is especially useful for Agent Studio: final responses prove user-visible output quality, while trajectory evaluation checks whether the agent used the right tools, arguments, and action sequence. Both are needed before high-autonomy routes can ship.

## RAG And GraphRAG Operations

The Google RAG and GraphRAG reference architectures make ingestion and serving distinct subsystems. Agent Studio should preserve that split:

- ingestion handles source intake, parsing, chunking, embeddings, graph extraction, vector/graph index updates, and quality checks;
- serving handles user query intake, query embedding, vector search, graph traversal where needed, prompt assembly, model call, safety filtering, response logging, and monitoring.

GraphRAG should not be treated as "RAG plus a diagram." It adds graph extraction, graph storage, entity/relationship quality checks, graph traversal policy, graph-vector join logic, and graph-specific eval cases. Use it only when relationships among sources materially improve retrieval or reasoning.

## CI/CD And Release Gates

Google's MLOps and GenAI deployment guidance points to a release pipeline that covers more than application code. Agent Studio release gates should include:

- source and dataset version changes;
- prompt and chain definition changes;
- retrieval index or graph index rebuilds;
- model/provider/adapter route changes;
- security and access-boundary checks;
- integration tests for APIs, tools, and databases;
- eval runs for final output and route trajectory;
- load, latency, scalability, and cost checks for online routes;
- batch throughput checks for ingestion and offline eval routes.

Batch and online routes need different promotion evidence. A background ingestion or eval route can trade latency for cost and durability; an interactive studio route needs low-latency integration tests and graceful degradation evidence.

## Agent Studio Datastore Implications

Add or strengthen these durable records:

- `prompted_component_release`: binds model/provider, prompt template, examples, grounding snapshot, chain definition, tools, safety policy, and eval gate.
- `chain_definition_record`: stores route graph, model/tool/API steps, input/output contracts, side-effect class, and version.
- `genai_artifact_version`: versions prompt templates, chain definitions, retrieval stores, graph indexes, adapter weights, eval datasets, and safety configs.
- `agent_trajectory_eval_case`: expected tool/action sequence, allowed alternatives, final-response requirement, and risk tags.
- `agent_trajectory_eval_result`: predicted trajectory, mismatch type, failing step, final-response score, and promotion impact.
- `rag_ingestion_subsystem_record`: source intake, parser, chunker, embedding profile, vector index, graph extraction, quality checks, and refresh trigger.
- `rag_serving_subsystem_record`: query handling, embedding model, retrieval policy, graph traversal policy, prompt assembly, model route, safety filter, and logging policy.
- `graph_retrieval_policy`: graph-store ref, traversal depth/bounds, relation filters, vector-graph join policy, entity-quality threshold, and fallback behavior.
- `genai_ci_cd_gate`: required tests, eval suites, security scans, load/cost checks, approval status, and rollback plan for a route release.
- `prompted_component_release_gate`: route release, prompted component refs, artifact versions, CI/CD gate, final-response evals, trajectory evals, ingestion/serving readiness, security checks, cost/latency checks, and rollback target.

## Design Commitments

- Version prompts, chains, retrieval stores, graph indexes, adapters, and safety configs as deployable artifacts.
- Evaluate route trajectories separately from final outputs.
- Keep ingestion and serving subsystems independently observable and releasable.
- Treat GraphRAG as an infrastructure and eval commitment, not a default retrieval upgrade.
- Promote online, batch, ingestion, and eval routes with different latency/cost/durability gates.
- Convert production failures and human corrections into eval cases before optimizing the next route version.
- Treat this note as canon-ready for Agent Studio route-release architecture because it is cross-checked against the current Google Cloud GenAI operations, MLOps, RAG, GraphRAG, and Vertex AI evaluation docs.
