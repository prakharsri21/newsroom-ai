from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.state import ResearchEvidence
from app.schemas.search import SearchResult
from app.services.source_ingestion import ingest_source


async def persist_research_evidence(
    db: AsyncSession,
    evidence: list[ResearchEvidence],
) -> tuple[list[int], list[ResearchEvidence]]:
    """
    Persist research evidence through the existing source-ingestion
    pipeline and attach database source IDs to the evidence.

    The research graph remains database-agnostic; persistence happens
    in the service layer.
    """
    source_ids: list[int] = []
    enriched_evidence: list[ResearchEvidence] = []

    for item in evidence:
        search_result = SearchResult(
            title=item.get("title", ""),
            url=item["url"],
            content=item.get("excerpt", ""),
            score=item.get("relevance_score"),
            published_at=item.get("published_at"),
        )

        source = await ingest_source(
            db,
            search_result,
        )

        source_id = source.id

        if source_id not in source_ids:
            source_ids.append(source_id)

        enriched_item = {
            **item,
            "source_id": source_id,
            "publisher": source.publisher or item.get("publisher", ""),
            "source_type": source.source_type,
        }

        enriched_evidence.append(enriched_item)

    return source_ids, enriched_evidence