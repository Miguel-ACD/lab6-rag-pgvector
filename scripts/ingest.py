from rag.db import initialize_schema
from rag.pdf_ingest import ingest_all


def report(progress: float, message: str) -> None:
    print(f"[{progress:6.1%}] {message}", flush=True)


initialize_schema()
for result in ingest_all(report):
    print(
        f"{result.status.upper():11} | {result.name} | "
        f"páginas {result.processed_pages}/{result.page_count} | "
        f"fragmentos {result.chunk_count} | omitidas {result.omitted_pages}",
        flush=True,
    )
