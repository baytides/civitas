"""Document processing pipeline.

Converts various document formats to AI-ready markdown with OCR support.
Heavy processing is offloaded to Carl (Ollama on Azure).
"""

from .chunker import DocumentChunker
from .detector import DocumentDetector
from .normalizer import DocumentNormalizer
from .pdf import PDFProcessor

__all__ = [
    "DocumentChunker",
    "DocumentDetector",
    "DocumentNormalizer",
    "PDFProcessor",
]
