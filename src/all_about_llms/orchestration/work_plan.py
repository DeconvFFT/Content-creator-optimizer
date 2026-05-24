from typing import Any
from uuid import UUID

from all_about_llms.contracts import (
    AgentMessage,
    AgentTaskStatus,
    ArtifactRecord,
    ArtifactType,
    ClaimRecord,
    ClaimSupportStatus,
    FeedbackItem,
    FeedbackStatus,
    GuardrailAuditStatus,
    RunEvent,
    RunStatus,
    RunWorkPlanItem,
    RunWorkPlanRequest,
    RunWorkPlanResult,
    SourceFreshnessStatus,
    SourceQualityStatus,
    SourceRecord,
    WorkerProfileStatus,
)
from all_about_llms.orchestration.a2a_projection import (
    public_a2a_message_event_payload,
)
from all_about_llms.orchestration.source_quality import evaluate_source_quality


class RunWorkPlanError(RuntimeError):
    """Base error for Sprint/Progress Agent run planning."""


class RunWorkPlanRunNotFoundError(RunWorkPlanError):
    """Raised when a run work plan references a missing run."""


PENDING_TASK_STATUSES = {
    AgentTaskStatus.ACCEPTED,
    AgentTaskStatus.CLAIMED,
    AgentTaskStatus.IN_PROGRESS,
    AgentTaskStatus.WAITING_FOR_HUMAN,
    AgentTaskStatus.BLOCKED,
}

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

FOLLOWUP_TASK_TYPES = {
    "audit_fix": "fix_guardrail_audit_blockers",
    "claim_review": "resolve_flagged_claims",
    "foundation_audit_remediation": "resolve_foundation_audit_finding",
    "guardrail_audit": "run_guardrail_audit",
    "routed_feedback": "incorporate_human_feedback",
    "source_freshness_review": "verify_source_freshness",
    "source_grounding": "attach_source_dependencies",
    "source_research": "replace_weak_sources",
}

DEDUPED_TASK_STATUSES = {
    AgentTaskStatus.ACCEPTED,
    AgentTaskStatus.CLAIMED,
    AgentTaskStatus.IN_PROGRESS,
    AgentTaskStatus.WAITING_FOR_HUMAN,
    AgentTaskStatus.BLOCKED,
    AgentTaskStatus.COMPLETED,
}


