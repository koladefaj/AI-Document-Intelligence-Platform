import uuid
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from pgvector.sqlalchemy import VECTOR
from app.infrastructure.db.models import DocumentEmbedding
from app.infrastructure.config import settings
from llama_index.core import Settings

logger = logging.getLogger(__name__)

class RAGService:
    """
    Service dedicated to Retrieval-Augmented Generation (RAG).
    Handles vector indexing and semantic querying.
    """

    def __init__(self, ollama_client=None, gemini_client=None):
        self.provider = settings.ai_provider.lower()
        self.ollama_client = ollama_client
        self.gemini_client = gemini_client
        self.ollama_model = settings.ollama_model
        self.gemini_model = settings.gemini_model

    def index_nodes(self, session: Session, document_id: str, nodes: list) -> int:
        """
        Generates embeddings for nodes and saves them to the vector store.
        Returns the number of indexed chunks.
        """
        try:
            # 1. Clean existing embeddings for this document (safety first)
            session.query(DocumentEmbedding).filter(
                DocumentEmbedding.document_id == (uuid.UUID(document_id) if isinstance(document_id, str) else document_id)
            ).delete()

            # 2. Batch Embedding Generation
            texts_to_embed = [node.get_content() for node in nodes]
            logger.info(f"RAG: Generating embeddings for {len(texts_to_embed)} chunks in batch.")
            
            embeddings = Settings.embed_model.get_text_embedding_batch(texts_to_embed)

            # 3. Save to DB
            for node, embedding in zip(nodes, embeddings):
                db_embedding = DocumentEmbedding(
                    document_id=uuid.UUID(document_id) if isinstance(document_id, str) else document_id,
                    text=node.get_content(),
                    embedding=embedding,
                    meta=node.metadata
                )
                session.add(db_embedding)
            
            session.commit()
            logger.info(f"RAG: Successfully indexed {len(nodes)} chunks for document {document_id}")
            return len(nodes)

        except Exception as e:
            session.rollback()
            logger.error(f"RAG Indexing Error: {e}")
            raise

    def query(self, session: Session, document_id: str, query_text: str, chat_history: list = None, limit: int = 5) -> dict:
        """
        Performs semantic search and generates an answer using the LLM with context.
        """
        results, prompt = self._prepare_rag_context(session, document_id, query_text, chat_history, limit)
        
        if not results:
            return {
                "answer": "I couldn't find any relevant information in the document to answer your question.",
                "sources": []
            }

        # 5. LLM Interaction
        if self.provider == "ollama":
            if not self.ollama_client:
                raise ValueError("Ollama client not initialized in RAGService")
            response = self.ollama_client.chat(
                model=self.ollama_model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1}
            )
            answer = response["message"]["content"]
        else:
            if not self.gemini_client:
                raise ValueError("Gemini client not initialized in RAGService")
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=[prompt]
            )
            answer = response.text

        # 6. Format Sources
        sources = [{"text": r.text, "metadata": r.meta} for r in results]

        return {
            "answer": answer,
            "sources": sources
        }

    def _prepare_rag_context(self, session: Session, document_id: str, query_text: str, chat_history: list = None, limit: int = 5):
        """Shared logic for context retrieval and prompt building with History support."""
        # 1. Generate Query Embedding
        query_embedding = Settings.embed_model.get_text_embedding(query_text)

        # 2. Vector Search
        stmt = (
            select(DocumentEmbedding)
            .filter(DocumentEmbedding.document_id == (uuid.UUID(document_id) if isinstance(document_id, str) else document_id))
            .order_by(DocumentEmbedding.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        
        results = session.execute(stmt).scalars().all()
        
        if not results:
            return None, None

        # 3. Build Context
        context_text = "\n\n---\n\n".join([r.text for r in results])
        
        # 4. Format History
        history_text = ""
        if chat_history:
            history_text = "RECENT CONVERSATION:\n" + "\n".join([f"{m['role'].upper()}: {m['content']}" for m in chat_history])
        
        # 5. Advanced Persona-Driven Prompt Engineering
        prompt = f"""You are Engram, a professional and intelligent document analyst. Your goal is to assist the user by providing precise insights based on the provided DOCUMENT CONTEXT.

CORE GUIDELINES:
1. CONVERSATIONAL AWARENESS: If the user is giving feedback (e.g., "okay cool", "thanks", "wow"), acknowledging your previous answer, or engaging in small talk, respond naturally and professionally as a person would. Do not try to force a document search for these interactions.
2. CONTEXTUAL ACCURACY: For specific questions about the document, only use the provided DOCUMENT CONTEXT. If the information isn't there, admit it clearly.
3. BREVITY: Keep your responses concise and impactful.
4. PERSONALITY: Be helpful, polite, and maintain the persona of an advanced intelligence partner.

{history_text}

DOCUMENT CONTEXT:
{context_text}

USER MESSAGE:
{query_text}

ENAGRAM RESPONSE:"""
        return results, prompt

    def stream_query(self, session: Session, document_id: str, query_text: str, chat_history: list = None, limit: int = 5):
        """
        Streams the RAG response token by token with history.
        """
        results, prompt = self._prepare_rag_context(session, document_id, query_text, chat_history, limit)

        if not results:
            yield "I couldn't find any relevant information in the document to answer your question."
            return

        if self.provider == "ollama":
            stream = self.ollama_client.chat(
                model=self.ollama_model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                options={"temperature": 0.1}
            )
            for chunk in stream:
                yield chunk['message']['content']
        else:
            # Gemini Streaming
            stream = self.gemini_client.models.generate_content_stream(
                model=self.gemini_model,
                contents=[prompt]
            )
            for chunk in stream:
                yield chunk.text
