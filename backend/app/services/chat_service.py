"""
Integrated chat service that combines LLM and memory.
"""
import logging
from typing import Dict, List

from app.services.rag_service import RAGService
from app.services.memory_service import MemoryService
from app.core.config import settings

logger = logging.getLogger(__name__)


class ChatService:
    """Integrated chat service with memory and RAG."""
    
    def __init__(self):
        """Initialize chat service."""
        self.rag_service = RAGService()
        self.memory_service = MemoryService()
        logger.info("Chat Service initialized")
    
    def chat(self, query: str, session_id: str, mode: str = "docs") -> Dict:
        """
        Process chat message with memory and RAG.
        
        Args:
            query: User message
            session_id: Conversation session ID
            mode: Search mode ('docs' or 'hybrid')
            
        Returns:
            Dictionary with response and metadata
        """
        try:
            # Detect language from query
            language = self.rag_service.detect_language(query)
            
            # Get conversation history (with language detection)
            history_context = ""
            if settings.MEMORY_ENABLED:
                history_context = self.memory_service.format_history_for_llm(session_id, language=language)
            
            # Save user message in memory
            if settings.MEMORY_ENABLED:
                self.memory_service.add_message(
                    session_id=session_id,
                    role="user",
                    content=query,
                    metadata=None
                )
            
            # Perform RAG query according to mode
            if mode == "hybrid":
                rag_result = self.rag_service.query_hybrid(query, history_context=history_context)
                # For hybrid mode, include web sources as well
                sources = rag_result.get("sources_docs", [])
                sources_web = rag_result.get("sources_web", [])
            else:
                rag_result = self.rag_service.query_docs_only(query, history_context=history_context)
                sources = rag_result.get("sources", [])
                sources_web = []
            
            # Get response
            answer = rag_result.get("answer", "Could not generate a response.")
            
            # Save assistant response in memory
            if settings.MEMORY_ENABLED:
                metadata = {
                    "sources": sources,
                    "sources_web": sources_web if mode == "hybrid" else [],
                    "mode": mode
                }
                self.memory_service.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=answer,
                    metadata=metadata
                )
            
            # Prepare response according to mode
            result = {
                "answer": answer,
                "sources": sources,
                "relevant_chunks": rag_result.get("relevant_chunks", []),
                "query": query,
                "session_id": session_id,
                "mode": mode
            }
            
            # Add web information if hybrid mode
            if mode == "hybrid":
                result["sources_web"] = sources_web
                result["web_results"] = rag_result.get("web_results", [])
            
            return result
            
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            raise ValueError(f"Error processing chat: {str(e)}")
    
    def get_conversation_history(self, session_id: str) -> List[Dict]:
        """
        Get conversation history.
        
        Args:
            session_id: Session ID
            
        Returns:
            List of messages
        """
        return self.memory_service.get_conversation_history(session_id)
    
    def clear_conversation(self, session_id: str) -> bool:
        """
        Clear conversation history.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if cleared successfully
        """
        return self.memory_service.clear_session(session_id)
    
    def list_sessions(self, limit: int = 50) -> List[Dict]:
        """
        List all conversation sessions.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of sessions with information
        """
        return self.memory_service.list_sessions(limit)

