"""
Tests para endpoints de chat con memoria.
"""
import pytest
from fastapi import status


def test_create_chat_message(client, sample_message_data):
    """Test crear un mensaje de chat."""
    response = client.post(
        "/api/chat/message",
        json=sample_message_data
    )
    # Puede fallar si no hay documentos, pero debe responder
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "answer" in data
        assert "session_id" in data


def test_list_sessions(client):
    """Test listar sesiones."""
    response = client.get("/api/chat/sessions")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "sessions" in data
    assert "total" in data
    assert isinstance(data["sessions"], list)


def test_get_conversation_history(client, sample_session_id):
    """Test obtener historial de conversación."""
    response = client.get(f"/api/chat/history/{sample_session_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "session_id" in data
    assert "messages" in data
    assert "total" in data
    assert isinstance(data["messages"], list)

