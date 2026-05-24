from collections import Counter
from uuid import UUID

from all_about_llms.contracts import (
    ArtifactRecord,
    ArtifactType,
    RunEvent,
    RunReplayEventEntry,
    RunReplayLedgerRequest,
    RunReplayLedgerResult,
    RunReplayStateDelta,
)


class RunReplayLedgerError(RuntimeError):
    """Base error for run replay ledger generation."""


class RunReplayLedgerRunNotFoundError(RunReplayLedgerError):
    """Raised when a run cannot be found for replay work."""


class RunReplayLedgerCheckpointNotFoundError(RunReplayLedgerError):
    """Raised when a requested checkpoint cannot be found."""


class RunReplayLedgerWorkflow:
    """Build a checkpoint-to-event replay ledger for long-running debug context."""

    def __init__(self, store):
        self._store = store

    async def build(
        self, run_id: UUID, request: RunReplayLedgerRequest
    ) -> RunReplayLedgerResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise RunReplayLedgerRunNotFoundError(f"Run not found: {run_id}")

        checkpoint = await self._select_checkpoint(run_id, request.checkpoint_id)
        replay_after_event_id = request.after_event_id
        if replay_after_event_id is None and checkpoint is not None:
            replay_after_event_id = checkpoint.event_cursor

        events = await self._store.list_events(
            run_id,
            limit=request.event_limit,
            after_event_id=replay_after_event_id,
        )
        latest_event_id = max(
            (event.event_id for event in events if event.event_id is not None),
            default=replay_after_event_id,
        )
        current_digest = await self._current_digest(run_id)
        checkpoint_digest = checkpoint.state_digest if checkpoint else {}
        state_deltas = _state_deltas(checkpoint_digest, current_digest)
        event_type_counts = Counter(event.event_type for event in events)
        actor_counts = Counter(event.actor for event in events)
        event_entries = [
            _event_entry(event, include_payload=request.include_event_payloads)
            for event in events
            if event.event_id is not None
        ]
        result = RunReplayLedgerResult(
            run_id=run_id,
            checkpoint_id=checkpoint.checkpoint_id if checkpoint else None,
            replay_after_event_id=replay_after_event_id,
            latest_event_id=latest_event_id,
            replay_event_count=len(event_entries),
            event_type_counts=dict(event_type_counts),
            actor_counts=dict(actor_counts),
            state_deltas=state_deltas,
            events=event_entries,
            summary=(
                f"Replay ledger captured {len(event_entries)} event(s) after "
                f"event {replay_after_event_id or 0}."
            ),
        )

        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.RUN_REPLAY_LEDGER,
                title="Run replay ledger",
                uri=f"artifact://runs/{run_id}/run-replay-ledger",
                content=result.model_dump(
                    mode="json", exclude={"replay_artifact_id", "event_id"}
                ),
                provenance={
                    "workflow": "run_replay_ledger_v1",
                    "agent_id": "agent-harness-engineer",
                    "checkpoint_id": (
                        str(checkpoint.checkpoint_id) if checkpoint else None
                    ),
                    "replay_after_event_id": replay_after_event_id,
                    "event_limit": request.event_limit,
                    "include_event_payloads": request.include_event_payloads,
                },
                revision_history=[
                    {
                        "actor": "agent-harness-engineer",
                        "note": "Recorded checkpoint-to-event replay context for long-running debug and resume work.",
                    }
                ],
            )
            result.replay_artifact_id = artifact.artifact_id
            artifact.content["replay_artifact_id"] = str(artifact.artifact_id)
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
                event_type="run_replay_ledger_built",
                actor="agent-harness-engineer",
                payload={
                    "checkpoint_id": (
                        str(result.checkpoint_id) if result.checkpoint_id else None
                    ),
                    "replay_after_event_id": result.replay_after_event_id,
                    "latest_event_id": result.latest_event_id,
                    "replay_event_count": result.replay_event_count,
                    "replay_artifact_id": (
                        str(result.replay_artifact_id)
                        if result.replay_artifact_id
                        else None
                    ),
                },
            )
        )
        result.event_id = event.event_id
        return result

    async def _select_checkpoint(self, run_id: UUID, checkpoint_id: UUID | None):
        checkpoints = await self._store.list_run_checkpoints(run_id, limit=100)
        if checkpoint_id is None:
            return checkpoints[0] if checkpoints else None
        for checkpoint in checkpoints:
            if checkpoint.checkpoint_id == checkpoint_id:
                return checkpoint
        raise RunReplayLedgerCheckpointNotFoundError(
            f"Checkpoint not found: {checkpoint_id}"
        )

    async def _current_digest(self, run_id: UUID) -> dict[str, int | str | None]:
        events = await self._store.list_events(run_id, limit=10000)
        messages = await self._store.list_agent_messages(run_id)
        sources = await self._store.list_sources(run_id)
        claims = await self._store.list_claims(run_id)
        artifacts = await self._store.list_artifacts(run_id)
        audits = await self._store.list_guardrail_audits(run_id)
        feedback_items = await self._store.list_feedback(run_id)
        worker_profiles = await self._store.list_worker_profiles(run_id)
        latest_event_id = max(
            (event.event_id for event in events if event.event_id is not None),
            default=None,
        )
        return {
            "latest_event_id": latest_event_id,
            "events": len(events),
            "agent_messages": len(messages),
            "sources": len(sources),
            "claims": len(claims),
            "artifacts": len(artifacts),
            "guardrail_audits": len(audits),
            "feedback_items": len(feedback_items),
            "worker_profiles": len(worker_profiles),
        }


def _event_entry(event: RunEvent, *, include_payload: bool) -> RunReplayEventEntry:
    payload = event.payload if include_payload else _payload_preview(event.payload)
    return RunReplayEventEntry(
        event_id=event.event_id or 0,
        event_type=event.event_type,
        actor=event.actor,
        created_at=event.created_at,
        payload_preview=payload,
    )


def _payload_preview(payload: dict) -> dict:
    preview = {}
    for key, value in (payload or {}).items():
        if len(preview) >= 8:
            break
        if isinstance(value, (str, int, float, bool)) or value is None:
            preview[key] = value
        elif isinstance(value, list):
            preview[key] = f"list[{len(value)}]"
        elif isinstance(value, dict):
            preview[key] = f"dict[{len(value)}]"
        else:
            preview[key] = type(value).__name__
    return preview


def _state_deltas(
    checkpoint_digest: dict, current_digest: dict
) -> list[RunReplayStateDelta]:
    keys = [
        "events",
        "agent_messages",
        "sources",
        "claims",
        "artifacts",
        "guardrail_audits",
        "feedback_items",
        "worker_profiles",
    ]
    deltas = []
    for key in keys:
        checkpoint_value = _int_or_none(checkpoint_digest.get(key))
        current_value = _int_or_none(current_digest.get(key))
        delta = (
            current_value - checkpoint_value
            if checkpoint_value is not None and current_value is not None
            else None
        )
        deltas.append(
            RunReplayStateDelta(
                key=key,
                checkpoint_value=checkpoint_value,
                current_value=current_value,
                delta=delta,
            )
        )
    return deltas


def _int_or_none(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
