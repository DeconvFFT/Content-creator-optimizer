---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_status: official_public
stores_raw_source_text: false
stores_long_excerpts: false
sources:
  - https://www.uber.com/ie/en/blog/michelangelo-machine-learning-platform/
  - https://www.uber.com/us/en/blog/automate-design-specs/
  - https://www.uber.com/at/en/blog/scaling-responsible-ai/
related:
  - "[[production-ml-platform-cross-check]]"
  - "[[../../03-patterns/agent-systems/agent-route-architecture-canon]]"
  - "[[../../03-patterns/security/genai-security-canon]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Uber ML Platform Agentic Governance

## Reading Scope

Direct-read pass over three official Uber Engineering posts: Michelangelo for end-to-end production ML platform shape, uSpec for local MCP-backed agent workflow design, and Uber's Responsible AI program for model inventory, model cards, explainability, shift-left governance, education, and adoption at scale.

This note stores compact original synthesis only. It does not store raw article text, image contents, copied tables, or long excerpts.

Current-source check on 2026-05-18: the official Michelangelo page still presents an end-to-end ML workflow for data management, training, evaluation, deployment, prediction, and monitoring, with feature pipeline reuse, train/serve parity, model repositories, deployment modes, prediction logging, holdbacks, delayed labels, and live monitoring as platform objects. Uber's 2026 uSpec post confirms the local-agent/MCP work-surface pattern: the agent runs locally, reads structured Figma component truth through Figma Console MCP, uses versioned skills, schemas, and reference docs, and renders directly back into Figma. The Responsible AI post still frames governance as inventory, model cards, explainability, education, and shift-left adoption across existing workflows.

## Core Read

Uber's platform story has three layers that map directly to Agent Studio:

1. Michelangelo standardizes the ML lifecycle: data management, training, evaluation, deployment, prediction, and monitoring.
2. uSpec shows an enterprise agent pattern: local agent plus MCP bridge plus domain-specific skills plus direct rendering into the work surface.
3. Responsible AI turns platform metadata into governance: model catalog, model cards, explainability, early review checks, education, and adoption across existing systems.

Agent Studio should treat these as one system-design lesson: production AI is not a model endpoint. It is a governed platform lifecycle with source/data parity, artifact registries, local tool boundaries, model/route cards, monitoring, and review gates.

## Production ML Platform Shape

Michelangelo was built to replace fragmented one-off model production paths with shared lifecycle infrastructure. The reusable pattern is not Uber's exact stack. It is the object model: offline and online data pipelines; canonical feature or signal names; train-serving parity through shared transformations; model configuration and resource requirements; evaluation reports and model repository entries; deployment modes for offline/batch, online service, and library-style serving; UUID/tag/alias-based model references for side-by-side deployment and traffic shifting; prediction logging, holdbacks, delayed labels, and live quality monitoring; and an API/UI management plane for orchestration, monitoring, and alerting.

Agent Studio implication: source-backed content routes need the same lifecycle. Source extraction, chunking, embeddings, graph transforms, reranking, prompt assembly, model/provider calls, generated artifacts, evaluations, publishing, feedback, and delayed outcome labels should be managed as linked platform objects rather than scattered scripts and notes.

## Agentic Design-Spec Automation

uSpec is relevant because it is an agentic workflow over a creative/engineering artifact. The agent does not merely generate prose. It reads a structured design source through an MCP bridge, applies domain-specific skill instructions, uses schemas and reference docs, and writes the result back into the design tool.

The durable design pattern:

- keep proprietary work local when the source surface is sensitive;
- make the connector expose structured source truth, not only screenshots;
- split domain expertise into explicit skills with validation rules and reference materials;
- use AI where interpretation matters and programmatic operations where precision matters;
- render into the operator's actual work surface instead of creating an orphan intermediate artifact;
- design for maintainability by updating generated documentation in place when source components change.

Agent Studio implication: browser, Figma, Obsidian, filesystem, social-platform, and publishing connectors should be governed MCP-style boundaries with capability snapshots and route-specific permissions. The best workflow is not "ask an agent to write a doc"; it is "let the agent inspect authoritative structured sources, validate against domain rules, and update the target artifact through a constrained tool path."

## Responsible AI Platform Governance

Uber's Responsible AI article turns governance into platform infrastructure. The core pattern is an evergreen inventory of AI systems, model cards as shared metadata, explainability linked into the model workflow, and governance checks shifted into planning and design stages instead of final release review.

Agent Studio implication:

- every production route should have a searchable route/model card, not just a Markdown note;
- governance fields should be partly machine-populated from run metadata and partly human-reviewed;
- explainability should be route-specific: feature attribution for structured models, source trace and retrieval rationale for RAG, tool/action trace for agents, and artifact lineage for media;
- governance should appear during route proposal and PRD/ERD-style design, before implementation;
- adoption work matters for old routes too: existing workflows need burndown and migration into the model/route catalog.

