import pytesseract
from PyPDF2 import PdfReader
from PIL import Image
from pdf2image import convert_from_path
import os
import tempfile


class DocumentProcessor:
    def extract_text(self, file_path: str) -> str:
        """Handles normal digital PDFs"""
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            return text
        except Exception:
            return ""


    def ocr_text(self, file_path: str) -> str:
        """OCR for images or scanned PDFs"""
        # if it's a PDF convert each page to image
        if file_path.lower().endswith(".pdf"):
            pages = convert_from_path(file_path)
            text = ""
            for i, page in enumerate(pages):
                with tempfile.NamedTemporaryFile(suffix="png", delete=False) as tmp:
                    page.save(tmp.name, "PNG")
                    text += pytesseract.image_to_string(Image.open(tmp.name), lang="eng")
                    os.remove(tmp.name)
            return text

    def analyze_text(self, text: str) -> dict:
        """Return metadata / structure"""
        return {
            "summary": text[:200],
            "word_count": len(text.split()),
            "contains_email": "@" in text,
            "contains_money": any(symbol in text for symbol in ["$", "USD"])
        }

    def process(self, file_path: str) -> dict:
        text = self.extract_text(file_path)
        if not text.strip():
            text = self.ocr_text(file_path)

        return {
            "raw_text": text,
            "analysis": self.analyze_text(text)
        }
