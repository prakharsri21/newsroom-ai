import pytest
from pydantic import ValidationError

from app.schemas.news_generation import (
    GenerateNewsRequest,
    NewsGenerationResponse,
    NewsSourceResponse,
)


def test_generation_request_defaults_category():
    request = GenerateNewsRequest(
        query="Latest RBI monetary policy"
    )

    assert request.query == "Latest RBI monetary policy"
    assert request.category == "General"


def test_generation_request_rejects_blank_query():
    with pytest.raises(ValidationError):
        GenerateNewsRequest(query="   ")


def test_source_response_preserves_evidence_reference():
    source = NewsSourceResponse(
        evidence_ref="E1",
        source_id=42,
        title="RBI policy announcement",
        publisher="RBI",
        url="https://rbi.org.in/example",
    )

    assert source.evidence_ref == "E1"
    assert source.source_id == 42


def test_generation_response_supports_unverified_result():
    response = NewsGenerationResponse(
        status="needs_review",
        query="Latest RBI monetary policy",
        headline="RBI policy decision",
        article="An article requiring further review.",
        research_complete=True,
        citation_validation_passed=True,
        fact_check_passed=False,
        fact_check_reason="A claim could not be confirmed.",
        message="The article requires further review.",
    )

    assert response.status == "needs_review"
    assert response.fact_check_passed is False
    assert response.sources == []
    assert response.claims == []