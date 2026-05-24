from datetime import datetime, timezone
from uuid import UUID

from all_about_llms.contracts import (
    ArtifactRecord,
    ArtifactType,
    MediaProductionRequest,
    MediaProductionResult,
    RunEvent,
)


class MediaProductionError(RuntimeError):
    """Base error for media production planning."""


class MediaProductionRunNotFoundError(MediaProductionError):
    """Raised when media production targets a missing run."""


class NoArtifactsForMediaProductionError(MediaProductionError):
    """Raised when there are no content artifacts to turn into media plans."""


SOURCE_CONTENT_TYPES = {
    ArtifactType.POST,
    ArtifactType.REEL_SCRIPT,
    ArtifactType.SUBSTACK_ARTICLE,
}


class MediaProductionWorkflow:
    """Create durable image, audio, and video planning artifacts from drafts."""

    def __init__(self, store):
        self._store = store

    async def run(
        self, run_id: UUID, request: MediaProductionRequest
    ) -> MediaProductionResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise MediaProductionRunNotFoundError(f"Run not found: {run_id}")

        artifacts = await self._select_source_artifacts(run_id, request)
        source_ids = _union_source_ids(artifacts)
        claim_ids = _union_claim_ids(artifacts)
        topic = _topic_from_artifacts(artifacts, run.goal)

        media_artifacts: list[ArtifactRecord] = []
        image_artifact_id = None
        audio_artifact_id = None
        video_artifact_id = None
        if request.include_image_prompt:
            image = _image_artifact(
                run_id=run_id,
                topic=topic,
                request=request,
                source_ids=source_ids,
                claim_ids=claim_ids,
                source_artifacts=artifacts,
            )
            media_artifacts.append(image)
            image_artifact_id = image.artifact_id
        if request.include_audio_brief:
            audio = _audio_artifact(
                run_id=run_id,
                topic=topic,
                request=request,
                source_ids=source_ids,
                claim_ids=claim_ids,
                source_artifacts=artifacts,
            )
            media_artifacts.append(audio)
            audio_artifact_id = audio.artifact_id
        if request.include_video_storyboard:
            video = _video_artifact(
                run_id=run_id,
                topic=topic,
                request=request,
                source_ids=source_ids,
                claim_ids=claim_ids,
                source_artifacts=artifacts,
            )
            media_artifacts.append(video)
            video_artifact_id = video.artifact_id

        for artifact in media_artifacts:
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
                event_type="media_production_plan_built",
                actor="video-reel-producer",
                payload={
                    "source_artifact_ids": [
                        str(artifact.artifact_id) for artifact in artifacts
                    ],
                    "media_artifact_ids": [
                        str(artifact.artifact_id) for artifact in media_artifacts
                    ],
                    "platform": request.platform,
                    "image_style": request.image_style,
                    "voice_style": request.voice_style,
                },
            )
        )
        return MediaProductionResult(
            run_id=run_id,
            source_artifact_ids=[artifact.artifact_id for artifact in artifacts],
            media_artifact_ids=[artifact.artifact_id for artifact in media_artifacts],
            image_artifact_id=image_artifact_id,
            audio_artifact_id=audio_artifact_id,
            video_artifact_id=video_artifact_id,
            event_id=event.event_id,
            summary=(
                f"Created {len(media_artifacts)} media planning artifact(s) "
                f"for {len(artifacts)} source artifact(s)."
            ),
        )

    async def _select_source_artifacts(
        self, run_id: UUID, request: MediaProductionRequest
    ) -> list[ArtifactRecord]:
        artifacts = [
            artifact
            for artifact in await self._store.list_artifacts(run_id)
            if artifact.artifact_type in SOURCE_CONTENT_TYPES
        ]
        if request.target_artifact_ids:
            targets = set(request.target_artifact_ids)
            artifacts = [
                artifact for artifact in artifacts if artifact.artifact_id in targets
            ]
        if not artifacts:
            raise NoArtifactsForMediaProductionError(
                "No post, reel, or Substack artifacts are available for media planning."
            )
        return artifacts


