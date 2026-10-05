from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from langfuse import observe

from app.core.observability import langfuse
from app.services.firecrawl_fetch import fetch_with_firecrawl


MIN_CONTENT_LENGTH = 200


@dataclass
class FetchedPage:
    url: str
    title: str | None
    text: str
    status_code: int
    extraction_method: str
    metadata: dict


@observe(
    name="fetch-source-http",
    as_type="tool",
    capture_output=False,
)
async def fetch_page(url: str) -> FetchedPage:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/139.0 Safari/537.36"
        )
    }

    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        headers=headers,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    content_type = response.headers.get("content-type", "")

    if "text/html" not in content_type.lower():
        raise ValueError(
            f"Unsupported content type: {content_type}"
        )

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    # Remove elements that generally don't contain useful article content.
    for element in soup(
        ["script", "style", "noscript", "svg", "nav", "footer"]
    ):
        element.decompose()

    title = (
        soup.title.get_text(strip=True)
        if soup.title
        else None
    )

    text = soup.get_text(
        separator=" ",
        strip=True,
    )

    if len(text) < MIN_CONTENT_LENGTH:
        raise ValueError(
            "Extracted page text is too short"
        )

    page = FetchedPage(
        url=str(response.url),
        title=title,
        text=text,
        status_code=response.status_code,
        extraction_method="HTTPX_BEAUTIFULSOUP",
        metadata={
            "content_type": content_type,
        },
    )

    langfuse.update_current_span(
        metadata={
            "status_code": str(response.status_code),
            "extraction_method": page.extraction_method,
            "text_length": str(len(page.text)),
        }
    )

    return page


@observe(
    name="fetch-source",
    as_type="tool",
    capture_output=False,
)
async def fetch_with_fallback(url: str) -> FetchedPage:
    try:
        return await fetch_page(url)

    except (httpx.HTTPError, ValueError):
        langfuse.update_current_span(
            metadata={
                "fallback": "firecrawl",
                "fallback_reason": "http_fetch_failed_or_content_insufficient",
            }
        )

        firecrawl_page = await fetch_with_firecrawl(url)

        return FetchedPage(
            url=firecrawl_page.url,
            title=firecrawl_page.title,
            text=firecrawl_page.text,
            status_code=200,
            extraction_method="FIRECRAWL",
            metadata=firecrawl_page.metadata,
        )