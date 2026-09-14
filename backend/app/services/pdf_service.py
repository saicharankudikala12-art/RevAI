"""Service layer for PDF validation, parsing, and text extraction."""
import io
import re
from typing import Dict, Any
import pypdf
from pypdf.errors import PdfStreamError, EmptyFileError


class PDFProcessingError(Exception):
    """Custom exception for expected PDF processing failures."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def validate_pdf_content(content: bytes, filename: str, max_size_mb: int) -> None:
    """
    Validate the raw bytes of an uploaded file.
    
    Args:
        content: Raw bytes of the uploaded file.
        filename: Original file name.
        max_size_mb: Maximum allowed file size in megabytes.
        
    Raises:
        PDFProcessingError: If validation fails.
    """
    if not content or len(content) == 0:
        raise PDFProcessingError("The uploaded file is empty.", status_code=400)

    max_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise PDFProcessingError(
            f"File size exceeds the maximum allowed limit of {max_size_mb} MB.",
            status_code=413
        )

    # Validate PDF signature (magic bytes)
    # The PDF header '%PDF-' must appear near the beginning of the file
    header_snippet = content[:1024].lstrip()
    if not header_snippet.startswith(b"%PDF-"):
        raise PDFProcessingError(
            "The uploaded file is not a valid PDF. File header does not match PDF specification.",
            status_code=400
        )


def extract_pdf_data(content: bytes, filename: str, max_size_mb: int = 25) -> Dict[str, Any]:
    """
    Process PDF content, determine page count, and extract text across all pages.
    
    Args:
        content: Raw bytes of the PDF file.
        filename: Original filename.
        max_size_mb: Maximum allowed file size.
        
    Returns:
        Dict containing filename, page_count, extracted_text, text_length, word_count, preview.
        
    Raises:
        PDFProcessingError: If validation, parsing, or extraction fails.
    """
    validate_pdf_content(content, filename, max_size_mb)

    try:
        stream = io.BytesIO(content)
        reader = pypdf.PdfReader(stream)
    except (PdfStreamError, EmptyFileError, Exception) as exc:
        raise PDFProcessingError(
            "The uploaded PDF is corrupted or could not be parsed.",
            status_code=400
        ) from exc

    page_count = len(reader.pages)
    if page_count == 0:
        raise PDFProcessingError("The uploaded PDF contains no pages.", status_code=400)

    extracted_pages = []
    for page_idx, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
            extracted_pages.append(page_text.strip())
        except Exception as exc:
            # Continue extracting remaining pages if a single page encounters an extraction issue
            extracted_pages.append("")

    full_text = "\n\n".join(filter(None, extracted_pages)).strip()

    # Normalize excessive consecutive newlines and spaces
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)

    if not full_text:
        raise PDFProcessingError(
            "No extractable text was found in the PDF. Please ensure the document contains digital text rather than scanned images.",
            status_code=400
        )

    words = full_text.split()
    preview_limit = 400
    preview = full_text[:preview_limit]
    if len(full_text) > preview_limit:
        preview += "..."

    return {
        "success": True,
        "status": "processed",
        "filename": filename,
        "page_count": page_count,
        "extracted_text": full_text,
        "text_length": len(full_text),
        "word_count": len(words),
        "preview": preview,
        "message": f"Successfully processed {page_count} page{'s' if page_count != 1 else ''} with {len(words):,} words."
    }
