from typing import Protocol


class DocumentProcessorInterface(Protocol):

    def extract_text(self, file_path) -> str:
        pass

    def ocr_text(self, file_path) -> str:
        pass

    def analyze_text(self, text: str):
        pass