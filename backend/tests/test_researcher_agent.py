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


@pytest.mark.anyio
async def test_researcher_forces_primary_planned_query_before_completing():
    response = SimpleNamespace(tool_calls=[], content="This is enough evidence.")
    mock_llm = SimpleNamespace(ainvoke=AsyncMock(return_value=response))

    with patch("app.graph.researcher_agent.researcher_llm", mock_llm):
        result = await researcher_agent_node(
            {
                "query": "CJP news update today",
                "query_plan": {
                    "intent": "current",
                    "primary_query": "CJP news",
                    "follow_up_queries": [
                        "CJP recent developments",
                        "CJP official response",
                    ],
                    "search_days": 7,
                },
                "messages": [],
                "iteration": 0,
                "research_queries": [],
                "research_evidence": [],
            }
        )

    tool_call = result["messages"][0].tool_calls[0]
    assert tool_call["name"] == "search_news"
    assert tool_call["args"]["query"] == "CJP news"
    assert tool_call["args"]["days"] == 7
    assert "research_complete" not in result


@pytest.mark.anyio
async def test_researcher_uses_follow_up_query_after_primary_was_searched():
    response = SimpleNamespace(tool_calls=[], content="Evidence needs a new development.")
    mock_llm = SimpleNamespace(ainvoke=AsyncMock(return_value=response))

    with patch("app.graph.researcher_agent.researcher_llm", mock_llm):
        result = await researcher_agent_node(
            {
                "query": "CJP news update today",
                "query_plan": {
                    "intent": "current",
                    "primary_query": "CJP news",
                    "follow_up_queries": [
                        "CJP recent developments",
                        "CJP official response",
                    ],
                    "search_days": 7,
                },
                "messages": [],
                "iteration": 1,
                "research_queries": ["CJP news"],
                "research_evidence": [
                    {
                        "url": "https://example.com/cjp",
                        "title": "Earlier CJP reporting",
                        "excerpt": "Earlier protest report.",
                        "relevance_score": 0.95,
                        "published_at": "2026-10-14T00:00:00Z",
                        "authority_tier": "reputable_secondary",
                        "authority_score": 0.8,
                        "freshness_score": 1.0,
                    }
                ],
            }
        )

    tool_call = result["messages"][0].tool_calls[0]
    assert tool_call["args"]["query"] == "CJP recent developments"


@pytest.mark.anyio
async def test_researcher_does_not_force_original_plan_during_follow_up_task():
    response = SimpleNamespace(tool_calls=[], content="Follow-up evidence found.")
    mock_llm = SimpleNamespace(ainvoke=AsyncMock(return_value=response))

    with patch("app.graph.researcher_agent.researcher_llm", mock_llm):
        result = await researcher_agent_node(
            {
                "query": "CJP news update today",
                "active_research_query": "Find the police response to CJP's request",
                "query_plan": {
                    "intent": "current",
                    "primary_query": "CJP news",
                    "follow_up_queries": ["CJP recent developments"],
                    "search_days": 7,
                },
                "messages": [],
                "iteration": 0,
                "research_queries": ["CJP news"],
                "research_evidence": [
                    {
                        "url": "https://example.com/cjp",
                        "title": "CJP report",
                        "excerpt": "The party made a request.",
                        "relevance_score": 0.95,
                        "published_at": "2026-10-14T00:00:00Z",
                        "authority_tier": "reputable_secondary",
                        "authority_score": 0.8,
                        "freshness_score": 1.0,
                    }
                ],
            }
        )

    assert not getattr(result["messages"][0], "tool_calls", [])



@pytest.mark.anyio
async def test_researcher_forces_historical_primary_without_date_filter():
    response = SimpleNamespace(tool_calls=[], content="Historical evidence found.")
    mock_llm = SimpleNamespace(ainvoke=AsyncMock(return_value=response))

    with patch("app.graph.researcher_agent.researcher_llm", mock_llm):
        result = await researcher_agent_node(
            {
                "query": "History of CJP protests",
                "query_plan": {
                    "intent": "historical",
                    "primary_query": "CJP protests timeline",
                    "follow_up_queries": [],
                    "search_days": None,
                },
                "messages": [],
                "iteration": 0,
                "research_queries": [],
                "research_evidence": [],
            }
        )

    tool_call = result["messages"][0].tool_calls[0]
    assert tool_call["args"]["query"] == "CJP protests timeline"
    assert tool_call["args"]["historical"] is True



@pytest.mark.anyio
async def test_researcher_does_not_force_second_follow_up_when_evidence_is_sufficient():
    response = SimpleNamespace(tool_calls=[], content="The evidence is sufficient.")
    mock_llm = SimpleNamespace(ainvoke=AsyncMock(return_value=response))

    with patch("app.graph.researcher_agent.researcher_llm", mock_llm):
        result = await researcher_agent_node(
            {
                "query": "CJP news today",
                "query_plan": {
                    "intent": "current",
                    "primary_query": "CJP news",
                    "follow_up_queries": [
                        "CJP recent developments",
                        "CJP official response",
                    ],
                    "search_days": 7,
                },
                "messages": [],
                "iteration": 2,
                "research_queries": [
                    "CJP news",
                    "CJP recent developments",
                ],
                "research_evidence": [
                    {
                        "url": "https://example.com/cjp",
                        "title": "CJP follow-up report",
                        "excerpt": "The report covers the latest confirmed development.",
                        "relevance_score": 0.95,
                        "published_at": "2026-10-14T00:00:00Z",
                        "authority_tier": "reputable_secondary",
                        "authority_score": 0.8,
                        "freshness_score": 1.0,
                    }
                ],
            }
        )

    assert result["research_complete"] is True
    assert not getattr(result["messages"][0], "tool_calls", [])


@pytest.mark.anyio
async def test_researcher_records_iteration_metrics():
    response = SimpleNamespace(
        tool_calls=[],
        content="Not enough evidence yet.",
    )
    mock_llm = SimpleNamespace(ainvoke=AsyncMock(return_value=response))

    with (
        patch("app.graph.researcher_agent.researcher_llm", mock_llm),
        patch("app.graph.researcher_agent.record_current_span") as record_span,
    ):
        result = await researcher_agent_node(
            {
                "query": "Test query",
                "query_plan": {
                    "intent": "current",
                    "primary_query": "Test query",
                    "follow_up_queries": [],
                    "search_days": 7,
                },
                "messages": [],
                "iteration": 0,
                "research_queries": ["Test query"],
                "research_evidence": [
                    {
                        "url": "https://example.com/article",
                        "title": "Test article",
                        "excerpt": "Test evidence.",
                        "relevance_score": 0.95,
                        "published_at": "2026-10-14T00:00:00Z",
                        "authority_tier": "reputable_secondary",
                        "authority_score": 0.8,
                        "freshness_score": 1.0,
                    }
                ],
            }
        )

    metrics = record_span.call_args.kwargs["metadata"]
    assert result["research_complete"] is True
    assert metrics["iteration"] == "1"
    assert metrics["query_plan_intent"] == "current"
    assert metrics["research_query_count"] == "1"
    assert metrics["evidence_count"] == "1"
    assert metrics["research_complete"] == "true"
