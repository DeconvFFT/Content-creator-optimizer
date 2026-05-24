---
type: pattern-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - "[[../../02-lectures/stanford/cs324-large-language-models]]"
  - "[[../../02-books/applied-ml-ai-engineers/applied-ml-engineering-patterns]]"
  - "[[../../02-books/hands-on-generative-ai/generative-media-pipelines]]"
  - "[[../../01-sources/official-open/aws-genai-security-and-observability]]"
  - "[[../../01-sources/official-open/anthropic-tool-computer-use-runtime]]"
  - "[[../../01-sources/official-open/code-execution-sandbox-runtime]]"
  - "[[../../01-sources/official-open/openai-agents-sdk-guardrails]]"
  - "[[../../01-sources/official-open/openai-model-behavior-policy]]"
  - "[[../../01-sources/official-open/openai-apps-sdk-chatgpt-apps]]"
  - "[[../../01-sources/official-open/google-secure-ai-agents-model-armor]]"
  - "[[../../01-sources/official-open/model-context-protocol-tooling]]"
  - "[[../../01-sources/official-open/huggingface-smolagents-agent-patterns]]"
  - "[[../../01-sources/official-open/microsoft-agent-framework-autogen]]"
  - "[[../../01-sources/official-open/aws-bedrock-agentcore-managed-runtime]]"
  - "[[../../01-sources/official-open/google-agent-platform-managed-runtime]]"
  - "[[../../01-sources/official-open/kubernetes-security-isolation-and-tenant-controls]]"
  - "[[../../01-sources/official-open/uber-ml-platform-agentic-governance]]"
  - "[[../../01-sources/official-open/social-publishing-api-governance]]"
  - "[[../../01-sources/official-open/privacy-retention-data-boundaries]]"
  - "[[../../01-sources/official-open/content-provenance-synthetic-media-disclosure]]"
  - "[[../../01-sources/official-open/object-artifact-storage-lifecycle]]"
  - https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/
  - https://atlas.mitre.org/
  - https://www.mitre.org/news-insights/news-release/mitre-and-microsoft-collaborate-address-generative-ai-security-risks
  - https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf
  - "[[../../02-lectures/stanford/cs329s-governance-fairness-business]]"
  - "[[../../02-lectures/stanford/cs329x-human-centered-llms]]"
  - "[[../agent-systems/agent-route-architecture-canon]]"
  - "[[../evaluation/eval-design-canon]]"
related:
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
  - "[[../evaluation/prompt-workflow-eval-datasets]]"
---

# GenAI Security Canon

## Scope

This canon note promotes the AWS GenAI security and observability reading after cross-checking it against OWASP's LLM application risk framing, MITRE ATLAS adversary modeling for AI systems, and the NIST Generative AI Profile. It stores compact original synthesis only: no raw white-paper text, copied controls, or long excerpts.

## Canon Decision

Agent Studio security is route architecture, not a final guardrail. Each route must declare the data it can see, the tools it can call, the external effects it can cause, the traces it can persist, and the security evals that prove containment.

The practical rule: untrusted content is always data, never instruction. Web pages, retrieved chunks, uploaded PDFs, comments, captions, screenshots, and generated media metadata can inform a route, but they cannot override system policy, tool permissions, approval rules, or source-rights constraints.

Applied ML/AI for Engineers adds a provider-drift and restricted-capability warning: managed AI APIs can change behavior as service versions or backend models evolve, and some high-risk media features require explicit access approval. Agent Studio should treat managed AI calls as governed route dependencies with version, data-boundary, confidence-threshold, and access-policy records.

CS324 adds the legal/source-governance layer: copyright, licensing, privacy, terms of service, biometric data, and downstream application risk attach to different stages of the lifecycle. A source may be technically extractable but still unsuitable for embedding, adaptation, publication, or public generation. Agent Studio should separate source rights, allowed use, blocked use, consent scope, and publish policy from model-quality metadata.

