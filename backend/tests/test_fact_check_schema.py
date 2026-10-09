
import pytest
from pydantic import ValidationError

from app.schemas.fact_check import (
    ClaimVerification,
    FactCheckReport,
)


def test_supported_claim_requires_supporting_evidence():
    review = ClaimVerification(
        claim_index=0,
        claim_text="The repo rate increased to 5.50%.",
        verdict="SUPPORTED",
        confidence=0.95,
        rationale="The cited source reports the rate increase.",
        supporting_evidence_refs=["E1"],
    )

    assert review.verdict == "SUPPORTED"
    assert review.supporting_evidence_refs == ["E1"]


def test_supported_claim_without_evidence_is_rejected():
    with pytest.raises(ValidationError):
        ClaimVerification(
            claim_index=0,
            claim_text="The repo rate increased to 5.50%.",
            verdict="SUPPORTED",
            confidence=0.95,
            rationale="The claim appears correct.",
        )


def test_contradicted_claim_requires_contradicting_evidence():
    with pytest.raises(ValidationError):
        ClaimVerification(
            claim_index=0,
            claim_text="The repo rate was unchanged.",
            verdict="CONTRADICTED",
            confidence=0.9,
            rationale="The evidence reports an increase.",
        )


def test_unverifiable_claim_can_have_no_supporting_evidence():
    review = ClaimVerification(
        claim_index=1,
        claim_text="The decision surprised every analyst.",
        verdict="UNVERIFIABLE",
        confidence=0.85,
        rationale="The available evidence does not establish this.",
        reviewed_evidence_refs=["E1"],
    )

    assert review.verdict == "UNVERIFIABLE"
    assert review.supporting_evidence_refs == []


def test_confidence_must_be_between_zero_and_one():
    with pytest.raises(ValidationError):
        ClaimVerification(
            claim_index=0,
            claim_text="Example claim",
            verdict="UNVERIFIABLE",
            confidence=1.5,
            rationale="Insufficient evidence.",
        )


def test_claim_index_cannot_be_negative():
    with pytest.raises(ValidationError):
        ClaimVerification(
            claim_index=-1,
            claim_text="Example claim",
            verdict="UNVERIFIABLE",
            confidence=0.5,
            rationale="Insufficient evidence.",
        )


def test_fact_check_report_requires_at_least_one_review():
    with pytest.raises(ValidationError):
        FactCheckReport(
            claim_reviews=[],
            overall_summary="No claims were checked.",
        )
