from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean,func

from app.db.base import Base


class NewsStory(Base):
    __tablename__ = "news_stories"

    id: Mapped[int] = mapped_column(primary_key=True)

    headline: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    importance_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
    )

    # Distinguish discovered feed items from generated articles.
    is_discovery: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # Timestamp used to decide whether cached discovery results are fresh.
    last_refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )