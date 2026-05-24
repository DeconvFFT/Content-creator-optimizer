from dataclasses import dataclass

from all_about_llms.providers.interfaces import (
    GemmaExpertProvider,
    RerankerProvider,
    WebSearchProvider,
)


@dataclass(frozen=True)
class ContentWorkflowServices:
    search_provider: WebSearchProvider | None = None
    gemma_provider: GemmaExpertProvider | None = None
    reranker_provider: RerankerProvider | None = None
