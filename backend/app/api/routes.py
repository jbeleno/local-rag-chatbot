"""
API endpoints for the RAG chatbot.
"""
import os
import logging
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

from app.models.schemas import (
    DocumentUploadResponse,
    QueryRequest,
    QueryResponse,
    QueryDocsResponse,
    QueryHybridResponse,
    DocumentListResponse,
    DocumentInfo,
    DeleteDocumentResponse,
    ErrorResponse,
    ChunkInfo,
    WebResultInfo
)
from app.services.document_processor import DocumentProcessor
from app.services.rag_service import RAGService
from app.core.config import settings
from app.core.dependencies import RAGServiceDep, DocumentProcessorDep
from app.core.validators import validate_file_extension, validate_file_size, validate_file_content, sanitize_filename
from fastapi import BackgroundTasks
from datetime import datetime

logger = logging.getLogger(__name__)

# Note: Services are now injected as dependencies in endpoints

# API Router
router = APIRouter(prefix="/api", tags=["RAG Chatbot"])


@router.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    document_processor: DocumentProcessor = DocumentProcessorDep,
    rag_service: RAGService = RAGServiceDep
):
    """
    Upload and process a document (PDF, TXT, DOCX).
    
    The document is processed automatically:
    - Text is extracted
    - Divided into chunks
    - Embeddings are generated
    - Saved to ChromaDB
    """
    try:
        # Sanitize filename
        safe_filename = sanitize_filename(file.filename)
        
        # Validate extension
        try:
            file_extension = validate_file_extension(safe_filename)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        # Read file content
        file_content = await file.read()
        
        # Validate size
        try:
            file_content = validate_file_size(file_content)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        # Validate actual file content
        try:
            file_content = validate_file_content(file_content, safe_filename)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        logger.info(f"Processing file: {safe_filename} ({len(file_content)} bytes)")
        
        # Process document asynchronously in background
        def process_document_task():
            try:
                document_id, chunks = document_processor.process_document(
                    file_content=file_content,
                    filename=safe_filename
                )
                chunks_added = rag_service.add_documents(chunks)
                logger.info(f"Document processed successfully: {document_id} ({chunks_added} chunks)")
            except Exception as e:
                logger.error(f"Error in async processing: {e}", exc_info=True)
        
        # Add task in background
        background_tasks.add_task(process_document_task)
        
        # Return immediate response (processing continues in background)
        # Note: To get the real document_id, you would need to save it before or use a queue
        # For now, we return a message indicating it's being processed
        return DocumentUploadResponse(
            status="processing",
            document_id="pending",  # Will be assigned when processing completes
            filename=safe_filename,
            chunks_created=0,
            message="Document received and processing. Processing will continue in the background."
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error processing document: {str(e)}"
        )


@router.post(
    "/chat/query",
    response_model=QueryResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def query_chatbot(
    request: QueryRequest,
    rag_service: RAGService = RAGServiceDep
):
    """
    Ask a question to the RAG chatbot.
    
    The system:
    1. Searches for relevant chunks using semantic search
    2. Generates a response using the local LLM with the retrieved context
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query cannot be empty"
            )
        
        logger.info(f"Processing query: {request.query[:100]}...")
        
        # Perform RAG query
        result = rag_service.query(request.query)
        
        # Convert chunks to response format
        relevant_chunks = [
            ChunkInfo(
                content=chunk["content"],
                score=chunk["score"],
                metadata=chunk["metadata"]
            )
            for chunk in result["relevant_chunks"]
        ]
        
        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            relevant_chunks=relevant_chunks,
            query=result["query"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error processing query: {str(e)}"
        )


@router.post(
    "/chat/query-docs",
    response_model=QueryDocsResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def query_chatbot_docs_only(
    request: QueryRequest,
    rag_service: RAGService = RAGServiceDep
):
    """
    Mode 1: Ask a question to the RAG chatbot using ONLY documentation.
    
    The system:
    1. Searches for relevant chunks using semantic search in ChromaDB
    2. Generates a paraphrased response using the local LLM with the retrieved context
    3. If information is not in the documents, clearly indicates that it doesn't have that information
    
    Responses are paraphrased and do not copy literal text from documents.
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query cannot be empty"
            )
        
        logger.info(f"Processing docs-only mode query: {request.query[:100]}...")
        
        # Perform RAG query with documentation only
        result = rag_service.query_docs_only(request.query)
        
        # Convert chunks to response format
        relevant_chunks = [
            ChunkInfo(
                content=chunk["content"],
                score=chunk["score"],
                metadata=chunk["metadata"]
            )
            for chunk in result["relevant_chunks"]
        ]
        
        return QueryDocsResponse(
            answer=result["answer"],
            sources=result["sources"],
            relevant_chunks=relevant_chunks,
            query=result["query"],
            mode=result.get("mode", "docs-only")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing docs-only query: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error processing query: {str(e)}"
        )


