---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_source_note
rights_status: official_public
source_urls:
  - https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale
  - https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/deploy-an-agent
  - https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/manage-deployed-agents
  - https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/manage-revisions-and-traffic
  - https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/manage-agent-access
  - https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/agent-identity
  - https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/agent-gateway-runtime-deploy
  - https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/optimize-and-scale
  - https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/tracing
  - https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/logging
  - https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/monitoring
  - https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/memory-bank
  - https://docs.cloud.google.com/gemini-enterprise-agent-platform/optimize/evaluation/agent-evaluation
---

# Google Agent Platform Managed Runtime

## Direct-Read Scope

This note is original synthesis from current official Google Cloud Gemini Enterprise Agent Platform pages. The older Vertex AI Agent Engine URLs now redirect into this Agent Platform documentation surface, so this pass records the current canonical URLs and keeps the old product name only as historical context.

Scope: Agent Runtime deployment and management, revisions and traffic splitting, access and agent identity, Agent Gateway, runtime scaling, tracing, logging, monitoring, Memory Bank, and agent evaluation.

No raw documentation text, copied code blocks, screenshots, trace payloads, or long excerpts are stored here.

Current-source check: the current Gemini Enterprise Agent Platform docs still expose immutable runtime revisions and traffic splitting as a preview/v1beta1 API surface, list versioned runtime fields that create new revisions, describe per-agent identity with certificate-bound credentials and Context-Aware Access, and call out Memory Bank risks such as memory poisoning alongside asynchronous generation and consolidation.

## Core Reading

Google's current managed-agent platform separates production agent operation into runtime, context, quality, security, and observability planes. The important Agent Studio lesson is that a deployed "agent" is not one object. It is a set of versioned surfaces: source/package/container, framework, runtime resource, revision, traffic split, identity, gateway binding, session state, memory store, telemetry, metrics, logs, and evaluation loop.

Agent Runtime supports multiple deployment shapes: in-memory agent object, source files, Dockerfile, Artifact Registry container image, and Developer Connect repository. These are not interchangeable governance paths. Interactive object deployment is useful for experimentation, while source/container/repository deployments better support reproducibility, CI/CD, infrastructure-as-code, and review. Agent Studio should store deployment source type and reproducibility evidence separately from the route's logical prompt/tool graph.

The runtime is Python-first in the current docs and supports framework-specific packaging for ADK, A2A, LangChain, LangGraph, AG2, LlamaIndex, and custom agents. Agent Studio should treat framework support as runtime capability, not as route identity. A route can be conceptually the same task while its runtime adapter changes; release records still need to preserve package pins, extra files, env vars, build scripts, framework declaration, operation schemas, and generated runtime resource IDs.

## Revisions, Traffic, And Rollout

Google's revision model is especially relevant to Agent Studio. Updates to package specs, dependency files, env/secret env, image override, server mode, PSC config, instance counts, resource limits, concurrency, class methods, framework, source-code spec, identity type, and agent-card fields create immutable revisions. Traffic can then be split across active revisions.

Agent Studio should make every production route release revision-aware:

- versioned fields should create immutable deployment revisions;
- unversioned metadata changes should be tracked without pretending the runtime behavior changed;
- traffic split, primary revision, latest revision, and deprecated revisions should be explicit rollout state;
- old revisions should be deprecated or deleted when they carry quota, error, or security risk;
- a canary should be tied to eval, trace, cost, latency, and safety evidence before promotion.

This complements KServe, Ray Serve, and Bedrock AgentCore coverage already in the vault: model serving canaries are not enough for agent releases because agent revisions include prompts, tools, identities, and gateway exposure as well as code and resources.

## Identity And Gateway

The access docs separate agent identity, service accounts, API keys, and OAuth clients. Agent identity is the most important architectural signal: a deployed agent can receive a per-agent identity tied to its lifecycle and used for least-privilege IAM. The docs also describe certificate-bound credentials and context-aware restrictions so credentials are less replayable outside the intended runtime.

Agent Studio should therefore represent identity as a first-class route surface:

- service accounts are broad execution identities and need explicit least-privilege review;
- per-agent identities are preferred when the platform supports them;
- API keys belong behind scoped tool adapters, not in prompt-visible state;
- OAuth client flows are user-delegated and need consent, token, and audit records;
- logs should be able to distinguish user identity from agent identity for delegated actions.

Agent Gateway adds a governed network/security boundary for user-to-agent, agent-to-tool, agent-to-model, API, and inter-agent traffic. The current docs mark some gateway paths as preview/private-preview and impose project/region limits. Agent Studio should record gateway maturity, mode, region, policy set, Model Armor binding, IAP/authorization policy, egress/ingress mode, and whether a gateway binding can be removed.

## Sessions And Memory

Sessions are the chronological interaction state for a user-agent interaction. Memory Bank is the longer-lived personalization layer. It generates, consolidates, stores, retrieves, and revises scoped memories from session events, direct events, or pre-extracted facts. It can run asynchronously, ingest events continuously, use custom extraction topics/examples, isolate by identity scope, and retrieve through exact scope or similarity search.

Agent Studio should not collapse sessions and memories into chat history:

- sessions are source-of-truth event streams for a conversation;
- memories are derived facts with scope, extraction policy, consolidation policy, retrieval policy, revision history, and privacy implications;
- memory generation is a long-running background operation and must have completion status and failure handling;
- multimodal memory extraction creates textual memory from media, so media provenance and consent still matter;
- explicit remember/forget instructions require separate policy records, not only prompt handling.
- memory generation needs safety review because long-term memory can be poisoned by session content, tool output, or user/agent misunderstanding.

## Scaling And Observability

Agent Runtime exposes deployment controls such as minimum instances, maximum instances, CPU, memory, and container concurrency. Google calls out cold starts and underutilized async workers as common bottlenecks. Agent Studio should preserve route-level baseline traffic assumptions, spike profile, min-instance choice, concurrency policy, async-worker posture, warmup/load-test evidence, and cost tradeoff.

Tracing, logging, and monitoring are separate controls:

- tracing uses Cloud Trace/OpenTelemetry concepts with spans for requests, model calls, and tool/function work;
- message-content capture is a separate privacy-sensitive switch from telemetry itself;
- logging supports stdout/stderr, Python logging, or Cloud Logging client approaches, with structured logs preferred for correlation;
- Cloud Logging does not cover every subresource, so sessions, memory, code execution, and example-store surfaces need explicit telemetry plans;
- monitoring has built-in request, latency, CPU allocation, and memory allocation metrics for the runtime resource and can be extended with custom metrics and alerts.

For Agent Studio, observability should be per runtime resource and per route release. A release without trace, log, metric, redaction, sampling, and alert policy is not production-ready even if the agent answers correctly in a notebook.

## Evaluation Loop

Google's agent evaluation workflow frames evaluation as an iterative loop: define eval cases, run inferences, capture traces, compute metrics with raters, and refine instructions or tools. Eval cases can include multi-turn tasks, state, and simulated users; traces are immutable behavior records covering model inputs, responses, and tool calls.

Agent Studio should tie this to route promotion:

- eval cases should specify task, context/state, allowed tools, expected outcome, and forbidden behavior;
- simulated users are useful for multi-turn paths but must be versioned and audited;
- trace-based scoring should cover task success, safety, tool use, latency, and cost;
- prompt/tool optimization proposals must be verified against regression suites before traffic promotion;
- online monitors and quality alerts should backfill failing traces into eval datasets.

## Canon Cross-Check

AWS AgentCore and Google Agent Platform agree on the main architecture: managed agents are runtime resources, not merely model endpoints. This Google source is canon for revision/traffic-split behavior, deployment-source reproducibility, framework packaging, per-agent identity, Memory Bank, runtime telemetry, and trace-based eval loops.

The AWS source contributes policy, payments, browser/code resources, and service-role review details. The Google source contributes stronger rollout and identity specifics: versioned fields create immutable revisions; active revisions may receive traffic or be deprecated; old revisions can become quota, error, or security risk; per-agent identity can be bound to the intended runtime environment.

