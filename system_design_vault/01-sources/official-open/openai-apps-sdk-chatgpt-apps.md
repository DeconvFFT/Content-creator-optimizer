---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://developers.openai.com/apps-sdk
  - https://developers.openai.com/apps-sdk/concepts/mcp-server
  - https://developers.openai.com/apps-sdk/build/mcp-server
  - https://developers.openai.com/apps-sdk/build/chatgpt-ui
  - https://developers.openai.com/apps-sdk/build/state-management
  - https://developers.openai.com/apps-sdk/guides/security-privacy
  - https://developers.openai.com/apps-sdk/deploy/testing
  - https://developers.openai.com/apps-sdk/reference
---

# OpenAI Apps SDK And ChatGPT Apps

## Source Boundary

This note synthesizes current official OpenAI Apps SDK pages for ChatGPT app architecture, MCP servers, UI bridge behavior, state management, security/privacy, testing, and reference metadata. It stores only original synthesis and Agent Studio implications, not copied docs text or code.

Current-doc check on 2026-05-18 found the cited official OpenAI Apps SDK pages still aligned with this note. The current docs still frame ChatGPT apps as MCP-backed tool/resource integrations with host-rendered widgets, explicit state scopes, sandboxed iframe/CSP controls, discovery testing, and launch-readiness review. The reference pages add a useful current distinction: new apps should prefer standard `_meta.ui.*` metadata where available, while some OpenAI compatibility keys remain relevant for ChatGPT behavior such as output templates, widget CSP redirect domains, status text, and widget session correlation.

## Core Design Lessons

Apps SDK turns an app into three cooperating surfaces: an MCP server, model-visible tool results, and an iframe UI. The MCP server defines tools, schemas, auth, handlers, and UI templates. ChatGPT decides when to call tools from the metadata. The widget renders inside ChatGPT and communicates through the MCP Apps bridge. Agent Studio should therefore model an app integration as a route with server contracts, tool schemas, UI templates, bridge events, auth scopes, and review gates, not as a single frontend component.

Structured content and private metadata have different audiences. The model reads `structuredContent` and can use it in follow-up reasoning. Widget-only metadata stays private to the component. This is a critical Agent Studio boundary: model-visible data should be concise, schema-validated, rights-checked, and safe to repeat in the conversation; UI-only data can include richer local render state but still must not carry secrets.

The UI is message-scoped and host-controlled. A widget instance is tied to the response that rendered it. It can keep local UI state, request display changes, invoke app tools, send follow-up messages, upload/select files where available, and update model context through the host bridge. Agent Studio needs to treat UI state, backend business data, and cross-session preferences as separate records with separate lifetimes.

MCP app tools need stronger metadata than ordinary internal functions. Tool names, descriptions, schemas, output schemas, resource URIs, visibility, status text, file parameters, and security schemes all affect discovery, model choice, validation, and user trust. Agent Studio should version these as tool-interface release artifacts and evaluate both positive prompts that should select the tool and negative prompts that should not.

Security is not optional because the app can receive user data, access third-party APIs, and execute write actions. Least privilege, explicit consent, server-side input validation, audit logs, retention policy, PII redaction, token/scope enforcement, human confirmation for irreversible actions, iframe CSP, outbound network policy, dependency patching, and anomaly monitoring all belong in the same release checklist as functionality.

Testing has three product surfaces: tool correctness, component UX, and discovery precision. Unit tests should cover handler schemas, auth, errors, and edge cases. MCP Inspector and developer-mode testing should verify raw requests/responses, component rendering, golden prompts, negative prompts, mobile layouts, confirmation prompts, and output-schema compliance before launch.

## Agent Studio Implications

Agent Studio should represent a ChatGPT app as a governed distribution route:

- MCP server identity, transport, auth mode, endpoint, capability snapshot, owner, and deployment state;
- app tool definitions with input/output schemas, output template/resource URI, visibility, file params, security schemes, and model-facing description hash;
- tool result records separating model-visible structured content from widget-only metadata;
- widget template records for iframe resource URI, CSP domains, assets, layout mode, supported display modes, and host bridge capabilities;
- app bridge event records for tool input/result notifications, widget-initiated tool calls, follow-up messages, model-context updates, file operations, display requests, and close/open-external actions;
- state-scope records separating authoritative backend data, message-scoped UI state, and durable cross-session preferences;
- app auth grant records with OAuth/CIMD/DCR posture, scopes, token storage policy, expiry, and per-tool enforcement;
- app discovery eval records for positive, indirect, ambiguous, and negative prompts;
- app launch review records tying schema validation, UX screenshots, auth tests, CSP/network review, privacy/retention posture, dependency review, and submission readiness to a release.

## Datastore Requirements

Add app-specific records on top of the existing MCP/tool ledger:

- `chatgpt_app_record`: app identity, owner, distribution status, app store/plugin status, MCP server refs, review status, and allowed workspaces;
- `app_tool_descriptor_record`: versioned tool descriptor with schemas, output template/resource URI, visibility, file params, security schemes, and model-facing metadata hash;
- `app_widget_template_record`: iframe template, resource URI, CSP domains, assets, theme/display constraints, and compatible host bridge version;
- `app_bridge_event_record`: JSON-RPC/bridge event with direction, method, widget/message/run refs, payload hash, model-visible flag, and error state;
- `app_state_scope_record`: authoritative business data, message-scoped UI state, and cross-session preference state with ownership, lifetime, persistence, and deletion behavior;
- `app_file_authorization_record`: user-selected/uploaded file refs, file param mapping, temporary download URL refresh policy, library availability, and allowed tool use;
- `app_discovery_eval_case`: prompt, expected tool selection or rejection, observed tool call, arguments, confidence/discovery notes, and regression status;
- `app_launch_review_record`: release checklist for handler tests, schema validation, auth/scopes, UI screenshots, mobile coverage, CSP/network policy, retention policy, and submission readiness.
- `chatgpt_app_release_gate`: route-level promotion gate linking MCP server identity, app record, tool descriptor versions, output schemas, widget templates, CSP/network review, structured-content versus `_meta` boundary tests, bridge-event coverage, state-scope policy, file authorization policy, auth grants/scopes, discovery evals, handler tests, UX/mobile screenshots, privacy/retention review, dependency review, submission/review status, fallback behavior, rollback target, decision, and review timestamp.

## Operating Rule

Do not ship a ChatGPT app route because a widget renders locally. Ship only when the MCP server, tool descriptors, bridge behavior, model-visible data boundary, state ownership, auth/scopes, security/privacy posture, discovery evals, and launch review evidence are all versioned and tied to a release.

Promote ChatGPT app routes only after a `chatgpt_app_release_gate` proves the server/tool/UI contract end to end. The gate must block release when model-visible `structuredContent` or `content` leaks private widget data, `_meta` carries secrets, widget actions bypass server authorization, CSP or redirect domains are too broad, discovery prompts select the wrong tool, file authorization is stale, or launch-review evidence is missing.
