import json
from typing import Any

from langchain_core.messages import ToolMessage

from app.graph.evidence_quality import (
    calculate_freshness_score,
    classify_authority,
    is_usable_evidence,
)
from app.graph.state import ResearchEvidence
from app.services.url_utils import normalize_url


def message_text(message: Any) -> str:
    """
    Extract human-readable text from an AIMessage.

    Responses API messages can contain content blocks rather
    than a single plain string.
    """
    content = getattr(message, "content", "")

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []

        for item in content:
            if not isinstance(item, dict):
                continue

            if item.get("type") in {"text", "output_text"}:
                text = item.get("text", "")
                if text:
                    parts.append(str(text))

        return "\n".join(parts)

    return ""


def collect_research_updates(
    messages: list[Any],
    existing_queries: list[str] | None = None,
    existing_evidence: list[ResearchEvidence] | None = None,
) -> tuple[list[str], list[ResearchEvidence]]:
    """
    Extract search queries and evidence from the graph message history.

    This function is deliberately side-effect free so it can be
    tested without calling OpenAI or Tavily.
    """
    queries = list(existing_queries or [])
    evidence = list(existing_evidence or [])

    known_urls: set[str] = set()

    for item in evidence:
        url = item.get("url")

        if not url:
            continue

        try:
            known_urls.add(normalize_url(url))
        except ValueError:
            known_urls.add(url)

    for message in messages:
        # Capture queries requested by the LLM.
        for tool_call in getattr(message, "tool_calls", []):
            if tool_call.get("name") != "search_news":
                continue

            args = tool_call.get("args") or {}
            query = args.get("query")

            if query and query not in queries:
                queries.append(query)

        # Capture results returned by the search tool.
        if not isinstance(message, ToolMessage):
            continue

        if not isinstance(message.content, str):
            continue

        try:
            payload = json.loads(message.content)
        except json.JSONDecodeError:
            continue

        query = payload.get("query")

        if query and query not in queries:
            queries.append(query)

        for result in payload.get("results", []):
            url = result.get("url")

            if not url:
                continue

            # Filter incoming search candidates.
            if not is_usable_evidence(
                url,
                result.get("score"),
            ):
                continue

            try:
                normalized_url = normalize_url(url)
            except ValueError:
                normalized_url = url

            if normalized_url in known_urls:
                continue

            excerpt = result.get("content", "")
            published_at = result.get("published_at")

            authority_tier, authority_score = classify_authority(url)

            freshness_score = calculate_freshness_score(
                published_at
            )

            evidence.append(
                {
                    "url": url,
                    "title": result.get("title", ""),
                    "excerpt": excerpt[:1500],
                    "relevance_score": result.get("score"),
                    "published_at": published_at,
                    "authority_tier": authority_tier,
                    "authority_score": authority_score,
                    "freshness_score": freshness_score,
                }
            )

            known_urls.add(normalized_url)

    return queries, evidence