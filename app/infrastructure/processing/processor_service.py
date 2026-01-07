import os
import logging
import pandas as pd
from ollama import Client
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_message
from pypdf import PdfReader
from google import genai
from docx import Document as DocxReader
from app.infrastructure.config import settings
from app.domain.exceptions import ProcessingError
from app.domain.services.document_processor import DocumentProcessorInterface

logger = logging.getLogger(__name__)

class DocumentProcessor(DocumentProcessorInterface):
    def __init__(self):
        self.provider = settings.ai_provider.lower()
        self.api_key = settings.gemini_api.strip('"')
        
        # Gemini client (async)
        self.gemini_client = genai.Client(api_key=self.api_key)
        self.ollama_model = settings.ollama_model
        
        # FIXED: Use synchronous Client for Celery compatibility
        self.ollama_client = Client(host=settings.ollama_base_url)

    def _extract_text_metadata(self, file_path: str) -> str:
        """Fallback text extraction for metadata and word counts."""
        ext = os.path.splitext(file_path)[1].lower()
        text = ""
        try:
            if ext == ".pdf":
                reader = PdfReader(file_path)
                text = "\n".join([p.extract_text() or "" for p in reader.pages])
            elif ext in [".docx", ".doc"]:
                doc = DocxReader(file_path)
                text = "\n".join([p.text for p in doc.paragraphs])
            elif ext in [".xlsx", ".xls", ".csv"]:
                df = pd.read_excel(file_path) if ext != ".csv" else pd.read_csv(file_path)
                text = df.to_string()
            elif ext == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
        except Exception as e:
            logger.error(f"Text extraction failed for {file_path}: {e}")
        return text

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=10, max=60),
        retry=retry_if_exception_message(match=".*Rate Limit.*|.*429.*")
    )
    async def _get_gemini_summary(self, file_path: str, mime_type: str) -> str:
        """Sends the file to Gemini 2.0 Flash."""
        try:
            uploaded_file = self.gemini_client.files.upload(
                file=file_path, 
                config={'mime_type': mime_type}
            )

            await asyncio.sleep(2)
            
            response = self.gemini_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=[
                    "Analyze this document and provide a professional 4-bullet point summary.",
                    uploaded_file
                ]
            )
            return response.text.strip()
            
        except Exception as e:
            if "429" in str(e):
                logger.warning("Gemini Rate Limit (429) hit. Tenacity is retrying...")
                raise Exception("Gemini Rate Limit reached.")
            raise Exception(f"Gemini Cloud Error: {str(e)}")

    def _get_ollama_summary_sync(self, file_path: str) -> str:
        """
        Synchronous Ollama processing for Celery.
        Extracts text first, then sends to Ollama.
        """
        try:
            # Step 1: Extract text from document
            extracted_text = self._extract_text_metadata(file_path)
            
            if not extracted_text or len(extracted_text.strip()) < 50:
                raise ProcessingError("Document text extraction failed or document is too short")
            
            # Step 2: Truncate if too long (Ollama context limits)
            max_chars = 8000  # Adjust based on your model's context window
            if len(extracted_text) > max_chars:
                logger.warning(f"Document text truncated from {len(extracted_text)} to {max_chars} chars")
                extracted_text = extracted_text[:max_chars] + "...(truncated)"
            
            # Step 3: Send to Ollama for summarization
            logger.info(f"Sending {len(extracted_text)} chars to Ollama model: {self.ollama_model}")
            
            response = self.ollama_client.chat(
                model=self.ollama_model,
                messages=[{
                    'role': 'user',
                    'content': f"""Analyze this document and provide a professional 4-bullet point summary.

Document content:
{extracted_text}

Provide ONLY the 4 bullet points, nothing else."""
                }]
            )
            
            summary = response['message']['content']
            logger.info(f"Ollama summary generated: {len(summary)} chars")
            return summary
            
        except Exception as e:
            logger.error(f"Ollama Error at {settings.ollama_base_url}: {e}")
            raise ProcessingError(f"AI Engine failed: {str(e)}")

    async def process(self, file_path: str, mime_type: str = None) -> dict:
        """Main entry point for document analysis - ASYNC version for FastAPI."""
        logger.info(f"Processing document with {self.provider}: {file_path}")

        if self.provider == "ollama":
            # Run sync Ollama in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            summary = await loop.run_in_executor(None, self._get_ollama_summary_sync, file_path)
        else:
            summary = await self._get_gemini_summary(file_path, mime_type)

        raw_text = self._extract_text_metadata(file_path)

        analysis = {
            "summary": summary,
            "word_count": len(raw_text.split()),
            "contains_email": "@" in raw_text,
            "contains_money": any(s in raw_text for s in ["$", "USD", "NGN", "€"]),
            "ai_provider": self.provider
        }

        return {
            "raw_text": raw_text,
            "analysis": analysis
        }
    
    def process_sync(self, file_path: str, mime_type: str = None) -> dict:
        """SYNCHRONOUS version for Celery worker."""
        logger.info(f"Processing document with {self.provider}: {file_path}")

        if self.provider == "ollama":
            summary = self._get_ollama_summary_sync(file_path)
        else:
            # For Gemini in Celery, we need to run async code in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                summary = loop.run_until_complete(self._get_gemini_summary(file_path, mime_type))
            finally:
                loop.close()

        raw_text = self._extract_text_metadata(file_path)

        analysis = {
            "summary": summary,
            "word_count": len(raw_text.split()),
            "contains_email": "@" in raw_text,
            "contains_money": any(s in raw_text for s in ["$", "USD", "NGN", "€"]),
            "ai_provider": self.provider
        }

        return {
            "raw_text": raw_text,
            "analysis": analysis
        }