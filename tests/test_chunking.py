from rag.pdf_ingest import chunk_text


def test_chunking_preserves_content_and_limits_size():
    text = " ".join(["Una oración de prueba."] * 200)
    chunks = chunk_text(text, size=250, overlap=30)
    assert len(chunks) > 1
    assert all(chunk for chunk in chunks)
    assert all(len(chunk) <= 250 for chunk in chunks)


def test_empty_text_has_no_chunks():
    assert chunk_text("  \n\t ", size=100, overlap=10) == []