def _image_artifact(
    *,
    run_id: UUID,
    topic: str,
    request: MediaProductionRequest,
    source_ids: list[UUID],
    claim_ids: list[UUID],
    source_artifacts: list[ArtifactRecord],
) -> ArtifactRecord:
    return ArtifactRecord(
        run_id=run_id,
        artifact_type=ArtifactType.IMAGE,
        title=f"Imagegen prompt pack: {topic}",
        uri=f"artifact://runs/{run_id}/imagegen-prompt-pack",
        content={
            "format": "imagegen_prompt_pack",
            "primary_prompt": (
                f"Create a crisp educational social visual about {topic}. "
                f"Style: {request.image_style}. Show the real concept with clear "
                "visual hierarchy, source-backed labels, and no decorative clutter."
            ),
            "thumbnail_prompt": (
                f"Create a vertical reel thumbnail for {topic} with one clear "
                "ELI5 hook, high contrast, and readable mobile-safe text."
            ),
            "asset_requirements": [
                "Use as raster generation input only through the imagegen boundary.",
                "Keep all factual labels traceable to linked source and claim ids.",
                "Leave safe space for captions and platform UI overlays.",
            ],
        },
        provenance=_media_provenance(
            workflow="media_production_v1",
            agent_id="image-generation-agent",
            source_artifacts=source_artifacts,
            source_ids=source_ids,
            claim_ids=claim_ids,
            generation_mode="imagegen_prompt_only",
        ),
        source_ids=source_ids,
        reviewer_decisions=[
            _initial_media_reviewer_decision(
                reviewer_agent_id="visual-director",
                blocking_issue="requires_imagegen_boundary_review",
            )
        ],
        revision_history=[
            {
                "actor": "image-generation-agent",
                "note": "Created source-linked imagegen prompt pack for media planning.",
            }
        ],
    )


def _audio_artifact(
    *,
    run_id: UUID,
    topic: str,
    request: MediaProductionRequest,
    source_ids: list[UUID],
    claim_ids: list[UUID],
    source_artifacts: list[ArtifactRecord],
) -> ArtifactRecord:
    script = _best_reel_script(source_artifacts)
    return ArtifactRecord(
        run_id=run_id,
        artifact_type=ArtifactType.AUDIO,
        title=f"Audio brief: {topic}",
        uri=f"artifact://runs/{run_id}/audio-brief",
        content={
            "format": "audio_brief",
            "voice_style": request.voice_style,
            "provider_boundary": "OpenRouter deepseek/deepseek-v4-flash handles text-turn live dialogue reasoning, Kokoro handles TTS, and LiveKit handles realtime transport; raw microphone PCM is not sent to OpenRouter. Legacy native-Gemma/HF audio understanding is non-default context. Pipecat is optional for internal pipeline composition.",
            "voiceover_script": script,
            "pacing": "Short sentences, one idea per breath, pause before the key source-backed caveat.",
            "pronunciation_notes": [
                "Say OpenRouter as open router.",
                "Say pgvector as P-G vector.",
                "Use natural phrasing for A2A as agent-to-agent.",
            ],
            "qa_checks": [
                "No unsupported factual claims in spoken copy.",
                "Caveats remain audible, not hidden in captions.",
                "Voice can be interrupted and resumed cleanly.",
            ],
        },
        provenance=_media_provenance(
            workflow="media_production_v1",
            agent_id="audio-producer",
            source_artifacts=source_artifacts,
            source_ids=source_ids,
            claim_ids=claim_ids,
            generation_mode="audio_brief",
        ),
        source_ids=source_ids,
        reviewer_decisions=[
            _initial_media_reviewer_decision(
                reviewer_agent_id="audio-producer",
                blocking_issue="requires_audio_boundary_review",
            )
        ],
        revision_history=[
            {
                "actor": "audio-producer",
                "note": "Created source-linked realtime/TTS audio brief for media planning.",
            }
        ],
    )


