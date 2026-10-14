from langfuse import observe
from tavily import AsyncTavilyClient

from app.core.config import get_settings
from app.schemas.search import SearchResult, WebSearchResponse
from app.services.observability import record_current_span


settings = get_settings()


@observe(
    name="web-search",
    as_type="tool",
    capture_output=False,
)
async def search_web(
    query: str,
    *,
    max_results: int = 3,
    days: int | None = None,
) -> WebSearchResponse:
    client = AsyncTavilyClient(
        api_key=settings.tavily_api_key
    )

    response = await client.search(
        query=query,
        topic="news",
        search_depth="basic",
        max_results=max_results,
        days=days,
        include_answer=False,
    )

    results = [
        SearchResult(
            title=result["title"],
            url=result["url"],
            content=result.get("content", ""),
            score=result.get("score"),
            published_at=result.get("published_date"),
        )
        for result in response.get("results", [])
    ]

    record_current_span(
        metadata={
            "provider": "tavily",
            "result_count": str(len(results)),
            "max_results": str(max_results),
            "search_depth": "basic",
            "query_length": str(len(query)),
            "days": str(days) if days is not None else "none",
        }
    )

    return WebSearchResponse(
        query=query,
        results=results,
    )