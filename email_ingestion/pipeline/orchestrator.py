"""Main orchestration logic."""

from __future__ import annotations

from datetime import datetime
import json
import logging
import uuid
from email_ingestion.config import AppConfig
from email_ingestion.db.repo import Repository
from email_ingestion.db.session import Base, make_engine, make_session_factory
from email_ingestion.heads.base import HeadInput, Artifact
from email_ingestion.heads.email_body import EmailBodyHead
from email_ingestion.heads.calendar_invite import CalendarInviteHead
from email_ingestion.normalize.calendar import parse_ics, merge_calendar_fields, CalendarDetails
from email_ingestion.normalize.email import (
    normalize_recipients,
    normalize_recipient_list,
    normalize_single_address,
    html_to_text,
    extract_links,
)
from email_ingestion.outlook.fetcher import OutlookFetcher, OutlookMessage, OutlookAttachment
from email_ingestion.pipeline.router import route_by_extension
from email_ingestion.storage.cas import ContentAddressedStorage
from email_ingestion.util.hashing import sha256_str


logger = logging.getLogger(__name__)


def make_email_id(entry_id: str, store_id: str) -> str:
    return sha256_str(f"outlook:{store_id}:{entry_id}")


def make_attachment_id(email_id: str, sha256: str, content_id: str | None, filename: str | None) -> str:
    return sha256_str(f"{email_id}:{sha256}:{content_id or ''}:{filename or ''}")


def make_artifact_id(
    email_id: str,
    attachment_id: str | None,
    head_name: str | None,
    artifact: Artifact,
) -> str:
    payload_hash = ""
    if artifact.text:
        payload_hash += sha256_str(artifact.text)
    if artifact.payload is not None:
        payload_hash += sha256_str(json.dumps(artifact.payload, sort_keys=True))
    if artifact.file_path:
        payload_hash += sha256_str(artifact.file_path)
    return sha256_str(
        f"{email_id}:{attachment_id or ''}:{head_name or ''}:{artifact.artifact_type}:{payload_hash}"
    )


def _safe_extension(filename: str | None) -> str | None:
    if not filename or "." not in filename:
        return None
    return filename.rsplit(".", 1)[-1].lower()


def _calendar_from_message(message: OutlookMessage) -> CalendarDetails:
    return CalendarDetails(
        start=message.meeting_start,
        end=message.meeting_end,
        timezone=message.meeting_timezone,
        location=message.meeting_location,
        organizer=normalize_single_address(message.meeting_organizer) or message.meeting_organizer,
        attendees=normalize_recipient_list(message.meeting_recipients) or message.meeting_recipients,
    )


