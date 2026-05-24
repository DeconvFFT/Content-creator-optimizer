---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://www.nist.gov/privacy-framework
  - https://openai.com/security-and-privacy/
  - https://openai.com/enterprise-privacy/
  - https://help.openai.com/en/articles/7039943-data-controls-faq
  - https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data
  - https://privacy.claude.com/en/articles/8956058-i-have-a-zero-data-retention-agreement-with-anthropic-what-products-does-it-apply-to
  - https://docs.cloud.google.com/sensitive-data-protection/docs/sensitive-data-protection-overview
  - https://cloud.google.com/sensitive-data-protection/docs/deidentify-sensitive-data
---

# Privacy, Retention, And Data Boundaries

## Source Boundary

This note synthesizes official/current privacy and sensitive-data sources: NIST Privacy Framework, OpenAI security/privacy and enterprise privacy pages, OpenAI data-usage FAQ, Anthropic commercial retention and zero-data-retention privacy center pages, and Google Cloud Sensitive Data Protection overview/de-identification docs. It stores compact original synthesis only, with no copied policy text beyond short source references. Current-source check: NIST has Privacy Framework 1.1 draft material in progress; Anthropic commercial retention/ZDR pages are dated March 16, 2026; Google Sensitive Data Protection pages show May 2026 updates.

## Core Design Lessons

Privacy is a data-processing lifecycle, not a static "do not log" flag. NIST Privacy Framework frames privacy risk around identifying, governing, controlling, communicating, and protecting data processing. For Agent Studio, every source, trace, memory, provider call, artifact, feedback item, and publish action is a processing activity with purpose, sensitivity, retention, access, and downstream-use constraints.

Provider data boundaries differ by product and configuration. OpenAI distinguishes consumer and business/API data controls, with business data not used for model training by default and enterprise controls for retention, internal-source access, authentication, and encryption. Anthropic distinguishes default commercial retention, product features that intentionally persist data, and separate zero-data-retention arrangements for eligible API surfaces. Agent Studio cannot treat "uses provider X" as a complete privacy answer; each route needs product, feature, retention, training-use, logging, file/cache, web-search, and third-party-sharing fields.

Sensitive-data handling should happen before data reaches durable traces or external providers. Google Sensitive Data Protection separates discovery, inspection, classification, risk analysis, and de-identification. It supports built-in and custom detectors and transformations such as redaction, masking, tokenization/surrogates, encryption-based transformations, and date shifting. Agent Studio should apply the same pattern locally: classify first, transform or block second, then store only references, hashes, redacted summaries, or approved artifacts.

De-identification is not deletion. Redaction, masking, tokenization, and format-preserving transforms reduce exposure, but each has scope, reversibility, key-management, and utility tradeoffs. A route should record whether sensitive data was removed, transformed, encrypted, tokenized, retained under access controls, or sent externally. The retention class should follow the most sensitive surviving representation, not the optimistic label of the route.

Privacy controls need user and organization affordances. Provider pages emphasize access controls, deletion, retention, training opt-in/default posture, audit/logging, and account or organization boundaries. Agent Studio needs matching local records: who can access a source or memory, how long traces/artifacts persist, which provider received what data class, whether the data can be deleted, what remains as hashes/derived notes, and whether deletion should also trigger index, cache, memory, eval, or artifact cleanup.

## Canon Cross-Check

Object/artifact storage owns binary retention, versioning, lifecycle, restore, and signed-access evidence; privacy owns processing purpose, data class, provider training/retention posture, deletion/export affordances, and human access to sensitive content.

Data-quality contracts own validation and failure handling; privacy owns whether sensitive content can be stored, indexed, reused for evals, sent to providers, or published after transformation.

Agent, browser, computer-use, and tool-runtime notes own execution surfaces; privacy owns which observations, screenshots, files, tool outputs, and provider payloads may persist or leave the local boundary.

Provider runtime notes own API operation; this note owns the product/API-level data-use, retention, ZDR, training, file/cache/batch, third-party sharing, and support-access posture that must be recorded per route.

## Agent Studio Implications

Agent Studio should treat these as separate privacy surfaces:

- local source files and extracted text;
- compact Obsidian notes and generated synthesis;
- chunks, embeddings, indexes, feature stores, and graph edges;
- provider requests, files, prompt caches, background jobs, and conversation state;
- traces, screenshots, browser/computer-use observations, and tool outputs;
- user feedback, preferences, memories, and personalization records;
- generated media, drafts, captions, and public publishing artifacts.

Each route should declare:

- data classes it may read;
- data classes it may send to each provider;
- whether provider training-use is allowed, blocked by default, or explicitly opted in;
- provider retention and local retention;
- redaction/de-identification policy before provider calls and before trace storage;
- deletion/export affordance;
- audit evidence for human access and external sharing;
- third-party web-search or connector caveats.

## Datastore Requirements

Agent Studio needs privacy-shaped records for:

- privacy processing activity: route, purpose, data subject class, data classes, processing stages, provider/tool surfaces, legal or policy basis, owner, and status;
- sensitive data profile: source/artifact/chunk/trace/memory ref, detected info types, likelihood or confidence, sensitivity label, detector version, custom detector refs, and review state;
- de-identification policy: transformation type, reversible or irreversible posture, key/surrogate policy, field scope, utility caveat, and approval status;
- de-identification event: input ref, output ref, policy ref, findings summary, residual sensitivity, skipped fields, and created-at;
- retention policy record: subject family, local retention, provider retention, deletion trigger, exception reasons, legal/security hold, and expiry;
- provider data boundary: provider, product/API surface, route, training-use posture, ZDR or retention agreement status, files/cache/batch caveats, third-party sharing caveats, and review state;
- privacy subject request: export/delete/correct request, affected source/memory/artifact/index/cache/provider refs, fulfillment state, retained exception refs, and audit evidence;
- human access audit: reviewer/operator/provider-support access to sensitive content, purpose, approval, scope, time, and review outcome.
- privacy release gate: route/release, linked processing activity, sensitive-data profile, de-identification policy/events, retention policy, provider data boundary, deletion/export tests, human-access audit, third-party sharing review, decision, reviewer, and created-at.

## Operating Rule

No route that touches private local material, user memory, provider files, web search, screenshots, generated media, or publishing should be production-ready until its privacy processing activity, sensitive-data profile, provider data boundary, retention policy, redaction/de-identification policy, deletion/export affordance, third-party sharing caveat, and human-access audit are explicit.
