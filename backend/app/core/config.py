"""Application configuration using environment variables."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from .env / environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # ---------------- Chunking & retrieval ----------------
    CHUNK_SIZE: int = 700
    CHUNK_OVERLAP: int = 100
    TOP_K_RESULTS: int = 4
    # Relevance threshold for filtering chunks (lower scores = more relevant for cosine distance).
    RELEVANCE_THRESHOLD: float = 0.8

    # ---------------- LLM & embedding models --------------
    LLM_MODEL: str = "qwen2.5:7b"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    LLM_TEMPERATURE: float = 0.4  # 0.3-0.5 keeps natural paraphrasing without hallucination drift.
    LLM_TOP_P: float = 0.9
    LLM_MAX_TOKENS: int = 2048
    LLM_NUM_CTX: int = 8192  # Context window

    # ---------------- Storage paths -----------------------
    CHROMA_PERSIST_DIR: str = "../data/chroma_db"
    DOCUMENTS_DIR: str = "../data/documents"
    MEMORY_DB_PATH: str = "../data/memory.db"  # SQLite fallback when USE_POSTGRES=False
    COLLECTION_NAME: str = "documents_collection"

    # ---------------- Ollama ------------------------------
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # ---------------- PostgreSQL (optional, for memory) ---
    USE_POSTGRES: bool = Field(default=False)
    DATABASE_URL: Optional[str] = None
    POSTGRES_POOL_MIN_CONN: int = 1
    POSTGRES_POOL_MAX_CONN: int = 10

    # ---------------- Web search --------------------------
    WEB_SEARCH_ENABLED: bool = Field(default=True)
    WEB_SEARCH_MAX_RESULTS: int = Field(default=6)

    # ---------------- Conversational memory ---------------
    MAX_HISTORY_LENGTH: int = Field(default=10)
    MEMORY_ENABLED: bool = Field(default=True)

    # ---------------- Advanced RAG ------------------------
    ENABLE_RERANKING: bool = Field(default=True)
    ENABLE_QUERY_EXPANSION: bool = Field(default=True)
    RERANKING_TOP_K: int = Field(default=5)
    # Chunking strategy: recursive | paragraphs | characters | tokens | adaptive
    CHUNKING_STRATEGY: str = Field(default="adaptive")
    ENABLE_CACHE: bool = Field(default=True)
    CACHE_TTL_SECONDS: int = Field(default=3600)
    EMBEDDING_BATCH_SIZE: int = Field(default=32)

    # ---------------- FastAPI metadata --------------------
    API_TITLE: str = Field(default="Local RAG Chatbot")
    API_VERSION: str = Field(default="1.0.0")
    API_DESCRIPTION: str = Field(
        default="Fully local RAG chatbot using Ollama, ChromaDB and Sentence-Transformers"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure data directories exist on first import.
        Path(self.DOCUMENTS_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)


# Global configuration instance
settings = Settings()
