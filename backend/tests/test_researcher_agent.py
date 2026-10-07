from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.graph.researcher_agent import researcher_agent_node


@pytest.mark.anyio
async def test_researcher_agent_requests_tool():
    tool_call = {
        "name": "search_news",
        "args": {
            "query": "RBI monetary policy announcement",
            "max_results": 3,
        },
        "id": "test-tool-call",
        "type": "tool_call",
    }

    response = SimpleNamespace(
        tool_calls=[tool_call],
        content="",
    )

    mock_llm = SimpleNamespace(
        ainvoke=AsyncMock(return_value=response)
    )

    with patch(
        "app.graph.researcher_agent.researcher_llm",
        mock_llm,
    ):
        result = await researcher_agent_node(
            {
                "query": "Latest RBI monetary policy decision?",
                "messages": [],
            }
        )

    mock_llm.ainvoke.assert_awaited_once()

    assert len(result["messages"]) == 1
    assert result["messages"][0].tool_calls[0]["name"] == "search_news"


@pytest.mark.anyio
async def test_researcher_marks_research_complete():
    response = SimpleNamespace(
        tool_calls=[],
        content="The available evidence is sufficient.",
    )

    mock_llm = SimpleNamespace(
        ainvoke=AsyncMock(return_value=response)
    )

    with patch(
        "app.graph.researcher_agent.researcher_llm",
        mock_llm,
    ):
        result = await researcher_agent_node(
            {
                "query": "Test query",
                "messages": [],
                "iteration": 0,
                "research_queries": ["Test query"],
                "research_evidence": [
                    {
                        "url": "https://example.com/article",
                        "title": "Test Article",
                        "excerpt": "Test evidence supporting the query.",
                        "relevance_score": 0.95,
                        "published_at": "2026-10-08T00:00:00Z",
                        "authority_tier": "reputable_secondary",
                        "authority_score": 0.8,
                        "freshness_score": 1.0,
                    }
                ],
            }
        )

    assert result["research_complete"] is True
    assert result["research_summary"] == (
        "The available evidence is sufficient."
    )


@pytest.mark.anyio
async def test_researcher_cannot_complete_without_evidence():
    response = SimpleNamespace(
        tool_calls=[],
        content="Research is sufficient.",
    )

    mock_llm = SimpleNamespace(
        ainvoke=AsyncMock(return_value=response)
    )

    with patch(
        "app.graph.researcher_agent.researcher_llm",
        mock_llm,
    ):
        result = await researcher_agent_node(
            {
                "query": "Test query",
                "messages": [],
                "iteration": 0,
                "research_queries": [],
                "research_evidence": [],
            }
        )

    assert result["research_complete"] is False