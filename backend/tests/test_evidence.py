import json

from langchain_core.messages import AIMessage, ToolMessage

from app.graph.evidence import collect_research_updates, message_text


def test_extracts_search_query_and_evidence():
    messages = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_news",
                    "args": {
                        "query": "RBI monetary policy",
                        "max_results": 3,
                    },
                    "id": "call-1",
                    "type": "tool_call",
                }
            ],
        ),
        ToolMessage(
            content=json.dumps(
                {
                    "query": "RBI monetary policy",
                    "results": [
                        {
                            "title": "RBI Announcement",
                            "url": "https://www.rbi.org.in/article/",
                            "content": "Repo rate increased.",
                            "score": 0.95,
                            "published_at": "2026-10-07",
                        }
                    ],
                }
            ),
            tool_call_id="call-1",
        ),
    ]

    queries, evidence = collect_research_updates(messages)

    assert queries == ["RBI monetary policy"]
    assert len(evidence) == 1
    assert evidence[0]["title"] == "RBI Announcement"
    assert evidence[0]["published_at"] == "2026-10-07"


def test_deduplicates_equivalent_urls():
    messages = [
        ToolMessage(
            content=json.dumps(
                {
                    "query": "test",
                    "results": [
                        {
                            "title": "Same article",
                            "url": "https://example.com/article/?utm_source=test",
                            "content": "Evidence",
                            "score": 0.9,
                        },
                        {
                            "title": "Same article again",
                            "url": "https://www.example.com/article/",
                            "content": "Same evidence",
                            "score": 0.8,
                        },
                    ],
                }
            ),
            tool_call_id="call-1",
        )
    ]

    _, evidence = collect_research_updates(messages)

    assert len(evidence) == 1


def test_preserves_existing_evidence():
    existing = [
        {
            "url": "https://example.com/existing",
            "title": "Existing",
            "excerpt": "Existing evidence",
        }
    ]

    queries, evidence = collect_research_updates(
        [],
        existing_queries=["previous query"],
        existing_evidence=existing,
    )

    assert queries == ["previous query"]
    assert evidence == existing


def test_message_text_extracts_response_text():
    message = AIMessage(
        content=[
            {
                "type": "text",
                "text": "Research is sufficient.",
            }
        ]
    )

    assert message_text(message) == "Research is sufficient." 