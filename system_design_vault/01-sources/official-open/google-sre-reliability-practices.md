---
type: source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://sre.google/books/
  - https://sre.google/sre-book/service-level-objectives/
  - https://sre.google/workbook/alerting-on-slos/
  - https://sre.google/sre-book/service-best-practices/
  - https://sre.google/sre-book/postmortem-culture/
  - https://sre.google/sre-book/eliminating-toil/
  - https://sre.google/workbook/error-budget-policy/
related:
  - "[[scale-and-reliability-sources]]"
  - "[[aws-builders-library-resilience]]"
  - "[[netflix-load-spike-prioritized-shedding]]"
  - "[[../../03-patterns/system-design/production-agent-studio-canon]]"
  - "[[../../04-agent-studio-implications/HLD - Agent Studio System Design]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
source_status: official_or_open_public
verification_notes:
  - Google SRE book/workbook pages were opened directly on 2026-05-18.
  - This note stores original synthesis only and does not copy book text, tables, examples, or long excerpts.
---

# Google SRE Reliability Practices

## Direct-Read Scope

Direct-read pass over official Google SRE book/workbook pages for SLOs, SLO-based alerting, production service best practices, postmortem culture, toil, and error-budget policy. This note narrows the broad "Google SRE books" citation into concrete Agent Studio release and operations controls.

## Canon Cross-Check

Promoted to `canon_ready` after cross-check against [[scale-and-reliability-sources]], [[aws-builders-library-resilience]], [[netflix-load-spike-prioritized-shedding]], [[async-workflow-and-queue-reliability]], [[apache-kafka-event-streams]], [[postgresql-durability-and-consistency]], [[../../03-patterns/system-design/production-agent-studio-canon]], [[../../04-agent-studio-implications/HLD - Agent Studio System Design]], and [[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]].

The cross-check sets this boundary:

- SRE defines user-visible reliability targets, error-budget release control, alert actionability, incident learning, and toil pressure.
- AWS Builders Library defines dependency mechanics: timeout ownership, retry budgets, backoff/jitter, idempotency, static stability, and dependency isolation.
- Netflix shedding defines overload behavior: criticality tags, lane-local saturation, success/failure buffers, and shed/defer order.
- Async/event/Postgres notes define execution and state guarantees: workflow replay, queue redrive, event-family replay, durable transactions, and recoverability.

SRE is therefore canon for Agent Studio's reliability decision plane. A route is not production-ready until its quality, freshness, latency, safety, source coverage, artifact durability, and publishing outcomes have SLIs, SLOs, error-budget policy, alert classification, incident triggers, toil tracking, and release-gate consequences.

## Core Read

SRE starts with user-visible behavior, not machine convenience. SLIs should represent what users experience: availability, latency, throughput, durability, correctness, freshness, or end-to-end pipeline delay. For Agent Studio, server-side provider latency alone is insufficient. The product needs SLIs for source-backed answer correctness, citation coverage, artifact durability, realtime turn timing, first-audio/text response, feedback save durability, publish safety, and ingestion freshness.

Averages are dangerous for interactive systems. Google SRE emphasizes distributions and tail latency because a small fraction of slow requests can dominate user experience. Agent Studio should track p50/p90/p99 or similar buckets for realtime voice, retrieval, reranking, model calls, browser/computer-use tools, source extraction, and artifact rendering. A route that looks healthy by average latency can still be unusable in the tails.

SLOs are product decisions. They should specify measurement window, valid conditions, workload class, and user impact. Agent Studio should define separate SLOs for foreground conversation, realtime voice, long-running synthesis, source ingestion, eval execution, media generation, and publishing rather than using one uptime target.

Error budgets turn reliability into a release-control mechanism. If a route burns its budget, new risky feature work should pause or require review while reliability work moves forward. For Agent Studio, this applies to quality and safety budgets too: unsupported-claim rate, stale-source rate, failed-eval rate, provider-fallback rate, publish-block rate, and voice-interruption failure should all be able to freeze a route promotion.

