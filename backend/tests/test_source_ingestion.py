import pytest

from app.db.session import AsyncSessionLocal
from app.schemas.search import SearchResult
from app.services.source_ingestion import ingest_source
from app.services.web_fetch import FetchedPage


@pytest.mark.anyio
async def test_ingest_source(monkeypatch):
    async def fake_fetch(url: str) -> FetchedPage:
        return FetchedPage(
            url=url,
            title="Test Article",
            text="Test article content " * 20,
            status_code=200,
            extraction_method="TEST",
            metadata={},
        )

    monkeypatch.setattr(
        "app.services.source_ingestion.fetch_with_fallback",
        fake_fetch,
    )

    search_result = SearchResult(
        title="Test Article",
        url="https://example.com/test-ingestion",
        content="Search snippet",
        score=0.9,
    )

    async with AsyncSessionLocal() as db:
        source = await ingest_source(
            db,
            search_result,
        )

        assert source.url == "https://example.com/test-ingestion"
        assert source.title == "Test Article"
        assert source.domain == "example.com"
        assert source.content.startswith("Test article content")