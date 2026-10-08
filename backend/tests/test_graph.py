from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.graph.graph import newsroom_graph


def make_research_result(query: str) -> dict:
    return {
        "query": query,
        "research_complete": True,
        "research_summary": (
            "The RBI announced its latest monetary policy decision."
        ),
        "research_evidence": [
            {
                "url": "https://example.com/rbi",
                "title": "RBI Monetary Policy Decision",
                "publisher": "Example News",
                "source_type": "news",
                "excerpt": (
                    "The RBI announced its latest monetary policy decision."
                ),
                "relevance_score": 0.95,
                "published_at": "2026-10-07T10:00:00Z",
                "authority_tier": "reputable_secondary",
                "authority_score": 0.8,
                "freshness_score": 1.0,
            }
        ],
        "source_ids": [],
        "iteration": 0,
        "article_version": 0,
    }


def make_editor_draft():
    return SimpleNamespace(
        headline="RBI Announces Monetary Policy Decision",
        headline_evidence_refs=["E1"],
        summary="The RBI announced its latest monetary policy decision.",
        summary_evidence_refs=["E1"],
        paragraphs=[
            SimpleNamespace(
                text=(
                    "The RBI announced its latest monetary policy decision."
                ),
                evidence_refs=["E1"],
                model_dump=lambda: {
                    "text": (
                        "The RBI announced its latest monetary policy decision."
                    ),
                    "evidence_refs": ["E1"],
                },
            )
        ],
        claims=[
            SimpleNamespace(
                claim_text=(
                    "The RBI announced its latest monetary policy decision."
                ),
                evidence_refs=["E1"],
                model_dump=lambda: {
                    "claim_text": (
                        "The RBI announced its latest monetary policy decision."
                    ),
                    "evidence_refs": ["E1"],
                },
            )
        ],
    )


async def run_graph_with_mocks(query: str):
    research_result = make_research_result(query)
    fake_editor = SimpleNamespace(
        ainvoke=AsyncMock(return_value=make_editor_draft())
    )

    with (
        patch(
            "app.graph.research_graph.research_graph.ainvoke",
            new=AsyncMock(return_value=research_result),
        ),
        patch(
            "app.graph.editor_agent.editor_llm",
            fake_editor,
        ),
        patch(
            "app.graph.editor_agent.get_client",
        ) as mock_get_client,
    ):
        mock_get_client.return_value.update_current_span = (
            lambda **kwargs: None
        )

        return await newsroom_graph.ainvoke(
            {
                "query": query,
                "iteration": 0,
                "article_version": 0,
            }
        )


@pytest.mark.anyio
async def test_newsroom_graph_completes():
    result = await run_graph_with_mocks(
        "test newsroom workflow"
    )

    assert result["research_complete"] is True
    assert result["article_version"] == 1
    assert result["citation_validation_passed"] is True
    assert result["article_draft"]


@pytest.mark.anyio
async def test_graph_state_contains_expected_fields():
    result = await run_graph_with_mocks(
        "test state"
    )

    assert result["query"] == "test state"
    assert "article_draft" in result
    assert "article_headline" in result
    assert "article_summary" in result
    assert "article_claims" in result
    assert "citation_validation_errors" in result
    assert result["iteration"] == 0

@pytest.mark.anyio
async def test_newsroom_graph_does_not_edit_incomplete_research():
    incomplete_research = {
        "query": "test incomplete research",
        "research_complete": False,
        "research_failure_reason": (
            "Research reached the maximum iteration limit "
            "without sufficient evidence."
        ),
        "research_summary": (
            "The available evidence was insufficient to confirm the request."
        ),
        "research_evidence": [],
        "source_ids": [],
        "iteration": 3,
        "article_version": 0,
    }

    with patch(
        "app.graph.research_graph.research_graph.ainvoke",
        new=AsyncMock(return_value=incomplete_research),
    ):
        result = await newsroom_graph.ainvoke(
            {
                "query": "test incomplete research",
                "iteration": 0,
                "article_version": 0,
            }
        )

    assert result["research_complete"] is False
    assert result["research_failure_reason"]
    assert "article_headline" not in result