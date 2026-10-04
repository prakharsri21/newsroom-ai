from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClaimSource(Base):
    __tablename__ = "claim_sources"

    claim_id: Mapped[int] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"),
        primary_key=True,
    )

    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        primary_key=True,
    )

    relationship: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    evidence_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )