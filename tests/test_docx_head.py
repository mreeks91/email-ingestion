import io

from email_ingestion.heads.docx import DocxHead
from email_ingestion.heads.base import HeadInput


def test_docx_head_extracts_text():
    try:
        from docx import Document
    except Exception:
        return
    doc = Document()
    doc.add_paragraph("Hello Docx")
    buf = io.BytesIO()
    doc.save(buf)
    data = buf.getvalue()
    head = DocxHead()
    result = head.process(
        HeadInput(
            email_id="email",
            subject="subject",
            body_text=None,
            body_html=None,
            is_calendar=False,
            attachment_id="att",
            attachment_name="test.docx",
            attachment_ext="docx",
            attachment_bytes=data,
            attachment_content_id=None,
        )
    )
    assert result.artifacts
    assert "Hello Docx" in (result.artifacts[0].text or "")
