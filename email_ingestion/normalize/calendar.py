"""Calendar invite parsing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from email_ingestion.normalize.email import normalize_recipient_list, normalize_single_address


@dataclass
class CalendarDetails:
    start: datetime | None
    end: datetime | None
    timezone: str | None
    location: str | None
    organizer: str | None
    attendees: list[str] | None


def parse_ics(data: bytes) -> CalendarDetails:
    try:
        from icalendar import Calendar  # type: ignore
    except Exception as exc:  # pragma: no cover - import guard
        raise RuntimeError("Missing dependency: icalendar") from exc
    cal = Calendar.from_ical(data)
    event = None
    for component in cal.walk():
        if component.name == "VEVENT":
            event = component
            break
    if not event:
        return CalendarDetails(None, None, None, None, None, None)
    start = event.get("dtstart")
    end = event.get("dtend")
    start_dt = start.dt if start else None
    end_dt = end.dt if end else None
    tzinfo = None
    if hasattr(start_dt, "tzinfo") and start_dt.tzinfo:
        tzinfo = str(start_dt.tzinfo)
    location = str(event.get("location")) if event.get("location") else None
    raw_organizer = str(event.get("organizer")) if event.get("organizer") else None
    organizer = normalize_single_address(raw_organizer) or raw_organizer
    attendees = []
    attendee_vals = event.get("attendee")
    if attendee_vals:
        if not isinstance(attendee_vals, list):
            attendee_vals = [attendee_vals]
        attendees = [str(item) for item in attendee_vals]
    attendees = normalize_recipient_list(attendees) or attendees
    return CalendarDetails(
        start=start_dt,
        end=end_dt,
        timezone=tzinfo,
        location=location,
        organizer=organizer,
        attendees=attendees or None,
    )


def merge_calendar_fields(
    details: CalendarDetails,
    fallback: dict[str, Any],
) -> CalendarDetails:
    return CalendarDetails(
        start=details.start or fallback.get("start"),
        end=details.end or fallback.get("end"),
        timezone=details.timezone or fallback.get("timezone"),
        location=details.location or fallback.get("location"),
        organizer=details.organizer or fallback.get("organizer"),
        attendees=details.attendees or fallback.get("attendees"),
    )