Alerting should page only for actionable, significant budget burn. A good alert is not "a metric crossed a line"; it is a signal that human action is needed now. Agent Studio should separate pages, tickets, and logs: realtime outage and publish-risk issues may page; slow embedding refresh or stale secondary sources can become tickets; routine eval distributions can remain logs/dashboard data.

Postmortems are system-learning artifacts. They should trigger on user-visible degradation, data loss, manual intervention, long resolution time, monitoring failure, or stakeholder request. For Agent Studio, postmortems should become eval cases, route-change proposals, source-ledger updates, runbook changes, and schema/control-plane fixes.

Toil limits matter for an agent studio because repeated human cleanup is a product smell. If reviewers repeatedly fix the same citation failure, unsupported claim, routing error, prompt leak, or tool approval confusion, the response should be engineering: improve evals, route logic, source policies, UI state, or automation. Human judgment should gate genuinely hard decisions, not compensate for avoidable system design gaps.

## Agent Studio Design Implications

- Define `sli_record` before each `slo_record`: what is measured, where it is measured, aggregation method, client/server perspective, and quality caveat.
- Track route SLOs by workload class: realtime, foreground, background, ingestion, eval, media, publishing, and maintenance.
- Use distribution-aware latency and quality metrics, not averages only.
- Treat correctness and source quality as reliability surfaces: unsupported claim rate, source coverage, stale-source rate, retrieval miss rate, and citation validity belong beside latency and availability.
- Gate route releases on error-budget state. If budget is exhausted, route changes should freeze except for reliability, safety, or urgent bug fixes.
- Convert SLO burn into alert classes: page, ticket, or log/dashboard.
- Add postmortem triggers before incidents happen.
- Link postmortems to durable corrective artifacts: eval cases, regression slices, runbook updates, schema changes, route-change proposals, and source-ledger fixes.
- Track toil caused by repeated manual reviews, reviewer overrides, recurring prompt fixes, repeated source cleanup, and operational interrupts. Recurring toil should create engineering backlog, not permanent process.
- Require a `reliability_release_gate` for every route promotion that can affect user-visible answers, source freshness, artifact durability, voice/realtime behavior, eval state, or external publishing.
- Treat SLOs as route-specific contracts, not global dashboards. A background ingestion SLO, a realtime voice SLO, a retrieval coverage SLO, and a publishing safety SLO can burn for different reasons and should drive different actions.
- Link error-budget exceptions to named reviewers and corrective work. An exception without an owner, expiry, and compensating control is just silent reliability debt.

## Datastore Objects To Add Or Strengthen

| Object | Requirement |
|---|---|
| `sli_record` | Metric definition, user-visible behavior, collection point, aggregation/window, distribution buckets, and proxy caveat. |
| `slo_record` | Add workload class, valid conditions, target distribution/threshold, user-impact rationale, and advertised/internal target split. |
| `error_budget_record` | Track budget spend, burn rate, release-freeze state, exception policy, and route-change link. |
| `slo_burn_alert_policy` | Burn-rate rule, alert class, notification target, detection/reset expectations, and actionability test. |
| `alert_event_record` | Page/ticket/log event with linked SLI/SLO, burn evidence, action taken, and false-positive review. |
| `postmortem_record` | Add trigger class, impact scope, monitoring failure flag, contributing factors, corrective actions, eval/source/route links, and review status. |
| `toil_record` | Repetitive/manual/interrupt-driven operational work, source, frequency, owner, automation candidate, and backlog link. |
| `reliability_release_gate` | Release freeze/allow decision based on SLO, error budget, incident, postmortem, and toil evidence. |
| `error_budget_exception` | Explicit reviewer-approved exception with scope, expiry, compensating control, and linked reliability work. |

## Canon Decision

Agent Studio should treat reliability as a source-backed release gate. A route is not production-ready until it has user-visible SLIs, explicit SLOs, error-budget policy, actionable alert classes, postmortem triggers, a toil-reduction path, and release consequences when budgets burn. Quality, source correctness, safety, and freshness are reliability dimensions for this product, not optional analytics.
