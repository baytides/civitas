"""Unified document normalizer - converts any format to markdown."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from civitas.storage import AzureStorageClient

from .detector import DocumentDetector, DocumentInfo, DocumentType
from .docx import DOCXProcessor
from .html import HTMLProcessor
from .pdf import PDFProcessor
from .xml import XMLProcessor


@dataclass
class NormalizedDocument:
    """A document normalized to markdown."""

    original_path: Path
    document_info: DocumentInfo
    markdown_content: str
    markdown_path: Optional[Path] = None
    text_path: Optional[Path] = None
    word_count: int = 0
    page_count: int = 0

    # Azure URLs if uploaded
    azure_original_url: Optional[str] = None
    azure_markdown_url: Optional[str] = None


class DocumentNormalizer:
    """Normalize any document format to clean markdown.

    This is the main entry point for document processing.
    Automatically detects format and applies appropriate processor.
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        azure_client: Optional[AzureStorageClient] = None,
    ):
        """Initialize normalizer.

        Args:
            output_dir: Base directory for processed files.
            azure_client: Azure storage client for uploads.
        """
        self.output_dir = output_dir or Path("data/processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.azure_client = azure_client

        # Initialize processors
        self.detector = DocumentDetector()
        self.pdf_processor = PDFProcessor(
            azure_client=azure_client,
            output_dir=self.output_dir / "pdf",
        )
        self.html_processor = HTMLProcessor(
            output_dir=self.output_dir / "markdown",
        )
        self.xml_processor = XMLProcessor(
            output_dir=self.output_dir / "markdown",
        )
        self.docx_processor = DOCXProcessor(
            output_dir=self.output_dir / "markdown",
        )

    def normalize(
        self,
        path: Path | str,
        force_ocr: bool = False,
        upload_to_azure: bool = True,
    ) -> NormalizedDocument:
        """Normalize a document to markdown.

        Args:
            path: Path to the document.
            force_ocr: Force OCR for PDFs even if text exists.
            upload_to_azure: Upload results to Azure storage.

        Returns:
            NormalizedDocument with markdown content.
        """
        path = Path(path)

        # Detect document type
        info = self.detector.detect(path)

        # Process based on type
        if info.document_type == DocumentType.PDF:
            result = self._process_pdf(path, info, force_ocr, upload_to_azure)

        elif info.document_type == DocumentType.HTML:
            result = self._process_html(path, info)

        elif info.document_type == DocumentType.XML:
            result = self._process_xml(path, info)

        elif info.document_type == DocumentType.DOCX:
            result = self._process_docx(path, info)

        elif info.document_type in (DocumentType.TXT, DocumentType.MARKDOWN):
            result = self._process_text(path, info)

        else:
            raise ValueError(f"Unsupported document type: {info.document_type}")

        # Upload markdown to Azure if configured
        if upload_to_azure and self.azure_client and result.markdown_content:
            self._upload_markdown(result, info)

        return result

    def _process_pdf(
        self,
        path: Path,
        info: DocumentInfo,
        force_ocr: bool,
        upload_to_azure: bool,
    ) -> NormalizedDocument:
        """Process PDF document."""
        pdf_result = self.pdf_processor.process(
            path,
            force_ocr=force_ocr,
            upload_to_azure=upload_to_azure,
            document_type=info.content_type.value,
        )

        # Read text content
        markdown_content = ""
        if pdf_result.text_path and pdf_result.text_path.exists():
            markdown_content = pdf_result.text_path.read_text(encoding="utf-8")

        return NormalizedDocument(
            original_path=path,
            document_info=info,
            markdown_content=markdown_content,
            markdown_path=pdf_result.text_path,
            text_path=pdf_result.text_path,
            word_count=len(markdown_content.split()),
            page_count=pdf_result.page_count,
            azure_original_url=pdf_result.azure_original_url,
            azure_markdown_url=pdf_result.azure_text_url,
        )

    def _process_html(self, path: Path, info: DocumentInfo) -> NormalizedDocument:
        """Process HTML document."""
        html_result = self.html_processor.process(path, encoding=info.encoding or "utf-8")

        return NormalizedDocument(
            original_path=path,
            document_info=info,
            markdown_content=html_result.text_content,
            markdown_path=html_result.markdown_path,
            word_count=html_result.word_count,
        )

    def _process_xml(self, path: Path, info: DocumentInfo) -> NormalizedDocument:
        """Process XML document."""
        xml_result = self.xml_processor.process(path)

        return NormalizedDocument(
            original_path=path,
            document_info=info,
            markdown_content=xml_result.text_content,
            markdown_path=xml_result.markdown_path,
            word_count=len(xml_result.text_content.split()),
        )

    def _process_docx(self, path: Path, info: DocumentInfo) -> NormalizedDocument:
        """Process DOCX document."""
        docx_result = self.docx_processor.process(path)

        return NormalizedDocument(
            original_path=path,
            document_info=info,
            markdown_content=docx_result.text_content,
            markdown_path=docx_result.markdown_path,
            word_count=docx_result.word_count,
        )

    def _process_text(self, path: Path, info: DocumentInfo) -> NormalizedDocument:
        """Process plain text or markdown."""
        content = path.read_text(encoding=info.encoding or "utf-8")

        return NormalizedDocument(
            original_path=path,
            document_info=info,
            markdown_content=content,
            markdown_path=path if info.document_type == DocumentType.MARKDOWN else None,
            word_count=len(content.split()),
        )

    def _upload_markdown(self, result: NormalizedDocument, info: DocumentInfo) -> None:
        """Upload markdown to Azure."""
        if not self.azure_client or not result.markdown_content:
            return

        result.azure_markdown_url = self.azure_client.upload_document(
            result.markdown_content.encode("utf-8"),
            "documents/normalized/markdown",
            info.content_type.value,
            result.original_path.stem,
            "md",
        )

    def batch_normalize(
        self,
        paths: list[Path],
        progress_callback: Optional[callable] = None,
    ) -> list[NormalizedDocument]:
        """Normalize multiple documents.

        Args:
            paths: List of document paths.
            progress_callback: Called with (current, total) after each file.

        Returns:
            List of normalized documents.
        """
        results = []
        total = len(paths)

        for i, path in enumerate(paths):
            try:
                result = self.normalize(path)
                results.append(result)
            except Exception as e:
                print(f"Error normalizing {path}: {e}")
                # Add empty result
                info = DocumentInfo(
                    path=path,
                    document_type=DocumentType.UNKNOWN,
                    content_type=self.detector._detect_content_type(path),
                    mime_type="application/octet-stream",
                    size_bytes=0,
                    needs_ocr=False,
                )
                results.append(
                    NormalizedDocument(
                        original_path=path,
                        document_info=info,
                        markdown_content="",
                    )
                )

            if progress_callback:
                progress_callback(i + 1, total)

        return results
