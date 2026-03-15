"""Track model for completed audio outputs."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lofty.models.base import Base, UUIDPrimaryKeyMixin


class Track(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tracks"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("generation_jobs.id"), unique=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    sample_rate: Mapped[int] = mapped_column(Integer, default=32000, nullable=False)
    format: Mapped[str] = mapped_column(String(10), default="wav", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    job: Mapped["GenerationJob"] = relationship(back_populates="track")  # noqa: F821
    user: Mapped["User"] = relationship(back_populates="tracks")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Track {self.id} title={self.title!r}>"
