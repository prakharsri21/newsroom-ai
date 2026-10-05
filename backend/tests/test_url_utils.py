import pytest

from app.services.url_utils import normalize_url


def test_removes_fragment():
    assert (
        normalize_url("https://example.com/article#comments")
        == "https://example.com/article"
    )


def test_removes_tracking_parameters():
    assert (
        normalize_url(
            "https://example.com/article"
            "?utm_source=twitter&utm_medium=social"
        )
        == "https://example.com/article"
    )


def test_preserves_meaningful_query_parameters():
    assert (
        normalize_url("https://example.com/article?id=123&utm_source=test")
        == "https://example.com/article?id=123"
    )


def test_removes_trailing_slash():
    assert (
        normalize_url("https://example.com/article/")
        == "https://example.com/article"
    )


def test_preserves_root_slash():
    assert normalize_url("https://example.com") == "https://example.com/"


def test_normalizes_scheme_and_hostname():
    assert (
        normalize_url("HTTPS://EXAMPLE.COM/article")
        == "https://example.com/article"
    )


def test_rejects_non_http_urls():
    with pytest.raises(ValueError):
        normalize_url("ftp://example.com/file")