"""MSG attachment head (optional dependency)."""

from __future__ import annotations

import tempfile
import os

from datetime import date, datetime

from email_ingestion.heads.base import HeadInput, HeadResult, Artifact


class MsgHead:
    name = "msg"
    supported_extensions = {"msg"}

    def process(self, head_input: HeadInput) -> HeadResult:
        if not head_input.attachment_bytes:
            return HeadResult()
        try:
            import extract_msg  # type: ignore
        except Exception as exc:  # pragma: no cover - import guard
            raise RuntimeError("Missing dependency: extract-msg") from exc
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".msg")
        msg = None
        try:
            handle.write(head_input.attachment_bytes)
            handle.close()
            msg = extract_msg.Message(handle.name)
            if hasattr(msg, "process"):
                msg.process()
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
        date_value = getattr(msg, "date", None)
        if isinstance(date_value, (datetime, date)):
            date_value = date_value.isoformat()
        payload = {
            "subject": getattr(msg, "subject", None),
            "sender": getattr(msg, "sender", None),
            "to": getattr(msg, "to", None),
            "cc": getattr(msg, "cc", None),
            "date": date_value,
        }
        body = getattr(msg, "body", None)
        artifacts = [Artifact(artifact_type="msg_embedded", payload=payload, text=body)]
        return HeadResult(artifacts=artifacts)
