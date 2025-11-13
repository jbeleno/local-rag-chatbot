"""
Servicio de reranking para mejorar la precisión de recuperación de documentos.
Usa modelos cross-encoder para reranking de resultados de búsqueda semántica.
"""
import logging
from typing import List, Dict, Optional

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    CrossEncoder = None

from app.core.config import settings

logger = logging.getLogger(__name__)


class RerankingService:
    """Servicio para reranking de resultados de búsqueda semántica."""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Inicializar el servicio de reranking.
        
        Args:
            model_name: Nombre del modelo cross-encoder a usar.
                       Por defecto usa un modelo ligero y rápido.
        """
        self.model_name = model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self.reranker = None
        
        if CROSS_ENCODER_AVAILABLE:
            try:
                logger.info(f"Inicializando reranker: {self.model_name}")
                self.reranker = CrossEncoder(self.model_name)
                logger.info("Reranker inicializado correctamente")
            except Exception as e:
                logger.warning(f"Error al inicializar reranker: {e}. Reranking deshabilitado.")
                self.reranker = None
        else:
            logger.warning("sentence-transformers no disponible. Reranking deshabilitado.")
    
    def rerank(
        self, 
        query: str, 
        chunks: List[Dict], 
        top_k: Optional[int] = None
    ) -> List[Dict]:
        """
        Rerankear chunks basándose en la relevancia con la query.
        
        Args:
            query: Consulta del usuario
            chunks: Lista de chunks con 'content' y 'score' (opcional)
            top_k: Número máximo de resultados a retornar (None = todos)
            
        Returns:
            Lista de chunks rerankeada y ordenada por relevancia
        """
        if not self.reranker or not chunks:
            # Si no hay reranker, retornar chunks originales ordenados por score
            return sorted(
                chunks, 
                key=lambda x: x.get('score', 0.0),
                reverse=False  # Scores menores = más relevantes en similarity search
            )[:top_k] if top_k else chunks
        
        try:
            # Crear pares (query, chunk_content) para el cross-encoder
            pairs = [[query, chunk.get('content', '')] for chunk in chunks]
            
            # Obtener scores de relevancia del cross-encoder
            # Scores más altos = más relevantes
            rerank_scores = self.reranker.predict(pairs)
            
            # Combinar chunks con sus nuevos scores
            reranked_chunks = []
            for chunk, score in zip(chunks, rerank_scores):
                reranked_chunk = chunk.copy()
                reranked_chunk['rerank_score'] = float(score)
                # Mantener el score original para referencia
                reranked_chunk['original_score'] = chunk.get('score', None)
                reranked_chunks.append(reranked_chunk)
            
            # Ordenar por rerank_score descendente (mayor = más relevante)
            reranked_chunks.sort(key=lambda x: x['rerank_score'], reverse=True)
            
            # Retornar top_k si se especifica
            if top_k:
                reranked_chunks = reranked_chunks[:top_k]
            
            logger.debug(f"Rerankeado {len(chunks)} chunks, retornando {len(reranked_chunks)}")
            return reranked_chunks
            
        except Exception as e:
            logger.error(f"Error en reranking: {e}")
            # Fallback: retornar chunks originales ordenados por score
            return sorted(
                chunks,
                key=lambda x: x.get('score', 0.0),
                reverse=False
            )[:top_k] if top_k else chunks
    
    def is_available(self) -> bool:
        """Verificar si el reranking está disponible."""
        return self.reranker is not None

