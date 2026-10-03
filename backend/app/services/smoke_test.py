from langfuse import observe

from app.core.observability import langfuse, add_request_context


@observe(name="newsroom-smoke-test", as_type="span")
def run_smoke_test(message: str) -> dict[str, str]:
    with add_request_context(
        tags=["day1", "smoke-test"],
        metadata={
            "component": "backend",
            "environment": "development",
        },
    ):
        result = {
            "message": message,
            "status": "ok",
        }

        trace_url = langfuse.get_trace_url()

        return {
            **result,
            "trace_url": trace_url,
        }