def _video_artifact(
    *,
    run_id: UUID,
    topic: str,
    request: MediaProductionRequest,
    source_ids: list[UUID],
    claim_ids: list[UUID],
    source_artifacts: list[ArtifactRecord],
) -> ArtifactRecord:
    return ArtifactRecord(
        run_id=run_id,
        artifact_type=ArtifactType.VIDEO,
        title=f"Reel storyboard: {topic}",
        uri=f"artifact://runs/{run_id}/reel-storyboard",
        content={
            "format": "reel_storyboard",
            "platform": request.platform,
            "duration_seconds": 35,
            "scenes": [
                {
                    "time": "0-4s",
                    "visual": "Hook frame with one concrete question.",
                    "caption": "Why trust this AI draft?",
                },
                {
                    "time": "4-12s",
                    "visual": "Three-agent studio layout: writer, researcher, guardrails.",
                    "caption": "One writes, one checks, one blocks weak claims.",
                },
                {
                    "time": "12-24s",
                    "visual": "Source ledger and claim links animate into the draft.",
                    "caption": "Every big claim needs a source trail.",
                },
                {
                    "time": "24-35s",
                    "visual": "Publish gate turns from needs review to ready after fixes.",
                    "caption": "Drafts publish only after review.",
                },
            ],
            "subtitle_rules": [
                "Maximum two lines per frame.",
                "Keep ELI5 language in subtitles.",
                "Do not hide caveats or source uncertainty.",
            ],
            "asset_dependencies": [
                "imagegen prompt pack",
                "audio brief",
                "source ledger snapshot",
            ],
        },
        provenance=_media_provenance(
            workflow="media_production_v1",
            agent_id="video-reel-producer",
            source_artifacts=source_artifacts,
            source_ids=source_ids,
            claim_ids=claim_ids,
            generation_mode="storyboard_plan",
        ),
        source_ids=source_ids,
        reviewer_decisions=[
            _initial_media_reviewer_decision(
                reviewer_agent_id="video-reel-producer",
                blocking_issue="requires_reel_storyboard_review",
            )
        ],
        revision_history=[
            {
                "actor": "video-reel-producer",
                "note": "Created source-linked reel storyboard for media planning.",
            }
        ],
    )


def _media_provenance(
    *,
    workflow: str,
    agent_id: str,
    source_artifacts: list[ArtifactRecord],
    source_ids: list[UUID],
    claim_ids: list[UUID],
    generation_mode: str,
) -> dict:
    return {
        "workflow": workflow,
        "agent_id": agent_id,
        "source_artifact_ids": [
            str(artifact.artifact_id) for artifact in source_artifacts
        ],
        "source_ids": [str(source_id) for source_id in source_ids],
        "claim_ids": [str(claim_id) for claim_id in claim_ids],
        "generation_mode": generation_mode,
    }


def _initial_media_reviewer_decision(
    *, reviewer_agent_id: str, blocking_issue: str
) -> dict[str, object]:
    return {
        "reviewer_agent_id": reviewer_agent_id,
        "status": "needs_revision",
        "notes": "Media plan requires guardrail review and human approval before use.",
        "blocking_issues": [blocking_issue],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _topic_from_artifacts(artifacts: list[ArtifactRecord], fallback: str) -> str:
    for artifact in artifacts:
        topic = artifact.content.get("topic")
        if isinstance(topic, str) and topic.strip():
            return topic.strip()
    return fallback.replace("Create source-backed content about ", "").strip()


def _best_reel_script(artifacts: list[ArtifactRecord]) -> str:
    for artifact in artifacts:
        if artifact.artifact_type == ArtifactType.REEL_SCRIPT:
            script = artifact.content.get("script")
            if isinstance(script, list):
                return " ".join(str(line) for line in script)
            hook = artifact.content.get("hook")
            body = artifact.content.get("body")
            if hook or body:
                return " ".join(str(part) for part in [hook, body] if part)
    return "Explain the idea in ELI5 language, cite the source trail, and end with a review-before-publish call to action."


def _union_source_ids(artifacts: list[ArtifactRecord]) -> list[UUID]:
    source_ids = []
    for artifact in artifacts:
        for source_id in artifact.source_ids:
            if source_id not in source_ids:
                source_ids.append(source_id)
    return source_ids


def _union_claim_ids(artifacts: list[ArtifactRecord]) -> list[UUID]:
    claim_ids = []
    for artifact in artifacts:
        for raw_claim_id in [
            *artifact.provenance.get("claim_ids", []),
            *artifact.content.get("claim_ids", []),
        ]:
            try:
                claim_id = UUID(str(raw_claim_id))
            except (TypeError, ValueError):
                continue
            if claim_id not in claim_ids:
                claim_ids.append(claim_id)
    return claim_ids
