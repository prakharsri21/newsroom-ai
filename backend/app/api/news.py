from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.news import NewsStory


router = APIRouter(prefix="/news", tags=["news"])


@router.post("/stories")
async def create_story(
    headline: str,
    category: str,
    summary: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    story = NewsStory(
        headline=headline,
        category=category,
        summary=summary,
    )

    db.add(story)
    await db.commit()
    await db.refresh(story)

    return {
        "id": story.id,
        "headline": story.headline,
        "category": story.category,
    }


@router.get("/stories/{story_id}")
async def get_story(
    story_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NewsStory).where(NewsStory.id == story_id)
    )

    story = result.scalar_one_or_none()

    if story is None:
        return {"error": "Story not found"}

    return {
        "id": story.id,
        "headline": story.headline,
        "category": story.category,
        "summary": story.summary,
    }