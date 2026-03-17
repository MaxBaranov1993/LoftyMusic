"""Fine-tuning job and LoRA adapter models."""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lofty.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FineTuneJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "finetune_jobs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
        index=True,
        nullable=False,
    )  # pending, queued, running, completed, failed, cancelled
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    compute_mode: Mapped[str] = mapped_column(String(10), nullable=False)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    adapter: Mapped["LoRAAdapter | None"] = relationship(
        back_populates="finetune_job", uselist=False
    )

    def __repr__(self) -> str:
        return f"<FineTuneJob {self.id} status={self.status}>"


class LoRAAdapter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lora_adapters"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    finetune_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("finetune_jobs.id"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)  # S3 path
    adapter_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    base_model: Mapped[str] = mapped_column(String(100), nullable=False)
    training_method: Mapped[str] = mapped_column(
        String(20), default="lokr", server_default="lokr", nullable=False
    )  # lora, lokr
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    finetune_job: Mapped["FineTuneJob"] = relationship(back_populates="adapter")

    def __repr__(self) -> str:
        return f"<LoRAAdapter {self.id} '{self.name}' method={self.training_method}>"
