---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
course: Stanford CS224G Building and Scaling LLM Applications
rights_status: official_or_open_public
provenance_status: official_stanford_course_page_schedule_and_public_lecture_pdfs_direct_read_no_class_recording_claim
sources:
  - https://web.stanford.edu/class/cs224g/index.html
  - https://web.stanford.edu/class/cs224g/schedule.html
  - https://web.stanford.edu/class/cs224g/lectures/CS%20224G%202026%20Lecture%205%20-%20Context%20Engineering.pdf
  - https://web.stanford.edu/class/cs224g/lectures/CS%20224G%202026%20Lecture%206%20-%20More%20Context%20Engineering.pdf
  - https://web.stanford.edu/class/cs224g/lectures/CS%20224G%202026%20Lecture%207%20-%20Agent%20Orchestration%20%26%20Workflow%20Design.pdf
  - https://web.stanford.edu/class/cs224g/lectures/CS%20224G%202026%20Lecture%2015%20-%20Data%20Strategy%20and%20Memory%20Layer%20for%20AI%20Agents.pdf
  - https://web.stanford.edu/class/cs224g/lectures/CS%20224G%202026%20Lecture%2017%20-%20Workshop%20Building%20and%20Scaling%20Realtime%20Voice%20AI%20Apps.pdf
  - https://web.stanford.edu/class/cs224g/lectures/CS%20224G%202026%20Lecture%2018%20-%20Ethics%20and%20Guardrails.pdf
---

# CS224G - Building And Scaling LLM Applications

## Scope

Direct-read synthesis from Stanford CS224G Winter 2026 public course page, public schedule, and selected public lecture PDFs on context engineering, agent orchestration, data strategy and memory layers, realtime voice AI, and guardrails, with a current-source check on May 18, 2026. The course page still describes CS224G as a project-based course for production-ready AI applications and still states that the class is not recorded or available via Zoom, so this note does not claim class-recording or transcript ingestion. It stores no raw slide text, copied code, or long excerpts.

## Production Thesis

CS224G frames LLM application work as product-and-systems engineering, not prompt tinkering. The useful production unit is a shipped loop: context assembly, model call, tool/action path, evaluation, deployment, observability, and product feedback. For Agent Studio, this supports treating every content-production capability as a route release with measurable context inputs, route topology, eval gates, observability, and feedback capture.

## Context Engineering

The context-engineering lectures sharpen a core datastore requirement: the visible chat box is only the last layer of a compiled request. Agent Studio needs to record the full request assembly path: immutable provider/system behavior, product instructions, user preferences, tool definitions, recent tool outputs, retrieved knowledge, memories, uploaded/user-provided data, conversation state, and generation parameters.

Design implications:

- Store context assembly as a first-class artifact, not an incidental prompt string.
- Separate privileged product instructions from user-controllable persona/preferences and untrusted retrieved/uploaded content.
- Track generation parameters with the same seriousness as prompt versions because temperature, output limits, logit bias, and context-window pressure change route behavior.
- Treat token budget as an engineering budget. Summarization, truncation, retrieval, and memory injection should be explicit decisions with loss/fidelity notes.
- Put extraction before analysis when source grounding matters. Raw source data should be converted into constrained fields before the route asks for judgment, scoring, publishing, or side effects.

## Agent Orchestration

The agent orchestration lecture aligns with existing Anthropic/OpenAI guidance: start with deterministic or single-agent workflows and only add multi-agent structure when role specialization, context separation, or tool-boundary separation gives measured benefit. Multi-agent systems are a partitioning mechanism, not a default sign of sophistication.

Agent Studio route design should require:

- a baseline simpler route and the failure slice that justifies agentic escalation;
- a declared topology such as single agent, sequential workflow, router, orchestrator-worker, reviewer loop, or multi-agent collaboration;
- role-specific tools, state, and instructions for specialist routes;
- a stop policy for loops, debates, retries, and self-review;
- traceable handoffs with task contract, returned artifact, failure policy, and synthesis decision.

MCP and A2A belong in the architecture as different layers. MCP-style connectors expose tools/resources/prompts to a route; A2A-style records describe specialist identity, task lifecycle, artifacts, status, and handoffs. Agent Studio should keep these records separate so a tool-list drift does not masquerade as a specialist-agent capability change.

## Data Strategy And Memory Layer

The data-strategy lecture's strongest point for Agent Studio is that durable advantage comes from product workflows that earn better data over time. Static scraped corpora become less differentiating; longitudinal user interactions, feedback loops, artifact revisions, internal review traces, and domain-specific source curation become the useful moat.

