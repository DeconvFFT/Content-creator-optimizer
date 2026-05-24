from collections import Counter, defaultdict
from uuid import UUID

from all_about_llms.contracts import (
    AgentMessage,
    ArtifactRecord,
    ArtifactType,
    MultimodalAssetEntry,
    MultimodalAssetInput,
    MultimodalIntakeRequest,
    MultimodalIntakeResult,
    RunEvent,
)
from all_about_llms.orchestration.a2a_projection import (
    public_a2a_message_event_payload,
)


class MultimodalIntakeError(RuntimeError):
    """Base error for multimodal intake ledger generation."""


class MultimodalIntakeRunNotFoundError(MultimodalIntakeError):
    """Raised when a run cannot be found for multimodal intake work."""


class MultimodalIntakeWorkflow:
    """Record multimodal user assets and route them to specialist agents."""

    def __init__(self, store):
        self._store = store

    async def record(
        self, run_id: UUID, request: MultimodalIntakeRequest
    ) -> MultimodalIntakeResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise MultimodalIntakeRunNotFoundError(f"Run not found: {run_id}")

        assets = [_asset_entry(asset) for asset in request.assets]
        modality_counts = Counter(asset.modality for asset in assets)
        recommended_agent_ids = _unique(
            agent_id
            for asset in assets
            for agent_id in asset.recommended_agent_ids
        )
        task_message_ids: list[UUID] = []

        if request.create_agent_tasks:
            grouped_assets: dict[str, list[MultimodalAssetEntry]] = defaultdict(list)
            for asset in assets:
                for agent_id in asset.recommended_agent_ids:
                    grouped_assets[agent_id].append(asset)
            for agent_id in recommended_agent_ids:
                message = AgentMessage(
                    run_id=run_id,
                    sender_agent_id="realtime-conversation-host",
                    recipient_agent_id=agent_id,
                    task_type="review_multimodal_intake",
                    payload={
                        "workflow": "multimodal_intake_v1",
                        "run_goal": run.goal,
                        "notes": request.notes,
                        "assets": [
                            asset.model_dump(mode="json")
                            for asset in grouped_assets[agent_id]
                        ],
                        "all_asset_ids": [str(asset.asset_id) for asset in assets],
                        "modality_counts": dict(modality_counts),
                        "provider_boundaries": _provider_boundaries(),
                    },
                    requires_human_feedback=request.require_human_feedback,
                )
                await self._store.record_agent_message(message)
                await self._store.append_event(
                    RunEvent(
                        run_id=run_id,
                        event_type="agent_message_accepted",
                        actor="realtime-conversation-host",
                        payload=public_a2a_message_event_payload(message),
                    )
                )
                task_message_ids.append(message.message_id)

        result = MultimodalIntakeResult(
            run_id=run_id,
            asset_count=len(assets),
            modality_counts=dict(modality_counts),
            recommended_agent_ids=recommended_agent_ids,
            task_message_ids=task_message_ids,
            assets=assets,
            summary=_summary(
                asset_count=len(assets),
                modalities=list(modality_counts.keys()),
                agent_count=len(recommended_agent_ids),
                task_count=len(task_message_ids),
            ),
        )

        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.MULTIMODAL_INTAKE_LEDGER,
                title="Multimodal intake ledger",
                uri=f"artifact://runs/{run_id}/multimodal-intake-ledger",
                content={},
                provenance={
                    "workflow": "multimodal_intake_v1",
                    "agent_id": "realtime-conversation-host",
                    "asset_count": len(assets),
                    "create_agent_tasks": request.create_agent_tasks,
                    "require_human_feedback": request.require_human_feedback,
                },
                revision_history=[
                    {
                        "actor": "realtime-conversation-host",
                        "note": (
                            "Recorded user-provided multimodal inputs with "
                            "specialist routing and provider boundaries."
                        ),
                    }
                ],
            )
            result.intake_artifact_id = artifact.artifact_id
            artifact.content = result.model_dump(mode="json", exclude={"event_id"})
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
                event_type="multimodal_intake_recorded",
                actor="realtime-conversation-host",
                payload={
                    "asset_count": result.asset_count,
                    "modality_counts": result.modality_counts,
                    "recommended_agent_ids": result.recommended_agent_ids,
                    "task_message_ids": [
                        str(message_id) for message_id in result.task_message_ids
                    ],
                    "intake_artifact_id": (
                        str(result.intake_artifact_id)
                        if result.intake_artifact_id
                        else None
                    ),
                },
            )
        )
        result.event_id = event.event_id
        return result


