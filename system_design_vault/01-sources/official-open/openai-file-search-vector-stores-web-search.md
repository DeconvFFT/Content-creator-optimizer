---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
rights_status: official_public
provenance_status: official_openai_retrieval_search_docs_direct_read
sources:
  - https://developers.openai.com/api/docs/guides/tools-file-search
  - https://developers.openai.com/api/docs/guides/retrieval
  - https://developers.openai.com/api/reference/resources/vector_stores
  - https://developers.openai.com/api/docs/guides/tools-web-search
---

# OpenAI File Search, Vector Stores, And Web Search

## Scope

Direct-read synthesis from current official OpenAI API documentation for hosted file search, retrieval/vector stores, vector-store API reference, and hosted web search. This note captures Agent Studio datastore and route implications. It stores no copied code blocks, raw docs text, or long excerpts.

## Core Pattern

OpenAI's hosted retrieval path has two different evidence systems:

- `file_search` searches files previously uploaded into OpenAI-managed vector stores.
- `web_search` searches the public web and returns URL-citation annotations and optional full source-list details.

Both are useful provider tools, but neither should become the only source ledger. Agent Studio still needs local source records, rights status, chunk/index releases, query traces, accepted/rejected evidence, citation checks, and retention policy. Provider-hosted search can be a route capability; the local vault remains the audit authority.

## File Search Contract

File search is a Responses API tool backed by vector stores. The operational lifecycle is: upload file, create or select vector store, attach file, wait for processing completion, then expose selected vector stores to a model route.

Agent Studio should model this as a governed ingestion and route-release sequence:

- source file identity and local provenance before upload;
- provider file ID after upload;
- vector store identity and status;
- vector store file status and failure state;
- processing completion evidence before route promotion;
- vector store IDs allowed by route;
- output annotations and citation validation;
- optional returned search results when trace inspection is needed.

Search-result inclusion is explicit. If a route needs retrieval diagnostics, evals, or reviewer-visible evidence packs, it must request and store provider search-result summaries or references. Otherwise, final message citations alone are insufficient for tuning recall, ranking, and rejection policy.

## Ranking And Filtering

OpenAI's retrieval guide exposes several route-sensitive knobs: metadata attributes on vector-store files, boolean filters, ranking options, score thresholds, per-file chunking settings, file batches, and expiration policies. Current file-search docs describe hosted semantic and keyword search, but do not expose a route-level hybrid-weight control in the current official surface.

Agent Studio implications:

- Metadata filters are policy boundaries, not convenience parameters. Tenant, project, confidentiality, language, source type, freshness, and rights filters should be stored as route policy and retrieval trace fields.
- Score thresholds trade recall for precision. A higher threshold can hide useful evidence, so changes need eval coverage and false-negative review.
- Keyword and semantic behavior is still release-relevant even when the provider does not expose explicit weights. API names, filenames, model IDs, policy names, dates, and rare technical terms need recall tests and false-negative review.
- `max_num_results` is a latency/cost/context budget control, not a quality guarantee. It should be tuned with retrieval recall and answer faithfulness metrics.

## Current-Source Cross-Check

Current OpenAI file-search guidance still frames file search as a hosted Responses API tool backed by vector stores, where files must be uploaded, attached, processed, and then exposed to routes through selected vector stores. It also still distinguishes user-visible annotations from optional returned search results, so Agent Studio should request result inclusion when eval, debugging, or reviewer evidence requires the candidate list.

Current OpenAI retrieval and vector-store reference docs support treating vector stores as release-managed resources: vector store and vector store file statuses, file counts, failure states, usage bytes, expiration policy, file attributes, chunking strategy, file batches, and per-file limits are all provider state that can change retrieval behavior or cost.

Current OpenAI web-search guidance supports route-level web policy: tool-choice behavior, domain allowlists/blocklists, complete source-list inclusion, inline citations, approximate user location, and Responses API versus specialized search-model differences should be represented as route fields and trace evidence, not prompt-only instructions.

## Vector Store Lifecycle

Vector stores are provider-side containers of processed files. File attachment and batch processing can be asynchronous; files can be in progress, completed, cancelled, or failed. Removal can be eventually consistent for a short period, so search may temporarily return content from removed files.

Agent Studio should store:

- vector store release state: candidate, processing, validated, active, draining, expired, retired;
- provider file counts and failed-file counts;
- last-active and expiration policy;
- chunking strategy and chunk-size/overlap settings;
- upload and processing run IDs;
- route references that depend on a store;
- deletion/removal event plus consistency grace window;
- cost/usage byte snapshots.

