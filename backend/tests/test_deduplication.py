from app.services.deduplication import deduplicate_urls


def test_deduplicates_equivalent_urls():
    urls = [
        "https://example.com/article",
        "https://example.com/article/",
        "https://example.com/article#comments",
        "https://example.com/article?utm_source=test",
        "https://example.com/other",
    ]

    result = deduplicate_urls(urls)

    assert result == [
        "https://example.com/article",
        "https://example.com/other",
    ]