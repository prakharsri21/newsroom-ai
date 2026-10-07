from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ResearchDecision(BaseModel):
    action: Literal["search", "complete"] = Field(
        description="Whether to perform another search or finish research."
    )

    search_query: str | None = Field(
        default=None,
        description="The next web search query. Required when action is 'search'.",
    )

    rationale: str = Field(
        description="Brief explanation for why the researcher chose this action."
    )

    @model_validator(mode="after")
    def validate_search_query(self) -> "ResearchDecision":
        if self.action == "search" and not self.search_query:
            raise ValueError(
                "search_query is required when action is 'search'"
            )

        if self.action == "complete" and self.search_query is not None:
            raise ValueError(
                "search_query must be null when action is 'complete'"
            )

        return self