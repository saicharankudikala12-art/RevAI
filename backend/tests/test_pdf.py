"""Automated tests for PDF upload and processing service."""
import io
import pytest
from fastapi.testclient import TestClient
import pypdf

try:
    from backend.app.main import app
    from backend.app.core.config import settings
    from backend.app.services.pdf_service import (
        validate_pdf_content,
        extract_pdf_data,
        PDFProcessingError,
    )
except ImportError:
    from app.main import app
    from app.core.config import settings
    from app.services.pdf_service import (
        validate_pdf_content,
        extract_pdf_data,
        PDFProcessingError,
    )


def create_sample_pdf(num_pages: int = 1, text_per_page: str = "Revision Question: What is an algorithm?") -> bytes:
    """Generate an in-memory valid PDF with text across specified number of pages."""
    base_pdf = f"""%PDF-1.4
1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj
2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj
3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources <</Font <</F1 5 0 R>>>>>> endobj
4 0 obj <</Length {len(text_per_page) + 36}>> stream
BT
/F1 14 Tf
50 700 Td
({text_per_page}) Tj
ET
endstream
endobj
5 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000227 00000 n 
0000000322 00000 n 
trailer <</Size 6 /Root 1 0 R>>
startxref
393
%%EOF"""
    reader = pypdf.PdfReader(io.BytesIO(base_pdf.encode("latin1")))
    writer = pypdf.PdfWriter()
    for _ in range(num_pages):
        writer.add_page(reader.pages[0])
    
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def create_blank_pdf(num_pages: int = 1) -> bytes:
    """Generate an in-memory PDF with blank pages (no extractable text)."""
    writer = pypdf.PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


@pytest.fixture
def client():
    """Test client fixture."""
    with TestClient(app) as test_client:
        yield test_client


def test_valid_pdf_upload_single_page(client):
    """Test uploading a valid single-page PDF returns correct metrics and text."""
    pdf_bytes = create_sample_pdf(num_pages=1, text_per_page="Physics Exam: Explain Newton First Law")
    response = client.post(
        "/api/pdf/upload",
        files={"file": ("physics_exam.pdf", pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "processed"
    assert data["filename"] == "physics_exam.pdf"
    assert data["page_count"] == 1
    assert "Newton First Law" in data["extracted_text"]
    assert data["text_length"] > 0
    assert data["word_count"] > 0
    assert len(data["preview"]) > 0


def test_valid_pdf_upload_multi_page(client):
    """Test uploading a multi-page PDF correctly counts all pages and extracts text."""
    pdf_bytes = create_sample_pdf(num_pages=4, text_per_page="Computer Science Data Structures Revision")
    response = client.post(
        "/api/pdf/upload",
        files={"file": ("cs_revision_bank.pdf", pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["page_count"] == 4
    assert data["filename"] == "cs_revision_bank.pdf"
    assert "Data Structures" in data["extracted_text"]


def test_missing_file(client):
    """Test sending a request without a file parameter returns 422 or 400."""
    response = client.post("/api/pdf/upload")
    assert response.status_code in [400, 422]


def test_non_pdf_file_extension(client):
    """Test uploading a file with non-PDF extension is rejected with 400."""
    response = client.post(
        "/api/pdf/upload",
        files={"file": ("study_notes.txt", b"Some plain text notes", "text/plain")}
    )
    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]


def test_fake_pdf_magic_bytes(client):
    """Test uploading a file named .pdf but containing non-PDF bytes is rejected."""
    fake_bytes = b"Hello, this is not a real PDF document."
    response = client.post(
        "/api/pdf/upload",
        files={"file": ("spoofed.pdf", fake_bytes, "application/pdf")}
    )
    assert response.status_code == 400
    assert "does not match PDF specification" in response.json()["detail"]


def test_empty_pdf_file(client):
    """Test uploading a 0-byte file is rejected with 400."""
    response = client.post(
        "/api/pdf/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_corrupted_pdf_file(client):
    """Test uploading a corrupted PDF file is rejected with 400."""
    corrupted_bytes = b"%PDF-1.4\n" + b"\x00\xFF\xAA\x55GarbageCorruptDataThatCannotBeParsed"
    response = client.post(
        "/api/pdf/upload",
        files={"file": ("corrupted.pdf", corrupted_bytes, "application/pdf")}
    )
    assert response.status_code == 400
    assert "corrupted" in response.json()["detail"].lower()


def test_pdf_with_no_extractable_text(client):
    """Test uploading a PDF with only blank/image pages returns an informative 400."""
    blank_pdf = create_blank_pdf(num_pages=2)
    response = client.post(
        "/api/pdf/upload",
        files={"file": ("scanned_blank.pdf", blank_pdf, "application/pdf")}
    )
    assert response.status_code == 400
    assert "no extractable text" in response.json()["detail"].lower()


def test_oversized_file_handling():
    """Test that file exceeding MAX_UPLOAD_SIZE_MB raises 413."""
    # Test validate_pdf_content with 1MB limit and 1.5MB of data
    oversized_bytes = b"%PDF-1.4" + b"X" * (2 * 1024 * 1024)
    with pytest.raises(PDFProcessingError) as exc_info:
        validate_pdf_content(oversized_bytes, "oversized.pdf", max_size_mb=1)
    assert exc_info.value.status_code == 413
    assert "exceeds the maximum allowed limit" in exc_info.value.message