class RunWorkPlanWorkflow:
    """Build a current, durable work plan for the next autonomous agent pass."""

    def __init__(self, store):
        self._store = store

    async def build(
        self, run_id: UUID, request: RunWorkPlanRequest
    ) -> RunWorkPlanResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise RunWorkPlanRunNotFoundError(f"Run not found: {run_id}")

        messages = await self._store.list_agent_messages(run_id)
        feedback_items = await self._store.list_feedback(run_id)
        sources = await self._store.list_sources(run_id)
        artifacts = await self._store.list_artifacts(run_id)
        claims = await self._store.list_claims(run_id)
        audits = await self._store.list_guardrail_audits(run_id)
        worker_profiles = await self._store.list_worker_profiles(run_id)

        items = _build_plan_items(
            run_status=run.status,
            messages=messages,
            feedback_items=feedback_items,
            sources=sources,
            artifacts=artifacts,
            claims=claims,
            audits=audits,
            worker_profiles=worker_profiles,
            include_completed_tasks=request.include_completed_tasks,
        )[: request.max_items]
        created_messages: list[AgentMessage] = []
        skipped_duplicate_task_count = 0
        if request.create_followup_tasks:
            (
                created_messages,
                skipped_duplicate_task_count,
            ) = await self._materialize_followup_tasks(
                run_id=run_id,
                items=items,
                existing_messages=messages,
            )
        created_task_message_ids = [
            message.message_id for message in created_messages
        ]
        pending_task_count = _pending_task_count(messages) + len(created_messages)

        artifact_id = None
        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.SYSTEM_PLAN,
                title="Autonomous run work plan",
                uri="",
                content={
                    "plan_items": [
                        item.model_dump(mode="json") for item in items
                    ],
                    "recommended_agent_ids": _recommended_agent_ids(items),
                    "open_feedback_count": _feedback_count(
                        feedback_items,
                        FeedbackStatus.OPEN,
                    ),
                    "routed_feedback_count": _feedback_count(
                        feedback_items,
                        FeedbackStatus.ROUTED,
                    ),
                    "pending_task_count": pending_task_count,
                    "blocked_item_count": _blocked_item_count(items),
                    "created_task_message_ids": [
                        str(message_id) for message_id in created_task_message_ids
                    ],
                    "skipped_duplicate_task_count": skipped_duplicate_task_count,
                    "refresh_reason": request.refresh_reason,
                },
                provenance={
                    "workflow": "run_work_plan_v1",
                    "created_by": "sprint-progress-agent",
                    "refresh_reason": request.refresh_reason,
                    "source_message_ids": [
                        str(message.message_id) for message in messages
                    ],
                    "source_feedback_ids": [
                        str(feedback.feedback_id) for feedback in feedback_items
                    ],
                    "created_task_message_ids": [
                        str(message_id) for message_id in created_task_message_ids
                    ],
                },
            )
            artifact.uri = (
                f"artifact://runs/{run_id}/work-plans/{artifact.artifact_id}"
            )
            await self._store.record_artifact(artifact)
            artifact_id = artifact.artifact_id

        event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="run_work_plan_built",
                actor="sprint-progress-agent",
                payload={
                    "artifact_id": str(artifact_id) if artifact_id else None,
                    "plan_item_count": len(items),
                    "recommended_agent_ids": _recommended_agent_ids(items),
                    "open_feedback_count": _feedback_count(
                        feedback_items,
                        FeedbackStatus.OPEN,
                    ),
                    "routed_feedback_count": _feedback_count(
                        feedback_items,
                        FeedbackStatus.ROUTED,
                    ),
                    "pending_task_count": pending_task_count,
                    "blocked_item_count": _blocked_item_count(items),
                    "created_task_message_ids": [
                        str(message_id) for message_id in created_task_message_ids
                    ],
                    "skipped_duplicate_task_count": skipped_duplicate_task_count,
                    "refresh_reason": request.refresh_reason,
                },
            )
        )

        return RunWorkPlanResult(
            run_id=run_id,
            plan_items=items,
            recommended_agent_ids=_recommended_agent_ids(items),
            open_feedback_count=_feedback_count(feedback_items, FeedbackStatus.OPEN),
            routed_feedback_count=_feedback_count(
                feedback_items,
                FeedbackStatus.ROUTED,
            ),
            pending_task_count=pending_task_count,
            blocked_item_count=_blocked_item_count(items),
            created_task_message_ids=created_task_message_ids,
            skipped_duplicate_task_count=skipped_duplicate_task_count,
            artifact_id=artifact_id,
            event_id=event.event_id,
            refresh_reason=request.refresh_reason,
            summary=_summary(
                items,
                created_task_count=len(created_messages),
                skipped_duplicate_task_count=skipped_duplicate_task_count,
            ),
        )

    async def _materialize_followup_tasks(
        self,
        *,
        run_id: UUID,
        items: list[RunWorkPlanItem],
        existing_messages: list[AgentMessage],
    ) -> tuple[list[AgentMessage], int]:
        signatures = {
            str(message.payload.get("work_plan_signature"))
            for message in existing_messages
            if message.payload.get("work_plan_signature")
            and message.status in DEDUPED_TASK_STATUSES
        }
        created_messages: list[AgentMessage] = []
        skipped_duplicates = 0
        for item in items:
            task_type = FOLLOWUP_TASK_TYPES.get(item.item_type)
            if task_type is None:
                continue
            signature = _work_plan_signature(item)
            if signature in signatures:
                skipped_duplicates += 1
                continue
            message = AgentMessage(
                run_id=run_id,
                sender_agent_id="sprint-progress-agent",
                recipient_agent_id=item.owner_agent_id,
                task_type=task_type,
                payload={
                    "work_plan_item_id": str(item.item_id),
                    "work_plan_item_type": item.item_type,
                    "work_plan_signature": signature,
                    "title": item.title,
                    "recommended_action": item.recommended_action,
                    "reason": item.reason,
                    "priority": item.priority,
                    "blocking": item.blocking,
                    "source_message_id": (
                        str(item.source_message_id)
                        if item.source_message_id
                        else None
                    ),
                    "source_feedback_id": (
                        str(item.source_feedback_id)
                        if item.source_feedback_id
                        else None
                    ),
                    "metadata": item.metadata,
                },
            )
            await self._store.record_agent_message(message)
            await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="agent_message_accepted",
                    actor="sprint-progress-agent",
                    payload=public_a2a_message_event_payload(message),
                )
            )
            created_messages.append(message)
            signatures.add(signature)
        return created_messages, skipped_duplicates


