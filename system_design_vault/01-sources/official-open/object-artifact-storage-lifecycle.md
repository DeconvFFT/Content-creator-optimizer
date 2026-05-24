---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
  - https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html
  - https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html
  - https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
  - https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html
  - https://docs.cloud.google.com/storage/docs/consistency
  - https://docs.cloud.google.com/storage/docs/object-versioning
  - https://docs.cloud.google.com/storage/docs/lifecycle
  - https://docs.cloud.google.com/storage/docs/access-control/signed-urls
  - https://docs.cloud.google.com/storage/docs/retention-policy
  - https://learn.microsoft.com/en-us/azure/storage/blobs/versioning-overview
  - https://learn.microsoft.com/en-us/azure/storage/blobs/lifecycle-management-overview
  - https://learn.microsoft.com/en-us/azure/storage/blobs/immutable-storage-overview
  - https://learn.microsoft.com/en-us/azure/storage/common/storage-sas-overview
---

# Object And Artifact Storage Lifecycle

## Direct-Read Scope

This note synthesizes official AWS S3, Google Cloud Storage, and Azure Blob Storage documentation for object identity, versioning, retention/immutability, lifecycle management, consistency, and temporary delegated access. It stores original architecture implications only, not provider documentation copies.

## Core Takeaway

Object storage is the binary payload plane. It is not the source of truth for Agent Studio source identity, rights, route releases, evals, approvals, or publication state. The product ledger should store stable artifact records that point to bucket/container, key/name, generation or version ID, content hash, MIME type, size, encryption posture, retention/lifecycle policy, access grants, and producing run. The blob itself should be replaceable, restored, expired, or tiered only through ledger-visible policy.

## Storage Model

- Store binary sources and generated outputs in object storage; store identity, provenance, permissions, dependency edges, and release state in Postgres.
- Treat object identity as `bucket_or_container + object_key + generation_or_version`, not just a path string.
- Record content hashes and size at write time so replay and integrity checks do not depend on provider listing behavior.
- Keep mutable aliases separate from immutable versions. A user-facing "latest draft" pointer can move; the artifact version used for a route release or evaluation cannot.
- Model delete as a lifecycle event. Versioning, soft delete, retention, legal hold, and delete markers can leave recoverable prior state even when the current object is gone.

## Lifecycle And Retention

Lifecycle policies are product behavior. Moving a source PDF, audio artifact, eval result, generated video, or sandbox output to cheaper storage can change restore latency and replay eligibility; expiring it can break audits, regressions, and user-facing diffs. Agent Studio should attach lifecycle rules to artifact classes rather than hiding them in bucket configuration.

Retention and immutability are release evidence for:

- source snapshots used for notes, eval generation, or adaptation;
- user-provided local material that backs source-aware claims;
- generated media before public publishing;
- eval inputs, outputs, and reviewer decisions;
- route releases, prompt releases, tool schema releases, and guardrail configurations;
- incident evidence and postmortem traces.

## Access And Delegation

Signed URLs and SAS tokens are temporary capabilities, not durable permission models. A route that issues one should record issuer, subject, object version, allowed operations, expiry, recipient surface, credential type, revocation posture, and whether the URL was user-visible or provider-facing. Long-lived sharing should go through normal authorization policy, not ad hoc signed links.

## Consistency And Replay

Modern object stores provide strong read-after-write behavior for ordinary object operations, but Agent Studio should still model storage behavior explicitly:

- list results are not a release gate; completed upload manifests are;
- overwrite and delete are product decisions with version and retention consequences;
- multipart or generated-artifact exports need commit records so partial objects do not become canonical;
- lifecycle transitions can make old evidence slower or impossible to replay;
- provider-specific version IDs, generations, and soft-delete semantics must be normalized before cross-cloud migration.

## Agent Studio Design Implications

- Add an `object_artifact_release_gate` before a route claims auditability, replay, eval regression support, or publication rollback from binary evidence.
- Add an `artifact_object_ref` for every source, generated artifact, media asset, sandbox export, batch manifest, eval output, and note artifact that has binary payload.
- Add `object_storage_policy` records for bucket/container class, encryption, versioning, retention, lifecycle, replication, access logging, and allowed artifact classes.
- Add `object_version_event` and `object_lifecycle_event` records so restore, expiration, tier movement, delete marker, and retention changes are visible in the run timeline.
- Add `signed_object_access_event` records for temporary share/download/upload capability issuance.
- Keep route-release evidence pinned to immutable object versions or generations, never mutable keys alone.
- Require storage restore drills for evidence classes that support audit, eval regression, or published artifact rollback.
- Treat artifact durability as an SLO surface separate from database durability.

## Canon Cross-Check

- Registry/lineage canon owns artifact identity, immutable artifact versions, producer runs, lineage edges, and alias audit; this note owns the binary object pointer, provider object version/generation, retention/lifecycle, signed access, and restore evidence behind those artifact versions.
- Data-quality canon owns validation results and failure evidence; this note owns whether the binary evidence supporting validation, evals, notes, media, and publication rollback remains retrievable and integrity-checkable.
- Privacy/retention canon owns data-processing and deletion/export policy; this note owns storage-layer retention, legal hold/immutability, lifecycle transitions, and temporary delegated access events that can alter replayability or privacy exposure.
- Production canon and HLD already treat object storage as the payload plane rather than product truth; this pass makes binary replayability a release-gated requirement.

## Concrete Contract

An Agent Studio artifact record is incomplete unless it can answer:

- Which source/run produced the object?
- Which immutable object version or generation contains the bytes?
- What hash, size, MIME type, and encryption posture were observed at write time?
- Which retention/lifecycle policy protects or expires it?
- Which route, eval, publication, note, or approval depends on it?
- Which humans, providers, or agents received temporary access to it?
- Can it be restored quickly enough for the route that claims replayability?

## Canon Decision

Agent Studio must not treat a binary source file, generated media asset, sandbox export, batch manifest, eval output, trace attachment, or note artifact as release evidence unless an object-artifact release gate links immutable object version or generation, content hash, storage policy, lifecycle/retention posture, signed-access history, restore-drill evidence, and the dependent route/eval/publication records.
