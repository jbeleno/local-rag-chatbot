"""
Tests extendidos para el servicio de memoria.
"""
import pytest
from app.services.memory_service import MemoryService


@pytest.fixture
def memory_service():
    """Fixture para servicio de memoria."""
    return MemoryService()


@pytest.fixture
def sample_session_id():
    """Fixture para ID de sesión."""
    return "test_session_extended_123"


def test_format_history_for_llm(memory_service, sample_session_id):
    """Test formatear historial para LLM."""
    # Usar un ID único para este test
    unique_session_id = f"{sample_session_id}_format_test"
    
    # Crear sesión y agregar mensajes
    memory_service.create_session(unique_session_id)
    memory_service.add_message(unique_session_id, "user", "Pregunta 1")
    memory_service.add_message(unique_session_id, "assistant", "Respuesta 1")
    memory_service.add_message(unique_session_id, "user", "Pregunta 2")
    
    formatted = memory_service.format_history_for_llm(unique_session_id)
    
    assert "Historial de conversación anterior" in formatted
    assert "Usuario" in formatted
    assert "Asistente" in formatted
    assert "Pregunta 1" in formatted
    assert "Respuesta 1" in formatted


def test_format_history_empty(memory_service, sample_session_id):
    """Test formatear historial vacío."""
    # Usar un ID único para este test
    unique_session_id = f"{sample_session_id}_empty_test"
    memory_service.create_session(unique_session_id)
    
    formatted = memory_service.format_history_for_llm(unique_session_id)
    
    assert formatted == ""


def test_add_message_with_metadata(memory_service, sample_session_id):
    """Test agregar mensaje con metadatos."""
    # Usar un ID único para este test
    unique_session_id = f"{sample_session_id}_metadata_test"
    memory_service.create_session(unique_session_id)
    
    metadata = {"source": "test", "score": 0.9}
    result = memory_service.add_message(
        session_id=unique_session_id,
        role="user",
        content="Mensaje con metadata",
        metadata=metadata
    )
    
    assert result is True
    
    # Verificar que se guardó correctamente
    history = memory_service.get_conversation_history(unique_session_id)
    assert len(history) == 1
    assert history[0]["metadata"] == metadata


def test_get_conversation_history_with_limit(memory_service, sample_session_id):
    """Test obtener historial con límite."""
    # Usar un ID único para este test
    unique_session_id = f"{sample_session_id}_limit_test"
    memory_service.create_session(unique_session_id)
    
    # Agregar más mensajes que el límite
    for i in range(15):
        memory_service.add_message(unique_session_id, "user", f"Mensaje {i}")
    
    # Obtener con límite
    history = memory_service.get_conversation_history(unique_session_id, limit=5)
    
    assert len(history) == 5


def test_get_conversation_history_chronological_order(memory_service, sample_session_id):
    """Test que el historial está en orden cronológico."""
    # Usar un ID único para este test
    unique_session_id = f"{sample_session_id}_chrono_test"
    memory_service.create_session(unique_session_id)
    
    memory_service.add_message(unique_session_id, "user", "Primero")
    memory_service.add_message(unique_session_id, "assistant", "Segundo")
    memory_service.add_message(unique_session_id, "user", "Tercero")
    
    history = memory_service.get_conversation_history(unique_session_id)
    
    assert len(history) == 3
    assert history[0]["content"] == "Primero"
    assert history[1]["content"] == "Segundo"
    assert history[2]["content"] == "Tercero"


def test_list_sessions_with_limit(memory_service):
    """Test listar sesiones con límite."""
    # Crear múltiples sesiones
    for i in range(5):
        session_id = f"test_session_{i}"
        memory_service.create_session(session_id)
        memory_service.add_message(session_id, "user", f"Test {i}")
    
    sessions = memory_service.list_sessions(limit=3)
    
    assert len(sessions) <= 3


def test_create_session_duplicate(memory_service, sample_session_id):
    """Test crear sesión duplicada (no debe fallar)."""
    result1 = memory_service.create_session(sample_session_id)
    result2 = memory_service.create_session(sample_session_id)
    
    assert result1 is True
    assert result2 is True  # No debe fallar si ya existe


def test_clear_session_nonexistent(memory_service):
    """Test limpiar sesión que no existe."""
    result = memory_service.clear_session("nonexistent_session")
    
    # Debe retornar True incluso si no existe
    assert result is True

