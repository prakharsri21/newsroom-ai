
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.graph.graph import newsroom_graph


CLAIM_TEXT = "The RBI announced its latest monetary policy decision."


def make_research_result(query: str = "") -> dict:
    return {
        "research_complete": True,
        "research_summary": CLAIM_TEXT,
        "research_evidence": [
            {
                "url": "https://example.com/rbi",
                "title": "RBI Monetary Policy Decision",
                "publisher": "Example News",
                "source_type": "news",
                "excerpt": CLAIM_TEXT,
                "relevance_score": 0.95,
                "published_at": "2026-10-07T10:00:00Z",
                "authority_tier": "reputable_secondary",
                "authority_score": 0.8,
                "freshness_score": 1.0,
            }
        ],
        "source_ids": [],
        "iteration": 0,
    }


def make_editor_draft():
    return SimpleNamespace(
        headline="RBI Announces Monetary Policy Decision",
        headline_evidence_refs=["E1"],
        summary=CLAIM_TEXT,
        summary_evidence_refs=["E1"],
        paragraphs=[
            SimpleNamespace(
                text=CLAIM_TEXT,
                evidence_refs=["E1"],
                model_dump=lambda: {
                    "text": CLAIM_TEXT,
                    "evidence_refs": ["E1"],
                },
            )
        ],
        claims=[
            SimpleNamespace(
                claim_text=CLAIM_TEXT,
                evidence_refs=["E1"],
                model_dump=lambda: {
                    "claim_text": CLAIM_TEXT,
                    "evidence_refs": ["E1"],
                },
            )
        ],
    )


def make_fact_check_result(
    *,
    passed: bool = True,
    next_action: str = "done",
    verdict: str = "SUPPORTED",
    research_follow_up_query: str = "",
) -> dict:
    review = {
        "claim_index": 0,
        "claim_text": CLAIM_TEXT,
        "verdict": verdict,
        "confidence": 0.95,
        "rationale": "Test verdict based on the mocked evidence.",
        "supporting_evidence_refs": (
            ["E1"] if verdict == "SUPPORTED" else []
        ),
        "contradicting_evidence_refs": (
            ["E1"] if verdict == "CONTRADICTED" else []
        ),
        "reviewed_evidence_refs": ["E1"],
    }

    return {
        "fact_check_report": {
            "claim_reviews": [review],
            "overall_summary": "Mock fact-check report.",
        },
        "claim_verifications": [review],
        "fact_check_passed": passed,
        "fact_check_reason": "Mock fact-check result.",
        "next_action": next_action,
        "research_follow_up_query": research_follow_up_query,
    }


async def run_graph_with_mocks(
    query: str,
    *,
    fact_check_results: list[dict] | None = None,
    research_results: list[dict] | None = None,
    return_mocks: bool = False,
):
    research_result = make_research_result(query)

    fake_editor_llm = SimpleNamespace(
        ainvoke=AsyncMock(return_value=make_editor_draft())
    )

    checker_results = (
        fact_check_results
        if fact_check_results is not None
        else [make_fact_check_result()]
    )
    research_outputs = (
        research_results
        if research_results is not None
        else [research_result]
    )

    fact_checker_mock = AsyncMock(side_effect=checker_results)
    research_mock = AsyncMock(side_effect=research_outputs)

    with (
        patch(
            "app.graph.research_graph.research_graph.ainvoke",
            new=research_mock,
        ),
        patch(
            "app.graph.editor_agent.editor_llm",
            fake_editor_llm,
        ),
        patch(
            "app.graph.editor_agent.get_client",
        ) as mock_get_client,
        patch(
            "app.graph.fact_checker.fact_checker_agent_node",
            new=fact_checker_mock,
        ),
    ):
        mock_get_client.return_value.update_current_span = (
            lambda **kwargs: None
        )

        result = await newsroom_graph.ainvoke(
            {
                "query": query,
                "iteration": 0,
                "article_version": 0,
            }
        )

    if return_mocks:
        return (
            result,
            fact_checker_mock,
            research_mock,
            fake_editor_llm,
        )

    return result


@pytest.mark.anyio
async def test_newsroom_graph_completes():
    result, checker, _, _ = await run_graph_with_mocks(
        "test newsroom workflow",
        return_mocks=True,
    )

    assert result["research_complete"] is True
    assert result["article_version"] == 1
    assert result["citation_validation_passed"] is True
    assert result["fact_check_passed"] is True
    assert result["fact_check_attempts"] == 1
    assert result["article_draft"]
    assert checker.await_count == 1


@pytest.mark.anyio
async def test_graph_state_contains_expected_fields():
    result = await run_graph_with_mocks("test state")

    assert result["query"] == "test state"
    assert "article_draft" in result
    assert "article_headline" in result
    assert "article_summary" in result
    assert "article_claims" in result
    assert "citation_validation_errors" in result
    assert result["iteration"] == 0


@pytest.mark.anyio
async def test_newsroom_graph_does_not_edit_incomplete_research():
    incomplete_research = {
        "research_complete": False,
        "research_failure_reason": (
            "Research reached the maximum iteration limit "
            "without sufficient evidence."
        ),
        "research_summary": (
            "The available evidence was insufficient."
        ),
        "research_evidence": [],
        "source_ids": [],
        "iteration": 3,
    }

    with patch(
        "app.graph.research_graph.research_graph.ainvoke",
        new=AsyncMock(return_value=incomplete_research),
    ):
        result = await newsroom_graph.ainvoke(
            {
                "query": "test incomplete research",
                "iteration": 0,
                "article_version": 0,
            }
        )

    assert result["research_complete"] is False
    assert result["research_failure_reason"]
    assert "article_headline" not in result


@pytest.mark.anyio
async def test_failed_claim_returns_to_editor():
    failed_check = make_fact_check_result(
        passed=False,
        next_action="editor",
        verdict="CONTRADICTED",
    )

    result, checker, _, editor_llm = await run_graph_with_mocks(
        "test rewrite routing",
        fact_check_results=[
            failed_check,
            make_fact_check_result(),
        ],
        return_mocks=True,
    )

    assert checker.await_count == 2
    assert editor_llm.ainvoke.await_count == 2
    assert result["fact_check_passed"] is True
    assert result["fact_check_attempts"] == 2


@pytest.mark.anyio
async def test_unverifiable_claim_triggers_follow_up_research():
    unresolved_check = make_fact_check_result(
        passed=False,
        next_action="researcher",
        verdict="UNVERIFIABLE",
        research_follow_up_query=(
            "Find recent authoritative evidence for the RBI decision."
        ),
    )

    result, checker, research, _ = await run_graph_with_mocks(
        "test follow-up research",
        fact_check_results=[
            unresolved_check,
            make_fact_check_result(),
        ],
        research_results=[
            make_research_result(),
            make_research_result(),
        ],
        return_mocks=True,
    )

    assert checker.await_count == 2
    assert research.await_count == 2
    assert result["active_research_query"] == (
        "Find recent authoritative evidence for the RBI decision."
    )
    assert result["fact_check_passed"] is True
    assert result["fact_check_attempts"] == 2


@pytest.mark.anyio
async def test_fact_check_stops_after_maximum_attempts():
    failed_check = make_fact_check_result(
        passed=False,
        next_action="editor",
        verdict="CONTRADICTED",
    )

    result, checker, _, editor_llm = await run_graph_with_mocks(
        "test maximum attempts",
        fact_check_results=[
            failed_check,
            failed_check,
            failed_check,
        ],
        return_mocks=True,
    )

    assert checker.await_count == 3
    assert editor_llm.ainvoke.await_count == 3
    assert result["fact_check_attempts"] == 3
    assert result["fact_check_passed"] is False
