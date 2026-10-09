
from unittest.mock import MagicMock

import pytest

from app.graph import fact_checker_agent
from app.graph.citation import build_evidence_registry
from app.schemas.fact_check import ClaimVerification, FactCheckReport


CLAIM_TEXT = "The repo rate increased to 5.50%."


def make_state():
    return {
        "query": "Latest RBI monetary policy decision",
        "article_headline": "RBI raises the repo rate",
        "article_summary": "The RBI increased its repo rate.",
        "article_paragraphs": [
            {"text": "The repo rate increased to 5.50%."}
        ],
        "article_claims": [
            {
                "claim_text": CLAIM_TEXT,
                "evidence_refs": ["E1"],
            }
        ],
        "research_evidence": [
            {
                "title": "RBI policy announcement",
                "publisher": "RBI",
                "published_at": "2026-10-07",
                "url": "https://rbi.org.in/example",
                "excerpt": "The policy rate was increased to 5.50%.",
                "authority_tier": "primary",
            }
        ],
    }


def make_report(verdict="SUPPORTED", evidence_ref="E1"):
    supporting_refs = (
        [evidence_ref] if verdict == "SUPPORTED" else []
    )
    contradicting_refs = (
        [evidence_ref] if verdict == "CONTRADICTED" else []
    )

    return FactCheckReport(
        claim_reviews=[
            ClaimVerification(
                claim_index=0,
                claim_text=CLAIM_TEXT,
                verdict=verdict,
                confidence=0.95,
                rationale="The supplied evidence was assessed against the claim.",
                supporting_evidence_refs=supporting_refs,
                contradicting_evidence_refs=contradicting_refs,
                reviewed_evidence_refs=["E1"]
                + (
                    [evidence_ref]
                    if evidence_ref != "E1"
                    else []
                ),
            )
        ],
        overall_summary="The claim was reviewed against the supplied evidence.",
    )


class FakeLLM:
    def __init__(self, report):
        self.report = report

    async def ainvoke(self, messages):
        return self.report


@pytest.fixture
def mock_langfuse(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(
        fact_checker_agent,
        "get_client",
        lambda: client,
    )
    return client


@pytest.mark.anyio
async def test_supported_claim_passes(
    monkeypatch,
    mock_langfuse,
):
    monkeypatch.setattr(
        fact_checker_agent,
        "fact_checker_llm",
        FakeLLM(make_report()),
    )

    result = await fact_checker_agent.fact_checker_agent_node(
        make_state()
    )

    assert result["fact_check_passed"] is True
    assert result["next_action"] == "done"
    assert result["claim_verifications"][0]["verdict"] == "SUPPORTED"
    mock_langfuse.update_current_span.assert_called_once()


@pytest.mark.anyio
async def test_unverifiable_claim_routes_to_researcher(
    monkeypatch,
    mock_langfuse,
):
    monkeypatch.setattr(
        fact_checker_agent,
        "fact_checker_llm",
        FakeLLM(make_report("UNVERIFIABLE")),
    )

    result = await fact_checker_agent.fact_checker_agent_node(
        make_state()
    )

    assert result["fact_check_passed"] is False
    assert result["next_action"] == "researcher"


@pytest.mark.anyio
async def test_unknown_evidence_reference_is_rejected(
    monkeypatch,
    mock_langfuse,
):
    monkeypatch.setattr(
        fact_checker_agent,
        "fact_checker_llm",
        FakeLLM(make_report(evidence_ref="E99")),
    )

    with pytest.raises(ValueError, match="unknown evidence"):
        await fact_checker_agent.fact_checker_agent_node(
            make_state()
        )


@pytest.mark.anyio
async def test_missing_claim_fails_closed(
    monkeypatch,
    mock_langfuse,
):
    state = make_state()
    state["article_claims"] = []

    with pytest.raises(ValueError, match="without article claims"):
        await fact_checker_agent.fact_checker_agent_node(state)



def test_missing_claim_review_is_detected():
    state = make_state()
    registry = build_evidence_registry(
        state["research_evidence"]
    )

    report = FactCheckReport.model_construct(
        claim_reviews=[],
        overall_summary="No claims were reviewed.",
    )

    errors = fact_checker_agent.validate_fact_check_report(
        report,
        state["article_claims"],
        registry,
    )

    assert "Claim 0 has no fact-check review." in errors


    # FactCheckReport requires at least one review, so its schema
    # rejects this before the custom coverage validator can run.
    assert registry == {"E1": state["research_evidence"][0]}
