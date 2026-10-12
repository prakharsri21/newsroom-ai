from fastapi import FastAPI
from app.api.news import router as news_router

from app.core.config import get_settings
from app.services.smoke_test import run_smoke_test
from fastapi.middleware.cors import CORSMiddleware

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
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