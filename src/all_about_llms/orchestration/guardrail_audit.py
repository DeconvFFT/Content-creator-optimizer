from uuid import UUID

from all_about_llms.contracts import (
    ArtifactRecord,
    ArtifactType,
    ClaimRecord,
    ClaimSupportStatus,
    GuardrailAuditRecord,
    GuardrailAuditRequest,
    GuardrailAuditResult,
    GuardrailAuditStatus,
    RunEvent,
    RunStatus,
)
from all_about_llms.orchestration.artifact_provenance import (
    artifact_provenance_issues,
)


AUDITABLE_ARTIFACT_TYPES = {
    ArtifactType.POST,
    ArtifactType.REEL_SCRIPT,
    ArtifactType.SUBSTACK_ARTICLE,
    ArtifactType.SOCIAL_PACKAGE,
    ArtifactType.VISUAL_BRIEF,
    ArtifactType.IMAGE,
    ArtifactType.AUDIO,
    ArtifactType.VIDEO,
}


class GuardrailAuditError(RuntimeError):
    """Base error for guardrail audit orchestration."""


class GuardrailAuditRunNotFoundError(GuardrailAuditError):
    """Raised when a guardrail audit is requested for a missing run."""


class NoArtifactsToAuditError(GuardrailAuditError):
    """Raised when no artifacts can be audited."""


class GuardrailAuditWorkflow:
    """Persist deterministic source and claim audits for generated artifacts."""

    def __init__(self, store):
        self._store = store

    async def run(
        self, run_id: UUID, request: GuardrailAuditRequest
    ) -> GuardrailAuditResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise GuardrailAuditRunNotFoundError(f"Run not found: {run_id}")

        artifacts = await self._select_artifacts(run_id, request)
        claims = await self._store.list_claims(run_id)
        source_ids = {source.source_id for source in await self._store.list_sources(run_id)}

        audits = []
        for artifact in artifacts:
            audit = _audit_artifact(
                run_id=run_id,
                artifact=artifact,
                claims=claims,
                known_source_ids=source_ids,
            )
            await self._store.record_guardrail_audit(audit)
            await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="guardrail_audit_recorded",
                    actor="guardrails-agent",
                    payload=audit.model_dump(mode="json"),
                )
            )
            audits.append(audit)

        overall_status = _overall_status(audits)
        feedback_gate_opened = False
        if request.open_feedback_gate and overall_status != GuardrailAuditStatus.APPROVED:
            await self._store.update_run_status(run_id, RunStatus.WAITING_FOR_HUMAN)
            await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="human_feedback_gate_opened",
                    actor="guardrails-agent",
                    payload={
                        "reason": "guardrail_audit_requires_review",
                        "status": overall_status.value,
                        "audit_ids": [str(audit.audit_id) for audit in audits],
                    },
                )
            )
            feedback_gate_opened = True

        return GuardrailAuditResult(
            run_id=run_id,
            audits=audits,
            status=overall_status,
            feedback_gate_opened=feedback_gate_opened,
            summary=(
                f"Audited {len(audits)} artifacts: "
                f"{sum(1 for audit in audits if audit.status == GuardrailAuditStatus.APPROVED)} approved, "
                f"{sum(1 for audit in audits if audit.status == GuardrailAuditStatus.NEEDS_REVISION)} needs revision, "
                f"{sum(1 for audit in audits if audit.status == GuardrailAuditStatus.BLOCKED)} blocked."
            ),
        )

    async def _select_artifacts(
        self, run_id: UUID, request: GuardrailAuditRequest
    ) -> list[ArtifactRecord]:
        artifacts = [
            artifact
            for artifact in await self._store.list_artifacts(run_id)
            if artifact.artifact_type in AUDITABLE_ARTIFACT_TYPES
        ]
        if request.target_artifact_ids:
            target_ids = set(request.target_artifact_ids)
            artifacts = [
                artifact for artifact in artifacts if artifact.artifact_id in target_ids
            ]
        if not artifacts:
            raise NoArtifactsToAuditError("No artifacts are available for audit.")
        return artifacts


