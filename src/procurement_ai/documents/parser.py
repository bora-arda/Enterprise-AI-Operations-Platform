"""Document parsing utilities."""

import logging
from pathlib import Path

from pypdf import PdfReader

logger = logging.getLogger(__name__)


class DocumentParser:
    """Parse various document formats into text."""

    @staticmethod
    def parse_pdf(file_path: Path) -> str:
        """Extract text from a PDF file."""
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text

    @staticmethod
    def parse_text(file_path: Path) -> str:
        """Read a text file."""
        return file_path.read_text(encoding="utf-8")

    @staticmethod
    def parse_docx(file_path: Path) -> str:
        """Extract text from a DOCX file."""
        from docx import Document

        doc = Document(str(file_path))
        return "\n".join([para.text for para in doc.paragraphs])

    @classmethod
    def parse(cls, file_path: Path) -> str:
        """Parse a document based on its extension."""
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return cls.parse_pdf(file_path)
        elif suffix == ".txt" or suffix == ".md":
            return cls.parse_text(file_path)
        elif suffix == ".docx":
            return cls.parse_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
