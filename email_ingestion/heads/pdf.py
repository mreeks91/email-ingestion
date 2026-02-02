"""PDF processing head."""

from __future__ import annotations

import io

from email_ingestion.heads.base import HeadInput, HeadResult, Artifact


class PdfHead:
    name = "pdf"
    supported_extensions = {"pdf"}

    def process(self, head_input: HeadInput) -> HeadResult:
        if not head_input.attachment_bytes:
            return HeadResult()
        try:
            from pypdf import PdfReader  # type: ignore
        except Exception as exc:  # pragma: no cover - import guard
            raise RuntimeError("Missing dependency: pypdf") from exc
        reader = PdfReader(io.BytesIO(head_input.attachment_bytes))
        chunks = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text:
                chunks.append(text)
        joined = "\n".join(chunks).strip() or None
        artifacts = [Artifact(artifact_type="text", text=joined)]
        return HeadResult(artifacts=artifacts, metrics={"pages": len(reader.pages)})
