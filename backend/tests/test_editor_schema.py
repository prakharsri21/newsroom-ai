import pytest
from pydantic import ValidationError

from app.schemas.editor import ArticleClaim, ArticleDraft, ArticleParagraph


def test_article_claim_requires_evidence():
    with pytest.raises(ValidationError):
        ArticleClaim(
            claim_text="RBI raised the repo rate.",
            evidence_refs=[],
        )


def test_article_claim_accepts_evidence():
    claim = ArticleClaim(
        claim_text="RBI raised the repo rate.",
        evidence_refs=["E1"],
    )

    assert claim.evidence_refs == ["E1"]


def test_article_draft_accepts_structured_content():
    draft = ArticleDraft(
        headline="RBI Raises Repo Rate",
        headline_evidence_refs=["E1"],
        summary="The RBI announced a change in monetary policy.",
        summary_evidence_refs=["E1"],
        paragraphs=[
            ArticleParagraph(
                text="The RBI raised the repo rate.",
                evidence_refs=["E1"],
            )
        ],
        claims=[
            ArticleClaim(
                claim_text="The RBI raised the repo rate.",
                evidence_refs=["E1"],
            )
        ],
    )

    assert draft.headline == "RBI Raises Repo Rate"
    assert draft.headline_evidence_refs == ["E1"]
    assert len(draft.paragraphs) == 1
    assert len(draft.claims) == 1