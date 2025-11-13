"""
Tests para el servicio de memoria.
"""
import pytest
from app.services.memory_service import MemoryService


@pytest.fixture
def memory_service():
    """Fixture para servicio de memoria."""
    return MemoryService()


def test_create_session(memory_service, sample_session_id):
    """Test crear una sesión."""
    result = memory_service.create_session(sample_session_id)
    assert result is True


def test_add_message(memory_service, sample_session_id):
    """Test agregar un mensaje."""
    # Crear sesión primero
    memory_service.create_session(sample_session_id)
    
    # Agregar mensaje
    result = memory_service.add_message(
        session_id=sample_session_id,
        role="user",
        content="Hola, ¿cómo estás?",
        metadata=None
    )
    assert result is True


def test_get_conversation_history(memory_service, sample_session_id):
    """Test obtener historial de conversación."""
    # Usar un ID único para este test
    unique_session_id = f"{sample_session_id}_history_test"
    
    # Crear sesión y agregar mensajes
    memory_service.create_session(unique_session_id)
    memory_service.add_message(unique_session_id, "user", "Pregunta 1")
    memory_service.add_message(unique_session_id, "assistant", "Respuesta 1")
    
    # Obtener historial
    history = memory_service.get_conversation_history(unique_session_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_list_sessions(memory_service, sample_session_id):
    """Test listar sesiones."""
    # Crear una sesión
    memory_service.create_session(sample_session_id)
    memory_service.add_message(sample_session_id, "user", "Test message")
    
    # Listar sesiones
    sessions = memory_service.list_sessions(limit=10)
    assert len(sessions) > 0
    assert any(s["session_id"] == sample_session_id for s in sessions)


def test_clear_session(memory_service, sample_session_id):
    """Test limpiar sesión."""
    # Crear sesión y agregar mensajes
    memory_service.create_session(sample_session_id)
    memory_service.add_message(sample_session_id, "user", "Test")
    
    # Limpiar
    result = memory_service.clear_session(sample_session_id)
    assert result is True
    
    # Verificar que está vacío
    history = memory_service.get_conversation_history(sample_session_id)
    assert len(history) == 0

