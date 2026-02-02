"""Attachment routing to heads."""

from __future__ import annotations

from email_ingestion.heads.docx import DocxHead
from email_ingestion.heads.pptx import PptxHead
from email_ingestion.heads.pdf import PdfHead
from email_ingestion.heads.image import ImageHead
from email_ingestion.heads.msg import MsgHead
from email_ingestion.heads.calendar_invite import CalendarInviteHead


DEFAULT_HEADS = [
    DocxHead(),
    PptxHead(),
    PdfHead(),
    ImageHead(),
    MsgHead(),
    CalendarInviteHead(),
]


def route_by_extension(ext: str | None):
    if not ext:
        return None
    ext = ext.lower().lstrip(".")
    for head in DEFAULT_HEADS:
        if head.supported_extensions and ext in head.supported_extensions:
            return head
    return None
