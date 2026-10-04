from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news import NewsStory


async def create_story(
    db: AsyncSession,
    *,
    headline: str,
    category: str,
    summary: str | None = None,
) -> NewsStory:
    story = NewsStory(
        headline=headline,
        category=category,
        summary=summary,
    )

    db.add(story)
    await db.commit()
    await db.refresh(story)

    return story


async def get_story(
    db: AsyncSession,
    *,
    story_id: int,
) -> NewsStory | None:
    result = await db.execute(
        select(NewsStory).where(NewsStory.id == story_id)
    )

    return result.scalar_one_or_none()