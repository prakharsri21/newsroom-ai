
from langfuse import observe

from app.graph.fact_checker_agent import fact_checker_agent_node
from app.graph.state import NewsroomState


@observe(
    name="fact-checker-node",
    as_type="span",
    capture_output=False,
)
async def fact_checker_node(state: NewsroomState) -> dict:
    result = await fact_checker_agent_node(state)

    result["fact_check_attempts"] = (
        state.get("fact_check_attempts", 0) + 1
    )

    return result
