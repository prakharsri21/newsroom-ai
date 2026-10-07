import json
from unittest.mock import AsyncMock, patch

import pytest

from app.graph.tools.research_tools import search_news
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
                published_at="2026-10-08",
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

    mock_search.assert_awaited_once_with(
        "test query",
        max_results=3,
    )

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

    mock_search.assert_awaited_once_with(
        "test query",
        max_results=3,
    )