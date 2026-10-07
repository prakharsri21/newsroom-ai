from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.research_persistence import persist_research_evidence


@pytest.mark.anyio
async def test_persists_research_evidence():
    fake_source = SimpleNamespace(
        id=42,
        publisher="Reuters",
        source_type="NEWS",
    )

    evidence = [
        {
            "url": "https://www.reuters.com/article",
            "title": "Test article",
            "excerpt": "Test evidence",
            "relevance_score": 0.95,
            "published_at": "2026-10-08T00:00:00Z",
            "authority_tier": "reputable_secondary",
            "authority_score": 0.8,
            "freshness_score": 1.0,
        }
    ]

    with patch(
        "app.services.research_persistence.ingest_source",
        new_callable=AsyncMock,
        return_value=fake_source,
    ) as mock_ingest:
        source_ids, enriched = await persist_research_evidence(
            SimpleNamespace(),
            evidence,
        )

    assert source_ids == [42]

    assert enriched[0]["source_id"] == 42
    assert enriched[0]["publisher"] == "Reuters"
    assert enriched[0]["source_type"] == "NEWS"

    mock_ingest.assert_awaited_once()

@pytest.mark.anyio
async def test_deduplicates_source_ids():
    fake_source = SimpleNamespace(
        id=42,
        publisher="Reuters",
        source_type="NEWS",
    )

    evidence = [
        {
            "url": "https://example.com/a",
            "title": "Article A",
            "excerpt": "Evidence A",
        },
        {
            "url": "https://example.com/b",
            "title": "Article B",
            "excerpt": "Evidence B",
        },
    ]

    with patch(
        "app.services.research_persistence.ingest_source",
        new_callable=AsyncMock,
        return_value=fake_source,
    ):
        source_ids, enriched = await persist_research_evidence(
            SimpleNamespace(),
            evidence,
        )

    assert source_ids == [42]
    assert enriched[0]["source_id"] == 42
    assert enriched[1]["source_id"] == 42