from all_about_llms.providers.interfaces import (
    GeneratedImage,
    ImageGenerationProvider,
    ProviderConfigurationError,
)


class ImagegenBoundaryProvider(ImageGenerationProvider):
    """Boundary object for the Codex imagegen skill.

    The app records image generation intent and provenance, but actual raster
    image generation is performed by Codex's imagegen capability outside the
    FastAPI process.
    """

    async def generate(self, prompt: str, metadata: dict) -> GeneratedImage:
        raise ProviderConfigurationError(
            "imagegen is a Codex tool boundary, not a FastAPI network provider."
        )
