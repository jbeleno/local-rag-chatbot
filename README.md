# Local RAG Chatbot

A fully local RAG (Retrieval-Augmented Generation) chatbot system that combines local documentation with real-time web search.

## 🏗️ Project Structure

```
chatbot/
├── backend/          # FastAPI Backend
│   ├── app/         # Application code
│   ├── main.py      # Entry point
│   └── requirements.txt
├── frontend/        # Web frontend
│   └── index.html   # Chatbot interface
└── data/            # Data (documents, database, etc.)
```

## 🚀 Quick Start

### Backend

1. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Run server:
```bash
# From project root
uvicorn backend.main:app --reload

# Or from backend/
cd backend
uvicorn main:app --reload
```

### Frontend

1. Open `frontend/index.html` in your browser, or serve with an HTTP server:
```bash
cd frontend
python -m http.server 3000
```

2. Open `http://localhost:3000` in your browser.

## 📋 Requirements

- Python 3.11+
- Ollama with Qwen2.5-7B model installed
- Node.js (optional, for serving the frontend)

## 🔧 Configuration

See `backend/app/core/config.py` to configure:
- LLM and embedding models
- Data paths
- Web search configuration
- LLM parameters

## 📚 API Documentation

Once the backend is running:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🎯 Features

- ✅ Fully local RAG
- ✅ Two modes: Documentation only and Hybrid (docs + web)
- ✅ Web search with DuckDuckGo
- ✅ Relevance filtering of chunks
- ✅ Modern web interface
- ✅ Complete REST API
- ✅ Bilingual support (ES/EN)
- ✅ Conversational memory
- ✅ Advanced RAG features (reranking, query expansion, caching)

## 🌐 Language Support

The system supports both Spanish and English:
- **Frontend**: Bilingual interface with language selector
- **Backend**: Automatic language detection for LLM responses
- **API**: Error messages in English (standard)

## 🔧 Advanced Features

- **Reranking**: Cross-encoder models for improved retrieval accuracy
- **Query Expansion**: Automatic query enhancement with synonyms
- **Caching**: LRU cache for embeddings and TTL cache for responses
- **Multiple Chunking Strategies**: Recursive, paragraphs, characters, tokens, adaptive
- **Async Processing**: Background tasks for document processing
- **Conversational Memory**: Persistent session management with PostgreSQL
