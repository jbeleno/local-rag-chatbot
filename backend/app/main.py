"""
Main FastAPI application for the local RAG chatbot.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api import routes
from app.api import chat_routes

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Configure specific level for noisy modules
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("chromadb.telemetry").setLevel(logging.ERROR)
logging.getLogger("primp").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router)
app.include_router(chat_routes.router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Local RAG Chatbot API",
        "version": settings.API_VERSION,
        "docs": "/docs",
        "endpoints": {
            "documents": {
                "upload": "/api/documents/upload",
                "list": "/api/documents/list",
                "delete": "/api/documents/{document_id}"
            },
            "chat": {
                "message": "/api/chat/message",
                "history": "/api/chat/history/{session_id}",
                "clear_history": "/api/chat/history/{session_id}"
            },
            "rag": {
                "query": "/api/chat/query",
                "query_docs": "/api/chat/query-docs",
                "query_hybrid": "/api/chat/query-hybrid"
            }
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    from app.services.web_search import WebSearchService
    
    # Check web search status
    web_search = WebSearchService()
    duckduckgo_status = "available" if web_search.ddgs else "unavailable"
    
    return {
        "status": "healthy",
        "llm_model": settings.LLM_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "ollama_url": settings.OLLAMA_BASE_URL,
        "memory_enabled": settings.MEMORY_ENABLED,
        "web_search": {
            "enabled": settings.WEB_SEARCH_ENABLED,
            "duckduckgo": {
                "status": duckduckgo_status
            }
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

