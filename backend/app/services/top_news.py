import logging
import re
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news import NewsStory
from app.models.source import Source
from app.models.story_source import StorySource
from app.schemas.search import SearchResult
from app.schemas.top_news import TopNewsItem, TopNewsResponse
from app.services.sources import get_source_by_url
from app.services.url_utils import normalize_url
from app.services.web_search import search_web

logger = logging.getLogger(__name__)

CACHE_TTL = timedelta(minutes=30)
DEFAULT_LIMIT = 4
SEARCH_RESULT_LIMIT = 20
MAX_ARTICLE_AGE = timedelta(days=10)
DISCOVERY_DAYS = 7

# Keep this to one provider call per refresh. Request more candidates than we
# display so filtering and category diversity do not leave only one or two cards.
DISCOVERY_QUERY = (
    "latest important news today India and world politics government economy "
    "markets technology science sports major developments"
)

PUBLISHER_NAMES = {
    "reuters.com": "Reuters",
    "apnews.com": "Associated Press",
    "bbc.com": "BBC News",
    "bbc.co.uk": "BBC News",
    "thehindu.com": "The Hindu",
    "indianexpress.com": "The Indian Express",
    "ndtv.com": "NDTV",
    "hindustantimes.com": "Hindustan Times",
    "aljazeera.com": "Al Jazeera",
    "cnn.com": "CNN",
    "theguardian.com": "The Guardian",
    "npr.org": "NPR",
    "economictimes.indiatimes.com": "The Economic Times",
    "livemint.com": "Mint",
    "business-standard.com": "Business Standard",
    "cnbc.com": "CNBC",
    "espn.com": "ESPN",
    "espncricinfo.com": "ESPNcricinfo",
}

NOISE_TITLE_PHRASES = (
    "school assembly",
    "assembly news headlines",
    "morning assembly",
    "assembly headlines",
    "news headlines for students",
    "headlines for school assembly",
    "school news headlines",
    "comment synopsis",
    "synopsis school assembly",
    "speech for morning assembly",
    "daily assembly news",
)

GENERIC_TITLE_PHRASES = (
    "latest news headlines today",
    "news headlines today",
    "todays top headlines",
    "top india world sports business news",
    "top national world business and sports updates",
)

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "after", "amid", "by", "for", "from",
    "has", "have", "in", "into", "is", "its", "of", "on", "or", "over", "says",
    "said", "the", "to", "with", "what", "when", "who", "why", "how", "today",
}


class TopNewsUnavailableError(RuntimeError):
    """Raised when live discovery fails and no cached stories are available."""


def _parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def _publisher_for_domain(domain: str) -> str:
    return PUBLISHER_NAMES.get(
        domain,
        domain.removeprefix("www.").split(".")[0].replace("-", " ").title(),
    )


