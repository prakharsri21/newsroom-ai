from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source
from app.schemas.source import NormalizedSource


async def get_source_by_url(
    db: AsyncSession,
    *,
    url: str,
) -> Source | None:
    result = await db.execute(
        select(Source).where(Source.url == url)
    )

    return result.scalar_one_or_none()


async def save_source(
    db: AsyncSession,
    source_data: NormalizedSource,
) -> Source:
    existing = await get_source_by_url(
        db,
        url=str(source_data.url),
    )

    if existing:
        return existing

    source = Source(
        url=str(source_data.url),
        domain=source_data.domain,
        publisher=source_data.publisher,
        title=source_data.title,
        author=source_data.author,
        published_at=source_data.published_at,
        content=source_data.content,
        source_type=source_data.source_type,
    )

    db.add(source)

    await db.commit()
    await db.refresh(source)

    return source