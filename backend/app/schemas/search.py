from pydantic import BaseModel, HttpUrl


class SearchResult(BaseModel):
    title: str
    url: HttpUrl
    content: str
    score: float | None = None
    published_at: str | None = None


class WebSearchResponse(BaseModel):
    query: str
    results: list[SearchResult]