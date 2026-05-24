---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://docs.cohere.com/v2/reference/rerank
  - https://docs.cohere.com/v2/docs/rerank-overview
  - https://docs.voyageai.com/docs/reranker
  - https://docs.voyageai.com/reference/reranker-api
  - https://jina.ai/en-US/reranker/
  - https://www.sbert.net/docs/package_reference/cross_encoder/model.html
---

# Reranker Provider Runtime Contracts

## Source Boundary

This note synthesizes current official reranking docs from Cohere, Voyage AI, Jina AI, and SentenceTransformers CrossEncoder docs. It covers runtime contracts and Agent Studio datastore implications, not benchmark claims. The practical lesson is that reranking is a provider call or local model stage with its own limits, truncation behavior, score semantics, privacy boundary, latency, and false-negative risk.

## Provider Contract Lessons

Cohere's v2 rerank API makes the basic hosted-reranker shape explicit: a query, a document list, model ID, optional output cutoff, document token cap, request priority, relevance scores, result indices, and billed search units. Cohere also recommends YAML formatting for structured records, which matters for Agent Studio because table/code/email/source-card fields should not be collapsed into one ambiguous blob before reranking.

Voyage AI makes capacity limits first-class: model-specific query token limits, per-document context limits, total request-token limits, a maximum document count, optional `top_k`, optional document return, and a truncation switch. This is the strongest signal that Agent Studio needs a reranker route policy rather than a boolean `rerank=true`; candidate-pool size, truncation mode, and document-return policy directly change recall, privacy, latency, and auditability.

Jina's official API page frames reranking as a metered API endpoint with request-per-minute and token-per-minute limits, token usage based on input size, shared API-key billing/monitoring, and hosted/cloud/on-prem deployment options. For Agent Studio, Jina-style provider use should be represented as a provider boundary with quota buckets, deployment mode, token budget, and commercial/licensing posture, not just a model name.

SentenceTransformers CrossEncoder docs describe the local/open-source alternative: a cross-encoder jointly processes query-document pairs and outputs scores or labels, which improves pairwise relevance but cannot precompute standalone document vectors. Runtime behavior depends on model, max length, device, backend, activation/softmax choice, batch size, and hardware. Agent Studio should keep a local cross-encoder profile as an explicit fallback or private-source route, with its own latency and calibration evidence.

## Current-Source Cross-Check

Current Cohere v2 rerank docs still expose the hosted-reranker contract as query plus document list, model ID, output cutoff, document token cap, request priority, relevance scores, result indices, errors, and billed search units. The docs also still call out automatic truncation and structured-document formatting, which means Agent Studio must make rank-field serialization and truncation posture explicit.

Current Voyage reranker API docs still make model-specific query limits, per-document limits, total request-token limits, document-count limits, `top_k`, returned-document policy, and truncation behavior part of the API surface. Current Jina reranker docs still expose truncation, `top_n`, API key/billing, rate-limit posture, and hosted/cloud deployment choices. Current SentenceTransformers CrossEncoder docs still represent the local path where query-document pairs are scored at runtime with model, sequence length, backend, and batching behavior shaping latency and calibration.

The cross-check is that reranking is not an invisible quality booster. It is a runtime dependency that can drop evidence, leak fields to a provider, add latency/cost, and produce provider-specific scores that require route-level calibration and false-negative review.

## Agent Studio Design Implications

Provider-hosted reranking should happen after broad lexical/vector/metadata/graph retrieval and deduplication, not before recall has been established. The input candidate count should be selected by eval, then reduced to a final context pack by a provider-specific route policy.

Reranker scores are not universal confidence scores. They are model/provider-specific ordering signals. Agent Studio should store original rank, reranked rank, score, kept/dropped decision, and calibration bucket per candidate; downstream claim verification still needs source support.

Truncation is a correctness risk. Silent truncation can turn a relevant source into a false negative if the answer-bearing section is outside the retained window. Every reranker event should record whether truncation was enabled, which fields were sent, approximate token pressure, and candidate IDs selected for false-negative review.

Structured documents need a rank-field contract. For source cards, emails, tables, code snippets, PRDs, and book chunks, the route should declare which fields leave the local boundary, how they are serialized, and whether sensitive fields are redacted, hashed, omitted, or kept local for a CrossEncoder-only route.

Hosted reranking is an external dependency. It needs timeout, retry, quota, privacy, retention, fallback, cost, and outage behavior. A retrieval route should be able to degrade to deterministic scoring, local CrossEncoder, smaller candidate pools, or source-ledger-only answers without silently publishing weaker evidence.

## Datastore Requirements

Agent Studio needs provider-neutral records for:

- provider capability: endpoint, model, document limits, token limits, score semantics, billing unit, deployment mode, supported document shape, and privacy boundary;
- route policy: candidate-pool size, final output count, fields serialized, truncation mode, timeout, retry, fallback, budget, and eval references;
- request event: trace ID, provider/model, input/output counts, query hash, document hashes, rank fields, truncation flag, latency, usage units, and error class;
- score snapshot: candidate ID, original rank, reranked rank, score, calibration bucket, kept/dropped decision, and rejection reason;
- false-negative review: dropped candidate, expected relevance, cause, reviewer, and corrective action;
- provider eval: dataset, route, provider/model, pool size, cutoff, ranking metrics, latency, cost, privacy notes, and promotion decision;
- local cross-encoder profile: model, device/backend, max length, batch policy, quantization/precision, throughput, latency, and fallback role;
- privacy policy: allowed fields, redaction strategy, retention posture, sensitive-source handling, and provider eligibility.
- `reranker_release_gate`: promotion gate binding provider capability, route policy, candidate-pool size, final output count, rank-field serialization, truncation policy, privacy policy, quota/budget, timeout/retry/fallback, request-event tracing, score-snapshot policy, false-negative review samples, provider evals, local CrossEncoder fallback, latency/cost evidence, and rollback target.

## Agent Studio Operating Rule

Reranking is a release-managed route stage. A production retrieval route must know which reranker ran, what it was allowed to see, which candidates it moved or dropped, how much it cost, how slow it was, and how its false negatives are audited.

## Release Gate

A reranked retrieval route cannot be promoted unless a `reranker_release_gate` proves provider or local capability, route policy, candidate-pool and final-output settings, rank-field serialization, truncation behavior, privacy and retention posture, timeout/retry/quota/budget controls, local fallback or deterministic degradation, score-snapshot capture, false-negative audit coverage, provider eval comparison, latency/cost evidence, and rollback to the prior reranker or no-rerank policy.

## Canon Decision

This note is canon-ready for Agent Studio reranking architecture. Rerankers are high-impact retrieval stages, not helper functions: they require release records because they decide which evidence survives into the final context pack.
