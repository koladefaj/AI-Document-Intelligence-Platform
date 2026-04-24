import os
import logging
import asyncio
import pandas as pd
import pytesseract
from ollama import Client
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_message
from pypdf import PdfReader
from google import genai
from docx import Document as DocxReader
from pdf2image import convert_from_path


from app.infrastructure.config import settings
from app.domain.exceptions import ProcessingError
from app.domain.services.document_processor import DocumentProcessorInterface

logger = logging.getLogger(__name__)


class DocumentProcessor(DocumentProcessorInterface):
    def __init__(self, provider: str, ollama_client: Client = None, gemini_client: genai.Client = None):
        """
        Dependency Injected Constructor.
        Clients are passed in rather than created internally for better coupling.
        """
        self.provider = provider.lower()
        self.ollama_client = ollama_client
        self.gemini_client = gemini_client
        
        self.ollama_model = settings.ollama_model
        self.gemini_model = settings.gemini_model
        self.api_key = settings.gemini_api.strip('"') if settings.gemini_api else ""

    # TEXT SANITIZATION (GLOBAL – CRITICAL)
    
    def _sanitize_text(self, text: str) -> str:
        if not text:
            return ""

        # Remove NULL bytes (DB / JSON killers)
        text = text.replace("\x00", "")

        # Remove other control characters except whitespace
        text = "".join(
            c for c in text
            if c.isprintable() or c in "\n\r\t"
        )

        return text.strip()

    # TEXT EXTRACTION (EXTENSION + MIME SAFE)
    
    def _extract_text_metadata(self, file_path: str, mime_type: str | None = None) -> str:
        text = ""

        try:
            ext = os.path.splitext(file_path)[1].lower()

            is_pdf = ext == ".pdf" or mime_type == "application/pdf"
            is_docx = (
                ext in [".docx", ".doc"]
                or mime_type in [
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/msword",
                ]
            )
            is_excel = (
                ext in [".xls", ".xlsx"]
                or mime_type in [
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "application/vnd.ms-excel",
                ]
            )
            is_csv = ext == ".csv" or mime_type == "text/csv"
            is_txt = ext == ".txt" or mime_type == "text/plain"

            # ---------------- PDF ----------------
            if is_pdf:
                reader = PdfReader(file_path)

                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    page_text = self._sanitize_text(page_text)
                    text += page_text
                    logger.debug(f"PDF page {i + 1}: {len(page_text)} chars")

                logger.info(f"PDF extraction complete: {len(text)} characters")

                # OCR fallback
                if not text.strip():
                    logger.warning("PDF appears to be scanned. Using OCR...")
                    try:
                        pages = convert_from_path(file_path)
                        ocr_text = ""

                        for i, page_image in enumerate(pages[:20]):
                            ocr_page_text = pytesseract.image_to_string(page_image)
                            ocr_page_text = self._sanitize_text(ocr_page_text)
                            ocr_text += ocr_page_text
                            logger.debug(f"OCR page {i + 1}: {len(ocr_page_text)} chars")

                        if not ocr_text.strip():
                            logger.error("OCR failed to extract any text.")
                            text = "[This appears to be a scanned PDF with no extractable text. OCR failed.]"
                        else:
                            text = ocr_text
                            logger.info(f"OCR extraction complete: {len(text)} characters")

                    except Exception as e:
                        logger.error("OCR processing failed", exc_info=True)
                        raise ProcessingError(f"Text extraction error: {e}")

                return self._sanitize_text(text)

            # ---------------- DOCX ----------------
            elif is_docx:
                doc = DocxReader(file_path)
                text = "\n".join(p.text for p in doc.paragraphs)
                logger.info(f"DOCX extraction: {len(text)} characters")

            # ---------------- EXCEL ----------------
            elif is_excel:
                df = pd.read_excel(file_path, nrows=500)
                text = df.to_string(index=False)
                logger.info(f"Excel extraction: {len(text)} characters")

            # ---------------- CSV ----------------
            elif is_csv:
                df = pd.read_csv(file_path, nrows=500)
                text = df.to_string(index=False)
                logger.info(f"CSV extraction: {len(text)} characters")

            # ---------------- TXT ----------------
            elif is_txt:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                logger.info(f"TXT extraction: {len(text)} characters")

            else:
                logger.warning(f"Unsupported file type: {mime_type or ext}")

        except Exception as e:
            logger.error("Text extraction failed", exc_info=True)
            raise ProcessingError(f"Text extraction error: {e}")

        return self._sanitize_text(text)

    # GEMINI (ASYNC)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=10, max=60),
        retry=retry_if_exception_message(match=".*Rate Limit.*|.*429.*"),
    )
    async def _get_gemini_summary(self, file_path: str, mime_type: str) -> str:
        try:
            uploaded_file = self.gemini_client.files.upload(
                file=file_path,
                config={"mime_type": mime_type},
            )

            await asyncio.sleep(2)

            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=[
                    "Analyze the document below and extract its most important insights.\n"
                    "Rules:\n"
                    "- Provide EXACTLY 4 bullet points\n"
                    "- Each bullet should capture a key insight\n"
                    "- No intro, no conclusion\n"
                    "- Output ONLY bullet points\n\n"
                    "Document:",
                    uploaded_file,
                ],
            )

            return response.text.strip()

        except Exception as e:
            if "429" in str(e):
                raise Exception("Gemini Rate Limit")
            raise Exception(f"Gemini error: {e}")

    
    # OLLAMA (SYNC – CELERY SAFE)
    
    def _get_ollama_summary_sync(self, file_path: str, mime_type: str | None = None) -> str:
        try:
            extracted_text = self._sanitize_text(
                self._extract_text_metadata(file_path, mime_type)
            )

            if not extracted_text or len(extracted_text) < 50:
                raise ProcessingError(
                    f"NON_RETRYABLE: document too short ({len(extracted_text)} chars)"
                )

            if len(extracted_text) > 8000:
                extracted_text = extracted_text[:8000] + "...(truncated)"

            logger.info(f"Sending {len(extracted_text)} chars to Ollama")

            response = self.ollama_client.chat(
                model=self.ollama_model,
                options={"temperature": 0.2},
                messages=[{
                    "role": "user",
                    "content": f"""Analyze the document below and extract its most important insights.

RULES (STRICT):
- EXACTLY 4 bullet points
- One sentence per bullet
- No intro, no conclusion
- Output ONLY bullet points

DOCUMENT:
{extracted_text}
"""
                }],
            )

            return self._sanitize_text(response["message"]["content"])

        except ProcessingError:
            raise

        except Exception as e:
            if "NUL" in str(e):
                raise ProcessingError("NON_RETRYABLE: NUL character detected")
            logger.error("Ollama processing failed", exc_info=True)
            raise ProcessingError(f"AI Engine failed: {e}")

    
    def _format_results(self, raw_text: str, summary: str) -> dict:
        """Shared logic for formatting analysis output."""
        return {
            "raw_text": raw_text,
            "analysis": {
                "summary": summary,
                "word_count": len(raw_text.split()),
                # Basic token estimation: ~4 chars per token for English text
                "estimated_tokens": len(raw_text) // 4,
                "contains_email": "@" in raw_text,
                "contains_money": any(s in raw_text for s in ["$", "USD", "NGN", "€"]),
                "ai_provider": self.provider,
            },
        }

    # FASTAPI (ASYNC)
    
    async def process(self, file_path: str, mime_type: str | None = None) -> dict:
        logger.info(f"Processing document with {self.provider}: {file_path}")

        if self.provider == "ollama":
            loop = asyncio.get_running_loop()
            summary = await loop.run_in_executor(
                None, self._get_ollama_summary_sync, file_path, mime_type
            )
        else:
            summary = await self._get_gemini_summary(file_path, mime_type)

        raw_text = self._extract_text_metadata(file_path, mime_type)

        return self._format_results(raw_text, summary)

    
    # CELERY (SYNC)
    
    def process_sync(self, file_path: str, mime_type: str | None = None) -> dict:
        """
        Extracts text and generates a summary. 
        Vector indexing has been moved to RAGService.
        """
        logger.info(f"Processing document for extraction: {file_path}")

        raw_text = self._extract_text_metadata(file_path, mime_type)
        
        if not raw_text.strip():
            raise ProcessingError("No text could be extracted from the document.")

        # Generate a high-fidelity summary
        summary_limit = 10000 
        summary_prompt = (
            "Summarize the document content below.\n"
            "STRICT RULES:\n"
            "- START IMMEDIATELY with the summary content.\n"
            "- Do NOT say 'Here is a summary', 'This document is about', or any other introduction.\n"
            "- Provide 3-5 concise, professional sentences.\n"
            "- If you fail to follow these rules, the output will be rejected.\n\n"
            f"Document Content:\n{raw_text[:summary_limit]}"
        )
        
        try:
            if self.provider == "ollama":
                response = self.ollama_client.chat(
                    model=self.ollama_model,
                    messages=[{"role": "user", "content": summary_prompt}]
                )
                summary = response["message"]["content"]
            else:
                response = self.gemini_client.models.generate_content(
                    model=self.gemini_model,
                    contents=[summary_prompt]
                )
                summary = response.text
        except Exception as e:
            logger.warning(f"Failed to generate initial summary: {e}")
            summary = "Summary unavailable."

        return self._format_results(raw_text, summary)


