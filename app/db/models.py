from datetime import datetime

from uuid import UUID

from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID, JSONB
from sqlalchemy import UniqueConstraint

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.connection import Base


class TutorMessage(Base):
    __tablename__ = "tutor_messages"

    __table_args__ = (
        CheckConstraint(
            "role IN ('human', 'ai')",
            name="tutor_messages_role_check",
        ),
        Index(
            "idx_tutor_messages_conversation",
            "conversation_id",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    conversation_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # One message can have at most one embedding.
    embedding_record: Mapped["TutorMessageEmbedding | None"] = relationship(
        back_populates="message",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class TutorMessageEmbedding(Base):
    __tablename__ = "tutor_message_embeddings"

    __table_args__ = (
        Index(
            "idx_tutor_message_embeddings_conversation",
            "conversation_id",
        ),
    )

    message_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tutor_messages.id", ondelete="CASCADE"),
        primary_key=True,
    )

    conversation_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    embedding: Mapped[list[float]] = mapped_column(
        Vector(768),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    message: Mapped[TutorMessage] = relationship(
        back_populates="embedding_record",
    )

class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint("email", name="users_email_key"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        nullable=False,
    )

    # The database allows NULL for email, so preserve that.
    email: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    display_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class CareerRoadmap(Base):
    __tablename__ = "career_roadmaps"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        nullable=False,
    )

    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    target_role: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    milestones: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default="[]",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )