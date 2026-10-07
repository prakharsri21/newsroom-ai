from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_PARAMETERS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
    "mc_cid",
    "mc_eid",
}


def normalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())

    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")

    if not parsed.hostname:
        raise ValueError("URL must contain a hostname")

    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower()

    if hostname.startswith("www."):
        hostname = hostname[4:]

    # Preserve non-default ports.
    if parsed.port is not None:
        if not (
            (scheme == "http" and parsed.port == 80)
            or (scheme == "https" and parsed.port == 443)
        ):
            hostname = f"{hostname}:{parsed.port}"

    path = parsed.path or "/"

    # Remove a trailing slash except for the root path.
    if path != "/":
        path = path.rstrip("/")

    query_pairs = parse_qsl(
        parsed.query,
        keep_blank_values=True,
    )

    filtered_query = [
        (key, value)
        for key, value in query_pairs
        if key.lower() not in TRACKING_PARAMETERS
    ]

    query = urlencode(filtered_query, doseq=True)

    # Fragments are client-side and should not identify a separate source.
    return urlunsplit(
        (
            scheme,
            hostname,
            path,
            query,
            "",
        )
    )