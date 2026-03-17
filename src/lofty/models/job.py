"""Generation job model."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lofty.models.base import Base, UUIDPrimaryKeyMixin


class JobStatus(enum.StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationJob(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "generation_jobs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=JobStatus.PENDING.value,
        index=True,
        nullable=False,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    lyrics: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), default="ace-step-1.5", nullable=False)
    generation_params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    lora_adapter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lora_adapters.id"), nullable=True
    )
    compute_mode: Mapped[str] = mapped_column(
        String(10), default="gpu", server_default="gpu", nullable=False
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="jobs")  # noqa: F821
    track: Mapped["Track | None"] = relationship(  # noqa: F821
        back_populates="job", uselist=False, lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<GenerationJob {self.id} status={self.status}>"
