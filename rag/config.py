import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    postgres_db: str = os.getenv("POSTGRES_DB", "raglab")
    postgres_user: str = os.getenv("POSTGRES_USER", "raglab")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "raglab-local")
    postgres_host: str = os.getenv("POSTGRES_HOST", "db")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    pdf_dir: Path = Path(os.getenv("PDF_DIR", "/pdfs"))
    max_pages_per_pdf: int = int(os.getenv("MAX_PAGES_PER_PDF", "300"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "2200"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "250"))
    ollama_url: str = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434").rstrip("/")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    generation_model: str = os.getenv("GENERATION_MODEL", "llama3.2:3b")
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "768"))

    @property
    def dsn(self) -> str:
        return (
            f"dbname={self.postgres_db} user={self.postgres_user} "
            f"password={self.postgres_password} host={self.postgres_host} port={self.postgres_port}"
        )


settings = Settings()
