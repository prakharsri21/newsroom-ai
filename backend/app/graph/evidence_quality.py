from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit


PRIMARY_DOMAINS = {
    "rbi.org.in",
    "pib.gov.in",
    "gov.in",
    "india.gov.in",
}

REPUTABLE_NEWS_DOMAINS = {
    "reuters.com",
    "bbc.com",
    "bbc.co.uk",
    "thehindu.com",
    "indianexpress.com",
    "ndtv.com",
    "cnn.com",
}

SOCIAL_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "x.com",
    "twitter.com",
    "tiktok.com",
    "youtube.com",
}


def is_usable_evidence(
    url: str,
    relevance_score: float | None,
) -> bool:
    domain = extract_domain(url)

    if domain in SOCIAL_DOMAINS or any(
        domain.endswith(f".{social}")
        for social in SOCIAL_DOMAINS
    ):
        return False

    if relevance_score is not None and relevance_score < 0.5:
        return False

    return True


def extract_domain(url: str) -> str:
    hostname = urlsplit(url).hostname

    if not hostname:
        return ""

    hostname = hostname.lower()

    if hostname.startswith("www."):
        hostname = hostname[4:]

    return hostname


def classify_authority(url: str) -> tuple[str, float]:
    """
    Classify a source by domain-level authority.

    This is a heuristic used for evidence ranking, not truth detection.
    """
    domain = extract_domain(url)

    if domain in PRIMARY_DOMAINS or domain.endswith(".gov.in"):
        return "primary", 1.0

    if domain in REPUTABLE_NEWS_DOMAINS:
        return "reputable_secondary", 0.8

    return "other", 0.4


def parse_published_date(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError:
        pass

    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


def calculate_freshness_score(
    published_at: str | None,
    *,
    now: datetime | None = None,
) -> float:
    """
    Calculate a simple freshness signal.

    The score is deliberately only a signal. Historical queries may
    legitimately need older evidence.
    """
    published = parse_published_date(published_at)

    if published is None:
        return 0.0

    if published.tzinfo is None:
        published = published.replace(tzinfo=UTC)

    current = now or datetime.now(UTC)

    age_days = max(
        0,
        (current - published).total_seconds() / 86400,
    )

    if age_days <= 1:
        return 1.0

    if age_days <= 7:
        return 0.9

    if age_days <= 30:
        return 0.7

    if age_days <= 180:
        return 0.4

    return 0.1