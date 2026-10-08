from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.graph.graph import newsroom_graph


@pytest.mark.anyio
async def test_newsroom_graph_researches_then_edits():
    research_state = {
        "query": "Latest RBI monetary policy decision",
        "research_summary": "The RBI announced its latest monetary policy decision.",
        "research_complete": True,
        "research_evidence": [
            {
                "url": "https://example.com/rbi",
                "title": "RBI Monetary Policy Decision",
                "publisher": "Example News",
                "source_type": "news",
                "excerpt": "The RBI announced its latest monetary policy decision.",
                "relevance_score": 0.95,
                "published_at": "2026-10-07T10:00:00Z",
                "authority_tier": "reputable_secondary",
                "authority_score": 0.8,
                "freshness_score": 1.0,
            }
        ],
    }

    mock_draft = SimpleNamespace(
        headline="RBI Announces Monetary Policy Decision",
        headline_evidence_refs=["E1"],
        summary="The RBI announced its latest monetary policy decision.",
        summary_evidence_refs=["E1"],
        paragraphs=[
            SimpleNamespace(
                text="The RBI announced its latest monetary policy decision.",
                evidence_refs=["E1"],
                model_dump=lambda: {
                    "text": "The RBI announced its latest monetary policy decision.",
                    "evidence_refs": ["E1"],
                },
            )
        ],
        claims=[
            SimpleNamespace(
                claim_text="The RBI announced its latest monetary policy decision.",
                evidence_refs=["E1"],
                model_dump=lambda: {
                    "claim_text": "The RBI announced its latest monetary policy decision.",
                    "evidence_refs": ["E1"],
                },
            )
        ],
    )

    fake_editor = SimpleNamespace(
        ainvoke=AsyncMock(return_value=mock_draft)
    )

    with (
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

        with patch(
            "app.graph.research_graph.research_graph.ainvoke",
            new=AsyncMock(return_value=research_state),
        ):
            result = await newsroom_graph.ainvoke(
                {"query": research_state["query"]}
            )

    assert result["article_headline"] == (
        "RBI Announces Monetary Policy Decision"
    )
    assert result["article_version"] == 1
    assert result["citation_validation_passed"] is True
    assert result["article_claims"][0]["evidence_refs"] == ["E1"]