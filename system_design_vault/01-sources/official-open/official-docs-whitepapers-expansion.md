---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://platform.openai.com/docs/guides/evaluation-best-practices
  - https://platform.openai.com/docs/guides/agent-evals
  - https://platform.openai.com/docs/guides/trace-grading
  - https://platform.openai.com/docs/guides/agent-builder
  - https://platform.openai.com/docs/guides/agent-builder-safety
  - https://help.openai.com/en/articles/6654000-best-practices-for-prompt-engineering-with-openai-api
  - https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview
  - https://docs.anthropic.com/en/docs/test-and-evaluate/define-success
  - https://docs.anthropic.com/en/docs/test-and-evaluate/develop-tests
  - https://docs.anthropic.com/en/docs/test-and-evaluate/eval-tool
  - https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
  - https://docs.cloud.google.com/architecture/rag-reference-architectures
  - https://www.anthropic.com/engineering/contextual-retrieval
  - https://pgxn.org/dist/vector/0.7.4/README.html
  - https://docs.langchain.com/oss/python/integrations/retrievers/contextual/
  - https://cloud.google.com/architecture/deploy-operate-generative-ai-applications
  - https://aws.amazon.com/blogs/architecture/announcing-the-aws-well-architected-generative-ai-lens/
  - https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/security.html
  - https://docs.aws.amazon.com/pdfs/whitepapers/latest/navigating-security-landscape-genai/navigating-security-landscape-genai.pdf
  - https://developers.openai.com/api/docs/guides/evaluation-best-practices
  - https://developers.openai.com/api/docs/guides/evals
  - https://developers.openai.com/api/docs/guides/agent-evals
  - https://developers.openai.com/api/docs/guides/trace-grading
  - https://developers.openai.com/api/docs/guides/graders
  - https://developers.openai.com/api/docs/guides/agent-builder-safety
  - https://platform.claude.com/docs/en/test-and-evaluate/develop-tests
  - https://docs.cloud.google.com/architecture/framework/perspectives/ai-ml/reliability
  - https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/design-principles.html
  - https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genops03.html
  - https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/observability-and-monitoring.html
  - https://cs336.stanford.edu/
  - https://raw.githubusercontent.com/stanford-cs336/lectures/main/lecture_10.py
  - https://docs.vllm.ai/en/stable/
  - https://docs.nvidia.com/tensorrt-llm/
  - https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/batcher.html
  - https://docs.ray.io/en/latest/serve/llm/index.html
  - https://docs.ray.io/en/latest/serve/llm/user-guides/observability.html
  - https://sgl-project-sglang-93.mintlify.app/concepts/radix-attention
  - https://learn.microsoft.com/en-us/azure/machine-learning/concept-model-monitoring?view=azureml-api-2
  - https://learn.microsoft.com/en-us/azure/machine-learning/concept-endpoints
  - https://www.kubeflow.org/docs/components/pipelines/concepts/pipeline/
  - https://mlflow.org/docs/2.11.1/model-registry.html
  - https://opentelemetry.io/docs/specs/semconv/gen-ai/
  - https://developers.google.com/machine-learning/guides/rules-of-ml/
  - https://papers.nips.cc/paper_files/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html
  - https://machinelearning.apple.com/research/overton
  - https://kserve.github.io/archive/0.13/modelserving/v1beta1/rollout/canary/
  - https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/
  - https://huggingface.co/docs/text-generation-inference/main/en/index
  - https://docs.langchain.com/oss/python/langgraph/observability
  - https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/
---

# Official Docs And White Papers Expansion

This note extends the system-design datastore beyond local books. The goal is a best-practices corpus that does not miss production guidance from official providers, cloud architecture teams, and security/reliability white papers.

## Direct-Read Coverage Update - 2026-05-18

The remaining provider-doc inventory links were rechecked directly where accessible:

| Source | Direct-read signal | Agent Studio implication |
|---|---|---|
| OpenAI Help prompt-engineering best practices | Official help article still captures baseline prompt hygiene: clear instructions, examples, explicit output formats, and step-by-step task decomposition. | Keep prompt guidance as baseline craft, but require evals, trace grading, and route release records before production promotion. |
| Anthropic prompt caching | Current Claude docs redirect to `platform.claude.com` and frame prompt caching as a structured prefix/cost/latency optimization. | Add cache policy fields that separate static system/tool/context prefixes from dynamic user content, with cache scope, TTL, privacy boundary, and invalidation. |
| Google Cloud deploy/operate GenAI apps | Current Cloud Architecture Center page places GenAI deployment inside the Well-Architected pillars and links agentic AI, RAG, reliability, cost, performance, security, and operations concerns. | Treat GenAI apps as operating lifecycles: architecture, deployment, monitoring, cost, security, reliability, feedback, and continuous improvement. |
| AWS Well-Architected GenAI Lens announcement | Official AWS Architecture Blog source for GenAI Lens availability and well-architected review framing. | Keep GenAI design reviews as explicit route/release gates rather than informal best-practice checklists. |
| pgvector README on PGXN | Official package README confirms exact and approximate vector search, HNSW/IVFFlat, filtering, hybrid search, half/binary/sparse vectors, monitoring, and scaling concerns. | Store vector index type, distance metric, recall/speed settings, filter strategy, hybrid fusion, and re-rank policy as route metadata. |

The Stanford CS324 lecture index remains tracked under Stanford lecture/source-map notes rather than this provider-doc expansion note.

## Best-Practice Themes To Ingest

| Theme | Official source families | Agent Studio implication |
|---|---|---|
| Agent evaluation | OpenAI evaluation best practices and agent evals | Add scenario evals, trace grading, regression datasets, and continuous quality gates before enabling autonomous profiles. |
| Prompt engineering | OpenAI and Anthropic prompt engineering docs | Prompts need success criteria, empirical tests, examples, structured outputs, and clear tool boundaries. |
| RAG architecture | Google Cloud RAG reference architectures, Anthropic contextual retrieval, pgvector, reranking docs | Retrieval should be hybrid, metadata-aware, reranked, freshness-aware, and tied to claim verification. |
| GenAI operations | Google Cloud deploy/operate GenAI apps, AWS Well-Architected GenAI Lens | Treat GenAI as a lifecycle: scope, model choice, customization, integration, deployment, iteration, governance. |
| MLOps operations | Google Cloud MLOps, AWS Machine Learning Lens, Azure ML monitoring/endpoints, Kubeflow, MLflow | Treat ingestion, evaluation, model routing, prompt release, retrieval indexing, and note promotion as lifecycle-managed production workflows. |
| Security | AWS generative AI security whitepaper, provider safety docs, tool guardrail docs | Tool use, retrieval, file access, provider credentials, and generated artifacts require threat modeling and least privilege. |
| Inference reliability | Baseten Inference Engineering, Stanford CS336, OpenAI Realtime, cloud serving docs | Track latency, cost, batching, fallback, observability, provider readiness, and workload-specific routing. |

## Cross-Check: AI Engineering Chapter 10

Status: `canon_ready`.

The official sources reinforce the chapter 10 architecture rather than contradicting it.

| Book theme | Official-source confirmation | Agent Studio design implication |
|---|---|---|
| Workflows should be explicit and inspectable | OpenAI Agent Builder describes workflows as versioned objects composed from nodes and typed edges, with preview/debug and evaluation paths. | Store agent workflows as versioned DAG/state-machine artifacts with typed inputs/outputs, not as unstructured prompt chains. |
| Agent quality requires trace-level evaluation | OpenAI agent evals and trace grading focus on reproducible evaluations over agent traces, including decisions, tool calls, and workflow behavior. | Keep per-run traces as evaluable artifacts. Regression suites should grade route choices, retrieval choices, tool calls, and final outputs. |
| Guardrails are only one layer | OpenAI agent safety guidance frames guardrails as a first wave and recommends combining structured outputs, tool approvals, trace graders, evals, and careful handling of untrusted input. | Agent Studio should combine guardrail policy, human approval, least-privilege tools, structured extraction, and evals instead of relying on prompt-only safety. |
| Success criteria precede prompt work | Anthropic prompt-engineering guidance starts with defined success criteria and empirical tests before prompt iteration. | Agent cards should require success criteria and eval datasets before a workflow can be marked production-ready. |
| Evals need task fidelity and scalable grading | Anthropic eval guidance emphasizes task-specific test cases, edge cases, automation when possible, and clear rubrics for LLM-based grading. | Eval datasets should include realistic user distributions, adversarial/edge cases, code or exact graders where possible, and rubric-backed model graders where judgment is needed. |
| Prompt caching is a cost/latency lever with structure requirements | Anthropic prompt caching guidance treats static content such as tool definitions, system instructions, context, and examples as cacheable when arranged correctly. | Cache policy should distinguish static system/tool/context prefixes from per-user dynamic content and should record cache scope/freshness. |
| Security must include access control, data flow, monitoring, and agency limits | AWS GenAI Lens security guidance emphasizes least privilege, secured component communication, monitoring/enforcement boundaries, prompt security, response validation, event monitoring, and excessive-agency risk. | Agent Studio needs permission-scoped tools, event monitoring, prompt/catalog governance, response validation, and explicit controls for write actions and autonomous behavior. |
| RAG is an architecture, not a single vector search call | Google Cloud RAG references present multiple deployment architectures across managed search, vector stores, operational databases, and orchestration. | Retrieval components should declare storage backend, freshness model, operational-data boundaries, ranking path, and deployment constraints. |

