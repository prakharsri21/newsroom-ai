
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.news import generate_news_endpoint
from app.schemas.news_generation import (
    GenerateNewsRequest,
    NewsGenerationResponse,
)


def make_response():
    return NewsGenerationResponse(
        status="verified",
        query="Latest RBI monetary policy",
        story_id=10,
        article_id=20,
        headline="RBI Policy Decision",
        summary="A summary grounded in research.",
        article="RBI Policy Decision\n\nA summary grounded in research.",
        research_complete=True,
        citation_validation_passed=True,
        fact_check_passed=True,
        fact_check_reason="All claims were supported.",
        message="Research, citation validation, and claim verification passed.",
    )


@pytest.mark.anyio
async def test_generate_endpoint_returns_service_result():
    db = object()
    expected = make_response()

    with patch(
        "app.api.news.generate_news_service",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock_generate:
        result = await generate_news_endpoint(
            GenerateNewsRequest(
                query="Latest RBI monetary policy",
                category="National",
            ),
            db=db,
        )

    assert result.status == "verified"
    assert result.story_id == 10
    assert result.article_id == 20

    mock_generate.assert_awaited_once_with(
        db,
        query="Latest RBI monetary policy",
        category="National",
    )


@pytest.mark.anyio
async def test_generate_endpoint_hides_internal_errors():
    with patch(
        "app.api.news.generate_news_service",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Sensitive internal details"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await generate_news_endpoint(
                GenerateNewsRequest(
                    query="Latest RBI monetary policy",
                ),
                db=object(),
            )

    assert exc_info.value.status_code == 500
    assert "Sensitive internal details" not in exc_info.value.detail
