"""PDF processing with OCR support."""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from civitas.storage import AzureStorageClient


@dataclass
class PDFProcessingResult:
    """Result of PDF processing."""

    original_path: Path
    searchable_pdf_path: Optional[Path] = None
    text_path: Optional[Path] = None
    page_count: int = 0
    ocr_applied: bool = False
    confidence: float = 0.0
    azure_original_url: Optional[str] = None
    azure_searchable_url: Optional[str] = None
    azure_text_url: Optional[str] = None


class PDFProcessor:
    """Process PDFs with OCR and text extraction.

    Uses ocrmypdf for OCR and PyMuPDF for text extraction.
    Heavy OCR work can be offloaded to Carl (Azure VM).
    """

    def __init__(
        self,
        azure_client: Optional[AzureStorageClient] = None,
        carl_url: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ):
        """Initialize PDF processor.

        Args:
            azure_client: Azure storage client for uploading results.
            carl_url: URL for Carl AI (for offloading heavy OCR).
            output_dir: Local directory for processed files.
        """
        self.azure_client = azure_client
        self.carl_url = carl_url or os.getenv("CARL_URL", "http://20.98.70.48:11434")
        self.output_dir = output_dir or Path("data/processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process(
        self,
        pdf_path: Path | str,
        force_ocr: bool = False,
        upload_to_azure: bool = True,
        document_type: str = "general",
    ) -> PDFProcessingResult:
        """Process a PDF file.

        Args:
            pdf_path: Path to the PDF file.
            force_ocr: Force OCR even if text is extractable.
            upload_to_azure: Upload results to Azure Blob Storage.
            document_type: Type for Azure storage organization.

        Returns:
            PDFProcessingResult with paths and metadata.
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        result = PDFProcessingResult(original_path=pdf_path)

        # Get page count and check if OCR is needed
        needs_ocr, page_count, existing_text = self._analyze_pdf(pdf_path)
        result.page_count = page_count

        if force_ocr or needs_ocr:
            # Apply OCR
            searchable_path = self._apply_ocr(pdf_path)
            if searchable_path:
                result.searchable_pdf_path = searchable_path
                result.ocr_applied = True
                # Extract text from OCR'd PDF
                text_content = self._extract_text(searchable_path)
            else:
                # OCR failed, use original
                text_content = existing_text
        else:
            # PDF already has text
            result.searchable_pdf_path = pdf_path
            text_content = existing_text

        # Save text file
        if text_content:
            text_path = self.output_dir / f"{pdf_path.stem}.txt"
            text_path.write_text(text_content, encoding="utf-8")
            result.text_path = text_path

        # Upload to Azure if configured
        if upload_to_azure and self.azure_client:
            result = self._upload_to_azure(result, document_type)

        return result

    def _analyze_pdf(self, pdf_path: Path) -> tuple[bool, int, str]:
        """Analyze PDF to determine if OCR is needed.

        Returns:
            (needs_ocr, page_count, existing_text)
        """
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)
            page_count = len(doc)

            # Extract text from all pages
            text_parts = []
            total_chars = 0

            for page in doc:
                text = page.get_text()
                text_parts.append(text)
                total_chars += len(text.strip())

            doc.close()

            existing_text = "\n\n".join(text_parts)

            # If less than 100 chars per page average, likely needs OCR
            avg_chars_per_page = total_chars / page_count if page_count > 0 else 0
            needs_ocr = avg_chars_per_page < 100

            return needs_ocr, page_count, existing_text

        except ImportError:
            # PyMuPDF not available, assume OCR needed
            return True, 0, ""
        except Exception as e:
            print(f"Error analyzing PDF: {e}")
            return True, 0, ""

    def _apply_ocr(self, pdf_path: Path) -> Optional[Path]:
        """Apply OCR to PDF using ocrmypdf.

        Returns:
            Path to searchable PDF, or None if OCR failed.
        """
        output_path = self.output_dir / f"{pdf_path.stem}_ocr.pdf"

        try:
            # Use ocrmypdf command line
            result = subprocess.run(
                [
                    "ocrmypdf",
                    "--skip-text",  # Don't OCR pages that already have text
                    "--optimize", "1",  # Light optimization
                    "--output-type", "pdf",
                    str(pdf_path),
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            if result.returncode == 0:
                return output_path
            else:
                print(f"OCR failed: {result.stderr}")
                return None

        except FileNotFoundError:
            print("ocrmypdf not installed. Install with: pip install ocrmypdf")
            return None
        except subprocess.TimeoutExpired:
            print("OCR timed out")
            return None
        except Exception as e:
            print(f"OCR error: {e}")
            return None

    def _extract_text(self, pdf_path: Path) -> str:
        """Extract text from PDF."""
        try:
            import fitz

            doc = fitz.open(pdf_path)
            text_parts = []

            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

            doc.close()
            return "\n\n".join(text_parts)

        except ImportError:
            return ""
        except Exception as e:
            print(f"Text extraction error: {e}")
            return ""

    def _upload_to_azure(
        self,
        result: PDFProcessingResult,
        document_type: str,
    ) -> PDFProcessingResult:
        """Upload processed files to Azure Blob Storage."""
        if not self.azure_client:
            return result

        base_name = result.original_path.stem

        # Upload original
        with open(result.original_path, "rb") as f:
            result.azure_original_url = self.azure_client.upload_document(
                f.read(),
                "documents/originals/pdf",
                document_type,
                base_name,
                "pdf",
            )

        # Upload searchable PDF if different from original
        if result.searchable_pdf_path and result.searchable_pdf_path != result.original_path:
            with open(result.searchable_pdf_path, "rb") as f:
                result.azure_searchable_url = self.azure_client.upload_document(
                    f.read(),
                    "documents/processed/pdf",
                    document_type,
                    f"{base_name}_searchable",
                    "pdf",
                )

        # Upload text
        if result.text_path:
            with open(result.text_path, "rb") as f:
                result.azure_text_url = self.azure_client.upload_document(
                    f.read(),
                    "documents/processed/text",
                    document_type,
                    base_name,
                    "txt",
                )

        return result

    def batch_process(
        self,
        pdf_paths: list[Path],
        document_type: str = "general",
        progress_callback: Optional[callable] = None,
    ) -> list[PDFProcessingResult]:
        """Process multiple PDFs.

        Args:
            pdf_paths: List of PDF paths to process.
            document_type: Type for Azure storage organization.
            progress_callback: Called with (current, total) after each file.

        Returns:
            List of processing results.
        """
        results = []
        total = len(pdf_paths)

        for i, pdf_path in enumerate(pdf_paths):
            try:
                result = self.process(pdf_path, document_type=document_type)
                results.append(result)
            except Exception as e:
                print(f"Error processing {pdf_path}: {e}")
                results.append(PDFProcessingResult(original_path=pdf_path))

            if progress_callback:
                progress_callback(i + 1, total)

        return results
