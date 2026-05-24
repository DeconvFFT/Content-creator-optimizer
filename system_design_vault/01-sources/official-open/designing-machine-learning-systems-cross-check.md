---
type: official-source-cross-check
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
source_book: "Designing Machine Learning Systems"
covered_chapters:
  - "1 - Overview of Machine Learning Systems"
  - "2 - Introduction to Machine Learning Systems Design"
  - "3 - Data Engineering Fundamentals"
  - "4 - Training Data"
  - "5 - Feature Engineering"
  - "6 - Model Development and Offline Evaluation"
  - "7 - Model Deployment and Prediction Service"
  - "8 - Data Distribution Shifts and Monitoring"
  - "9 - Continual Learning and Test in Production"
  - "10 - Infrastructure and Tooling for MLOps"
  - "11 - The Human Side of Machine Learning"
sources:
  - https://developers.google.com/machine-learning/guides/rules-of-ml/
  - https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10
  - https://arxiv.org/abs/1810.03993
  - https://arxiv.org/abs/1803.09010
  - https://developers.openai.com/api/docs/guides/evaluation-best-practices
  - https://developers.openai.com/api/docs/guides/trace-grading
  - https://platform.claude.com/docs/en/test-and-evaluate/eval-tool
  - https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning
  - https://docs.cloud.google.com/vertex-ai/docs/start/introduction-mlops
  - https://docs.cloud.google.com/architecture/deploy-operate-generative-ai-applications
  - https://docs.cloud.google.com/architecture/framework/perspectives/ai-ml/reliability
  - https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/machine-learning-lens.html
  - https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/monitoring.html
  - https://papers.nips.cc/paper_files/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html
  - https://machinelearning.apple.com/research/overton
  - https://kserve.github.io/archive/0.13/modelserving/v1beta1/rollout/canary/
  - https://opentelemetry.io/docs/specs/semconv/gen-ai/
  - https://www.uber.com/ie/en/blog/michelangelo-machine-learning-platform/
  - https://docs.metaflow.org/introduction/what-is-metaflow
  - https://ai.google/static/documents/responsible-development-of-ai.pdf
---

# Designing Machine Learning Systems - Official Cross-Check

## Scope

This note cross-checks the direct-read notes for Designing Machine Learning Systems chapters 1-11. It uses official docs, official engineering writing, and open papers only. It is original synthesis and does not store raw book text or long source excerpts.

## Verdict

Chapters 1-11 are `canon_ready` for Agent Studio architecture decisions.

The sources agree on the same production pattern: start with product objectives and simple baselines; treat data, features, labels, evals, model routes, and traces as versioned production assets; evaluate beyond aggregate metrics; document datasets and routes; design for responsible use; and make deployment the start of a monitored operating lifecycle.

## Confirmation Matrix

