"""Email body normalization head."""

from __future__ import annotations

from email_ingestion.heads.base import HeadInput, HeadResult, Artifact
from email_ingestion.normalize.email import html_to_text, extract_links


class EmailBodyHead:
    name = "email_body"
    supported_extensions = None

    def process(self, head_input: HeadInput) -> HeadResult:
        normalized_text = head_input.body_text
        if head_input.body_html:
            normalized_text = html_to_text(head_input.body_html) or normalized_text
        links = extract_links(head_input.body_text, head_input.body_html)
        artifacts = [
            Artifact(artifact_type="text", text=normalized_text),
            Artifact(artifact_type="link", payload={"links": links}),
        ]
        return HeadResult(artifacts=artifacts, metrics={"link_count": len(links)})
