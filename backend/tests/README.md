# Tests del Chatbot RAG

Este directorio contiene los tests automatizados para el proyecto.

## Estructura

```
tests/
├── conftest.py              # Configuración global de pytest
├── test_api/                # Tests de endpoints de la API
│   ├── test_routes.py       # Tests de endpoints generales
│   └── test_chat_routes.py  # Tests de endpoints de chat
├── test_services/           # Tests de servicios
│   ├── test_memory_service.py    # Tests del servicio de memoria
│   └── test_rag_evaluation.py    # Tests de evaluación RAG
└── test_utils/              # Tests de utilidades
    └── test_token_counting.py    # Tests de conteo de tokens
```

## Ejecutar Tests

### Todos los tests
```bash
pytest
```

### Con coverage
```bash
pytest --cov=app --cov-report=html --cov-report=term
```

### Tests específicos
```bash
pytest tests/test_api/
pytest tests/test_services/
pytest tests/test_utils/
```

### Un test específico
```bash
pytest tests/test_api/test_routes.py::test_health_check
```

## Scripts

- `scripts/run_tests.sh` (Linux/Mac) - Ejecuta tests con coverage
- `scripts/run_tests.bat` (Windows) - Ejecuta tests con coverage

## Coverage

El proyecto tiene un objetivo de coverage mínimo del 50% (configurado en `pytest.ini`).

Para ver el reporte de coverage:
1. Ejecuta los tests con coverage: `pytest --cov=app --cov-report=html`
2. Abre `htmlcov/index.html` en tu navegador

## Notas

- Los tests usan una base de datos SQLite en memoria para aislar cada test
- Los tests de API usan `TestClient` de FastAPI para simular requests HTTP
- Los tests de servicios prueban la lógica de negocio directamente

