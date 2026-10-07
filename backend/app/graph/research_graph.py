from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.graph.researcher_agent import researcher_agent_node
from app.graph.state import MAX_ITERATIONS, NewsroomState
from app.graph.tools.research_tools import search_news


tools_node = ToolNode([search_news])


def route_after_researcher(state: NewsroomState) -> str:
    """
    Decide whether the Researcher should use a tool
    or finish the research phase.
    """
    iteration = state.get("iteration", 0)

    if iteration >= MAX_ITERATIONS:
        return "complete"

    messages = state.get("messages", [])

    if not messages:
        return "complete"

    last_message = messages[-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "complete"


workflow = StateGraph(NewsroomState)

workflow.add_node("researcher", researcher_agent_node)
workflow.add_node("tools", tools_node)

workflow.add_edge(START, "researcher")

workflow.add_conditional_edges(
    "researcher",
    route_after_researcher,
    {
        "tools": "tools",
        "complete": END,
    },
)

workflow.add_edge("tools", "researcher")

research_graph = workflow.compile()