import os
from collections.abc import Mapping
from pathlib import Path
from uuid import UUID

from all_about_llms.contracts import (
    ArtifactRecord,
    ArtifactType,
    ClaimRecord,
    ClaimSupportStatus,
    FeedbackItem,
    FeedbackStatus,
    GuardrailAuditRecord,
    GuardrailAuditStatus,
    PublishReadinessRequest,
    PublishReadinessResult,
    PublishReadinessStatus,
    PublishChannelCheck,
    RunEvent,
    RunStatus,
    SourceFreshnessStatus,
    SourceQualityStatus,
    SourceRecord,
)
from all_about_llms.orchestration.source_quality import evaluate_source_quality
from all_about_llms.orchestration.retrieval_evidence import (
    accepted_retrieval_evidence_by_source,
    latest_retrieval_quality_ledger,
    retrieval_quality_ledger_status,
)
from all_about_llms.orchestration.artifact_provenance import (
    artifact_expert_model_issues,
    artifact_provenance_issues,
)
from all_about_llms.realtime_safety import safe_realtime_metadata


class PublishReadinessError(RuntimeError):
    """Base error for publish-readiness assessment."""


class PublishReadinessRunNotFoundError(PublishReadinessError):
    """Raised when readiness is requested for a missing run."""


PUBLISHABLE_ARTIFACT_TYPES = {
    ArtifactType.POST,
    ArtifactType.REEL_SCRIPT,
    ArtifactType.SUBSTACK_ARTICLE,
    ArtifactType.SOCIAL_PACKAGE,
    ArtifactType.VISUAL_BRIEF,
    ArtifactType.IMAGE,
    ArtifactType.AUDIO,
    ArtifactType.VIDEO,
}

PUBLISH_CHANNEL_CREDENTIAL_ENVS = {
    "instagram_post": ("INSTAGRAM_ACCESS_TOKEN",),
    "instagram_reel": ("INSTAGRAM_ACCESS_TOKEN",),
    "linkedin": ("LINKEDIN_ACCESS_TOKEN",),
    "x_thread": ("X_ACCESS_TOKEN", "X_API_KEY"),
    "substack": ("SUBSTACK_API_TOKEN",),
}

PUBLISH_CHANNEL_CREDENTIAL_FILE_ENVS = {
    "INSTAGRAM_ACCESS_TOKEN": "INSTAGRAM_ACCESS_TOKEN_FILE",
    "LINKEDIN_ACCESS_TOKEN": "LINKEDIN_ACCESS_TOKEN_FILE",
    "X_ACCESS_TOKEN": "X_ACCESS_TOKEN_FILE",
    "X_API_KEY": "X_API_KEY_FILE",
    "SUBSTACK_API_TOKEN": "SUBSTACK_API_TOKEN_FILE",
}

PUBLISH_CHANNEL_ALIASES = {
    "instagram": "instagram_post",
    "insta": "instagram_post",
    "ig": "instagram_post",
    "reel": "instagram_reel",
    "reels": "instagram_reel",
    "twitter": "x_thread",
    "x": "x_thread",
    "substack_article": "substack",
}


