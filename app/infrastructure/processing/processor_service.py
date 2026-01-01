import os
import logging
import pandas as pd
import ollama
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_message
from PyPDF2 import PdfReader
from google import genai
from docx import Document as DocxReader
from app.infrastructure.config import settings
from app.domain.services.document_processor import DocumentProcessorInterface

logger = logging.getLogger(__name__)

class DocumentProcessor(DocumentProcessorInterface):
    def __init__(self):
        self.provider = settings.ai_provider.lower()
        # Clean the API key (removes potential quotes from .env parsing)
        self.api_key = settings.gemini_api.strip('"')
        
        # New 2025/2026 GenAI Client
        self.gemini_client = genai.Client(api_key=self.api_key)
        self.ollama_model = "qwen2.5-vl:3b"

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
                # engine='openpyxl' is preferred for modern Excel files
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
        """
        Sends the file to Gemini 2.0 Flash.
        Uses tenacity to auto-retry on 429 'Rate Limit' errors.
        """
        try:
            # Step 1: Upload the file to the Gemini File API
            uploaded_file = self.gemini_client.files.upload(
                file=file_path, 
                config={'mime_type': mime_type}
            )

            await asyncio.sleep(2)
            
            # Step 2: Generate content with the 2.0 Flash model
            # 2.0 Flash is faster and more cost-effective for summaries
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

    async def _get_ollama_summary(self, file_path: str) -> str:
        """Local fallback using Ollama for privacy-sensitive or offline tasks."""
        try:
            # Using loop.run_in_executor because ollama-python is currently sync
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: ollama.chat(
                    model=self.ollama_model,
                    messages=[{
                        'role': 'user',
                        'content': 'Summarize this document in 4 professional bullet points.',
                        'images': [file_path] 
                    }]
                )
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"Local VLM Error: {e}")
            return f"Local VLM Error: {str(e)}"

    async def process(self, file_path: str, mime_type: str = None) -> dict:
        """Main entry point for document analysis."""
        logger.info(f"Processing document with {self.provider}: {file_path}")

        if self.provider == "ollama":
            summary = await self._get_ollama_summary(file_path)
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