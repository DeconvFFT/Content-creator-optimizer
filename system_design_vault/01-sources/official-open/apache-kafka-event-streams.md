---
type: source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://kafka.apache.org/42/
  - https://kafka.apache.org/42/getting-started/introduction/
  - https://kafka.apache.org/42/design/design/
  - https://kafka.apache.org/42/implementation/log/
  - https://kafka.apache.org/42/kafka-connect/overview/
  - https://kafka.apache.org/42/streams/core-concepts/
  - https://kafka.apache.org/42/streams/architecture/
source_status: official_public
verification_notes:
  - Apache Kafka 4.2 documentation opened directly from kafka.apache.org on 2026-05-18.
  - This note stores original synthesis only and does not copy source text or examples.
---

# Apache Kafka Event Streams

## Direct-Read Scope

Direct-read pass over official Apache Kafka 4.2 introduction, design, log implementation, Kafka Connect overview, Kafka Streams core concepts, and Kafka Streams architecture pages. The focus is not Kafka adoption by name; it is the event-log discipline Agent Studio needs for durable run history, ingestion replay, source refresh, route release, and long-running agent recovery.

This note is promoted to `canon_ready` after cross-check against [[postgresql-durability-and-consistency]], [[async-workflow-and-queue-reliability]], [[schema-api-evolution-and-compatibility]], [[../../03-patterns/system-design/production-agent-studio-canon]], and the datastore schema. The cross-check separates the durable event log from Postgres transaction/outbox boundaries, workflow task queues, event schema compatibility, and rebuildable projections.

## Core Read

Kafka treats events as durable records in partitioned topics. Producers and consumers are decoupled, topics can have multiple producers and subscribers, and consumers control their own position in the log. For Agent Studio, that maps cleanly to run timelines, ingestion events, artifact updates, feedback decisions, eval results, and route release changes: every event should be replayable without requiring hidden in-memory state.

Partitioning is the central design constraint. Events with the same key can preserve order within a partition, but global ordering is not free. Agent Studio should therefore choose keys deliberately: `run_id` for run timelines, `source_id` for source refresh, `artifact_id` for revision history, `route_id` for release/eval events, and `tenant_id` or workspace scope only when cross-run ordering matters more than parallelism.

Consumer position is product state. Processing before committing a position gives at-least-once behavior; committing before processing risks loss. Exactly-once behavior is strongest when reading and writing within Kafka topics using transactions and read-committed isolation. When writing to an external system, the practical requirement is to coordinate the consumer position with the external output or make the sink idempotent. Agent Studio should not promise generic exactly-once side effects for tool calls, uploads, publishing, emails, or external APIs.

Replication and committed messages clarify what durability means. A record is durable only under the configured acknowledgment, in-sync-replica, and leader-election conditions. Agent Studio's event ledger should expose similar release-facing language: which events are acknowledged, replicated, checkpointed, replayable, or only best-effort telemetry.

Log compaction is a different retention policy from time/size retention. It preserves the latest value per key while keeping offsets stable and maintaining order among retained records. For Agent Studio, compacted topics fit current-state projections such as latest source freshness, latest artifact status, provider capability snapshots, and route release state. They do not replace the full audit log when old intermediate events matter for incident review, eval regression, or legal/source provenance.

Kafka Streams reinforces the stream/table duality and the topology model. A stream is an ordered, replayable sequence of immutable records; a processing topology turns input streams into derived streams or state stores. Agent Studio should model source ingestion, retrieval indexing, eval aggregation, and route-monitoring jobs as topologies with source processors, transform nodes, sink processors, local state, and recovery behavior.

## Agent Studio Design Implications

- Treat `run_events` as an event log, not just an append-only table.
- Define an `event_topic_contract` for every durable event family: event type, partition key, ordering scope, retention policy, compaction policy, schema version, replay eligibility, and consumer group.
- Store `event_offset_record` or equivalent consumer cursor state for every background processor that derives artifacts, indexes, eval summaries, source freshness, or monitoring projections.
- Separate the full audit stream from compacted projections. A current-state table can be rebuilt from events, but it should not become the only record of what happened.
- Require idempotent sinks for side-effecting consumers. External publishing, media generation, notifications, uploads, and browser/computer actions need idempotency keys and replay behavior before they can consume retried events.
- Make partition-key selection a design review item. Poor keys can create hot partitions, broken ordering assumptions, or impossible replay boundaries.
- Store per-route delivery semantics: at-most-once, at-least-once with idempotent sink, transactional stream-to-stream, or manual/reviewer-mediated side effect.
- Attach schema-evolution rules to event families so old run events and source events remain decodable after route upgrades.
- Use stream-table projections for cockpit views: latest run state, artifact status, source freshness, eval pass/fail, provider health, and route rollout state.
- Use replay drills as reliability tests: rebuild a projection from event history and compare it with the live table.

## Datastore Objects To Add

| Object | Purpose |
|---|---|
| `event_topic_contract` | Event family contract with partition key, ordering scope, retention/compaction policy, schema version, replay eligibility, and allowed producers/consumers. |
| `event_offset_record` | Durable consumer position for a processor, including topic, partition, offset, processor version, last processed event, and commit policy. |
| `event_projection_record` | Derived table or view built from event streams, with source event families, rebuild command, freshness target, lag, and validation status. |
| `event_delivery_semantics` | Declared guarantee for a route or processor: at-most-once, at-least-once, transactional stream-to-stream, or external side-effect with idempotent sink. |
| `stream_processor_topology` | Source processors, transform nodes, state stores, sink processors, parallelism, partition dependencies, and failure/restart behavior. |
| `event_replay_drill` | Evidence that a projection or artifact can be rebuilt from events without hidden state. |
| `event_schema_version` | Schema version, compatibility rule, migration notes, decoder status, and affected event families. |

## Canon Decision

Agent Studio should use event streams as the source of operational truth for runs, ingestion, route releases, evals, artifacts, feedback, and monitoring. The implementation can start in Postgres, but the contract should already be Kafka-shaped: immutable events, explicit ordering scope, durable consumer positions, idempotent sinks, replayable projections, and clear delivery semantics. Without those contracts, "replayable run history" becomes a UI claim rather than a recoverable system property.

## Canon Release Gate

An event family is production-ready only when it has:

- an event-topic contract with event types, partition key, ordering scope, retention/compaction policy, schema version, producers, consumers, and replay eligibility;
- a schema compatibility policy and decoder check for historical events;
- a consumer offset/cursor record for every projection, indexer, monitor, and side-effecting processor;
- declared delivery semantics for every processor, including the transaction boundary and idempotent sink behavior;
- projection rebuild evidence comparing rebuilt state against the current table or view;
- partition-key review for hot-key risk, ordering assumptions, replay boundary, and tenant/workspace isolation;
- compaction review proving that compacted current-state topics do not replace the audit log when intermediate history matters;
- outbox or transaction coordination when events are emitted from Postgres-backed writes.
