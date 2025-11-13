"""
Modelos de base de datos para documentos con soft deletes y versionado.
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean
from sqlalchemy.sql import func

from app.core.database import Base


class Document(Base):
    """Modelo para documentos cargados con soft deletes y versionado."""
    
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, index=True)  # UUID del documento
    filename = Column(String, nullable=False, index=True)
    file_path = Column(String, nullable=False)
    file_extension = Column(String, nullable=False, index=True)
    file_size = Column(Integer, nullable=False)  # Tamaño en bytes
    text_length = Column(Integer, nullable=True)  # Longitud del texto extraído
    chunks_count = Column(Integer, nullable=True, default=0)  # Número de chunks
    
    # Metadatos adicionales (usar nombre diferente para evitar conflicto con SQLAlchemy)
    document_metadata = Column(Text, nullable=True, name='metadata')  # JSON como texto
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, index=True)
    
    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="false", index=True)
    
    # Versionado
    version = Column(Integer, nullable=False, default=1, server_default="1")
    
    def __repr__(self):
        return f"<Document(id='{self.id}', filename='{self.filename}')>"
    
    def soft_delete(self):
        """Marcar documento como eliminado (soft delete)."""
        from datetime import datetime
        self.deleted_at = datetime.utcnow()
        self.is_deleted = True
    
    def restore(self):
        """Restaurar documento eliminado."""
        self.deleted_at = None
        self.is_deleted = False
