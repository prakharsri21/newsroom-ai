from app.graph.graph import newsroom_graph


def test_newsroom_graph_completes():
    result = newsroom_graph.invoke(
        {
            "query": "test newsroom workflow",
            "iteration": 0,
            "article_version": 0,
        }
    )

    assert result["research_complete"] is True
    assert result["article_version"] == 1
    assert result["fact_check_passed"] is True
    assert result["next_action"] == "done"


def test_graph_state_contains_expected_fields():
    result = newsroom_graph.invoke(
        {
            "query": "test state",
            "iteration": 0,
            "article_version": 0,
        }
    )

    assert result["query"] == "test state"
    assert "article_draft" in result
    assert "fact_check_reason" in result
    assert result["iteration"] == 0