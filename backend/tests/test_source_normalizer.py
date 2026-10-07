from datetime import datetime, timezone

from app.schemas.search import SearchResult
from app.services.source_normalizer import normalize_source
from app.services.web_fetch import FetchedPage


def test_normalizes_news_source():
    search_result = SearchResult(
        title="India-US trade talks",
        url="https://www.reuters.com/world/india/example?utm_source=test",
        content="Search snippet",
        score=0.95,
        published_at="2026-10-05T10:30:00Z",
    )

    fetched_page = FetchedPage(
        url="https://www.reuters.com/world/india/example/",
        title="India-US trade talks",
        text="Full article content goes here.",
        status_code=200,
        extraction_method="HTTPX_BEAUTIFULSOUP",
        metadata={},
    )

    source = normalize_source(
        search_result,
        fetched_page,
    )

    assert str(source.url) == (
    "https://reuters.com/world/india/example"
    )
    assert source.domain == "reuters.com"
    assert source.publisher == "Reuters"
    assert source.source_type == "NEWS"
    assert source.title == "India-US trade talks"
    assert source.author is None


def test_parses_published_date():
    search_result = SearchResult(
        title="Test",
        url="https://example.com/article",
        content="Content",
        published_at="2026-10-05T10:30:00Z",
    )

    fetched_page = FetchedPage(
        url="https://example.com/article",
        title="Test",
        text="Long enough content",
        status_code=200,
        extraction_method="HTTPX_BEAUTIFULSOUP",
        metadata={},
    )

    source = normalize_source(
        search_result,
        fetched_page,
    )

    assert source.published_at == datetime(
        2026,
        10,
        5,
        10,
        30,
        tzinfo=timezone.utc,
    )