from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.graph.researcher import decide_research_action
from app.schemas.research import ResearchDecision


@pytest.mark.anyio
async def test_researcher_requests_more_research():
    decision = ResearchDecision(
        action="search",
        search_query="RBI official monetary policy announcement",
        rationale="No authoritative evidence has been collected yet.",
    )

    mock_llm = SimpleNamespace(
        ainvoke=AsyncMock(return_value=decision)
    )

    with patch(
        "app.graph.researcher.researcher_decision_llm",
        mock_llm,
    ):
        result = await decide_research_action(
            query="RBI monetary policy announcement",
            evidence=[],
            previous_queries=[],
        )

    mock_llm.ainvoke.assert_awaited_once()

    assert result.action == "search"
    assert result.search_query == (
        "RBI official monetary policy announcement"
    )


@pytest.mark.anyio
async def test_researcher_can_complete():
    decision = ResearchDecision(
        action="complete",
        rationale="The available evidence is sufficient.",
    )

    mock_llm = SimpleNamespace(
        ainvoke=AsyncMock(return_value=decision)
    )

    with patch(
        "app.graph.researcher.researcher_decision_llm",
        mock_llm,
    ):
        result = await decide_research_action(
            query="RBI monetary policy announcement",
            evidence=[
                {
                    "source_id": 1,
                    "url": "https://example.com",
                    "title": "RBI Announcement",
                    "publisher": "RBI",
                    "source_type": "NEWS",
                    "excerpt": "Example evidence",
                    "relevance_score": 0.95,
                }
            ],
            previous_queries=[
                "RBI monetary policy announcement"
            ],
        )

    mock_llm.ainvoke.assert_awaited_once()

    assert result.action == "complete"
    assert result.search_query is None