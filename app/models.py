import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "User"

    UserID: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    Email: Mapped[str] = mapped_column(String)
    DisplayName: Mapped[str] = mapped_column(String)
    AuthProvider: Mapped[str] = mapped_column(String)