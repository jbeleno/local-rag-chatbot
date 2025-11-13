"""
Tests para el servicio de chat.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.chat_service import ChatService
from app.core.config import settings


@pytest.fixture
def chat_service():
    """Fixture para servicio de chat."""
    return ChatService()


@pytest.fixture
def sample_session_id():
    """Fixture para ID de sesión."""
    return "test_session_chat_123"


@patch('app.services.chat_service.settings.MEMORY_ENABLED', True)
def test_chat_with_memory(chat_service, sample_session_id):
    """Test chat con memoria habilitada."""
    with patch.object(chat_service.rag_service, 'query') as mock_query:
        mock_query.return_value = {
            "answer": "Respuesta de prueba",
            "sources": ["doc1"],
            "relevant_chunks": []
        }
        
        result = chat_service.chat("Hola", sample_session_id)
        
        assert result["answer"] == "Respuesta de prueba"
        assert result["session_id"] == sample_session_id
        assert "sources" in result
        mock_query.assert_called_once()


@patch('app.services.chat_service.settings.MEMORY_ENABLED', False)
def test_chat_without_memory(chat_service, sample_session_id):
    """Test chat sin memoria."""
    with patch.object(chat_service.rag_service, 'query') as mock_query:
        mock_query.return_value = {
            "answer": "Respuesta sin memoria",
            "sources": [],
            "relevant_chunks": []
        }
        
        result = chat_service.chat("Hola", sample_session_id)
        
        assert result["answer"] == "Respuesta sin memoria"
        mock_query.assert_called_once()


def test_chat_error_handling(chat_service, sample_session_id):
    """Test manejo de errores en chat."""
    with patch.object(chat_service.rag_service, 'query') as mock_query:
        mock_query.side_effect = Exception("Error de RAG")
        
        with pytest.raises(ValueError, match="Error al procesar chat"):
            chat_service.chat("Hola", sample_session_id)


def test_get_conversation_history(chat_service, sample_session_id):
    """Test obtener historial de conversación."""
    with patch.object(chat_service.memory_service, 'get_conversation_history') as mock_get:
        mock_get.return_value = [
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "Hola, ¿cómo estás?"}
        ]
        
        history = chat_service.get_conversation_history(sample_session_id)
        
        assert len(history) == 2
        assert history[0]["role"] == "user"
        mock_get.assert_called_once_with(sample_session_id)


def test_clear_conversation(chat_service, sample_session_id):
    """Test limpiar conversación."""
    with patch.object(chat_service.memory_service, 'clear_session') as mock_clear:
        mock_clear.return_value = True
        
        result = chat_service.clear_conversation(sample_session_id)
        
        assert result is True
        mock_clear.assert_called_once_with(sample_session_id)


def test_list_sessions(chat_service):
    """Test listar sesiones."""
    with patch.object(chat_service.memory_service, 'list_sessions') as mock_list:
        mock_list.return_value = [
            {"session_id": "session1", "message_count": 5},
            {"session_id": "session2", "message_count": 3}
        ]
        
        sessions = chat_service.list_sessions(limit=10)
        
        assert len(sessions) == 2
        mock_list.assert_called_once_with(10)

