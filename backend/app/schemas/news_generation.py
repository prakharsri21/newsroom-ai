from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.fact_check import ClaimVerification


GenerationStatus = Literal[
    "verified",
    "needs_review",
    "research_incomplete",
    "citation_validation_failed",
]


class GenerateNewsRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=3, max_length=500)
    category: str = Field(
        default="General",
        min_length=1,
        max_length=50,
    )


class NewsSourceResponse(BaseModel):
    evidence_ref: str
    source_id: int | None = None
    title: str
    publisher: str | None = None
    url: str
    published_at: str | None = None
    authority_tier: str | None = None


class NewsGenerationResponse(BaseModel):
    status: GenerationStatus
    query: str

    story_id: int | None = None
    article_id: int | None = None

    headline: str | None = None
    summary: str | None = None
    article: str | None = None

    research_complete: bool
    citation_validation_passed: bool | None = None
    fact_check_passed: bool | None = None
    fact_check_reason: str | None = None
    research_failure_reason: str | None = None
    citation_validation_errors: list[str] = Field(default_factory=list)

    sources: list[NewsSourceResponse] = Field(default_factory=list)
    claims: list[ClaimVerification] = Field(default_factory=list)

    message: str