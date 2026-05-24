from collections import defaultdict
from pathlib import Path
from uuid import UUID

import yaml

from all_about_llms.agents import AGENT_ROSTER, get_agent_card, skill_cards_for_agent
from all_about_llms.agents import SKILL_CARDS
from all_about_llms.contracts import (
    AgentMessage,
    AgentTaskStatus,
    ArtifactRecord,
    ArtifactType,
    RunEvent,
    SkillSourceContractEntry,
    SkillUsageEntry,
    SkillUsageLedgerRequest,
    SkillUsageLedgerResult,
)


class SkillUsageLedgerError(RuntimeError):
    """Base error for skill usage ledger generation."""


class SkillUsageLedgerRunNotFoundError(SkillUsageLedgerError):
    """Raised when a skill usage ledger references a missing run."""


PROCESSED_STATUSES = {
    AgentTaskStatus.COMPLETED,
    AgentTaskStatus.FAILED,
    AgentTaskStatus.BLOCKED,
    AgentTaskStatus.WAITING_FOR_HUMAN,
}
PROJECT_ROOT = Path(__file__).resolve().parents[3]
REQUIRED_OPENAI_MANIFEST_INTERFACE_FIELDS = (
    "display_name",
    "short_description",
    "default_prompt",
)


class SkillUsageLedgerWorkflow:
    """Audit whether specialist workers are using their project skill cards."""

    def __init__(self, store):
        self._store = store

    async def build(
        self,
        run_id: UUID,
        request: SkillUsageLedgerRequest,
    ) -> SkillUsageLedgerResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise SkillUsageLedgerRunNotFoundError(f"Run not found: {run_id}")

        messages = await self._store.list_agent_messages(
            run_id,
            limit=request.max_messages,
        )
        if not request.include_pending_tasks:
            messages = [
                message
                for message in messages
                if message.status in PROCESSED_STATUSES
            ]
        events = await self._store.list_events(run_id, limit=request.max_events)
        invocation_events = _skill_invocation_events_by_message(events)

        entries = [
            _entry_for_message(message, invocation_events)
            for message in messages
        ]
        processed_entries = [
            entry
            for entry in entries
            if AgentTaskStatus(entry.status) in PROCESSED_STATUSES
        ]
        missing_skill_usage_message_ids = [
            entry.message_id
            for entry in processed_entries
            if not entry.has_result_skill_usage and not entry.has_invocation_event
        ]
        processed_agent_ids = {entry.agent_id for entry in processed_entries}
        relevant_agent_ids = _relevant_agent_ids(run.active_agents, messages)
        unprocessed_agent_ids = sorted(relevant_agent_ids - processed_agent_ids)
        skill_ids_used = sorted(
            {
                skill_id
                for entry in entries
                if entry.has_result_skill_usage or entry.has_invocation_event
                for skill_id in entry.skill_ids
            }
        )
        invocation_count = sum(
            1 for entry in entries if entry.has_result_skill_usage or entry.has_invocation_event
        )
        source_contracts = (
            build_skill_source_contracts(PROJECT_ROOT)
            if request.include_source_contracts
            else []
        )
        source_contract_issue_count = sum(
            entry.issue_count for entry in source_contracts
        )
        result = SkillUsageLedgerResult(
            run_id=run_id,
            agent_count=len(relevant_agent_ids),
            task_count=len(entries),
            processed_task_count=len(processed_entries),
            skill_count=len(skill_ids_used),
            skill_invocation_count=invocation_count,
            missing_skill_usage_message_ids=missing_skill_usage_message_ids,
            unprocessed_agent_ids=unprocessed_agent_ids,
            skill_source_contract_issue_count=source_contract_issue_count,
            skill_source_contracts=source_contracts,
            entries=entries,
            recommended_actions=_recommended_actions(
                entries=entries,
                missing_skill_usage_message_ids=missing_skill_usage_message_ids,
                unprocessed_agent_ids=unprocessed_agent_ids,
                source_contract_issue_count=source_contract_issue_count,
            ),
            summary=_summary(
                processed_task_count=len(processed_entries),
                invocation_count=invocation_count,
                missing_count=len(missing_skill_usage_message_ids),
                unprocessed_agent_count=len(unprocessed_agent_ids),
                source_contract_issue_count=source_contract_issue_count,
            ),
        )

        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.SKILL_USAGE_LEDGER,
                title="Agent skill usage ledger",
                uri=f"artifact://runs/{run_id}/skill-usage-ledger",
                content=result.model_dump(
                    mode="json",
                    exclude={"artifact_id", "event_id"},
                ),
                provenance={
                    "workflow": "skill_usage_ledger_v1",
                    "agent_id": "a2a-protocol-agent",
                    "include_pending_tasks": request.include_pending_tasks,
                    "include_source_contracts": request.include_source_contracts,
                    "max_messages": request.max_messages,
                    "max_events": request.max_events,
                    "source_message_ids": [
                        str(message.message_id) for message in messages
                    ],
                },
                revision_history=[
                    {
                        "actor": "a2a-protocol-agent",
                        "note": (
                            "Built an auditable ledger of project skill-card "
                            "usage across processed A2A tasks."
                        ),
                    }
                ],
            )
            result.artifact_id = artifact.artifact_id
            artifact.content["artifact_id"] = str(artifact.artifact_id)
            await self._store.record_artifact(artifact)
            await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="artifact_recorded",
                    actor="artifact-librarian",
                    payload=artifact.model_dump(mode="json"),
                )
            )

        event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="agent_skill_usage_ledger_built",
                actor="a2a-protocol-agent",
                payload={
                    "artifact_id": str(result.artifact_id)
                    if result.artifact_id
                    else None,
                    "agent_count": result.agent_count,
                    "task_count": result.task_count,
                    "processed_task_count": result.processed_task_count,
                    "skill_count": result.skill_count,
                    "skill_invocation_count": result.skill_invocation_count,
                    "missing_skill_usage_count": len(
                        result.missing_skill_usage_message_ids
                    ),
                    "unprocessed_agent_count": len(result.unprocessed_agent_ids),
                    "skill_source_contract_issue_count": (
                        result.skill_source_contract_issue_count
                    ),
                },
            )
        )
        result.event_id = event.event_id
        return result


