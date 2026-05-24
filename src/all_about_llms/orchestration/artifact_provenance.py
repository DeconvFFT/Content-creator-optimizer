from all_about_llms.contracts import ArtifactRecord, ArtifactType


GEMMA_EXPERT_CONTENT_TYPES = {
    ArtifactType.POST,
    ArtifactType.REEL_SCRIPT,
    ArtifactType.SUBSTACK_ARTICLE,
    ArtifactType.SOCIAL_PACKAGE,
}


def artifact_provenance_issues(artifact: ArtifactRecord) -> list[str]:
    """Return review issues for missing generated-artifact provenance."""

    issues: list[str] = []
    provenance = artifact.provenance or {}
    content = artifact.content or {}
    if not artifact.revision_history:
        issues.append("missing_artifact_revision_history")
    if not artifact.reviewer_decisions:
        issues.append("missing_artifact_reviewer_decisions")
    if not _has_generation_provenance(provenance):
        issues.append("missing_artifact_generation_provenance")
    if not _has_input_context(provenance, content):
        issues.append("missing_artifact_prompt_or_input_context")
    return issues


def artifact_expert_model_issues(artifact: ArtifactRecord) -> list[str]:
    """Return issues for publishable writing that did not use Gemma 4 on HF."""

    if artifact.artifact_type not in GEMMA_EXPERT_CONTENT_TYPES:
        return []
    provenance = artifact.provenance or {}
    model_provider = str(provenance.get("model_provider") or "").lower()
    model_id = str(provenance.get("model_id") or "").lower()
    generation_mode = str(provenance.get("generation_mode") or "").lower()
    if (
        "deterministic" in model_provider
        or "deterministic" in model_id
        or "deterministic" in generation_mode
    ):
        return ["deterministic_fallback_content_not_publishable"]
    if model_provider or model_id:
        if model_provider != "huggingface" or "gemma-4" not in model_id:
            return ["publishable_content_requires_gemma4_hf_provenance"]
    return []


def _has_generation_provenance(provenance: dict) -> bool:
    return bool(
        provenance.get("model_provider")
        or provenance.get("model_id")
        or provenance.get("tool_boundary")
        or provenance.get("generation_mode")
        or provenance.get("workflow")
    )


def _has_input_context(provenance: dict, content: dict) -> bool:
    return bool(
        provenance.get("prompt_input")
        or provenance.get("source_artifact_ids")
        or provenance.get("source_ids")
        or provenance.get("source_citation_ids")
        or content.get("prompt_input")
        or content.get("source_dependencies")
        or content.get("source_artifact_ids")
        or content.get("source_citations")
    )
