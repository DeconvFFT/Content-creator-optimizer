---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
source_title: "Stanford CS25 Transformers United V6"
lecture_title: "From Representation Learning to World Modeling through Joint Embedding Predictive Architectures"
speaker: "Hazel Nam and Lucas Maes"
source_status: official_public_listing_plus_open_papers
updated: 2026-05-18
sources:
  - https://web.stanford.edu/class/cs25/
  - https://web.stanford.edu/class/cs25/recordings/
  - https://arxiv.org/abs/2602.11389
  - https://arxiv.org/abs/2603.19312
related:
  - "[[cs25-state-space-transformer-tradeoffs]]"
  - "[[../../03-patterns/vision-multimodal/visual-multimodal-qa-canon]]"
  - "[[../../03-patterns/agent-systems/agent-route-architecture-canon]]"
  - "[[../../03-patterns/transformer-systems/cs25-transformer-systems-canon]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# CS25 - World Modeling Through JEPA

## Reading Status

Canon-ready direct read of the official Stanford CS25 V6 listing for the April 9 world-modeling talk, the CS25 recordings page, and open primary papers for Causal-JEPA and LeWorldModel, rechecked on 2026-05-18. The public recordings page does not currently expose this lecture as a selected public recording in visible page text, so this note does not claim video-level coverage and stores no transcript, copied slide text, or long excerpts.

## Why This Matters

Agent Studio is not a robotics platform, but it does operate over evolving worlds: source collections, user briefs, generated artifacts, visual states, draft revisions, route traces, and publishing surfaces. A useful agent needs more than one-shot text generation. It needs a compact state model of what exists, what changed, what depends on what, and what actions are likely to preserve or break the desired outcome.

The CS25 world-modeling slice is useful because it shifts attention from reconstructing surface pixels or text to learning latent predictive representations. For Agent Studio, the equivalent is not predicting every token in the vault. It is maintaining the right latent state: source provenance, artifact version, visual region, workflow step, dependency, reviewer intent, and next action.

## Predictive Representation Over Surface Reconstruction

The official CS25 listing frames the lecture around joint embedding predictive architectures that predict in latent space rather than reconstructing every pixel. The product analogy is direct: an agent does not need to copy every source line into memory; it needs to preserve the abstract state needed for decisions.

Agent Studio should therefore store:

- source identity and rights rather than raw source text in notes;
- artifact state and diff summaries rather than duplicate drafts;
- visual regions and object relations rather than only prose critiques;
- workflow state and dependencies rather than hidden chat history;
- eval failure slices rather than full transcripts.

This supports the user's existing requirement: compact original notes and design implications, not raw book dumps or transcript dumps.

## Object And Relation Bias

Causal-JEPA emphasizes object-level masking and relational prediction. For Agent Studio, that maps to a design rule: represent meaningful units explicitly. A social post, image, caption, source chunk, claim, citation, tool action, reviewer decision, and route release are objects with relations.

Useful relations include:

- claim supported by source;
- visual edit targets region;
- draft derived from source snapshot;
- route uses model/runtime/retriever version;
- reviewer decision approves artifact;
- eval case covers failure slice;
- tool action changes external state.

If these relations only live in a prompt transcript, the system cannot reliably audit, repair, or reuse them.

## Predictive Agent State

World models are useful when they support planning. Agent Studio's planning problem is editorial and operational rather than physical. Before taking an action, the system should be able to predict likely state changes:

- editing an image region may invalidate a prior visual approval;
- changing retrieval filters may reduce citation recall;
- switching runtime may change latency and formatting;
- revising a prompt may invalidate a calibrated eval comparison;
- publishing creates an external side effect that needs provenance and rollback policy.

This argues for explicit `state_transition_record` and `artifact_dependency_graph` objects.

## Multimodal State

The lecture's raw-pixel and object-representation context matters for media workflows. Agent Studio needs multimodal state records for images, video, audio, and text:

