"""Time helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from dateutil import parser


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return parser.parse(value)