The privacy note owns data-use, retention, deletion/export, and provider boundaries. This note owns the operational records that make sessions and memories governable: event streams, generation operations, scoped memory stores, memory revisions, retrieval mode, identity isolation, and memory safety review.

The eval canon owns release decisions. This note supplies managed-agent evaluation evidence: multi-turn eval cases, simulated-user policies, immutable traces, raters/metrics, failure clusters, online monitors, quality alerts, and prompt/tool optimization feedback.

## Agent Studio Datastore Additions

- `google_agent_runtime_resource`: managed Agent Platform runtime resource with project, location, resource ID, deployment source type, framework, operation schemas, and lifecycle state.
- `agent_runtime_deployment_source`: agent object, source files, Dockerfile, Artifact Registry image, or Developer Connect source with reproducibility, CI/CD, IaC, and review evidence.
- `agent_runtime_package_spec`: package pins, dependency artifacts, extra packages, Python version, source-code spec, build scripts, and environment-variable policy.
- `agent_runtime_revision`: immutable runtime revision with versioned field hashes, active/deprecated state, created time, source refs, and release refs.
- `agent_runtime_traffic_split`: manual/latest split mode, revision percentages, primary revision, canary state, promotion gate refs, and rollback target.
- `agent_runtime_identity`: service-account, per-agent identity, API-key, or OAuth-client mode with scope, consent/audit refs, replay-resistance posture, and review state.
- `agent_gateway_binding`: ingress or egress gateway binding with project/region, gateway mode, policy refs, Model Armor/IAP refs, limitations, and removal caveats.
- `agent_session_record`: chronological conversation event stream with user, agent, state, event refs, retention, and access policy.
- `agent_memory_bank_record`: scoped long-term memory store with extraction topics, consolidation policy, revision policy, retrieval mode, identity isolation, and privacy review.
- `memory_generation_operation`: background memory extraction/consolidation operation with source event refs, scope, operation status, generated-memory refs, and failure handling.
- `memory_safety_review`: poisoning risk, source-event trust class, remember/forget policy, identity scope, privacy review, reviewer override, and rollback/revision refs.
- `agent_runtime_scaling_profile`: min/max instances, CPU, memory, container concurrency, async-worker posture, baseline traffic, spike profile, warmup policy, and load-test evidence.
- `agent_runtime_trace_config`: telemetry enabled, content capture enabled, span surfaces, trace exporter, sampling, redaction, and retention policy.
- `agent_runtime_log_config`: log method, log IDs/resource type, structured payload policy, trace correlation, sensitive-field policy, and subresource coverage gap.
- `agent_runtime_metric_alert`: request, latency, CPU, memory, custom metric, PromQL/query, alert threshold, owner, and incident policy.
- `agent_eval_case`: multi-turn task, state/context, simulated-user policy, expected outcome, forbidden behavior, allowed tools, and risk tags.
- `agent_eval_trace_score`: trace ref, rater, metric, score, failure cluster, refinement proposal, regression impact, and promotion decision.

## Design Commitments

- Treat managed agent runtime as a release plane that contains source/package/runtime/revision/traffic/identity/gateway/session/memory/telemetry/eval records, not as a single endpoint URL.
- Prefer reproducible source/container/repository deployments for production route releases; object deployment remains an experimental path unless snapshotted.
- Make revisions and traffic splitting first-class rollout records for agent routes, not only model endpoints.
- Use per-agent identity when available; service-account/API-key/OAuth paths need separate least-privilege, consent, and audit evidence.
- Keep session events, long-term memories, and prompt context separate.
- Require trace/log/metric/redaction/sampling policy before production promotion.
- Use trace-based multi-turn evals and online monitors as the feedback loop for prompt, tool, and route changes.
- Treat managed-agent memory as a derived, reviewable artifact. It should have source events, generation operation status, safety review, privacy review, revision history, and rollback before it affects future sessions.
