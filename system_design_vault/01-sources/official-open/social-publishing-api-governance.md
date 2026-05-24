---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_source_note
rights_status: official_public_docs
sources:
  - https://developers.facebook.com/docs/instagram-platform/content-publishing/
  - https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api?view=li-lms-2026-05
  - https://developers.google.com/youtube/v3/docs/videos/insert
  - https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits
  - https://developers.tiktok.com/doc/content-posting-api-reference-direct-post
  - https://developers.tiktok.com/doc/content-posting-api-reference-upload-video
  - https://docs.x.com/x-api/posts/manage-tweets/integrate
  - https://docs.x.com/x-api/posts/create-post
---

# Social Publishing API Governance

## Direct-Read Scope

Direct-read pass over current official docs for Meta Instagram Platform content publishing, LinkedIn Posts API, YouTube Data API video upload and quota/compliance audit guidance, TikTok Content Posting API direct-post and inbox-upload flows, and X manage-posts integration/API reference.

This note captures original system-design synthesis only. It does not store API examples, credentials, request bodies, platform text, or long excerpts.

## Source Signals

Meta Instagram Platform content publishing treats posting to Instagram professional accounts as a container lifecycle. Images, videos, reels, stories, and carousel posts move through media/container creation, optional resumable upload for video, container status polling, and `media_publish`. The official docs expose publish permission requirements, Page Publishing Authorization risk, content-publishing-limit checks, public media URL requirements for fetch-based publishing, carousel child-container constraints, Reels/Stories modes, and terminal container status states.

LinkedIn treats publishing as a versioned REST surface with explicit author URNs, visibility, distribution, lifecycle state, content asset URNs, API version headers, and response IDs. Media posts require prior asset upload, and article previews should be supplied explicitly rather than relying on scraping.

YouTube treats video upload as a high-authority side effect with OAuth scopes, media upload constraints, mutable metadata parts, privacy status, publish time, subscriber-notification behavior, synthetic-media declaration, and project compliance audit constraints. Uploads from unverified post-2020 projects can be restricted to private visibility until compliance is verified.

TikTok separates direct posting from inbox upload. Direct Post requires creator info for UI rendering, explicit user consent before exporting video, post initialization, upload/export, and audit before unaudited clients can publish beyond private visibility. Inbox upload requires users to complete the final post inside TikTok and exposes pending-share caps and domain/URL ownership checks for pull-from-URL flows.

X manage-posts docs treat post creation, reply, deletion, media attachment, source labels, rate limits, and profile settings as integration concerns. The create/edit endpoint also exposes fields such as AI-generated-media labeling and paid-partnership disclosure, which matter for provenance and compliance.

## Current-Source Cross-Check

Current official YouTube upload and compliance-audit guidance still treats video insertion as a high-authority OAuth side effect with upload cost, channel authorization, mutable metadata/status parts, synthetic-media declaration, and audit-controlled visibility for API projects that need compliance review. Current TikTok Content Posting API docs still require creator-info rendering, explicit user consent before export, post initialization, publish-status tracking, per-user request limits, privacy options, and audit gates that can restrict unaudited clients to private visibility.

Current LinkedIn Posts API guidance still requires versioned REST headers, author URNs, permission/role boundaries, explicit visibility/distribution/lifecycle fields, prior asset upload for media URNs, and durable response IDs. The Instagram and X surfaces remain platform-specific side-effect APIs rather than generic posting targets: Instagram publishing depends on account eligibility, app permissions, media container readiness, publish limits, and account-bound media IDs; X post creation needs authenticated-user authority, media/disclosure fields, reply/visibility constraints, rate-limit posture, and durable post IDs.

## Canon Lessons

- Publishing is not a generation step. It is an external side effect with identity, consent, platform policy, quota, asset readiness, review, idempotency, and rollback constraints.
- Every platform has a different authority model. Instagram publishing depends on professional-account eligibility, app permissions, and Page Publishing Authorization state; LinkedIn uses author/resource URNs and version headers; YouTube uses channel OAuth scopes and compliance audit state; TikTok uses creator consent, creator-info UX, and audit gates; X uses authenticated-user posting with rate/source/media constraints.
- Media publishing is multi-stage. Container creation, upload/fetch, processing/status polling, metadata update, visibility transition, notification choice, and published URL/ID capture must be separate records.
- Platform fields are product controls. Visibility, audience targeting, subscriber notifications, synthetic-media labels, paid partnership flags, reply settings, duet/stitch/comment settings, and post lifecycle should not be hidden adapter defaults.
- Unverified, unaudited, or restricted API clients should produce draft/private/manual-completion routes, not public automation.
- Rate limits, pending-share caps, app-level quotas, user-level limits, and compliance audits belong in release gates before scheduled or autonomous posting.
- The system must preserve platform post IDs and response status. A content artifact is not published until the platform returns durable identity or a user-completed confirmation path.

## Agent Studio Design Implications

Agent Studio should treat publishing as a governed route family:

- `draft_only`: produce platform-formatted artifacts with no external side effect;
- `ready_for_review`: artifact passed source, safety, rights, and platform checks;
- `manual_publish`: user receives instructions or opens platform-native composer;
- `assisted_publish`: user approves a prepared API call or upload flow;
- `scheduled_publish`: queued external side effect with final preflight;
- `published`: platform returned ID/URL or user confirmed completion;
- `rollback_requested`: delete, hide, unlist, private, or correction route is triggered.

The platform adapter should never silently promote a draft to a public post. It needs explicit route state, reviewer approval, platform-account identity, credential scope, post metadata, asset lineage, and postcondition checks.

## Datastore Additions

- `publish_route_record`: platform, account scope, route class, autonomy mode, allowed content types, required approval policy, and rollout state.
- `platform_account_record`: platform, account/channel/organization/user URN or ID, credential boundary, owner, permitted route classes, audit/compliance status, and expiry.
- `publishing_asset_record`: source artifact, platform-specific asset ID/URN, upload state, processing state, content hash, dimensions/duration, MIME type, and validation status.
- `instagram_media_container_record`: Instagram account, container ID, media type, source media URL or upload-session ref, carousel child refs, caption ref, status code, expiry time, validation errors, and publish eligibility.
- `instagram_publish_limit_record`: Instagram account, moving-window usage, scheduled-post reservations, admission decision, and source endpoint check ref.
- `platform_post_intent`: artifact refs, target platform/account, text/caption/title/description refs, visibility/audience settings, disclosure flags, notification policy, scheduled time, and reviewer decision.
- `platform_post_execution`: intent ref, API/client version, request hash, idempotency key, platform response ID, status, error class, retry policy, and terminal postcondition.
- `platform_compliance_gate`: platform requirement, audit/review state, client verification status, allowed visibility, restricted modes, quota policy, and blocking reason.
- `platform_rate_limit_record`: platform, endpoint, user/app/account scope, limit window, remaining capacity, reset time, pending-share cap, and admission decision.
- `publish_rollback_record`: platform post ID, rollback action, allowed action set, approval requirement, execution status, user-visible result, and residual-risk note.
- `synthetic_media_disclosure_record`: artifact, platform, generated/edited media class, label field, disclosure policy, reviewer decision, and published-state evidence.
- `publishing_release_gate`: route, platform account, credential scope, approved artifacts/text/visibility/audience/disclosure/schedule, platform compliance state, rate-limit admission, media/container readiness, execution idempotency, durable platform ID or manual-completion proof, postcondition monitoring, rollback policy, approval evidence, decision, and review time.

## Release Gates

A route cannot publish externally unless:

- source/citation, rights, safety, and platform-format checks pass;
- account identity and credential scope match the target platform surface;
- required platform audit/compliance state allows the requested visibility;
- asset upload and processing are complete or the route stays in manual/inbox mode;
- Instagram media containers are ready, unexpired, within the content-publishing limit, and tied to the exact account and media assets approved by the reviewer;
- human approval covers the exact post text, media, target account, visibility, audience, disclosure fields, and scheduled time;
- rate-limit and quota admission pass;
- execution creates an auditable platform ID or a user-confirmed manual completion record;
- rollback/delete/private/unlist/correction policy exists before the side effect happens.

## Canon Decision

This note is canon-ready for Agent Studio external publishing architecture. Publishing is a governed side-effect route: no system route may post externally without exact approval, platform account identity, credential-scope proof, API/compliance/rate-limit admission, artifact and media/container readiness, required disclosure evidence, durable platform ID or manual-completion proof, postcondition monitoring, and a rollback/delete/private/correction path.

## Open Caveats

Platform API docs and access policies change frequently. Implementation must version-pin docs, app review state, scopes, API versions, endpoint behavior, quota limits, and platform-specific disclosure requirements before enabling production posting.
