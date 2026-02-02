"""MSG attachment head (optional dependency)."""

from __future__ import annotations

import tempfile
import os

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
            raise RuntimeError("Missing dependency: extract-msg (install optional extra)") from exc
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".msg")
        try:
            handle.write(head_input.attachment_bytes)
            handle.close()
            msg = extract_msg.Message(handle.name)
            msg.process()
        finally:
            try:
                os.unlink(handle.name)
            except Exception:
                pass
        payload = {
            "subject": msg.subject,
            "sender": msg.sender,
            "to": msg.to,
            "cc": msg.cc,
            "date": msg.date,
        }
        artifacts = [Artifact(artifact_type="msg_embedded", payload=payload, text=msg.body)]
        return HeadResult(artifacts=artifacts)