def _build_plan_items(
    *,
    run_status: RunStatus,
    messages: list[AgentMessage],
    feedback_items: list[FeedbackItem],
    sources: list[SourceRecord],
    artifacts: list[ArtifactRecord],
    claims: list[ClaimRecord],
    audits,
    worker_profiles,
    include_completed_tasks: bool,
) -> list[RunWorkPlanItem]:
    feedback_by_id = {
        str(feedback.feedback_id): feedback for feedback in feedback_items
    }
    linked_feedback_ids = set()
    items: list[RunWorkPlanItem] = []
    messages_by_id = {message.message_id: message for message in messages}
    dependency_cycles = _dependency_cycles(messages, messages_by_id)
    dependency_cycle_message_ids = {
        message_id for cycle in dependency_cycles for message_id in cycle
    }

    if run_status == RunStatus.WAITING_FOR_HUMAN:
        items.append(
            RunWorkPlanItem(
                item_type="human_gate",
                title="Resolve run-level human gate",
                owner_agent_id="forward-deployed-engineer",
                status="waiting_for_human",
                priority="high",
                blocking=True,
                recommended_action=(
                    "Ask the user for approval or correction, then resolve "
                    "the feedback gate."
                ),
                reason="Run status is waiting_for_human.",
            )
        )

    for feedback in feedback_items:
        if feedback.status == FeedbackStatus.OPEN:
            items.append(_open_feedback_item(feedback))

    message_items = []
    for message in messages:
        if (
            message.status not in PENDING_TASK_STATUSES
            and not include_completed_tasks
        ):
            continue
        feedback_id = _message_feedback_id(message)
        if feedback_id:
            linked_feedback_ids.add(feedback_id)
        feedback = feedback_by_id.get(feedback_id) if feedback_id else None
        message_items.append(
            _message_item(
                message,
                feedback,
                messages_by_id,
                dependency_cycle_message_ids,
                dependency_cycles,
            )
        )
    items.extend(message_items)

    for feedback in feedback_items:
        if feedback.status != FeedbackStatus.ROUTED:
            continue
        if str(feedback.feedback_id) in linked_feedback_ids:
            continue
        items.append(_unlinked_routed_feedback_item(feedback))

    items.extend(
        _quality_gate_items(
            artifacts=artifacts,
            claims=claims,
            sources=sources,
            audits=audits,
        )
    )
    items.extend(_foundation_audit_items(artifacts))

    active_profiles = [
        profile
        for profile in worker_profiles
        if profile.status == WorkerProfileStatus.ACTIVE
    ]
    pending_agents = sorted(
        {
            message.recipient_agent_id
            for message in messages
            if message.status in {
                AgentTaskStatus.ACCEPTED,
                AgentTaskStatus.CLAIMED,
                AgentTaskStatus.IN_PROGRESS,
            }
        }
    )
    if pending_agents and not active_profiles:
        items.append(
            RunWorkPlanItem(
                item_type="worker_profile",
                title="Create or start an always-on worker profile",
                owner_agent_id="agent-harness-engineer",
                status="needed",
                priority="normal",
                recommended_action=(
                    "Create or start a worker profile covering: "
                    + ", ".join(pending_agents)
                    + "."
                ),
                reason="Pending A2A tasks exist but no active worker profile is running.",
                metadata={"pending_agent_ids": pending_agents},
            )
        )
    elif active_profiles:
        items.append(
            RunWorkPlanItem(
                item_type="worker_heartbeat",
                title="Heartbeat active worker profiles",
                owner_agent_id="agent-harness-engineer",
                status="ready",
                priority="normal",
                recommended_action=(
                    "Run the worker profile scheduler or heartbeat active profiles."
                ),
                reason="At least one active worker profile can process due tasks.",
                metadata={
                    "active_profile_ids": [
                        str(profile.profile_id) for profile in active_profiles
                    ]
                },
            )
        )

    return sorted(items, key=_sort_key)