## Failure Modes

- Letting each agent route invent its own source ingestion, eval, deployment, and monitoring path.
- Treating MCP or browser/computer-use access as a convenience instead of a governed connector boundary.
- Generating artifact text from screenshots when structured source data is available.
- Recording model/provider names without route cards, ownership, intended use, metrics, deployment status, and review state.
- Moving governance to the end of release, where route shape and source choices are already hard to change.
- Monitoring only provider health while missing delayed product outcomes such as user edits, rejected claims, publish failures, and stale-source incidents.

## Datastore Requirements

Add or strengthen:

| Object | Purpose |
|---|---|
| `route_card_record` | Searchable route/model card with owner, purpose, model/provider, route family, deployment status, metrics, risks, governance state, and linked docs. |
| `feature_or_signal_record` | Canonical feature/signal/source input with owner, freshness, SLA, online/offline availability, transformation refs, and privacy class. |
| `online_offline_parity_check` | Evidence that ingestion/training/batch logic matches serving/query/runtime logic for the route. |
| `prediction_or_output_log` | Sampled route output with source snapshot, route version, artifact refs, delayed-label refs, and monitoring eligibility. |
| `delayed_outcome_join` | Join record connecting generated output/prediction to later observed user, reviewer, publishing, or business outcome. |
| `mcp_work_surface_record` | Governed local work surface exposed through MCP or equivalent connector, including capability snapshot, data boundary, and write permissions. |
| `agent_skill_instruction_record` | Versioned agent skill with domain rules, reference docs, schemas, validation checks, and allowed target surfaces. |
| `artifact_render_action` | Programmatic write/render operation into Figma, Obsidian, HTML, social draft, or publishing destination with validation and rollback refs. |
| `explainability_artifact` | Route-specific explanation evidence: feature attribution, source trace, retrieval rationale, tool trace, or media lineage. |
| `governance_adoption_record` | Burndown/adoption state for bringing existing routes into the route catalog and governance process. |

## Platform Lifecycle And Work-Surface Governance Gate

`platform_lifecycle_work_surface_gate` is the promotion gate for routes that combine production ML lifecycle objects with local or product-embedded work surfaces such as Obsidian, browser, Figma, social drafts, or publishing targets. It makes sure Agent Studio treats agent automation as a governed platform workflow rather than a one-off assistant action.

Required evidence:

- `gate_id`, `route_id`, `candidate_release_id`, `route_card_ref`, `source_datasheet_refs`, `feature_or_signal_refs`, `model_or_provider_refs`, `artifact_registry_refs`, and `deployment_alias_refs`;
- `offline_pipeline_refs`, `online_runtime_refs`, `online_offline_parity_check_refs`, `evaluation_report_refs`, `prediction_or_output_log_refs`, `holdback_or_sample_policy_ref`, `delayed_outcome_join_refs`, `monitoring_signal_refs`, and `alert_policy_refs`;
- `mcp_work_surface_refs`, `capability_snapshot_refs`, `read_scope_refs`, `write_scope_refs`, `local_execution_boundary_ref`, `credential_scope_refs`, `data_boundary_refs`, and `rollback_policy_refs`;
- `agent_skill_instruction_refs`, `domain_rule_refs`, `reference_doc_refs`, `schema_refs`, `validation_check_refs`, `template_refs`, `artifact_render_action_refs`, and `render_validation_refs`;
- `explainability_artifact_refs`, `responsible_ai_review_refs`, `governance_adoption_refs`, `legacy_route_burndown_refs`, `education_or_playbook_refs`, `owner_refs`, `decision`, and `reviewed_at`.

Do not promote a platform/work-surface route when:

- source extraction, training/eval, runtime serving, monitoring, and delayed outcomes are disconnected records;
- offline and online logic can drift without a parity check;
- output logs lack source snapshot, route version, artifact refs, sample policy, or delayed-label eligibility;
- MCP or browser/computer-use access is granted without a capability snapshot, read/write scope, credential boundary, and rollback path;
- skill instructions are not versioned with domain rules, schemas, reference docs, and validation checks;
- generated artifacts are written into a work surface without render validation and rollback evidence;
- responsible-AI inventory, route/model cards, explainability, review ownership, and adoption burndown are postponed until after implementation.

## Canon Decision

Agent Studio should build toward a governed AI platform, not a collection of clever agents. The minimum platform contract is route cards, source/feature parity, artifact registries, deployment aliases, sampled output logs, delayed outcome joins, MCP work-surface governance, skill instruction versions, explainability artifacts, and adoption tracking for old routes.