## Cross-Checked Decisions

- Gateway-centered architecture remains valid: official docs and cloud guidance converge on centralized control, monitoring, versioning, and secure access.
- Trace-first observability is required: final answers alone are not enough to debug agent behavior.
- Guardrails need false-refusal and bypass monitoring: safety controls are fallible and must be measured.
- Tool approvals and least privilege are mandatory for write actions and high-risk reads.
- Evaluation belongs inside the product lifecycle, not after launch.
- Prompt caching and semantic caching need different risk treatment: static-prefix caching is an optimization; semantic response reuse can become a correctness bug.
- pgvector index settings are product behavior: approximate indexes, distance metrics, HNSW/IVFFlat settings, filters, and hybrid fusion can change recall and therefore need eval-linked release records.
- GenAI operating guidance is lifecycle guidance: deployment, monitoring, security, cost, reliability, and continuous improvement belong in route release gates.

## Cross-Check: AI Engineering Chapters 1-10

Status: `canon_ready`.

Detailed note: [[ai-engineering-cross-check]].

OpenAI eval, prompt, production, model-optimization, fine-tuning, and latency guidance; Anthropic prompt/eval/prompt-caching guidance; Google Cloud GenAI operations and AI/ML reliability guidance; Stanford CS336; vLLM; and TensorRT-LLM reinforce the direct-read AI Engineering notes. The canon decision is that Agent Studio needs explicit product objectives, route contracts, eval contracts, prompt/version controls, dataset lineage, adaptation gates, serving profiles, runtime telemetry, and feedback loops as one connected system.

## Direct Note: OpenAI Evals And Agent Evals

Status: `deep_read_pass_1`.

Detailed note: [[openai-evals-and-agent-evals]].

OpenAI's official evaluation, agent-eval, trace-grading, grader, and agent-safety docs support a trace-first eval architecture for Agent Studio. The core design implication is that evals are versioned production artifacts: datasets, cases, graders, trace graders, eval runs, results, and promotion gates should be stored alongside prompt, model, tool, retrieval, and workflow versions.

The note is now the canonical official-source entry for OpenAI eval mechanics. Cross-check notes may cite it, but should not duplicate its contents.

## Cross-Check: Building ML Powered Applications

Status: `cross_check_pass_1`.

Detailed note: [[building-ml-powered-applications-cross-check]].

The official sources reinforce the book's practical production loop: define success criteria first, use baselines before complex agent architectures, evaluate against task-specific cases, debug traces rather than only final answers, version prompts/chains/data/assets, monitor application-level behavior, collect user feedback, and design for controlled autonomy with fallbacks and human approvals.

This supports the Building ML chapter notes as design input for Agent Studio. The later production-platform cross-check against Uber Michelangelo, Metaflow, and Google Cloud MLOps promoted the chapter set to `canon_ready`.

## Cross-Check: Inference Engineering Chapters 1, 5, And 7

Status: `canon_ready`.

Detailed note: [[inference-engineering-cross-check]].

Stanford CS336, vLLM, TensorRT-LLM, Triton, Ray Serve LLM, SGLang, and KServe reinforce the direct-read inference notes: product latency/cost constraints come first, generation is memory-bound, KV-cache management matters, batching trades latency for throughput, quantization/speculation need eval gates, production serving requires observability, and model-serving changes need canary/rollback discipline.

## Cross-Check: Practical MLOps Chapters 1-12

Status: `canon_ready`.

Detailed note: [[practical-mlops-cross-check]].

