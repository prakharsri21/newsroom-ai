"""Small, failure-safe helpers for Langfuse span metadata."""

import logging
from typing import Literal

from langfuse import get_client

logger = logging.getLogger(__name__)

SpanLevel = Literal["DEBUG", "DEFAULT", "WARNING", "ERROR"]


def record_current_span(
    metadata: dict[str, str],
    *,
    level: SpanLevel | None = None,
    status_message: str | None = None,
) -> None:
    """Attach low-cardinality metadata without letting telemetry break the app."""
    kwargs: dict[str, object] = {"metadata": metadata}
    if level is not None:
        kwargs["level"] = level
    if status_message is not None:
        kwargs["status_message"] = status_message

    try:
        get_client().update_current_span(**kwargs)
    except Exception:
        # News generation must still work when Langfuse is unavailable.
        logger.debug("Unable to record Langfuse span metadata", exc_info=True)
