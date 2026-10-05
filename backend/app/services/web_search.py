from langfuse import get_client, observe
from tavily import AsyncTavilyClient

from app.core.config import get_settings
from app.schemas.search import SearchResult, WebSearchResponse


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
) -> WebSearchResponse:
    client = AsyncTavilyClient(
        api_key=settings.tavily_api_key
    )

    response = await client.search(
        query=query,
        topic="news",
        search_depth="basic",
        max_results=max_results,
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

    langfuse = get_client()

    langfuse.update_current_span(
        metadata={
            "provider": "tavily",
            "result_count": str(len(results)),
            "search_depth": "basic",
        }
    )

    return WebSearchResponse(
        query=query,
        results=results,
    )