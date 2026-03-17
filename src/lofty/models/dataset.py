"""Dataset models for fine-tuning training data."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lofty.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Dataset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "datasets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending", nullable=False
    )  # pending, processing, ready, failed
    num_tracks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    storage_prefix: Mapped[str] = mapped_column(
        String(1024), default="", server_default="", nullable=False
    )  # S3 prefix for processed data

    tracks: Mapped[list["DatasetTrack"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Dataset {self.id} '{self.name}' status={self.status}>"


class DatasetTrack(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "dataset_tracks"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    upload_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audio_uploads.id"), nullable=False
    )
    lyrics: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    caption: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    key_scale: Mapped[str | None] = mapped_column(String(30), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending", nullable=False
    )  # pending, processed, failed

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    dataset: Mapped["Dataset"] = relationship(back_populates="tracks")

    def __repr__(self) -> str:
        return f"<DatasetTrack {self.id} dataset={self.dataset_id}>"