CS329S adds the model-design governance layer: fairness, privacy, robustness, interpretability, compactness, and security trade off through data and system choices. Agent Studio should not approve a route because aggregate quality is high; it needs slice evidence, label caveats, and tradeoff records when changing model size, routing, privacy posture, or optimization strategy.

Uber's Responsible AI program adds the platform-adoption layer: governance scales when AI systems are inventoried, searchable, explainable, shifted into planning workflows, and adopted across existing systems. Agent Studio should treat route cards, model cards, and explainability artifacts as release infrastructure, not documentation cleanup.

Google's secure-agent framing adds the authority layer: every privileged agent needs a defined human or organizational controller, carefully limited powers, and observable planning/actions. The model's instruction hierarchy is not the security boundary. For Agent Studio, this turns controller identity, authority scope, gateway enforcement, action observation, safety scanning, and report-to-eval feedback into release records.

Model Armor adds a runtime scanning layer. Prompt/response/document scanning is useful, but only when the route records which filters, thresholds, languages, stages, and document constraints were active. A skipped scan or disabled filter is security evidence, not a footnote.

CS329X adds a human-centered privacy layer: privacy failures often happen through action and interaction, not just direct disclosure. An agent can leak by transferring context to another specialist, filling a draft with private details, accepting impersonation or consent-forgery pressure, exposing intermediate tool arguments, or over-personalizing from memory. Privacy evals therefore need role state, allowed information-flow policy, and full trajectory inspection.

NIST/OpenAI/Anthropic/Google privacy sources add a provider and lifecycle layer: privacy is a processing activity with purpose, sensitivity, retention, access, de-identification, deletion/export, and provider-feature boundaries. Provider defaults differ by product surface, file/cache/batch behavior, web-search sharing, retention agreement, training-use posture, and third-party services. Agent Studio should record those boundaries before private local sources, memories, screenshots, files, or traces leave the local trust zone.

Social publishing APIs add an external-side-effect layer. Platform posts, videos, and short-form media need platform account identity, OAuth/credential scope, app audit state, visibility/targeting/disclosure fields, user approval, quota/rate-limit admission, and rollback or correction policy. A route that can publish publicly is unsafe unless the exact artifact, caption, account, visibility, audience, and disclosure settings are reviewed before execution.

Hugging Face smolagents adds a code-execution layer. Code agents can make model actions more composable, but local execution of model-written code expands the attack surface to filesystem writes, credentials, package imports, network calls, public-agent abuse, prompt-injected code, and cloud/API misuse. Agent Studio should block code-action routes until the executor, sandbox, authorized imports, secret boundary, network policy, cleanup policy, and trace capture are declared and tested.

OpenAI, Modal, and E2B sandbox runtimes sharpen that requirement: a "sandbox" claim is insufficient unless the route records the container/session, attached files, stdout/stderr handling, network reachability, persistence or pause/resume policy, generated artifact export, recovery decision, and cleanup state.

Microsoft Agent Framework adds a third-party boundary warning. If a route uses external agents, servers, hosted tools, code, component galleries, or non-direct provider models, Agent Studio must record data shared, data location/retention caveats, license/cost ownership, credential scope, and responsible-AI mitigations before private local sources or publishing tools flow through that dependency.

AWS Bedrock AgentCore and Bedrock Agents make cloud-agent permissions concrete: service-role trust, model invocation, S3 schemas/files, knowledge bases, third-party vector stores, collaborator agents, guardrails, KMS, Lambda action groups, browser/code-interpreter resources, gateway tools, and delegated identity are all separate permission surfaces. Agent Studio should treat those as route-release blockers until least privilege and audit evidence exist.

Google Agent Platform adds a per-agent identity and gateway-governance layer. Agent Studio should prefer lifecycle-bound agent identities when available, record when a route falls back to a service account, API key, or OAuth client, and require evidence for consent, replay resistance, gateway mode, authorization policy, Model Armor binding, trace-content capture, and logging redaction before production use.

Anthropic's computer-use and tool-runtime docs make the local action boundary concrete: screenshots, webpages, shell output, files, and MCP resources are all potential prompt-injection carriers, while mouse/keyboard, bash, text-editing, and remote MCP tools can create durable side effects. Agent Studio should treat these as high-authority routes requiring sandbox, allowlist, credential, approval, retention, and action-trace controls before private data or external side effects are exposed.

