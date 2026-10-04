from fastapi import FastAPI
from app.api.news import router as news_router

from app.core.config import get_settings
from app.services.smoke_test import run_smoke_test

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.include_router(news_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
    }


@app.get("/debug/trace")
async def debug_trace() -> dict[str, str]:
    return run_smoke_test("Day 1 Langfuse test")