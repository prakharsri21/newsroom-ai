from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.research_graph import research_graph
from app.graph.state import NewsroomState
from app.services.research_persistence import persist_research_evidence


async def run_research(
    db: AsyncSession,
    state: NewsroomState,
) -> NewsroomState:
    """
    Run the Researcher graph and persist its collected sources.
    """

    result = await research_graph.ainvoke(state)

    evidence = result.get("research_evidence", [])

    if result.get("research_complete") and evidence:
        source_ids, enriched_evidence = (
            await persist_research_evidence(
                db,
                evidence,
            )
        )

        result["source_ids"] = source_ids
        result["research_evidence"] = enriched_evidence

    return result