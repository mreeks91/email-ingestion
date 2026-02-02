"""Head interfaces and result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol


@dataclass
class HeadInput:
    email_id: str
    subject: str | None
    body_text: str | None
    body_html: str | None
    is_calendar: bool
    attachment_id: str | None = None
    attachment_name: str | None = None
    attachment_ext: str | None = None
    attachment_bytes: bytes | None = None
    attachment_content_id: str | None = None
    received_at: object | None = None


@dataclass
class Artifact:
    artifact_type: str
    text: str | None = None
    payload: dict | None = None
    file_path: str | None = None
    metadata: dict | None = None


@dataclass
class HeadResult:
    artifacts: list[Artifact] = field(default_factory=list)
    metrics: dict | None = None


class Head(Protocol):
    name: str
    supported_extensions: set[str] | None

    def process(self, head_input: HeadInput) -> HeadResult:
        ...
