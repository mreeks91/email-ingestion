"""Outlook item fetcher."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging
import tempfile
import os
from typing import Iterator

from email_ingestion.outlook.mapi import get_namespace, resolve_shared_folder


logger = logging.getLogger(__name__)


CONTENT_ID_PROP = "http://schemas.microsoft.com/mapi/proptag/0x3712001F"
ATTACH_FLAGS_PROP = "http://schemas.microsoft.com/mapi/proptag/0x7FFD0003"


@dataclass
class OutlookAttachment:
    filename: str
    data: bytes
    size: int | None
    content_id: str | None
    is_inline: bool


@dataclass
class OutlookMessage:
    entry_id: str
    store_id: str
    received_time: datetime | None
    sent_time: datetime | None
    subject: str | None
    sender_name: str | None
    sender_email: str | None
    to: str | None
    cc: str | None
    bcc: str | None
    conversation_id: str | None
    body_text: str | None
    body_html: str | None
    message_class: str | None
    is_meeting: bool
    meeting_start: datetime | None
    meeting_end: datetime | None
    meeting_timezone: str | None
    meeting_location: str | None
    meeting_organizer: str | None
    meeting_recipients: list[str] | None
    attachments: list[OutlookAttachment] = field(default_factory=list)


class OutlookFetcher:
    def __init__(
        self,
        mailbox: str,
        folder_path: str,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> None:
        self.mailbox = mailbox
        self.folder_path = folder_path
        self.since = since
        self.limit = limit

    def iter_messages(self) -> Iterator[OutlookMessage]:
        namespace = get_namespace()
        folder = resolve_shared_folder(namespace, self.mailbox, self.folder_path)
        items = folder.Items
        items.Sort("[ReceivedTime]", True)
        count = 0
        for item in items:
            try:
                message = self._convert_item(item)
            except Exception:
                logger.exception("Failed to convert Outlook item")
                continue
            if self.since and message.received_time and message.received_time < self.since:
                continue
            yield message
            count += 1
            if self.limit and count >= self.limit:
                break

    def _convert_item(self, item) -> OutlookMessage:
        entry_id = getattr(item, "EntryID", None)
        store_id = getattr(item, "StoreID", None)
        message_class = getattr(item, "MessageClass", None)
        is_meeting = message_class and message_class.startswith("IPM.Schedule")
        meeting_start = getattr(item, "Start", None) if is_meeting else None
        meeting_end = getattr(item, "End", None) if is_meeting else None
        meeting_timezone = None
        if is_meeting:
            try:
                tz = getattr(item, "StartTimeZone", None)
                if tz is not None:
                    meeting_timezone = getattr(tz, "ID", None) or getattr(tz, "Name", None)
            except Exception:
                meeting_timezone = None
        meeting_location = getattr(item, "Location", None) if is_meeting else None
        meeting_organizer = getattr(item, "Organizer", None) if is_meeting else None
        meeting_recipients = None
        try:
            if is_meeting and getattr(item, "Recipients", None):
                meeting_recipients = [recip.Address for recip in item.Recipients]
        except Exception:
            meeting_recipients = None
        attachments = self._extract_attachments(item)
        return OutlookMessage(
            entry_id=entry_id or "",
            store_id=store_id or "",
            received_time=getattr(item, "ReceivedTime", None),
            sent_time=getattr(item, "SentOn", None),
            subject=getattr(item, "Subject", None),
            sender_name=getattr(item, "SenderName", None),
            sender_email=getattr(item, "SenderEmailAddress", None),
            to=getattr(item, "To", None),
            cc=getattr(item, "CC", None),
            bcc=getattr(item, "BCC", None),
            conversation_id=getattr(item, "ConversationID", None),
            body_text=getattr(item, "Body", None),
            body_html=getattr(item, "HTMLBody", None),
            message_class=message_class,
            is_meeting=bool(is_meeting),
            meeting_start=meeting_start,
            meeting_end=meeting_end,
            meeting_timezone=meeting_timezone,
            meeting_location=meeting_location,
            meeting_organizer=meeting_organizer,
            meeting_recipients=meeting_recipients,
            attachments=attachments,
        )

    def _extract_attachments(self, item) -> list[OutlookAttachment]:
        results: list[OutlookAttachment] = []
        if not getattr(item, "Attachments", None):
            return results
        for attachment in item.Attachments:
            try:
                data = self._read_attachment_bytes(attachment)
                filename = getattr(attachment, "FileName", "attachment")
                size = getattr(attachment, "Size", None)
                content_id = None
                is_inline = False
                try:
                    accessor = attachment.PropertyAccessor
                    content_id = accessor.GetProperty(CONTENT_ID_PROP)
                except Exception:
                    content_id = None
                try:
                    accessor = attachment.PropertyAccessor
                    flags = accessor.GetProperty(ATTACH_FLAGS_PROP)
                    is_inline = bool(flags and int(flags) & 0x4)
                except Exception:
                    is_inline = bool(content_id)
                results.append(
                    OutlookAttachment(
                        filename=filename,
                        data=data,
                        size=size,
                        content_id=content_id,
                        is_inline=is_inline,
                    )
                )
            except Exception:
                logger.exception("Failed to read attachment")
                continue
        return results

    def _read_attachment_bytes(self, attachment) -> bytes:
        handle = None
        try:
            handle = tempfile.NamedTemporaryFile(delete=False)
            handle.close()
            attachment.SaveAsFile(handle.name)
            with open(handle.name, "rb") as reader:
                return reader.read()
        finally:
            if handle:
                try:
                    os.unlink(handle.name)
                except Exception:
                    logger.debug("Failed to delete temp attachment file")
