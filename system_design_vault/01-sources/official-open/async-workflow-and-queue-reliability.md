---
type: source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://docs.temporal.io/workflows
  - https://docs.temporal.io/activities
  - https://docs.temporal.io/encyclopedia/retry-policies
  - https://docs.temporal.io/workers
  - https://docs.temporal.io/task-queue
  - https://docs.temporal.io/evaluate/development-production-features/failure-detection
  - https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues.html
  - https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-fifo-queues.html
  - https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html
  - https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html
  - https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/best-practices-message-deduplication.html
  - https://docs.cloud.google.com/tasks/docs/dual-overview
  - https://docs.cloud.google.com/tasks/docs/configuring-queues
source_status: official_public
verification_notes:
  - Temporal docs, AWS SQS docs, and Google Cloud Tasks docs opened directly on 2026-05-18.
  - Google Cloud Tasks page showed last updated 2026-05-15 UTC.
  - This note stores original synthesis only and does not copy source text or examples.
---

# Async Workflow And Queue Reliability

## Direct-Read Scope

Direct-read pass over official Temporal workflow/activity/retry/worker/task-queue/failure-detection docs, AWS SQS standard/FIFO/visibility-timeout/DLQ/deduplication docs, and Google Cloud Tasks overview/configuration docs.

This note is promoted to `canon_ready` after cross-check against [[aws-builders-library-resilience]], [[apache-kafka-event-streams]], [[schema-api-evolution-and-compatibility]], [[../../03-patterns/system-design/production-agent-studio-canon]], and the datastore schema. The cross-check separates workflow state, event truth, queue dispatch, side-effect activities, retry ownership, and schema evolution so no queue is treated as a correctness guarantee by itself.

This note fills the async execution gap between Agent Studio's event ledger and its worker fleet. Event logs record what happened; async workflow and queue contracts decide what work is pending, who can pick it up, when it retries, how long it may run, how failures surface, and whether repeated execution is safe.

## Core Read

Temporal separates deterministic workflow orchestration from fallible activity execution. Workflow state is rebuilt by replaying ordered event history, so workflow code must make the same decisions on replay and must not directly call non-deterministic dependencies. Activities are where external I/O belongs: API calls, database queries, LLM calls, file work, downloads, media processing, and other operations that can fail. Activity results are recorded in workflow history; replay reuses the recorded result instead of doing the work again.

For Agent Studio, this maps cleanly to long-running content pipelines. The workflow owns route state: source selected, extraction started, embedding requested, eval queued, reviewer interrupt pending, artifact approved. Activities own side effects: reading a file, calling a provider, uploading an artifact, producing audio, running OCR, or notifying a user. That split is critical because replayable orchestration is not the same thing as repeatable side effects.

Temporal retry policy adds the failure taxonomy: activities are retryable by default with exponential backoff, while whole workflows are not normally retried by default. This is a useful rule for Agent Studio: retry the failing activity when a provider, tool, media step, or extractor fails; do not blindly restart a whole multi-step run and risk duplicating side effects or losing the reason a gate failed.

Temporal task queues and workers provide the routing layer. A worker entity polls a single task queue, pulls work only when it has spare capacity, and can be scaled horizontally. Task queues persist workflow and activity tasks when workers are down. Queue names and worker registrations are therefore deployment contracts, not implementation details. A worker that listens to a queue must actually know how to process the task types on that queue.

AWS SQS and Google Cloud Tasks add queue-level delivery and backpressure lessons. Standard SQS is at-least-once and can deliver duplicates or out-of-order messages; FIFO queues add ordering and deduplication constraints but have throughput tradeoffs. Visibility timeout is a lease, not a lock: if a worker fails to delete the message before the timeout expires, the message becomes eligible again. DLQs isolate repeatedly failing messages for inspection and redrive, but using DLQs with strict FIFO workflows can break operation order. Cloud Tasks similarly frames async work as durable, at-least-once dispatch with rate limits, retry parameters, task deduplication by name, and HTTP success semantics.

The common design rule is that a queue is not a correctness proof. It provides durable dispatch and backpressure, but handlers must be idempotent, retries must be bounded or observable, failed work must be inspectable, and queue configuration must match workload shape.

## Agent Studio Design Implications

