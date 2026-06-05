# External Publication Proof Runbook

This is the committed no-secret handoff for closing the remaining Agent Studio publication gate. It complements the generated operator packet under `social_media_optimiser/output/provider-proof/.../operator-unblocker-checklist.md`, which remains ignored proof output and must not be committed.

## Current Gate

- Run id: `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e`
- Accepted proof: `provider-backed-live-voice-proof`
- Active realtime path: OpenRouter `deepseek/deepseek-v4-flash` + LiveKit + Kokoro
- Remaining proof: `external-publication-proof`
- Current status: blocked until the manual publication policy acknowledgement artifact, durable destination, and rollback or postcondition artifact are supplied and validated.

## Manual Post Contract

The content system produces a review-ready distribution package. The operator reviews that package, manually posts the approved content to LinkedIn, and then supplies durable evidence of that manual action. Agents do not publish to LinkedIn for this proof path, and no LinkedIn publication token is required.

The three operator inputs are trace evidence of the operator-owned manual post:

- `LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID`: durable reference to the operator's LinkedIn policy review.
- `PUBLICATION_DURABLE_PLATFORM_ID_OR_URL`: URL or durable platform ID of the operator's manual LinkedIn post.
- `PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID`: durable proof that the operator can delete/edit the post or that postcondition monitoring is in place.

## Minimal Operator Path

Use this as the short route. The full commands remain below for copy/paste.

1. Build and review the distribution package for the UUID run.
2. Manually post the approved content to LinkedIn.
3. Copy the three keys from `docs/external-publication-operator-inputs.example.env` into the ignored UUID operator input file.
4. Replace every placeholder with durable evidence: your policy review artifact, your manual LinkedIn destination, and your rollback or postcondition artifact. No LinkedIn token is required for manual publication.
5. Run the strict readiness command. If it reports `blocked_by_operator_inputs`, stop and fix the named fields.
6. After strict readiness passes, refresh the proof packets, capture the publication preflight evidence, validate the proof record, and record it.
7. Recheck completion status, then run closure review and blocker-state update. Do not claim completion before those checks pass.

## Required Operator Inputs

Fill only local file paths or durable artifact IDs in `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env`. Use `docs/external-publication-operator-inputs.example.env` as the committed no-secret key list, then copy only the keys and local replacements into the ignored operator input file.

- `LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID`: durable non-local policy acknowledgement artifact id or URL. Generic bare values such as `policy-artifact-1` are not sufficient; LinkedIn URNs must include the platform id suffix, not only the prefix.
- `PUBLICATION_DURABLE_PLATFORM_ID_OR_URL`: durable LinkedIn platform id or URL. Local previews, screenshots, and draft-only IDs are not enough.
- `PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID`: durable non-local rollback, delete/private/correction, or postcondition monitoring artifact id or URL. Generic bare values such as `rollback-artifact-1` are not sufficient; LinkedIn URNs must include the platform id suffix, not only the prefix.
- Reserved documentation domains such as `example.com`, `example.org`, and `example.net` are placeholders, not durable evidence. Replace them with real external artifact IDs, approved document URLs, LinkedIn URNs with IDs, or whitelisted UUID-bearing artifact IDs before running strict readiness.

No secret values should ever be printed by these commands. Do not commit `.secrets/`, operator input files, generated provider proof output, screenshots, PDFs, images, media, browser traces, local databases, or token-bearing logs.

## Strict Readiness Gate

Run the strict operator-input check first. It must return `ready_for_credential_snapshot_refresh` before any publication proof capture can be accepted.

Command anchor: `uv run all-about-llms-admin provider-proof-operator-input-readiness --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e --input-path social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env --fail-on-blocked > social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-input-readiness.json`

```bash
uv run all-about-llms-admin provider-proof-operator-input-readiness \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e \
  --input-path social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env \
  --fail-on-blocked \
  > social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-input-readiness.json
```

If this reports `blocked_by_operator_inputs`, stop and update the operator input file. Do not run blocker-state updates, closure review, or goal-completion claims.

## Refresh Proof Packets

After strict readiness clears, regenerate the no-secret proof packets into ignored output.

```bash
uv run all-about-llms-admin blocker-credential-snapshot \
  --operator-input-path social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env \
  > social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/credential-snapshot.json

uv run all-about-llms-admin provider-proof-plan \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e \
  --operator-input-path social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env \
  > social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json

uv run all-about-llms-admin provider-proof-current-blocker-matrix \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e \
  --output-dir social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e \
  > social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-blocker-matrix.json

uv run all-about-llms-admin provider-proof-current-status \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e \
  --output-dir social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e \
  > social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-proof-status.md

uv run all-about-llms-admin provider-proof-operator-unblocker-checklist \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e \
  --output-dir social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e \
  > social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-unblocker-checklist.md
```

## Capture And Validate Publication Evidence

Capture product and publish-readiness preflight evidence only after action-time approval for the manual LinkedIn publication path.

Command anchor: `uv run all-about-llms-admin validate-provider-proof-preflight-artifacts --proof external-publication-proof --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e --preflight-dir social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e`

```bash
uv run all-about-llms-admin run-autonomous-pass \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e \
  --acknowledge-publish-channel-policy \
  --manual-publication-mode

uv run all-about-llms-admin build-distribution-package \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e \
  > social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/distribution-package.json

curl -sS \
  -o social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/product-run.preflight.json \
  http://127.0.0.1:8000/api/runs/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e

curl -sS -X POST \
  -o social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/publish-readiness.preflight.json \
  http://127.0.0.1:8000/api/runs/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/publish-readiness \
  -H 'Content-Type: application/json' \
  --data '{"open_feedback_gate":false,"mark_run_completed_if_ready":false,"check_publish_channel_readiness":true,"acknowledge_publish_channel_policy":true,"manual_publication_mode":true}'

uv run all-about-llms-admin validate-provider-proof-preflight-artifacts \
  --proof external-publication-proof \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e \
  --preflight-dir social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e \
  > social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/external-publication-proof.preflight-validation.json
```

The accepted `external-publication-proof` record must include durable destination-channel linkage, policy acknowledgement, rollback or postcondition evidence, zero failed post-capture validation checks, and a passed secret-redaction check.

## Record The Proof

Create the proof-record draft, fill it with the durable artifact IDs, validate it, and record it into the configured project and system-design audit targets.

Command anchors: `uv run all-about-llms-admin provider-proof-record-template --proof external-publication-proof --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e`; `uv run all-about-llms-admin validate-provider-proof-record --proof external-publication-proof --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e --record-path <provider-proof-record.json>`; `uv run all-about-llms-admin record-provider-proof-record --proof external-publication-proof --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e --record-path <provider-proof-record.json>`

```bash
uv run all-about-llms-admin provider-proof-record-template \
  --proof external-publication-proof \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e

uv run all-about-llms-admin validate-provider-proof-record \
  --proof external-publication-proof \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e \
  --record-path <provider-proof-record.json> \
  --preflight-validation-path social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/external-publication-proof.preflight-validation.json \
  --workspace-validation-path social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/workspace-validation.json

uv run all-about-llms-admin record-provider-proof-record \
  --proof external-publication-proof \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e \
  --record-path <provider-proof-record.json> \
  --preflight-validation-path social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/external-publication-proof.preflight-validation.json \
  --workspace-validation-path social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/workspace-validation.json
```

## Completion And Closure

Only after the external publication record validates and records as accepted:

```bash
uv run all-about-llms-admin provider-proof-completion-status \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e

uv run all-about-llms-admin provider-proof-closure-review-template \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e

uv run all-about-llms-admin validate-provider-proof-closure-review \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e \
  --record-path <provider-proof-closure-review.json>

uv run all-about-llms-admin record-provider-proof-closure-review \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e \
  --record-path <provider-proof-closure-review.json>

uv run all-about-llms-admin provider-proof-closure-review-status \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e

uv run all-about-llms-admin record-provider-proof-blocker-state-update \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e
```

Do not call the Agent Studio goal complete until completion status, closure review, and blocker-state update all prove the external publication proof is accepted without secret leakage.