def _skill_invocation_events_by_message(
    events: list[RunEvent],
) -> dict[UUID, list[RunEvent]]:
    by_message: dict[UUID, list[RunEvent]] = defaultdict(list)
    for event in events:
        if event.event_type != "agent_skill_invocation_recorded":
            continue
        message_id = event.payload.get("message_id")
        if not message_id:
            continue
        try:
            by_message[UUID(str(message_id))].append(event)
        except ValueError:
            continue
    return by_message


def _entry_for_message(
    message: AgentMessage,
    invocation_events: dict[UUID, list[RunEvent]],
) -> SkillUsageEntry:
    result_skill_usage = (
        message.result.get("skill_usage")
        if isinstance(message.result.get("skill_usage"), dict)
        else {}
    )
    declared_cards = skill_cards_for_agent(message.recipient_agent_id)
    event_payload = (
        invocation_events[message.message_id][-1].payload
        if invocation_events.get(message.message_id)
        else {}
    )
    skill_ids = (
        list(result_skill_usage.get("skill_ids") or [])
        or list(event_payload.get("skill_ids") or [])
        or [skill.id for skill in declared_cards]
    )
    source_paths = _first_mapping(
        result_skill_usage.get("skill_source_paths"),
        event_payload.get("skill_source_paths"),
        {skill.id: skill.source_path for skill in declared_cards},
    )
    outputs = _first_mapping(
        result_skill_usage.get("skill_outputs"),
        event_payload.get("skill_outputs"),
        {skill.id: skill.outputs for skill in declared_cards},
    )
    guardrails = _first_mapping(
        result_skill_usage.get("skill_guardrails"),
        event_payload.get("skill_guardrails"),
        {skill.id: skill.guardrails for skill in declared_cards},
    )
    return SkillUsageEntry(
        message_id=message.message_id,
        agent_id=message.recipient_agent_id,
        task_type=message.task_type,
        status=message.status.value,
        skill_ids=skill_ids,
        skill_source_paths={
            key: str(value) for key, value in source_paths.items()
        },
        declared_outputs={
            key: list(value) for key, value in outputs.items() if isinstance(value, list)
        },
        guardrails={
            key: list(value)
            for key, value in guardrails.items()
            if isinstance(value, list)
        },
        invocation_event_ids=[
            event.event_id
            for event in invocation_events.get(message.message_id, [])
            if event.event_id is not None
        ],
        has_result_skill_usage=bool(result_skill_usage),
        has_invocation_event=bool(invocation_events.get(message.message_id)),
        result_generation_mode=message.result.get("generation_mode"),
        artifact_ids=_artifact_ids_from_result(message.result),
        metadata={
            "sender_agent_id": message.sender_agent_id,
            "claimed_by_agent_id": message.claimed_by_agent_id,
            "requires_human_feedback": message.requires_human_feedback,
            "attempt_count": message.attempt_count,
            "max_attempts": message.max_attempts,
            "known_agent": get_agent_card(message.recipient_agent_id) is not None,
            "declared_skill_count": len(declared_cards),
        },
    )


def _first_mapping(*values) -> dict:
    for value in values:
        if isinstance(value, dict):
            return value
    return {}


def _artifact_ids_from_result(result: dict) -> list[str]:
    artifact_ids: list[str] = []
    for key, value in result.items():
        if key.endswith("artifact_id") and value:
            artifact_ids.append(str(value))
        elif key.endswith("artifact_ids") and isinstance(value, list):
            artifact_ids.extend(str(item) for item in value if item)
    return sorted(set(artifact_ids))


