from email_ingestion.pipeline.router import route_by_extension


def test_route_docx():
    head = route_by_extension("docx")
    assert head is not None
    assert head.name == "docx"


def test_route_unknown():
    head = route_by_extension("unknown")
    assert head is None