def _asset_entry(asset: MultimodalAssetInput) -> MultimodalAssetEntry:
    modality = _normalize_modality(asset.modality)
    return MultimodalAssetEntry(
        asset_uri=asset.asset_uri,
        modality=modality,
        source=asset.source,
        description=asset.description,
        recommended_agent_ids=_recommended_agents(modality),
        analysis_boundary=_analysis_boundary(modality),
        generation_boundary=_generation_boundary(modality),
        requires_transcription=modality in {"audio", "voice"},
        requires_visual_analysis=modality in {
            "image",
            "screenshot",
            "screen",
            "video",
            "reel",
        },
        metadata=asset.metadata,
    )


def _normalize_modality(modality: str) -> str:
    normalized = modality.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "photo": "image",
        "picture": "image",
        "diagram": "image",
        "chart": "image",
        "screen_capture": "screenshot",
        "screen_recording": "screen",
        "voice_note": "voice",
        "speech": "voice",
        "reels": "reel",
        "movie": "video",
        "pdf": "document",
        "doc": "document",
        "article": "document",
    }
    return aliases.get(normalized, normalized or "unknown")


def _recommended_agents(modality: str) -> list[str]:
    routing = {
        "image": ["visual-director"],
        "screenshot": ["lead-ui-ux-designer", "visual-director"],
        "screen": [
            "lead-ui-ux-designer",
            "interactive-systems-designer",
            "visual-director",
        ],
        "audio": ["audio-producer", "realtime-conversation-host"],
        "voice": ["audio-producer", "realtime-conversation-host"],
        "video": ["video-reel-producer", "visual-director"],
        "reel": ["video-reel-producer", "visual-director"],
        "document": ["context-engineering-agent", "content-strategist"],
        "text": ["intent-router", "context-engineering-agent"],
    }
    return routing.get(modality, ["context-engineering-agent"])


def _analysis_boundary(modality: str) -> str:
    if modality in {"image", "screenshot", "screen"}:
        return (
            "Gemma 4 multimodal HF endpoints analyze images, screenshots, UI "
            "state, diagrams, and visual references; imagegen is not used for "
            "input analysis."
        )
    if modality in {"video", "reel"}:
        return (
            "Video/Reel Producer and Gemma 4 multimodal frame analysis inspect "
            "reference footage, scenes, captions, and storyboard implications."
        )
    if modality in {"audio", "voice"}:
        return (
            "Realtime audio or transcription providers handle speech capture; "
            "Audio Producer turns transcripts and timing notes into content "
            "decisions."
        )
    if modality == "document":
        return (
            "Context Engineering Agent parses the document reference into durable "
            "context before content or research agents rely on it."
        )
    return (
        "Context Engineering Agent classifies the asset before specialist "
        "analysis or content synthesis."
    )


def _generation_boundary(modality: str) -> str:
    if modality in {"image", "screenshot", "screen"}:
        return (
            "Raster generation or editing may use imagegen later, but only after "
            "a reviewed prompt pack and artifact provenance exist."
        )
    if modality in {"audio", "voice"}:
        return (
            "Spoken output and narration use realtime/TTS providers; Gemma 4 "
            "does not own live voice transport."
        )
    if modality in {"video", "reel"}:
        return (
            "Video output starts as storyboard, subtitles, shot list, and media "
            "asset requirements; still-image generation remains imagegen-bound."
        )
    return (
        "Generated text, plans, and content artifacts must store prompt input, "
        "model/provider, source dependencies, and review decisions."
    )


def _provider_boundaries() -> dict[str, str]:
    return {
        "gemma4_hf": (
            "Expert reasoning, vision, multimodal critique, and long-context "
            "synthesis for specialist agents."
        ),
        "realtime_audio": (
            "Natural speech transport, interruptions, transcription, TTS, and "
            "spoken output."
        ),
        "imagegen": (
            "Raster visual generation or editing only; not hidden input analysis."
        ),
        "web_search": (
            "Required for fresh source-backed factual claims before publishing."
        ),
    }


def _unique(values) -> list[str]:
    unique_values = []
    for value in values:
        if value not in unique_values:
            unique_values.append(value)
    return unique_values


def _summary(
    *, asset_count: int, modalities: list[str], agent_count: int, task_count: int
) -> str:
    modality_text = ", ".join(modalities) if modalities else "no modalities"
    return (
        f"Multimodal intake recorded {asset_count} asset(s) across "
        f"{modality_text}, routed to {agent_count} specialist agent(s), and "
        f"created {task_count} A2A task(s)."
    )