def _foundation_audit_items(
    artifacts: list[ArtifactRecord],
) -> list[RunWorkPlanItem]:
    audits = [
        artifact
        for artifact in artifacts
        if artifact.artifact_type == ArtifactType.FOUNDATION_AUDIT
    ]
    if not audits:
        return []
    latest_audit = max(audits, key=lambda artifact: artifact.created_at)
    remediation_items = latest_audit.content.get("remediation_items")
    if not isinstance(remediation_items, list):
        remediation_items = _remediation_items_from_foundation_checks(
            latest_audit.content.get("checks", [])
        )
    items = []
    for remediation in remediation_items:
        if not isinstance(remediation, dict):
            continue
        check_id = str(remediation.get("check_id") or "unknown-foundation-check")
        owner_agent_id = str(
            remediation.get("owner_agent_id") or "product-manager"
        )
        blocking = bool(remediation.get("blocking"))
        missing = remediation.get("missing") or []
        if not isinstance(missing, list):
            missing = [str(missing)]
        items.append(
            RunWorkPlanItem(
                item_type="foundation_audit_remediation",
                title=f"Resolve foundation audit: {remediation.get('title') or check_id}",
                owner_agent_id=owner_agent_id,
                status=str(remediation.get("status") or "needs_attention"),
                priority=str(
                    remediation.get("priority")
                    or ("high" if blocking else "normal")
                ),
                blocking=blocking,
                recommended_action=str(
                    remediation.get("recommended_action")
                    or "Resolve the latest foundation audit finding."
                ),
                reason="; ".join(str(item) for item in missing)
                or str(
                    remediation.get("requirement")
                    or "Foundation audit check needs attention."
                ),
                metadata={
                    "foundation_audit_artifact_id": str(latest_audit.artifact_id),
                    "foundation_audit_check_id": check_id,
                    "missing": [str(item) for item in missing],
                    "requirement": remediation.get("requirement"),
                },
            )
        )
    return items


def _remediation_items_from_foundation_checks(checks) -> list[dict[str, Any]]:
    remediation_items = []
    if not isinstance(checks, list):
        return remediation_items
    for check in checks:
        if not isinstance(check, dict):
            continue
        if check.get("status") == "pass":
            continue
        remediation_items.append(
            {
                "check_id": check.get("check_id"),
                "title": check.get("title"),
                "status": check.get("status"),
                "owner_agent_id": check.get("owner_agent_id"),
                "priority": "high" if check.get("status") == "fail" else "normal",
                "blocking": check.get("status") == "fail",
                "missing": check.get("missing", []),
                "recommended_action": (
                    "Resolve: " + "; ".join(check.get("missing", [])[:3])
                    if check.get("missing")
                    else "Resolve the latest foundation audit finding."
                ),
                "requirement": check.get("requirement"),
            }
        )
    return remediation_items


def _open_feedback_item(feedback: FeedbackItem) -> RunWorkPlanItem:
    return RunWorkPlanItem(
        item_type="open_feedback",
        title="Resolve open feedback",
        owner_agent_id=feedback.target_agent_id or "forward-deployed-engineer",
        status=feedback.status.value,
        priority="high",
        blocking=True,
        source_feedback_id=feedback.feedback_id,
        recommended_action="Clarify, accept, reject, or convert this feedback into routed work.",
        reason=feedback.feedback_text,
        metadata={"author": feedback.author},
    )