@router.post(
    "/chat/query-hybrid",
    response_model=QueryHybridResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def query_chatbot_hybrid(
    request: QueryRequest,
    rag_service: RAGService = RAGServiceDep
):
    """
    Mode 2: Ask a question to the RAG chatbot using documentation + web search.
    
    The system:
    1. Searches for relevant chunks using semantic search in ChromaDB
    2. Automatically detects if updated information is needed (temporal keywords)
    3. If necessary, searches for complementary information on the internet using DuckDuckGo
    4. Generates a paraphrased response combining both contexts
    5. Clearly indicates which information comes from docs and which from the internet
    
    Responses are paraphrased and do not copy literal text from documents or web.
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query cannot be empty"
            )
        
        logger.info(f"Processing hybrid mode query: {request.query[:100]}...")
        
        # Perform hybrid RAG query (docs + web)
        result = rag_service.query_hybrid(request.query)
        
        # Convert chunks to response format
        relevant_chunks = [
            ChunkInfo(
                content=chunk["content"],
                score=chunk["score"],
                metadata=chunk["metadata"]
            )
            for chunk in result["relevant_chunks"]
        ]
        
        # Convert web results to response format
        web_results = [
            WebResultInfo(
                title=web_result["title"],
                snippet=web_result["snippet"],
                url=web_result["url"]
            )
            for web_result in result.get("web_results", [])
        ]
        
        return QueryHybridResponse(
            answer=result["answer"],
            sources_docs=result.get("sources_docs", []),
            sources_web=result.get("sources_web", []),
            relevant_chunks=relevant_chunks,
            web_results=web_results,
            query=result["query"],
            mode=result.get("mode", "hybrid")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing hybrid query: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error processing query: {str(e)}"
        )


@router.get(
    "/documents/list",
    response_model=DocumentListResponse,
    responses={
        500: {"model": ErrorResponse}
    }
)
async def list_documents(rag_service: RAGService = RAGServiceDep):
    """
    List all documents loaded in the system.
    """
    try:
        # Get document IDs
        document_ids = rag_service.get_document_ids()
        
        # Get information for each document
        documents = []
        for doc_id in document_ids:
            doc_info = rag_service.get_document_info(doc_id)
            if doc_info:
                # Find physical file to get size
                file_path = os.path.join(settings.DOCUMENTS_DIR, f"{doc_id}.*")
                import glob
                files = glob.glob(file_path)
                file_size = None
                if files:
                    file_size = os.path.getsize(files[0])
                
                # Parse date
                uploaded_at = datetime.fromisoformat(doc_info["uploaded_at"]) if doc_info.get("uploaded_at") else datetime.now()
                
                documents.append(DocumentInfo(
                    id=doc_info["id"],
                    filename=doc_info["filename"],
                    uploaded_at=uploaded_at,
                    chunks_count=doc_info.get("chunks_count", 0),
                    file_size=file_size
                ))
        
        return DocumentListResponse(
            documents=documents,
            total=len(documents)
        )
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error listing documents: {str(e)}"
        )


@router.delete(
    "/documents/{document_id}",
    response_model=DeleteDocumentResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def delete_document(
    document_id: str,
    rag_service: RAGService = RAGServiceDep
):
    """
    Delete a document and all its chunks from the system.
    """
    try:
        # Verify that the document exists
        doc_info = rag_service.get_document_info(document_id)
        if not doc_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found"
            )
        
        # Delete from vector store
        chunks_deleted = rag_service.delete_document(document_id)
        
        # Delete physical file
        import glob
        file_pattern = os.path.join(settings.DOCUMENTS_DIR, f"{document_id}.*")
        files = glob.glob(file_pattern)
        for file_path in files:
            try:
                os.remove(file_path)
                logger.info(f"File deleted: {file_path}")
            except Exception as e:
                logger.warning(f"Could not delete file {file_path}: {e}")
        
        logger.info(f"Document deleted: {document_id} ({chunks_deleted} chunks)")
        
        return DeleteDocumentResponse(
            status="success",
            document_id=document_id,
            message=f"Document deleted successfully. {chunks_deleted} chunks deleted."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error deleting document: {str(e)}"
        )

