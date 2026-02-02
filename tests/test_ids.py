from email_ingestion.pipeline.orchestrator import make_email_id, make_attachment_id


def test_make_email_id_deterministic():
    first = make_email_id("entry", "store")
    second = make_email_id("entry", "store")
    assert first == second


def test_make_attachment_id_deterministic():
    first = make_attachment_id("email", "sha", "cid", "file.pdf")
    second = make_attachment_id("email", "sha", "cid", "file.pdf")
    assert first == second
