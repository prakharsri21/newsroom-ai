import json
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo
from langchain_core.tools import tool

from app.services.web_search import search_web
from app.graph.evidence_quality import (
    calculate_freshness_score,
    classify_authority,
)

_CURRENT_NEWS_CUES = re.compile(
    r"\b(today|yesterday|latest|current|recent|breaking|news|"
    r"updates?|developments?|this week|follow[- ]?up)\b",
    re.IGNORECASE,
)

_HISTORICAL_QUERY_CUES = re.compile(
    r"\b(history of|historical|timeline of|origins of|background of)\b",
    re.IGNORECASE,
)


def build_date_aware_query(
    query: str,
    today: date | None = None,
) -> str:
    """Add today's date to current-news searches without altering the UI query."""
    cleaned_query = " ".join(query.split())

    if not cleaned_query:
        return cleaned_query

    has_current_intent = bool(_CURRENT_NEWS_CUES.search(cleaned_query))
    is_historical = bool(_HISTORICAL_QUERY_CUES.search(cleaned_query))

    if is_historical and not has_current_intent:
        return cleaned_query

    current_date = today or datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).date()

    date_label = current_date.strftime("%d %B %Y")

    date_variants = (
        date_label,
        f"{current_date.day} {current_date.strftime('%B %Y')}",
        current_date.isoformat(),
        current_date.strftime("%d %b %Y"),
        current_date.strftime("%B %d, %Y"),
    )

    query_lower = cleaned_query.casefold()

    if any(
        variant.casefold() in query_lower
        for variant in date_variants
    ):
        return cleaned_query

    if has_current_intent:
        return f"{cleaned_query} follow-up updates as of {date_label}"

    return (
        f"{cleaned_query} latest news and follow-up updates "
        f"as of {date_label}"
    )
@tool
async def search_news(query: str, max_results: int = 3) -> str:
    """
    Search the web for recent news related to the given query.

    Use this tool when you need additional factual information
    or evidence for a news story.
    """
    safe_max_results = min(max(max_results, 1), 3)

    requested_query = " ".join(query.split())
    dated_query = build_date_aware_query(requested_query)

    response = await search_web(
        dated_query,
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