
from typing import Literal

from pydantic import BaseModel, Field, model_validator


FactCheckVerdict = Literal[
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "CONTRADICTED",
    "UNVERIFIABLE",
    "OUTDATED",
]


class ClaimVerification(BaseModel):
    claim_index: int = Field(ge=0)
    claim_text: str = Field(min_length=1)

    verdict: FactCheckVerdict
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)

    # Evidence that supports or contradicts this claim.
    supporting_evidence_refs: list[str] = Field(default_factory=list)
    contradicting_evidence_refs: list[str] = Field(default_factory=list)

    # All evidence reviewed, including inconclusive sources.
    reviewed_evidence_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_verdict_evidence(self):
        if (
            self.verdict == "SUPPORTED"
            and not self.supporting_evidence_refs
        ):
            raise ValueError(
                "A supported claim must have supporting evidence."
            )

        if (
            self.verdict == "CONTRADICTED"
            and not self.contradicting_evidence_refs
        ):
            raise ValueError(
                "A contradicted claim must have contradicting evidence."
            )

        if (
            self.verdict == "PARTIALLY_SUPPORTED"
            and not (
                self.supporting_evidence_refs
                or self.contradicting_evidence_refs
            )
        ):
            raise ValueError(
                "A partially supported claim must reference relevant evidence."
            )

        return self


class FactCheckReport(BaseModel):
    claim_reviews: list[ClaimVerification] = Field(min_length=1)
    overall_summary: str = Field(min_length=1)
