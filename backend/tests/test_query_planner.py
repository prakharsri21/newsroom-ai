from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.graph.query_planner import build_news_query_plan
from app.schemas.query_plan import NewsQueryPlan


def _plan(**overrides):
    values = {
        "is_in_scope": True,
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
async def test_query_planner_fails_closed_when_model_fails():
    with (
        patch("app.graph.query_planner.query_planner_llm") as mock_llm,
        patch("app.graph.query_planner.record_current_span"),
    ):
        mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("provider unavailable"))

        with pytest.raises(RuntimeError, match="provider unavailable"):
            await build_news_query_plan(
                "Latest RBI monetary policy",
                today=date(2026, 10, 15),
            )


@pytest.mark.anyio
async def test_query_planner_rejects_website_building_help():
    rejected_plan = _plan(
        is_in_scope=False,
        rejection_reason="Newsroom AI only researches news.",
    )
    with patch("app.graph.query_planner.query_planner_llm") as mock_llm:
        mock_llm.ainvoke = AsyncMock(return_value=rejected_plan)
        result = await build_news_query_plan(
            "Can you help me build a website?",
            today=date(2026, 10, 15),
        )

    assert result.is_in_scope is False
    assert result.rejection_reason
    assert result.primary_query == ""
    assert result.follow_up_queries == []
    assert result.search_days is None

    messages = mock_llm.ainvoke.await_args.args[0]
    prompt = messages[0].content
    assert "Can you help me build a website?" in prompt
    assert "What are the latest developments in AI website builders?" in prompt


@pytest.mark.anyio
async def test_query_planner_accepts_news_about_ai_website_builders():
    with patch("app.graph.query_planner.query_planner_llm") as mock_llm:
        mock_llm.ainvoke = AsyncMock(
            return_value=_plan(
                normalized_topic="AI website builders",
                primary_query="Latest AI website builder developments",
            )
        )
        result = await build_news_query_plan(
            "What are the latest developments in AI website builders?",
            today=date(2026, 10, 15),
        )

    assert result.is_in_scope is True
    assert result.primary_query == "Latest AI website builder developments"


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
