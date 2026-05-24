---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_doc_page
rights_status: official_or_open_public
stores_raw_source_text: false
stores_long_excerpts: false
sources:
  - https://www.rfc-editor.org/rfc/rfc9309
  - https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec
  - https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
  - https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
  - https://commoncrawl.org/overview
  - https://commoncrawl.org/get-started
  - https://commoncrawl.org/faq
  - https://commoncrawl.org/terms-of-use
related:
  - [[../../02-lectures/stanford/cs336-data-and-alignment]]
  - [[../../03-patterns/system-design/production-agent-studio-canon]]
  - [[document-layout-ocr-ingestion-runtime]]
  - [[privacy-retention-data-boundaries]]
---

# Web Source Acquisition And Crawl Governance

## Source Scope

This note synthesizes official/open crawling and web-source documentation from RFC 9309, Google Search Central crawler/canonical/sitemap guidance, and Common Crawl's official corpus and FAQ pages. It is about Agent Studio's source-acquisition control plane, not SEO advice or bulk web scraping. It stores no raw webpage text or long excerpts.

## Core Synthesis

Official web-source ingestion needs a source-acquisition ledger before extraction or chunking. A URL is not enough. The system should know how the URL was discovered, whether crawling was allowed for the current user agent, what canonical URL should represent duplicate content, what freshness signal exists, what HTTP result was observed, and what rights/terms boundary applies.

RFC 9309 is the baseline reminder: robots.txt is a protocol that crawlers are requested to honor; it is not access authorization. Agent Studio should treat robots checks as an acquisition policy input, not as proof that downstream use is legally or product-safe. A route can be allowed to fetch a page and still be barred from storing, training on, republishing, or exposing content by terms, license, privacy, or product policy.

Google's robots guidance adds operational detail that matters for implementation:

- robots rules are scoped by host, protocol, and port;
- robots files are fetched from the site root;
- HTTP status and fetch errors affect whether a crawler can know the current rules;
- rules are path-sensitive and case-sensitive in their values;
- sitemap entries in robots are discovery hints, not per-user-agent rules;
- robots should not be used for canonicalization or indexing decisions.

Sitemaps and canonical URLs are separate acquisition signals. Sitemaps help discover preferred URLs and freshness hints, but they do not guarantee that a crawler should fetch, trust, or promote a page. Canonical URLs help collapse duplicates and tracking variants; they should not erase provenance. Agent Studio needs both the canonical page identity and the observed URL that produced the artifact.

Common Crawl is useful as an open web corpus but should be treated as a bulk historical snapshot, not as a rights-clean substitute for current official sources. Its official docs describe regularly collected crawl data, raw page data, metadata extracts, text extracts, free access through public datasets, crawler identity, robots checking before fetch, redirect limits, and terms-of-use boundaries. For Agent Studio, Common Crawl is best suited for broad background research or corpus statistics, while current official docs remain the source of truth for product architecture decisions.

## Current-Source Cross-Check

Current RFC 9309 and Google crawler guidance still require robots decisions to be scoped by user agent, host, protocol, port, path matching, redirects, HTTP error behavior, parser limits, and cache lifetime. The important architecture point is unchanged: a robots policy check is acquisition evidence, not copyright, privacy, terms, or product eligibility.

Current Google Search Central sitemap and canonical guidance still treats sitemaps as discovery/freshness/canonical hints and canonicalization as a signal stack across redirects, `rel=canonical`, HTTP link headers, and sitemap inclusion. Agent Studio should therefore store sitemap and canonical signals as evidence with confidence and conflict notes, not as destructive URL rewriting.

Current Common Crawl pages still describe the corpus as regularly collected web data with raw page data, metadata extracts, text extracts, public-data access, crawler identity, robots checks, rate/backoff behavior, sitemap use, and terms-of-use caveats. Cross-checking this with the Stanford CS336 Common Crawl data-pipeline note reinforces that bulk crawl material must preserve snapshot IDs, projection type, extraction loss, filter counters, dedupe state, and validation leakage checks before any derived note or retrieval artifact is trusted.

## Agent Studio Acquisition Model

Web-source ingestion should follow this order:

1. Discover candidate URL from an official page, sitemap, known docs index, API docs navigation, course schedule, repository, or user-provided link.
2. Normalize URL and capture redirect chain, canonical hint, sitemap source, discovered anchor text, and referring source.
3. Check robots/source-access policy for the intended fetch mode and user agent.
4. Capture HTTP metadata, content type, response hash, fetch time, cache validators, and final URL.
5. Classify rights and allowed use separately from crawl allowance.
6. Extract with a source-type-specific parser and record extraction loss.
7. Chunk/index only after source eligibility and extraction quality pass.
8. Refresh on explicit cadence using ETag, Last-Modified, sitemap `lastmod`, provider changelog, or manual source-watch policy.

## Datastore Commitments

