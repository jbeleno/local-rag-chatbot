"""
Dependency Injection para servicios de la aplicación.
Permite mejor testabilidad y gestión de dependencias.
"""
from typing import Generator
from fastapi import Depends

from app.core.database import get_db
from app.services.rag_service import RAGService
from app.services.chat_service import ChatService
from app.services.memory_service import MemoryService
from app.services.document_processor import DocumentProcessor
from app.services.cache_service import CacheService
from app.core.config import settings

# Instancias singleton de servicios (se crean una vez)
_rag_service: RAGService = None
_chat_service: ChatService = None
_memory_service: MemoryService = None
_document_processor: DocumentProcessor = None
_cache_service: CacheService = None


def get_rag_service() -> RAGService:
    """
    Obtener instancia del servicio RAG (singleton).
    
    Returns:
        Instancia de RAGService
    """
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


def get_chat_service() -> ChatService:
    """
    Obtener instancia del servicio de chat (singleton).
    
    Returns:
        Instancia de ChatService
    """
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


def get_memory_service() -> MemoryService:
    """
    Obtener instancia del servicio de memoria (singleton).
    
    Returns:
        Instancia de MemoryService
    """
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service


def get_document_processor() -> DocumentProcessor:
    """
    Obtener instancia del procesador de documentos (singleton).
    
    Returns:
        Instancia de DocumentProcessor
    """
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor()
    return _document_processor


def get_cache_service() -> CacheService:
    """
    Obtener instancia del servicio de caché (singleton).
    
    Returns:
        Instancia de CacheService
    """
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService(ttl_seconds=settings.CACHE_TTL_SECONDS) if settings.ENABLE_CACHE else None
    return _cache_service


# Dependencias para usar en endpoints
RAGServiceDep = Depends(get_rag_service)
ChatServiceDep = Depends(get_chat_service)
MemoryServiceDep = Depends(get_memory_service)
DocumentProcessorDep = Depends(get_document_processor)
CacheServiceDep = Depends(get_cache_service)