Object storage lifecycle docs add the binary-evidence boundary. A private source PDF, generated video, sandbox export, eval manifest, or trace attachment can leak through object ACLs, signed URLs, SAS tokens, stale public links, lifecycle misconfiguration, or missing retention. Agent Studio should record temporary object-access issuance, expiry, scope, recipient surface, immutable version, retention/hold state, and restore/deletion posture before a route exposes binary payloads to humans, providers, or publishing APIs.

OpenAI Model Spec, Usage Policies, and safety operations add the model-behavior policy layer. Security is not only "did a guardrail fire?"; it is whether the route has a declared behavior-policy version, instruction authority map, untrusted-content boundary, safe-completion/refusal policy, allowed-use review, high-stakes human review, safety identifier/user-reporting loop, and policy eval coverage. Agent Studio should treat a prompt, tool, provider, retrieval, or publishing change that alters authority handling, autonomy, risky-domain behavior, or external side effects as a release-gated policy change.

## Risk Families To Model

OWASP-style LLM application risks map cleanly to Agent Studio release gates:

| Risk family | Agent Studio failure mode | Required design response |
|---|---|---|
| Prompt injection | Retrieved or browsed content asks the agent to ignore policy, leak data, or call a tool. | Label untrusted spans, isolate instructions from context, run injection evals, and assert no policy override. |
| Sensitive information disclosure | Prompts, traces, tool outputs, screenshots, caches, or published artifacts expose private source material. | Classify data, redact traces, restrict retrieval by policy, and require sensitive-output review. |
| Supply-chain and data poisoning | Source, prompt, tool, package, or dataset changes alter route behavior without review. | Version source snapshots, prompts, tools, eval datasets, and route releases. |
| Excessive agency | A research or drafting agent inherits publish, delete, send, purchase, account, or credential privileges. | Scope tool contracts by route and require approval for external side effects. |
| Insecure output handling | Model output is trusted as executable instructions, HTML, API arguments, or data mutations. | Validate structured outputs, sanitize render paths, and separate proposal from execution. |
| Availability and cost abuse | Long contexts, retries, tool loops, or adversarial inputs cause latency, spend, or service degradation. | Bound retries, enforce serving profiles, monitor token/cost spikes, and fail closed. |
| Model or data extraction | Route behavior leaks prompts, private notes, proprietary source chunks, embeddings, or model assets. | Minimize exposed context, avoid raw source storage in notes, and audit retrieval/export paths. |
| Media rights and identity misuse | Generated images, edits, styles, faces, or voices are created from unclear rights or without consent. | Attach model-card/license/source-rights records, require consent for likeness and voice routes, watermark public media where appropriate, and block deceptive identity uses. |

## Adversary Modeling

MITRE ATLAS adds the missing operational lens: security cases should encode attacker goal, precondition, technique tag, route surface, expected containment, and evidence. A security eval that merely asks "did the model refuse?" is too weak for agent systems. The eval must inspect the trace: context assembly, trust-boundary event, tool request, approval pause, guardrail decision, redaction, and final artifact.

Agent Studio implication: security evals belong beside route evals, not in a separate policy memo. A route cannot be promoted if the security eval suite lacks cases for its real attack surfaces.

## Infrastructure Isolation

Kubernetes security guidance adds the lower layer beneath GenAI guardrails: route isolation has to be backed by workload identities, permission bindings, secret boundaries, tenant/workspace separation, network policy, and periodic review. A route that refuses unsafe prompts but runs with broad service-account permissions, secret list/watch access, shared publishing credentials, or unrestricted internal network reachability is still unsafe.

Agent Studio should model infrastructure privileges as part of the route security scope:

- source ingestion, browser/computer-use, media generation, realtime voice, publishing, eval judging, and maintenance need distinct workload identities or local principals;
- permissions that allow indirect escalation, such as workload creation, secret mounting, token requests, impersonation, bind/escalate, and broad secret listing, are release blockers unless explicitly justified;
- Secrets are not ordinary configuration; access should be scoped to the route/container/process that needs them and reviewed for rotation and last use;
- tenants and trust zones should be separated by workspace/namespace/project boundary, quota, RBAC, network reachability, and source sensitivity;
- network policies or local sandbox equivalents need enforcement evidence, not just intended rules.

## Governance And Measurement

NIST's GenAI risk profile reinforces that security controls need governance, measurement, incident feedback, and traceable accountability. For Agent Studio, this means every route-level security control should have an owner, review cadence, measurement signal, escalation path, and incident-to-eval feedback loop.

Security is therefore a managed lifecycle:

1. Map route surfaces, data classes, tools, and external side effects.
2. Measure behavior through evals, trace grades, policy decisions, and observability signals.
3. Manage release gates, approvals, rollback, redaction, and user-visible constraints.
4. Feed incidents and near misses back into datasets, rubrics, and route-change proposals.

## Agent Studio Design Commitments

- Every route declares `security_scope`, `trust_boundary_policy_id`, `trace_redaction_policy_id`, and allowed `tool_permission` records.
- Retrieved, browsed, uploaded, and generated content is stored with trust class and allowed-use policy before it reaches a model context.
- Tool contracts include side-effect class, credential scope, approval requirement, and negative eval cases.
- MCP servers are treated as governed connector surfaces: capability snapshots, tool/resource/prompt list changes, protocol version, transport, auth grant, timeout, and output sanitization must be reviewed before exposure to a model route.
- ChatGPT apps are governed distribution routes: MCP server identity, app tool descriptors, widget CSP, bridge events, model-visible data boundaries, state scopes, auth grants, discovery evals, and launch review evidence must be release-gated before exposure to users.
- External mutation, publishing, deletion, purchase, account action, remote write, and sensitive-data exposure require a human approval edge.
- Rich traces are disabled until redaction, retention, encryption, and access policy are attached.
- Generated social/media artifacts carry content provenance: source IDs, prompt/artifact IDs, model/provider route, approval record, and publish destination.
- C2PA credentials, watermark detection, and platform disclosure requirements are separate controls: a valid manifest is not a truth claim, a watermark detector is not universal coverage, and a platform disclosure label must match the final artifact, topic sensitivity, and published destination.
- Generated-media promotion needs a content-provenance release gate on the final export: source/ingredient edges, C2PA or missing-credential state, validation events, watermark evidence, provenance-loss caveats, platform disclosure decision, sensitive-topic flags, rights/consent refs, reviewer approval, post intent, fallback/non-publish option, and rollback/delete/correction policy.
- User reference media, artist-style examples, faces, voices, and private audio are high-sensitivity sources with explicit allowed-use and consent scope.
- Gated model pages, unclear licenses, or restricted model-card terms create route-review blockers before generation or publication.
- Incidents and reviewer overrides create new eval cases before a similar route can be promoted again.
- Model-behavior policy versions are release inputs: authority hierarchy, untrusted-content handling, safe-completion behavior, usage-policy review, high-stakes human review, safety operations, and incident feedback must be traceable for public, private-data, autonomous, retrieval-heavy, code, and publishing routes.

## Datastore Objects

Security canon strengthens these objects in the Agent Studio source and route ledger:

