from pydantic import BaseModel


class ModelRoute(BaseModel):
    task: str
    primary_model: str
    fallback_model: str | None = None
    rationale: str
    provider_boundary: str


MODEL_ROUTES: tuple[ModelRoute, ...] = (
    ModelRoute(
        task="live_conversation",
        primary_model="OpenRouter deepseek/deepseek-v4-flash plus hexgrad/Kokoro-82M over LiveKit",
        fallback_model="text chat plus open-source TTS/STT adapters or explicitly selected paid voice provider",
        rationale="Natural dialogue requires interruption handling, voice activity detection, context pruning, and low-latency spoken output.",
        provider_boundary="LiveKit handles realtime voice transport, Rust handles VAD/barge-in buffers, OpenRouter handles text-turn live dialogue reasoning through deepseek/deepseek-v4-flash without raw microphone PCM, and Kokoro handles speech output. Pipecat is optional for internal pipeline composition; native Gemma/HF audio is legacy/non-default context.",
    ),
    ModelRoute(
        task="deep_reasoning_and_planning",
        primary_model="OpenRouter deepseek/deepseek-v4-flash",
        fallback_model="OpenRouter alternate reasoning model",
        rationale="Deep content planning, critique, synthesis, and architecture review should use the approved OpenRouter reasoning route by default.",
        provider_boundary="OpenRouter cloud endpoint with no Hugging Face/Gemma default.",
    ),
    ModelRoute(
        task="fast_routing_and_triage",
        primary_model="OpenRouter deepseek/deepseek-v4-flash",
        fallback_model="OpenRouter alternate small/fast model",
        rationale="Routing and short decisions should stay on the approved OpenRouter provider path unless a later decision changes it.",
        provider_boundary="OpenRouter cloud endpoint with no Hugging Face/Gemma default.",
    ),
    ModelRoute(
        task="vision_and_multimodal_review",
        primary_model="OpenRouter selected multimodal-capable model",
        fallback_model="human/manual visual review",
        rationale="Screenshots, charts, UI states, and visual evidence should use an approved OpenRouter-compatible visual route or explicit manual review, not a Hugging Face/Gemma default.",
        provider_boundary="OpenRouter or manual visual-review boundary; legacy Gemma/HF multimodal routes are non-default.",
    ),
    ModelRoute(
        task="raster_visual_generation",
        primary_model="codex imagegen skill",
        fallback_model=None,
        rationale="Raster assets are generated through the project imagegen capability, not through the product text agents.",
        provider_boundary="Image generation is a tool boundary with provenance recorded in artifacts.",
    ),
)


def list_model_routes() -> tuple[ModelRoute, ...]:
    return MODEL_ROUTES