Implications for the vault and app:

- Memory is application infrastructure, not model magic. Cross-session memory writes need source evidence, namespace, scope, retention, and review status.
- Feedback should be captured at the artifact and route-decision level: accepted sources, rejected sources, edit deltas, reviewer comments, publish outcomes, and user corrections.
- Data flywheels must avoid poisoning themselves. Promote only reviewed memories, high-quality examples, and source-backed decisions into canon or training/eval material.
- Internal tools are part of the product system. The best Studio data may come from review queues, rejection reasons, editorial changes, and source-quality labels rather than only final published posts.

The lecture makes feedback design concrete enough to turn into product schema. Agent Studio should not treat "feedback" as one column. A low-friction label, a star rating, a free-text complaint, a direct artifact edit, a passive behavior signal, and an expert review all have different reliability, cost, bias, and downstream-use constraints.

Product implications:

- Direct edits are high-value because the diff identifies the user's target behavior. Store edit deltas, target span, artifact version, route version, and whether the user accepted the final result.
- Ratings are useful aggregate telemetry but weak training data unless paired with task context, source evidence, and a short reason or follow-up classification.
- Passive signals such as dwell time, regeneration, clickthrough, and abandonment should be labeled as behavioral evidence, not preference truth. They can prioritize review but should not silently tune routes.
- LLM-assisted feedback cleanup is allowed only as transformation, not authority. If an LLM clusters complaints, extracts a rationale, or proposes a memory update, the output needs provenance, confidence, and review state before promotion.
- Product feedback must deliver immediate user value. If a correction only benefits the training pipeline later, users will under-contribute and the data will skew toward unusual complaints.

The memory layer should therefore have a promotion ladder:

1. raw interaction or edit event;
2. candidate preference or memory extracted from the event;
3. reviewed memory with scope, expiry, and user-visible edit/delete affordance;
4. route-eligible memory used in context assembly;
5. training/eval example only after privacy, rights, quality, and source-grounding checks.

Do not collapse those stages. A useful user correction can be valid for that user's next session while still being unsafe as global training data.

The lecture also highlights contribution quality. Agent Studio should weight feedback by demonstrated expertise, consistency, and task difficulty rather than by volume alone. A retained expert reviewer who reliably fixes hard citation failures should not be averaged away by many casual likes. At the same time, expert-heavy or early-adopter-heavy data can underrepresent the real creator audience, so contributor weighting needs representation audits and slice-level evals.

Design consequences:

- Store contributor class, credential or role evidence where appropriate, consistency score, hard-case accuracy, peer agreement, and conflict-of-interest caveats.
- Track whether a feedback item came from an expert, retained power user, novice, contractor labeler, model judge, or passive usage signal.
- Add representativeness checks before using feedback for route-wide personalization, retriever tuning, or preference optimization.
- Treat internal labeling/review tools as product-critical surfaces. Poor tooling creates bad data even when reviewers are capable.
- For "give-to-get" data contribution models, require clear usage rights, privacy review, anonymization or redaction policy, quality verification, and user-visible value exchange before contributed material can enter shared retrieval, eval, or training pools.

## Realtime Voice Architecture

The realtime voice workshop distinguishes chained STT-to-LLM-to-TTS systems from native realtime voice sessions. The important design consequence is not that one vendor path always wins; it is that realtime voice routes have different state, latency, security, and recovery contracts than text routes.

Agent Studio should model realtime routes with:

- transport choice: native realtime/WebRTC, WebSocket sideband, or chained STT/LLM/TTS;
- ephemeral token/session-token policy so client apps never receive master provider credentials;
- media stream versus control-data channel separation;
- interruption/barge-in behavior and turn-detection policy;
- sideband/server-control pattern when the backend must inspect events, enforce state, or run privileged tools;
- reconnect behavior because short-term conversation state can be lost when a realtime connection drops;
- token and audio-cost budget, since voice sessions can consume budget differently from text-only calls.

## Guardrails And Socio-Technical Risk

The guardrails lecture is useful as a release-gate reminder: safety is not a final moderation call. It spans harm taxonomy, bias/privacy/manipulation concerns, red teaming, adversarial testing, governance lag, regulatory context, and open-versus-closed model tradeoffs.

For Agent Studio, guardrails should be records and evals:

