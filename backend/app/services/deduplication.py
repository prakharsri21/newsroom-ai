from app.services.url_utils import normalize_url


def deduplicate_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_urls: list[str] = []

    for url in urls:
        normalized = normalize_url(url)

        if normalized in seen:
            continue

        seen.add(normalized)
        unique_urls.append(normalized)

    return unique_urls