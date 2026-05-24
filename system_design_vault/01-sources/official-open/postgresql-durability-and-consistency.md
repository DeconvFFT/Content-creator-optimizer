---
type: source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://www.postgresql.org/docs/current/
  - https://www.postgresql.org/docs/current/transaction-iso.html
  - https://www.postgresql.org/docs/current/mvcc.html
  - https://www.postgresql.org/docs/current/mvcc-serialization-failure-handling.html
  - https://www.postgresql.org/docs/current/explicit-locking.html
  - https://www.postgresql.org/docs/current/wal-intro.html
  - https://www.postgresql.org/docs/current/runtime-config-wal.html
  - https://www.postgresql.org/docs/current/continuous-archiving.html
  - https://www.postgresql.org/docs/current/warm-standby.html
  - https://www.postgresql.org/docs/current/logical-replication.html
  - https://www.postgresql.org/docs/current/logical-replication-architecture.html
  - https://www.postgresql.org/docs/current/logicaldecoding-explanation.html
source_status: official_public
verification_notes:
  - PostgreSQL current documentation resolved to PostgreSQL 18 on 2026-05-18, with the page banner showing PostgreSQL 18.4 released on 2026-05-14.
  - This note stores original synthesis only and does not copy source text or examples.
---

# PostgreSQL Durability And Consistency

## Direct-Read Scope

Direct-read pass over official PostgreSQL current documentation for transaction isolation, MVCC/concurrency control, serialization failure handling, explicit locks, write-ahead logging, WAL configuration, continuous archiving/PITR, streaming replication, logical replication, logical replication architecture, and logical decoding.

The goal is to make Agent Studio's Postgres commitment operationally precise: which writes are durable, which reads are consistent, which conflicts require retries, which projections are rebuildable, and which replication or CDC paths are safe enough for source-ledger and route-state work.

## Canon Cross-Check

Promoted to `canon_ready` after cross-check against [[apache-kafka-event-streams]], [[async-workflow-and-queue-reliability]], [[schema-api-evolution-and-compatibility]], [[../../03-patterns/system-design/production-agent-studio-canon]], [[../../04-agent-studio-implications/HLD - Agent Studio System Design]], and [[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]].

The cross-check separates four reliability planes that must not be conflated:

- PostgreSQL owns the local durable state, transaction invariants, PITR posture, replica freshness, and CDC/outbox boundary.
- Kafka-style event contracts own event-family ordering, partitioning, consumer cursors, delivery semantics, and projection replay.
- Workflow/queue systems own deterministic orchestration state, side-effect activities, retries, leases, quarantine, and redrive.
- Schema/API compatibility owns historical decodability, migration safety, consumer readiness, and deprecation windows.

Postgres is therefore canon for Agent Studio's state plane only when the route has a durable-state release gate. A route is not production-ready merely because it writes to Postgres; it must prove transaction consistency, WAL/PITR recovery, replica-read eligibility, logical-decoding or outbox duplicate handling, invariant checks, and schema migration safety.

## Core Read

Postgres uses MVCC so readers and writers can proceed concurrently, but isolation is a chosen contract, not magic. `READ COMMITTED` is the default and each statement sees a fresh committed snapshot. This is often right for simple single-row operations, but it can produce inconsistent command-level views for complex search-and-update logic. `REPEATABLE READ` gives a stable transaction snapshot and can raise serialization failures on conflicting updates. `SERIALIZABLE` gives the strongest application-level guarantee, but only if the application retries failed transactions and treats read results as provisional until commit succeeds.

Agent Studio should therefore classify every write path by consistency requirement. Simple event inserts, artifact inserts, and feedback inserts can often use default isolation plus unique constraints and idempotency keys. Route promotion, source freshness state transitions, eval gate decisions, and "only one active release" invariants need either serializable transactions, explicit locks, or carefully designed uniqueness constraints with retry logic.

Serialization failure handling is an application contract. Postgres exposes retryable failure classes, but it does not automatically retry because the whole decision logic must be rerun. Agent Studio should make retry boundaries explicit: a failed transaction should not reuse stale model/tool decisions that depended on a pre-abort read.

WAL is the base durability mechanism. Data-page changes are recoverable because the log is flushed before the data pages need to be. `fsync`, `synchronous_commit`, `wal_level`, checkpoint, archiving, and replication settings change the durability, latency, recovery, and change-capture behavior. Turning `fsync` off is not a product optimization for Agent Studio; it changes the system from durable product state to disposable scratch state.

Continuous archiving and PITR use the WAL stream plus a base backup to recover to a consistent point in time. This matters because Agent Studio's local-first store will contain source provenance, generated artifacts, feedback, eval results, and route release decisions. A backup that only dumps a subset of tables is not enough to prove recoverability of a whole event-ledger system.

