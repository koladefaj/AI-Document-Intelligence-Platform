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
    def __init__(self):
        self.provider = settings.ai_provider.lower()
        self.api_key = settings.gemini_api.strip('"')

        # Gemini client (async)
        self.gemini_client = genai.Client(api_key=self.api_key)

        # Ollama
        self.ollama_model = settings.ollama_model
        self.ollama_client = Client(host=settings.ollama_base_url)

    # TEXT EXTRACTION (EXTENSION + MIME SAFE)
    def _extract_text_metadata(self, file_path: str, mime_type: str | None = None) -> str:
        text = ""

        try:
            ext = os.path.splitext(file_path)[1].lower()

            is_pdf = ext == ".pdf" or mime_type == "application/pdf"

            is_docx = (
                ext in [".docx", ".doc"]
                or mime_type
                in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]
            )

            is_excel = (
                ext in [".xls", ".xlsx"]
                or mime_type
                in [
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "application/vnd.ms-excel",
                ]
            )

            is_csv = ext == ".csv" or mime_type == "text/csv"
            is_txt = ext == ".txt" or mime_type == "text/plain"

            if is_pdf:
                reader = PdfReader(file_path)
                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    text += page_text
                    logger.debug(f"PDF page {i + 1}: {len(page_text)} chars")

                logger.info(f"PDF extraction complete: {len(text)} characters")

                if not text.strip():
                    logger.warning("PDF appears to be scanned. Using OCR...")
                    try:
                        # Convert PDF pages to images
                        pages = convert_from_path(file_path)
                        ocr_text = ""

                        # Limit OCR to first 20 pages to avoid huge PDFs slowing things down
                        for i, page_image in enumerate(pages[:20]):
                            ocr_page_text = pytesseract.image_to_string(page_image)
                            ocr_text += ocr_page_text
                            logger.debug(f"OCR page {i + 1}: {len(ocr_page_text)} chars")

                        # Check if OCR succeeded
                        if not ocr_text.strip():
                            logger.error("OCR failed to extract any text from the scanned PDF.")
                            text = "[This appears to be a scanned PDF with no extractable text. OCR failed.]"
                        else:
                            text = ocr_text
                            logger.info(f"OCR extraction complete: {len(text)} characters")

                    except Exception as e:
                        logger.error(f"OCR processing failed: {e}", exc_info=True)
                        raise ProcessingError(f"Text extraction error: {e}")
                    
                    if text:
                        text = text.replace("\x00", "")
                        text = "".join(char for char in text if char.isprintable() or char in "\n\r\t")

                    return text
                    



            elif is_docx:
                doc = DocxReader(file_path)
                text = "\n".join(p.text for p in doc.paragraphs)
                logger.info(f"DOCX extraction: {len(text)} characters")

            elif is_excel:
                df = pd.read_excel(file_path, nrows=500)
                text = df.to_string(index=False)
                logger.info(f"Excel extraction: {len(text)} characters")

            elif is_csv:
                df = pd.read_csv(file_path, nrows=500)
                text = df.to_string(index=False)
                logger.info(f"CSV extraction: {len(text)} characters")

            elif is_txt:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                logger.info(f"TXT extraction: {len(text)} characters")

            else:
                logger.warning(
                    f"Unsupported file type: {mime_type or ext}"
                )

        except Exception as e:
            logger.error("Text extraction failed", exc_info=True)
            raise ProcessingError(f"Text extraction error: {e}")

        return text

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
                model="gemini-2.0-flash",
                contents=[
                    "Analyze the document below and extract its most important insights.\n"
                    "Rules:\n"
                    "- Provide EXACTLY 4 bullet points\n"
                    "- Each bullet should capture a key insight, result, or recommendation\n"
                    "- Be concise and professional\n"
                    "- No intro, no conclusion, no extra text\n"
                    "- Output ONLY bullet points\n\n"
                    "Document:",
                    uploaded_file,
                ],
            )

            return response.text.strip()

        except Exception as e:
            if "429" in str(e):
                logger.warning("Gemini rate limit hit")
                raise Exception("Gemini Rate Limit")
            raise Exception(f"Gemini error: {e}")

    # OLLAMA (SYNC – CELERY SAFE)
    def _get_ollama_summary_sync(self, file_path: str, mime_type: str | None = None) -> str:
        try:
            extracted_text = self._extract_text_metadata(file_path, mime_type)

            if extracted_text == "[SCANNED_PDF]":
                raise ProcessingError("NON_RETRYABLE: scanned PDF requires OCR")

            if not extracted_text or len(extracted_text.strip()) < 50:
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
- No intro, no conclusion, no headings
- Output ONLY bullet points

DOCUMENT:
{extracted_text}
"""
                }],
            )

            return response["message"]["content"].strip()

        except ProcessingError:
            raise

        except Exception as e:
            logger.error("Ollama processing failed", exc_info=True)
            raise ProcessingError(f"AI Engine failed: {e}")

    # ------------------------------------------------------------------
    # FASTAPI (ASYNC)
    # ------------------------------------------------------------------
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

        return {
            "raw_text": raw_text,
            "analysis": {
                "summary": summary,
                "word_count": len(raw_text.split()),
                "contains_email": "@" in raw_text,
                "contains_money": any(s in raw_text for s in ["$", "USD", "NGN", "€"]),
                "ai_provider": self.provider,
            },
        }

    # ------------------------------------------------------------------
    # CELERY (SYNC)
    # ------------------------------------------------------------------
    def process_sync(self, file_path: str, mime_type: str | None = None) -> dict:
        logger.info(f"Processing document with {self.provider}: {file_path}")

        if self.provider == "ollama":
            summary = self._get_ollama_summary_sync(file_path, mime_type)
        else:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                summary = loop.run_until_complete(
                    self._get_gemini_summary(file_path, mime_type)
                )
            finally:
                loop.close()

        raw_text = self._extract_text_metadata(file_path, mime_type)

        return {
            "raw_text": raw_text,
            "analysis": {
                "summary": summary,
                "word_count": len(raw_text.split()),
                "contains_email": "@" in raw_text,
                "contains_money": any(s in raw_text for s in ["$", "USD", "NGN", "€"]),
                "ai_provider": self.provider,
            },
        }
