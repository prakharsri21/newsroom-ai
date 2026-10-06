from typing import TypedDict

MAX_ITERATIONS = 3

class NewsroomState(TypedDict, total=False):
    # Original user request
    query: str

    # Research outputs
    source_ids: list[int]
    research_complete: bool

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
    