import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, call, patch

import pytest

from app.graph.tools.research_tools import search_news
from app.schemas.search import SearchResult, WebSearchResponse
from app.services.query_normalization import normalize_search_query


def _response(*, results=None, query="CJP news"):
    return WebSearchResponse(query=query, results=results or [])


def _article():
    return SearchResult(
        title="CJP announces next protest step",
        url="https://example.com/cjp-update",
        content="The party announced a new protest step.",
        score=0.95,
        published_at=datetime.now(UTC).date().isoformat(),
    )


@pytest.mark.anyio
async def test_search_news_tool_returns_scored_results():
    fake = _response(
        results=[
            SearchResult(
                title="Test Article",
                url="https://example.com/article",
                content="Test article content",
                score=0.95,
                published_at=datetime.now(UTC).date().isoformat(),
            )
        ],
        query="test query",
    )
    with patch(
        "app.graph.tools.research_tools.search_web",
        new_callable=AsyncMock,
        return_value=fake,
    ) as mock_search:
        result = await search_news.ainvoke({"query": "test query", "max_results": 3})

    mock_search.assert_awaited_once_with("test query", max_results=3, days=7)
    payload = json.loads(result)
    item = payload["results"][0]
    assert payload["query"] == "test query"
    assert payload["search_metadata"]["fallback_used"] is False
    assert item["title"] == "Test Article"
    assert item["url"] == "https://example.com/article"
    assert item["authority_tier"] == "other"
    assert item["authority_score"] == 0.4
    assert item["freshness_score"] == 1.0


@pytest.mark.anyio
async def test_empty_current_search_retries_with_wider_date_window():
    empty = _response(query="test query")
    with patch(
        "app.graph.tools.research_tools.search_web",
        new_callable=AsyncMock,
        return_value=empty,
    ) as mock_search:
        result = await search_news.ainvoke({"query": "test query", "max_results": 5})

    assert mock_search.await_args_list == [
        call("test query", max_results=3, days=7),
        call("test query", max_results=3, days=14),
    ]
    payload = json.loads(result)
    assert payload["results"] == []
    assert payload["search_metadata"]["fallback_used"] is True
    assert payload["search_metadata"]["fallback_days"] == 14


@pytest.mark.anyio
async def test_cjp_query_variants_normalize_identically_and_fallback_recovers():
    empty = _response(query="CJP news")
    found = _response(results=[_article()], query="CJP news")
    with patch(
        "app.graph.tools.research_tools.search_web",
        new_callable=AsyncMock,
        side_effect=[empty, found],
    ) as mock_search:
        result = await search_news.ainvoke(
            {"query": "CJP news update today", "max_results": 3}
        )

    assert normalize_search_query("CJP news update today") == "CJP news"
    assert normalize_search_query("CJP news today") == "CJP news"
    assert mock_search.await_args_list == [
        call("CJP news", max_results=3, days=7),
        call("CJP news", max_results=3, days=14),
    ]
    payload = json.loads(result)
    assert len(payload["results"]) == 1
    assert payload["search_metadata"]["fallback_used"] is True


@pytest.mark.anyio
async def test_historical_query_skips_date_filter():
    with patch(
        "app.graph.tools.research_tools.search_web",
        new_callable=AsyncMock,
        return_value=_response(query="History of CJP"),
    ) as mock_search:
        await search_news.ainvoke({"query": "History of CJP", "max_results": 3})

    mock_search.assert_awaited_once_with(
        "History of CJP",
        max_results=3,
        days=None,
    )



@pytest.mark.anyio
async def test_historical_plan_flag_skips_date_filter_even_for_rewritten_query():
    with patch(
        "app.graph.tools.research_tools.search_web",
        new_callable=AsyncMock,
        return_value=_response(query="CJP election 2022"),
    ) as mock_search:
        await search_news.ainvoke(
            {
                "query": "CJP election 2022",
                "max_results": 3,
                "historical": True,
            }
        )

    mock_search.assert_awaited_once_with(
        "CJP election 2022",
        max_results=3,
        days=None,
    )
