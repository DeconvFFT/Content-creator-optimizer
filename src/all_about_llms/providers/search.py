from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import ValidationError

from all_about_llms.providers.interfaces import (
    ProviderConfigurationError,
    SearchRequest,
    SearchResult,
)


class TavilySearchProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str = "https://api.tavily.com/search",
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._api_key = api_key
        self._base_url = base_url
        self._transport = transport

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        if not self._api_key:
            raise ProviderConfigurationError("TAVILY_API_KEY is not configured.")

        payload = {
            "query": request.query,
            "max_results": request.max_results,
            "include_answer": False,
            "include_raw_content": False,
            "include_domains": request.required_domains,
            "exclude_domains": request.blocked_domains,
        }
        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    self._base_url,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderConfigurationError(
                f"Tavily search failed with HTTP {exc.response.status_code}."
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderConfigurationError(
                f"Tavily search request failed: {type(exc).__name__}."
            ) from exc
        try:
            raw = response.json()
        except ValueError as exc:
            raise ProviderConfigurationError(
                "Tavily search returned invalid JSON."
            ) from exc
        if not isinstance(raw, dict):
            raise ProviderConfigurationError(
                "Tavily search returned non-object JSON."
            )
        results = raw.get("results", [])
        if not isinstance(results, list):
            raise ProviderConfigurationError(
                "Tavily search returned invalid results JSON."
            )

        return _parse_result_items("Tavily", results)


class SerpApiSearchProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str = "https://serpapi.com/search.json",
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._api_key = api_key
        self._base_url = base_url
        self._transport = transport

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        if not self._api_key:
            raise ProviderConfigurationError("SERPAPI_API_KEY is not configured.")

        params = {
            "engine": "google",
            "q": request.query,
            "api_key": self._api_key,
            "num": request.max_results,
        }
        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                transport=self._transport,
            ) as client:
                response = await client.get(self._base_url, params=params)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderConfigurationError(
                f"SerpAPI search failed with HTTP {exc.response.status_code}."
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderConfigurationError(
                f"SerpAPI search request failed: {type(exc).__name__}."
            ) from exc
        try:
            raw = response.json()
        except ValueError as exc:
            raise ProviderConfigurationError(
                "SerpAPI search returned invalid JSON."
            ) from exc
        if not isinstance(raw, dict):
            raise ProviderConfigurationError(
                "SerpAPI search returned non-object JSON."
            )

        raw_results = raw.get("organic_results", [])
        if not isinstance(raw_results, list):
            raise ProviderConfigurationError(
                "SerpAPI search returned invalid organic results JSON."
            )
        results = raw_results[: request.max_results]
        return _parse_result_items(
            "SerpAPI",
            [
                {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "content": item.get("snippet", ""),
                    "publisher": item.get("source"),
                    "published_at": item.get("date"),
                }
                for item in results
                if isinstance(item, dict)
            ],
            source_item_count=len(results),
        )


def _parse_result_items(
    provider_name: str, items: list[Any], *, source_item_count: int | None = None
) -> list[SearchResult]:
    checked_item_count = len(items) if source_item_count is None else source_item_count
    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            results.append(_to_search_result(item))
        except (TypeError, ValueError, ValidationError):
            continue
    if checked_item_count and not results:
        raise ProviderConfigurationError(
            f"{provider_name} search returned no valid source result records."
        )
    return results


def _to_search_result(item: dict[str, Any]) -> SearchResult:
    return SearchResult(
        title=item.get("title") or "Untitled source",
        url=item.get("url") or item.get("link"),
        snippet=item.get("content") or item.get("snippet") or "",
        publisher=item.get("publisher") or item.get("source"),
        published_at=item.get("published_at"),
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )
