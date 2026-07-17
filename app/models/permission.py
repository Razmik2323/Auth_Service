from typing import TYPE_CHECKING

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDMixin
from app.models.associations import role_permissions

if TYPE_CHECKING:
    from app.models.role import Role


class Permission(UUIDMixin, CreatedAtMixin, Base):
    """Atomic permission over a resource and an action."""

    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("resource", "action"),)

    resource: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(255))

    roles: Mapped[list["Role"]] = relationship(
        secondary=role_permissions, back_populates="permissions"
    )
