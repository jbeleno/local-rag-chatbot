"""
Service for managing memory and conversations using SQLAlchemy ORM.
"""
import logging
import json
import re
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.models.database_models import Session as SessionModel, Message as MessageModel

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for managing conversation memory using SQLAlchemy ORM."""
    
    def __init__(self):
        """Initialize the memory service."""
        self.max_history = settings.MAX_HISTORY_LENGTH
        logger.info("Memory Service initialized with SQLAlchemy ORM")
    
    def _detect_language(self, text: str) -> str:
        """
        Detect language of text using simple heuristics.
        
        Args:
            text: Text to analyze
            
        Returns:
            'es' or 'en'
        """
        text_lower = text.lower()
        
        # Spanish indicators
        spanish_indicators = [
            'ñ', 'á', 'é', 'í', 'ó', 'ú', 'ü',
            '¿', '¡', 'qué', 'cómo', 'dónde', 'cuándo', 'cuál', 'cuáles',
            'español', 'españa', 'mexico', 'colombia', 'argentina',
            'según', 'también', 'más', 'está', 'están', 'tiene', 'tienen'
        ]
        
        # English indicators
        english_indicators = [
            'the', 'is', 'are', 'what', 'how', 'where', 'when', 'which',
            'english', 'united states', 'usa', 'according', 'also', 'more',
            'has', 'have', 'been', 'this', 'that', 'these', 'those'
        ]
        
        spanish_count = sum(1 for indicator in spanish_indicators if indicator in text_lower)
        english_count = sum(1 for indicator in english_indicators if indicator in text_lower)
        
        # Default to Spanish if no clear indicator
        if english_count > spanish_count and english_count > 0:
            return 'en'
        return 'es'
    
    @contextmanager
    def _get_session(self) -> Session:
        """
        Context manager to get database session.
        
        Yields:
            SQLAlchemy Session
        """
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    
    def create_session(self, session_id: str) -> bool:
        """
        Create a new conversation session.
        
        Args:
            session_id: Unique session ID
            
        Returns:
            True if created successfully
        """
        try:
            with self._get_session() as db:
                # Try to create the session
                session = SessionModel(session_id=session_id)
                db.add(session)
                try:
                    db.commit()
                    logger.info(f"Session created: {session_id}")
                    return True
                except IntegrityError:
                    # Session already exists, not an error
                    db.rollback()
                    logger.debug(f"Session already exists: {session_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return False
    
    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> bool:
        """
        Add a message to the conversation.
        
        Args:
            session_id: Session ID
            role: Message role ('user' or 'assistant')
            content: Message content
            metadata: Additional metadata (optional)
            
        Returns:
            True if added successfully
        """
        try:
            with self._get_session() as db:
                # Create session if it doesn't exist (in the same transaction)
                session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
                if not session:
                    session = SessionModel(session_id=session_id)
                    db.add(session)
                    try:
                        db.flush()  # Flush to check for integrity error
                    except IntegrityError:
                        db.rollback()
                        # Session already exists, get it
                        session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
                
                # Create message
                message = MessageModel(
                    session_id=session_id,
                    role=role,
                    content=content,
                    message_metadata=metadata
                )
                db.add(message)
                
                # Update session timestamp
                if session:
                    session.updated_at = datetime.utcnow()
                
                # Commit everything together (session and message in the same transaction)
                db.commit()
                logger.debug(f"Message added to session {session_id}: {role}")
                return True
                
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return False
    
    def get_conversation_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session ID
            limit: Message limit (None = use max_history)
            
        Returns:
            List of messages ordered by date
        """
        try:
            if limit is None:
                limit = self.max_history
            
            with self._get_session() as db:
                # Get messages ordered by descending date
                messages = db.query(MessageModel).filter(
                    MessageModel.session_id == session_id
                ).order_by(
                    desc(MessageModel.created_at)
                ).limit(limit).all()
                
                # Convert to list of dictionaries (reverse order to have chronological)
                result = []
                for msg in reversed(messages):
                    result.append({
                        "role": msg.role,
                        "content": msg.content,
                        "metadata": msg.message_metadata,
                        "created_at": msg.created_at.isoformat() if msg.created_at else ""
                    })
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []
    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear history for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if cleared successfully
        """
        try:
            with self._get_session() as db:
                # Delete messages (session is kept)
                deleted = db.query(MessageModel).filter(
                    MessageModel.session_id == session_id
                ).delete()
                
                db.commit()
                logger.info(f"History cleared for session: {session_id} ({deleted} messages deleted)")
                return True
                
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
            return False
    
    def delete_empty_sessions(self) -> int:
        """
        Delete all sessions that have no messages.
        
        Returns:
            Number of sessions deleted
        """
        try:
            with self._get_session() as db:
                # Find sessions without messages using subquery
                from sqlalchemy import select
                sessions_with_messages = db.query(MessageModel.session_id).distinct().subquery()
                
                # Delete sessions that are not in the list of sessions with messages
                empty_sessions = db.query(SessionModel).filter(
                    ~SessionModel.session_id.in_(select(sessions_with_messages.c.session_id))
                ).all()
                
                count = len(empty_sessions)
                
                if count > 0:
                    for session in empty_sessions:
                        db.delete(session)
                    db.commit()
                    logger.info(f"Deleted {count} empty sessions")
                
                return count
        except Exception as e:
            logger.error(f"Error deleting empty sessions: {e}")
            return 0
    
    def format_history_for_llm(self, session_id: str, language: Optional[str] = None) -> str:
        """
        Format conversation history to include in LLM prompt.
        
        Args:
            session_id: Session ID
            language: Language code ('es' or 'en'). If None, detects from history.
            
        Returns:
            Formatted string with history
        """
        history = self.get_conversation_history(session_id)
        
        if not history:
            return ""
        
        # Detect language from history if not provided
        if language is None:
            # Use the last user message to detect language
            for msg in reversed(history):
                if msg["role"] == "user":
                    language = self._detect_language(msg["content"])
                    break
            # Default to Spanish if no user message found
            if language is None:
                language = 'es'
        
        # Format labels based on language
        if language == 'en':
            history_label = "Previous conversation history:"
            user_label = "User"
            assistant_label = "Assistant"
        else:
            history_label = "Historial de conversación anterior:"
            user_label = "Usuario"
            assistant_label = "Asistente"
        
        formatted = f"\n\n{history_label}\n"
        for msg in history:
            role_name = user_label if msg["role"] == "user" else assistant_label
            formatted += f"{role_name}: {msg['content']}\n"
        
        return formatted
    
    def list_sessions(self, limit: Optional[int] = 50) -> List[Dict]:
        """
        List all conversation sessions ordered by update date.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of dictionaries with session information
        """
        try:
            with self._get_session() as db:
                # Query with join and aggregation using SQLAlchemy
                sessions_query = db.query(
                    SessionModel.session_id,
                    SessionModel.created_at,
                    SessionModel.updated_at,
                    func.count(MessageModel.id).label('message_count')
                ).outerjoin(
                    MessageModel, SessionModel.session_id == MessageModel.session_id
                ).group_by(
                    SessionModel.session_id,
                    SessionModel.created_at,
                    SessionModel.updated_at
                ).order_by(
                    desc(SessionModel.updated_at)
                ).limit(limit).all()
                
                # Convert to list of dictionaries and filter empty sessions
                sessions = []
                for session_id, created_at, updated_at, message_count in sessions_query:
                    message_count = message_count or 0
                    # Only include sessions that have at least one message
                    if message_count > 0:
                        sessions.append({
                            "session_id": session_id,
                            "created_at": created_at.isoformat() if created_at else "",
                            "updated_at": updated_at.isoformat() if updated_at else "",
                            "message_count": message_count
                        })
                
                return sessions
                
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []
