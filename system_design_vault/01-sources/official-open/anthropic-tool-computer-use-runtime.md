---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
rights_status: official_public
provenance_status: official_anthropic_tool_runtime_docs_direct_read
sources:
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/bash-tool
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/text-editor-tool
  - https://platform.claude.com/docs/en/agents-and-tools/mcp-connector
  - https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks
---

# Anthropic Tool And Computer-Use Runtime

## Scope

Direct-read synthesis from current official Anthropic/Claude docs for tool use, computer use, bash, text editor, MCP connector, and prompt-injection/jailbreak mitigation. This note captures Agent Studio route and datastore implications. It stores no copied code blocks, system prompts, API examples, or long excerpts.

Current-source check: Anthropic's current tool docs distinguish client tools from server tools, computer use remains beta and ZDR-eligible, prompt-injection classifiers can steer computer-use flows toward user confirmation, and MCP connector now uses the `mcp-client-2025-11-20` beta header. The MCP connector currently supports remote HTTP MCP servers rather than local STDIO direct connection, only supports MCP tool calls from the broader MCP feature set, and is not covered by ZDR arrangements.

## Core Pattern

Anthropic's current tool docs split tool execution into two families:

- client tools, where Claude returns a structured tool request and the product executes the operation;
- server tools, where Anthropic executes the tool on provider infrastructure and returns results through the API response.

Agent Studio should preserve that distinction in route releases. A model-visible tool name is not enough. The datastore needs execution owner, sandbox, retention mode, network boundary, credential scope, output policy, and replay evidence.

## Computer Use Contract

Computer use is a beta desktop-control capability. It gives the model screenshot-based perception plus mouse and keyboard actions, while the application owns the actual environment and executes the requested actions.

Agent Studio implications:

- The computer is an environment with state, not a simple function call.
- The route needs a sandboxed VM/container or equivalent isolated desktop, explicit display dimensions, installed apps, network policy, and file/credential boundary.
- Screenshots are untrusted input. Web pages, images, PDFs, and UI text can carry prompt-injection instructions.
- Human confirmation is required before meaningful real-world consequences, affirmative-consent actions, credential use, financial actions, terms acceptance, account changes, or public posting.
- The product should inform users of the risks and obtain consent before enabling computer-use routes.
- Computer-use traces should store action metadata, screenshots as bounded artifact refs where allowed, and redacted summaries by default, not raw screen streams in ordinary notes.

The agent loop itself is a release surface: model request, tool action, environment result, follow-up request, terminal decision. Each iteration needs bounded step count, stop reason, approval state, and rollback or cleanup policy.

## Bash And Text Editor Contract

Bash gives a persistent shell session. Text editor lets the model view and modify text files. Both are powerful because they create durable side effects and preserve state between steps.

Agent Studio should treat these as privileged tools:

- Bash session state, working directory, environment variables, network access, package install permissions, and filesystem scope need explicit records.
- Text-editor operations need file scope, max-view/truncation behavior, diff/patch evidence, undo/rollback policy, and review state.
- Generated commands and edits should be proposals until an execution policy admits them.
- Tests and build commands should be stored as evidence, but command stdout/stderr may contain secrets and needs redaction policy.
- Persistent sessions need restart/cleanup records so later commands are not explained by invisible prior state.

For the vault itself, this reinforces the current rule: use compact synthesis notes, keep raw source text out of notes, and record file/action provenance instead of pasting command output or source material.

## MCP Connector Boundary

Anthropic's MCP connector can connect Claude directly to remote MCP servers from the Messages API. Current docs emphasize toolset configuration, multiple servers, auth tokens, and allow/deny style per-tool configuration. They also note a retention caveat: MCP connector data is not covered by ZDR arrangements and follows standard retention.

Agent Studio implications:

- Remote MCP tools are third-party executable capability, not ordinary context.
- MCP server URL, transport, auth token scope, toolset configuration, allowed/disabled tools, imported tool-list hash, and per-tool config should be release evidence.
- MCP resources and prompts are different from tools. If resources are converted into message content or files, the route should record source identity, MIME/content constraints, and unsupported-value failures.
- ZDR/private-source routes should not use MCP connector paths unless provider retention and third-party retention are explicitly reviewed.
- Local STDIO MCP and remote HTTP MCP should be modeled separately because they have different trust and network boundaries.
- MCP connector beta header, server definition, OAuth token source, MCPToolset default config, per-tool configs, allowed/disabled tool list, and migration state should be versioned as release evidence.

## Prompt Injection And Abuse Controls

Anthropic's prompt-injection guidance and computer-use warning converge on the same rule: untrusted content can steer a model toward unsafe actions. For Agent Studio, this must be checked at the trace and tool boundary, not only in the final answer.

Required controls:

- input safety scans for untrusted web, screenshot, uploaded, retrieved, and tool-output content;
- trust labels in context assembly;
- human confirmation before sensitive tool actions;
- action allowlists and domain allowlists for browser/computer routes;
- repeated-abuse throttling or account controls;
- structured guardrail outputs when screening inputs;
- security eval cases that inspect tool attempts, approvals, and blocked actions.

