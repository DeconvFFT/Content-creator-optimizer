---
type: source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://dataintensive.net/
  - https://martin.kleppmann.com/2017/03/27/designing-data-intensive-applications.html
  - https://martin.kleppmann.com/talks.html
  - https://martin.kleppmann.com/2020/11/18/distributed-systems-and-elliptic-curves.html
  - https://www.cl.cam.ac.uk/teaching/2021/ConcDisSys/dist-sys-notes.pdf
  - https://martin.kleppmann.com/2015/09/26/transactions-at-strange-loop.html
  - https://martin.kleppmann.com/papers/debs21-keynote.pdf
  - https://arxiv.org/abs/1509.05393
source_status: official_or_open_public
verification_notes:
  - DDIA itself is not present in the current local book folder, so this is not a full DDIA chapter note.
  - Official author/book pages, Martin Kleppmann public talk pages, Cambridge distributed-systems course notes, and open papers were opened directly on 2026-05-18.
  - This note stores original synthesis only and does not copy book text, course-note text, figures, or long excerpts.
---

# DDIA Distributed Systems Foundations

## Direct-Read Scope

Direct-read pass over the official DDIA book site, Martin Kleppmann's official talks index and distributed-systems course announcement, the public Cambridge distributed-systems notes, Kleppmann's transaction talk page, the DEBS event-systems keynote paper, and the CAP critique arXiv abstract page.

This fills the DDIA-shaped gap without pretending that the unavailable local DDIA book has been chapter-ingested. The usable scope is the public design vocabulary: reliability, scalability, maintainability, replication, consistency, transaction boundaries, event logs, stream processing, and the tradeoffs behind distributed data systems.

Current-source check on 2026-05-18: the official DDIA site and author publication page still frame the book around reliable, scalable, maintainable systems and explicit tradeoffs rather than tool selection. Kleppmann's transaction talk still centers on ACID meaning, weak isolation anomalies, high-availability limits, linearizability, session guarantees, CAP confusion, and stream-processing transaction options. The Cambridge distributed-systems notes remain public course material for partial failure, replication, consistency, fault assumptions, consensus, and recovery. This note remains a public/open distributed-systems synthesis, not a substitute for chapter-level DDIA book ingestion.

## Core Read

The official DDIA site frames data-system design as tradeoff reasoning, not product shopping. Agent Studio should therefore avoid architecture claims like "use Postgres," "use Kafka-shaped events," or "cache aggressively" unless each claim names the reliability, scalability, maintainability, latency, consistency, and operational tradeoffs it accepts.

The Cambridge distributed-systems material makes partial failure the default condition. A route that touches providers, tools, source stores, queues, browsers, workers, or replicas can fail in one component while the rest of the product keeps running. Agent Studio needs failure boundaries that preserve useful reduced behavior: local drafts remain visible, source ledgers remain inspectable, queued work remains resumable, and externally mutating actions stay idempotent or blocked until recovered.

Replication is not just "more copies." The course material separates replica reconciliation, quorum behavior, state-machine replication, consensus, linearizability, eventual consistency, and conflict resolution. Agent Studio should assign each data family a consistency contract. User-facing run state, approval decisions, route releases, source rights decisions, and publish actions need stronger ordering than background freshness signals, analytics projections, or cache warmth. Quorum reads/writes alone do not prove linearizability unless the read-repair/write-back behavior and real-time observation boundary are part of the contract.

Event logs are more than notifications. The DEBS keynote distinguishes ephemeral notifications from persistent event records and shows how event sourcing can rebuild derived state with revised processing logic. Agent Studio's event ledger should keep this distinction explicit: a WebSocket progress ping can be ephemeral, but a run-state change, source-ingestion decision, feedback gate, artifact revision, route promotion, or publishing action must be a persistent event with replay semantics.

Partitioning is a correctness decision, not only a throughput decision. Kafka-style logs provide total order inside a partition, not across all partitions. Agent Studio should partition by the object whose state must be replayed deterministically: `run_id` for run timelines, `artifact_id` for revision histories, `source_id` for source-refresh decisions, `route_id` for release/eval histories, and `tenant_id` only when cross-object ordering is more important than concurrency. Multi-entity operations need explicit transaction or saga boundaries.

Transaction boundaries reduce application failure handling, but distributed transactions and weak isolation each impose costs. The transaction talk frames ACID, weak isolation anomalies, highly available transactions, session/causal/linearizable guarantees, CAP confusion, and stream-processing transaction options as design choices. Agent Studio should not use "eventual consistency" as a vague excuse; it should mark which invariants can be temporarily stale and which require serializable or linearizable behavior.

The CAP critique argues that CAP is too blunt for practical design and proposes reasoning about operation latency sensitivity to network delay. For Agent Studio, this means each route should declare whether it is delay-sensitive. Realtime interruption cannot wait for global coordination; route promotion, billing-impacting cost attribution, and source-rights decisions can afford stronger coordination. The datastore should capture that distinction as policy rather than burying it in code.

## Agent Studio Design Implications

