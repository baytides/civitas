"""PDF processing utilities including OCR support.

This module provides utilities for processing PDFs, including:
- OCR processing for scanned documents
- Text extraction
- File validation

Uses OCRmyPDF for OCR processing when installed.
"""

import os
import subprocess
import tempfile
from pathlib import Path


def has_ocrmypdf() -> bool:
    """Check if ocrmypdf is available."""
    try:
        result = subprocess.run(
            ["ocrmypdf", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def ocr_pdf(
    input_path: str | Path,
    output_path: str | Path | None = None,
    force_ocr: bool = False,
    skip_text: bool = True,
    deskew: bool = True,
    language: str = "eng",
) -> Path:
    """Run OCR on a PDF file.

    Args:
        input_path: Path to input PDF
        output_path: Path for output PDF (defaults to temp file)
        force_ocr: Force OCR even if text exists
        skip_text: Skip pages that already have text
        deskew: Attempt to straighten skewed pages
        language: OCR language (default: English)

    Returns:
        Path to the OCR'd PDF

    Raises:
        RuntimeError: If OCRmyPDF is not installed
        subprocess.CalledProcessError: If OCR fails
    """
    if not has_ocrmypdf():
        raise RuntimeError(
            "ocrmypdf is not installed. Install with: sudo apt install ocrmypdf"
        )

    input_path = Path(input_path)
    if output_path is None:
        # Create temp file with same name pattern
        suffix = f"_ocr{input_path.suffix}"
        fd, output_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
    output_path = Path(output_path)

    cmd = ["ocrmypdf"]

    if force_ocr:
        cmd.append("--force-ocr")
    elif skip_text:
        cmd.append("--skip-text")

    if deskew:
        cmd.append("--deskew")

    cmd.extend(["-l", language])
    cmd.extend([str(input_path), str(output_path)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        result.check_returncode()
    except subprocess.CalledProcessError as e:
        # Check if it's just "no text found" which is OK
        if "PriorOcrFoundError" in e.stderr or "already has text" in e.stderr.lower():
            # Just copy input to output
            import shutil
            shutil.copy(input_path, output_path)
        else:
            raise

    return output_path


def extract_text_from_pdf(pdf_path: str | Path, max_pages: int | None = None) -> str:
    """Extract text from a PDF file.

    Uses pdfplumber for text extraction. If the PDF appears to be scanned
    (no text extracted), attempts OCR first if available.

    Args:
        pdf_path: Path to the PDF file
        max_pages: Maximum number of pages to process (None for all)

    Returns:
        Extracted text content
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber required: pip install pdfplumber")

    pdf_path = Path(pdf_path)
    text_parts = []

    with pdfplumber.open(pdf_path) as pdf:
        pages_to_process = pdf.pages[:max_pages] if max_pages else pdf.pages

        for page in pages_to_process:
            text = page.extract_text()
            if text:
                text_parts.append(text)

    # If no text found, try OCR
    if not text_parts and has_ocrmypdf():
        try:
            ocr_path = ocr_pdf(pdf_path, force_ocr=True)
            with pdfplumber.open(ocr_path) as pdf:
                pages_to_process = pdf.pages[:max_pages] if max_pages else pdf.pages
                for page in pages_to_process:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            # Clean up temp file
            if str(ocr_path).startswith(tempfile.gettempdir()):
                os.unlink(ocr_path)
        except Exception:
            pass  # OCR failed, return empty

    return "\n\n".join(text_parts)


def is_scanned_pdf(pdf_path: str | Path, sample_pages: int = 3) -> bool:
    """Check if a PDF appears to be a scanned document (no embedded text).

    Args:
        pdf_path: Path to the PDF file
        sample_pages: Number of pages to sample

    Returns:
        True if the PDF appears to be scanned (no text on sampled pages)
    """
    try:
        import pdfplumber
    except ImportError:
        return False  # Can't determine without pdfplumber

    pdf_path = Path(pdf_path)

    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_to_check = pdf.pages[:sample_pages]
            for page in pages_to_check:
                text = page.extract_text()
                if text and len(text.strip()) > 50:  # Has meaningful text
                    return False
            return True  # No text found
    except Exception:
        return False


def process_pdf_for_ingestion(
    pdf_path: str | Path,
    output_dir: str | Path | None = None,
    ocr_if_needed: bool = True,
) -> tuple[Path, str]:
    """Process a PDF for ingestion, applying OCR if needed.

    This is the main entry point for PDF processing in ingestion pipelines.

    Args:
        pdf_path: Path to the input PDF
        output_dir: Directory for processed files (defaults to same dir as input)
        ocr_if_needed: Whether to apply OCR to scanned documents

    Returns:
        Tuple of (processed_pdf_path, extracted_text)
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir) if output_dir else pdf_path.parent

    # Check if OCR is needed
    needs_ocr = ocr_if_needed and is_scanned_pdf(pdf_path)

    if needs_ocr and has_ocrmypdf():
        # Apply OCR
        output_path = output_dir / f"{pdf_path.stem}_ocr{pdf_path.suffix}"
        try:
            processed_path = ocr_pdf(pdf_path, output_path, force_ocr=True)
        except Exception:
            # Fall back to original if OCR fails
            processed_path = pdf_path
    else:
        processed_path = pdf_path

    # Extract text
    text = extract_text_from_pdf(processed_path)

    return processed_path, text


# CLI for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PDF processing utilities")
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument("--ocr", action="store_true", help="Force OCR")
    parser.add_argument("--check", action="store_true", help="Check if scanned")
    parser.add_argument("--extract", action="store_true", help="Extract text")

    args = parser.parse_args()

    if args.check:
        is_scanned = is_scanned_pdf(args.pdf)
        print(f"Is scanned: {is_scanned}")

    if args.ocr:
        if not has_ocrmypdf():
            print("ocrmypdf not installed")
        else:
            output = ocr_pdf(args.pdf)
            print(f"OCR output: {output}")

    if args.extract:
        text = extract_text_from_pdf(args.pdf)
        print(f"Extracted {len(text)} characters")
        print(text[:1000])
