import pytest
from pydantic import ValidationError

from app.schemas.research import ResearchDecision


def test_search_decision_requires_query():
    decision = ResearchDecision(
        action="search",
        search_query="RBI repo rate October 2026",
        rationale="Need more evidence.",
    )

    assert decision.action == "search"
    assert decision.search_query == "RBI repo rate October 2026"


def test_complete_decision_has_no_query():
    decision = ResearchDecision(
        action="complete",
        rationale="We have sufficient evidence.",
    )

    assert decision.action == "complete"
    assert decision.search_query is None


def test_search_without_query_is_invalid():
    with pytest.raises(ValidationError):
        ResearchDecision(
            action="search",
            rationale="Need more evidence.",
        )


def test_complete_with_query_is_invalid():
    with pytest.raises(ValidationError):
        ResearchDecision(
            action="complete",
            search_query="unnecessary query",
            rationale="We have enough evidence.",
        )