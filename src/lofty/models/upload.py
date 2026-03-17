"""Audio upload model for user-uploaded reference tracks and training data."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from lofty.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AudioUpload(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audio_uploads"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)  # wav, mp3, flac, ogg
    analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # BPM, key, caption, etc.

    def __repr__(self) -> str:
        return f"<AudioUpload {self.id} {self.original_filename}>"
