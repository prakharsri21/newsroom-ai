from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.news import create_story, get_story
import logging
from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.news_generation import (
    GenerateNewsRequest,
    NewsGenerationResponse,
)
from app.services.generation import (
    generate_news as generate_news_service,
)
from app.schemas.top_news import TopNewsResponse
from app.services.top_news import (
    TopNewsUnavailableError,
    get_top_news as get_top_news_service,
)

logger = logging.getLogger(__name__)
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


@router.post(
    "/generate",
    response_model=NewsGenerationResponse,
)
async def generate_news_endpoint(
    request: GenerateNewsRequest,
    db: AsyncSession = Depends(get_db),
) -> NewsGenerationResponse:
    """Generate an evidence-backed article and return its verification results."""
    try:
        return await generate_news_service(
            db,
            query=request.query,
            category=request.category,
        )
    except Exception as exc:
        logger.exception("News generation request failed")
        raise HTTPException(
            status_code=500,
            detail="News generation could not be completed. Please try again.",
        ) from exc


@router.get("/top", response_model=TopNewsResponse)
async def get_top_news_endpoint(
    limit: int = Query(default=5, ge=1, le=10),
    refresh: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
) -> TopNewsResponse:
    """Return the latest discovered news, using a 30-minute cache."""
    try:
        return await get_top_news_service(
            db,
            limit=limit,
            force_refresh=refresh,
        )
    except TopNewsUnavailableError as exc:
        logger.warning("Top-news discovery is unavailable: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Live news discovery is temporarily unavailable.",
        ) from exc