- Give every durable data family a `consistency_contract`: required guarantee, ordering scope, stale-read tolerance, conflict policy, and user-visible consequence.
- Keep `event_topic_contract` from the Kafka note, but add distributed-system assumptions: fault model, retry surface, partition key, multi-partition behavior, and replay scope.
- Treat realtime UI events, progress pings, and audio state as notification events unless they change durable workflow state.
- Treat run state, source ledger decisions, artifact revisions, feedback approvals, route changes, eval outcomes, and publish actions as persistent event records.
- Add linearizability only where the product semantics require it. For example, approval decisions and route releases should not let one reviewer see a newer state while a later reviewer acts on an older state.
- Use eventual consistency for projections, search indexes, metric dashboards, cache warmth, and read-only cockpit summaries only when stale-state labels and refresh paths are visible.
- Use saga or workflow compensation for cross-entity actions such as "generate artifact, attach sources, debit budget, and publish." Do not hide partial completion behind a single success flag.
- Record conflict-resolution policy for collaborative edits, source-note merges, user feedback, memory writes, and artifact revisions. Last-writer-wins is only acceptable when losing a concurrent update is harmless.
- Design replay drills around partition boundaries: replay one run, one source, one artifact, one route, and one tenant/workspace without assuming global ordering.
- Make delay sensitivity part of capacity and consistency planning: realtime paths prefer local progress and interruption; release, rights, billing, and publishing paths prefer stronger coordination.

## Datastore Objects To Add

| Object | Purpose |
|---|---|
| `distributed_system_assumption` | Fault model, synchrony assumption, network partition behavior, retry surface, and recovery expectation for a route or data family. |
| `consistency_contract` | Required consistency level, ordering scope, stale-read tolerance, conflict policy, and user-visible consequence. |
| `replication_topology_record` | Replica role, quorum rule, freshness target, failover behavior, reconciliation policy, and durability caveat. |
| `quorum_policy_record` | Read/write quorum sizes, read-repair/write-back rule, acknowledged-write condition, and linearizability caveat. |
| `linearizability_boundary` | Product operation that must respect real-time order, with evidence source, affected tables/events, and test case refs. |
| `eventual_consistency_policy` | Data family allowed to lag, maximum staleness, conflict handling, refresh trigger, and user-facing stale-state label. |
| `conflict_resolution_policy` | Merge semantics for concurrent writes: reject, reviewer merge, CRDT-style merge, multi-value preservation, or last-writer-wins with loss caveat. |
| `distributed_transaction_boundary` | Cross-entity workflow requiring atomic transaction, saga compensation, outbox, reviewer resume, or explicit partial-completion state. |
| `delay_sensitivity_record` | Route or operation sensitivity to network delay and the resulting consistency, coordination, timeout, and degradation choice. |

## Distributed Data Contract Release Gate

`distributed_data_contract_release_gate` is the promotion gate for any Agent Studio route or data family whose correctness depends on replication, event logs, projections, caches, queues, cross-entity workflows, or delayed distributed state. It turns "eventual consistency" and "event sourcing" from labels into explicit product contracts.

Required evidence:

- `gate_id`, `route_id`, `data_family_refs`, `candidate_release_id`, `distributed_system_assumption_refs`, `fault_model`, `synchrony_assumption`, `network_partition_policy`, and `retry_surface_refs`;
- `consistency_contract_refs`, `ordering_scope_refs`, `stale_read_tolerance_refs`, `user_visible_stale_state_refs`, and `delay_sensitivity_refs`;
- `replication_topology_refs`, `quorum_policy_refs`, `freshness_target_refs`, `failover_policy_refs`, `reconciliation_policy_refs`, and `durability_caveat_refs`;
- `linearizability_boundary_refs`, `real_time_order_test_refs`, `approval_or_release_state_refs`, `publish_action_refs`, and `billing_or_rights_state_refs` when those surfaces require stronger ordering;
- `event_topic_contract_refs`, `partition_key_policy_refs`, `replay_scope_refs`, `projection_rebuild_refs`, `notification_vs_persistent_event_policy_ref`, and `consumer_cursor_refs`;
- `conflict_resolution_policy_refs`, `collaborative_edit_policy_refs`, `memory_write_policy_refs`, `artifact_revision_policy_refs`, and `lost_update_risk_refs`;
- `distributed_transaction_boundary_refs`, `saga_compensation_refs`, `outbox_policy_refs`, `idempotency_contract_refs`, `partial_completion_state_refs`, `recovery_drill_refs`, `fallback_mode_refs`, `rollback_target_ref`, `decision`, and `reviewed_at`.

Do not promote a distributed route when:

- consistency is described only as "eventual" without stale-read tolerance, refresh trigger, user-visible consequence, and conflict behavior;
- event streams mix ephemeral notifications with persistent state transitions without replay semantics;
- partition keys do not match the object whose timeline must replay deterministically;
- quorum reads/writes are treated as linearizable without read-repair/write-back and real-time observation evidence;
- route releases, source-rights decisions, approvals, memory writes, artifact revisions, or publish actions can be reordered across reviewers without an explicit boundary;
- cross-entity workflows hide partial completion instead of using a transaction, outbox, saga, reviewer resume, or visible partial state;
- delayed realtime paths block on global coordination when local progress and interruption are the safer product behavior.

## Canon Decision

Agent Studio should treat distributed data design as a visible contract layer. Every important route or durable data family should say what can fail, what must be ordered, what can be stale, how conflicts resolve, how replay works, and what latency/coordination tradeoff is accepted. This keeps the system from relying on vague "eventual consistency" or "event sourcing" labels when the product actually needs specific guarantees for approvals, source truth, memory, cost, publishing, and route releases.
