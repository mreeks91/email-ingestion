"""JSON safety helpers."""

from __future__ import annotations

from datetime import date, datetime
import json
from typing import Any


def make_json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, dict):
        return {str(k): make_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(v) for v in value]
    return value


def json_dumps_safe(value: Any, **kwargs) -> str:
    return json.dumps(make_json_safe(value), **kwargs)
