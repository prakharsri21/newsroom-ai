import re


_HISTORICAL_QUERY_CUES = re.compile(
    r"\b(history of|historical|timeline of|origins of|background of|"
    r"how did .* evolve|in the year \d{4})\b",
    re.IGNORECASE,
)

_SEARCH_FILLER = re.compile(
    r"\b(today|yesterday|latest|current|breaking|updates?|follow[- ]?up)\b",
    re.IGNORECASE,
)


def normalize_search_query(query: str) -> str:
    """Remove common temporal filler while preserving the user's topic."""
    cleaned = " ".join(query.split())
    if not cleaned:
        return ""

    normalized = _SEARCH_FILLER.sub(" ", cleaned)
    normalized = re.sub(r"\s+", " ", normalized).strip(" \t,;:-")
    return normalized or cleaned


def is_historical_query(query: str) -> bool:
    """Detect explicit requests for historical rather than current news."""
    return bool(_HISTORICAL_QUERY_CUES.search(" ".join(query.split())))


def default_search_days(query: str) -> int | None:
    """Use a seven-day publication window for news; do not filter history."""
    return None if is_historical_query(query) else 7
