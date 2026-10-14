from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.graph.query_planner import build_news_query_plan
from app.schemas.query_plan import NewsQueryPlan


def _plan(**overrides):
    values = {
        "normalized_topic": "CJP news",
        "intent": "current",
        "primary_query": "CJP news",
        "follow_up_queries": [
            "CJP recent developments",
            "CJP official response",
        ],
        "search_days": 7,
        "disambiguation_notes": "Do not confuse CJP with another acronym.",
        "rationale": "Find current news and check follow-up developments.",
    }
    values.update(overrides)
    return NewsQueryPlan(**values)


@pytest.mark.anyio
async def test_query_planner_receives_current_india_date():
    with patch("app.graph.query_planner.query_planner_llm") as mock_llm:
        mock_llm.ainvoke = AsyncMock(return_value=_plan())
        result = await build_news_query_plan(
            "CJP news update today",
            today=date(2026, 10, 15),
        )

    assert result.primary_query == "CJP news"
    assert result.search_days == 7
    messages = mock_llm.ainvoke.await_args.args[0]
    assert "15 October 2026" in messages[0].content
    assert "Asia/Kolkata" in messages[1].content


@pytest.mark.anyio
async def test_query_planner_falls_back_when_model_fails():
    with patch("app.graph.query_planner.query_planner_llm") as mock_llm:
        mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("provider unavailable"))
        result = await build_news_query_plan(
            "CJP news update today",
            today=date(2026, 10, 15),
        )

    assert result.intent == "current"
    assert result.primary_query == "CJP news"
    assert result.search_days == 7
    assert len(result.follow_up_queries) == 2
    assert "fallback" in result.rationale.lower()


@pytest.mark.anyio
async def test_explicit_historical_query_disables_date_window():
    with patch("app.graph.query_planner.query_planner_llm") as mock_llm:
        mock_llm.ainvoke = AsyncMock(return_value=_plan())
        result = await build_news_query_plan(
            "History of CJP protests",
            today=date(2026, 10, 15),
        )

    assert result.intent == "historical"
    assert result.search_days is None
    assert result.follow_up_queries == []
