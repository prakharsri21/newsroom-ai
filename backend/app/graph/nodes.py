from langfuse import observe

from app.graph.state import NewsroomState


@observe(
    name="researcher-node",
    as_type="span",
    capture_output=False,
)
def researcher_node(state: NewsroomState) -> NewsroomState:
    iteration = state.get("iteration", 0)

    print("Researcher node running...")

    return {
        "research_complete": True,
        "source_ids": state.get("source_ids", []),
        "iteration": iteration,
    }


@observe(
    name="editor-node",
    as_type="span",
    capture_output=False,
)
def editor_node(state: NewsroomState) -> NewsroomState:
    iteration = state.get("iteration", 0)

    print("Editor node running...")

    return {
        "article_draft": (
            f"Draft article for query: {state.get('query', '')}"
        ),
        "article_version": state.get("article_version", 0) + 1,
        "iteration": iteration,
    }


@observe(
    name="fact-checker-node",
    as_type="span",
    capture_output=False,
)
def fact_checker_node(state: NewsroomState) -> NewsroomState:
    print("Fact Checker node running...")

    return {
        "fact_check_passed": True,
        "fact_check_reason": "Day 4 skeleton check passed.",
        "next_action": "done",
    }