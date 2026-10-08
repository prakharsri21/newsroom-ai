from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

MAX_ITERATIONS = 3


class ResearchEvidence(TypedDict, total=False):
    source_id: int
    url: str
    title: str
    publisher: str
    source_type: str
    excerpt: str
    relevance_score: float
    published_at: str

    # Evidence quality signals
    authority_tier: str
    authority_score: float
    freshness_score: float


class NewsroomState(TypedDict, total=False):
    # Original user request
    query: str

    # Research inputs / outputs
    research_queries: list[str]
    source_ids: list[int]
    research_evidence: list[ResearchEvidence]
    research_summary: str
    research_complete: bool
    research_failure_reason: str

    article_headline: str
    article_summary: str
    article_paragraphs: list[dict[str, object]]
    article_claims: list[dict[str, object]]
    citation_validation_passed: bool
    citation_validation_errors: list[str]

    # Editorial output
    article_draft: str
    article_version: int

    # Fact-check output
    fact_check_passed: bool
    fact_check_reason: str

    # Router decision
    next_action: str

    # Loop protection
    iteration: int

    messages: Annotated[list[AnyMessage], add_messages()]