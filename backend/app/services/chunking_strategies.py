"""
Múltiples estrategias de chunking para diferentes tipos de documentos.
"""
import logging
from typing import List, Dict
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
    TokenTextSplitter
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class ChunkingStrategies:
    """Estrategias de chunking para diferentes tipos de documentos."""
    
    def __init__(self):
        """Inicializar todas las estrategias de chunking."""
        # Estrategia 1: Recursiva (por defecto) - mejor para texto general
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Estrategia 2: Por párrafos - mejor para documentos estructurados
        self.paragraph_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE * 2,  # Párrafos pueden ser más largos
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n"]  # Solo separar por párrafos
        )
        
        # Estrategia 3: Por caracteres - para código o texto sin estructura
        self.character_splitter = CharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len
        )
        
        # Estrategia 4: Semántica (basada en tokens) - mejor preservación de contexto
        # Nota: Requiere tiktoken, usamos aproximación con palabras
        self.token_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=self._count_tokens_approx,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def _count_tokens_approx(self, text: str) -> int:
        """
        Aproximación de conteo de tokens (1.3 tokens por palabra promedio).
        
        Args:
            text: Texto a contar
            
        Returns:
            Aproximación de número de tokens
        """
        return int(len(text.split()) * 1.3)
    
    def chunk_recursive(self, text: str) -> List[str]:
        """
        Chunking recursivo (por defecto).
        Mejor para: Texto general, documentos mixtos.
        
        Args:
            text: Texto a dividir
            
        Returns:
            Lista de chunks
        """
        return self.recursive_splitter.split_text(text)
    
    def chunk_by_paragraphs(self, text: str) -> List[str]:
        """
        Chunking por párrafos.
        Mejor para: Documentos estructurados, artículos, libros.
        
        Args:
            text: Texto a dividir
            
        Returns:
            Lista de chunks (párrafos)
        """
        return self.paragraph_splitter.split_text(text)
    
    def chunk_by_characters(self, text: str) -> List[str]:
        """
        Chunking por caracteres.
        Mejor para: Código, texto sin estructura, datos tabulares.
        
        Args:
            text: Texto a dividir
            
        Returns:
            Lista de chunks
        """
        return self.character_splitter.split_text(text)
    
    def chunk_by_tokens(self, text: str) -> List[str]:
        """
        Chunking basado en tokens (aproximado).
        Mejor para: Texto donde importa el contexto semántico.
        
        Args:
            text: Texto a dividir
            
        Returns:
            Lista de chunks
        """
        return self.token_splitter.split_text(text)
    
    def chunk_adaptive(self, text: str, file_extension: str = None) -> List[str]:
        """
        Seleccionar estrategia de chunking automáticamente según el tipo de archivo.
        
        Args:
            text: Texto a dividir
            file_extension: Extensión del archivo (opcional)
            
        Returns:
            Lista de chunks
        """
        if file_extension:
            ext = file_extension.lower()
            
            # PDFs y DOCX: usar párrafos (generalmente bien estructurados)
            if ext in ['pdf', 'docx', 'doc']:
                logger.debug(f"Usando chunking por párrafos para {ext}")
                return self.chunk_by_paragraphs(text)
            
            # TXT: usar recursivo (más flexible)
            elif ext == 'txt':
                logger.debug(f"Usando chunking recursivo para {ext}")
                return self.chunk_recursive(text)
        
        # Por defecto: recursivo
        return self.chunk_recursive(text)
    
    def chunk_with_strategy(
        self, 
        text: str, 
        strategy: str = "recursive",
        file_extension: str = None
    ) -> List[str]:
        """
        Chunking con estrategia específica.
        
        Args:
            text: Texto a dividir
            strategy: Estrategia a usar ('recursive', 'paragraphs', 'characters', 'tokens', 'adaptive')
            file_extension: Extensión del archivo (para estrategia 'adaptive')
            
        Returns:
            Lista de chunks
        """
        strategy = strategy.lower()
        
        if strategy == "recursive":
            return self.chunk_recursive(text)
        elif strategy == "paragraphs":
            return self.chunk_by_paragraphs(text)
        elif strategy == "characters":
            return self.chunk_by_characters(text)
        elif strategy == "tokens":
            return self.chunk_by_tokens(text)
        elif strategy == "adaptive":
            return self.chunk_adaptive(text, file_extension)
        else:
            logger.warning(f"Estrategia desconocida '{strategy}', usando recursiva")
            return self.chunk_recursive(text)