Google Cloud MLOps, AWS Machine Learning Lens, Azure model monitoring/endpoints, Kubeflow Pipelines, MLflow Registry, and OpenTelemetry GenAI conventions reinforce the direct-read Practical MLOps notes: production AI systems need automation, metadata, reproducibility, monitoring, registries, security, cost controls, feedback loops, and deployment discipline around every data/model/prompt/retrieval artifact.

## Cross-Check: Designing Machine Learning Systems Chapters 1-11

Status: `canon_ready`.

Detailed note: [[designing-machine-learning-systems-cross-check]].

Google Rules of ML, NIST AI RMF, Model Cards, Datasheets for Datasets, OpenAI eval and trace-grading docs, Anthropic eval tooling, Google Cloud MLOps and GenAI operations guidance, AWS Machine Learning Lens, Apple Overton, KServe canary rollout docs, OpenTelemetry GenAI conventions, Uber Michelangelo, Metaflow, and the NeurIPS technical-debt paper reinforce the direct-read DMLS notes: production ML starts with objectives and simple baselines; data, labels, features, evals, and traces need lineage; responsible AI needs documented intended use, privacy, fairness, and transparency controls; deployment is an operating lifecycle; monitoring must see silent quality failure; continual learning needs artifact promotion controls; and platform infrastructure must preserve reproducibility, rollback, and shared feature definitions.

## Cross-Check: LLM Engineer's Handbook Chapters 4, 7, 8, 9, And 11

Status: `canon_ready`.

Detailed note: [[llm-engineers-handbook-cross-check]].

Google Cloud RAG architectures, Anthropic contextual retrieval, pgvector hybrid search, LangChain reranking, OpenAI eval/agent/trace grading docs, Anthropic eval guidance, Ragas metrics, vLLM, Hugging Face TGI, TensorRT-LLM, Stanford CS336, Google Cloud GenAI operations, OpenTelemetry GenAI spans, LangSmith observability, and Anthropic prompt caching reinforce the direct-read handbook notes: production RAG needs versioned ingestion and retrieval traces; evals need task-specific and trace-level coverage; inference optimization must be workload-specific; and LLMOps must version prompts, chains, retrieval data, models, guardrails, feedback, and deployment artifacts together.

## Cross-Check: AI Engineering Chapter 6

Status: `cross_check_pass_1`.

The official retrieval and agent sources support the chapter 6 note.

| Book theme | Official-source confirmation | Agent Studio design implication |
|---|---|---|
| Hybrid retrieval | Anthropic contextual retrieval and pgvector guidance both support combining lexical/BM25-style search with vector search, then fusing or reranking candidates. | Use lexical, vector, metadata, and graph candidates as the first-stage pool; do not rely on embeddings alone. |
| Contextual chunks | Anthropic recommends adding compact chunk-specific context before embedding and keyword indexing, and calls out chunk boundaries as a core implementation variable. | Store chunk context, chunking policy, source IDs, and chunk provenance in the ingestion datastore. |
| Reranking | Anthropic and LangChain guidance treat reranking/compression as a precision layer over retrieved candidates, with explicit latency/cost tradeoffs. | Rerank where answer correctness matters; expose reranker version, candidate count, top-k, latency, and dropped evidence in traces. |
| RAG deployment architecture | Google Cloud RAG references cover vector search, operational databases, AlloyDB/Postgres, Cloud SQL, GKE, and GraphRAG as separate architecture options. | The vault should record backend choice, data freshness, graph involvement, operational-data boundaries, and deployment constraints for each retrieval source. |
| Agent evals | OpenAI agent evals and trace grading cover workflow-level decisions, tool calls, and trace annotations. | Agent Studio evals need planning, retrieval, grounding, tool-use, final answer, and efficiency graders. |

## Agent Studio Design Implications

- Every agent workflow needs an eval plan, not just a prompt.
- Every source-backed answer needs evidence quality, freshness, and claim coverage checks.
- Every retrieval stack needs recall controls and precision controls.
- Every tool-capable agent needs guardrails, audit trails, and permission boundaries.
- Every provider integration needs smoke tests, readiness state, fallback behavior, cost/latency telemetry, and failure evidence.
- Every local book note should be cross-checked against official docs or white papers before becoming an architectural decision.
- Every prompt-cache or retrieval-index optimization needs a correctness gate because cheaper/faster context can silently remove evidence or reuse stale context.

## Ingestion Rule

Prefer official docs, official white papers, official course materials, and official provider examples. Use blogs only when they are official engineering blogs or when they supply primary implementation detail not covered in docs.
