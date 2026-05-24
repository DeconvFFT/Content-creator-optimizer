---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://developers.openai.com/api/docs/guides/agent-builder
  - https://developers.openai.com/api/docs/guides/chatkit
  - https://developers.openai.com/api/docs/guides/chatkit-widgets
  - https://developers.openai.com/api/docs/guides/chatkit-actions
---

# OpenAI Agent Builder And ChatKit Product Integration

## Source Boundary

This note synthesizes official OpenAI Agent Builder and ChatKit docs for visual workflow assembly, workflow publication/versioning, embedded chat deployment, widget design, and ChatKit actions. It stores only original synthesis and Agent Studio design implications, not copied docs text or code.

Current-doc check on 2026-05-18 found the official OpenAI Agent Builder and ChatKit pages still aligned with this note. Agent Builder still treats a published workflow as an ID/versioned snapshot with typed node/edge contracts, preview/debug traces, and trace graders. ChatKit still requires backend session creation with workflow ID and authenticated user binding, frontend client-secret handoff without storing the secret, hosted OpenAI workflow serving by default, widgets served from product/backend definitions, and actions handled through typed payloads and server/client callbacks.

## Core Design Lessons

Agent Builder turns an agent into a versioned workflow object, not a prompt file. The workflow is built from agents, tools, control-flow logic, typed node inputs/outputs, and typed edges. Preview/debug traces and trace graders become part of the route-development loop. Agent Studio should treat visual workflow publication as a release event with graph version, node contracts, edge contracts, sample trace evidence, grader results, and deployment target.

ChatKit is a product embedding layer around a workflow. In the hosted pattern, a product creates an Agent Builder workflow, creates a ChatKit session from the backend, passes the workflow ID, and gives the frontend a client secret. That means Agent Studio needs a separate product-session boundary: the end-user identity comes from the product backend, the workflow version comes from OpenAI/Agent Builder, and the chat UI runs in the customer's product surface.

The client secret is a short-lived frontend credential, not an application secret. The product backend remains responsible for authenticating the end user, creating the session, binding the workflow, and returning only what the frontend needs. Agent Studio should store session issuance events, user/workspace binding, workflow ID/version, client-secret expiry posture, and failure mode without storing secrets.

ChatKit widgets are structured conversation UI, not decoration. They can render cards, lists, status, assets hosted by the backend, and interactive buttons. A widget action can trigger backend logic, update widgets, stream new thread items, or run inference. Agent Studio should store widget definitions, asset refs, action configs, action payload schemas, sender item refs, and resulting thread events.

Actions are side-effect and inference triggers that bypass ordinary user-message submission. They may originate from widget interaction or an imperative frontend call. Action payloads are client-provided and must be treated as untrusted. Agent Studio should route them through the same validation, authorization, idempotency, audit, and human-confirmation policies as tool calls or publishing actions.

Hosted ChatKit and self-hosted/advanced ChatKit are different route classes. Hosted mode gives OpenAI-managed backend scaling around Agent Builder workflows. Advanced mode uses the ChatKit SDK with a custom backend. Agent Studio should record which mode is used, who owns scaling and persistence, where traces live, how actions are handled, and what migration path exists if the hosted workflow needs to move into custom code.

## Agent Studio Implications

Agent Studio should model product-facing agent chat as its own release surface:

- workflow graph object with published version, node contracts, edge contracts, preview trace refs, and grader/eval refs;
- ChatKit integration record with product surface, hosted-versus-custom backend mode, workflow ID/version, client setup, and feature flags;
- session issuance record with authenticated user ref, workspace/tenant ref, workflow version, client-secret issuance and expiry metadata, and no stored secret value;
- widget definition record with backend-hosted asset refs, layout components, status fields, action bindings, and rendered thread item refs;
- widget/action event record with action type, sender item, payload hash, validation result, authorization result, side-effect class, idempotency key, and generated thread/inference refs;
- thread item record for visible messages, hidden context items, widget items, files, action side effects, and streamed deltas;
- hosted-backend dependency record for OpenAI-managed workflow serving versus self-hosted ChatKit backend serving;
- product launch evals for workflow traces, UI interaction, action validation, widget rendering, mobile behavior, and support handoff.

## Datastore Requirements

Add product-chat records on top of the existing agent/app/tool ledger:

- `agent_builder_workflow_record`: workflow ID, version, published snapshot, node refs, edge refs, owner, deploy target, and status;
- `workflow_node_contract_record`: node type, model/tool/agent binding, input schema, output schema, guardrails, eval refs, and trace fields;
- `chatkit_integration_record`: product surface, hosted/custom mode, workflow ref, frontend embed config, backend session endpoint ref, enabled features, and owner;
- `chatkit_session_record`: product user ref, workspace/tenant ref, workflow version, session lifecycle, client-secret issuance metadata, expiry posture, and error state;
- `chatkit_widget_definition`: widget type, layout schema, asset refs, action bindings, status/cancel/confirm controls, theme, and version;
- `chatkit_action_event`: action type, source widget/item, payload hash, validation result, authorization result, side-effect class, idempotency key, generated thread item refs, and created_at;
- `chatkit_thread_item_record`: visible, hidden-context, widget, file, action, and streamed thread item with model visibility and source refs;
- `agent_builder_trace_grade`: trace grader configuration, trace ref, score, failure cluster, workflow version, and promotion decision.
- `product_chat_release_gate`: route-level promotion gate linking workflow ID/version, workflow snapshot, node/edge contracts, preview trace refs, trace grader refs, hosted-versus-custom mode, ChatKit integration, session issuance endpoint, authenticated user/workspace binding, client-secret expiry posture, widget definitions, action schemas, action validation/auth/idempotency tests, thread item lineage, UI/mobile tests, support handoff, fallback behavior, rollback target, decision, and review timestamp.

## Operating Rule

Do not treat an embedded chat as production just because the workflow runs in preview. Product launch requires workflow versioning, session issuance controls, user identity binding, widget/action schemas, untrusted action validation, trace grading, UI interaction tests, and a clear hosted-versus-custom ownership record.

Promote product-embedded chat routes only after a `product_chat_release_gate` proves the workflow and UI are the same release. The gate must block release when the workflow version is ambiguous, a client secret is stored or issued without authenticated user binding, widget action payloads are accepted without validation and authorization, action side effects lack idempotency, trace graders do not cover the launch workflow, or hosted/custom ownership and rollback are unclear.
