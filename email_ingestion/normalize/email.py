"""Email body normalization."""

from __future__ import annotations

import re
from typing import Iterable


URL_PATTERN = re.compile(r"https?://[^\s<>\"]+")
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def extract_links(text: str | None, html: str | None) -> list[str]:
    links = set()
    for blob in (text or "", html or ""):
        for match in URL_PATTERN.findall(blob):
            links.add(match)
    return sorted(links)


def extract_emails(value: str | None) -> list[str]:
    if not value:
        return []
    return EMAIL_PATTERN.findall(value)


def normalize_recipients(value: str | None) -> list[str] | None:
    if not value:
        return None
    emails = set(extract_emails(value))
    return sorted(emails) or None


def normalize_recipient_list(values: Iterable[str] | None) -> list[str] | None:
    if not values:
        return None
    emails = set()
    for item in values:
        emails.update(extract_emails(item))
    return sorted(emails) or None


def normalize_single_address(value: str | None) -> str | None:
    emails = extract_emails(value)
    return emails[0] if emails else None


def html_to_text(html: str | None) -> str | None:
    if not html:
        return None
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except Exception:
        return strip_html(html)
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(separator="\n").strip()


def strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
