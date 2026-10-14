from typing import Literal

from pydantic import BaseModel, Field, model_validator


class NewsQueryPlan(BaseModel):
    """Scope decision plus a validated search plan for a news query."""

    # Required: never infer scope from the existence of a rewritten query.
    is_in_scope: bool
    rejection_reason: str = Field(default="", max_length=300)
    normalized_topic: str = Field(default="", max_length=300)
    intent: Literal["current", "historical"] = "current"
    primary_query: str = Field(default="", max_length=300)
    follow_up_queries: list[str] = Field(default_factory=list, max_length=2)
    search_days: int | None = Field(default=7, ge=1, le=30)
    disambiguation_notes: str = Field(default="", max_length=500)
    rationale: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def normalize_plan(self) -> "NewsQueryPlan":
        self.normalized_topic = " ".join(self.normalized_topic.split()).strip()
        self.primary_query = " ".join(self.primary_query.split()).strip()
        self.rejection_reason = " ".join(self.rejection_reason.split()).strip()
        self.rationale = " ".join(self.rationale.split()).strip()

        if not self.is_in_scope:
            # Rejected queries do not need a fabricated search plan.
            self.follow_up_queries = []
            self.search_days = None
            self.primary_query = ""
            self.normalized_topic = ""
            if not self.rejection_reason:
                self.rejection_reason = (
                    "Newsroom AI only researches current or historical news."
                )
            if not self.rationale:
                self.rationale = "The request is outside news-research scope."
            return self

        if len(self.normalized_topic) < 2:
            raise ValueError("normalized_topic cannot be blank for in-scope queries.")
        if len(self.primary_query) < 2:
            raise ValueError("primary_query cannot be blank for in-scope queries.")
        if not self.rationale:
            raise ValueError("rationale cannot be blank for in-scope queries.")

        cleaned: list[str] = []
        seen = {self.primary_query.casefold()}
        for query in self.follow_up_queries:
            value = " ".join(query.split()).strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(value)
            if len(cleaned) == 2:
                break

        self.follow_up_queries = cleaned
        if self.intent == "historical":
            self.search_days = None
        elif self.search_days is None:
            self.search_days = 7
        return self