- harm taxonomy attached to each public route and media surface;
- red-team/adversarial eval cases before route promotion;
- regulatory or policy assumptions as versioned release constraints;
- open/closed model choice captured as a risk/operability decision, not just a cost decision;
- reviewer burden and escalation policy for claims, sensitive sources, voice/persona outputs, and public publishing.

## Agent Studio Canon Decisions

- `context_assembly_record` should be mandatory for every generation route. It should link instruction layers, user state, retrieval, memory, tool definitions, attachments, parameters, and truncation/summarization decisions.
- `memory_promotion_record` should distinguish raw interaction data, candidate memory, reviewed memory, rejected memory, and canon source note.
- `feedback_capture_event` should preserve the feedback form, target artifact/span, route version, source context, user value returned, and whether the signal is direct, explanatory, passive, edited, or expert-reviewed.
- `contributor_quality_profile` should keep privacy-safe evidence for expertise, consistency, hard-case accuracy, peer agreement, and representation caveats before feedback is weighted.
- `memory_extraction_review` should separate LLM-extracted candidate memories from reviewed memories and route-eligible memories.
- `route_topology_decision` should capture why a route is deterministic, single-agent, workflow-based, or multi-agent, with measured evidence for escalation.
- `realtime_session_record` should track ephemeral credentials, transport, media/control channels, turn policy, tool-call path, reconnect state, and sideband controls.
- `guardrail_validation_run` should store red-team cases, failures, mitigations, residual risk, reviewer signoff, and release-blocking flags.
- `llm_application_route_release_gate` should bind the shipped product loop: compiled context, route topology, tool/action surface, state and memory policy, evals, observability, deployment mode, feedback loop, realtime lane where applicable, guardrails, human approval, fallback, and rollback.
- Product feedback should become typed training/eval data only after rights, privacy, quality, and source-grounding checks.

## Release Gate Contract

CS224G's durable architecture contribution is that an LLM application route is a shipped loop, not a prompt. Agent Studio should promote an LLM application route only when the release gate proves:

- product objective, target user, route owner, and deployment mode;
- compiled context assembly with instruction layers, trust labels, retrieval/memory/upload/tool segments, generation parameters, and truncation or summarization policy;
- token-budget policy, pinned context, eviction/compression behavior, and re-retrieval path for dropped source material;
- selected topology and rejected simpler alternatives, including deterministic, single-call, single-agent, workflow, router, parallel, orchestrator-worker, evaluator-optimizer, and multi-agent options;
- tool schema and execution-owner policy, including what the model may request versus what the product runtime executes;
- state and memory contract across short-term thread state, checkpointing, long-term memory, candidate memory, reviewed memory, and rejected memory;
- data-flywheel policy for feedback, revisions, user corrections, reviewer notes, and internal-tool labels, with rights/privacy/quality filters before reuse;
- contributor-quality and representation checks for feedback reused beyond the originating user or artifact;
- data-contribution rights and value-exchange evidence when user-provided artifacts can benefit shared route quality;
- observability records for latency, errors, tool frequency, retrieval quality, feedback outcomes, and route-specific success metrics;
- realtime voice lane evidence when present: ephemeral credentials, transport, media/control channels, sideband/backend control, turn detection, interruption, reconnect behavior, audio-cost policy, and latency SLO;
- guardrail taxonomy, adversarial/red-team evals, prompt-injection checks, sensitive-data protections, policy/regulatory assumptions, reviewer burden, escalation, fallback, and rollback.

Do not promote the gate when the change is only a prompt edit, when context is not reconstructible, when the route chooses multi-agent orchestration without simpler-route evidence, when memory writes bypass review, when realtime clients can reach master credentials or privileged tools, or when guardrails are only a final moderation call.

## Cross-Checks

- Reinforces [[../../01-sources/official-open/anthropic-effective-agents]] on starting simple and escalating to agents only when evals show need.
- Reinforces [[../../01-sources/official-open/openai-practical-agents]] and [[../../01-sources/official-open/openai-agents-sdk-guardrails]] on handoffs, human intervention, guardrails, and traceable route safety.
- Reinforces [[../../01-sources/official-open/langchain-memory-and-persistence]] on checkpointed route state versus long-term memory.
- Reinforces [[../../01-sources/official-open/google-a2a-protocols]] and [[../../01-sources/official-open/model-context-protocol-tooling]] on separating agent task protocols from tool/resource connector surfaces.
- Reinforces [[../../01-sources/official-open/gemma4-and-realtime-sources]] on realtime session, voice, and transport decisions.