def _message_item(
    message: AgentMessage,
    feedback: FeedbackItem | None,
    messages_by_id: dict[UUID, AgentMessage],
    dependency_cycle_message_ids: set[UUID],
    dependency_cycles: list[list[UUID]],
) -> RunWorkPlanItem:
    retry_exhausted = _retry_exhausted(message)
    unmet_dependency_ids = _unmet_dependency_message_ids(message, messages_by_id)
    in_dependency_cycle = message.message_id in dependency_cycle_message_ids
    waiting_for_dependencies = (
        message.status == AgentTaskStatus.ACCEPTED and bool(unmet_dependency_ids)
    )
    blocking = message.status in {
        AgentTaskStatus.WAITING_FOR_HUMAN,
        AgentTaskStatus.BLOCKED,
    } or waiting_for_dependencies or in_dependency_cycle
    return RunWorkPlanItem(
        item_type=(
            "retry_exhausted_task"
            if retry_exhausted
            else "dependency_cycle_task"
            if in_dependency_cycle
            else "dependency_waiting_task"
            if waiting_for_dependencies
            else "feedback_task" if feedback else "agent_task"
        ),
        title=_message_title(
            message,
            feedback,
            unmet_dependency_ids,
            in_dependency_cycle,
        ),
        owner_agent_id=(
            "agent-harness-engineer"
            if retry_exhausted or waiting_for_dependencies or in_dependency_cycle
            else message.recipient_agent_id
        ),
        status=message.status.value,
        priority="high" if blocking else "normal",
        blocking=blocking,
        source_message_id=message.message_id,
        source_feedback_id=feedback.feedback_id if feedback else None,
        recommended_action=_message_action(
            message,
            unmet_dependency_ids,
            in_dependency_cycle,
        ),
        reason=_message_reason(
            message,
            feedback,
            unmet_dependency_ids,
            in_dependency_cycle,
        ),
        metadata={
            "task_type": message.task_type,
            "sender_agent_id": message.sender_agent_id,
            "recipient_agent_id": message.recipient_agent_id,
            "requires_human_feedback": message.requires_human_feedback,
            "attempt_count": message.attempt_count,
            "max_attempts": message.max_attempts,
            "retry_exhausted": retry_exhausted,
            "in_dependency_cycle": in_dependency_cycle,
            "dependency_cycles": [
                [str(message_id) for message_id in cycle]
                for cycle in dependency_cycles
                if message.message_id in cycle
            ],
            "handoff_trace_count": len(message.handoff_trace),
            "latest_handoff_action": (
                message.handoff_trace[-1].get("action")
                if message.handoff_trace
                else None
            ),
            "depends_on_message_ids": [
                str(dependency_id)
                for dependency_id in message.depends_on_message_ids
            ],
            "unmet_dependency_message_ids": [
                str(dependency_id) for dependency_id in unmet_dependency_ids
            ],
        },
    )


def _unlinked_routed_feedback_item(feedback: FeedbackItem) -> RunWorkPlanItem:
    return RunWorkPlanItem(
        item_type="routed_feedback",
        title="Create missing A2A task for routed feedback",
        owner_agent_id=feedback.target_agent_id or "forward-deployed-engineer",
        status=feedback.status.value,
        priority="normal",
        source_feedback_id=feedback.feedback_id,
        recommended_action=(
            "Create or recover the specialist A2A task linked to this feedback."
        ),
        reason=feedback.feedback_text,
        metadata={"route_reason": feedback.metadata.get("route_reason")},
    )