class PublishReadinessWorkflow:
    """Create a run-level publish/no-publish decision from durable state."""

    def __init__(
        self,
        store,
        credential_env_values: Mapping[str, str | None] | None = None,
    ):
        self._store = store
        self._credential_env_values = credential_env_values

    async def run(
        self, run_id: UUID, request: PublishReadinessRequest
    ) -> PublishReadinessResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise PublishReadinessRunNotFoundError(f"Run not found: {run_id}")

        sources = await self._store.list_sources(run_id)
        claims = await self._store.list_claims(run_id)
        all_artifacts = await self._store.list_artifacts(run_id)
        artifacts = self._select_artifacts(all_artifacts, request)
        audits = await self._store.list_guardrail_audits(run_id)
        feedback_items = await self._store.list_feedback(run_id)
        publish_channel_checks = _publish_channel_checks(
            artifacts=artifacts,
            request=request,
            credential_env_values=self._credential_env_values,
        )

        status, issues, next_actions = _assess_readiness(
            artifacts=artifacts,
            all_artifacts=all_artifacts,
            claims=claims,
            sources=sources,
            audits=audits,
            feedback_items=feedback_items,
            publish_channel_checks=publish_channel_checks,
        )
        feedback_gate_opened = False
        feedback_id = None
        if status != PublishReadinessStatus.READY and request.open_feedback_gate:
            feedback = FeedbackItem(
                run_id=run_id,
                author="guardrails-agent",
                target_agent_id="forward-deployed-engineer",
                feedback_text=(
                    "Publishing readiness is not approved. Resolve the listed "
                    "blocking issues before using the content."
                ),
                metadata={
                    "gate": "publish_readiness",
                    "status": status.value,
                    "blocking_issues": issues,
                    "recommended_next_actions": next_actions,
                },
            )
            await self._store.record_feedback(feedback)
            feedback_id = feedback.feedback_id
            await self._store.update_run_status(run_id, RunStatus.WAITING_FOR_HUMAN)
            await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="feedback_recorded",
                    actor="guardrails-agent",
                    payload=safe_realtime_metadata(feedback.model_dump(mode="json")),
                )
            )
            await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="human_feedback_gate_opened",
                    actor="guardrails-agent",
                    payload=safe_realtime_metadata(
                        {
                            "reason": "publish_readiness_requires_resolution",
                            "feedback_id": str(feedback.feedback_id),
                            "status": status.value,
                            "blocking_issues": issues,
                        }
                    ),
                )
            )
            feedback_gate_opened = True
        elif status == PublishReadinessStatus.READY and request.mark_run_completed_if_ready:
            await self._store.update_run_status(run_id, RunStatus.COMPLETED)

        open_feedback_count = _open_feedback_count(feedback_items) + (
            1 if feedback_gate_opened else 0
        )
        result = PublishReadinessResult(
            run_id=run_id,
            status=status,
            ready=status == PublishReadinessStatus.READY,
            artifact_ids=[artifact.artifact_id for artifact in artifacts],
            source_count=len(sources),
            claim_count=len(claims),
            audit_count=len(
                [
                    audit
                    for audit in audits
                    if audit.artifact_id in {artifact.artifact_id for artifact in artifacts}
                ]
            ),
            open_feedback_count=open_feedback_count,
            blocking_issues=issues,
            recommended_next_actions=next_actions,
            publish_channel_checks=publish_channel_checks,
            feedback_gate_opened=feedback_gate_opened,
            feedback_id=feedback_id,
            summary=_summary(status, artifacts, issues),
        )
        await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="publish_readiness_checked",
                actor="guardrails-agent",
                payload=safe_realtime_metadata(result.model_dump(mode="json")),
            )
        )
        return result

    def _select_artifacts(
        self, artifacts: list[ArtifactRecord], request: PublishReadinessRequest
    ) -> list[ArtifactRecord]:
        if request.target_artifact_ids:
            target_ids = set(request.target_artifact_ids)
            return [
                artifact for artifact in artifacts if artifact.artifact_id in target_ids
            ]
        return _leaf_publishable_artifacts(artifacts)