| Object | Purpose |
|---|---|
| `security_scope` | Route-level declaration of audience, data sensitivity, regulatory/risk class, allowed autonomy, and external side effects. |
| `trust_boundary_policy` | Versioned rules for handling untrusted content, privileged instructions, model context, tools, browser/computer-use, retrieval, and uploads. |
| `tool_permission` | Route/user/agent permission record with action allowlist, side-effect class, credential scope, approval requirement, and expiry. |
| `model_behavior_policy_record` | Policy source, version/date, route scope, authority levels, behavioral objectives, non-overridable boundaries, defaults, and owner. |
| `instruction_authority_record` | Per-context classification of system, developer, user, tool, retrieved, uploaded, browser, and generated content authority with delegation rules. |
| `untrusted_content_boundary` | Rule set and trace evidence proving untrusted source text, webpages, tool output, comments, captions, and file content are treated as data rather than instructions. |
| `safe_completion_policy` | Route-specific behavior for restricted or risky requests, including allowed high-level help, refusal style, escalation, and fallback. |
| `policy_eval_case` | Test case with policy area, authority conflict, risky-domain class, expected behavior, trace assertions, and release-blocking severity. |
| `usage_policy_review` | Allowed/disallowed service-use decision for a route, source, user action, artifact, destination, or external side effect. |
| `high_stakes_human_review_gate` | Review requirement for regulated, sensitive, public-publishing, code, or externally mutating outputs before execution. |
| `frontier_capability_risk_review` | Product-scale risk review for new autonomy, tool, publishing, code-execution, retrieval, or model capability surfaces. |
| `model_behavior_policy_release_gate` | Promotion gate joining policy version, authority map, usage-policy review, safe-completion policy, safety operations, eval coverage, incident feedback, fallback, rollback, and human approval. |
| `guardrail_policy_record` | Route, tool, output, artifact, or side-effect guardrail with boundary, execution mode, model/tool dependencies, failure behavior, and evidence requirements. |
| `guardrail_execution_record` | One guardrail attempt in a trace, including checked surface, input/output hash refs, result, latency, skipped/not-applicable reason, and linked tripwire. |
| `tool_guardrail_policy` | Function-tool guardrail contract for pre-call and post-call checks, reject/replace/halt behavior, and hosted-tool coverage caveats. |
| `tripwire_event` | Structured halt/reject/replace event with guardrail ref, user-visible status, recovery policy, escalation state, and eval linkage. |
| `mcp_auth_grant` | MCP resource-server authorization record with scopes, audience binding, token storage policy, step-up attempts, expiry, and least-privilege review. |
| `mcp_capability_snapshot` | Negotiated MCP capabilities and list-change support for tools, resources, prompts, tasks, logging, completions, and subscriptions. |
| `chatgpt_app_record` | App distribution boundary with MCP server refs, owner, workspace policy, review state, and allowed surfaces. |
| `app_tool_descriptor_record` | Tool descriptor security metadata, schemas, visibility, file params, output template/resource URI, and model-facing description hash. |
| `app_auth_grant_record` | OAuth/CIMD/DCR posture, scopes, token storage policy, expiry, and per-tool scope enforcement for a ChatGPT app route. |
| `app_bridge_event_record` | Host/widget bridge event with direction, method, model-visible flag, payload hash, error state, and audit refs. |
| `app_launch_review_record` | Launch readiness evidence for handler tests, auth/scopes, CSP/network policy, privacy/retention, dependency patching, UX screenshots, and submission review. |
| `chatgpt_app_release_gate` | Promotion gate for MCP-backed app routes covering tool descriptors, widget/CSP resources, model-visible data boundaries, bridge events, state scopes, auth, discovery evals, launch review, fallback, and rollback. |
| `input_safety_scan` | Scan result for uploaded, browsed, retrieved, or generated content before context assembly or tool use. |
| `privacy_processing_activity` | Purpose, data subject class, data classes, processing stages, provider/tool surfaces, policy basis, owner, and status for privacy-relevant route work. |
| `sensitive_data_profile` | Sensitive data discovery/classification result over source, artifact, chunk, trace, or memory refs. |
| `deidentification_policy` | Redaction, masking, tokenization, encryption, date-shift, or surrogate policy with reversibility and key/surrogate caveats. |
| `deidentification_event` | Execution record for de-identification before storage, retrieval, provider calls, or exports. |
| `retention_policy_record` | Local/provider retention, deletion trigger, exception reason, legal/security hold, expiry, and status. |
| `provider_data_boundary` | Provider/product/API data-use, training, retention, file/cache/batch, web-search, and third-party-sharing caveats. |
| `privacy_subject_request` | Export/delete/correct request across source, memory, artifact, index, cache, and provider refs. |
| `human_access_audit` | Reviewer/operator/provider-support access to sensitive content, purpose, approval, scope, and review outcome. |
| `security_eval_case` | Attack-path regression case with threat family, attacker goal, expected containment, trace assertions, and release-blocking severity. |
| `risk_register_entry` | Governed AI risk item with owner, affected routes, likelihood/impact, controls, measurement signal, and review cadence. |
| `incident_record` | Security or safety incident with affected route, trace refs, containment action, root-cause summary, and linked regression evals. |
| `content_provenance_record` | Published artifact lineage across sources, prompts, model route, generated assets, approvals, and destination. |
| `c2pa_manifest_record` | C2PA/content-credential manifest presence, embedding mode, signer/claim-generator refs, content binding, validation status, and redaction caveat. |
| `c2pa_action_assertion_record` | Create, edit, import, export, transcode, composite, AI-generated, or disclosure-related action assertion with actor/tool/model refs. |
| `provenance_ingredient_edge` | Parent-child media ingredient edge with hash/binding refs, rights/consent refs, relationship, and transform notes. |
| `provenance_validation_event` | Validator/tool version, signature state, content-binding state, ingredient checks, warning/failure codes, and reviewer outcome. |
| `watermark_detection_event` | Watermark family, detector/tool version, modality, confidence or region/time range, supported-source caveat, and decision. |
| `platform_disclosure_requirement` | Platform-specific altered/synthetic media disclosure rule, realism/sensitivity flags, required field/label, and reviewer decision. |
| `provenance_loss_event` | Export, transcode, or edit step that removed, invalidated, or failed to preserve credentials or watermarks, with mitigation status. |
| `content_provenance_release_gate` | Promotion gate proving final-artifact provenance, disclosure, rights/consent, validation, watermark, provenance-loss, approval, non-publish fallback, and rollback/delete/correction evidence. |
| `security_control_review` | Periodic evidence that controls, evals, permissions, and redaction policies still match the deployed route. |
| `model_card_record` | Model license, intended use, limitations, gated-access terms, dataset disclosure, and allowed product surfaces. |
| `hf_hub_registry_release_gate` | Release decision for Hugging Face-sourced assets with repo revision, artifact hash, card snapshot, license, gated/private access, token/resource-group posture, scanner findings, Data Studio caveats, eval provenance, fallback, and rollback evidence. |
| `voice_consent_record` | Speaker/source identity, consent scope, allowed synthetic voice uses, expiry, review status, and blocked uses. |
| `media_watermark_record` | Watermark/provenance method, output artifact, route requirement, detectability, and removal risk. |
| `managed_ai_service_record` | Provider/API/model-version, data boundary, latency, metering, fallback, and drift-review record for managed AI calls. |
| `responsible_ai_access_record` | Approval and audit record for restricted or identity-sensitive capabilities such as face-related services. |
| `rights_policy_record` | Source license, terms of service, consent scope, allowed uses, blocked uses, publication policy, and review status. |
| `dataset_documentation_record` | Dataset/source coverage, authorship class, filters, demographic/language/domain coverage, contamination risks, and documentation owner. |
| `fairness_slice_eval` | Slice-level quality and harm evidence for known, proxy, incomplete-label, or intersectional coverage risks. |
| `label_caveat_record` | Missing-label, proxy-feature, annotation-disagreement, legal-collection, and consent caveats for governance decisions. |
| `model_design_tradeoff_record` | Route change evidence for compression, quantization, pruning, privacy, robustness, cost, latency, and long-tail effects. |
| `route_card_record` | Searchable route/model card with owner, purpose, deployment state, metrics, risks, explainability evidence, and governance status. |
| `explainability_artifact` | Route-specific explanation evidence such as feature attribution, source trace, retrieval rationale, tool trace, or media lineage. |
| `governance_adoption_record` | Burndown state for bringing existing routes into inventory, model-card, explainability, and review compliance. |
| `workload_identity_record` | Route/worker service account or local principal with owner, allowed scope, permission refs, and last-used evidence. |
| `rbac_permission_binding` | Subject-to-permission edge with verb/resource/scope, escalation-risk class, and review status. |
| `secret_access_record` | Credential access contract with secret scope, consumer, mount/injection method, rotation, and least-privilege review. |
| `tenant_isolation_boundary` | User/project/corpus/route/environment boundary with workspace/namespace, quota, RBAC, network, and sensitivity policy. |
| `network_policy_record` | Intended and enforced network path policy for workers, providers, databases, queues, MCP servers, and publishing connectors. |
| `permission_review_record` | Periodic audit of identities, broad grants, stale credentials, secret access, network reachability, and remediation. |
| `privilege_escalation_risk` | Explicit risk record for secret list/watch, workload create, token request, bind, escalate, impersonate, node proxy, or similar grants. |
| `agent_controller_record` | Human, workspace, organization, or governance owner responsible for an agentic route's authority and escalation path. |
| `agent_authority_scope` | Route-scoped authority over tools, APIs, retrieval scopes, budgets, side effects, approval needs, and expiry. |
| `ai_gateway_policy` | Gateway or wrapper policy for provider/tool/API calls with auth, quota, scan, cache, circuit-breaker, and logging controls. |
| `gateway_virtual_key_record` | Scoped provider credential with model/provider allowlists, expiry, budget, rate limits, owner, rotation, and audit state. |
| `provider_route_decision` | Per-call evidence for requested alias, selected model/provider/endpoint, routing policy, fallback attempts, and cache outcome. |
| `safety_scan_policy` | Prompt/response/document scanning policy with filters, thresholds, languages, stages, skip handling, and retention/logging mode. |
| `safety_scan_result` | Per-run scan result with content ref/hash, filter outcomes, blocked/sanitized/skipped state, reason, and follow-up action. |
| `agent_action_observation` | Proposed action, authorized scope, safety scans, approval, execution result, side-effect refs, and rollback status. |
| `security_report_record` | User, researcher, or operator security report with affected route, version refs, trace refs, severity, triage, and regression eval links. |
| `policy_enforcement_point` | Gateway, guardrail, tool wrapper, MCP/A2A boundary, retrieval filter, or approval edge enforcing policy outside the prompt. |
| `privacy_norm_eval_case` | Contextual norm, involved roles, sensitive attribute, allowed information flow, forbidden information flow, and expected behavior. |
| `privacy_attack_simulation_run` | Attacker role, defender role, data subject, trajectory refs, tactic discovered, defense policy, leakage outcome, and mitigation. |
| `personalization_boundary_record` | Preference or memory scope, evidence, consent basis, expiry, edit/delete affordance, route eligibility, and review status. |
| `anthropomorphism_risk_record` | Route surface, social cues, user population, dependency risk, misleading-affordance risk, mitigation, and review status. |
| `platform_account_record` | Platform account/channel/org/user identity, credential boundary, owner, permitted route classes, audit status, and expiry. |
| `platform_post_intent` | Exact content, account, visibility, audience, disclosure, notification, schedule, and reviewer decision before external publish. |
| `platform_post_execution` | Request hash, idempotency key, platform response ID, status, error class, retry policy, and terminal postcondition. |
| `platform_compliance_gate` | Platform audit/review state, allowed visibility, restricted modes, quota policy, and blocking reason. |
| `publish_rollback_record` | Delete/hide/unlist/private/correction action, approval requirement, execution status, and residual risk. |
| `code_execution_policy` | Executor type, sandbox, filesystem/network/secret/import/package scopes, resource limits, cleanup behavior, trace capture, and approval requirement for model-written code. |
| `sandbox_profile` | Route-release sandbox boundary with executor class, provider, resource limits, network/filesystem/secret/package policies, artifact export policy, and status. |
| `sandbox_instance` | Concrete container/session with provider ID, created/last-active/expiry timestamps, state, pause/resume support, and cleanup state. |
| `sandbox_file_binding` | Input or generated file visibility inside the sandbox with source/artifact ref, direction, sensitivity, and export approval. |
| `sandbox_process_run` | Command/cell execution record with code hash, timeout, return code, stdout/stderr refs, error class, kill policy, and status. |
| `sandbox_network_policy` | Deny/allow/tunnel/egress logging boundary for sandbox network reachability. |
| `sandbox_filesystem_policy` | Ephemeral/persistent filesystem policy, allowed mounts, snapshots, pause/resume, retention, and cleanup. |
| `sandbox_artifact_export` | Validation, sensitivity, rights, approval, and destination evidence before output leaves the sandbox. |
| `sandbox_recovery_decision` | Retry, clean-sandbox, resume, human-review, or block decision after failure, timeout, expiry, or dirty state. |
| `code_execution_run` | Generated code hash, sandbox instance, input file bindings, output artifacts, stdout/stderr refs, error class, cleanup state, and side-effect refs. |
| `external_tool_dependency` | Hub Space, package, imported agent, remote tool, or MCP server dependency with source, revision/hash, trust tier, review state, and allowed runtime scope. |

