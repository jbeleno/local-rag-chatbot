"""
Servicio de caché para embeddings y respuestas frecuentes.
"""
import logging
import hashlib
import json
from typing import Optional, Any, Callable
from functools import wraps
from cachetools import TTLCache, LRUCache

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Servicio de caché para embeddings y respuestas."""
    
    def __init__(
        self,
        embedding_cache_size: int = 1000,
        response_cache_size: int = 500,
        ttl_seconds: int = 3600  # 1 hora por defecto
    ):
        """
        Inicializar servicio de caché.
        
        Args:
            embedding_cache_size: Tamaño máximo del caché de embeddings
            response_cache_size: Tamaño máximo del caché de respuestas
            ttl_seconds: Tiempo de vida en segundos para entradas con TTL
        """
        # Caché LRU para embeddings (sin expiración, basado en uso)
        self.embedding_cache: LRUCache = LRUCache(maxsize=embedding_cache_size)
        
        # Caché TTL para respuestas (con expiración temporal)
        self.response_cache: TTLCache = TTLCache(
            maxsize=response_cache_size,
            ttl=ttl_seconds
        )
        
        logger.info(f"Caché inicializado: embeddings (LRU, {embedding_cache_size}), respuestas (TTL, {response_cache_size}, {ttl_seconds}s)")
    
    def _generate_key(self, *args, **kwargs) -> str:
        """
        Generar clave única para el caché basada en argumentos.
        
        Args:
            *args: Argumentos posicionales
            **kwargs: Argumentos nombrados
            
        Returns:
            Clave hash para el caché
        """
        # Crear representación serializable
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        
        # Generar hash
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get_embedding(self, text: str) -> Optional[Any]:
        """
        Obtener embedding del caché.
        
        Args:
            text: Texto para el cual buscar embedding
            
        Returns:
            Embedding si existe en caché, None en caso contrario
        """
        key = self._generate_key(text)
        return self.embedding_cache.get(key)
    
    def set_embedding(self, text: str, embedding: Any) -> None:
        """
        Guardar embedding en caché.
        
        Args:
            text: Texto original
            embedding: Embedding a guardar
        """
        key = self._generate_key(text)
        self.embedding_cache[key] = embedding
        logger.debug(f"Embedding guardado en caché para texto de {len(text)} caracteres")
    
    def get_response(self, query: str, context: str = "") -> Optional[Any]:
        """
        Obtener respuesta del caché.
        
        Args:
            query: Query del usuario
            context: Contexto adicional (opcional)
            
        Returns:
            Respuesta si existe en caché, None en caso contrario
        """
        key = self._generate_key(query, context=context)
        return self.response_cache.get(key)
    
    def set_response(self, query: str, response: Any, context: str = "") -> None:
        """
        Guardar respuesta en caché.
        
        Args:
            query: Query del usuario
            response: Respuesta a guardar
            context: Contexto adicional (opcional)
        """
        key = self._generate_key(query, context=context)
        self.response_cache[key] = response
        logger.debug(f"Respuesta guardada en caché para query: {query[:50]}...")
    
    def clear_embedding_cache(self) -> None:
        """Limpiar caché de embeddings."""
        self.embedding_cache.clear()
        logger.info("Caché de embeddings limpiado")
    
    def clear_response_cache(self) -> None:
        """Limpiar caché de respuestas."""
        self.response_cache.clear()
        logger.info("Caché de respuestas limpiado")
    
    def clear_all(self) -> None:
        """Limpiar todos los cachés."""
        self.clear_embedding_cache()
        self.clear_response_cache()
        logger.info("Todos los cachés limpiados")
    
    def get_stats(self) -> dict:
        """
        Obtener estadísticas de los cachés.
        
        Returns:
            Diccionario con estadísticas
        """
        return {
            "embedding_cache": {
                "size": len(self.embedding_cache),
                "maxsize": self.embedding_cache.maxsize,
                "currsize": self.embedding_cache.currsize
            },
            "response_cache": {
                "size": len(self.response_cache),
                "maxsize": self.response_cache.maxsize,
                "currsize": self.response_cache.currsize
            }
        }


def cached_embedding(cache_service: CacheService):
    """
    Decorador para cachear embeddings de funciones.
    
    Args:
        cache_service: Instancia del servicio de caché
        
    Returns:
        Decorador
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(text: str, *args, **kwargs):
            # Intentar obtener del caché
            cached = cache_service.get_embedding(text)
            if cached is not None:
                logger.debug(f"Embedding obtenido del caché para: {text[:50]}...")
                return cached
            
            # Calcular embedding
            embedding = func(text, *args, **kwargs)
            
            # Guardar en caché
            cache_service.set_embedding(text, embedding)
            
            return embedding
        
        return wrapper
    return decorator


def cached_response(cache_service: CacheService):
    """
    Decorador para cachear respuestas de funciones.
    
    Args:
        cache_service: Instancia del servicio de caché
        
    Returns:
        Decorador
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(query: str, *args, context: str = "", **kwargs):
            # Intentar obtener del caché
            cached = cache_service.get_response(query, context)
            if cached is not None:
                logger.debug(f"Respuesta obtenida del caché para: {query[:50]}...")
                return cached
            
            # Calcular respuesta
            response = func(query, *args, context=context, **kwargs)
            
            # Guardar en caché
            cache_service.set_response(query, response, context)
            
            return response
        
        return wrapper
    return decorator

