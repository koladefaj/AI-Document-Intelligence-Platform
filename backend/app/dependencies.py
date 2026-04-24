import os
import logging
from app.infrastructure.processing.processor_service import DocumentProcessor
from app.domain.services.storage_interface import StorageInterface
from app.domain.services.rag_service import RAGService

# Initialize logger
logger = logging.getLogger(__name__)

# Global variables to cache the instances
_storage_instance = None
_processor_instance = None
_rag_instance = None

def setup_llamaindex():
    """Initializes global LlamaIndex settings for LLM and Embeddings."""
    from llama_index.core import Settings
    from llama_index.llms.ollama import Ollama
    from llama_index.embeddings.ollama import OllamaEmbedding
    from llama_index.llms.gemini import Gemini
    from llama_index.embeddings.gemini import GeminiEmbedding
    from app.infrastructure.config import settings

    provider = settings.ai_provider.lower()
    
    if provider == "gemini":
        api_key = settings.gemini_api.strip('"') if settings.gemini_api else ""
        Settings.llm = Gemini(
            model_name=settings.gemini_model,
            api_key=api_key
        )
        Settings.embed_model = GeminiEmbedding(
            model_name=settings.gemini_embedding_model,
            api_key=api_key
        )
    else:
        # Ollama setup
        Settings.llm = Ollama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            request_timeout=120.0
        )
        Settings.embed_model = OllamaEmbedding(
            model_name=settings.ollama_embedding_model,
            base_url=settings.ollama_base_url
        )
    
    logger.info(f"DI: LlamaIndex configured with provider: {provider}")

def get_storage_service() -> StorageInterface:
    """
    Dependency Provider for Storage with Lazy Loading (Singleton).
    """
    global _storage_instance
    
    if _storage_instance is not None:
        return _storage_instance

    storage_type = os.getenv("STORAGE_TYPE", "r2").lower()

    if storage_type == "minio":
        from app.infrastructure.storage.minio_service import MinioStorage
        logger.info("DI: Initializing MinioStorage")
        _storage_instance = MinioStorage()
    elif storage_type == "local":
        from app.infrastructure.storage.local_storage import LocalStorage
        logger.info("DI: Initializing LocalStorage")
        _storage_instance = LocalStorage()
    else:
        # Default to R2
        from app.infrastructure.storage.r2_storage import R2Storage
        logger.info("DI: Initializing R2Storage")
        _storage_instance = R2Storage()
    
    return _storage_instance

def get_document_processor() -> DocumentProcessor:
    """
    Dependency Provider for DocumentProcessor (Singleton).
    Handles client initialization and injection.
    """
    global _processor_instance
    
    if _processor_instance is None:
        from app.infrastructure.config import settings
        from ollama import Client
        
        logger.info(f"DI: Initializing DocumentProcessor with provider: {settings.ai_provider}")
        
        # Initialize clients based on provider
        ollama_client = Client(host=settings.ollama_base_url)
        gemini_client = None
        
        if settings.ai_provider.lower() == "gemini":
            from google import genai
            api_key = settings.gemini_api.strip('"') if settings.gemini_api else ""
            if api_key:
                gemini_client = genai.Client(api_key=api_key)
            else:
                logger.warning("DI: Gemini API key missing, Gemini client not initialized.")

        # Ensure LlamaIndex is configured
        setup_llamaindex()

        # Inject clients into processor
        _processor_instance = DocumentProcessor(
            provider=settings.ai_provider,
            ollama_client=ollama_client,
            gemini_client=gemini_client
        )
        
    return _processor_instance

def get_rag_service() -> RAGService:
    """
    Dependency Provider for RAGService (Singleton).
    """
    global _rag_instance
    
    if _rag_instance is None:
        from app.infrastructure.config import settings
        from ollama import Client
        
        # We can reuse the same client logic as above
        ollama_client = Client(host=settings.ollama_base_url)
        gemini_client = None
        
        if settings.ai_provider.lower() == "gemini":
            from google import genai
            api_key = settings.gemini_api.strip('"') if settings.gemini_api else ""
            if api_key:
                gemini_client = genai.Client(api_key=api_key)

        # Ensure LlamaIndex is configured
        setup_llamaindex()

        _rag_instance = RAGService(
            ollama_client=ollama_client,
            gemini_client=gemini_client
        )
        
    return _rag_instance