from datetime import datetime

from pydantic import BaseModel, HttpUrl


class NormalizedSource(BaseModel):
    url: HttpUrl
    domain: str
    publisher: str | None = None
    title: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    content: str
    source_type: str = "OTHER"