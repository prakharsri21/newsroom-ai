
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.citation import build_evidence_registry
from app.graph.graph import run_newsroom_graph
from app.models.article import Article
from app.models.claim import Claim
from app.models.claim_source import ClaimSource
from app.models.fact_check import FactCheck
from app.models.news import NewsStory
from app.models.story_source import StorySource
from app.schemas.fact_check import ClaimVerification
from app.schemas.news_generation import (
    NewsGenerationResponse,
    NewsSourceResponse,
)
from app.services.research_persistence import persist_research_evidence
from app.graph.query_planner import build_news_query_plan


def _as_string(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _generation_status(result: dict[str, Any]) -> str:
    if not result.get("research_complete", False):
        return "research_incomplete"

    if result.get("citation_validation_passed") is False:
        return "citation_validation_failed"

    if (
        result.get("citation_validation_passed") is True
        and result.get("fact_check_passed") is True
    ):
        return "verified"

    return "needs_review"


async def _persist_article_results(
    db: AsyncSession,
    *,
    result: dict[str, Any],
    category: str,
    evidence: list[dict[str, Any]],
) -> tuple[int | None, int | None]:
    """Persist an article, its claims, verdicts, and source relationships."""
    article_text = result.get("article_draft")
    if not article_text:
        return None, None

    story = NewsStory(
        headline=result.get("article_headline") or result["query"],
        summary=result.get("article_summary"),
        category=category,
    )
    db.add(story)
    await db.flush()

    # Connect the story to its deduplicated source records.
    source_ids = {
        item["source_id"]
        for item in evidence
        if item.get("source_id") is not None
    }
    for source_id in source_ids:
        db.add(
            StorySource(
                story_id=story.id,
                source_id=source_id,
            )
        )

    article = Article(
        story_id=story.id,
        content=article_text,
        version=max(1, int(result.get("article_version", 1) or 1)),
    )
    db.add(article)
    await db.flush()

    evidence_registry = build_evidence_registry(evidence)
    reviews = result.get("claim_verifications", [])
    reviews_by_index = {
        review["claim_index"]: review
        for review in reviews
    }

    for index, claim_data in enumerate(result.get("article_claims", [])):
        review = reviews_by_index.get(index)

        claim = Claim(
            article_id=article.id,
            claim_text=claim_data["claim_text"],
            status=review["verdict"] if review else "UNVERIFIED",
            confidence=review["confidence"] if review else None,
        )
        db.add(claim)
        await db.flush()

        # No fact-check record is created for an unchecked claim.
        if review is None:
            continue

        db.add(
            FactCheck(
                claim_id=claim.id,
                verdict=review["verdict"],
                confidence=review["confidence"],
                reason=review["rationale"],
            )
        )

        supporting = set(review.get("supporting_evidence_refs", []))
        contradicting = set(
            review.get("contradicting_evidence_refs", [])
        )
        reviewed = set(review.get("reviewed_evidence_refs", []))
        relationships: dict[int, tuple[str, str | None]] = {}

        for evidence_ref in reviewed | supporting | contradicting:
            item = evidence_registry.get(evidence_ref)
            if item is None or item.get("source_id") is None:
                continue

            source_id = item["source_id"]

            if (
                evidence_ref in supporting
                and evidence_ref in contradicting
            ):
                relationship = "CONFLICTING"
            elif evidence_ref in supporting:
                relationship = "SUPPORTS"
            elif evidence_ref in contradicting:
                relationship = "CONTRADICTS"
            else:
                relationship = "REVIEWED"

            excerpt = item.get("excerpt")
            previous = relationships.get(source_id)

            # The database relationship is unique per claim/source pair.
            # Preserve disagreement if different evidence entries map to
            # the same canonical source.
            if previous is not None and previous[0] != relationship:
                old_relationship = previous[0]
                if {
                    old_relationship,
                    relationship,
                } == {"SUPPORTS", "CONTRADICTS"}:
                    relationship = "CONFLICTING"
                elif old_relationship == "CONFLICTING":
                    relationship = old_relationship
                elif old_relationship != "REVIEWED":
                    relationship = old_relationship

            relationships[source_id] = (relationship, excerpt)

        for source_id, (relationship, excerpt) in relationships.items():
            db.add(
                ClaimSource(
                    claim_id=claim.id,
                    source_id=source_id,
                    relationship=relationship,
                    evidence_text=excerpt,
                )
            )

    await db.commit()
    return story.id, article.id


async def generate_news(
    db: AsyncSession,
    *,
    query: str,
    category: str = "General",
) -> NewsGenerationResponse:
    """Run the newsroom graph, persist its output, and build an API response."""
    query_plan = await build_news_query_plan(query)
    result = await run_newsroom_graph(
        {
            "query": query,
            "query_plan": query_plan.model_dump(mode="json"),
            "iteration": 0,
            "article_version": 0,
        }
    )

    raw_evidence = result.get("research_evidence", [])
    evidence = raw_evidence

    # Persist collected evidence even if research was incomplete,
    # so any sources returned to the client have stable database IDs.
    if raw_evidence:
        _, evidence = await persist_research_evidence(
            db,
            raw_evidence,
        )
        result["research_evidence"] = evidence

    story_id, article_id = await _persist_article_results(
        db,
        result=result,
        category=category,
        evidence=evidence,
    )

    sources = [
        NewsSourceResponse(
            evidence_ref=f"E{index}",
            source_id=item.get("source_id"),
            title=item.get("title") or "Untitled source",
            publisher=item.get("publisher"),
            url=str(item["url"]),
            published_at=_as_string(item.get("published_at")),
            authority_tier=item.get("authority_tier"),
        )
        for index, item in enumerate(evidence, start=1)
    ]

    claims = [
        ClaimVerification.model_validate(review)
        for review in result.get("claim_verifications", [])
    ]

    status = _generation_status(result)

    messages = {
        "verified": "Research, citation validation, and claim verification passed.",
        "needs_review": (
            "The article requires review because not all verification checks passed."
        ),
        "research_incomplete": (
            "Research was incomplete. No article is presented as verified."
        ),
        "citation_validation_failed": (
            "Article citations failed validation. The article requires review."
        ),
    }

    return NewsGenerationResponse(
        status=status,
        query=query,
        story_id=story_id,
        article_id=article_id,
        headline=result.get("article_headline"),
        summary=result.get("article_summary"),
        article=result.get("article_draft"),
        research_complete=result.get("research_complete", False),
        citation_validation_passed=result.get(
            "citation_validation_passed"
        ),
        fact_check_passed=result.get("fact_check_passed"),
        fact_check_reason=result.get("fact_check_reason"),
        sources=sources,
        claims=claims,
        message=messages[status],
        research_failure_reason=result.get("research_failure_reason"),
        citation_validation_errors=result.get("citation_validation_errors", []),
    )
