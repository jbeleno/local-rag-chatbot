"""
Tests extendidos para endpoints de chat.
"""
import pytest
from fastapi import status
from unittest.mock import patch, MagicMock


def test_send_chat_message_empty_query(client):
    """Test enviar mensaje con query vacía."""
    response = client.post(
        "/api/chat/message",
        json={"query": "", "session_id": "test_session"}
    )
    
    # FastAPI/Pydantic devuelve 422 para validación
    assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]


def test_send_chat_message_whitespace_query(client):
    """Test enviar mensaje con query solo espacios."""
    response = client.post(
        "/api/chat/message",
        json={"query": "   ", "session_id": "test_session"}
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_send_chat_message_missing_session_id(client):
    """Test enviar mensaje sin session_id."""
    response = client.post(
        "/api/chat/message",
        json={"query": "Hola"}
    )
    
    # Debe fallar por validación
    assert response.status_code in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_422_UNPROCESSABLE_ENTITY
    ]


def test_send_chat_message_empty_session_id(client):
    """Test enviar mensaje con session_id vacío."""
    response = client.post(
        "/api/chat/message",
        json={"query": "Hola", "session_id": ""}
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_send_chat_message_error_handling(client):
    """Test manejo de errores en send_chat_message."""
    with patch('app.api.chat_routes.chat_service') as mock_service:
        mock_service.chat.side_effect = Exception("Error interno")
        
        response = client.post(
            "/api/chat/message",
            json={"query": "Hola", "session_id": "test_session"}
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_get_conversation_history_error(client):
    """Test manejo de errores al obtener historial."""
    with patch('app.api.chat_routes.chat_service') as mock_service:
        mock_service.get_conversation_history.side_effect = Exception("Error de BD")
        
        response = client.get("/api/chat/history/test_session")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_clear_conversation_error(client):
    """Test manejo de errores al limpiar conversación."""
    with patch('app.api.chat_routes.chat_service') as mock_service:
        mock_service.clear_conversation.return_value = False
        
        response = client.delete("/api/chat/history/test_session")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_list_sessions_error(client):
    """Test manejo de errores al listar sesiones."""
    with patch('app.api.chat_routes.chat_service') as mock_service:
        mock_service.list_sessions.side_effect = Exception("Error de BD")
        
        response = client.get("/api/chat/sessions")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_clear_conversation(client, sample_session_id):
    """Test limpiar conversación."""
    with patch('app.api.chat_routes.chat_service') as mock_service:
        mock_service.clear_conversation.return_value = True
        
        response = client.delete(f"/api/chat/history/{sample_session_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"


def test_clear_conversation_nonexistent(client):
    """Test limpiar conversación inexistente."""
    response = client.delete("/api/chat/history/nonexistent_session")
    
    # Debe retornar 200 incluso si no existe
    assert response.status_code == status.HTTP_200_OK


def test_list_sessions_with_limit(client):
    """Test listar sesiones con límite."""
    response = client.get("/api/chat/sessions?limit=5")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "sessions" in data
    assert "total" in data
    assert isinstance(data["sessions"], list)


def test_get_conversation_history_empty(client):
    """Test obtener historial de sesión vacía."""
    response = client.get("/api/chat/history/empty_session")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 0
    assert isinstance(data["messages"], list)

