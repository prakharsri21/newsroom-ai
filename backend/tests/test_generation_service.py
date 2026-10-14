
from unittest.mock import AsyncMock, patch

import pytest

from app.models.article import Article
from app.models.claim import Claim
from app.models.claim_source import ClaimSource
from app.models.fact_check import FactCheck
from app.models.news import NewsStory
from app.models.story_source import StorySource
from app.schemas.query_plan import NewsQueryPlan
from app.services.generation import generate_news


def _fake_query_plan():
    return NewsQueryPlan(
        is_in_scope=True,
        normalized_topic="Latest RBI monetary policy",
        intent="current",
        primary_query="RBI monetary policy",
        follow_up_queries=[
            "RBI monetary policy recent developments",
            "RBI official response",
        ],
        search_days=7,
        disambiguation_notes="",
        rationale="Test plan.",
    )


@pytest.fixture(autouse=True)
def mock_query_planner():
    with patch(
        "app.services.generation.build_news_query_plan",
        new_callable=AsyncMock,
        return_value=_fake_query_plan(),
    ):
        yield


CLAIM_TEXT = "The RBI announced its latest monetary policy decision."


class FakeSession:
    """Small async-session stand-in for service-level tests."""

    def __init__(self):
        self.items = []
        self.next_id = 1
        self.committed = False
        self.rolled_back = False

    def add(self, item):
        self.items.append(item)

    async def flush(self):
        for item in self.items:
            if hasattr(item, "id") and item.id is None:
                item.id = self.next_id
                self.next_id += 1

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


def complete_graph_result(*, passed=True):
    verdict = "SUPPORTED" if passed else "CONTRADICTED"

    review = {
        "claim_index": 0,
        "claim_text": CLAIM_TEXT,
        "verdict": verdict,
        "confidence": 0.95,
        "rationale": "The claim was checked against the provided evidence.",
        "supporting_evidence_refs": ["E1"] if passed else [],
        "contradicting_evidence_refs": [] if passed else ["E1"],
        "reviewed_evidence_refs": ["E1"],
    }

    return {
        "query": "Latest RBI monetary policy",
        "research_complete": True,
        "research_evidence": [
            {
                "url": "https://example.com/rbi",
                "title": "RBI policy announcement",
                "publisher": "Example News",
                "excerpt": "The RBI announced its latest monetary policy decision.",
                "published_at": "2026-10-09",
                "authority_tier": "reputable_secondary",
            }
        ],
        "article_headline": "RBI Announces Monetary Policy Decision",
        "article_summary": CLAIM_TEXT,
        "article_draft": f"RBI Announces Monetary Policy Decision\n\n{CLAIM_TEXT}",
        "article_version": 1,
        "article_claims": [
            {
                "claim_text": CLAIM_TEXT,
                "evidence_refs": ["E1"],
            }
        ],
        "citation_validation_passed": True,
        "citation_validation_errors": [],
        "claim_verifications": [review],
        "fact_check_passed": passed,
        "fact_check_reason": review["rationale"],
    }


@pytest.mark.anyio
async def test_out_of_scope_request_stops_before_research_or_persistence():
    db = FakeSession()
    rejected_plan = NewsQueryPlan(
        is_in_scope=False,
        rejection_reason=(
            "Newsroom AI researches news only. Try searching for a news "
            "development or event instead."
        ),
        rationale="The request asks for website-development assistance.",
    )

    with (
        patch(
            "app.services.generation.build_news_query_plan",
            new_callable=AsyncMock,
            return_value=rejected_plan,
        ) as planner,
        patch(
            "app.services.generation.run_newsroom_graph",
            new_callable=AsyncMock,
        ) as graph,
        patch(
            "app.services.generation.persist_research_evidence",
            new_callable=AsyncMock,
        ) as persist_evidence,
        patch("app.services.generation.record_current_span") as record_span,
    ):
        response = await generate_news(
            db,
            query="Can you help me build a website?",
        )

    planner.assert_awaited_once()
    graph.assert_not_awaited()
    persist_evidence.assert_not_awaited()
    assert response.status == "out_of_scope"
    assert response.research_complete is False
    assert response.article is None
    assert response.story_id is None
    assert response.article_id is None
    assert response.sources == []
    assert response.claims == []
    assert "news only" in response.message.lower()
    assert db.items == []
    assert db.committed is False

    metadata = record_span.call_args.kwargs["metadata"]
    assert metadata["query_plan_scope"] == "out_of_scope"
    assert metadata["status"] == "out_of_scope"
    assert "graph_ms" not in metadata


@pytest.mark.anyio
async def test_generate_news_persists_verified_article():
    db = FakeSession()
    graph_result = complete_graph_result()

    with (
        patch(
            "app.services.generation.run_newsroom_graph",
            new_callable=AsyncMock,
            return_value=graph_result,
        ),
        patch(
            "app.services.generation.persist_research_evidence",
            new_callable=AsyncMock,
            return_value=(
                [42],
                [
                    {
                        **graph_result["research_evidence"][0],
                        "source_id": 42,
                    }
                ],
            ),
        ),
        patch("app.services.generation.record_current_span") as record_span,
    ):
        response = await generate_news(
            db,
            query="Latest RBI monetary policy",
            category="National",
        )

    assert response.status == "verified"
    assert response.research_complete is True
    assert response.fact_check_passed is True
    assert response.story_id is not None
    assert response.article_id is not None
    assert response.sources[0].evidence_ref == "E1"
    assert response.sources[0].source_id == 42
    assert db.committed is True
    assert any(isinstance(item, NewsStory) for item in db.items)
    assert any(isinstance(item, Article) for item in db.items)
    assert any(isinstance(item, Claim) for item in db.items)
    assert any(isinstance(item, FactCheck) for item in db.items)
    assert any(isinstance(item, ClaimSource) for item in db.items)
    assert any(isinstance(item, StorySource) for item in db.items)

    metrics = record_span.call_args.kwargs["metadata"]
    assert metrics["pipeline"] == "news_generation"
    assert metrics["status"] == "verified"
    assert metrics["research_complete"] == "true"
    assert metrics["evidence_count"] == "1"
    assert float(metrics["total_pipeline_ms"]) >= 0
    assert "graph_ms" in metrics


@pytest.mark.anyio
async def test_incomplete_research_does_not_create_article():
    db = FakeSession()

    incomplete_result = {
        "query": "Latest RBI monetary policy",
        "research_complete": False,
        "research_failure_reason": "Not enough reliable evidence.",
        "research_evidence": [],
        "iteration": 3,
    }

    with patch(
        "app.services.generation.run_newsroom_graph",
        new_callable=AsyncMock,
        return_value=incomplete_result,
    ):
        response = await generate_news(
            db,
            query="Latest RBI monetary policy",
        )

    assert response.status == "research_incomplete"
    assert response.article is None
    assert response.story_id is None
    assert response.article_id is None
    assert response.research_failure_reason == (
        "Not enough reliable evidence."
    )
    assert not any(isinstance(item, Article) for item in db.items)
    assert not any(isinstance(item, NewsStory) for item in db.items)


@pytest.mark.anyio
async def test_contradicted_claim_is_not_marked_verified():
    db = FakeSession()
    graph_result = complete_graph_result(passed=False)

    with (
        patch(
            "app.services.generation.run_newsroom_graph",
            new_callable=AsyncMock,
            return_value=graph_result,
        ),
        patch(
            "app.services.generation.persist_research_evidence",
            new_callable=AsyncMock,
            return_value=(
                [42],
                [
                    {
                        **graph_result["research_evidence"][0],
                        "source_id": 42,
                    }
                ],
            ),
        ),
    ):
        response = await generate_news(
            db,
            query="Latest RBI monetary policy",
        )

    assert response.status == "needs_review"
    assert response.fact_check_passed is False
    assert response.claims[0].verdict == "CONTRADICTED"

    stored_claims = [
        item for item in db.items if isinstance(item, Claim)
    ]
    assert stored_claims[0].status == "CONTRADICTED"
