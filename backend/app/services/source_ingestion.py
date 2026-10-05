from langfuse import observe
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.search import SearchResult
from app.services.source_normalizer import normalize_source
from app.services.sources import save_source
from app.services.web_fetch import fetch_with_fallback


@observe(
    name="ingest-source",
    as_type="span",
    capture_output=False,
)
async def ingest_source(
    db: AsyncSession,
    search_result: SearchResult,
):
    fetched_page = await fetch_with_fallback(
        str(search_result.url)
    )

    normalized_source = normalize_source(
        search_result,
        fetched_page,
    )

    source = await save_source(
        db,
        normalized_source,
    )

    return source