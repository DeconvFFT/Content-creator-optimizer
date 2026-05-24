from urllib.parse import urlparse

from all_about_llms.config import Settings


def gemma_audio_endpoint_url(settings: Settings) -> str | None:
    """Return the dedicated Gemma native-audio endpoint, if configured."""

    endpoint = _non_empty_string(settings.gemma4_multimodal_endpoint_url)
    if endpoint and _is_http_url(endpoint):
        return endpoint
    return None


def gemma_audio_endpoint_metadata(settings: Settings) -> dict[str, object]:
    raw_audio_endpoint = _non_empty_string(settings.gemma4_multimodal_endpoint_url)
    audio_endpoint = gemma_audio_endpoint_url(settings)
    primary_endpoint = _non_empty_string(settings.gemma4_primary_endpoint_url)
    router_chat_configured = bool(
        settings.hf_inference_router_enabled
        and _is_http_url(settings.hf_inference_router_chat_completions_url)
    )
    endpoint_error = (
        "invalid_url" if raw_audio_endpoint and not audio_endpoint else None
    )
    return {
        "has_endpoint": bool(audio_endpoint),
        "gemma_endpoint_configured": bool(audio_endpoint),
        "gemma_audio_endpoint_configured": bool(audio_endpoint),
        "gemma_multimodal_endpoint_configured": bool(raw_audio_endpoint),
        "gemma_audio_endpoint_error": endpoint_error,
        "gemma_primary_endpoint_configured": bool(primary_endpoint),
        "gemma_primary_endpoint_usable_for_audio": False,
        "hf_router_chat_completions_configured": router_chat_configured,
        "hf_router_chat_only": router_chat_configured,
        "requires_dedicated_audio_endpoint": True,
        "required_audio_endpoint_env": "GEMMA4_MULTIMODAL_ENDPOINT_URL",
        "text_endpoint_env": "GEMMA4_PRIMARY_ENDPOINT_URL",
    }


def _non_empty_string(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def _is_http_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