## Datastore Additions

| Object | Purpose | Key fields |
|---|---|---|
| `tool_execution_boundary` | Declares where a model-visible tool runs | `tool_id`, `provider`, `execution_owner`, `client_or_server_tool`, `sandbox_ref`, `network_policy_ref`, `credential_scope_ref`, `retention_policy_ref`, `replay_policy`, `status` |
| `computer_use_environment` | Desktop/browser environment controlled by an agent | `environment_id`, `route_id`, `display_profile`, `container_or_vm_ref`, `installed_apps`, `network_allowlist`, `file_scope_policy`, `credential_policy`, `cleanup_policy`, `consent_policy`, `status` |
| `computer_use_action_event` | Per-action trace for screenshot/mouse/keyboard control | `action_event_id`, `run_id`, `environment_id`, `action_type`, `coordinates_or_keys_hash`, `screenshot_artifact_ref`, `approval_ref`, `prompt_injection_scan_ref`, `result_summary`, `created_at` |
| `shell_session_record` | Persistent bash state and execution boundary | `shell_session_id`, `run_id`, `working_directory`, `env_scope_hash`, `network_policy_ref`, `filesystem_scope`, `restart_events`, `cleanup_event_ref`, `status` |
| `shell_command_event` | Command proposal/execution evidence | `command_event_id`, `shell_session_id`, `command_hash`, `approval_ref`, `stdout_artifact_ref`, `stderr_artifact_ref`, `redaction_policy_ref`, `exit_status`, `side_effect_summary`, `created_at` |
| `text_editor_action_event` | File view/edit operation evidence | `edit_event_id`, `run_id`, `file_ref`, `operation`, `max_characters`, `before_hash`, `after_hash`, `diff_artifact_ref`, `approval_ref`, `rollback_ref`, `created_at` |
| `mcp_connector_policy` | Remote MCP connector release policy | `policy_id`, `route_id`, `server_refs`, `transport`, `auth_scope`, `toolset_config_hash`, `allowed_tools`, `disabled_tools`, `retention_review`, `zdr_eligible`, `status` |
| `mcp_resource_conversion_event` | MCP resource/prompt converted into content or file input | `conversion_id`, `run_id`, `server_ref`, `resource_uri_hash`, `conversion_mode`, `mime_type`, `unsupported_value_error`, `source_record_ref`, `created_at` |
| `high_authority_tool_release_gate` | Promotion gate for computer-use, shell, text-editor, remote MCP, browser, or external-mutation tools | `gate_id`, `route_id`, `candidate_release_id`, `tool_execution_boundary_refs`, `sandbox_refs`, `network_allowlist_refs`, `credential_scope_refs`, `consent_policy_refs`, `approval_policy_refs`, `prompt_injection_eval_refs`, `trace_redaction_policy_refs`, `retention_review_refs`, `mcp_connector_policy_refs`, `rollback_cleanup_refs`, `decision`, `reviewer`, `created_at` |

## Canon Cross-Check

The security canon owns the rule that untrusted content is data, not instruction. This note is canon for the concrete high-authority tool surfaces where that rule must be enforced: screenshots, web pages, shell output, file contents, MCP tool results, and generated UI text.

The guardrail and eval notes own trace grading, tripwires, and release gating. This note supplies the action evidence those graders must inspect: computer-use action events, shell command events, text-editor diffs, MCP tool import/config events, prompt-injection scans, approval decisions, and cleanup proof.

The privacy note owns provider retention and data-boundary posture. This note adds the key split: computer use can be compatible with ZDR when the organization has that arrangement, but MCP connector is explicitly non-ZDR and should not be used for private-source routes without a retention review.

## Release Gates

Do not promote a tool/computer-use route when:

- execution owner is ambiguous;
- a computer-use route lacks sandbox, network allowlist, credential boundary, user consent, and human confirmation policy;
- screenshots or tool outputs can override privileged instructions;
- bash commands can access arbitrary filesystem, network, package install, or secrets without route approval;
- text-editor edits lack diff, review, and rollback evidence;
- persistent shell state is not restartable or explainable;
- MCP connector tools are enabled without server identity, auth scope, allow/deny configuration, and retention review;
- ZDR/private-source routes depend on MCP connector data paths without explicit review;
- prompt-injection evals inspect only final text rather than the tool/action trace.
- high-authority tool routes lack a release gate linking sandbox, network, credential, consent, approval, prompt-injection eval, trace-redaction, retention, and rollback/cleanup evidence.

## Agent Studio Decision

Treat computer use, bash, text editing, and MCP connector calls as high-authority route surfaces. They belong behind typed execution boundaries, sandbox policies, trust-boundary scans, approval records, and traceable action events. The model can propose actions; Agent Studio owns the environment, permissions, retention, execution, and rollback evidence.
