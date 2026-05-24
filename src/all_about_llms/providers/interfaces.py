from typing import Any, Protocol

from pydantic import BaseModel, Field, HttpUrl


class RealtimeSessionRequest(BaseModel):
    provider: str
    run_id: str
    voice: str | None = None
    instructions: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RealtimeSessionResponse(BaseModel):
    provider: str
    session_id: str
    client_secret: str | None = None
    websocket_url: str | None = None
    transport: dict[str, Any] | None = None
    expires_at_unix: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GemmaRequest(BaseModel):
    model_id: str
    agent_id: str
    system_context: str
    user_input: str
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    response_format: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GemmaResponse(BaseModel):
    model_id: str
    agent_id: str
    content: str
    raw_response: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str
    freshness: str = "current"
    max_results: int = 10
    required_domains: list[str] = Field(default_factory=list)
    blocked_domains: list[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    title: str
    url: HttpUrl
    snippet: str
    publisher: str | None = None
    published_at: str | None = None
    retrieved_at: str


class RerankCandidate(BaseModel):
    candidate_id: str
    title: str
    url: str | None = None
    snippet: str | None = None
    query: str | None = None
    retrievers: list[str] = Field(default_factory=list)
    rank: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class RerankRequest(BaseModel):
    query: str
    candidates: list[RerankCandidate]
    top_k: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RerankResult(BaseModel):
    candidate_id: str
    rank_before: int
    rank_after: int
    relevance_score: float = Field(ge=0.0, le=1.0)
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GeneratedImage(BaseModel):
    artifact_uri: str
    prompt: str
    provider: str = "imagegen"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderConfigurationError(RuntimeError):
    """Raised when a provider is selected without required local configuration."""


class RealtimeAudioProvider(Protocol):
    async def create_session(
        self, request: RealtimeSessionRequest
    ) -> RealtimeSessionResponse:
        """Create a full speech-to-speech conversation session."""


class GemmaExpertProvider(Protocol):
    async def complete(self, request: GemmaRequest) -> GemmaResponse:
        """Run a Gemma 4 expert-agent request through a Hugging Face endpoint."""


class WebSearchProvider(Protocol):
    async def search(self, request: SearchRequest) -> list[SearchResult]:
        """Return source candidates for source-backed content generation."""


class RerankerProvider(Protocol):
    async def rerank(self, request: RerankRequest) -> list[RerankResult]:
        """Rerank fused retrieval candidates before context assembly."""


class ImageGenerationProvider(Protocol):
    async def generate(self, prompt: str, metadata: dict[str, Any]) -> GeneratedImage:
        """Generate or edit raster visuals through the imagegen boundary."""
