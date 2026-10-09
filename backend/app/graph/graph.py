from langchain_core.messages import RemoveMessage
from langfuse import observe
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from app.graph.editor import editor_node
from app.graph.fact_checker import fact_checker_node
from app.graph.research_graph import research_graph
from app.graph.state import NewsroomState


MAX_FACT_CHECK_ATTEMPTS = 3


def route_after_research(state: NewsroomState) -> str:
    """Only edit an article when research completed successfully."""
    if state.get("research_complete", False):
        return "editor"

    return END


def route_after_editor(state: NewsroomState) -> str:
    """Only fact-check drafts whose citations passed structural validation."""
    if state.get("citation_validation_passed", False):
        return "fact_checker"

    return END


def route_after_fact_check(state: NewsroomState) -> str:
    """Route verified, failed, and unresolved claims safely."""
    if state.get("fact_check_passed", False):
        return END

    if state.get("fact_check_attempts", 0) >= MAX_FACT_CHECK_ATTEMPTS:
        return END

    action = state.get("next_action")

    if action == "editor":
        return "editor"

    if action == "researcher":
        return "prepare_research"

    return END


def prepare_follow_up_research(state: NewsroomState) -> dict:
    """Start a fresh research loop while retaining collected evidence."""
    follow_up_query = (
        state.get("research_follow_up_query", "").strip()
        or state["query"]
    )

    result = {
        "active_research_query": follow_up_query,
        "research_follow_up_query": "",
        "iteration": 0,
        "research_complete": False,
        "research_failure_reason": "",
        "research_summary": "",
        "article_headline": "",
        "article_summary": "",
        "article_paragraphs": [],
        "article_claims": [],
        "article_draft": "",
        "citation_validation_passed": False,
        "citation_validation_errors": [],
        "fact_check_passed": False,
        "fact_check_reason": "",
        "fact_check_report": {},
        "claim_verifications": [],
        "next_action": "",
    }

    # Clear the previous Researcher's tool-call history.
    # Keep research_evidence and research_queries so new findings
    # can build upon the existing research.
    if state.get("messages"):
        result["messages"] = [
            RemoveMessage(id=REMOVE_ALL_MESSAGES)
        ]

    return result


workflow = StateGraph(NewsroomState)

workflow.add_node("research", research_graph)
workflow.add_node("editor", editor_node)
workflow.add_node("fact_checker", fact_checker_node)
workflow.add_node(
    "prepare_follow_up_research",
    prepare_follow_up_research,
)

workflow.add_edge(START, "research")

workflow.add_conditional_edges(
    "research",
    route_after_research,
    {
        "editor": "editor",
        END: END,
    },
)

workflow.add_conditional_edges(
    "editor",
    route_after_editor,
    {
        "fact_checker": "fact_checker",
        END: END,
    },
)

workflow.add_conditional_edges(
    "fact_checker",
    route_after_fact_check,
    {
        "editor": "editor",
        "prepare_research": "prepare_follow_up_research",
        END: END,
    },
)

workflow.add_edge("prepare_follow_up_research", "research")

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