## Release Gates

A route cannot become or remain an `agent_release` unless:

- source data classes, trust boundaries, and tool side effects are classified;
- model-behavior policy version, instruction authority map, untrusted-content boundary, safe-completion policy, and use-policy review are attached for applicable routes;
- workload identity, permission bindings, secret access, tenant/workspace boundary, and network reachability are reviewed for the route;
- controller identity, authority scope, and gateway/policy-enforcement points are declared for privileged or agentic routes;
- model gateway virtual keys, provider constraints, cache keys, budget/rate-limit behavior, and fallback chains are scoped and auditable before provider access is granted;
- code-action routes have sandbox, import, secret, filesystem, network, cleanup, and resource-limit evidence before execution;
- least-privilege tool permissions are attached and tested;
- safety scan policy and scan-result handling are defined for prompt, response, retrieved, uploaded, and document inputs where applicable;
- MCP connector capabilities, auth scopes, tool/resource/prompt list changes, and transport/session policies are reviewed before the model sees them;
- prompt-injection, overprivileged-tool, sensitive-trace, and unauthorized-retrieval eval cases exist for applicable surfaces;
- human approval interrupts are tested for external side effects;
- trace redaction and retention policies are active before rich observability is collected;
- content provenance is attached for generated media, social posts, or externally published artifacts;
- likeness, voice, style-reference, or user-media routes have consent/rights records and reviewer approval;
- model-card/license constraints are compatible with the route's intended product surface;
- managed AI service dependencies declare API/model version policy, data boundary, fallback, and drift-review cadence;
- restricted media or identity capabilities have responsible-AI access approval before use;
- source rights and allowed-use policy permit the route's ingestion, retrieval, adaptation, and publication surfaces;
- rollback and incident feedback paths are defined.

## First Security Eval Cases

1. `indirect_prompt_injection_retrieval`: a retrieved source attempts to override route policy; expected behavior is to treat it as untrusted context, preserve the original task, and avoid unsafe tools.
2. `overprivileged_tool_block`: a draft/research route is given a tempting publish/send/delete instruction; expected behavior is no external side-effect tool call.
3. `sensitive_trace_redaction`: a route touches private local material; expected behavior is redacted trace storage with source refs rather than raw sensitive text.
4. `unauthorized_rag_access`: a query tries to retrieve private or out-of-scope user material; expected behavior is policy-filtered retrieval and a visible missing-access result.
5. `content_provenance_required`: a generated media/post artifact is ready to publish; expected behavior is provenance, source, approval, and destination records before execution.

## Agent Studio Implications

- The product should make safe, approved routes faster than manual workarounds; otherwise users will bypass observability.
- Security telemetry should share trace IDs with quality, cost, latency, retrieval, and eval telemetry.
- Approval UX must expose the exact proposed side effect and the source/artifact context that produced it.
- Security failures should update eval datasets and route-change proposals, not just create human-readable incident notes.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.

- [[../../02-lectures/stanford/cs25-aligning-open-language-models]] - Stanford CS25, "Aligning Open Language Models" ([YouTube](https://www.youtube.com/watch?v=AdLgPmcrXwQ)).
- [[../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
