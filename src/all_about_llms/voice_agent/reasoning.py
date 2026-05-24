from dataclasses import dataclass
from urllib.parse import urlparse

from all_about_llms.config import Settings
from all_about_llms.providers.factory import build_gemma_provider
from all_about_llms.voice_agent.adapters import HuggingFaceGemmaAudioReasoner
from all_about_llms.voice_agent.gemma import gemma_audio_endpoint_url
from all_about_llms.voice_agent.models import RealtimeVoiceAgentConfig


@dataclass(frozen=True, slots=True)
class VoiceReasoningRoute:
    provider: str
    endpoint_url: str | None
    token: str | None
    include_audio_attachments: bool
    required_env: list[str]
    configured_env: list[str]

    @property
    def ready(self) -> bool:
        return bool(self.endpoint_url and self.token and not self.missing_env)

    @property
    def missing_env(self) -> list[str]:
        return [
            env_name
            for env_name in self.required_env
            if env_name not in self.configured_env
        ]


def voice_reasoning_route(settings: Settings) -> VoiceReasoningRoute:
    openrouter_route = openrouter_voice_reasoning_route(settings)
    if openrouter_route.ready:
        return openrouter_route
    return gemma_native_audio_reasoning_route(settings)


def openrouter_voice_reasoning_route(settings: Settings) -> VoiceReasoningRoute:
    openrouter_endpoint = _openrouter_chat_endpoint_url(settings)
    configured_env: list[str] = []
    if settings.openrouter_api_key:
        configured_env.append("OPENROUTER_API_KEY")
    return VoiceReasoningRoute(
        provider="openrouter",
        endpoint_url=openrouter_endpoint,
        token=settings.openrouter_api_key,
        include_audio_attachments=False,
        required_env=["OPENROUTER_API_KEY"],
        configured_env=configured_env,
    )


def gemma_native_audio_reasoning_route(settings: Settings) -> VoiceReasoningRoute:
    gemma_endpoint = gemma_audio_endpoint_url(settings)
    configured_env: list[str] = []
    required_env = ["HF_TOKEN", "GEMMA4_MULTIMODAL_ENDPOINT_URL"]
    if settings.hf_token:
        configured_env.append("HF_TOKEN")
    if gemma_endpoint:
        configured_env.append("GEMMA4_MULTIMODAL_ENDPOINT_URL")
    return VoiceReasoningRoute(
        provider="gemma_native_audio",
        endpoint_url=gemma_endpoint,
        token=settings.hf_token,
        include_audio_attachments=True,
        required_env=required_env,
        configured_env=configured_env,
    )


def _openrouter_chat_endpoint_url(settings: Settings) -> str | None:
    endpoint = str(settings.openrouter_chat_completions_url or "").strip()
    if endpoint and _is_http_url(endpoint):
        return endpoint
    return None


def _is_http_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def build_voice_reasoner(
    settings: Settings,
    config: RealtimeVoiceAgentConfig,
    *,
    provider=None,
    route: VoiceReasoningRoute | None = None,
) -> HuggingFaceGemmaAudioReasoner:
    route = route or voice_reasoning_route(settings)
    return HuggingFaceGemmaAudioReasoner(
        provider=provider or build_gemma_provider(settings),
        config=config,
        endpoint_url=route.endpoint_url,
        token=route.token,
        include_audio_attachments=route.include_audio_attachments,
        provider_label=route.provider,
    )
