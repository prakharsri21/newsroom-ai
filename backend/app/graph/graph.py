from langfuse import observe
from langgraph.graph import END, START, StateGraph

from app.graph.editor import editor_node
from app.graph.research_graph import research_graph
from app.graph.state import NewsroomState


def route_after_research(state: NewsroomState) -> str:
    """
    Decide whether the completed research is sufficient
    to proceed to the Editor.
    """
    if state.get("research_complete", False):
        return "editor"

    return END


workflow = StateGraph(NewsroomState)

workflow.add_node("research", research_graph)
workflow.add_node("editor", editor_node)

workflow.add_edge(START, "research")

workflow.add_conditional_edges(
    "research",
    route_after_research,
    {
        "editor": "editor",
        END: END,
    },
)

workflow.add_edge("editor", END)

newsroom_graph = workflow.compile()


@observe(
    name="newsroom-graph",
    as_type="span",
    capture_output=False,
)
async def run_newsroom_graph(
    state: NewsroomState,
) -> NewsroomState:
    return await newsroom_graph.ainvoke(state)