- visual object/region evidence;
- temporal frame or shot evidence;
- OCR text tied to regions;
- audio/transcript alignment;
- generated-media lineage;
- edits and masks;
- platform crop/aspect-ratio constraints.

Text-only memory is insufficient for a content studio that generates, critiques, edits, and publishes visual artifacts.

## Planning And Control Caveat

World-model language can sound more powerful than the evidence warrants. For Agent Studio, the safe interpretation is modest: store predictive state and action consequences for the product workflow. Do not imply that an agent has a complete world model or reliable causal understanding unless evals prove it for a narrow route.

Release gating should require transition evals:

- given artifact state and proposed action, predict which approvals or evals become stale;
- given source update, predict which notes/routes need refresh;
- given visual edit, predict which regions and captions may be affected;
- given route change, predict which eval surfaces need rerun.

## Failure Modes

- The system stores long transcripts but cannot answer which source supports a claim.
- A visual critique says an edit is correct but lacks region evidence.
- A generated artifact changes while downstream approvals remain marked valid.
- Agent memory is treated as a text summary rather than a typed state graph.
- A route action changes external state without a predicted state transition or rollback path.
- A multimodal route evaluates final prose but not object/region/frame evidence.
- World-model claims are used as vague capability marketing without route-specific transition evals.

## Agent Studio Design Implications

1. Treat artifact/source/workflow state as typed objects and relations, not only text context.
2. Store compact predictive state needed for future decisions rather than raw source or transcript copies.
3. Add transition evals for actions that mutate artifacts, routes, sources, approvals, or publish state.
4. Keep visual regions, object relations, OCR spans, and temporal traces as first-class evidence.
5. Separate product workflow prediction from broad claims about general world modeling.
6. Require stale-dependency detection when sources, prompts, routes, or artifacts change.
7. Require a `state_transition_release_gate` before routes that mutate sources, artifacts, media regions, approvals, eval state, route configs, or publish state are promoted.

## Datastore Implications

Add or strengthen these records:

- `world_state_record`: typed snapshot of source, artifact, workflow, route, approval, and publish state relevant to an agent run.
- `artifact_dependency_graph`: nodes and edges connecting sources, chunks, claims, drafts, media regions, evals, approvals, and published artifacts.
- `state_transition_record`: proposed action, predicted state changes, affected artifacts, invalidated approvals/evals, rollback path, and observed outcome.
- `object_relation_record`: typed relation between visual/text/workflow objects, with source evidence and review status.
- `multimodal_state_record`: image/video/audio/text state with regions, frames, OCR spans, transcript refs, masks, and transform history.
- `transition_eval_case`: initial state, proposed action, expected state delta, forbidden side effect, and grader/reviewer policy.
- `stale_dependency_record`: changed source/artifact/route, dependent objects, stale reason, required refresh, and owner.
- `state_transition_release_gate`: promotion gate proving that a state-mutating route predicts affected objects, invalidated approvals/evals, stale dependencies, forbidden side effects, rollback path, and observed outcome capture before it can change production state.

## Release Gate Contract

`state_transition_release_gate` is required before Agent Studio promotes any route that mutates source metadata, note state, generated artifacts, media regions, route configs, approvals, eval status, memory, graph facts, or publish state.

The gate rejects promotion unless the release record binds:

- initial `world_state_record` and scoped `artifact_dependency_graph`;
- proposed action class, affected object refs, and object-relation refs;
- predicted state delta for sources, claims, drafts, media regions, masks, OCR spans, transcript refs, route configs, approvals, evals, memory, graph facts, and publish targets;
- invalidated approval refs, invalidated eval refs, stale dependency records, and required refresh actions;
- multimodal state evidence for visual, video, audio, OCR, transcript, mask, and transform-history surfaces where used;
- transition eval cases covering expected state deltas, forbidden side effects, reviewer policy, and risk level;
- observed outcome capture policy, discrepancy handling, rollback path, owner, and incident feedback path.
