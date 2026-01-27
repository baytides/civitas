"""Document type and format detection."""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class DocumentType(Enum):
    """Supported document types."""

    PDF = "pdf"
    HTML = "html"
    XML = "xml"
    DOCX = "docx"
    TXT = "txt"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"


class ContentType(Enum):
    """Content categories."""

    P2025 = "p2025"
    COURT_OPINION = "court_opinion"
    EXECUTIVE_ORDER = "eo"
    FEDERAL_REGISTER = "federal_register"
    US_CODE = "us_code"
    STATE_CONSTITUTION = "state_constitution"
    STATE_BILL = "state_bill"
    CONGRESSIONAL_BILL = "congressional_bill"
    NEWS_ARTICLE = "news_article"
    UNKNOWN = "unknown"


@dataclass
class DocumentInfo:
    """Information about a detected document."""

    path: Path
    document_type: DocumentType
    content_type: ContentType
    mime_type: str
    size_bytes: int
    needs_ocr: bool
    encoding: str | None = None


class DocumentDetector:
    """Detects document format, type, and processing requirements."""

    # Extension to type mapping
    EXT_MAP = {
        ".pdf": DocumentType.PDF,
        ".html": DocumentType.HTML,
        ".htm": DocumentType.HTML,
        ".xml": DocumentType.XML,
        ".docx": DocumentType.DOCX,
        ".txt": DocumentType.TXT,
        ".md": DocumentType.MARKDOWN,
        ".markdown": DocumentType.MARKDOWN,
    }

    # Path patterns for content type detection
    CONTENT_PATTERNS = {
        "project2025": ContentType.P2025,
        "mandate": ContentType.P2025,
        "scotus": ContentType.COURT_OPINION,
        "supreme": ContentType.COURT_OPINION,
        "opinion": ContentType.COURT_OPINION,
        "executive-order": ContentType.EXECUTIVE_ORDER,
        "eo-": ContentType.EXECUTIVE_ORDER,
        "federal-register": ContentType.FEDERAL_REGISTER,
        "uscode": ContentType.US_CODE,
        "constitution": ContentType.STATE_CONSTITUTION,
        "bill": ContentType.STATE_BILL,
    }

    def detect(self, path: Path | str) -> DocumentInfo:
        """Detect document information.

        Args:
            path: Path to the document file.

        Returns:
            DocumentInfo with detected properties.
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Document not found: {path}")

        # Detect document type from extension
        ext = path.suffix.lower()
        doc_type = self.EXT_MAP.get(ext, DocumentType.UNKNOWN)

        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        mime_type = mime_type or "application/octet-stream"

        # Get file size
        size_bytes = path.stat().st_size

        # Detect content type from path
        content_type = self._detect_content_type(path)

        # Determine if OCR is needed
        needs_ocr = self._needs_ocr(path, doc_type)

        # Detect encoding for text files
        encoding = None
        if doc_type in (
            DocumentType.HTML,
            DocumentType.XML,
            DocumentType.TXT,
            DocumentType.MARKDOWN,
        ):
            encoding = self._detect_encoding(path)

        return DocumentInfo(
            path=path,
            document_type=doc_type,
            content_type=content_type,
            mime_type=mime_type,
            size_bytes=size_bytes,
            needs_ocr=needs_ocr,
            encoding=encoding,
        )

    def _detect_content_type(self, path: Path) -> ContentType:
        """Detect content type from path patterns."""
        path_str = str(path).lower()

        for pattern, content_type in self.CONTENT_PATTERNS.items():
            if pattern in path_str:
                return content_type

        return ContentType.UNKNOWN

    def _needs_ocr(self, path: Path, doc_type: DocumentType) -> bool:
        """Determine if document needs OCR processing."""
        if doc_type != DocumentType.PDF:
            return False

        # Check if PDF has extractable text
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(path)
            # Sample first few pages
            text_chars = 0
            for page_num in range(min(3, len(doc))):
                page = doc[page_num]
                text = page.get_text()
                text_chars += len(text.strip())

            doc.close()

            # If very little text, likely needs OCR
            return text_chars < 100

        except ImportError:
            # Assume OCR needed if can't check
            return True
        except Exception:
            return True

    def _detect_encoding(self, path: Path) -> str:
        """Detect text file encoding."""
        try:
            import chardet

            with open(path, "rb") as f:
                raw = f.read(10000)
                result = chardet.detect(raw)
                return result.get("encoding", "utf-8") or "utf-8"

        except ImportError:
            return "utf-8"
        except Exception:
            return "utf-8"
