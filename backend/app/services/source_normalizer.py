from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

from app.schemas.search import SearchResult
from app.schemas.source import NormalizedSource
from app.services.url_utils import normalize_url
from app.services.web_fetch import FetchedPage


def parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None

    # ISO-8601 dates
    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError:
        pass

    # RFC-style dates
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


def extract_domain(url: str) -> str:
    hostname = urlsplit(url).hostname

    if not hostname:
        raise ValueError("URL has no hostname")

    hostname = hostname.lower()

    if hostname.startswith("www."):
        hostname = hostname[4:]

    return hostname


def infer_publisher(domain: str) -> str | None:
    publisher_map = {
        "reuters.com": "Reuters",
        "hindustantimes.com": "Hindustan Times",
        "ndtv.com": "NDTV",
        "bbc.com": "BBC",
        "bbc.co.uk": "BBC",
        "cnn.com": "CNN",
        "thehindu.com": "The Hindu",
        "indianexpress.com": "The Indian Express",
    }

    return publisher_map.get(domain)


def infer_source_type(domain: str) -> str:
    news_domains = {
        "reuters.com",
        "hindustantimes.com",
        "ndtv.com",
        "bbc.com",
        "bbc.co.uk",
        "cnn.com",
        "thehindu.com",
        "indianexpress.com",
    }

    if domain in news_domains:
        return "NEWS"

    return "OTHER"


def normalize_source(
    search_result: SearchResult,
    fetched_page: FetchedPage,
) -> NormalizedSource:
    canonical_url = normalize_url(fetched_page.url)
    domain = extract_domain(canonical_url)

    return NormalizedSource(
        url=canonical_url,
        domain=domain,
        publisher=infer_publisher(domain),
        title=fetched_page.title or search_result.title,
        author=None,
        published_at=parse_published_at(
            search_result.published_at
        ),
        content=fetched_page.text,
        source_type=infer_source_type(domain),
    )