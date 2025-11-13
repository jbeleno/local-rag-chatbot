# Backend - Chatbot RAG Local

Backend FastAPI para el chatbot RAG con soporte para documentación local y búsqueda web.

## Estructura

```
backend/
├── app/
│   ├── api/          # Rutas de la API
│   ├── core/         # Configuración
│   ├── models/       # Modelos Pydantic
│   ├── services/     # Servicios (RAG, búsqueda web, etc.)
│   └── main.py       # Aplicación FastAPI
├── main.py           # Punto de entrada
└── requirements.txt  # Dependencias
```

## Instalación

1. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Ejecución

Desde la raíz del proyecto (no desde backend/):

```bash
uvicorn backend.main:app --reload
```

O desde la carpeta backend/:

```bash
cd backend
uvicorn main:app --reload
```

El servidor estará disponible en `http://localhost:8000`

## API Documentation

Una vez que el servidor esté corriendo, visita:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

