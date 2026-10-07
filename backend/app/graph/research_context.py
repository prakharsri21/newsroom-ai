from app.graph.state import ResearchEvidence


def format_research_context(
    evidence: list[ResearchEvidence],
    queries: list[str],
) -> str:
    query_text = "\n".join(
        f"- {query}" for query in queries
    ) or "None"

    evidence_blocks: list[str] = []

    for index, item in enumerate(evidence, start=1):
        evidence_blocks.append(
            "\n".join(
                [
                    f"Evidence {index}:",
                    f"Title: {item.get('title', 'Unknown')}",
                    f"URL: {item.get('url', '')}",
                    f"Published: {item.get('published_at', 'Unknown')}",
                    f"Relevance: {item.get('relevance_score', 'Unknown')}",
                    f"Authority: {item.get('authority_tier', 'Unknown')}",
                    f"Authority score: {item.get('authority_score', 'Unknown')}",
                    f"Freshness score: {item.get('freshness_score', 'Unknown')}",
                    f"Excerpt: {item.get('excerpt', '')[:800]}",
                ]
            )
        )

    evidence_text = "\n\n".join(evidence_blocks) or "No evidence collected."

    return (
        "PREVIOUS SEARCH QUERIES:\n"
        f"{query_text}\n\n"
        "STRUCTURED RESEARCH EVIDENCE:\n"
        f"{evidence_text}"
    )