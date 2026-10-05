from dataclasses import dataclass

from firecrawl import AsyncFirecrawl

from app.core.config import get_settings


settings = get_settings()


@dataclass
class FirecrawlPage:
    url: str
    title: str | None
    text: str
    metadata: dict


async def fetch_with_firecrawl(url: str) -> FirecrawlPage:
    client = AsyncFirecrawl(
        api_key=settings.firecrawl_api_key,
    )

    result = await client.scrape(
        url=url,
        formats=["markdown"],
    )

    markdown = result.markdown or ""

    metadata_object = result.metadata

    if hasattr(metadata_object, "model_dump"):
        metadata = metadata_object.model_dump()
    elif isinstance(metadata_object, dict):
        metadata = metadata_object
    else:
        metadata = {}

    title = (
        metadata.get("title")
        or metadata.get("og_title")
    )

    source_url = (
        metadata.get("source_url")
        or metadata.get("url")
        or url
    )

    return FirecrawlPage(
        url=str(source_url),
        title=title,
        text=markdown,
        metadata=metadata,
    )