- Split durable orchestration from side effects. Route workflows should be deterministic state machines; provider calls, file extraction, media generation, publishing, notifications, and browser/computer actions should run as activities or jobs with explicit idempotency.
- Define workload-specific task queues: realtime support, source extraction, embedding/indexing, eval judging, media generation, publishing, cleanup, and low-priority backfills should not share one generic worker lane.
- Each queue needs rate limits, concurrency limits, retry policy, timeout/visibility lease, max attempts or max retry duration, DLQ/quarantine policy, and owner.
- Store worker registration evidence: queue name, worker version, supported workflow/activity types, deployment identity, region, resource class, and last heartbeat/poll time.
- Treat at-least-once delivery as the default. Every task handler needs an idempotency key and a side-effect ledger before it can call external APIs or write user-visible artifacts.
- Use FIFO/message-group semantics only for work that truly needs per-key order, such as one artifact revision chain, one route release, one source refresh stream, or one publishing destination. Do not serialize unrelated work.
- Use DLQ/quarantine records for repeated failures, but preserve ordering caveats for ordered queues.
- Use visibility leases/heartbeats for long-running work and break work into smaller steps when one job can exceed queue lease limits.
- Record retry classification: transient provider error, throttling, worker crash, malformed input, permanent policy block, source unavailable, or human action required.
- Queue metrics should become release evidence: backlog depth, oldest age, in-flight count, retry count, DLQ count, dispatch rate, worker poll rate, lease extensions, and timeout rate.
- For Cloud Tasks-style HTTP jobs, handler success must map to explicit durable state, not just a 2xx response.
- Prefer replayable workflow history for long-running multi-step routes; use plain queues for independent one-shot jobs.

## Datastore Objects To Add

| Object | Purpose |
|---|---|
| `workflow_execution_record` | Durable workflow instance with workflow type, input refs, event history refs, replay status, current state, and terminal outcome. |
| `activity_execution_record` | Side-effecting activity attempt with task queue, activity type, input/output artifact refs, timeout policy, retry policy, idempotency key, and result. |
| `task_queue_contract` | Queue name, workload class, ordering scope, rate/concurrency limits, timeout/visibility lease, retry policy, DLQ/quarantine policy, and allowed worker types. |
| `worker_registration_record` | Worker identity, queue subscriptions, registered workflow/activity types, version, resource class, region, heartbeat/poll status, and deployment ref. |
| `retry_policy_record` | Initial interval, backoff coefficient, max interval, max attempts, max retry duration, non-retryable error types, and owner. |
| `task_attempt_record` | One dispatch/attempt with attempt number, lease deadline, heartbeat/extension refs, status, error class, and next action. |
| `dead_letter_record` | Failed task/message moved to quarantine with source queue, receive count, failure summary, payload hash, redrive decision, and reviewer. |
| `queue_backpressure_signal` | Queue depth, oldest age, in-flight count, retry rate, DLQ count, dispatch rate, worker capacity, and affected route surfaces. |
| `handler_idempotency_record` | Idempotency key, side-effect class, first successful result, duplicate attempt behavior, and conflict status. |

## Canon Decision

Agent Studio should use a layered async model: event ledger for truth, workflow execution for long-running route state, task queues for dispatch/backpressure, activities/jobs for side effects, and idempotency records for repeated execution. The minimum release contract for any background lane is: queue contract, worker registration, timeout/lease policy, retry policy, DLQ/quarantine path, idempotent handler, queue metrics, and replay or redrive drill.

## Canon Release Gate

A background lane is production-ready only when the following evidence exists:

- the workflow owns deterministic route state and non-deterministic I/O is isolated into activities or jobs;
- the queue contract declares workload class, ordering scope, timeout/visibility lease, retry policy, DLQ/quarantine behavior, rate limit, and concurrency limit;
- worker registration proves the deployed worker version can process the declared workflow and activity types;
- at-least-once delivery is assumed and every side-effecting handler has an idempotency key and duplicate-attempt behavior;
- ordered/FIFO routing is scoped to a single entity that truly needs order, such as one artifact revision chain, route release, source refresh stream, or publishing destination;
- queue health metrics include backlog age, in-flight count, retry rate, DLQ count, worker poll rate, lease extensions, and timeout rate;
- replay, redrive, and quarantine drills have been run before the lane is allowed to carry user-facing work.