def _quality_gate_items(
    *,
    artifacts: list[ArtifactRecord],
    claims: list[ClaimRecord],
    sources: list[SourceRecord],
    audits,
) -> list[RunWorkPlanItem]:
    items: list[RunWorkPlanItem] = []
    publishable_artifacts = [
        artifact
        for artifact in artifacts
        if artifact.artifact_type in PUBLISHABLE_ARTIFACT_TYPES
    ]
    audited_artifact_ids = {audit.artifact_id for audit in audits}
    unaudited_artifacts = [
        artifact
        for artifact in publishable_artifacts
        if artifact.artifact_id not in audited_artifact_ids
    ]
    if unaudited_artifacts:
        items.append(
            RunWorkPlanItem(
                item_type="guardrail_audit",
                title="Run guardrail audit on current artifacts",
                owner_agent_id="guardrails-agent",
                status="needed",
                priority="high",
                recommended_action="Run `/api/runs/{run_id}/guardrail-audit`.",
                reason="Publishable artifacts exist without guardrail audit records.",
                metadata={
                    "artifact_ids": [
                        str(artifact.artifact_id) for artifact in unaudited_artifacts
                    ],
                    "artifact_count": len(unaudited_artifacts),
                },
            )
        )

    ungrounded_artifacts = [
        artifact for artifact in publishable_artifacts if not artifact.source_ids
    ]
    if ungrounded_artifacts:
        items.append(
            RunWorkPlanItem(
                item_type="source_grounding",
                title="Add source dependencies to ungrounded artifacts",
                owner_agent_id="source-ledger-agent",
                status="needed",
                priority="high",
                blocking=True,
                recommended_action=(
                    "Attach source records and claim links before publishing."
                ),
                reason="One or more artifacts have no source dependencies.",
                metadata={
                    "artifact_ids": [
                        str(artifact.artifact_id)
                        for artifact in ungrounded_artifacts
                    ]
                },
            )
        )

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
    if unsupported_claims or needs_review_claims:
        items.append(
            RunWorkPlanItem(
                item_type="claim_review",
                title="Resolve unsupported or needs-review claims",
                owner_agent_id="claim-verification-agent",
                status="needed",
                priority="high",
                blocking=bool(unsupported_claims),
                recommended_action="Verify, source, rewrite, or remove flagged claims.",
                reason="Claims still need evidence decisions before publishing.",
                metadata={
                    "unsupported_claim_ids": [
                        str(claim.claim_id) for claim in unsupported_claims
                    ],
                    "needs_review_claim_ids": [
                        str(claim.claim_id) for claim in needs_review_claims
                    ],
                },
            )
        )

    claim_by_id = {claim.claim_id: claim for claim in claims}
    referenced_source_ids = _referenced_source_ids(
        artifacts=publishable_artifacts,
        claim_by_id=claim_by_id,
    )
    source_entries = [
        evaluate_source_quality(source)
        for source in sources
        if source.source_id in referenced_source_ids
    ]
    weak_sources = [
        entry
        for entry in source_entries
        if entry.quality_status == SourceQualityStatus.WEAK
    ]
    stale_or_unknown_sources = [
        entry
        for entry in source_entries
        if entry.freshness_status
        in {
            SourceFreshnessStatus.STALE,
            SourceFreshnessStatus.UNKNOWN,
        }
    ]
    if weak_sources:
        items.append(
            RunWorkPlanItem(
                item_type="source_research",
                title="Replace weak or placeholder sources",
                owner_agent_id="web-research-agent",
                status="needed",
                priority="high",
                blocking=True,
                recommended_action=(
                    "Run web research and replace weak source records before publishing."
                ),
                reason="One or more source records are weak placeholders or low-confidence evidence.",
                metadata={
                    "weak_source_ids": [
                        str(entry.source_id) for entry in weak_sources
                    ],
                    "weak_citation_ids": [
                        entry.citation_id for entry in weak_sources
                    ],
                },
            )
        )
    elif stale_or_unknown_sources:
        items.append(
            RunWorkPlanItem(
                item_type="source_freshness_review",
                title="Verify stale or unknown-freshness sources",
                owner_agent_id="web-research-agent",
                status="needed",
                priority="normal",
                recommended_action=(
                    "Check publication dates or add fresher corroborating sources."
                ),
                reason="Some sources need freshness review before final approval.",
                metadata={
                    "source_ids": [
                        str(entry.source_id) for entry in stale_or_unknown_sources
                    ],
                    "citation_ids": [
                        entry.citation_id for entry in stale_or_unknown_sources
                    ],
                },
            )
        )

    blocking_audits = [
        audit
        for audit in audits
        if audit.status
        in {
            GuardrailAuditStatus.BLOCKED,
            GuardrailAuditStatus.NEEDS_REVISION,
        }
    ]
    if blocking_audits:
        items.append(
            RunWorkPlanItem(
                item_type="audit_fix",
                title="Fix guardrail audit blockers",
                owner_agent_id="guardrails-agent",
                status="needed",
                priority="high",
                blocking=True,
                recommended_action="Route audit blockers to the owning content agents.",
                reason="Latest audit state contains blocked or needs-revision records.",
                metadata={
                    "audit_ids": [str(audit.audit_id) for audit in blocking_audits]
                },
            )
        )
    return items


