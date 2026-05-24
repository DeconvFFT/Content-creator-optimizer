from all_about_llms.config import Settings
from all_about_llms.providers.huggingface import HuggingFaceGemmaProvider
from all_about_llms.providers.imagegen_boundary import ImagegenBoundaryProvider
from all_about_llms.providers.realtime import (
    CartesiaRealtimeTTSProvider,
    ElevenLabsRealtimeProvider,
    Gemma4RealtimeVoiceProvider,
    OpenAIRealtimeProvider,
    OpenSourceRealtimeVoiceProvider,
)
from all_about_llms.providers.rerank import (
    DeterministicRerankerProvider,
    RustRetrievalRankerProvider,
)
from all_about_llms.providers.search import SerpApiSearchProvider, TavilySearchProvider


def build_gemma_provider(settings: Settings) -> HuggingFaceGemmaProvider:
    return HuggingFaceGemmaProvider(
        token=settings.hf_token,
        default_endpoint_url=settings.gemma_chat_endpoint_url(
            settings.gemma4_primary_endpoint_url
        ),
    )


def build_realtime_provider(settings: Settings, provider: str | None = None):
    selected = provider or settings.realtime_default_provider
    if selected in {"openrouter_livekit", "openrouter-livekit", "gemma4_realtime"}:
        return Gemma4RealtimeVoiceProvider(
            provider_name="openrouter_livekit",
            transport_framework=settings.gemma4_realtime_transport_framework,
            livekit_url=settings.realtime_livekit_url(),
            livekit_api_key=settings.livekit_api_key,
            livekit_api_secret=settings.livekit_api_secret,
            livekit_token_ttl_seconds=(
                settings.gemma4_realtime_livekit_token_ttl_seconds
            ),
            websocket_url=settings.gemma4_realtime_ws_url,
            audio_input_model=settings.gemma4_realtime_audio_input_model,
            reasoning_model=settings.gemma4_realtime_reasoning_model,
            audio_output_model=settings.gemma4_realtime_audio_output_model,
            audio_format=settings.gemma4_realtime_audio_format,
            sample_rate=settings.gemma4_realtime_sample_rate,
            context_prune_after_turns=(
                settings.gemma4_realtime_context_prune_after_turns
            ),
            max_audio_seconds_per_turn=(
                settings.gemma4_realtime_max_audio_seconds_per_turn
            ),
            rust_vad_model=settings.gemma4_realtime_rust_vad_model,
            rust_vad_backend=settings.rust_voice_edge_vad_backend,
            rust_vad_fallback_allowed=settings.rust_voice_edge_allow_vad_fallback,
            gemma_streaming_enabled=settings.gemma4_realtime_stream_gemma,
        )
    if selected == "open_source_realtime":
        return OpenSourceRealtimeVoiceProvider(
            websocket_url=settings.open_source_realtime_ws_url,
            stt_model=settings.open_source_realtime_stt_model,
            llm_model=settings.open_source_realtime_llm_model,
            tts_model=settings.open_source_realtime_tts_model,
            audio_format=settings.open_source_realtime_audio_format,
            sample_rate=settings.open_source_realtime_sample_rate,
        )
    if selected == "openai_realtime":
        return OpenAIRealtimeProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_realtime_model,
        )
    if selected == "elevenlabs":
        return ElevenLabsRealtimeProvider(
            api_key=settings.elevenlabs_api_key,
            agent_id=settings.elevenlabs_agent_id,
        )
    if selected == "cartesia":
        return CartesiaRealtimeTTSProvider(
            api_key=settings.cartesia_api_key,
            model_id=settings.cartesia_model_id,
            voice_id=settings.cartesia_voice_id,
        )
    raise ValueError(f"Unknown realtime provider: {selected}")


def build_search_provider(settings: Settings):
    if settings.web_search_provider == "tavily":
        return TavilySearchProvider(api_key=settings.tavily_api_key)
    if settings.web_search_provider == "serpapi":
        return SerpApiSearchProvider(api_key=settings.serpapi_api_key)
    raise ValueError(f"Unknown web search provider: {settings.web_search_provider}")


def build_reranker_provider(settings: Settings):
    if settings.reranker_provider == "deterministic":
        return DeterministicRerankerProvider()
    if settings.reranker_provider == "rust":
        return RustRetrievalRankerProvider(
            binary_path=settings.rust_reranker_binary_path,
            timeout_seconds=settings.rust_reranker_timeout_seconds,
        )
    raise ValueError(f"Unknown reranker provider: {settings.reranker_provider}")


def build_image_generation_provider() -> ImagegenBoundaryProvider:
    return ImagegenBoundaryProvider()
