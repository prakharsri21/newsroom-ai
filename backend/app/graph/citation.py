from collections.abc import Sequence

from app.schemas.editor import ArticleDraft
from app.graph.state import ResearchEvidence


def build_evidence_registry(
    evidence: Sequence[ResearchEvidence],
) -> dict[str, ResearchEvidence]:
    """Assign stable E1, E2, ... references to research evidence."""
    return {
        f"E{index}": item
        for index, item in enumerate(evidence, start=1)
    }


def validate_article_citations(
    draft: ArticleDraft,
    evidence_registry: dict[str, ResearchEvidence],
) -> list[str]:
    """Return validation errors for invalid or missing evidence references."""
    errors: list[str] = []

    def validate_refs(location: str, refs: list[str]) -> None:
        if not refs:
            errors.append(f"{location} has no evidence references.")
            return

        for ref in refs:
            if ref not in evidence_registry:
                errors.append(
                    f"{location} references unknown evidence '{ref}'."
                )

    validate_refs(
        "headline",
        draft.headline_evidence_refs,
    )

    validate_refs(
        "summary",
        draft.summary_evidence_refs,
    )

    for index, paragraph in enumerate(draft.paragraphs):
        validate_refs(
            f"paragraph[{index}]",
            paragraph.evidence_refs,
        )

    for index, claim in enumerate(draft.claims):
        validate_refs(
            f"claim[{index}]",
            claim.evidence_refs,
        )

    return errors