def _message_feedback_id(message: AgentMessage) -> str | None:
    value = message.payload.get("feedback_id")
    if isinstance(value, str) and value:
        return value
    return None


def _work_plan_signature(item: RunWorkPlanItem) -> str:
    if item.source_feedback_id:
        source_key = f"feedback:{item.source_feedback_id}"
    elif item.source_message_id:
        source_key = f"message:{item.source_message_id}"
    else:
        metadata_ids = _metadata_identity(item.metadata)
        source_key = metadata_ids or item.title
    return f"{item.item_type}:{item.owner_agent_id}:{source_key}"


def _metadata_identity(metadata: dict[str, Any]) -> str:
    identity_keys = [
        "artifact_ids",
        "audit_ids",
        "citation_ids",
        "foundation_audit_artifact_id",
        "foundation_audit_check_id",
        "needs_review_claim_ids",
        "source_ids",
        "unsupported_claim_ids",
        "weak_citation_ids",
        "weak_source_ids",
    ]
    values = []
    for key in identity_keys:
        value = metadata.get(key)
        if isinstance(value, list) and value:
            values.append(f"{key}={','.join(sorted(str(item) for item in value))}")
        elif isinstance(value, str) and value:
            values.append(f"{key}={value}")
    return "|".join(values)


def _message_title(
    message: AgentMessage,
    feedback: FeedbackItem | None,
    unmet_dependency_ids: list[UUID],
    in_dependency_cycle: bool,
) -> str:
    if _retry_exhausted(message):
        return f"Authorize retry for exhausted {message.recipient_agent_id} task"
    if in_dependency_cycle:
        return f"Break circular A2A dependency for {message.recipient_agent_id}"
    if unmet_dependency_ids:
        return f"Wait for upstream dependencies before {message.recipient_agent_id}"
    if feedback:
        return f"Process feedback for {message.recipient_agent_id}"
    return f"Run {message.task_type} for {message.recipient_agent_id}"


def _message_action(
    message: AgentMessage,
    unmet_dependency_ids: list[UUID],
    in_dependency_cycle: bool,
) -> str:
    if _retry_exhausted(message):
        return (
            "Review the task error, then authorize retry from the cockpit or "
            "`POST /api/a2a/messages/{message_id}/retry`."
        )
    if in_dependency_cycle:
        return (
            "Remove or replace one circular `depends_on_message_ids` edge, then "
            "rebuild the A2A graph before running workers."
        )
    if unmet_dependency_ids:
        return (
            "Complete or repair upstream A2A dependencies before this task is "
            "claimable."
        )
    if message.status == AgentTaskStatus.ACCEPTED:
        return f"Run worker for {message.recipient_agent_id}."
    if message.status == AgentTaskStatus.CLAIMED:
        return f"Resume claimed task for {message.recipient_agent_id}."
    if message.status == AgentTaskStatus.IN_PROGRESS:
        return f"Continue in-progress task for {message.recipient_agent_id}."
    if message.status == AgentTaskStatus.WAITING_FOR_HUMAN:
        return "Collect human input before continuing this task."
    if message.status == AgentTaskStatus.BLOCKED:
        return "Route blocker to the Forward Deployed Engineer."
    return "Review task result and decide whether follow-up is needed."


def _message_reason(
    message: AgentMessage,
    feedback: FeedbackItem | None,
    unmet_dependency_ids: list[UUID],
    in_dependency_cycle: bool,
) -> str:
    if _retry_exhausted(message):
        return (
            f"Task reached retry cap {message.attempt_count}/"
            f"{message.max_attempts}: {message.error or 'retry attempts exhausted'}"
        )
    if in_dependency_cycle:
        return (
            "Task is part of an active circular A2A dependency and cannot become "
            "claimable until the dependency graph is repaired."
        )
    if unmet_dependency_ids:
        return (
            "Task depends on unfinished or missing upstream A2A messages: "
            + ", ".join(str(dependency_id) for dependency_id in unmet_dependency_ids)
        )
    if feedback:
        return feedback.feedback_text
    instruction = message.payload.get("instruction")
    if isinstance(instruction, str) and instruction:
        return instruction
    return f"Pending A2A task `{message.task_type}`."