def build_skill_source_contracts(project_root: Path) -> list[SkillSourceContractEntry]:
    roster_ids = {agent.id for agent in AGENT_ROSTER}
    entries: list[SkillSourceContractEntry] = []
    for skill in SKILL_CARDS:
        source_path = project_root / skill.source_path
        manifest_path = source_path.parent / "agents" / "openai.yaml"
        frontmatter = _frontmatter(source_path)
        frontmatter_name = frontmatter.get("name")
        issues = []
        if not source_path.exists():
            issues.append("SKILL.md source file is missing.")
        if frontmatter_name != skill.id:
            issues.append("SKILL.md frontmatter name does not match skill card id.")
        if not frontmatter.get("description"):
            issues.append("SKILL.md frontmatter description is missing.")
        if not manifest_path.exists():
            issues.append("OpenAI agents manifest is missing.")
        else:
            manifest_issues = _openai_manifest_issues(manifest_path)
            issues.extend(manifest_issues)
        unknown_agent_ids = sorted(
            agent_id for agent_id in skill.applies_to_agents if agent_id not in roster_ids
        )
        if unknown_agent_ids:
            issues.append("Skill card references unknown agents.")
        if not skill.workflow_steps:
            issues.append("Skill card has no workflow steps.")
        if not skill.outputs:
            issues.append("Skill card has no declared outputs.")
        if not skill.guardrails:
            issues.append("Skill card has no guardrails.")
        entries.append(
            SkillSourceContractEntry(
                skill_id=skill.id,
                source_path=skill.source_path,
                file_exists=source_path.exists(),
                frontmatter_name=frontmatter_name,
                frontmatter_matches_card=frontmatter_name == skill.id,
                description_present=bool(frontmatter.get("description")),
                agents_manifest_exists=manifest_path.exists(),
                applies_to_agent_count=len(skill.applies_to_agents),
                unknown_agent_ids=unknown_agent_ids,
                issue_count=len(issues),
                issues=issues,
            )
        )
    return entries


def _openai_manifest_issues(path: Path) -> list[str]:
    try:
        parsed = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError):
        return ["OpenAI agents manifest is not valid YAML."]
    if not isinstance(parsed, dict):
        return ["OpenAI agents manifest must be a mapping."]
    interface = parsed.get("interface")
    if not isinstance(interface, dict):
        return ["OpenAI agents manifest interface section is missing."]
    missing_fields = [
        field
        for field in REQUIRED_OPENAI_MANIFEST_INTERFACE_FIELDS
        if not isinstance(interface.get(field), str) or not interface[field].strip()
    ]
    if missing_fields:
        return [
            "OpenAI agents manifest missing required interface fields: "
            + ", ".join(missing_fields)
        ]
    return []


def _frontmatter(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return {}
    if not lines or lines[0] != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            break
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip()] = value.strip().strip('"')
    return fields


def _relevant_agent_ids(
    active_agent_ids: list[str],
    messages: list[AgentMessage],
) -> set[str]:
    roster_ids = {agent.id for agent in AGENT_ROSTER}
    agent_ids = set(active_agent_ids)
    agent_ids.update(message.recipient_agent_id for message in messages)
    return {agent_id for agent_id in agent_ids if agent_id in roster_ids}


def _recommended_actions(
    *,
    entries: list[SkillUsageEntry],
    missing_skill_usage_message_ids: list[UUID],
    unprocessed_agent_ids: list[str],
    source_contract_issue_count: int,
) -> list[str]:
    actions: list[str] = []
    if source_contract_issue_count:
        actions.append(
            "Repair project skill source files or card mappings before relying on skill-guided workers."
        )
    if not entries:
        actions.append("Create or route A2A tasks before auditing skill usage.")
    if missing_skill_usage_message_ids:
        actions.append(
            "Re-run or inspect processed tasks missing skill_usage metadata before relying on their artifacts."
        )
    if unprocessed_agent_ids:
        actions.append(
            "Run workers for active agents without skill evidence: "
            + ", ".join(unprocessed_agent_ids[:8])
        )
    if not actions:
        actions.append(
            "Skill usage is auditable for the processed A2A tasks in this run."
        )
    return actions


def _summary(
    *,
    processed_task_count: int,
    invocation_count: int,
    missing_count: int,
    unprocessed_agent_count: int,
    source_contract_issue_count: int,
) -> str:
    return (
        f"Skill usage ledger covered {invocation_count}/{processed_task_count} "
        f"processed task(s), found {missing_count} missing skill evidence item(s), "
        f"{unprocessed_agent_count} active agent(s) without processed skill usage, "
        f"and {source_contract_issue_count} skill source contract issue(s)."
    )
