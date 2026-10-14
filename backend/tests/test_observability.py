from unittest.mock import Mock, patch

from app.services.observability import record_current_span


def test_record_current_span_updates_metadata_and_error_details():
    client = Mock()

    with patch("app.services.observability.get_client", return_value=client):
        record_current_span(
            metadata={"stage": "research_graph", "duration_ms": "123.4"},
            level="ERROR",
            status_message="Research graph failed",
        )

    client.update_current_span.assert_called_once_with(
        metadata={"stage": "research_graph", "duration_ms": "123.4"},
        level="ERROR",
        status_message="Research graph failed",
    )


def test_record_current_span_does_not_raise_when_langfuse_is_unavailable():
    with patch(
        "app.services.observability.get_client",
        side_effect=RuntimeError("Langfuse unavailable"),
    ):
        # Telemetry must not turn a successful product operation into a failure.
        record_current_span(metadata={"stage": "research_graph"})