The default chunking behavior is useful as a baseline, but production routes should not rely on it invisibly. Chunk size and overlap affect recall, latency, duplication, and citation quality, so they belong in index-release records and eval comparisons.

## Web Search Contract

OpenAI web search can run as a Responses API tool where the model may decide whether to search, or be required to search through tool-choice policy. Chat Completions search uses a different specialized-model path and lacks several Responses API controls.

For Agent Studio, a web-search-backed route should persist:

- whether search was optional or required;
- search context size or returned-token budget policy where available;
- allowed-domain and blocked-domain filters;
- live internet access setting versus cached/indexed-only search;
- approximate user-location fields when the task depends on geography;
- web-search call sources when requested;
- visible clickable URL citations for user-facing outputs;
- source freshness and contradiction checks before publishing claims.

Domain filters are especially important for high-stakes or official-source routes. A route that claims "official docs only" should store that domain allowlist in the route release, not just in prompt text.

## Datastore Additions

| Object | Purpose | Key fields |
|---|---|---|
| `provider_vector_store_record` | Provider-side vector-store identity and lifecycle | `provider`, `vector_store_id`, `name`, `status`, `file_counts`, `usage_bytes`, `last_active_at`, `expires_after`, `created_at`, `route_refs` |
| `provider_vector_store_file_record` | File attachment and processing state | `provider_file_id`, `source_id`, `vector_store_id`, `processing_status`, `failure_reason`, `attributes_hash`, `chunking_strategy_ref`, `uploaded_at`, `completed_at` |
| `hosted_retrieval_policy` | Route policy for hosted file search | `route_id`, `vector_store_refs`, `metadata_filter_policy`, `max_num_results`, `ranking_options`, `score_threshold`, `ranker`, `keyword_semantic_behavior_notes`, `result_include_policy`, `citation_policy` |
| `hosted_retrieval_trace` | Per-run hosted file-search evidence | `run_id`, `file_search_call_id`, `queries`, `filters`, `candidate_refs`, `accepted_refs`, `dropped_refs`, `scores_or_ranks`, `latency`, `annotations` |
| `vector_store_chunking_release` | Provider chunking settings tied to a store/file batch | `chunking_release_id`, `vector_store_id`, `strategy`, `max_chunk_size_tokens`, `chunk_overlap_tokens`, `source_snapshot_refs`, `eval_refs`, `status` |
| `web_search_policy` | Route policy for hosted web search | `route_id`, `tool_choice_policy`, `allowed_domains`, `blocked_domains`, `external_web_access`, `user_location_policy`, `context_size_policy`, `source_list_include_policy` |
| `web_search_trace` | Per-run web-search evidence and source list | `run_id`, `web_search_call_id`, `query_summary`, `search_required`, `sources_returned`, `url_citation_refs`, `domain_filter_refs`, `freshness_check_refs`, `latency` |
| `citation_visibility_check` | UI and artifact check for cited search sources | `artifact_id`, `citation_type`, `source_refs`, `visible_to_user`, `clickable`, `span_or_anchor_refs`, `review_status` |
| `hosted_search_release_gate` | Promotion gate for provider-hosted file search or web search routes | `gate_id`, `route_release_id`, `provider_vector_store_refs`, `provider_vector_store_file_refs`, `chunking_release_refs`, `hosted_retrieval_policy_ref`, `web_search_policy_ref`, `retrieval_eval_refs`, `citation_visibility_refs`, `source_rights_refs`, `freshness_policy_ref`, `consistency_grace_policy`, `decision`, `reviewed_at` |

## Release Gates

Do not promote a hosted retrieval/search route when:

- vector-store file processing status is unknown or failed;
- local source records are missing for uploaded files;
- chunking settings are not recorded;
- metadata filters are implemented only in prompt text;
- max-result limits or score thresholds changed without recall/precision checks;
- citations are shown without verifying source identity and support;
- provider search results are not retained or summarized enough for eval/debug needs;
- web search is optional for freshness-critical tasks without fallback review;
- domain allowlists/blocklists are absent for official-source or high-stakes tasks;
- live web access, location, and source-list inclusion settings are not declared;
- removed/expired files might still be served and the route has no consistency grace policy.

## Agent Studio Decision

This note is canon-ready for Agent Studio hosted retrieval/search architecture. Use OpenAI hosted file search and web search as provider capabilities behind an Agent Studio source ledger. The product should keep local source truth, route retrieval policy, provider vector-store lifecycle, retrieval traces, web-search traces, citation visibility, and hosted-search release gates separate. Hosted tools can reduce implementation burden, but they do not remove the need for provenance, recall testing, access control, and auditability.