def run_ingestion(
    config: AppConfig,
    mailbox: str,
    folder: str,
    since: datetime | None,
    limit: int | None,
    use_checkpoint: bool,
) -> dict:
    storage = ContentAddressedStorage(config.storage_root)
    storage.ensure_root()

    engine = make_engine(config.db_url)
    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine=engine)

    with session_factory() as session:
        repo = Repository(session)
        run = repo.start_run()
        checkpoint_value = repo.get_checkpoint(config.checkpoint_name) if use_checkpoint else None
        checkpoint_dt = None
        if checkpoint_value:
            checkpoint_dt = datetime.fromisoformat(checkpoint_value)
        effective_since = since or checkpoint_dt

        fetcher = OutlookFetcher(
            mailbox=mailbox,
            folder_path=folder,
            since=effective_since,
            limit=limit,
        )

        email_body_head = EmailBodyHead()
        calendar_head = CalendarInviteHead()
        processed = 0
        max_received = effective_since

        for message in fetcher.iter_messages():
            try:
                email_id = make_email_id(message.entry_id, message.store_id)
                normalized_text = html_to_text(message.body_html) or message.body_text
                links = extract_links(message.body_text, message.body_html)
                to_list = normalize_recipients(message.to)
                cc_list = normalize_recipients(message.cc)
                bcc_list = normalize_recipients(message.bcc)

                calendar_details = CalendarDetails(
                    start=None,
                    end=None,
                    timezone=None,
                    location=None,
                    organizer=None,
                    attendees=None,
                )
                for attachment in message.attachments:
                    ext = _safe_extension(attachment.filename)
                    if ext == "ics":
                        try:
                            calendar_details = parse_ics(attachment.data)
                        except Exception:
                            logger.exception("Failed to parse .ics attachment")
                        break
                calendar_details = merge_calendar_fields(calendar_details, _calendar_from_message(message).__dict__)

                email_payload = {
                    "email_id": email_id,
                    "source_system": "outlook",
                    "outlook_entry_id": message.entry_id,
                    "outlook_store_id": message.store_id,
                    "received_at": message.received_time,
                    "sent_at": message.sent_time,
                    "subject": message.subject,
                    "sender_name": message.sender_name,
                    "sender_email": message.sender_email,
                    "to_recipients": to_list,
                    "cc_recipients": cc_list,
                    "bcc_recipients": bcc_list,
                    "conversation_id": message.conversation_id,
                    "body_text_raw": message.body_text,
                    "body_text_normalized": normalized_text,
                    "body_html": message.body_html,
                    "link_list": links,
                    "is_calendar": bool(message.is_meeting or calendar_details.start or calendar_details.end),
                    "calendar_start": calendar_details.start,
                    "calendar_end": calendar_details.end,
                    "calendar_timezone": calendar_details.timezone,
                    "calendar_location": calendar_details.location,
                    "organizer": calendar_details.organizer,
                    "attendees": calendar_details.attendees,
                    "processing_state": "ingested",
                }
                repo.upsert_email(email_payload)

                attachment_records: list[tuple[OutlookAttachment, dict]] = []
                for attachment in message.attachments:
                    ext = _safe_extension(attachment.filename)
                    stored = storage.store_bytes(attachment.data, ext=ext)
                    attachment_id = make_attachment_id(
                        email_id=email_id,
                        sha256=stored.sha256,
                        content_id=attachment.content_id,
                        filename=attachment.filename,
                    )
                    payload = {
                        "attachment_id": attachment_id,
                        "email_id": email_id,
                        "filename": attachment.filename,
                        "ext": ext,
                        "mime": None,
                        "sha256": stored.sha256,
                        "size_bytes": stored.size_bytes,
                        "saved_path": str(stored.path),
                        "is_inline": attachment.is_inline,
                        "content_id": attachment.content_id,
                    }
                    repo.upsert_attachment(payload)
                    attachment_records.append((attachment, payload))

                # Email body head
                head_input = HeadInput(
                    email_id=email_id,
                    subject=message.subject,
                    body_text=message.body_text,
                    body_html=message.body_html,
                    is_calendar=message.is_meeting,
                    received_at=message.received_time,
                )
                _run_head(repo, run.run_id, email_id, None, email_body_head, head_input)

                # Calendar artifact for meeting items
                if message.is_meeting:
                    _store_calendar_artifact(repo, run.run_id, email_id, calendar_details)

                # Attachment heads
                for attachment, payload in attachment_records:
                    ext = payload.get("ext")
                    head = route_by_extension(ext)
                    if not head:
                        continue
                    head_input = HeadInput(
                        email_id=email_id,
                        subject=message.subject,
                        body_text=message.body_text,
                        body_html=message.body_html,
                        is_calendar=message.is_meeting,
                        attachment_id=payload["attachment_id"],
                        attachment_name=payload["filename"],
                        attachment_ext=ext,
                        attachment_bytes=attachment.data,
                        attachment_content_id=attachment.content_id,
                        received_at=message.received_time,
                    )
                    _run_head(repo, run.run_id, email_id, payload["attachment_id"], head, head_input)

                processed += 1
                if message.received_time and (not max_received or message.received_time > max_received):
                    max_received = message.received_time
            except Exception:
                logger.exception("Failed to process message")
                _add_event(
                    repo,
                    run.run_id,
                    email_id=None,
                    attachment_id=None,
                    head_name="message",
                    status="error",
                    error_message="message_processing_failed",
                )
                continue

        if max_received:
            repo.set_checkpoint(config.checkpoint_name, max_received.isoformat())
        repo.finish_run(run.run_id, stats={"processed": processed})
        return {"processed": processed, "checkpoint": max_received.isoformat() if max_received else None}


def _store_calendar_artifact(repo: Repository, run_id: str, email_id: str, details: CalendarDetails) -> None:
    payload = {
        "start": details.start.isoformat() if details.start else None,
        "end": details.end.isoformat() if details.end else None,
        "timezone": details.timezone,
        "location": details.location,
        "organizer": details.organizer,
        "attendees": details.attendees,
    }
    artifact = Artifact(artifact_type="calendar", payload=payload)
    artifact_id = make_artifact_id(email_id, None, "calendar_meeting", artifact)
    repo.add_artifact(
        {
            "artifact_id": artifact_id,
            "email_id": email_id,
            "attachment_id": None,
            "head_name": "calendar_meeting",
            "artifact_type": artifact.artifact_type,
            "payload": artifact.payload,
            "text": artifact.text,
            "file_path": artifact.file_path,
            "metadata": artifact.metadata,
        }
    )
    _add_event(repo, run_id, email_id, None, "calendar_meeting", "success", None)


def _run_head(repo: Repository, run_id: str, email_id: str, attachment_id: str | None, head, head_input: HeadInput) -> None:
    try:
        result = head.process(head_input)
        for artifact in result.artifacts:
            artifact_id = make_artifact_id(email_id, attachment_id, head.name, artifact)
            repo.add_artifact(
                {
                    "artifact_id": artifact_id,
                    "email_id": email_id,
                    "attachment_id": attachment_id,
                    "head_name": head.name,
                    "artifact_type": artifact.artifact_type,
                    "payload": artifact.payload,
                    "text": artifact.text,
                    "file_path": artifact.file_path,
                    "metadata": artifact.metadata,
                }
            )
        _add_event(
            repo,
            run_id,
            email_id,
            attachment_id,
            head.name,
            status="success",
            error_message=None,
            metrics=result.metrics,
        )
    except Exception as exc:
        logger.exception("Head failed: %s", head.name)
        _add_event(
            repo,
            run_id,
            email_id,
            attachment_id,
            head.name,
            status="error",
            error_message=str(exc),
        )


def _add_event(
    repo: Repository,
    run_id: str,
    email_id: str | None,
    attachment_id: str | None,
    head_name: str | None,
    status: str,
    error_message: str | None,
    metrics: dict | None = None,
) -> None:
    repo.add_processing_event(
        {
            "event_id": uuid.uuid4().hex,
            "run_id": run_id,
            "email_id": email_id,
            "attachment_id": attachment_id,
            "head_name": head_name,
            "status": status,
            "error_message": error_message,
            "metrics": metrics,
            "created_at": datetime.utcnow(),
        }
    )
