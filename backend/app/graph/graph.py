from langgraph.graph import END, START, StateGraph
from langfuse import observe

from app.graph.nodes import (
    editor_node,
    fact_checker_node,
    researcher_node,
)
from app.graph.state import MAX_ITERATIONS, NewsroomState


def route_after_fact_check(state: NewsroomState) -> str:
    iteration = state.get("iteration", 0)

    if iteration >= MAX_ITERATIONS:
        return END

    action = state.get("next_action", "done")

    if action == "research":
        return "researcher"

    if action == "edit":
        return "editor"

    return END

workflow = StateGraph(NewsroomState)

workflow.add_node("researcher", researcher_node)
workflow.add_node("editor", editor_node)
workflow.add_node("fact_checker", fact_checker_node)

workflow.add_edge(START, "researcher")
workflow.add_edge("researcher", "editor")
workflow.add_edge("editor", "fact_checker")

workflow.add_conditional_edges(
    "fact_checker",
    route_after_fact_check,
    {
        "researcher": "researcher",
        "editor": "editor",
        END: END,
    },
)

newsroom_graph = workflow.compile()

@observe(
    name="newsroom-graph",
    as_type="span",
    capture_output=False,
)
def run_newsroom_graph(
    state: NewsroomState,
) -> NewsroomState:
    return newsroom_graph.invoke(state)