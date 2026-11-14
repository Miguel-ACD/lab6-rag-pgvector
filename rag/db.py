from contextlib import contextmanager

import psycopg
from pgvector.psycopg import register_vector

from .config import settings


@contextmanager
def connection():
    conn = psycopg.connect(settings.dsn, autocommit=True)
    try:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(conn)
        yield conn
    finally:
        conn.close()


def initialize_schema() -> None:
    with connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                sha256 TEXT NOT NULL,
                page_count INTEGER NOT NULL,
                processed_pages INTEGER NOT NULL,
                omitted_pages INTEGER NOT NULL DEFAULT 0,
                pages_without_text INTEGER[] NOT NULL DEFAULT '{}',
                read_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS chunks (
                id BIGSERIAL PRIMARY KEY,
                document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                page_number INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding vector({settings.embedding_dim}) NOT NULL,
                UNIQUE(document_id, page_number, chunk_index)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
            ON chunks USING hnsw (embedding vector_cosine_ops)
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS chunks_document_page ON chunks(document_id, page_number)")


def health() -> tuple[bool, str]:
    try:
        with connection() as conn:
            version = conn.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()
            return True, f"PostgreSQL y pgvector {version[0]} disponibles"
    except Exception as exc:
        return False, str(exc)


def document_stats() -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT name, page_count, processed_pages, omitted_pages,
                   pages_without_text, read_errors, chunk_count, updated_at
            FROM documents ORDER BY name
            """
        ).fetchall()
    return [
        {
            "name": row[0],
            "page_count": row[1],
            "processed_pages": row[2],
            "omitted_pages": row[3],
            "pages_without_text": row[4] or [],
            "read_errors": row[5] or [],
            "chunk_count": row[6],
            "updated_at": row[7],
        }
        for row in rows
    ]


def retrieve(question_embedding, document_name: str | None, top_k: int) -> list[dict]:
    filters = "WHERE d.name = %s" if document_name else ""
    params = (
        [question_embedding, document_name, question_embedding, top_k]
        if document_name
        else [question_embedding, question_embedding, top_k]
    )
    with connection() as conn:
        rows = conn.execute(
            f"""
            SELECT d.name, c.page_number, c.content,
                   1 - (c.embedding <=> %s::vector) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            {filters}
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
            """,
            params,
        ).fetchall()
    return [
        {"document": row[0], "page": row[1], "content": row[2], "score": float(row[3])}
        for row in rows
    ]
