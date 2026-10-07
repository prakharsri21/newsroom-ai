from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.llm import researcher_decision_llm
from app.graph.state import ResearchEvidence
from app.schemas.research import ResearchDecision


RESEARCHER_SYSTEM_PROMPT = """
You are the Researcher agent in a news research system.

Your job is to determine whether the available evidence is sufficient
to support reliable factual reporting about the user's query.

Rules:

1. Do not assume information is true just because a source says it.
2. Prefer primary or authoritative sources when available.
3. Look for multiple relevant sources when appropriate.
4. Consider whether the evidence actually answers the user's question.
5. Do not repeat a previous search query unless there is a clear reason.
6. Choose "search" when important evidence is missing.
7. Choose "complete" only when the available evidence is sufficient
   for the Editor to write a factually grounded article.

Return a structured research decision.
"""


async def decide_research_action(
    query: str,
    evidence: list[ResearchEvidence],
    previous_queries: list[str],
) -> ResearchDecision:
    evidence_text = "\n".join(
        (
            f"- Publisher: {item.get('publisher', 'Unknown')}\n"
            f"  Title: {item.get('title', 'Unknown')}\n"
            f"  URL: {item.get('url', '')}\n"
            f"  Evidence: {item.get('excerpt', '')}\n"
        )
        for item in evidence
    )

    previous_query_text = "\n".join(
        f"- {item}" for item in previous_queries
    ) or "None"

    user_message = f"""
User query:
{query}

Previous research queries:
{previous_query_text}

Current evidence:
{evidence_text or "No evidence collected yet."}
"""

    decision = await researcher_decision_llm.ainvoke(
        [
            SystemMessage(content=RESEARCHER_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ]
    )

    return decision