def _assess_readiness(
    *,
    artifacts: list[ArtifactRecord],
    all_artifacts: list[ArtifactRecord],
    claims: list[ClaimRecord],
    sources: list[SourceRecord],
    audits: list[GuardrailAuditRecord],
    feedback_items: list[FeedbackItem],
    publish_channel_checks: list[PublishChannelCheck],
) -> tuple[PublishReadinessStatus, list[str], list[str]]:
    hard_issues: list[str] = []
    review_issues: list[str] = []
    source_ids = {source.source_id for source in sources}
    source_entries = [evaluate_source_quality(source) for source in sources]
    weak_source_ids = {
        entry.source_id
        for entry in source_entries
        if entry.quality_status == SourceQualityStatus.WEAK
    }
    stale_source_ids = {
        entry.source_id
        for entry in source_entries
        if entry.freshness_status == SourceFreshnessStatus.STALE
    }
    unknown_freshness_source_ids = {
        entry.source_id
        for entry in source_entries
        if entry.freshness_status == SourceFreshnessStatus.UNKNOWN
    }
    claim_by_id = {claim.claim_id: claim for claim in claims}
    retrieval_ledger = latest_retrieval_quality_ledger(all_artifacts)
    retrieval_ledger_status = retrieval_quality_ledger_status(retrieval_ledger)
    accepted_retrieval_evidence = accepted_retrieval_evidence_by_source(
        all_artifacts
    )
    accepted_retrieval_source_ids = set(accepted_retrieval_evidence)
    referenced_source_ids = _referenced_source_ids(
        artifacts=artifacts,
        claim_by_id=claim_by_id,
    )
    referenced_weak_source_ids = weak_source_ids & referenced_source_ids
    referenced_stale_source_ids = stale_source_ids & referenced_source_ids
    referenced_unknown_freshness_source_ids = (
        unknown_freshness_source_ids & referenced_source_ids
    )

    if not artifacts:
        hard_issues.append("no_publishable_artifacts")
    if not source_ids:
        hard_issues.append("no_source_records")
    if not claims:
        review_issues.append("no_claim_records")
    if referenced_weak_source_ids:
        hard_issues.append("weak_source_records")
    if referenced_stale_source_ids:
        review_issues.append("stale_source_records")
    if referenced_unknown_freshness_source_ids:
        review_issues.append("source_freshness_unknown")
    if (
        retrieval_ledger is not None
        and retrieval_ledger_status != "ready"
    ):
        hard_issues.append("retrieval_quality_not_ready")
    elif retrieval_ledger is not None and not accepted_retrieval_source_ids:
        hard_issues.append("no_accepted_retrieval_evidence")

    unsupported_claims = [
        claim
        for claim in claims
        if claim.support_status == ClaimSupportStatus.UNSUPPORTED
    ]
    needs_review_claims = [
        claim
        for claim in claims
        if claim.support_status == ClaimSupportStatus.NEEDS_REVIEW
    ]
    if unsupported_claims:
        hard_issues.append("unsupported_claims")
    if needs_review_claims:
        review_issues.append("claims_need_review")
    if accepted_retrieval_source_ids:
        claims_missing_accepted_retrieval_evidence = [
            claim
            for claim in claims
            if claim.source_ids
            and not any(
                source_id in accepted_retrieval_source_ids
                for source_id in claim.source_ids
            )
        ]
        if claims_missing_accepted_retrieval_evidence:
            hard_issues.append("claim_missing_accepted_retrieval_evidence")

    latest_audit_by_artifact = _latest_audit_by_artifact(audits)
    for artifact in artifacts:
        artifact_claim_ids = _extract_claim_ids(artifact)
        if not artifact.source_ids:
            hard_issues.append("missing_artifact_source_dependencies")
        elif not set(artifact.source_ids) <= source_ids:
            hard_issues.append("artifact_references_unknown_sources")
        elif set(artifact.source_ids) & weak_source_ids:
            hard_issues.append("artifact_references_weak_sources")
        elif set(artifact.source_ids) & (
            stale_source_ids | unknown_freshness_source_ids
        ):
            review_issues.append("artifact_sources_need_freshness_review")
        if accepted_retrieval_source_ids and artifact.source_ids:
            if not any(
                source_id in accepted_retrieval_source_ids
                for source_id in artifact.source_ids
            ):
                hard_issues.append("artifact_missing_accepted_retrieval_evidence")
        if not artifact_claim_ids:
            hard_issues.append("missing_claim_dependencies")
        elif any(claim_id not in claim_by_id for claim_id in artifact_claim_ids):
            hard_issues.append("artifact_references_unknown_claims")
        hard_issues.extend(artifact_expert_model_issues(artifact))
        review_issues.extend(artifact_provenance_issues(artifact))

        audit = latest_audit_by_artifact.get(artifact.artifact_id)
        if audit is None:
            review_issues.append("missing_guardrail_audit")
        elif audit.status == GuardrailAuditStatus.BLOCKED:
            hard_issues.append("blocked_guardrail_audit")
        elif audit.status == GuardrailAuditStatus.NEEDS_REVISION:
            review_issues.append("guardrail_audit_needs_revision")

    if _open_feedback_count(feedback_items):
        review_issues.append("unresolved_feedback_items")
    if any(
        "missing_publish_channel_credentials" in check.blocking_issues
        for check in publish_channel_checks
    ):
        hard_issues.append("missing_publish_channel_credentials")
    if any(
        "unsupported_publish_channel" in check.blocking_issues
        for check in publish_channel_checks
    ):
        hard_issues.append("unsupported_publish_channel")
    if any(
        "publish_channel_policy_review_required" in check.blocking_issues
        for check in publish_channel_checks
    ):
        review_issues.append("publish_channel_policy_review_required")

    issues = _dedupe([*hard_issues, *review_issues])
    next_actions = _next_actions(issues)
    if hard_issues:
        return PublishReadinessStatus.BLOCKED, issues, next_actions
    if review_issues:
        return PublishReadinessStatus.NEEDS_REVIEW, issues, next_actions
    return PublishReadinessStatus.READY, [], [
        "Publishing readiness is approved; final human judgment still applies."
    ]


def _leaf_publishable_artifacts(
    artifacts: list[ArtifactRecord],
) -> list[ArtifactRecord]:
    parent_ids = set()
    for artifact in artifacts:
        parent_id = artifact.provenance.get("parent_artifact_id")
        if isinstance(parent_id, str):
            try:
                parent_ids.add(UUID(parent_id))
            except ValueError:
                continue
    return [
        artifact
        for artifact in artifacts
        if artifact.artifact_type in PUBLISHABLE_ARTIFACT_TYPES
        and artifact.artifact_id not in parent_ids
    ]


