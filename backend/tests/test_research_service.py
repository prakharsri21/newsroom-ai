from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.research import run_research


@pytest.mark.anyio
async def test_run_research_persists_completed_research():

    graph_result = {
        "query": "Test query",
        "research_complete": True,
        "research_evidence": [
            {
                "url": "https://example.com/article",
                "title": "Test article",
                "excerpt": "Evidence",
                "relevance_score": 0.9,
                "published_at": "2026-10-08",
            }
        ],
    }

    with (
        patch(
            "app.services.research.research_graph.ainvoke",
            new_callable=AsyncMock,
            return_value=graph_result,
        ),
        patch(
            "app.services.research.persist_research_evidence",
            new_callable=AsyncMock,
            return_value=(
                [42],
                [
                    {
                        **graph_result["research_evidence"][0],
                        "source_id": 42,
                        "publisher": "Example",
                        "source_type": "NEWS",
                    }
                ],
            ),
        ),
    ):
        result = await run_research(
            SimpleNamespace(),
            {
                "query": "Test query",
                "iteration": 0,
            },
        )

    assert result["source_ids"] == [42]
    assert result["research_evidence"][0]["source_id"] == 42