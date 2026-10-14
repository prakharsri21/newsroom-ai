
from langfuse import observe

from app.services.observability import record_current_span

from app.graph.fact_checker_agent import fact_checker_agent_node
from app.graph.state import NewsroomState


@observe(
    name="fact-checker-node",
    as_type="span",
    capture_input=False,
    capture_output=False,
)
async def fact_checker_node(state: NewsroomState) -> dict:
    result = await fact_checker_agent_node(state)

    result["fact_check_attempts"] = (
        state.get("fact_check_attempts", 0) + 1
    )

    reviews = result.get("claim_verifications", [])
    verdicts = [review.get("verdict", "UNKNOWN") for review in reviews]
    record_current_span(
        metadata={
            "attempt": str(result["fact_check_attempts"]),
            "claim_count": str(len(reviews)),
            "supported_claim_count": str(verdicts.count("SUPPORTED")),
            "non_supported_claim_count": str(
                sum(verdict != "SUPPORTED" for verdict in verdicts)
            ),
            "fact_check_passed": str(
                bool(result.get("fact_check_passed"))
            ).lower(),
            "next_action": str(result.get("next_action", "none")),
            "follow_up_research_requested": str(
                bool(result.get("research_follow_up_query"))
            ).lower(),
        }
    )

    return result
