from typing import Literal

from pydantic import BaseModel, Field, model_validator


class NewsQueryPlan(BaseModel):
    """Validated search plan for a news query."""

    normalized_topic: str = Field(min_length=2, max_length=300)
    intent: Literal["current", "historical"] = "current"
    primary_query: str = Field(min_length=2, max_length=300)
    follow_up_queries: list[str] = Field(default_factory=list, max_length=2)
    search_days: int | None = Field(default=7, ge=1, le=30)
    disambiguation_notes: str = Field(default="", max_length=500)
    rationale: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def normalize_plan(self) -> "NewsQueryPlan":
        self.normalized_topic = " ".join(self.normalized_topic.split()).strip()
        self.primary_query = " ".join(self.primary_query.split()).strip()

        if not self.normalized_topic:
            raise ValueError("normalized_topic cannot be blank.")
        if not self.primary_query:
            raise ValueError("primary_query cannot be blank.")

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
