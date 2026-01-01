from typing import Protocol, Dict, Any, Optional

class DocumentProcessorInterface(Protocol):
    """
    The formal contract for Document Processing services.
    
    Any class implementing this interface must provide methods to 
    extract data and generate AI summaries. This allows the 
    infrastructure layer to swap AI providers (e.g., Gemini vs Ollama)
    without breaking the domain logic.
    """

    def process(self, file_path: str, mime_type: Optional[str] = None) -> Dict[str, Any]:
        """
        The main entry point for document analysis.
        
        Args:
            file_path: The absolute path to the file on disk or /tmp.
            mime_type: The document type (PDF, Image, etc.) for AI context.
            
        Returns:
            A dictionary containing 'raw_text' and 'analysis'.
        """
        ...

    def _get_gemini_summary(self, file_path: str, mime_type: str) -> str:
        """Requirement for cloud-based summarization."""
        ...

    def _get_ollama_summary(self, file_path: str) -> str:
        """Requirement for local-based summarization."""
        ...