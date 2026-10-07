from app.graph.research_context import format_research_context


def test_formats_research_context():
    result = format_research_context(
        evidence=[
            {
                "title": "RBI Announcement",
                "url": "https://rbi.org.in/example",
                "published_at": "2026-10-07",
                "relevance_score": 0.95,
                "authority_tier": "primary",
                "authority_score": 1.0,
                "freshness_score": 1.0,
                "excerpt": "Repo rate increased to 5.50%.",
            }
        ],
        queries=[
            "RBI monetary policy",
        ],
    )

    assert "RBI monetary policy" in result
    assert "RBI Announcement" in result
    assert "primary" in result
    assert "5.50%" in result