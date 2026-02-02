"""Image processing head (no OCR in v1)."""

from __future__ import annotations

from email_ingestion.heads.base import HeadInput, HeadResult, Artifact


class ImageHead:
    name = "image"
    supported_extensions = {"png", "jpg", "jpeg", "gif", "tif", "tiff", "bmp"}

    def process(self, head_input: HeadInput) -> HeadResult:
        metadata = {
            "filename": head_input.attachment_name,
            "content_id": head_input.attachment_content_id,
        }
        artifacts = [Artifact(artifact_type="image", metadata=metadata)]
        return HeadResult(artifacts=artifacts)
