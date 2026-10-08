from app.graph.citation import (
    build_evidence_registry,
    validate_article_citations,
)
from app.schemas.editor import (
    ArticleClaim,
    ArticleDraft,
    ArticleParagraph,
)


def make_evidence():
    return [
        {
            "url": "https://example.com/one",
            "title": "Source One",
            "publisher": "Example",
            "source_type": "news",
            "excerpt": "Evidence one.",
            "relevance_score": 0.9,
            "published_at": "2026-10-07T10:00:00Z",
            "authority_tier": "reputable_secondary",
            "authority_score": 0.8,
            "freshness_score": 1.0,
        },
        {
            "url": "https://example.com/two",
            "title": "Source Two",
            "publisher": "Example",
            "source_type": "news",
            "excerpt": "Evidence two.",
            "relevance_score": 0.85,
            "published_at": "2026-10-07T11:00:00Z",
            "authority_tier": "reputable_secondary",
            "authority_score": 0.8,
            "freshness_score": 1.0,
        },
    ]


def make_valid_draft():
    return ArticleDraft(
        headline="RBI Changes Policy",
        headline_evidence_refs=["E1"],
        summary="The RBI changed its policy stance.",
        summary_evidence_refs=["E1"],
        paragraphs=[
            ArticleParagraph(
                text="The RBI announced a policy change.",
                evidence_refs=["E1"],
            )
        ],
        claims=[
            ArticleClaim(
                claim_text="The RBI announced a policy change.",
                evidence_refs=["E1"],
            )
        ],
    )


def test_build_evidence_registry():
    registry = build_evidence_registry(make_evidence())

    assert list(registry.keys()) == ["E1", "E2"]
    assert registry["E1"]["title"] == "Source One"


def test_valid_article_citations_pass():
    draft = make_valid_draft()
    registry = build_evidence_registry(make_evidence())

    errors = validate_article_citations(draft, registry)

    assert errors == []


def test_unknown_evidence_reference_fails():
    draft = make_valid_draft()
    draft.claims[0].evidence_refs = ["E99"]

    registry = build_evidence_registry(make_evidence())

    errors = validate_article_citations(draft, registry)

    assert len(errors) == 1
    assert "E99" in errors[0]


def test_missing_paragraph_evidence_fails():
    draft = make_valid_draft()
    draft.paragraphs[0].evidence_refs = []

    registry = build_evidence_registry(make_evidence())

    errors = validate_article_citations(draft, registry)

    assert "paragraph[0] has no evidence references." in errors