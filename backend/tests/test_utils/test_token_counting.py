"""
Tests para conteo de tokens con tiktoken.
"""
import pytest
import tiktoken


def test_tiktoken_available():
    """Test que tiktoken está disponible."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        assert encoding is not None
    except Exception as e:
        pytest.skip(f"tiktoken no disponible: {e}")


def test_count_tokens_basic():
    """Test básico de conteo de tokens."""
    encoding = tiktoken.get_encoding("cl100k_base")
    text = "Hola, ¿cómo estás?"
    tokens = encoding.encode(text)
    assert len(tokens) > 0
    assert isinstance(len(tokens), int)


def test_count_tokens_spanish():
    """Test conteo de tokens en español."""
    encoding = tiktoken.get_encoding("cl100k_base")
    text = "Este es un texto en español con varias palabras."
    tokens = encoding.encode(text)
    assert len(tokens) > 5  # Debe tener varios tokens


def test_count_tokens_long_text():
    """Test conteo de tokens en texto largo."""
    encoding = tiktoken.get_encoding("cl100k_base")
    text = " ".join(["Palabra"] * 100)  # 100 palabras
    tokens = encoding.encode(text)
    assert len(tokens) > 50  # Debe tener muchos tokens


def test_token_encoding_decoding():
    """Test que encoding y decoding funcionan correctamente."""
    encoding = tiktoken.get_encoding("cl100k_base")
    original_text = "Hola mundo"
    tokens = encoding.encode(original_text)
    decoded_text = encoding.decode(tokens)
    assert decoded_text == original_text

