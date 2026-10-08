from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.graph.editor_agent import editor_agent_node


def make_state():
    return {
        "query": "Latest RBI monetary policy decision",
        "research_summary": (
            "The RBI announced its latest monetary policy decision."
        ),
        "research_evidence": [
            {
                "url": "https://example.com/rbi",
                "title": "RBI Monetary Policy Decision",
                "publisher": "Example News",
                "source_type": "news",
                "excerpt": "The RBI announced its monetary policy decision.",
                "relevance_score": 0.95,
                "published_at": "2026-10-07T10:00:00Z",
                "authority_tier": "reputable_secondary",
                "authority_score": 0.8,
                "freshness_score": 1.0,
            }
        ],
    }


@pytest.mark.anyio
async def test_editor_generates_structured_article():
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

    fake_llm = SimpleNamespace(
        ainvoke=AsyncMock(return_value=mock_draft)
    )

    with patch("app.graph.editor_agent.editor_llm", fake_llm):
        result = await editor_agent_node(make_state())

    assert result["article_headline"] == (
        "RBI Announces Monetary Policy Decision"
    )
    assert result["citation_validation_passed"] is True
    assert result["citation_validation_errors"] == []
    assert result["article_claims"][0]["evidence_refs"] == ["E1"]


@pytest.mark.anyio
async def test_editor_requires_research_evidence():
    state = make_state()
    state["research_evidence"] = []

    with pytest.raises(ValueError, match="without research evidence"):
        await editor_agent_node(state)