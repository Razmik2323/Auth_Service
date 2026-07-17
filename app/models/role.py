from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.associations import role_permissions, user_roles

if TYPE_CHECKING:
    from app.models.permission import Permission
    from app.models.user import User


class Role(UUIDMixin, TimestampMixin, Base):
    """Named role grouping a set of permissions."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))

    permissions: Mapped[list["Permission"]] = relationship(
        secondary=role_permissions, back_populates="roles", lazy="selectin"
    )
    users: Mapped[list["User"]] = relationship(secondary=user_roles, back_populates="roles")
