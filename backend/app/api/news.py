from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.news import create_story, get_story


router = APIRouter(
    prefix="/news",
    tags=["news"],
)


class CreateStoryRequest(BaseModel):
    headline: str
    category: str
    summary: str | None = None


@router.post("/stories")
async def create_news_story(
    request: CreateStoryRequest,
    db: AsyncSession = Depends(get_db),
):
    story = await create_story(
        db,
        headline=request.headline,
        category=request.category,
        summary=request.summary,
    )

    return {
        "id": story.id,
        "headline": story.headline,
        "category": story.category,
        "summary": story.summary,
    }


@router.get("/stories/{story_id}")
async def get_news_story(
    story_id: int,
    db: AsyncSession = Depends(get_db),
):
    story = await get_story(
        db,
        story_id=story_id,
    )

    if story is None:
        raise HTTPException(
            status_code=404,
            detail="Story not found",
        )

    return {
        "id": story.id,
        "headline": story.headline,
        "category": story.category,
        "summary": story.summary,
    }