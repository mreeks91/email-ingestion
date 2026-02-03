"""MSG attachment head (optional dependency)."""

from __future__ import annotations

import tempfile
import os

from datetime import date, datetime

from email_ingestion.heads.base import HeadInput, HeadResult, Artifact


class MsgHead:
    name = "msg"
    supported_extensions = {"msg"}

    def _safe_get(self, msg, attr: str):
        try:
            return getattr(msg, attr)
        except Exception:
            return None

    def process(self, head_input: HeadInput) -> HeadResult:
        if not head_input.attachment_bytes:
            return HeadResult()
        try:
            import extract_msg  # type: ignore
        except Exception as exc:  # pragma: no cover - import guard
            raise RuntimeError("Missing dependency: extract-msg") from exc
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".msg")
        msg = None
        payload = {}
        body = None
        try:
            handle.write(head_input.attachment_bytes)
            handle.close()
            msg = extract_msg.Message(handle.name)
            if hasattr(msg, "process"):
                msg.process()
            date_value = self._safe_get(msg, "date")
            if isinstance(date_value, (datetime, date)):
                date_value = date_value.isoformat()
            payload = {
                "subject": self._safe_get(msg, "subject"),
                "sender": self._safe_get(msg, "sender"),
                "to": self._safe_get(msg, "to"),
                "cc": self._safe_get(msg, "cc"),
                "date": date_value,
            }
            body = self._safe_get(msg, "body")
        finally:
            try:
                if msg is not None and hasattr(msg, "close"):
                    msg.close()
            except Exception:
                pass
            try:
                os.unlink(handle.name)
            except Exception:
                pass
        artifacts = [Artifact(artifact_type="msg_embedded", payload=payload, text=body)]
        return HeadResult(artifacts=artifacts)
