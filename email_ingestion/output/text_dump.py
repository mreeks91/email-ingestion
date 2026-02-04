"""Text file dump output valve."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import logging

from sqlalchemy import select

from email_ingestion.db.models import Email, ExtractedArtifact, Attachment
from email_ingestion.db.session import make_engine, make_session_factory


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DumpStats:
    emails: int
    files: int


def dump_email_texts(
    db_url: str,
    output_dir: str,
    max_bytes: int = 5120,
    limit: int | None = None,
    since: datetime | None = None,
) -> DumpStats:
    if max_bytes <= 0:
        raise ValueError("max_bytes must be > 0")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    engine = make_engine(db_url)
    session_factory = make_session_factory(engine=engine)

    file_index = 1
    buffer = ""
    buffer_size = 0
    emails_written = 0
    files_written = 0

    def flush() -> None:
        nonlocal buffer, buffer_size, file_index, files_written
        if not buffer:
            return
        filename = out_path / f"email_dump_{file_index:05d}.txt"
        filename.write_text(buffer, encoding="utf-8")
        files_written += 1
        file_index += 1
        buffer = ""
        buffer_size = 0

    with session_factory() as session:
        stmt = select(Email).order_by(Email.received_at, Email.email_id)
        if since:
            stmt = stmt.where(Email.received_at >= since)
        if limit:
            stmt = stmt.limit(limit)
        for email in session.execute(stmt).scalars():
            email_block = _format_email(session, email)
            email_bytes = len(email_block.encode("utf-8"))
            if buffer and buffer_size + email_bytes > max_bytes:
                flush()
            if not buffer and email_bytes > max_bytes:
                buffer = email_block
                flush()
                emails_written += 1
                continue
            buffer += email_block
            buffer_size += email_bytes
            emails_written += 1
        flush()

    logger.info("Dumped %s emails into %s files", emails_written, files_written)
    return DumpStats(emails=emails_written, files=files_written)


def _format_email(session, email: Email) -> str:
    header_lines = [
        f"Email-ID: {email.email_id}",
    ]
    if email.received_at:
        header_lines.append(f"Received: {email.received_at.isoformat()}")
    if email.subject:
        header_lines.append(f"Subject: {email.subject}")
    header = "\n".join(header_lines)

    body = email.body_text_normalized or email.body_text_raw or ""
    attachment_texts = _attachment_texts(session, email.email_id)

    parts = [header, ""]
    if body:
        parts.append(body.strip())
    if attachment_texts:
        parts.append("")
        parts.append("Attachment Text:")
        parts.append(attachment_texts.strip())
    parts.append("\n" + ("-" * 72) + "\n")
    return "\n".join(parts)


def _attachment_texts(session, email_id: str) -> str:
    stmt = (
        select(ExtractedArtifact.text, ExtractedArtifact.head_name, Attachment.filename)
        .join(Attachment, ExtractedArtifact.attachment_id == Attachment.attachment_id, isouter=True)
        .where(ExtractedArtifact.email_id == email_id)
        .where(ExtractedArtifact.attachment_id.is_not(None))
        .where(ExtractedArtifact.text.is_not(None))
    )
    blocks = []
    for text, head_name, filename in session.execute(stmt).all():
        label = []
        if filename:
            label.append(f"file={filename}")
        if head_name:
            label.append(f"head={head_name}")
        label_str = ", ".join(label) if label else "attachment"
        blocks.append(f"[{label_str}]\n{text}".strip())
    return "\n\n".join(blocks)
