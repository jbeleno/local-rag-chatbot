"""
Tests de evaluación para el servicio RAG.
"""
import pytest
from app.services.rag_service import RAGService


@pytest.fixture
def rag_service():
    """Fixture para servicio RAG."""
    return RAGService()


def test_count_tokens_basic(rag_service):
    """Test básico de conteo de tokens."""
    text = "Hola, ¿cómo estás?"
    tokens = rag_service.count_tokens(text)
    assert tokens > 0
    assert isinstance(tokens, int)


def test_count_tokens_spanish(rag_service):
    """Test conteo de tokens en español."""
    text = "Este es un texto en español con varias palabras."
    tokens = rag_service.count_tokens(text)
    assert tokens > 5  # Debe tener varios tokens


def test_count_tokens_long_text(rag_service):
    """Test conteo de tokens en texto largo."""
    text = " ".join(["Palabra"] * 100)  # 100 palabras
    tokens = rag_service.count_tokens(text)
    assert tokens > 50  # Debe tener muchos tokens


def test_count_tokens_empty(rag_service):
    """Test conteo de tokens en texto vacío."""
    tokens = rag_service.count_tokens("")
    assert tokens == 0


def test_rag_service_has_token_encoder(rag_service):
    """Test que el servicio RAG tiene token encoder configurado."""
    # El encoder puede ser None si tiktoken no está disponible
    # pero el método count_tokens debe funcionar de todas formas
    assert hasattr(rag_service, 'token_encoder')
    assert hasattr(rag_service, 'count_tokens')

