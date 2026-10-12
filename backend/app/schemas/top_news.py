from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TopNewsItem(BaseModel):
    id: int
    headline: str
    summary: str | None = None
    category: str
    published_at: datetime | None = None
    first_seen_at: datetime
    source_title: str | None = None
    publisher: str | None = None
    source_url: str | None = None
    verification_status: Literal["not_checked"] = "not_checked"
    source_count: int = 1


class TopNewsResponse(BaseModel):
    items: list[TopNewsItem] = Field(default_factory=list)
    served_from_cache: bool
    refreshed_at: datetime | None = None
    message: str