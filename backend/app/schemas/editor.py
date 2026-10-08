from pydantic import BaseModel, Field, model_validator


class ArticleParagraph(BaseModel):
    text: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)


class ArticleClaim(BaseModel):
    claim_text: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_evidence_refs(self):
        if not self.evidence_refs:
            raise ValueError("Every factual claim must have at least one evidence reference.")
        return self


class ArticleDraft(BaseModel):
    headline: str = Field(min_length=1)
    headline_evidence_refs: list[str] = Field(default_factory=list)

    summary: str = Field(min_length=1)
    summary_evidence_refs: list[str] = Field(default_factory=list)

    paragraphs: list[ArticleParagraph] = Field(min_length=1)
    claims: list[ArticleClaim] = Field(default_factory=list)