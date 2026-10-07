import json

from langchain_core.tools import tool

from app.services.web_search import search_web
from app.graph.evidence_quality import (
    calculate_freshness_score,
    classify_authority,
)


@tool
async def search_news(query: str, max_results: int = 3) -> str:
    """
    Search the web for recent news related to the given query.

    Use this tool when you need additional factual information
    or evidence for a news story.
    """
    safe_max_results = min(max(max_results, 1), 3)

    response = await search_web(
        query,
        max_results=safe_max_results,
    )

    results = []

    for result in response.results:
        url = str(result.url)

        authority_tier, authority_score = classify_authority(
            url
        )

        freshness_score = calculate_freshness_score(
            result.published_at
        )

        results.append(
            {
                "title": result.title,
                "url": url,
                "content": result.content,
                "score": result.score,
                "published_at": result.published_at,
                "authority_tier": authority_tier,
                "authority_score": authority_score,
                "freshness_score": freshness_score,
            }
        )

    return json.dumps(
        {
            "query": response.query,
            "results": results,
        }
    )