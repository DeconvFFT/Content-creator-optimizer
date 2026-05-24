---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
rights_status: official_or_open_public
provenance_status: official_openai_modal_e2b_sandbox_docs_direct_read
sources:
  - https://platform.openai.com/docs/guides/tools-code-interpreter/
  - https://platform.openai.com/docs/api-reference/containers
  - https://platform.openai.com/docs/api-reference/container-files/listContainerFiles
  - https://modal.com/docs/guide/sandbox
  - https://modal.com/docs/reference/modal.Sandbox
  - https://modal.com/docs/guide/sandbox-spawn
  - https://modal.com/docs/guide/sandbox-networking
  - https://modal.com/docs/examples/safe_code_execution
  - https://e2b.dev/docs/sandbox/persistence
  - https://e2b.dev/docs/sdk-reference/python-sdk/v2.15.0/sandbox_sync
---

# Code Execution Sandbox Runtime

## Scope

Direct-read synthesis from official OpenAI Code Interpreter and Containers docs, Modal Sandbox docs, and E2B Sandbox docs. This note captures the Agent Studio contract for running model-written or user-supplied code. It stores no code samples, credentials, user files, execution output, raw transcripts, or long excerpts.

## Core Pattern

Code execution is a privileged route stage, not a tool-call detail. A model can propose code, but the product must decide where it runs, which files it sees, which network paths are reachable, which packages/imports are allowed, how long it may run, what artifacts can leave the sandbox, and how cleanup is proven.

OpenAI's Code Interpreter docs make the hosted-container boundary explicit: a code-interpreter call requires a container, files can be attached or generated inside that container, memory tier is selected per container, and active containers expire. That turns container ID, memory limit, file list, generated-file citations, expiration, and download/retention behavior into trace fields.

Modal's Sandbox docs expose a lower-level runtime boundary: a sandbox has lifecycle events, resource configuration, entrypoints, process execution, stdout/stderr/stdin streams, idle timeouts, readiness probes, filesystem operations, volumes, tunnels, and network/security controls. This is the shape Agent Studio needs when the route owns execution rather than delegating to a provider-hosted tool.

E2B's current sandbox docs add persistence and agent-runtime details: a sandbox can run commands, expose filesystem operations, list or kill processes, pause/resume with filesystem and memory state, auto-pause on timeout, and reset continuous-runtime limits after resume. That is useful for coding agents and data-analysis agents, but it also means paused state, timeout policy, process inventory, and resume eligibility must be governed data.

## Current-Source Cross-Check

Current OpenAI code-interpreter and container docs still support treating hosted code execution as an ephemeral container boundary with explicit container IDs, file inputs/outputs, generated file references, memory tier, expiration, and container-file operations. Agent Studio should preserve those facts as route evidence even when execution is provider-hosted.

Current Modal Sandbox docs reinforce the lower-level execution contract: lifecycle state, command execution, timeout, idle timeout, readiness probes, file access, snapshots, networking, tunnels, secrets/environment variables, stdout/stderr streams, and termination state can all change correctness and data exposure.

Current E2B Sandbox docs reinforce persistence as a separate risk: pause/resume preserves filesystem and memory state, paused sandboxes can be listed and killed, timeout can auto-pause, and continuous runtime limits reset after resume. Agent Studio should never treat resumed code state as clean unless the recovery decision says state reuse is allowed.

## Runtime Boundary Decisions

- Treat hosted code-interpreter, cloud sandbox, local container, and desktop/computer-use execution as different executor classes.
- Store the sandbox policy before execution; do not infer it afterward from logs.
- Separate model-written code proposal from execution approval, execution run, and artifact export.
- Assume files inside the sandbox may include private source material, generated artifacts, package caches, temporary credentials, and intermediate outputs.
- Network access should be deny-by-default or allowlisted by route; "secure sandbox" is not enough without an egress policy record.
- Filesystem persistence is a product decision. Ephemeral containers reduce retention risk; paused/resumable sandboxes improve continuity but preserve sensitive state.
- Readiness probes, startup scripts, package installation, and volume mounts are part of the trust boundary because they can change what the model's code can do.
- Runtime streams are sensitive. stdout, stderr, screenshots, generated files, stack traces, and package logs can leak source text, secrets, filenames, or user data.
- Generated files need artifact provenance: which code hash, input files, container, package environment, and approval produced the file.

## Agent Studio Design Implications