| DMLS theme | Official/open confirmation | Agent Studio implication |
|---|---|---|
| ML should be used only when it beats simpler production choices | Google Rules of ML recommends shipping simple heuristics first and keeping the first model simple while getting infrastructure right. | Agent Studio should preserve deterministic/template baselines for retrieval, note synthesis, claim checking, and publishing before promoting multi-agent routes. |
| Objectives and product metrics precede model metrics | OpenAI eval guidance frames evals as structured tests for application performance, while NIST AI RMF treats trustworthiness as lifecycle risk management rather than isolated model scorekeeping. | Each workflow needs explicit product objective, eval objective, risk tier, and acceptance threshold before route tuning begins. |
| Data quality and documentation are architecture concerns | Datasheets for Datasets argues that datasets need documented motivation, composition, collection process, and recommended uses. | Source manifests should document provenance, rights, collection method, source class, intended use, excluded use, freshness, extraction method, and known gaps. |
| Dataflow and storage should follow access patterns | Google Cloud MLOps and Vertex AI organize experiments, model registry, features, monitoring, batch inference, online serving, and distributed compute as separate but connected lifecycle tools. | Keep raw sources, extracted text, source metadata, chunks, embeddings, graph edges, eval runs, traces, and Obsidian notes in distinct storage surfaces with shared IDs. |
| Labels, feedback, and annotations need lineage | OpenAI trace grading assigns structured labels and scores to traces; Anthropic's eval tool supports reusable test cases, prompt comparisons, grading, and prompt versioning. | Treat reviewer edits, trace grades, source approvals, and feedback signals as labeled data with rubric version, source snapshot, route config, and reviewer provenance. |
| Feature parity prevents train-serving skew | Google Cloud MLOps explicitly uses feature stores to standardize definitions, storage, and access for both training and serving and to avoid skew. Vertex AI Feature Store similarly centralizes reusable features. | Define source, chunk, retrieval, graph, route, prompt, and eval features once; offline ingestion and online retrieval should consume the same versioned definitions. |
| Leakage and duplicate contamination must be designed out | Google Rules of ML emphasizes pipeline correctness before clever models, and dataset documentation practice reinforces collection-process transparency. | Split evals by source/time/user/workflow when needed; deduplicate before splits; never tune prompts, filters, rerankers, or graders on final test sets. |
| Offline evals need baselines, cases, graders, and trace detail | OpenAI eval best practices and trace grading support application-specific evals, structured criteria, and workflow-level trace evaluation; Anthropic supports prompt version comparison across test cases. | Promotion gates should include heuristic/current baselines, perturbation tests, invariance tests, directional tests, calibration checks, confidence thresholds, and trace-level diagnosis. |
| Responsible AI requires transparency, accountability, privacy, fairness, and lifecycle governance | NIST AI RMF formalizes trustworthy AI risk management; Google responsible AI material highlights interpretability, adversarial robustness, privacy, and fairness; Model Cards documents intended use, evaluation conditions, and limitations. | Agent Studio needs source datasheets, route cards, risk tiers, human review gates, privacy classification, limitations, out-of-scope uses, and slice-level quality reporting. |
| Model/route cards prevent unsafe reuse | Model Cards recommends documenting model details, intended use, evaluation factors, metrics, data, ethical considerations, caveats, and recommendations. | Create Agent Studio route cards for every production agent/model route: owner, intended use, disallowed use, sources, eval slices, thresholds, fallback, rollback, and caveats. |
| Deployment is production operation, not endpoint exposure | Google Cloud's GenAI operations guidance treats production deployment as coordination across prompts, chains, data, adapter assets, databases, and application services. | Agent Studio needs deployment records for prompts, model routes, chains, retrieval indexes, tools, and workflow code, not only LLM provider names. |
| Production systems contain many routes and components | Uber Michelangelo describes end-to-end platform support for managing data, training, evaluation, deployment, prediction, and monitoring across multiple model types. | Keep a model-route and artifact registry that covers writing, judging, retrieval, reranking, moderation, embedding, vision, speech, and tool-policy routes. |
| Batch, online, and hybrid prediction need separate policies | Google Cloud MLOps separates pipeline delivery, model serving, monitoring, and continuous training. KServe canary docs show traffic-managed inference rollout. | Batch ingestion/eval queues and online user-facing runs should be separate deployment surfaces with shared lineage and promotion gates. |
| Train-serving skew is a production design bug | Google's Rules of ML emphasizes first getting the pipeline right and preserving feature parity between learning and serving. Google Cloud MLOps also calls out feature stores for shared batch and low-latency serving definitions. | Chunking, extraction metadata, embeddings, filters, reranker features, and source-rights fields should be defined once and reused across offline eval and online retrieval. |
| Monitoring must catch silent quality degradation | AWS Machine Learning Lens, Google Cloud reliability guidance, and Apple Overton all frame production ML quality as an operational monitoring problem, not only an offline accuracy problem. | Agent Studio should monitor citation validity, retrieval hit quality, reviewer acceptance, correction rate, tool success, prompt/model route regressions, cost, and latency. |
| Drift alerts require diagnosis, not automatic panic | Google Cloud MLOps ties monitoring to retraining cues and validation; DMLS' warning about internal pipeline bugs is consistent with platform guidance. | Drift alerts should open investigations that inspect source schema, extraction versions, index versions, prompt versions, provider changes, and production input mix. |
| Generated artifacts can create feedback loops | Overton's focus on fine-grained monitoring and contradictory/incomplete supervision reinforces the need for source lineage in systems that improve from feedback. | Generated notes must stay distinct from primary sources; retrieval should expose whether evidence is primary, official docs, local book synthesis, or derivative notes. |
| Continual learning is artifact promotion infrastructure | Google Cloud MLOps level 1/2 emphasizes CT, validation, metadata management, CI/CD, and pipeline deployment. | Treat index, prompt, model-route, eval-suite, and tool-policy updates as champion/challenger artifacts with approvals and rollback targets. |
| Production testing needs rollout controls | KServe documents inference-service canary rollout and rollback behavior; this matches DMLS' shadow/canary/A-B production testing ladder. | High-risk Agent Studio workflow changes should move through backtest, shadow, canary, and promotion states rather than direct replacement. |
| ML technical debt comes from hidden dependencies and weak boundaries | The NeurIPS technical-debt paper validates the risk of ML-specific maintenance costs from entanglement, undeclared consumers, configuration, and pipeline debt. | Keep narrow contracts between source registry, extraction, chunking, retrieval, generation, eval, and publication workflows. Make hidden dependencies visible in manifests. |
| Platform abstraction should preserve local-to-production parity | Metaflow's official docs emphasize a unified API for prototype-to-production data-intensive ML/AI work. | Agent Studio should expose high-level ingestion/eval/workflow controls while recording environment, image/dependency, parameter, and artifact metadata. |
| Observability needs shared semantics | OpenTelemetry GenAI conventions define signals for GenAI events, exceptions, metrics, model spans, agent spans, provider calls, and MCP. | Trace schema should preserve model spans, agent spans, retrieval/tool events, exceptions, metrics, prompt/index versions, and source/chunk IDs. |

