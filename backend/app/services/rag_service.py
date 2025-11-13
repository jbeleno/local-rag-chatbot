"""
Complete RAG service: embeddings, vector store, and response generation.
Supports two modes: documentation only and hybrid (documentation + web).
"""
import logging
import re
from typing import List, Dict, Optional, Tuple
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    tiktoken = None

from app.core.config import settings
from app.services.web_search import WebSearchService
from app.services.reranking_service import RerankingService
from app.services.query_expansion import QueryExpansionService
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class RAGService:
    """RAG service for retrieval and augmented generation."""
    
    def __init__(self):
        """Initialize the RAG service."""
        # Initialize embeddings
        logger.info(f"Initializing embedding model: {settings.EMBEDDING_MODEL}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={'device': 'cpu'}
        )
        
        # Initialize ChromaDB
        logger.info(f"Initializing ChromaDB at: {settings.CHROMA_PERSIST_DIR}")
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        # ChromaDB collection
        self.collection_name = settings.COLLECTION_NAME
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Collection '{self.collection_name}' found")
        except Exception:
            self.collection = self.client.create_collection(name=self.collection_name)
            logger.info(f"Collection '{self.collection_name}' created")
        
        # Initialize LangChain vector store using existing client
        self.vectorstore = Chroma(
            client=self.client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings
        )
        
        # Initialize Ollama LLM with Qwen2.5-7B parameters
        logger.info(f"Initializing Ollama LLM: {settings.LLM_MODEL}")
        self.llm = Ollama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            top_p=settings.LLM_TOP_P,
            num_ctx=settings.LLM_NUM_CTX
        )
        
        # Initialize web search service
        self.web_search = WebSearchService()
        
        # Initialize advanced services
        self.reranking_service = RerankingService() if settings.ENABLE_RERANKING else None
        self.query_expansion_service = QueryExpansionService() if settings.ENABLE_QUERY_EXPANSION else None
        self.cache_service = CacheService(ttl_seconds=settings.CACHE_TTL_SECONDS) if settings.ENABLE_CACHE else None
        
        # Initialize token encoder (tiktoken)
        self.token_encoder = None
        if TIKTOKEN_AVAILABLE:
            try:
                # Use cl100k_base which is compatible with many models
                self.token_encoder = tiktoken.get_encoding("cl100k_base")
                logger.info("tiktoken initialized for token counting")
            except Exception as e:
                logger.warning(f"Error initializing tiktoken: {e}")
        else:
            logger.warning("tiktoken not available, token counting disabled")
        
        # Prompt templates for documentation-only mode (Spanish)
        self.prompt_template_docs_es = PromptTemplate(
            input_variables=["context", "question"],
            template="""Eres un asistente experto. Tu tarea es responder preguntas basándote en el contexto proporcionado.

INSTRUCCIONES CRÍTICAS DE PARAFRASEADO:
- SIEMPRE debes parafrasear y reformular la información con tus propias palabras
- NO copies texto literal de los documentos
- Sintetiza la información y explica de forma clara y natural
- Usa lenguaje natural y conversacional
- Reorganiza la información de manera lógica y coherente

IMPORTANTE: Debes responder SOLO usando la información que aparece en el contexto proporcionado a continuación. 
NO uses ningún conocimiento previo, información general, o datos que no estén explícitamente en el contexto.
Si la información necesaria para responder NO está en el contexto, debes responder: "No tengo esa información en la documentación proporcionada."

Contexto de documentación:
{context}

Pregunta del usuario:
{question}

Instrucciones:
- Responde ÚNICAMENTE basándote en el contexto de arriba
- Parafrasea y explica con tus propias palabras (NO copies texto literal)
- Sintetiza la información de forma clara y natural
- Si la respuesta no está en el contexto, di claramente que no tienes esa información
- NO inventes, asumas o uses conocimiento que no esté en el contexto
- Responde en español

Respuesta:"""
        )
        
        # Prompt templates for documentation-only mode (English)
        self.prompt_template_docs_en = PromptTemplate(
            input_variables=["context", "question"],
            template="""You are an expert assistant. Your task is to answer questions based on the provided context.

CRITICAL PARAPHRASING INSTRUCTIONS:
- ALWAYS paraphrase and reformulate information in your own words
- DO NOT copy literal text from documents
- Synthesize information and explain clearly and naturally
- Use natural and conversational language
- Reorganize information logically and coherently

IMPORTANT: You must answer ONLY using the information that appears in the context provided below.
DO NOT use any prior knowledge, general information, or data not explicitly in the context.
If the information needed to answer is NOT in the context, you must respond: "I don't have that information in the provided documentation."

Documentation context:
{context}

User question:
{question}

Instructions:
- Answer ONLY based on the context above
- Paraphrase and explain in your own words (DO NOT copy literal text)
- Synthesize information clearly and naturally
- If the answer is not in the context, clearly state that you don't have that information
- DO NOT invent, assume, or use knowledge not in the context
- Respond in English

Answer:"""
        )
        
        # Prompt templates for hybrid mode (Spanish)
        self.prompt_template_hybrid_es = PromptTemplate(
            input_variables=["web_context", "question", "has_relevant_docs"],
            template="""Eres un asistente experto. Tu tarea es responder preguntas usando información de internet.

INSTRUCCIONES CRÍTICAS:
- SIEMPRE debes parafrasear y reformular la información con tus propias palabras
- NO copies texto literal de los documentos o de internet
- Sintetiza la información y explica de forma clara y natural
- Usa lenguaje natural y conversacional

{has_relevant_docs}

{web_context}

Pregunta del usuario:
{question}

REGLAS IMPORTANTES:
1. Si hay información web disponible (sección "Información de internet"), DEBES usarla para responder la pregunta. La información web tiene PRIORIDAD ABSOLUTA sobre la documentación.
2. Si la información web contiene datos relevantes para la pregunta, responde DIRECTAMENTE usando esa información.
3. Si la documentación NO es relevante para la pregunta, IGNÓRALA COMPLETAMENTE y NO la menciones.
4. Si la información web está disponible, NO digas que no tienes información. Usa la información web para responder.
5. Solo si NO hay información web Y la documentación es relevante, usa la documentación.
6. Si NO hay información web Y NO hay documentación relevante, entonces di que no tienes información.

FORMATO DE RESPUESTA:
- Si usas información web: "Según información actualizada de internet..." o "La información reciente indica que..."
- Si usas documentación: "Según la documentación..."
- Parafrasea TODO con tus propias palabras (NO copies texto literal)
- Responde en español de forma clara y directa

Respuesta:"""
        )
        
        # Prompt templates for hybrid mode (English)
        self.prompt_template_hybrid_en = PromptTemplate(
            input_variables=["web_context", "question", "has_relevant_docs"],
            template="""You are an expert assistant. Your task is to answer questions using information from the internet.

CRITICAL INSTRUCTIONS:
- ALWAYS paraphrase and reformulate information in your own words
- DO NOT copy literal text from documents or the internet
- Synthesize information and explain clearly and naturally
- Use natural and conversational language

{has_relevant_docs}

{web_context}

User question:
{question}

IMPORTANT RULES:
1. If web information is available (section "Internet information"), you MUST use it to answer the question. Web information has ABSOLUTE PRIORITY over documentation.
2. If web information contains relevant data for the question, answer DIRECTLY using that information.
3. If documentation is NOT relevant to the question, IGNORE IT COMPLETELY and DO NOT mention it.
4. If web information is available, DO NOT say you don't have information. Use the web information to answer.
5. Only if there is NO web information AND documentation is relevant, use the documentation.
6. If there is NO web information AND NO relevant documentation, then say you don't have information.

RESPONSE FORMAT:
- If using web information: "According to updated information from the internet..." or "Recent information indicates that..."
- If using documentation: "According to the documentation..."
- Paraphrase EVERYTHING in your own words (DO NOT copy literal text)
- Respond in English clearly and directly

Answer:"""
        )
        
        # Default to Spanish prompts (for backward compatibility)
        self.prompt_template_docs = self.prompt_template_docs_es
        self.prompt_template_hybrid = self.prompt_template_hybrid_es
        
        # Initialize QA chain for docs-only mode
        self.qa_chain_docs = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(
                search_kwargs={"k": settings.TOP_K_RESULTS}
            ),
            return_source_documents=True,
            chain_type_kwargs={"prompt": self.prompt_template_docs_es}
        )
        
        logger.info("RAG service initialized successfully")
    
    def detect_language(self, text: str) -> str:
        """
        Detect language of text using simple heuristics.
        
        Args:
            text: Text to analyze
            
        Returns:
            'es' or 'en'
        """
        text_lower = text.lower()
        
        # Spanish indicators
        spanish_indicators = [
            'ñ', 'á', 'é', 'í', 'ó', 'ú', 'ü',
            '¿', '¡', 'qué', 'cómo', 'dónde', 'cuándo', 'cuál', 'cuáles',
            'español', 'españa', 'mexico', 'colombia', 'argentina',
            'según', 'también', 'más', 'está', 'están', 'tiene', 'tienen'
        ]
        
        # English indicators
        english_indicators = [
            'the', 'is', 'are', 'what', 'how', 'where', 'when', 'which',
            'english', 'united states', 'usa', 'according', 'also', 'more',
            'has', 'have', 'been', 'this', 'that', 'these', 'those'
        ]
        
        spanish_count = sum(1 for indicator in spanish_indicators if indicator in text_lower)
        english_count = sum(1 for indicator in english_indicators if indicator in text_lower)
        
        # Default to Spanish if no clear indicator (can be changed)
        if english_count > spanish_count and english_count > 0:
            return 'en'
        return 'es'
    
    def get_prompt_template(self, language: str, mode: str):
        """
        Get prompt template based on language and mode.
        
        Args:
            language: Language code ('es' or 'en')
            mode: Mode ('docs' or 'hybrid')
            
        Returns:
            PromptTemplate instance
        """
        if language == 'en':
            if mode == 'docs':
                return self.prompt_template_docs_en
            else:
                return self.prompt_template_hybrid_en
        else:  # Spanish (default)
            if mode == 'docs':
                return self.prompt_template_docs_es
            else:
                return self.prompt_template_hybrid_es
    
    def add_documents(self, chunks: List[Dict]) -> int:
        """
        Add document chunks to vector store with embedding batching.
        
        Args:
            chunks: List of chunks with content and metadata
            
        Returns:
            Number of chunks added
        """
        try:
            texts = [chunk["content"] for chunk in chunks]
            metadatas = [chunk["metadata"] for chunk in chunks]
            
            # Generate unique IDs for each chunk
            ids = [
                f"{metadata['document_id']}_chunk_{metadata['chunk_index']}"
                for metadata in metadatas
            ]
            
            # Process in batches for better performance
            batch_size = settings.EMBEDDING_BATCH_SIZE
            total_added = 0
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_metadatas = metadatas[i:i + batch_size]
                batch_ids = ids[i:i + batch_size]
                
                # Add batch to ChromaDB using LangChain
                self.vectorstore.add_texts(
                    texts=batch_texts,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
                total_added += len(batch_texts)
                logger.debug(f"Added batch {i//batch_size + 1}: {len(batch_texts)} chunks")
            
            logger.info(f"Added {total_added} chunks to vector store (in {len(texts)//batch_size + 1} batches)")
            return total_added
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise ValueError(f"Error adding documents to vector store: {str(e)}")
    
    def delete_document(self, document_id: str) -> int:
        """
        Delete all chunks of a document from the vector store.
        
        Args:
            document_id: ID of document to delete
            
        Returns:
            Number of chunks deleted
        """
        try:
            # Find all chunks of the document
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            if results and results['ids']:
                # Delete chunks
                self.collection.delete(ids=results['ids'])
                chunks_deleted = len(results['ids'])
                logger.info(f"Deleted {chunks_deleted} chunks from document {document_id}")
                return chunks_deleted
            else:
                logger.warning(f"No chunks found for document {document_id}")
                return 0
                
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise ValueError(f"Error deleting document from vector store: {str(e)}")
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.
        
        Args:
            text: Text to count
            
        Returns:
            Estimated number of tokens
        """
        if self.token_encoder is not None:
            try:
                return len(self.token_encoder.encode(text))
            except Exception as e:
                logger.warning(f"Error counting tokens with tiktoken: {e}")
                # Fallback to approximate estimation
                return int(len(text.split()) * 1.3)
        else:
            # Approximate estimation if tiktoken is not available
            # Average: ~1.3 tokens per word
            return int(len(text.split()) * 1.3)
    
    def query(self, question: str, history_context: str = "") -> Dict:
        """
        Perform a RAG query: retrieve context and generate response.
        Legacy method - use query_docs_only or query_hybrid instead.
        
        Args:
            question: User question
            history_context: Recent conversation history for context
            
        Returns:
            Dictionary with response, sources, and relevant chunks
        """
        # Default to docs-only mode
        return self.query_docs_only(question, history_context=history_context)
    
    def query_docs_only(self, question: str, history_context: str = "") -> Dict:
        """
        Mode 1: RAG query with local documentation only.
        
        Responds only based on documents uploaded by the user.
        If information is not in the documents, clearly indicates that it doesn't have that information.
        
        Args:
            question: User question
            history_context: Recent conversation history for context
            
        Returns:
            Dictionary with response, sources, and relevant chunks
        """
        try:
            # Detect language from question
            language = self.detect_language(question)
            logger.debug(f"Detected language: {language} for question: {question[:50]}...")
            
            # Check if there are documents in the collection
            collection_count = self.collection.count()
            if collection_count == 0:
                logger.warning("No documents in database")
                no_docs_msg_es = "No hay documentos cargados en el sistema. Por favor, sube documentos primero para poder responder preguntas basándome en ellos."
                no_docs_msg_en = "No documents loaded in the system. Please upload documents first to answer questions based on them."
                return {
                    "answer": no_docs_msg_en if language == 'en' else no_docs_msg_es,
                    "sources": [],
                    "relevant_chunks": [],
                    "query": question,
                    "mode": "docs-only"
                }
            
            # Expand query if enabled
            expanded_question = question
            if self.query_expansion_service and settings.ENABLE_QUERY_EXPANSION:
                expanded_question = self.query_expansion_service.expand_query(question)
                logger.debug(f"Expanded query: '{question}' -> '{expanded_question}'")
            
            # Adjust k if necessary (use more results for reranking)
            k = min(settings.TOP_K_RESULTS * 2, collection_count) if self.reranking_service else min(settings.TOP_K_RESULTS, collection_count)
            
            # Perform semantic search to get relevant chunks
            relevant_docs = self.vectorstore.similarity_search_with_score(
                expanded_question,
                k=k
            )
            
            # Extract information from relevant chunks
            relevant_chunks = []
            sources = set()
            
            for doc, score in relevant_docs:
                metadata = doc.metadata
                relevant_chunks.append({
                    "content": doc.page_content,
                    "score": float(score),
                    "metadata": metadata
                })
                if "document_id" in metadata:
                    sources.add(metadata["document_id"])
            
            # Apply reranking if enabled
            if self.reranking_service and settings.ENABLE_RERANKING and relevant_chunks:
                logger.debug(f"Applying reranking to {len(relevant_chunks)} chunks")
                relevant_chunks = self.reranking_service.rerank(
                    question,  # Use original query for reranking
                    relevant_chunks,
                    top_k=settings.RERANKING_TOP_K
                )
                logger.debug(f"Reranking completed, {len(relevant_chunks)} chunks returned")
            
            # Build context from relevant chunks
            doc_context = "\n\n".join([chunk["content"] for chunk in relevant_chunks])
            
            # Build question with history if available
            if language == 'en':
                question_label = "Current user question:"
                history_label = "Previous conversation history:"
            else:
                question_label = "Pregunta actual del usuario:"
                history_label = "Historial de conversación anterior:"
            
            question_for_prompt = question
            if history_context:
                question_for_prompt = (
                    f"{history_label}\n{history_context.strip()}\n\n"
                    f"{question_label}\n{question.strip()}"
                )
            
            logger.debug(
                "Generating response (docs-only) with history: %s",
                "yes" if history_context else "no"
            )
            
            # Get appropriate prompt template based on language
            prompt_template = self.get_prompt_template(language, 'docs')
            prompt = prompt_template.format(
                context=doc_context,
                question=question_for_prompt
            )
            
            # Count tokens for logging/monitoring
            question_tokens = self.count_tokens(question)
            history_tokens = self.count_tokens(history_context) if history_context else 0
            prompt_tokens = self.count_tokens(prompt)
            total_input_tokens = question_tokens + history_tokens
            logger.info(f"Tokens in query: question={question_tokens}, history={history_tokens}, prompt={prompt_tokens}, total={total_input_tokens}")
            
            # Generate response using LLM
            answer = self.llm.invoke(prompt)
            
            # Count tokens in response
            answer_tokens = self.count_tokens(answer)
            logger.info(f"Tokens in response: {answer_tokens}")
            
            return {
                "answer": answer,
                "sources": list(sources),
                "relevant_chunks": relevant_chunks,
                "query": question,
                "mode": "docs-only",
                "token_count": {
                    "input": total_input_tokens,
                    "output": answer_tokens,
                    "total": total_input_tokens + answer_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing docs-only query: {e}")
            raise ValueError(f"Error processing query: {str(e)}")
    
    def query_hybrid(self, question: str, history_context: str = "") -> Dict:
        """
        Mode 2: Hybrid RAG query (documentation + web search).
        
        Combines information from local documents AND real-time web search.
        Prioritizes documentation information but complements with updated data from the internet.
        
        Args:
            question: User question
            history_context: Recent conversation history for context
            
        Returns:
            Dictionary with response, doc sources, web sources, and relevant chunks
        """
        try:
            # Detect language from question
            language = self.detect_language(question)
            logger.debug(f"Detected language: {language} for question: {question[:50]}...")
            
            # 1. Search in local documents (if there are documents)
            collection_count = self.collection.count()
            relevant_docs = []
            
            if collection_count > 0:
                # Adjust k if necessary
                k = min(settings.TOP_K_RESULTS, collection_count)
                relevant_docs = self.vectorstore.similarity_search_with_score(
                    question,
                    k=k
                )
            else:
                logger.info("No documents in database, only web search will be used")
            
            # Extract information from relevant chunks and filter by relevance threshold
            relevant_chunks = []
            sources_docs = set()
            
            for doc, score in relevant_docs:
                # Filter chunks by relevance threshold (lower scores = more relevant)
                if float(score) <= settings.RELEVANCE_THRESHOLD:
                    metadata = doc.metadata
                    relevant_chunks.append({
                        "content": doc.page_content,
                        "score": float(score),
                        "metadata": metadata
                    })
                    if "document_id" in metadata:
                        sources_docs.add(metadata["document_id"])
                else:
                    logger.debug(f"Chunk filtered by low relevance (score: {score:.3f} > threshold: {settings.RELEVANCE_THRESHOLD})")
            
            # Format document context (only if there are relevant chunks)
            if language == 'en':
                doc_context_label = "Documentation context:"
                no_docs_msg = "[No relevant documentation for this question. Ignore any reference to documentation and respond only with web information if available.]"
            else:
                doc_context_label = "Contexto de documentación:"
                no_docs_msg = "[No hay documentación relevante para esta pregunta. Ignora cualquier referencia a documentación y responde solo con la información web si está disponible.]"
            
            if relevant_chunks:
                doc_context = "\n\n".join([chunk["content"] for chunk in relevant_chunks])
                has_relevant_docs = f"{doc_context_label}\n{doc_context}"
            else:
                doc_context = ""
                has_relevant_docs = f"{doc_context_label}\n{no_docs_msg}"
            
            # 2. Search web if necessary
            web_results = []
            sources_web = []
            web_context = ""
            web_search_attempted = False
            
            if self.web_search.should_search_web(question):
                logger.info("Performing complementary web search")
                web_search_attempted = True
                web_results = self.web_search.search_web(question, num_results=settings.WEB_SEARCH_MAX_RESULTS)
                
                if web_results:
                    logger.info(f"Web search successful: {len(web_results)} results found")
                    web_context = self.web_search.format_web_results_for_context(web_results)
                    sources_web = [result["url"] for result in web_results]
                    # Log web context for debug
                    logger.info(f"Formatted web context:\n{web_context}")
                else:
                    logger.warning("Web search returned no results")
            
            # 3. Generate response combining both contexts
            # Build question with history labels based on language
            if language == 'en':
                question_label = "Current user question:"
                history_label = "Previous conversation history:"
            else:
                question_label = "Pregunta actual del usuario:"
                history_label = "Historial de conversación anterior:"
            
            question_for_prompt = question
            if history_context:
                question_for_prompt = (
                    f"{history_label}\n{history_context.strip()}\n\n"
                    f"{question_label}\n{question.strip()}"
                )
            
            if web_context:
                # Use hybrid prompt with both contexts
                prompt_template = self.get_prompt_template(language, 'hybrid')
                prompt = prompt_template.format(
                    web_context=web_context,
                    question=question_for_prompt,
                    has_relevant_docs=has_relevant_docs
                )
                logger.info(f"Full prompt sent to LLM:\n{prompt[:1000]}...")
            elif web_search_attempted and not web_results:
                # Web search was attempted but no results
                if language == 'en':
                    no_web_results_msg = """Web search was attempted but no relevant results were found.

Instructions:
- If you have information in the documentation, use it to answer
- If there is no information in the documentation, clearly indicate that you could not find information in either the documents or the internet
- Respond politely and helpfully

Answer:"""
                else:
                    no_web_results_msg = """Se intentó buscar información en internet pero no se encontraron resultados relevantes.

Instrucciones:
- Si tienes información en la documentación, úsala para responder
- Si no hay información en la documentación, indica claramente que no pudiste encontrar información ni en los documentos ni en internet
- Responde de forma educada y útil

Respuesta:"""
                
                if language == 'en':
                    prompt = f"""You are an expert assistant. The user asks: {question_for_prompt}

{has_relevant_docs}

{no_web_results_msg}"""
                else:
                    prompt = f"""Eres un asistente experto. El usuario pregunta: {question_for_prompt}

{has_relevant_docs}

{no_web_results_msg}"""
            else:
                # If no web, use docs-only prompt
                if relevant_chunks:
                    prompt_template = self.get_prompt_template(language, 'docs')
                    prompt = prompt_template.format(
                        context=doc_context,
                        question=question_for_prompt
                    )
                else:
                    # If no relevant chunks and no web, indicate no information
                    if language == 'en':
                        no_info_msg = """I don't have relevant information in the documentation or on the internet to answer this question.
Respond politely indicating that you cannot answer because you don't have the necessary information.

Answer:"""
                    else:
                        no_info_msg = """No tengo información relevante en la documentación ni en internet para responder esta pregunta.
Responde de forma educada indicando que no puedes responder porque no tienes la información necesaria.

Respuesta:"""
                    
                    if language == 'en':
                        prompt = f"""You are an expert assistant. The user asks: {question_for_prompt}

{no_info_msg}"""
                    else:
                        prompt = f"""Eres un asistente experto. El usuario pregunta: {question_for_prompt}

{no_info_msg}"""
            
            # Count tokens for logging/monitoring
            question_tokens = self.count_tokens(question)
            history_tokens = self.count_tokens(history_context) if history_context else 0
            prompt_tokens = self.count_tokens(prompt)
            total_input_tokens = question_tokens + history_tokens
            logger.info(f"Tokens in hybrid query: question={question_tokens}, history={history_tokens}, prompt={prompt_tokens}, total_input={total_input_tokens}")
            
            # Generate response with LLM
            answer = self.llm.invoke(prompt)
            
            # Count tokens in response
            answer_tokens = self.count_tokens(answer)
            logger.info(f"Tokens in response: {answer_tokens}")
            
            return {
                "answer": answer,
                "sources_docs": list(sources_docs),
                "sources_web": sources_web,
                "relevant_chunks": relevant_chunks,
                "web_results": web_results,
                "query": question,
                "mode": "hybrid",
                "token_count": {
                    "input": total_input_tokens,
                    "output": answer_tokens,
                    "total": total_input_tokens + answer_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing hybrid query: {e}", exc_info=True)
            raise ValueError(f"Error processing hybrid query: {str(e)}")
    
    def get_document_ids(self) -> List[str]:
        """
        Get list of unique document IDs in the vector store.
        
        Returns:
            List of document IDs
        """
        try:
            # Get all documents
            results = self.collection.get()
            
            if not results or not results['metadatas']:
                return []
            
            # Extract unique document IDs
            document_ids = set()
            for metadata in results['metadatas']:
                if 'document_id' in metadata:
                    document_ids.add(metadata['document_id'])
            
            return list(document_ids)
            
        except Exception as e:
            logger.error(f"Error getting document IDs: {e}")
            return []
    
    def get_document_info(self, document_id: str) -> Optional[Dict]:
        """
        Get information about a specific document.
        
        Args:
            document_id: Document ID
            
        Returns:
            Dictionary with document information or None
        """
        try:
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            if not results or not results['metadatas']:
                return None
            
            # Use first chunk to get document metadata
            metadata = results['metadatas'][0]
            
            return {
                "id": document_id,
                "filename": metadata.get("filename", "unknown"),
                "chunks_count": len(results['ids']),
                "uploaded_at": metadata.get("uploaded_at", ""),
                "file_extension": metadata.get("file_extension", ""),
                "text_length": metadata.get("text_length", 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting document information: {e}")
            return None

