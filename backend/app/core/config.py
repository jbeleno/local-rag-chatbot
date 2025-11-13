"""
Application configuration using environment variables.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import Field, AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration."""
    
    # Chunk configuration
    CHUNK_SIZE: int = 700
    CHUNK_OVERLAP: int = 100
    TOP_K_RESULTS: int = 4
    RELEVANCE_THRESHOLD: float = 0.8  # Relevance threshold for filtering chunks (lower scores = more relevant)
    
    # Models
    LLM_MODEL: str = "qwen2.5:7b"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    LLM_TEMPERATURE: float = 0.4  # Balance between consistency and naturalness (0.3-0.5 for natural paraphrasing)
    LLM_TOP_P: float = 0.9
    LLM_MAX_TOKENS: int = 2048
    LLM_NUM_CTX: int = 8192  # Context window
    
    # Directories (relative paths from backend/)
    CHROMA_PERSIST_DIR: str = "../data/chroma_db"
    DOCUMENTS_DIR: str = "../data/documents"
    MEMORY_DB_PATH: str = "../data/memory.db"  # SQLite fallback
    COLLECTION_NAME: str = "documents_collection"
    
    # Ollama configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    # PostgreSQL configuration (Neon or others)
    USE_POSTGRES: bool = Field(default=False)
    DATABASE_URL: Optional[str] = None
    POSTGRES_POOL_MIN_CONN: int = 1
    POSTGRES_POOL_MAX_CONN: int = 10
    
    # Web search configuration
    WEB_SEARCH_ENABLED: bool = Field(default=True)
    WEB_SEARCH_MAX_RESULTS: int = Field(default=6)
    RELEVANCE_THRESHOLD: float = Field(default=0.8)
    
    # Memory/conversation configuration
    MAX_HISTORY_LENGTH: int = Field(default=10)  # Maximum messages in history
    MEMORY_ENABLED: bool = Field(default=True)
    
    # Advanced RAG configuration
    ENABLE_RERANKING: bool = Field(default=True)  # Enable result reranking
    ENABLE_QUERY_EXPANSION: bool = Field(default=True)  # Enable query expansion
    RERANKING_TOP_K: int = Field(default=5)  # Top K for reranking
    CHUNKING_STRATEGY: str = Field(default="adaptive")  # Chunking strategy: recursive, paragraphs, characters, tokens, adaptive
    ENABLE_CACHE: bool = Field(default=True)  # Enable cache for embeddings and responses
    CACHE_TTL_SECONDS: int = Field(default=3600)  # Cache TTL in seconds
    EMBEDDING_BATCH_SIZE: int = Field(default=32)  # Batch size for embeddings
    
    # FastAPI configuration
    API_TITLE: str = Field(default="Local RAG Chatbot")
    API_VERSION: str = Field(default="1.0.0")
    API_DESCRIPTION: str = Field(
        default="Fully local RAG chatbot using Ollama, ChromaDB and Sentence-Transformers"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        Path(self.DOCUMENTS_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)


# Global configuration instance
settings = Settings()

