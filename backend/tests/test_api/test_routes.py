"""
Tests para endpoints de la API.
"""
import pytest
from fastapi import status


def test_health_check(client):
    """Test del endpoint de health check."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert "llm_model" in data
    assert "embedding_model" in data


def test_root_endpoint(client):
    """Test del endpoint raíz."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "endpoints" in data


def test_list_documents_empty(client):
    """Test listar documentos cuando no hay ninguno."""
    response = client.get("/api/documents/list")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # Puede haber documentos de otros tests, solo verificamos la estructura
    assert "total" in data
    assert isinstance(data["documents"], list)
    assert isinstance(data["total"], int)


def test_query_without_documents(client):
    """Test de consulta sin documentos cargados."""
    response = client.post(
        "/api/chat/query-docs",
        json={"query": "¿Qué es Python?"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "answer" in data
    assert "sources" in data

