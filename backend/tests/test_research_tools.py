import json
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.graph.tools.research_tools import (
    build_date_aware_query,
    search_news,
)
from app.schemas.search import SearchResult, WebSearchResponse


@pytest.mark.anyio
async def test_search_news_tool():
    fake_response = WebSearchResponse(
        query="test query",
        results=[
            SearchResult(
                title="Test Article",
                url="https://example.com/article",
                content="Test article content",
                score=0.95,
                published_at=datetime.now(UTC).date().isoformat(),
            )
        ],
    )

    with patch(
        "app.graph.tools.research_tools.search_web",
        new_callable=AsyncMock,
        return_value=fake_response,
    ) as mock_search:
        result = await search_news.ainvoke(
            {
                "query": "test query",
                "max_results": 3,
            }
        )

    mock_search.assert_awaited_once()

    called_query = mock_search.await_args.args[0]

    assert called_query.startswith("test query")
    assert "as of " in called_query
    assert mock_search.await_args.kwargs["max_results"] == 3

    payload = json.loads(result)

    assert payload["query"] == "test query"

    item = payload["results"][0]

    assert item["title"] == "Test Article"
    assert item["url"] == "https://example.com/article"
    assert item["authority_tier"] == "other"
    assert item["authority_score"] == 0.4
    assert item["freshness_score"] == 1.0


@pytest.mark.anyio
async def test_search_news_tool_caps_results_at_three():
    fake_response = WebSearchResponse(
        query="test query",
        results=[],
    )

    with patch(
        "app.graph.tools.research_tools.search_web",
        new_callable=AsyncMock,
        return_value=fake_response,
    ) as mock_search:
        await search_news.ainvoke(
            {
                "query": "test query",
                "max_results": 5,
            }
        )

    mock_search.assert_awaited_once()

    called_query = mock_search.await_args.args[0]

    assert called_query.startswith("test query")
    assert "as of " in called_query
    assert mock_search.await_args.kwargs["max_results"] == 3


def test_current_news_query_includes_today():
    result = build_date_aware_query(
        "CJP news today",
        today=date(2026, 10, 13),
    )

    assert result == (
        "CJP news today follow-up updates as of 13 October 2026"
    )


def test_historical_query_is_not_modified():
    result = build_date_aware_query(
        "History of CJP",
        today=date(2026, 10, 13),
    )

    assert result == "History of CJP"


def test_current_date_is_not_appended_twice():
    query = "CJP latest news on 13 October 2026"

    result = build_date_aware_query(
        query,
        today=date(2026, 10, 13),
    )

    assert result == query