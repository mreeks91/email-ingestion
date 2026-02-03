"""Database models."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    String,
    DateTime,
    Boolean,
    Integer,
    Text,
    JSON,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from email_ingestion.db.session import Base


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    host: Mapped[str | None] = mapped_column(String(256), nullable=True)
    stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Email(Base):
    __tablename__ = "emails"

    email_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_system: Mapped[str] = mapped_column(String(32), default="outlook")
    outlook_entry_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    outlook_store_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    sender_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    sender_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_recipients: Mapped[list | None] = mapped_column(JSON, nullable=True)
    cc_recipients: Mapped[list | None] = mapped_column(JSON, nullable=True)
    bcc_recipients: Mapped[list | None] = mapped_column(JSON, nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_text_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_text_normalized: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    link_list: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_calendar: Mapped[bool] = mapped_column(Boolean, default=False)
    calendar_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    calendar_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    calendar_timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    calendar_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    organizer: Mapped[str | None] = mapped_column(Text, nullable=True)
    attendees: Mapped[list | None] = mapped_column(JSON, nullable=True)
    raw_headers: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_state: Mapped[str | None] = mapped_column(String(32), nullable=True)

    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment",
        back_populates="email",
        cascade="all, delete-orphan",
    )


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        UniqueConstraint(
            "email_id",
            "sha256",
            "content_id",
            name="uq_attachment_email_sha_content",
        ),
    )

    attachment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email_id: Mapped[str] = mapped_column(ForeignKey("emails.email_id"))
    filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    ext: Mapped[str | None] = mapped_column(String(16), nullable=True)
    mime: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    saved_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_inline: Mapped[bool] = mapped_column(Boolean, default=False)
    content_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    email: Mapped["Email"] = relationship("Email", back_populates="attachments")


class ExtractedArtifact(Base):
    __tablename__ = "extracted_artifacts"
    __table_args__ = (
        UniqueConstraint(
            "artifact_id",
            name="uq_artifact_id",
        ),
    )

    artifact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email_id: Mapped[str] = mapped_column(String(64), ForeignKey("emails.email_id"))
    attachment_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("attachments.attachment_id"), nullable=True
    )
    head_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    artifact_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ProcessingEvent(Base):
    __tablename__ = "processing_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("ingestion_runs.run_id"))
    email_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("emails.email_id"))
    attachment_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("attachments.attachment_id"), nullable=True
    )
    head_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16))
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
