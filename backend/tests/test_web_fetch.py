from unittest.mock import Mock

import httpx
import pytest

from app.services.firecrawl_fetch import FirecrawlPage
from app.services.web_fetch import fetch_with_fallback


@pytest.mark.anyio
async def test_fetch_with_fallback_records_firecrawl_success(monkeypatch):
    url = "https://example.com/article"

    async def fail_http_fetch(requested_url: str):
        request = httpx.Request("GET", requested_url)
        response = httpx.Response(403, request=request)
        raise httpx.HTTPStatusError(
            "Forbidden",
            request=request,
            response=response,
        )

    async def successful_firecrawl_fetch(requested_url: str):
        return FirecrawlPage(
            url=requested_url,
            title="Fetched article",
            text="Article text " * 30,
            metadata={"source": "test"},
        )

    record_span = Mock()
    monkeypatch.setattr(
        "app.services.web_fetch.fetch_page",
        fail_http_fetch,
    )
    monkeypatch.setattr(
        "app.services.web_fetch.fetch_with_firecrawl",
        successful_firecrawl_fetch,
    )
    monkeypatch.setattr(
        "app.services.web_fetch.record_current_span",
        record_span,
    )

    page = await fetch_with_fallback(url)

    assert page.extraction_method == "FIRECRAWL"
    assert page.title == "Fetched article"
    assert page.metadata == {"source": "test"}

    recorded_metadata = [
        call.kwargs["metadata"]
        for call in record_span.call_args_list
    ]
    assert any(
        item.get("fallback_status") == "started"
        and item.get("fallback_trigger_error_type") == "HTTPStatusError"
        for item in recorded_metadata
    )
    assert any(
        item.get("fallback_status") == "success"
        and item.get("fallback_extraction_method") == "FIRECRAWL"
        and int(item["fallback_text_length"]) > 0
        for item in recorded_metadata
    )


@pytest.mark.anyio
async def test_fetch_with_fallback_records_firecrawl_error(monkeypatch):
    url = "https://example.com/article"

    async def insufficient_http_fetch(_url: str):
        raise ValueError("Extracted page text is too short")

    async def failed_firecrawl_fetch(_url: str):
        raise RuntimeError("Firecrawl unavailable")

    record_span = Mock()
    monkeypatch.setattr(
        "app.services.web_fetch.fetch_page",
        insufficient_http_fetch,
    )
    monkeypatch.setattr(
        "app.services.web_fetch.fetch_with_firecrawl",
        failed_firecrawl_fetch,
    )
    monkeypatch.setattr(
        "app.services.web_fetch.record_current_span",
        record_span,
    )

    with pytest.raises(RuntimeError, match="Firecrawl unavailable"):
        await fetch_with_fallback(url)

    recorded_metadata = [
        call.kwargs["metadata"]
        for call in record_span.call_args_list
    ]
    assert any(
        item.get("fallback_status") == "error"
        and item.get("fallback_error_type") == "RuntimeError"
        for item in recorded_metadata
    )