| Record | Purpose | Minimum fields |
|---|---|---|
| `web_source_candidate` | Candidate URL before fetch or extraction. | `candidate_id`, `discovered_url`, `discovery_source_ref`, `anchor_or_listing_context`, `source_owner`, `expected_source_class`, `discovered_at`, `status` |
| `robots_policy_check` | Crawl-policy evidence for a URL and user agent. | `robots_check_id`, `candidate_id`, `robots_url`, `user_agent`, `scope_host_protocol_port`, `fetch_status`, `matched_rule`, `allowed_to_fetch`, `checked_at`, `cache_until`, `error_policy` |
| `web_fetch_record` | HTTP fetch and redirect evidence. | `fetch_id`, `candidate_id`, `requested_url`, `final_url`, `redirect_chain_hash`, `status_code`, `content_type`, `content_length`, `etag`, `last_modified`, `response_hash`, `fetched_at` |
| `canonical_url_record` | Duplicate/canonical mapping without losing provenance. | `canonical_record_id`, `observed_url`, `canonical_url`, `canonical_method`, `sitemap_ref`, `confidence`, `conflict_notes`, `created_at` |
| `sitemap_discovery_record` | Source discovery and freshness hints from sitemap/feed. | `sitemap_record_id`, `sitemap_url`, `format`, `parent_scope`, `url_count`, `lastmod_policy`, `discovered_url_refs`, `fetched_at`, `status` |
| `source_terms_review` | Rights/terms/legal boundary separate from robots. | `terms_review_id`, `source_ref`, `terms_url`, `license_or_terms_summary`, `allowed_uses`, `blocked_uses`, `reviewer`, `reviewed_at`, `status` |
| `web_source_refresh_policy` | Freshness and recrawl schedule. | `refresh_policy_id`, `source_ref`, `freshness_signal_refs`, `refresh_cadence`, `stale_after`, `change_detection_method`, `owner`, `status` |
| `bulk_crawl_snapshot_ref` | Common Crawl or other bulk snapshot reference. | `snapshot_ref_id`, `corpus_provider`, `crawl_id`, `index_ref`, `record_locator`, `capture_time`, `warc_or_extract_class`, `terms_review_ref`, `status` |
| `web_source_acquisition_release_gate` | Promotion gate before a fetched web source can become retrieval/canon evidence. | `gate_id`, `candidate_id`, `robots_policy_check_ref`, `web_fetch_record_ref`, `canonical_url_record_ref`, `sitemap_discovery_ref`, `source_terms_review_ref`, `extraction_quality_ref`, `privacy_or_pii_review_ref`, `refresh_policy_ref`, `bulk_snapshot_ref`, `decision`, `reviewer`, `reviewed_at` |

## Agent Studio Design Implications

- Official docs should be fetched from canonical current URLs where possible, but the ledger should retain the originally discovered URL and redirect/canonical evidence.
- Robots allowance, source rights, source freshness, and source authority are different fields. Do not collapse them into one `eligible` boolean.
- For official docs, prefer current official docs pages over bulk crawl snapshots. Use Common Crawl-like corpora for historical availability, background corpus research, or large-scale analysis only after terms and privacy review.
- Sitemap `lastmod`, HTTP `Last-Modified`, ETag, docs changelog dates, and provider release notes are freshness signals, not proof that semantic content changed.
- A blocked robots fetch should not become an extraction failure; it should become a policy decision with an auditable reason.
- Canonicalization should reduce duplicate indexing but must not erase source provenance, quote/citation URL, or access-path history.

## Release Gate

A web-derived source cannot become retrieval evidence, canon evidence, or a refreshed note input unless a `web_source_acquisition_release_gate` proves discovery provenance, robots policy for the intended user agent, fetch/redirect/cache metadata, canonical and sitemap evidence, terms/rights review, extraction quality, privacy/PII handling, refresh policy, and bulk-snapshot lineage where applicable. A successful HTTP response, sitemap listing, canonical hint, or Common Crawl locator is not enough on its own.

## Anti-Patterns To Avoid

- Treating a successful HTTP 200 as source eligibility.
- Treating robots allowance as a license to train, republish, or store source text.
- Using robots.txt to choose canonical source identity.
- Dropping redirect and canonical history, making later citations impossible to audit.
- Refreshing official docs without recording the prior hash, source version, or stale-note impact.
- Mixing Common Crawl-derived text with current official-doc notes without snapshot IDs and terms review.

## Next Agent Studio Move

Add web-source acquisition checks to the ingestion pipeline before extraction. The product should be able to answer, for every official webpage-derived note: how the URL was found, whether fetch was allowed, what terms/rights status was assigned, which canonical URL was used for dedupe, what extraction transform ran, and when the source should be refreshed.

## Canon Decision

This note is canon-ready for Agent Studio source acquisition. Web ingestion is a governed source-control plane: official/open pages should enter the datastore only through ledgered discovery, source-access, rights, canonicalization, extraction-quality, privacy, refresh, and snapshot-lineage evidence.
