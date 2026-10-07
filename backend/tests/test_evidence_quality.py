from datetime import UTC, datetime, timedelta

from app.graph.evidence_quality import (
    calculate_freshness_score,
    classify_authority,
)


def test_rbi_is_primary_source():
    tier, score = classify_authority(
        "https://www.rbi.org.in/scripts/NotificationUser.aspx"
    )

    assert tier == "primary"
    assert score == 1.0


def test_reuters_is_reputable_secondary():
    tier, score = classify_authority(
        "https://www.reuters.com/world/india/article"
    )

    assert tier == "reputable_secondary"
    assert score == 0.8


def test_unknown_domain_has_lower_authority():
    tier, score = classify_authority(
        "https://example.com/article"
    )

    assert tier == "other"
    assert score == 0.4


def test_recent_evidence_has_high_freshness():
    now = datetime(
        2026,
        10,
        8,
        tzinfo=UTC,
    )

    published = (
        now - timedelta(hours=6)
    ).isoformat()

    score = calculate_freshness_score(
        published,
        now=now,
    )

    assert score == 1.0


def test_old_evidence_has_low_freshness():
    now = datetime(
        2026,
        10,
        8,
        tzinfo=UTC,
    )

    published = (
        now - timedelta(days=365)
    ).isoformat()

    score = calculate_freshness_score(
        published,
        now=now,
    )

    assert score == 0.1


def test_missing_date_has_zero_freshness():
    assert calculate_freshness_score(None) == 0.0