## Agent Studio Canon Decisions

- Require workflow objective declarations before model/prompt selection.
- Keep simple baselines and current-production baselines in every eval suite.
- Maintain source datasheets and route cards as first-class artifacts.
- Separate raw source, extracted text, chunk metadata, embeddings, graph relationships, traces, evals, and Obsidian synthesis.
- Version labels, reviewer feedback, rubric definitions, trace grades, and feedback-derived natural labels.
- Use active-learning style review queues for uncertain, disputed, and high-cost examples.
- Define shared feature schemas for source cards, chunks, retrieval candidates, graph nodes, route choices, and eval traces.
- Split and deduplicate eval datasets by source/time/group where leakage is plausible.
- Require task-specific, trace-level, slice-level, perturbation, invariance, directional, calibration, and confidence checks before route promotion.
- Add privacy classification and retention policy to user documents, traces, edits, prompts, source choices, and generated artifacts.
- Add `production_tier` and `serving_mode` to every workflow, model route, and artifact promotion.
- Split batch ingestion/eval operations from online serving, but use common source/chunk/retrieval feature definitions.
- Promote artifacts through `candidate`, `shadow`, `canary`, `production`, `rolled_back`, and `retired` states.
- Store lineage for prompts, model routes, retrieval indexes, tool policies, eval suites, corpora, source manifests, and generated notes.
- Instrument production runs with trace IDs, source IDs, chunk IDs, index versions, prompt versions, model routes, tool-policy versions, cost, latency, and outcome metrics.
- Keep generated synthesis notes, official docs, local book notes, and primary local/source files in separate provenance classes.
- Treat monitoring as a trigger for diagnosis and controlled update, not an automatic retraining command.
- Use platform tooling to make reproducible ingestion, eval, and rollout cheaper than manual notebooks or ad hoc scripts.

## Remaining Work

- Connect the DMLS canon set to concrete Agent Studio artifact registry, workflow-run schema, route-card schema, source-datasheet schema, and eval-suite schema.
