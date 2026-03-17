"""User model synced from Clerk."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lofty.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    clerk_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    display_name: Mapped[str | None] = mapped_column(String(255))

    jobs: Mapped[list["GenerationJob"]] = relationship(  # noqa: F821
        back_populates="user", lazy="noload"
    )
    tracks: Mapped[list["Track"]] = relationship(  # noqa: F821
        back_populates="user", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<User {self.clerk_id}>"