def _publish_channel_checks(
    *,
    artifacts: list[ArtifactRecord],
    request: PublishReadinessRequest,
    credential_env_values: Mapping[str, str | None] | None = None,
) -> list[PublishChannelCheck]:
    if not request.check_publish_channel_readiness:
        return []
    checks = []
    for platform in _publish_platforms(artifacts):
        credential_envs = list(PUBLISH_CHANNEL_CREDENTIAL_ENVS.get(platform, ()))
        blocking_issues = []
        recommended_next_actions = []
        if not credential_envs:
            credential_status = "unsupported"
            blocking_issues.append("unsupported_publish_channel")
            recommended_next_actions.append(
                "Add an explicit publish-channel credential mapping before "
                f"publishing to {platform}."
            )
        elif not any(
            _publish_channel_credential_is_configured(
                env_name,
                credential_env_values=credential_env_values,
            )
            for env_name in credential_envs
        ):
            credential_status = "missing"
            blocking_issues.append("missing_publish_channel_credentials")
            recommended_next_actions.append(
                "Configure one of "
                f"{_credential_setup_options(credential_envs)} before "
                f"publishing to {platform}."
            )
        else:
            credential_status = "configured"
        if not request.acknowledge_publish_channel_policy:
            blocking_issues.append("publish_channel_policy_review_required")
            recommended_next_actions.append(
                f"Confirm current {platform} platform policy and account "
                "permissions before live publication."
            )
        checks.append(
            PublishChannelCheck(
                platform=platform,
                credential_envs=credential_envs,
                credential_status=credential_status,
                policy_status=(
                    "acknowledged"
                    if request.acknowledge_publish_channel_policy
                    else "needs_review"
                ),
                blocking_issues=blocking_issues,
                recommended_next_actions=recommended_next_actions,
            )
        )
    return checks


def _publish_platforms(artifacts: list[ArtifactRecord]) -> list[str]:
    platforms = []
    for artifact in artifacts:
        for platform in _artifact_platforms(artifact):
            if platform not in platforms:
                platforms.append(platform)
        if artifact.artifact_type == ArtifactType.SUBSTACK_ARTICLE:
            if "substack" not in platforms:
                platforms.append("substack")
    return platforms


def _artifact_platforms(artifact: ArtifactRecord) -> list[str]:
    platforms = []
    raw_platforms = artifact.content.get("platforms")
    if not raw_platforms:
        raw_platforms = artifact.provenance.get("platforms")
    if not isinstance(raw_platforms, list):
        return platforms
    for raw_platform in raw_platforms:
        if isinstance(raw_platform, dict):
            value = raw_platform.get("platform")
        else:
            value = raw_platform
        if not isinstance(value, str):
            continue
        platform = _normalize_publish_platform(value)
        if platform and platform not in platforms:
            platforms.append(platform)
    return platforms


def _normalize_publish_platform(value: str) -> str:
    platform = value.strip().lower()
    return PUBLISH_CHANNEL_ALIASES.get(platform, platform)


def _env_is_configured(
    env_name: str,
    *,
    credential_env_values: Mapping[str, str | None] | None = None,
) -> bool:
    value = (
        os.environ.get(env_name)
        if credential_env_values is None
        else credential_env_values.get(env_name)
    )
    return isinstance(value, str) and bool(value.strip())


def _publish_channel_credential_is_configured(
    env_name: str,
    *,
    credential_env_values: Mapping[str, str | None] | None = None,
) -> bool:
    if _env_is_configured(env_name, credential_env_values=credential_env_values):
        return True
    file_env_name = PUBLISH_CHANNEL_CREDENTIAL_FILE_ENVS.get(env_name)
    return bool(
        file_env_name
        and _secret_file_env_is_configured(
            file_env_name,
            credential_env_values=credential_env_values,
        )
    )


def _secret_file_env_is_configured(
    file_env_name: str,
    *,
    credential_env_values: Mapping[str, str | None] | None = None,
) -> bool:
    value = (
        os.environ.get(file_env_name)
        if credential_env_values is None
        else credential_env_values.get(file_env_name)
    )
    raw_path = value.strip() if isinstance(value, str) else ""
    if not raw_path:
        return False
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        if not path.is_file():
            return False
        raw_secret = path.read_bytes()
        if not raw_secret.strip():
            return False
        raw_secret.decode("utf-8")
    except (OSError, UnicodeError):
        return False
    return True