def _is_noise_title(title: str | None) -> bool:
    normalized = re.sub(r"[^a-z0-9 ]+", " ", (title or "").lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return True
    return any(phrase in normalized for phrase in NOISE_TITLE_PHRASES + GENERIC_TITLE_PHRASES)


def _headline_tokens(title: str) -> set[str]:
    # Remove common publisher suffixes before comparing syndicated headline variants.
    cleaned = re.sub(
        r"\s+(?:-|–|—|\|)\s+(?:the\s+)?(?:economic times|associated press|bbc news|reuters|cnn|the guardian|ndtv|the hindu|the indian express|hindustan times|al jazeera)$",
        "",
        title.lower(),
    )
    return {
        token
        for token in re.findall(r"[a-z0-9]+", cleaned)
        if token not in STOPWORDS and len(token) > 1
    }


def _titles_are_similar(left: str, right: str) -> bool:
    left_tokens = _headline_tokens(left)
    right_tokens = _headline_tokens(right)
    if not left_tokens or not right_tokens:
        return False

    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    jaccard = intersection / union if union else 0.0
    sequence_ratio = SequenceMatcher(
        None,
        " ".join(sorted(left_tokens)),
        " ".join(sorted(right_tokens)),
    ).ratio()
    return jaccard >= 0.78 or sequence_ratio >= 0.84


def _category_for_result(result: SearchResult) -> str:
    # Classify primarily from the headline. Snippet text often mentions several
    # unrelated topics, which caused national stories to be labelled as sports.
    headline = result.title.lower()

    if any(term in headline for term in (
        "cricket", "football", "tennis", "olympic", "championship", "tournament",
        "match result", "world cup", "grand prix", "premier league", "ipl ",
        "nba", "wimbledon", "fifa", "athlete", "sports",
    )):
        return "Sports"

    if any(term in headline for term in (
        "stock market", "shares", "sensex", "nifty", "wall street", "earnings",
        "quarterly results", "interest rate", "inflation", "central bank", "rupee",
        "oil prices", "bond yields", "market rally", "market falls", "markets",
        "investor",
    )):
        return "Markets"

    if any(term in headline for term in (
        "artificial intelligence", "technology", "cybersecurity", "semiconductor",
        "software", "tech company", "openai", "google ai", "apple launches",
        "microsoft", "chipmaker", "data breach", "ai model",
    )) or re.search(r"\bAI\b", result.title):
        return "Technology"

    if any(term in headline for term in (
        "bollywood", "hollywood", "box office", "film review", "movie release",
        "music award", "celebrity", "actor ", "actress ", "netflix series",
    )):
        return "Entertainment"

    if any(term in headline for term in (
        "india", "indian", "new delhi", "narendra modi", "modi government", "lok sabha",
        "rajya sabha", "rbi ", "supreme court of india", "election commission of india",
        "karnataka", "maharashtra", "uttar pradesh", "west bengal", "tamil nadu",
    )):
        return "National"

    return "World"


def _is_recent_result(result: SearchResult, now: datetime) -> bool:
    published = _parse_published_at(result.published_at)
    if published is None:
        return True
    if published > now + timedelta(days=1):
        return False
    return published >= now - MAX_ARTICLE_AGE


def _select_distinct_results(results: list[SearchResult], limit: int, now: datetime) -> list[SearchResult]:
    candidates: list[SearchResult] = []
    seen_urls: set[str] = set()
    seen_titles: list[str] = []

    for result in results:
        title = (result.title or "").strip()
        if _is_noise_title(title) or not _is_recent_result(result, now):
            continue

        canonical_url = normalize_url(str(result.url))
        if not canonical_url or canonical_url in seen_urls:
            continue
        if any(_titles_are_similar(title, prior) for prior in seen_titles):
            continue

        seen_urls.add(canonical_url)
        seen_titles.append(title)
        candidates.append(result)

    # First pick the best available story per category, then fill remaining
    # places with the best remaining candidates. Preserve Tavily's relevance order.
    selected: list[SearchResult] = []
    selected_categories: set[str] = set()
    selected_urls: set[str] = set()

    for result in candidates:
        category = _category_for_result(result)
        canonical_url = normalize_url(str(result.url))
        if category in selected_categories:
            continue
        selected.append(result)
        selected_categories.add(category)
        selected_urls.add(canonical_url)
        if len(selected) >= limit:
            return selected

    for result in candidates:
        canonical_url = normalize_url(str(result.url))
        if canonical_url in selected_urls:
            continue
        selected.append(result)
        selected_urls.add(canonical_url)
        if len(selected) >= limit:
            break

    return selected


async def _load_discovery_items(
    db: AsyncSession,
    *,
    limit: int,
    refreshed_since: datetime | None = None,
) -> list[TopNewsItem]:
    source_counts = (
        select(
            StorySource.story_id,
            func.count(StorySource.source_id).label("source_count"),
        )
        .group_by(StorySource.story_id)
        .subquery()
    )

    statement = (
        select(NewsStory, Source, func.coalesce(source_counts.c.source_count, 0))
        .select_from(NewsStory)
        .outerjoin(StorySource, StorySource.story_id == NewsStory.id)
        .outerjoin(Source, Source.id == StorySource.source_id)
        .outerjoin(source_counts, source_counts.c.story_id == NewsStory.id)
        .where(NewsStory.is_discovery.is_(True))
        .order_by(
            NewsStory.last_refreshed_at.desc(),
            NewsStory.importance_score.desc(),
            NewsStory.published_at.desc().nullslast(),
        )
    )
    if refreshed_since is not None:
        statement = statement.where(NewsStory.last_refreshed_at >= refreshed_since)

    # Fetch extra rows first because we remove junk, stale entries, and duplicate titles below.
    rows = (await db.execute(statement.limit(max(limit * 8, 40)))).all()
    items: list[TopNewsItem] = []
    seen_story_ids: set[int] = set()
    seen_titles: list[str] = []
    now = datetime.now(UTC)

    for story, source, source_count in rows:
        if story.id in seen_story_ids:
            continue
        seen_story_ids.add(story.id)

        if _is_noise_title(story.headline):
            continue
        if story.published_at is not None:
            published = story.published_at
            if published.tzinfo is None:
                published = published.replace(tzinfo=UTC)
            if published < now - MAX_ARTICLE_AGE or published > now + timedelta(days=1):
                continue
        if any(_titles_are_similar(story.headline, prior) for prior in seen_titles):
            continue

        seen_titles.append(story.headline)
        items.append(
            TopNewsItem(
                id=story.id,
                headline=story.headline,
                summary=story.summary,
                category=story.category,
                published_at=story.published_at,
                first_seen_at=story.first_seen_at,
                source_title=source.title if source else None,
                publisher=source.publisher if source else None,
                source_url=source.url if source else None,
                verification_status="not_checked",
                source_count=max(1, source_count),
            )
        )

    # Diversify the order returned from the database, not just results from Tavily.
    diversified: list[TopNewsItem] = []
    categories: set[str] = set()
    for item in items:
        category = item.category.strip().lower()
        if category not in categories:
            diversified.append(item)
            categories.add(category)
        if len(diversified) >= limit:
            return diversified
    for item in items:
        if item not in diversified:
            diversified.append(item)
        if len(diversified) >= limit:
            break
    return diversified


async def _latest_refresh_time(db: AsyncSession) -> datetime | None:
    result = await db.execute(
        select(func.max(NewsStory.last_refreshed_at)).where(NewsStory.is_discovery.is_(True))
    )
    return result.scalar_one_or_none()


async def _save_discovery_result(
    db: AsyncSession,
    result: SearchResult,
    *,
    refreshed_at: datetime,
) -> None:
    canonical_url = normalize_url(str(result.url))
    parsed_url = urlsplit(canonical_url)
    domain = (parsed_url.hostname or "").lower().removeprefix("www.")
    if not domain:
        return

    source = await get_source_by_url(db, url=canonical_url)
    if source is None:
        source = Source(
            url=canonical_url,
            domain=domain,
            publisher=_publisher_for_domain(domain),
            title=result.title[:1000],
            published_at=_parse_published_at(result.published_at),
            content=result.content,
            source_type="NEWS",
        )
        db.add(source)
        await db.flush()
    else:
        source.title = result.title[:1000] or source.title
        source.publisher = source.publisher or _publisher_for_domain(domain)
        source.content = result.content or source.content
        source.published_at = _parse_published_at(result.published_at) or source.published_at

    existing_result = await db.execute(
        select(NewsStory)
        .join(StorySource, StorySource.story_id == NewsStory.id)
        .where(StorySource.source_id == source.id, NewsStory.is_discovery.is_(True))
        .limit(1)
    )
    story = existing_result.scalar_one_or_none()

    if story is None:
        story = NewsStory(
            headline=result.title[:500],
            summary=result.content or None,
            category=_category_for_result(result),
            published_at=_parse_published_at(result.published_at),
            importance_score=result.score or 0.0,
            is_discovery=True,
            last_refreshed_at=refreshed_at,
        )
        db.add(story)
        await db.flush()
        db.add(StorySource(story_id=story.id, source_id=source.id))
    else:
        story.headline = result.title[:500]
        story.summary = result.content or story.summary
        story.category = _category_for_result(result)
        story.published_at = _parse_published_at(result.published_at) or story.published_at
        story.importance_score = result.score or 0.0
        story.last_refreshed_at = refreshed_at


async def get_top_news(
    db: AsyncSession,
    *,
    limit: int = DEFAULT_LIMIT,
    force_refresh: bool = False,
) -> TopNewsResponse:
    """Return a small, diverse feed of recent, distinct headlines from Tavily."""
    limit = max(1, min(limit, 10))
    now = datetime.now(UTC)
    last_refresh = await _latest_refresh_time(db)

    # A refresh writes the same timestamp to each result in that batch. Grouping
    # by that timestamp prevents old discovery rows from leaking back into the feed.
    batch_cutoff = last_refresh - timedelta(milliseconds=10) if last_refresh else None
    cached_items = await _load_discovery_items(
        db,
        limit=limit,
        refreshed_since=batch_cutoff,
    )
    cache_is_fresh = bool(cached_items) and last_refresh is not None and now - last_refresh < CACHE_TTL

    if cache_is_fresh and not force_refresh:
        return TopNewsResponse(
            items=cached_items,
            served_from_cache=True,
            refreshed_at=last_refresh,
            message="Showing the latest saved set of distinct headlines.",
        )

    try:
        search_response = await search_web(
            DISCOVERY_QUERY,
            max_results=SEARCH_RESULT_LIMIT,
            days=DISCOVERY_DAYS,
        )
        refreshed_at = datetime.now(UTC)
        selected_results = _select_distinct_results(search_response.results, limit, refreshed_at)

        if not selected_results:
            if cached_items:
                return TopNewsResponse(
                    items=cached_items,
                    served_from_cache=True,
                    refreshed_at=last_refresh,
                    message="No recent, distinct headlines passed the quality filters; showing the last saved feed.",
                )
            return TopNewsResponse(
                items=[],
                served_from_cache=False,
                refreshed_at=None,
                message="The discovery provider returned no suitable recent headlines.",
            )

        for result in selected_results:
            await _save_discovery_result(db, result, refreshed_at=refreshed_at)
        await db.commit()

        fresh_items = await _load_discovery_items(
            db,
            limit=limit,
            refreshed_since=refreshed_at - timedelta(milliseconds=10),
        )
        latest_refresh = await _latest_refresh_time(db)
        if fresh_items:
            return TopNewsResponse(
                items=fresh_items,
                served_from_cache=False,
                refreshed_at=latest_refresh or refreshed_at,
                message="News refreshed with duplicate and low-quality headline filtering.",
            )

        if cached_items:
            return TopNewsResponse(
                items=cached_items,
                served_from_cache=True,
                refreshed_at=last_refresh,
                message="The refresh produced no displayable stories; showing the last saved feed.",
            )

        return TopNewsResponse(
            items=[],
            served_from_cache=False,
            refreshed_at=None,
            message="No displayable headlines were returned.",
        )

    except Exception as exc:
        await db.rollback()
        logger.exception("Top-news discovery refresh failed")
        if cached_items:
            return TopNewsResponse(
                items=cached_items,
                served_from_cache=True,
                refreshed_at=last_refresh,
                message="Live refresh failed; showing the last saved feed.",
            )
        raise TopNewsUnavailableError(
            "Live news discovery failed and no cached results are available."
        ) from exc
