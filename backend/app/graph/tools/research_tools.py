import json

from langchain_core.tools import tool

from app.graph.evidence_quality import (
    calculate_freshness_score,
    classify_authority,
)
from app.services.query_normalization import (
    default_search_days,
    normalize_search_query,
)
from app.services.web_search import search_web


@tool
async def search_news(
    query: str,
    max_results: int = 3,
    days: int | None = None,
) -> str:
    """
    Search for news using a concise topic-focused query.

    Current-news searches use a seven-day publication window by default.
    Set days explicitly when the Query Planner provides a window; historical
    requests omit date filtering.
    """
    safe_max_results = min(max(max_results, 1), 3)
    requested_query = " ".join(query.split())
    normalized_query = normalize_search_query(requested_query) or requested_query

    effective_days = (
        max(1, min(days, 30))
        if days is not None
        else default_search_days(requested_query)
    )

    response = await search_web(
        normalized_query,
        max_results=safe_max_results,
        days=effective_days,
    )
    fallback_used = False
    fallback_days: int | None = None

    # Widen the date window only when the narrower current-news search is empty.
    # This catches late-indexed reports without adding a second call on success.
    if not response.results and effective_days is not None:
        candidate_days = min(max(effective_days * 2, 14), 30)
        if candidate_days > effective_days:
            fallback_used = True
            fallback_days = candidate_days
            response = await search_web(
                normalized_query,
                max_results=safe_max_results,
                days=fallback_days,
            )

    results = []
    for result in response.results:
        url = str(result.url)
        authority_tier, authority_score = classify_authority(url)
        freshness_score = calculate_freshness_score(result.published_at)

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
            "search_metadata": {
                "requested_query": requested_query,
                "normalized_query": normalized_query,
                "search_days": effective_days,
                "fallback_used": fallback_used,
                "fallback_days": fallback_days,
            },
        }
    )
