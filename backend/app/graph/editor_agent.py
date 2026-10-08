from datetime import UTC, datetime

from langchain_core.messages import HumanMessage, SystemMessage

from langfuse import get_client
from app.graph.llm import editor_llm
from app.graph.research_context import build_editor_context
from app.graph.state import NewsroomState
from app.graph.citation import (
    build_evidence_registry,
    validate_article_citations,
)


EDITOR_SYSTEM_PROMPT = """
You are the Editor for a factual news publication system.

Your job is to turn the supplied research evidence into a clear,
concise news article.

STRICT EVIDENCE RULES:

1. Use only information supported by the supplied research evidence.
2. Do not introduce outside facts or background knowledge.
3. Do not invent statistics, dates, names, quotes, events, or explanations.
4. Do not invent evidence IDs.
5. Use only evidence references that actually exist in the supplied context.
6. Every factual claim must have at least one evidence reference.
7. Prefer stronger and more authoritative evidence when multiple sources
   support the same fact.
8. When sources conflict, do not silently choose a fact. Preserve the
   uncertainty or disagreement in the article where appropriate.
9. Do not turn assumptions or implications into factual claims.
10. Keep the article faithful to the research summary and evidence.

The output must follow the ArticleDraft schema exactly.

Current UTC date:
{current_date}
"""


async def editor_agent_node(state: NewsroomState) -> dict:
    evidence = state.get("research_evidence", [])

    if not evidence:
        raise ValueError("Editor cannot generate an article without research evidence.")

    current_date = datetime.now(UTC).date().isoformat()

    system_prompt = EDITOR_SYSTEM_PROMPT.format(
        current_date=current_date,
    )

    context = build_editor_context(
        state.get("query", ""),
        state.get("research_summary", ""),
        evidence,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=context),
    ]

    draft = await editor_llm.ainvoke(messages)

    langfuse = get_client()

    langfuse.update_current_span(
        metadata={
            "evidence_count": str(len(evidence)),
            "claim_count": str(len(draft.claims)),
        }
    )

    evidence_registry = build_evidence_registry(evidence)
    citation_errors = validate_article_citations(
        draft,
        evidence_registry,
    )

    article_parts = [
        f"{draft.headline} "
        f"[{', '.join(draft.headline_evidence_refs)}]"
        if draft.headline_evidence_refs
        else draft.headline,
        "",
        (
            f"{draft.summary} "
            f"[{', '.join(draft.summary_evidence_refs)}]"
            if draft.summary_evidence_refs
            else draft.summary
        ),
    ]

    for paragraph in draft.paragraphs:
        if paragraph.evidence_refs:
            citations = ", ".join(paragraph.evidence_refs)
            article_parts.append(
                f"{paragraph.text} [{citations}]"
            )
        else:
            article_parts.append(paragraph.text)

    article_draft = "\n\n".join(article_parts)

    return {
        "article_headline": draft.headline,
        "article_summary": draft.summary,
        "article_paragraphs": [
            paragraph.model_dump()
            for paragraph in draft.paragraphs
        ],
        "article_claims": [
            claim.model_dump()
            for claim in draft.claims
        ],
        "article_draft": article_draft,
        "citation_validation_passed": not citation_errors,
        "citation_validation_errors": citation_errors,
        "article_version": state.get("article_version", 0) + 1,
    }

