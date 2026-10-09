from datetime import UTC, datetime

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.evidence import collect_research_updates, message_text
from app.graph.llm import researcher_llm
from app.graph.research_context import format_research_context
from app.graph.state import MAX_ITERATIONS, NewsroomState


def build_researcher_system_prompt() -> str:
    current_date = datetime.now(UTC).date().isoformat()

    return f"""
You are the Researcher agent for a news research system.

Current date: {current_date}

Your job is to gather reliable evidence for the user's question.

Rules:

1. Prefer primary and authoritative sources when available.
2. For latest/current/today questions, prioritize information
   closest to the current date.
3. Never replace a current question with an older historical
   question unless the user explicitly asks for historical information.
4. If newer authoritative evidence exists, do not select an older
   conflicting result simply because it is easier to use.
5. When dates conflict, search for the specific current event,
   preferably on the authoritative source's domain.
6. Use the search_news tool when important evidence is missing.
7. Do not invent facts or sources.
8. Avoid repeating the same search query.
9. Only stop when the available evidence is sufficient for the
   Editor to write a factually grounded article.
10. If evidence is conflicting or incomplete, perform another search.
11. Treat authority_score, freshness_score, and relevance_score
    as evidence-quality signals, not as proof that a claim is true.
12. Prefer evidence with high authority and high freshness for
    current news.
13. A large number of low-quality sources does not compensate for
    missing authoritative evidence.
14. When a primary source is available, prefer it over secondary
    reporting for the core factual claim.
"""


async def researcher_agent_node(state: NewsroomState) -> dict:
    query = state.get("active_research_query") or state["query"]

    messages = state.get("messages", [])

    research_context = format_research_context(
        state.get("research_evidence", []),
        state.get("research_queries", []),
    )

    if not messages:
        messages = [
            SystemMessage(
                content=build_researcher_system_prompt(),
            ),
            HumanMessage(
                content=query,
            ),
        ]

    messages = [
        *messages,
        SystemMessage(
            content=(
                "Here is the current structured research state. "
                "Use it when deciding whether more research is needed.\n\n"
                f"{research_context}"
            ),
        ),
    ]

    response = await researcher_llm.ainvoke(messages)

    iteration = state.get("iteration", 0) + 1

    all_messages = [*messages, response]

    research_queries, research_evidence = collect_research_updates(
        all_messages,
        existing_queries=state.get("research_queries", []),
        existing_evidence=state.get("research_evidence", []),
    )

    wants_tool = bool(getattr(response, "tool_calls", []))

    result = {
        "messages": [response],
        "iteration": iteration,
        "research_queries": research_queries,
        "research_evidence": research_evidence,
    }

    if not wants_tool and research_evidence:
        result["research_complete"] = True
        result["research_summary"] = message_text(response)

    elif not wants_tool:
        result["research_complete"] = False
        result["research_failure_reason"] = (
            "No usable evidence was found for the requested query."
        )
        result["research_summary"] = (
            "Research stopped without collecting evidence. "
            "The research is incomplete."
        )

    elif iteration >= MAX_ITERATIONS:
        result["research_complete"] = False
        result["research_failure_reason"] = (
            "Research reached the maximum iteration limit "
            "without sufficient evidence."
        )
        result["research_summary"] = (
            "Research stopped after reaching the maximum number "
            "of Researcher iterations. Evidence may be incomplete."
        )

    return result