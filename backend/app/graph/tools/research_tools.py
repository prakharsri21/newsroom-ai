import json

from langchain_core.tools import tool
from langfuse import observe

from app.graph.evidence_quality import (
    calculate_freshness_score,
    classify_authority,
)
from app.services.observability import record_current_span
from app.services.query_normalization import (
    default_search_days,
    normalize_search_query,
)
from app.services.web_search import search_web


@tool
@observe(
    name="search-news-tool",
    as_type="tool",
    capture_input=False,
    capture_output=False,
)
async def search_news(
    query: str,
    max_results: int = 3,
    days: int | None = None,
    historical: bool = False,
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

    if historical:
        effective_days = None
    elif days is not None:
        effective_days = max(1, min(days, 30))
    else:
        effective_days = default_search_days(requested_query)

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

    record_current_span(
        metadata={
            "query_length": str(len(normalized_query)),
            "search_days": str(effective_days) if effective_days is not None else "none",
            "historical": str(historical or effective_days is None).lower(),
            "fallback_used": str(fallback_used).lower(),
            "fallback_days": str(fallback_days) if fallback_days is not None else "none",
            "search_attempt_count": "2" if fallback_used else "1",
            "result_count": str(len(results)),
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
                "historical": historical or effective_days is None,
            },
        }
    )
