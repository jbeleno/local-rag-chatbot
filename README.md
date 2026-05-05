# Local RAG Chatbot

[![Python](https://img.shields.io/badge/Python-3.11+-3670A0?style=flat-square&logo=python&logoColor=ffdd54)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-000000?style=flat-square)](https://ollama.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF6F00?style=flat-square)](https://www.trychroma.com/)
[![LangChain](https://img.shields.io/badge/LangChain-0.1-1C3C3C?style=flat-square)](https://www.langchain.com/)
[![Sentence_Transformers](https://img.shields.io/badge/Sentence_Transformers-3.3-FFAA00?style=flat-square)](https://www.sbert.net/)

Sistema **RAG (Retrieval-Augmented Generation) 100% local** que combina documentación propia con búsqueda web en tiempo real. **Ningún token sale a un proveedor SaaS:** el LLM corre vía **Ollama** local, los embeddings con **Sentence-Transformers** local, y el vector store es **ChromaDB** persistente. Diseñado con técnicas avanzadas (reranking con cross-encoder, query expansion, caching, múltiples estrategias de chunking).

> Proyecto personal de exploración profunda de RAG: el objetivo no era solo "hacer un chatbot que use mis docs", sino implementar las capas que separan un RAG juguete de uno production-ready — reranking, expansión semántica de queries, caching de embeddings, memoria conversacional persistente y modos de búsqueda híbrida.

---

## Highlights

- 🔒 **100% local por defecto**: Ollama (LLM) + Sentence-Transformers (embeddings) + ChromaDB (vectores). Sin OpenAI, sin Anthropic, sin tokens enviados afuera.
- 🌐 **Modo híbrido opcional**: docs locales + búsqueda web (DuckDuckGo) cuando el contexto local no alcanza.
- 🎯 **Reranking con cross-encoder**: después del retrieval inicial, los chunks se re-puntúan para máxima precisión.
- 🧠 **Query expansion**: expansión automática del query con sinónimos antes de buscar — capta documentos que el query original no tocaría.
- 💾 **Caching multi-capa**: LRU para embeddings + TTL cache para respuestas LLM (configurable).
- 🧩 **5 estrategias de chunking**: `recursive`, `paragraphs`, `characters`, `tokens`, `adaptive` — el adaptativo ajusta el tamaño según el documento.
- 💬 **Memoria conversacional persistente**: sesiones en PostgreSQL (recomendado) o SQLite (fallback).
- 🔄 **Procesamiento async**: tareas de fondo para ingesta de documentos pesados.
- 🌍 **Bilingüe**: detección automática del idioma del query (ES/EN) en las respuestas.

## Stack

| Capa | Tecnología |
|---|---|
| Web framework | FastAPI 0.115 + Uvicorn |
| LLM (local) | Ollama (Qwen2.5 7B / Llama 3.1 / cualquier modelo descargado) |
| Embeddings (local) | Sentence-Transformers (`all-MiniLM-L6-v2` por defecto) |
| Vector store | ChromaDB persistente |
| Orchestration | LangChain 0.1.x |
| Reranking | Cross-encoder (sentence-transformers) |
| Memory | PostgreSQL (preferido) / SQLite |
| Document parsing | pypdf, python-docx |
| Web search | DuckDuckGo (`ddgs`) |
| Caching | cachetools (LRU + TTL) |

---

## Arquitectura

```
                 ┌──────────────────┐
                 │  Frontend (HTML) │
                 │  i18n EN/ES      │
                 └────────┬─────────┘
                          │ HTTP
                          ▼
┌──────────────────────────────────────────────────┐
│                  FastAPI                         │
│  /api/documents/upload   /api/chat/query         │
└────────┬───────────────────────────┬─────────────┘
         │                           │
         ▼                           ▼
┌──────────────────┐         ┌────────────────────┐
│ DocumentProcessor│         │   ChatService      │
│ - extract text   │         │ - mode selection   │
│ - chunk          │         │ - memory load      │
│   (5 strategies) │         └────────┬───────────┘
└────────┬─────────┘                  │
         ▼                            ▼
┌──────────────────┐         ┌────────────────────┐
│   Embeddings     │◀────────│  QueryExpansion    │
│   (sbert local)  │         │  (synonyms)        │
└────────┬─────────┘         └────────┬───────────┘
         ▼                            ▼
┌──────────────────┐         ┌────────────────────┐
│   ChromaDB       │────────▶│   Reranker         │
│   (persistent)   │         │  (cross-encoder)   │
└──────────────────┘         └────────┬───────────┘
                                      │
                                      ▼
                             ┌────────────────────┐
                             │  Ollama LLM        │
                             │  (local inference) │
                             └────────┬───────────┘
                                      │
                                      ▼
                             ┌────────────────────┐
                             │  Memory store      │
                             │  PG or SQLite      │
                             └────────────────────┘
```

### Pipeline del query

1. **Query expansion** — el query original se expande con sinónimos (configurable).
2. **Embedding** del query expandido con Sentence-Transformers.
3. **Retrieval** desde ChromaDB con `RERANKING_TOP_K` candidatos (vamos amplios).
4. **Reranking** con cross-encoder reduce a `TOP_K_RESULTS` los chunks más relevantes.
5. **Filtrado por umbral** de relevancia (`RELEVANCE_THRESHOLD`).
6. (Modo híbrido) **Web search** complementaria con DuckDuckGo si el contexto local es débil.
7. **Memory load** — historial de la sesión actual.
8. **Prompt assembly + Ollama call** — generación con `LLM_TEMPERATURE`, `LLM_TOP_P`, `LLM_NUM_CTX`.
9. **Memory persist** — la respuesta se guarda en la sesión.

---

## Quick start

### 0. Pre-requisito: Ollama corriendo localmente

```bash
# Descargar de https://ollama.com
ollama pull qwen2.5:7b      # ~4.4 GB, recomendado por balance calidad/RAM
# Alternativas: ollama pull llama3.1   o   ollama pull mistral
ollama serve                # corre en http://localhost:11434
```

> ⚠️ **RAM mínima recomendada**: 16 GB para Qwen2.5-7B. Si tienes ≤8 GB, usar modelos pequeños (`llama3.2:3b`, `phi3:mini`) y bajar `LLM_NUM_CTX`.

### 1. Configurar `.env`

Crear en la raíz del proyecto:

```env
# Models
LLM_MODEL=qwen2.5:7b
EMBEDDING_MODEL=all-MiniLM-L6-v2
LLM_TEMPERATURE=0.4

# Ollama
OLLAMA_BASE_URL=http://localhost:11434

# Chunking & retrieval
CHUNK_SIZE=700
CHUNK_OVERLAP=100
TOP_K_RESULTS=4
RELEVANCE_THRESHOLD=0.8

# Storage
CHROMA_PERSIST_DIR=../data/chroma_db
DOCUMENTS_DIR=../data/documents

# Optional: PostgreSQL para memoria conversacional persistente
# Si no se setea, fallback a SQLite local en MEMORY_DB_PATH.
USE_POSTGRES=false
# DATABASE_URL=postgresql://user:pass@host:5432/db
```

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload
# API en http://localhost:8000
# Swagger UI en http://localhost:8000/docs
```

### 3. Frontend

```bash
cd frontend
python -m http.server 3000
# Abrir http://localhost:3000
```

O simplemente abrir `frontend/index.html` directamente (puede haber CORS si fetch a `localhost:8000`).

---

## API endpoints

| Método | Path | Descripción |
|---|---|---|
| POST | `/api/documents/upload` | Subir PDF/TXT/DOCX (chunkea + embebe + guarda en ChromaDB) |
| GET | `/api/documents/list` | Listar documentos ingestados |
| DELETE | `/api/documents/{id}` | Borrar documento + sus chunks de Chroma |
| POST | `/api/chat/query` | Pregunta al RAG (modo solo-docs o híbrido) |
| GET | `/api/chat/history/{session_id}` | Historial de sesión |
| DELETE | `/api/chat/history/{session_id}` | Limpiar historial |

Documentación completa en `/docs` (Swagger UI auto-generado).

---

## Configuración avanzada

`backend/app/core/config.py` expone todos los parámetros como `pydantic-settings`. Los más importantes:

| Variable | Default | Notas |
|---|---|---|
| `LLM_MODEL` | `qwen2.5:7b` | Cualquier modelo disponible en `ollama list` |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Multilingüe, 384 dims, rápido |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 700 / 100 | Tradeoff: más grande = más contexto, menos precisión |
| `TOP_K_RESULTS` | 4 | Chunks finales que llegan al LLM |
| `RERANKING_TOP_K` | 5 | Top antes del reranking |
| `RELEVANCE_THRESHOLD` | 0.8 | Cosine distance — más bajo es más estricto |
| `CHUNKING_STRATEGY` | `adaptive` | `recursive`, `paragraphs`, `characters`, `tokens`, `adaptive` |
| `ENABLE_RERANKING` | `true` | Cross-encoder reranking on top of vector search |
| `ENABLE_QUERY_EXPANSION` | `true` | Expansión con sinónimos |
| `ENABLE_CACHE` | `true` | LRU embeddings + TTL responses |
| `WEB_SEARCH_ENABLED` | `true` | Modo híbrido con DuckDuckGo |
| `MEMORY_ENABLED` | `true` | Memoria conversacional |
| `USE_POSTGRES` | `false` | Si false, SQLite local |

---

## Estructura del proyecto

```
local-rag-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py            # pydantic-settings
│   │   │   ├── database.py          # SQLAlchemy + pool
│   │   │   ├── dependencies.py      # FastAPI Depends
│   │   │   └── validators.py
│   │   ├── api/
│   │   │   ├── routes.py            # Documents endpoints
│   │   │   └── chat_routes.py       # Chat + memory endpoints
│   │   ├── services/
│   │   │   ├── document_processor.py    # PDF/TXT/DOCX → chunks
│   │   │   ├── chunking_strategies.py   # 5 strategies
│   │   │   ├── rag_service.py           # Core RAG orchestration
│   │   │   ├── chat_service.py          # High-level chat flow
│   │   │   ├── reranking_service.py     # Cross-encoder
│   │   │   ├── query_expansion.py       # Synonym expansion
│   │   │   ├── cache_service.py         # LRU + TTL
│   │   │   ├── memory_service.py        # Session persistence
│   │   │   └── web_search.py            # DuckDuckGo integration
│   │   └── models/
│   │       ├── schemas.py
│   │       ├── document_models.py
│   │       └── database_models.py
│   ├── pytest.ini
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── styles.css
│   ├── script.js
│   └── js/i18n.js                  # Bilingüe ES/EN
├── data/                           # Generado en runtime
│   ├── chroma_db/                  # ChromaDB persistente
│   ├── documents/                  # Originales subidos
│   └── memory.db                   # SQLite fallback
├── QUICKSTART.md
└── README.md
```

---

## Resource footprint

| Recurso | Mínimo | Recomendado |
|---|---|---|
| RAM (con Qwen2.5-7B cargado) | 8 GB (modelos pequeños como `phi3:mini`) | 16 GB |
| Disco | 5 GB (modelo + libs) | 10 GB |
| GPU | No requerida (Ollama usa Metal/CUDA si están disponibles) | NVIDIA o Apple Silicon |
| RAM (servicio sin LLM) | ~500 MB | — |

> El consumo de RAM dominante es **Ollama con el modelo cargado**, no FastAPI. Bajar de modelo (Qwen 7B → Llama 3.2 3B → Phi3 mini) reduce dramáticamente el footprint.

---

## Mejoras pendientes (deuda técnica reconocida)

- **Migrar LangChain 0.1.x → 0.3.x**. Cambia el módulo de imports (chains → runnables, LCEL como API principal). Tracking explícito en este README porque el upgrade rompe varios servicios y requiere refactor.
- **Tests**: existe `pytest.ini` y deps de pytest, pero la suite todavía no está. Cubrir al menos `chunking_strategies`, `rag_service`, `memory_service`.
- **Dockerfile + docker-compose**: para reproducibilidad, especialmente con servicios laterales (Postgres). El servicio puede ser containerizado pero **Ollama queda fuera** (corre en host por GPU/Metal).
- **Streaming de respuestas** vía SSE/WebSocket — hoy las respuestas son request/response. Para queries largas (> 30 tokens/s) el UX mejora con streaming token-a-token.
- **Persistencia de embeddings cacheados** — hoy el cache LRU vive en memoria, se pierde al reiniciar.
- **Trazabilidad / observabilidad**: logs estructurados (JSON) + métricas Prometheus (latencia retrieval, latencia LLM, hit rate de cache).
- **Eval automatizada** del RAG: dataset de preguntas con respuestas esperadas + métricas (faithfulness, answer relevancy, context precision) — Ragas es buen framework.
- **Hybrid search BM25 + vector** (no solo vector): chunks raros pero exactos a veces se pierden con embeddings densos.
- **Multimodal**: ingestar imágenes en PDF (OCR + visual embeddings).

---

## Licencia

Proyecto personal de exploración. Disponible para uso educativo.
