"""
Servicio para expansión y reescritura de queries para mejorar la recuperación.
"""
import logging
import re
from typing import List, Set

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    spacy = None

from app.core.config import settings

logger = logging.getLogger(__name__)


class QueryExpansionService:
    """Servicio para expandir y reescribir queries."""
    
    def __init__(self):
        """Inicializar el servicio de expansión de queries."""
        self.nlp = None
        
        if SPACY_AVAILABLE:
            try:
                # Intentar cargar modelo en español
                try:
                    self.nlp = spacy.load("es_core_news_sm")
                    logger.info("Modelo spaCy en español cargado")
                except OSError:
                    # Si no está disponible, intentar inglés
                    try:
                        self.nlp = spacy.load("en_core_web_sm")
                        logger.info("Modelo spaCy en inglés cargado (fallback)")
                    except OSError:
                        logger.warning("No se encontró modelo spaCy. Expansión de queries limitada.")
            except Exception as e:
                logger.warning(f"Error al cargar spaCy: {e}. Expansión de queries limitada.")
        
        # Diccionario básico de sinónimos comunes (puede expandirse)
        self.synonyms = {
            'qué': ['cuál', 'cómo', 'dónde'],
            'cómo': ['de qué manera', 'de qué forma'],
            'cuándo': ['en qué momento', 'en qué fecha'],
            'dónde': ['en qué lugar', 'en qué sitio'],
            'por qué': ['cuál es la razón', 'cuál es el motivo'],
            'explicar': ['describir', 'detallar', 'mostrar'],
            'definir': ['explicar', 'describir', 'qué es'],
            'ejemplo': ['ejemplos', 'casos', 'instancias'],
            'diferencia': ['diferencias', 'comparar', 'contrastar'],
            'ventaja': ['ventajas', 'beneficios', 'pros'],
            'desventaja': ['desventajas', 'contra', 'contras']
        }
    
    def expand_query(self, query: str) -> str:
        """
        Expandir query agregando sinónimos y variaciones.
        
        Args:
            query: Query original
            
        Returns:
            Query expandida
        """
        if not query:
            return query
        
        expanded_terms = []
        words = query.lower().split()
        
        for word in words:
            # Limpiar palabra (remover puntuación)
            clean_word = re.sub(r'[^\wáéíóúñü]', '', word)
            
            # Agregar palabra original
            expanded_terms.append(word)
            
            # Agregar sinónimos si existen
            if clean_word in self.synonyms:
                expanded_terms.extend(self.synonyms[clean_word])
        
        # Combinar términos expandidos
        expanded_query = " ".join(expanded_terms)
        
        # Si no hubo expansión, retornar original
        if expanded_query == query.lower():
            return query
        
        logger.debug(f"Query expandida: '{query}' -> '{expanded_query}'")
        return expanded_query
    
    def extract_keywords(self, query: str) -> List[str]:
        """
        Extraer palabras clave de la query usando NLP.
        
        Args:
            query: Query original
            
        Returns:
            Lista de palabras clave
        """
        if not self.nlp or not query:
            # Fallback: extraer palabras significativas manualmente
            return self._extract_keywords_manual(query)
        
        try:
            doc = self.nlp(query)
            # Extraer sustantivos, adjetivos y verbos (palabras significativas)
            keywords = [
                token.lemma_.lower() 
                for token in doc 
                if token.pos_ in ['NOUN', 'ADJ', 'VERB'] 
                and not token.is_stop 
                and not token.is_punct
            ]
            return keywords if keywords else self._extract_keywords_manual(query)
        except Exception as e:
            logger.warning(f"Error al extraer keywords con spaCy: {e}")
            return self._extract_keywords_manual(query)
    
    def _extract_keywords_manual(self, query: str) -> List[str]:
        """
        Extraer palabras clave manualmente (fallback).
        
        Args:
            query: Query original
            
        Returns:
            Lista de palabras clave
        """
        # Stop words en español
        stop_words = {
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
            'de', 'del', 'al', 'a', 'en', 'por', 'para', 'con', 'sin',
            'es', 'son', 'está', 'están', 'ser', 'estar', 'tener',
            'y', 'o', 'pero', 'mas', 'sino', 'aunque', 'que', 'qué'
        }
        
        # Limpiar y dividir
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def rewrite_query(self, query: str, mode: str = "expand") -> str:
        """
        Reescribir query según el modo especificado.
        
        Args:
            query: Query original
            mode: Modo de reescritura ('expand', 'keywords', 'original')
            
        Returns:
            Query reescrita
        """
        if mode == "expand":
            return self.expand_query(query)
        elif mode == "keywords":
            keywords = self.extract_keywords(query)
            return " ".join(keywords) if keywords else query
        elif mode == "original":
            return query
        else:
            logger.warning(f"Modo desconocido '{mode}', retornando query original")
            return query
    
    def is_available(self) -> bool:
        """Verificar si el servicio está disponible."""
        return True  # Siempre disponible (tiene fallback manual)

