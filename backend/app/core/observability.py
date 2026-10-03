from langfuse import Langfuse, propagate_attributes

from app.core.config import get_settings


settings = get_settings()

langfuse = Langfuse(
    public_key=settings.langfuse_public_key,
    secret_key=settings.langfuse_secret_key,
    base_url=settings.langfuse_base_url,
)


def add_request_context(
    *,
    tags: list[str] | None = None,
    metadata: dict[str, str] | None = None,
):
    return propagate_attributes(
        tags=tags or [],
        metadata=metadata or {},
    )