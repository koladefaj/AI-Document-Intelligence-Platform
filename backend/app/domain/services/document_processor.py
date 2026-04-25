from typing import Protocol, Dict, Any, Optional

class DocumentProcessorInterface(Protocol):
    """
    The formal contract for Document Processing services.
    
    Any class implementing this interface must provide methods to 
    extract data and generate AI summaries. This allows the 
    infrastructure layer to swap AI providers (e.g., Gemini vs Ollama)
    without breaking the domain logic.
    """

    async def process(self, file_path: str, mime_type: Optional[str] = None) -> Dict[str, Any]:
        """Async entry point for document analysis."""
        ...

    def process_sync(self, file_path: str, mime_type: Optional[str] = None, on_chunk: Optional[Any] = None) -> Dict[str, Any]:
        """
        Synchronous entry point for document analysis (optimized for Celery).
        Supports an optional on_chunk callback for streaming results.
        """
        ...

    def _get_gemini_summary(self, file_path: str, mime_type: str) -> str:
        """Requirement for cloud-based summarization."""
        pass

    def _get_ollama_summary(self, file_path: str) -> str:
        """Requirement for local-based summarization."""
        pass