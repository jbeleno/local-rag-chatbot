"""
Servicio para procesar documentos (PDF, TXT, DOCX) y dividirlos en chunks.
"""
import os
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

import pypdf  # successor of PyPDF2 (same maintainer, drop-in API)
from docx import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.services.chunking_strategies import ChunkingStrategies

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Procesador de documentos para extraer texto y crear chunks."""
    
    def __init__(self):
        """Inicializar el procesador de documentos."""
        # Mantener splitter original para compatibilidad
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Inicializar estrategias avanzadas de chunking
        self.chunking_strategies = ChunkingStrategies()
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extraer texto de un archivo PDF.
        
        Args:
            file_path: Ruta al archivo PDF
            
        Returns:
            Texto extraído del PDF
        """
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            logger.info(f"Texto extraído de PDF: {len(text)} caracteres")
            return text
        except Exception as e:
            logger.error(f"Error al extraer texto del PDF: {e}")
            raise ValueError(f"Error al procesar PDF: {str(e)}")
    
    def extract_text_from_txt(self, file_path: str) -> str:
        """
        Extraer texto de un archivo TXT.
        
        Args:
            file_path: Ruta al archivo TXT
            
        Returns:
            Texto extraído del TXT
        """
        try:
            # Intentar diferentes encodings
            encodings = ['utf-8', 'latin-1', 'cp1252']
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        text = file.read()
                    logger.info(f"Texto extraído de TXT ({encoding}): {len(text)} caracteres")
                    return text
                except UnicodeDecodeError:
                    continue
            raise ValueError("No se pudo decodificar el archivo TXT con ningún encoding")
        except Exception as e:
            logger.error(f"Error al extraer texto del TXT: {e}")
            raise ValueError(f"Error al procesar TXT: {str(e)}")
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """
        Extraer texto de un archivo DOCX.
        
        Args:
            file_path: Ruta al archivo DOCX
            
        Returns:
            Texto extraído del DOCX
        """
        try:
            doc = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            logger.info(f"Texto extraído de DOCX: {len(text)} caracteres")
            return text
        except Exception as e:
            logger.error(f"Error al extraer texto del DOCX: {e}")
            raise ValueError(f"Error al procesar DOCX: {str(e)}")
    
    def extract_text(self, file_path: str, file_extension: str) -> str:
        """
        Extraer texto de un archivo según su extensión.
        
        Args:
            file_path: Ruta al archivo
            file_extension: Extensión del archivo (pdf, txt, docx)
            
        Returns:
            Texto extraído
        """
        extension = file_extension.lower()
        
        if extension == 'pdf':
            return self.extract_text_from_pdf(file_path)
        elif extension == 'txt':
            return self.extract_text_from_txt(file_path)
        elif extension in ['docx', 'doc']:
            return self.extract_text_from_docx(file_path)
        else:
            raise ValueError(f"Formato de archivo no soportado: {extension}")
    
    def create_chunks(self, text: str, metadata: Dict, strategy: str = None) -> List[Dict]:
        """
        Dividir texto en chunks con metadatos usando estrategia especificada.
        
        Args:
            text: Texto a dividir
            metadata: Metadatos a agregar a cada chunk
            strategy: Estrategia de chunking a usar (None = usar configuración por defecto)
            
        Returns:
            Lista de chunks con metadatos
        """
        try:
            # Usar estrategia de configuración si no se especifica
            if strategy is None:
                strategy = settings.CHUNKING_STRATEGY
            
            # Obtener extensión del archivo para estrategia adaptativa
            file_extension = metadata.get("file_extension")
            
            # Dividir texto usando estrategia seleccionada
            if strategy == "recursive":
                chunks = self.text_splitter.split_text(text)
            else:
                chunks = self.chunking_strategies.chunk_with_strategy(
                    text, 
                    strategy=strategy,
                    file_extension=file_extension
                )
            
            # Agregar metadatos a cada chunk
            chunks_with_metadata = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    **metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunking_strategy": strategy
                }
                chunks_with_metadata.append({
                    "content": chunk,
                    "metadata": chunk_metadata
                })
            
            logger.info(f"Creados {len(chunks_with_metadata)} chunks usando estrategia '{strategy}'")
            return chunks_with_metadata
        except Exception as e:
            logger.error(f"Error al crear chunks: {e}")
            raise ValueError(f"Error al crear chunks: {str(e)}")
    
    def save_document(self, file_content: bytes, filename: str) -> Tuple[str, str]:
        """
        Guardar documento subido en el directorio de documentos.
        
        Args:
            file_content: Contenido del archivo en bytes
            filename: Nombre original del archivo
            
        Returns:
            Tupla con (document_id, file_path)
        """
        try:
            # Generar ID único para el documento
            document_id = str(uuid.uuid4())
            
            # Obtener extensión del archivo
            file_extension = Path(filename).suffix[1:]  # Sin el punto
            
            # Crear nombre de archivo único
            unique_filename = f"{document_id}.{file_extension}"
            file_path = os.path.join(settings.DOCUMENTS_DIR, unique_filename)
            
            # Guardar archivo
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"Documento guardado: {file_path}")
            return document_id, file_path
        except Exception as e:
            logger.error(f"Error al guardar documento: {e}")
            raise ValueError(f"Error al guardar documento: {str(e)}")
    
    def process_document(self, file_content: bytes, filename: str) -> Tuple[str, List[Dict]]:
        """
        Procesar un documento completo: guardar, extraer texto y crear chunks.
        
        Args:
            file_content: Contenido del archivo en bytes
            filename: Nombre original del archivo
            
        Returns:
            Tupla con (document_id, chunks_with_metadata)
        """
        try:
            # Guardar documento
            document_id, file_path = self.save_document(file_content, filename)
            
            # Obtener extensión
            file_extension = Path(filename).suffix[1:].lower()
            
            # Extraer texto
            text = self.extract_text(file_path, file_extension)
            
            if not text.strip():
                raise ValueError("El documento no contiene texto extraíble")
            
            # Crear metadatos
            metadata = {
                "document_id": document_id,
                "filename": filename,
                "file_path": file_path,
                "file_extension": file_extension,
                "uploaded_at": datetime.now().isoformat(),
                "text_length": len(text)
            }
            
            # Crear chunks
            chunks = self.create_chunks(text, metadata)
            
            return document_id, chunks
            
        except Exception as e:
            logger.error(f"Error al procesar documento: {e}")
            raise