def _retry_exhausted(message: AgentMessage) -> bool:
    retry_policy = message.result.get("retry_policy", {})
    retry_policy_attempts = retry_policy.get("attempt_count", message.attempt_count)
    retry_policy_max_attempts = retry_policy.get("max_attempts", message.max_attempts)
    return (
        message.status == AgentTaskStatus.BLOCKED
        and retry_policy_attempts >= retry_policy_max_attempts
    )


def _unmet_dependency_message_ids(
    message: AgentMessage,
    messages_by_id: dict[UUID, AgentMessage],
) -> list[UUID]:
    unmet_dependency_ids = []
    for dependency_id in message.depends_on_message_ids:
        dependency = messages_by_id.get(dependency_id)
        if dependency is None or dependency.status != AgentTaskStatus.COMPLETED:
            unmet_dependency_ids.append(dependency_id)
    return unmet_dependency_ids


def _dependency_cycles(
    messages: list[AgentMessage],
    messages_by_id: dict[UUID, AgentMessage],
) -> list[list[UUID]]:
    active_message_ids = {
        message.message_id
        for message in messages
        if message.status != AgentTaskStatus.COMPLETED
    }
    adjacency = {
        message.message_id: sorted(
            [
                dependency_id
                for dependency_id in message.depends_on_message_ids
                if dependency_id in messages_by_id
                and dependency_id in active_message_ids
            ],
            key=str,
        )
        for message in messages
        if message.message_id in active_message_ids
    }
    cycles_by_key: dict[tuple[str, ...], list[UUID]] = {}

    def visit(node_id: UUID, path: list[UUID]) -> None:
        if node_id in path:
            cycle = path[path.index(node_id) :]
            cycles_by_key.setdefault(_canonical_cycle_key(cycle), cycle)
            return
        for dependency_id in adjacency.get(node_id, []):
            visit(dependency_id, [*path, node_id])

    for message_id in sorted(adjacency, key=str):
        visit(message_id, [])
    return [cycles_by_key[key] for key in sorted(cycles_by_key)]


def _canonical_cycle_key(cycle: list[UUID]) -> tuple[str, ...]:
    cycle_values = [str(message_id) for message_id in cycle]
    rotations = [
        tuple(cycle_values[index:] + cycle_values[:index])
        for index in range(len(cycle_values))
    ]
    return min(rotations)


def _feedback_count(
    feedback_items: list[FeedbackItem],
    status: FeedbackStatus,
) -> int:
    return sum(1 for feedback in feedback_items if feedback.status == status)


def _pending_task_count(messages: list[AgentMessage]) -> int:
    return sum(1 for message in messages if message.status in PENDING_TASK_STATUSES)


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
        except (TypeError, ValueError):
            continue
        if claim_id not in claim_ids:
            claim_ids.append(claim_id)
    return claim_ids


def _blocked_item_count(items: list[RunWorkPlanItem]) -> int:
    return sum(1 for item in items if item.blocking)


def _recommended_agent_ids(items: list[RunWorkPlanItem]) -> list[str]:
    return sorted({item.owner_agent_id for item in items if item.status != "completed"})


def _summary(
    items: list[RunWorkPlanItem],
    *,
    created_task_count: int = 0,
    skipped_duplicate_task_count: int = 0,
) -> str:
    blocked = _blocked_item_count(items)
    materialized = ""
    if created_task_count or skipped_duplicate_task_count:
        materialized = (
            f" Created {created_task_count} follow-up task(s); "
            f"skipped {skipped_duplicate_task_count} duplicate(s)."
        )
    if not items:
        return "No immediate work items found; wait for the next user turn or agent task."
    if blocked:
        return (
            f"Built work plan with {len(items)} item(s), including "
            f"{blocked} blocker(s).{materialized}"
        )
    return f"Built work plan with {len(items)} runnable item(s) and no blockers.{materialized}"


def _sort_key(item: RunWorkPlanItem) -> tuple[int, str, str]:
    priority_rank = {"high": 0, "normal": 1, "low": 2}.get(item.priority, 1)
    blocking_rank = 0 if item.blocking else 1
    return (blocking_rank, priority_rank, item.owner_agent_id)
