import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

from .config import settings
from .db import connection
from .ollama_client import embed


@dataclass
class IngestionResult:
    name: str
    status: str
    page_count: int = 0
    processed_pages: int = 0
    omitted_pages: int = 0
    chunk_count: int = 0
    pages_without_text: list[int] = field(default_factory=list)
    read_errors: list[dict] = field(default_factory=list)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + size, len(normalized))
        if end < len(normalized):
            natural_break = normalized.rfind(". ", start + size // 2, end)
            if natural_break > start:
                end = natural_break + 1
        chunks.append(normalized[start:end].strip())
        if end >= len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks


def discover_pdfs() -> list[Path]:
    return sorted(settings.pdf_dir.glob("*.pdf"), key=lambda path: path.name.lower())


def ingest_all(progress=None) -> list[IngestionResult]:
    paths = discover_pdfs()
    if not paths:
        raise FileNotFoundError(f"No se encontraron PDF en {settings.pdf_dir}")
    results = []
    for index, path in enumerate(paths, start=1):
        if progress:
            progress((index - 1) / len(paths), f"Preparando {path.name}")
        results.append(ingest_pdf(path, progress, index, len(paths)))
    if progress:
        progress(1.0, "Ingesta completada")
    return results


def ingest_pdf(path: Path, progress=None, document_index: int = 1, document_total: int = 1) -> IngestionResult:
    sha256 = file_hash(path)
    reader = PdfReader(str(path))
    page_count = len(reader.pages)
    processed_pages = min(page_count, settings.max_pages_per_pdf)
    omitted_pages = max(page_count - processed_pages, 0)

    with connection() as conn:
        existing = conn.execute(
            "SELECT id, sha256, chunk_count, pages_without_text, read_errors FROM documents WHERE name=%s",
            (path.name,),
        ).fetchone()
        if existing and existing[1] == sha256:
            return IngestionResult(
                name=path.name,
                status="sin cambios",
                page_count=page_count,
                processed_pages=processed_pages,
                omitted_pages=omitted_pages,
                chunk_count=existing[2],
                pages_without_text=existing[3] or [],
                read_errors=existing[4] or [],
            )

    pages_without_text: list[int] = []
    read_errors: list[dict] = []
    page_chunks: list[tuple[int, int, str]] = []
    for page_index in range(processed_pages):
        page_number = page_index + 1
        try:
            text = (reader.pages[page_index].extract_text() or "").strip()
            if not text:
                pages_without_text.append(page_number)
                continue
            for chunk_index, content in enumerate(
                chunk_text(text, settings.chunk_size, settings.chunk_overlap)
            ):
                page_chunks.append((page_number, chunk_index, content))
        except Exception as exc:
            read_errors.append({"page": page_number, "error": str(exc)[:240]})
        if progress and page_number % 25 == 0:
            base = (document_index - 1) / document_total
            fraction = (page_number / processed_pages) / document_total
            progress(base + fraction * 0.35, f"Leyendo {path.name}: página {page_number}/{processed_pages}")

    embeddings: list[list[float]] = []
    batch_size = 16
    for start in range(0, len(page_chunks), batch_size):
        batch = page_chunks[start : start + batch_size]
        embeddings.extend(embed(item[2] for item in batch))
        if progress:
            base = (document_index - 1) / document_total
            portion = (start + len(batch)) / max(len(page_chunks), 1)
            progress(base + (0.35 + portion * 0.65) / document_total, f"Embeddings {path.name}: {start + len(batch)}/{len(page_chunks)}")

    with connection() as conn:
        with conn.transaction():
            conn.execute("DELETE FROM documents WHERE name=%s", (path.name,))
            document_id = conn.execute(
                """
                INSERT INTO documents
                    (name, sha256, page_count, processed_pages, omitted_pages,
                     pages_without_text, read_errors, chunk_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                RETURNING id
                """,
                (
                    path.name,
                    sha256,
                    page_count,
                    processed_pages,
                    omitted_pages,
                    pages_without_text,
                    json.dumps(read_errors, ensure_ascii=False),
                    len(page_chunks),
                ),
            ).fetchone()[0]
            with conn.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO chunks (document_id, page_number, chunk_index, content, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [
                        (document_id, page, chunk_index, content, embedding)
                        for (page, chunk_index, content), embedding in zip(
                            page_chunks, embeddings, strict=True
                        )
                    ],
                )

    return IngestionResult(
        name=path.name,
        status="procesado",
        page_count=page_count,
        processed_pages=processed_pages,
        omitted_pages=omitted_pages,
        chunk_count=len(page_chunks),
        pages_without_text=pages_without_text,
        read_errors=read_errors,
    )
