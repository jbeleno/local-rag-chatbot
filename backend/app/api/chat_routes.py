"""
Chat endpoints with memory and integrated RAG.
"""
import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.models.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationHistoryResponse,
    ClearConversationResponse,
    SessionListResponse,
    SessionInfo,
    ErrorResponse,
    MessageHistory,
    ChunkInfo,
    WebResultInfo
)
from app.services.chat_service import ChatService
from app.core.dependencies import ChatServiceDep

logger = logging.getLogger(__name__)

# API Router
router = APIRouter(prefix="/api/chat", tags=["Chat with Memory"])


@router.post(
    "/message",
    response_model=ChatMessageResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def send_chat_message(
    request: ChatMessageRequest,
    chat_service: ChatService = ChatServiceDep
):
    """
    Send a message in a conversation with memory.
    
    The system:
    1. Retrieves session history
    2. Searches for relevant information in uploaded documents
    3. Generates response using LLM with context
    4. Saves message and response in memory
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty"
            )
        
        if not request.session_id or not request.session_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="session_id is required"
            )
        
        logger.info(f"Processing message for session: {request.session_id}, mode: {request.mode}")
        
        # Procesar chat con el modo especificado
        result = chat_service.chat(
            query=request.query,
            session_id=request.session_id,
            mode=request.mode
        )
        
        # Convert chunks to response format
        relevant_chunks = [
            ChunkInfo(
                content=chunk["content"],
                score=chunk["score"],
                metadata=chunk["metadata"]
            )
            for chunk in result.get("relevant_chunks", [])
        ]
        
        # Prepare response according to mode
        response_data = {
            "answer": result["answer"],
            "sources": result.get("sources", []),
            "relevant_chunks": relevant_chunks,
            "query": result["query"],
            "session_id": result["session_id"],
            "mode": result.get("mode", "docs")
        }
        
        # Add web information if hybrid mode
        if result.get("mode") == "hybrid":
            response_data["sources_web"] = result.get("sources_web", [])
            response_data["web_results"] = [
                WebResultInfo(**web_result) for web_result in result.get("web_results", [])
            ]
        
        return ChatMessageResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error processing message: {str(e)}"
        )


@router.get(
    "/history/{session_id}",
    response_model=ConversationHistoryResponse,
    responses={
        500: {"model": ErrorResponse}
    }
)
async def get_conversation_history(
    session_id: str,
    chat_service: ChatService = ChatServiceDep
):
    """
    Get conversation history for a session.
    """
    try:
        history = chat_service.get_conversation_history(session_id)
        
        messages = [
            MessageHistory(
                role=msg["role"],
                content=msg["content"],
                created_at=msg["created_at"],
                metadata=msg.get("metadata")
            )
            for msg in history
        ]
        
        return ConversationHistoryResponse(
            session_id=session_id,
            messages=messages,
            total=len(messages)
        )
        
    except Exception as e:
        logger.error(f"Error getting history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error getting history: {str(e)}"
        )


@router.delete(
    "/history/{session_id}",
    response_model=ClearConversationResponse,
    responses={
        500: {"model": ErrorResponse}
    }
)
async def clear_conversation(
    session_id: str,
    chat_service: ChatService = ChatServiceDep
):
    """
    Clear conversation history for a session.
    """
    try:
        success = chat_service.clear_conversation(session_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not clear history"
            )
        
        return ClearConversationResponse(
            status="success",
            session_id=session_id,
            message="Conversation history cleared successfully."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error clearing history: {str(e)}"
        )


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    responses={
        500: {"model": ErrorResponse}
    }
)
async def list_sessions(
    limit: int = 50,
    chat_service: ChatService = ChatServiceDep
):
    """
    List all conversation sessions ordered by update date.
    """
    try:
        sessions_data = chat_service.list_sessions(limit)
        
        sessions = [
            SessionInfo(
                session_id=session["session_id"],
                created_at=session["created_at"],
                updated_at=session["updated_at"],
                message_count=session["message_count"]
            )
            for session in sessions_data
        ]
        
        return SessionListResponse(
            sessions=sessions,
            total=len(sessions)
        )
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error listing sessions: {str(e)}"
        )


@router.delete(
    "/sessions/cleanup-empty",
    response_model=dict,
    responses={
        500: {"model": ErrorResponse}
    }
)
async def cleanup_empty_sessions(
    chat_service: ChatService = ChatServiceDep
):
    """
    Delete all sessions that have no messages (empty sessions).
    """
    try:
        deleted_count = chat_service.memory_service.delete_empty_sessions()
        
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "message": f"Deleted {deleted_count} empty sessions"
        }
        
    except Exception as e:
        logger.error(f"Error cleaning empty sessions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error cleaning empty sessions: {str(e)}"
        )