- Code-capable routes need a `sandbox_profile` tied to route release, not ad hoc executor selection per run.
- Every execution run should preserve executor class, provider, image/template, memory, CPU/GPU, timeout, idle timeout, network policy, mounted volumes, file refs, and cleanup outcome.
- Container expiration and pause/resume state are user-visible correctness risks. If a run depends on container memory, the trace should say whether that state is reconstructible after expiration.
- Code output should flow through validation before it becomes an Obsidian note, source chunk, eval result, social artifact, route change, or publication candidate.
- Package installation and git checkout inside a sandbox are supply-chain events. They need source, version/ref, network access, and cache policy.
- Long-running or resumable coding agents need process inventory, kill policy, auto-pause behavior, and owner/reviewer controls.
- Generated file export should require artifact classification, rights/sensitivity scan, and optional human approval before leaving the sandbox.
- If a provider-hosted container handles files, Agent Studio still needs local source-ledger refs and retention policy; provider container state is not the system of record.
- A sandbox failure should produce a recovery decision: retry same sandbox, create a clean sandbox, resume from paused state, reduce scope, request human review, or block the route.

## Datastore Additions

| Object | Purpose | Key fields |
|---|---|---|
| `sandbox_profile` | Versioned execution boundary for a code-capable route | `sandbox_profile_id`, `executor_class`, `provider`, `image_or_template_ref`, `memory_limit`, `cpu_gpu_class`, `timeout`, `idle_timeout`, `network_policy_id`, `filesystem_policy_id`, `secret_policy_id`, `package_policy_id`, `artifact_export_policy_id`, `status` |
| `sandbox_instance` | Concrete container/sandbox/VM/session used in a run | `sandbox_instance_id`, `sandbox_profile_id`, `provider_container_id`, `route_release_id`, `created_at`, `last_active_at`, `expires_at`, `state`, `pause_resume_supported`, `cleanup_required`, `cleanup_status` |
| `sandbox_file_binding` | File made visible inside the sandbox or produced by it | `binding_id`, `sandbox_instance_id`, `source_or_artifact_ref`, `remote_path_hash`, `direction`, `mime_type`, `sensitivity_class`, `download_required`, `export_approval_ref`, `created_at` |
| `sandbox_process_run` | Command/cell/process executed in the sandbox | `process_run_id`, `sandbox_instance_id`, `code_hash`, `entrypoint_or_command_hash`, `started_at`, `ended_at`, `timeout`, `return_code`, `stdout_ref`, `stderr_ref`, `error_class`, `killed_by_policy`, `status` |
| `sandbox_network_policy` | Route-specific network reachability policy | `network_policy_id`, `default_mode`, `allowed_domains_or_cidrs`, `blocked_domains_or_cidrs`, `tunnel_policy`, `internet_allowed`, `egress_log_policy`, `review_status` |
| `sandbox_filesystem_policy` | Filesystem and persistence boundary | `filesystem_policy_id`, `ephemeral_or_persistent`, `allowed_mount_refs`, `writeable_paths`, `snapshot_policy`, `pause_resume_policy`, `retention_policy_id`, `cleanup_policy` |
| `sandbox_artifact_export` | Decision and evidence for moving output out of the sandbox | `export_id`, `sandbox_instance_id`, `file_binding_id`, `artifact_type`, `validation_refs`, `sensitivity_scan_ref`, `rights_policy_ref`, `approval_ref`, `destination_ref`, `status` |
| `sandbox_recovery_decision` | Failure or expiry recovery choice | `decision_id`, `sandbox_instance_id`, `trigger`, `candidate_actions`, `selected_action`, `state_reuse_allowed`, `data_loss_risk`, `review_required`, `created_at` |
| `code_execution_release_gate` | Promotion gate for code-capable routes | `gate_id`, `route_id`, `candidate_release_id`, `sandbox_profile_refs`, `sandbox_instance_policy_refs`, `file_binding_policy_refs`, `process_run_policy_refs`, `network_policy_refs`, `filesystem_policy_refs`, `secret_policy_refs`, `package_supply_chain_refs`, `artifact_export_policy_refs`, `recovery_decision_policy_refs`, `cleanup_proof_refs`, `validation_eval_refs`, `rollback_condition`, `decision`, `reviewed_at` |

## Release Gates

Do not approve a code-execution route when:

- executor class and sandbox profile are not fixed for the route release;
- network reachability, filesystem persistence, secrets, package installation, and artifact export are unspecified;
- model-written code can see private sources without traceable file bindings;
- stdout/stderr/generated files can be stored or exported without redaction and sensitivity review;
- container expiration or pause/resume behavior can silently change correctness;
- package or git operations have no supply-chain policy;
- retries can reuse dirty sandbox state without an explicit recovery decision;
- cleanup cannot be proven after failure, timeout, cancellation, or user interruption;
- final artifacts produced by code bypass eval, rights, source-grounding, and human-review gates.

## Agent Studio Decision

This note is canon-ready for Agent Studio code-execution architecture. Model-written code should enter Agent Studio as a proposal and leave as an audited execution record. The durable contract is: route-level sandbox profile, concrete sandbox instance, file bindings, process runs, network/filesystem policies, artifact export decisions, recovery decisions, cleanup proof, redacted observability, and a code-execution release gate. Provider-hosted Code Interpreter can be one implementation of this contract; it should not replace the local source ledger or route-release evidence.