def _audit_artifact(
    *,
    run_id: UUID,
    artifact: ArtifactRecord,
    claims: list[ClaimRecord],
    known_source_ids: set[UUID],
) -> GuardrailAuditRecord:
    artifact_claim_ids = _extract_claim_ids(artifact)
    claim_by_id = {claim.claim_id: claim for claim in claims}
    artifact_claims = [
        claim_by_id[claim_id]
        for claim_id in artifact_claim_ids
        if claim_id in claim_by_id
    ]
    supported = [
        claim
        for claim in artifact_claims
        if claim.support_status == ClaimSupportStatus.SUPPORTED
    ]
    needs_review = [
        claim
        for claim in artifact_claims
        if claim.support_status == ClaimSupportStatus.NEEDS_REVIEW
    ]
    unsupported = [
        claim
        for claim in artifact_claims
        if claim.support_status == ClaimSupportStatus.UNSUPPORTED
    ]
    missing_source_claims = [
        claim
        for claim in artifact_claims
        if not claim.source_ids or not set(claim.source_ids) <= known_source_ids
    ]

    blocking_issues: list[str] = []
    provenance_issues = artifact_provenance_issues(artifact)
    if not artifact.source_ids:
        blocking_issues.append("missing_artifact_source_dependencies")
    elif not set(artifact.source_ids) <= known_source_ids:
        blocking_issues.append("artifact_references_unknown_sources")
    if not artifact_claim_ids:
        blocking_issues.append("missing_claim_dependencies")
    if unsupported:
        blocking_issues.append("unsupported_claims")
    if missing_source_claims:
        blocking_issues.append("claims_missing_source_records")
    blocking_issues.extend(provenance_issues)

    claim_count = len(artifact_claims)
    source_coverage = len(supported) / claim_count if claim_count else 0.0
    if unsupported or not artifact.source_ids:
        status = GuardrailAuditStatus.BLOCKED
    elif blocking_issues or needs_review:
        status = GuardrailAuditStatus.NEEDS_REVISION
    else:
        status = GuardrailAuditStatus.APPROVED

    return GuardrailAuditRecord(
        run_id=run_id,
        artifact_id=artifact.artifact_id,
        status=status,
        source_coverage=round(source_coverage, 4),
        claim_count=claim_count,
        supported_claim_ids=[claim.claim_id for claim in supported],
        needs_review_claim_ids=[claim.claim_id for claim in needs_review],
        unsupported_claim_ids=[claim.claim_id for claim in unsupported],
        missing_source_claim_ids=[claim.claim_id for claim in missing_source_claims],
        blocking_issues=blocking_issues,
        notes=_audit_notes(status, blocking_issues, needs_review),
    )


def _extract_claim_ids(artifact: ArtifactRecord) -> list[UUID]:
    raw_claim_ids = [
        *artifact.provenance.get("claim_ids", []),
        *artifact.content.get("claim_ids", []),
    ]
    claim_ids = []
    for raw_claim_id in raw_claim_ids:
        try:
            claim_id = UUID(str(raw_claim_id))
        except ValueError:
            continue
        if claim_id not in claim_ids:
            claim_ids.append(claim_id)
    return claim_ids


def _overall_status(audits: list[GuardrailAuditRecord]) -> GuardrailAuditStatus:
    if any(audit.status == GuardrailAuditStatus.BLOCKED for audit in audits):
        return GuardrailAuditStatus.BLOCKED
    if any(audit.status == GuardrailAuditStatus.NEEDS_REVISION for audit in audits):
        return GuardrailAuditStatus.NEEDS_REVISION
    return GuardrailAuditStatus.APPROVED


def _audit_notes(
    status: GuardrailAuditStatus,
    blocking_issues: list[str],
    needs_review: list[ClaimRecord],
) -> str:
    if status == GuardrailAuditStatus.APPROVED:
        return "Artifact has source dependencies and all linked claims are supported."
    if status == GuardrailAuditStatus.BLOCKED:
        return "Artifact is blocked until source or unsupported-claim issues are resolved."
    provenance_issues = [
        issue for issue in blocking_issues if issue.startswith("missing_artifact_")
    ]
    if provenance_issues:
        return "Artifact needs revision because provenance or review metadata is incomplete."
    if needs_review:
        return "Artifact needs revision because at least one linked claim still needs review."
    return f"Artifact needs revision: {', '.join(blocking_issues)}."
