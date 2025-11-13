"""
Modelos de base de datos con SQLAlchemy.
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from sqlalchemy.sql import func

from app.core.database import Base


class Session(Base):
    """Modelo para sesiones de conversación."""
    
    __tablename__ = "sessions"
    
    session_id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, index=True)
    
    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relación con mensajes
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Session(session_id='{self.session_id}', created_at='{self.created_at}')>"
    
    def soft_delete(self):
        """Marcar sesión como eliminada (soft delete)."""
        from datetime import datetime
        self.deleted_at = datetime.utcnow()
    
    @property
    def is_deleted(self) -> bool:
        """Verificar si la sesión está eliminada."""
        return self.deleted_at is not None


class Message(Base):
    """Modelo para mensajes de conversación."""
    
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False, index=True)  # 'user' o 'assistant'
    content = Column(Text, nullable=False)
    # SQLAlchemy usa JSON para SQLite y automáticamente JSONB para PostgreSQL
    # Nota: 'metadata' es reservado en SQLAlchemy, usamos 'message_metadata' como atributo
    # pero mantenemos 'metadata' como nombre de columna en la BD
    message_metadata = Column(JSON, nullable=True, name='metadata')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Versionado (para auditoría)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    
    # Relación con sesión
    session = relationship("Session", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, session_id='{self.session_id}', role='{self.role}')>"
    
    def soft_delete(self):
        """Marcar mensaje como eliminado (soft delete)."""
        from datetime import datetime
        self.deleted_at = datetime.utcnow()
    
    @property
    def is_deleted(self) -> bool:
        """Verificar si el mensaje está eliminado."""
        return self.deleted_at is not None