Streaming replication is asynchronous by default, so a standby can lag and failover can lose recent acknowledged primary commits unless durability is configured appropriately. Synchronous replication can improve durability by waiting for standby confirmation, but it increases commit latency and needs careful placement and monitoring. Agent Studio should not read from replicas for "latest source state" or "latest route release" unless the read path knows its freshness and replay lag.

Logical replication and logical decoding turn WAL into a change stream. Publications/subscriptions can replicate subsets of data and preserve transactional order within a subscription, while logical decoding slots expose ordered changes to clients. But slots are stateful resources: they can resend recent changes after crashes, require consumers to handle duplicates, and can retain WAL or catalog rows if consumers stall. A CDC route is therefore not "set and forget"; it needs lag monitoring, duplicate handling, slot lifecycle policy, and failover behavior.

## Agent Studio Design Implications

- Treat Postgres as the durability plane only when `fsync`, WAL, backup, and recovery settings match product-state expectations.
- Define a `transaction_consistency_policy` per write path: isolation level, uniqueness constraints, lock strategy, retryable SQLSTATEs, idempotency key, and stale-read risk.
- Use `SERIALIZABLE` or explicit locking for release gates, source-state transitions, route version activation, and reviewer decisions where two concurrent actors must not both win.
- Retry the whole transaction and its decision logic after serialization failures; do not just replay the final SQL statement.
- Keep route/event writes small. Long transactions increase lock lifetime, retry cost, idle-in-transaction risk, and MVCC pressure.
- Treat `ON CONFLICT` upserts as useful idempotency tools, but not as a substitute for full invariant design.
- Add `postgres_durability_profile`: `fsync`, `synchronous_commit`, WAL level, checkpoint policy, archive mode, backup cadence, restore drill status, and replica/standby assumptions.
- Add `pitr_recovery_drill`: base backup, WAL archive range, restore target, recovered consistency check, and RPO/RTO evidence.
- Add `replica_freshness_record`: standby lag, replay LSN, read eligibility, route surfaces allowed to read stale state, and failover caveats.
- Add `logical_decoding_consumer`: slot name, output plugin, last processed LSN, duplicate-handling policy, lag, WAL retention risk, and failover status.
- Use logical decoding or trigger/outbox patterns only with explicit idempotent consumer behavior. A change stream can resend; consumers must tolerate it.
- Keep source ledgers, route-release state, and event projections in the same transactional boundary when they must be atomically visible.
- Add a `durable_state_release_gate` before promoting any route that mutates source ledgers, route releases, artifact revisions, memory, feedback, billing, publishing state, or eval evidence.
- Require the durable-state gate to include transaction policies, DB invariant checks, WAL/PITR posture, restore-drill evidence, replica-read policy, CDC/outbox duplicate handling, schema migration evidence, and event/projection coordination.

## Datastore Objects To Add

| Object | Purpose |
|---|---|
| `transaction_consistency_policy` | Declares isolation level, lock strategy, retry policy, uniqueness/idempotency constraints, and invariant scope for a write path. |
| `db_transaction_attempt` | Captures one transaction attempt, retryable SQLSTATE, decision inputs, commit/abort outcome, and replay boundary. |
| `postgres_durability_profile` | Records WAL/fsync/synchronous commit/checkpoint/archive/backup settings that determine durability and recovery behavior. |
| `pitr_recovery_drill` | Evidence that a base backup plus WAL archive can restore Agent Studio state to a target point. |
| `replica_freshness_record` | Tracks standby receive/replay lag and whether a route is allowed to read from that replica. |
| `logical_decoding_consumer` | Tracks replication slot, plugin/protocol, last LSN, duplicate handling, lag, WAL retention risk, and failover readiness. |
| `db_invariant_check` | Application-level invariant, transaction policy, validation query, conflict behavior, and release-blocking status. |
| `outbox_delivery_record` | Transactionally written side-effect event with idempotency key, consumer cursor, delivery attempts, and external side-effect status. |
| `durable_state_release_gate` | Promotion gate proving a route's database writes, recovery posture, replica-read policy, CDC/outbox behavior, invariant checks, and migration plan are safe enough for product state. |

## Canon Decision

Agent Studio can start with Postgres as the single durable product state plane, but the schema must distinguish ordinary committed writes from verified durability, recoverability, consistency, and replay guarantees. The minimum product-state contract is: WAL-backed persistence, safe fsync/synchronous-commit posture, transaction retry policy, explicit invariant protection, PITR/restore drills, replica freshness rules, idempotent outbox or CDC consumers, and a durable-state release gate for critical write paths. Without these, "local-first durable state" is an implementation preference rather than a reliable system guarantee.
