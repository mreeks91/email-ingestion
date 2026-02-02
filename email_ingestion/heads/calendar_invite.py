"""Calendar invite head."""

from __future__ import annotations

from email_ingestion.heads.base import HeadInput, HeadResult, Artifact
from email_ingestion.normalize.calendar import parse_ics, merge_calendar_fields, CalendarDetails


class CalendarInviteHead:
    name = "calendar_invite"
    supported_extensions = {"ics"}

    def process(self, head_input: HeadInput) -> HeadResult:
        details = CalendarDetails(
            start=None,
            end=None,
            timezone=None,
            location=None,
            organizer=None,
            attendees=None,
        )
        if head_input.attachment_bytes and head_input.attachment_ext == "ics":
            details = parse_ics(head_input.attachment_bytes)

        fallback = {
            "start": None,
            "end": None,
            "timezone": None,
            "location": None,
            "organizer": None,
            "attendees": None,
        }
        merged = merge_calendar_fields(details, fallback)
        payload = {
            "start": merged.start.isoformat() if merged.start else None,
            "end": merged.end.isoformat() if merged.end else None,
            "timezone": merged.timezone,
            "location": merged.location,
            "organizer": merged.organizer,
            "attendees": merged.attendees,
        }
        artifacts = [Artifact(artifact_type="calendar", payload=payload)]
        return HeadResult(artifacts=artifacts)
