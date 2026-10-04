from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StorySource(Base):
    __tablename__ = "story_sources"

    story_id: Mapped[int] = mapped_column(
        ForeignKey("news_stories.id", ondelete="CASCADE"),
        primary_key=True,
    )

    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        primary_key=True,
    )