from langchain_core.messages import AIMessage

from app.graph.research_graph import route_after_researcher


def test_routes_to_tools_when_ai_requests_tool():
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_news",
                        "args": {
                            "query": "RBI monetary policy"
                        },
                        "id": "test-call",
                        "type": "tool_call",
                    }
                ],
            )
        ],
        "iteration": 1,
    }

    assert route_after_researcher(state) == "tools"


def test_routes_to_complete_without_tool_call():
    state = {
        "messages": [
            AIMessage(
                content="Research is sufficient.",
            )
        ],
        "iteration": 1,
    }

    assert route_after_researcher(state) == "complete"


def test_routes_to_complete_at_max_iterations():
    state = {
        "messages": [
            AIMessage(
                content="I need another search.",
                tool_calls=[
                    {
                        "name": "search_news",
                        "args": {
                            "query": "another query"
                        },
                        "id": "test-call",
                        "type": "tool_call",
                    }
                ],
            )
        ],
        "iteration": 3,
    }

    assert route_after_researcher(state) == "complete"