def _credential_setup_options(credential_envs: list[str]) -> str:
    options: list[str] = []
    for env_name in credential_envs:
        file_env_name = PUBLISH_CHANNEL_CREDENTIAL_FILE_ENVS.get(env_name)
        if file_env_name:
            options.append(file_env_name)
        options.append(env_name)
    return ", ".join(options)


def _referenced_source_ids(
    *,
    artifacts: list[ArtifactRecord],
    claim_by_id: dict[UUID, ClaimRecord],
) -> set[UUID]:
    source_ids = {
        source_id
        for artifact in artifacts
        for source_id in artifact.source_ids
    }
    for artifact in artifacts:
        for claim_id in _extract_claim_ids(artifact):
            claim = claim_by_id.get(claim_id)
            if claim is not None:
                source_ids.update(claim.source_ids)
    return source_ids


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


def _latest_audit_by_artifact(
    audits: list[GuardrailAuditRecord],
) -> dict[UUID, GuardrailAuditRecord]:
    latest: dict[UUID, GuardrailAuditRecord] = {}
    for audit in audits:
        current = latest.get(audit.artifact_id)
        if current is None or audit.created_at > current.created_at:
            latest[audit.artifact_id] = audit
    return latest


def _open_feedback_count(feedback_items: list[FeedbackItem]) -> int:
    return len(
        [
            item
            for item in feedback_items
            if item.status in {FeedbackStatus.OPEN, FeedbackStatus.ROUTED}
        ]
    )


def _dedupe(items: list[str]) -> list[str]:
    deduped = []
    for item in items:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _next_actions(issues: list[str]) -> list[str]:
    action_by_issue = {
        "no_publishable_artifacts": "Generate content artifacts before approval.",
        "no_source_records": "Run web research and record source records.",
        "no_claim_records": "Extract content claims and record claim records.",
        "weak_source_records": "Replace placeholder or weak source records with concrete sources.",
        "stale_source_records": "Refresh stale sources or add newer corroborating evidence.",
        "source_freshness_unknown": "Verify publication dates or mark evergreen sources explicitly.",
        "no_accepted_retrieval_evidence": "Build or repair the retrieval quality ledger until it has accepted source evidence.",
        "retrieval_quality_not_ready": "Repair retrieval recall, precision, and coverage gaps until the latest retrieval quality ledger is ready.",
        "unsupported_claims": "Remove or rewrite unsupported claims.",
        "claims_need_review": "Run claim verification and resolve needs-review claims.",
        "claim_missing_accepted_retrieval_evidence": "Rewrite or hold claims that do not map to accepted retrieval evidence.",
        "missing_artifact_source_dependencies": "Attach source dependencies to each artifact.",
        "artifact_references_unknown_sources": "Repair artifact source references.",
        "artifact_references_weak_sources": "Replace weak sources referenced by artifacts.",
        "artifact_sources_need_freshness_review": "Review source freshness for each referenced artifact.",
        "artifact_missing_accepted_retrieval_evidence": "Revise artifacts so source dependencies use accepted retrieval evidence.",
        "missing_claim_dependencies": "Attach claim dependencies to each artifact.",
        "artifact_references_unknown_claims": "Repair artifact claim references.",
        "deterministic_fallback_content_not_publishable": "Regenerate written content with the Gemma 4 Hugging Face expert layer before publishing.",
        "publishable_content_requires_gemma4_hf_provenance": "Use Gemma 4 on Hugging Face for publishable written content and record that provenance.",
        "missing_guardrail_audit": "Run the guardrail audit loop for current artifacts.",
        "blocked_guardrail_audit": "Resolve blocked guardrail audit findings.",
        "guardrail_audit_needs_revision": "Revise artifacts with guardrail findings.",
        "unresolved_feedback_items": "Resolve or route open human feedback items.",
        "missing_publish_channel_credentials": "Configure publishing-channel credentials before live publication.",
        "unsupported_publish_channel": "Add a credential and policy mapping for unsupported publish channels before live publication.",
        "publish_channel_policy_review_required": "Confirm platform policy, account permissions, and human approval before live publication.",
    }
    return [action_by_issue[issue] for issue in issues if issue in action_by_issue]


def _summary(
    status: PublishReadinessStatus, artifacts: list[ArtifactRecord], issues: list[str]
) -> str:
    if status == PublishReadinessStatus.READY:
        return f"{len(artifacts)} artifact(s) are publish-ready."
    return (
        f"Publishing readiness is {status.value} for {len(artifacts)} artifact(s): "
        f"{', '.join(issues)}."
    )
