import uuid

from sqlalchemy import UUID, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.core.base_model import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String, nullable=False)

    name: Mapped[str] = mapped_column(String, nullable=False, default="")
    surname: Mapped[str] = mapped_column(String, nullable=False, default="")
    patronymic: Mapped[str | None] = mapped_column(String, nullable=True)
    o_sebe: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class UserContacts(Base):
    __tablename__ = "user_contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    phone: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    socials: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class UserExperience(Base):
    __tablename__ = "user_experience"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    need_work: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resume: Mapped[str | None] = mapped_column(String, nullable=True)
