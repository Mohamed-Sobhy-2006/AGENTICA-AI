import tempfile
from pathlib import Path

import pytest
from docx import Document

from docai import (
    DocAIError,
    DocumentResult,
    process_batch,
    process_document,
)

DATA_DIR = Path("tests/data")


def test_text_invoice_extraction_and_parsing():
    """Verify native text PDF invoice extraction and structured fields."""
    pdf_path = DATA_DIR / "invoice_001.pdf"
    if not pdf_path.exists():
        pytest.skip("Sample invoice_001.pdf not found in tests/data")

    result = process_document(pdf_path)

    assert isinstance(result, DocumentResult)
    assert result.filename == "invoice_001.pdf"
    assert result.doc_type == "invoice"
    assert result.confidence_score >= 0.95
    assert len(result.extracted_text) > 50

    data = result.structured_data
    assert data["invoice_number"] == "INV-2025-006253"
    assert data["vendor"] == "Mediterranean Foods"
    assert data["date"] == "2025-07-08"
    assert data["amount"] == 45.55


def test_scanned_invoice_ocr_and_parsing():
    """Verify scanned PDF falls back to PaddleOCR and parses European decimals & vendor."""
    scanned_path = DATA_DIR / "invoice_051_scanned.pdf"
    if not scanned_path.exists():
        pytest.skip("Sample invoice_051_scanned.pdf not found in tests/data")

    result = process_document(scanned_path)

    assert isinstance(result, DocumentResult)
    assert result.doc_type == "invoice"
    assert result.confidence_score >= 0.85
    assert len(result.extracted_text) > 50

    data = result.structured_data
    assert data["invoice_number"] == "84652373"
    assert data["vendor"] == "Nguyen-Roach"
    assert data["date"] == "02/23/2021"
    assert data["amount"] == 232.95
    assert data["currency"] == "USD"


def test_cv_extraction_and_classification():
    """Verify CV classification and contact/name extraction."""
    cv_path = DATA_DIR / "cv_11850315.pdf"
    if not cv_path.exists():
        pytest.skip("Sample cv_11850315.pdf not found in tests/data")

    result = process_document(cv_path)

    assert result.doc_type == "cv"
    assert result.confidence_score >= 0.90
    assert result.structured_data.get("name") == "Tammy Williams MD"


def test_docx_header_body_table_footer():
    """Verify .docx extraction preserves headers, paragraphs, deduplicated tables, and footers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = Path(tmpdir) / "sample_contract.docx"
        doc = Document()

        # Header & Footer
        doc.sections[0].header.paragraphs[0].text = "CONFIDENTIAL HEADER"
        doc.sections[0].footer.paragraphs[0].text = "Page 1 Footer"

        # Body paragraph + Table with merged cells
        doc.add_paragraph("Invoice No: INV-999")
        doc.add_paragraph("Seller:\nAcme Corp")
        table = doc.add_table(rows=1, cols=2)
        cell_a = table.cell(0, 0)
        cell_b = table.cell(0, 1)
        cell_a.merge(cell_b)
        cell_a.text = "Total: $150.00"

        doc.save(docx_path)

        result = process_document(docx_path)
        assert result.doc_type == "invoice"
        assert result.confidence_score == 1.0
        assert "CONFIDENTIAL HEADER" in result.extracted_text
        assert "Page 1 Footer" in result.extracted_text
        # التأكد من عدم تكرار الخلية المدمجة
        assert result.extracted_text.count("Total: $150.00") == 1


def test_email_and_generic_classification():
    """Verify email headers and generic fallback text documents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        email_file = Path(tmpdir) / "meeting.txt"
        email_file.write_text(
            "From: lead@agentica.ai\n"
            "To: fatma@agentica.ai\n"
            "Subject: DocAI Pipeline Review\n"
            "Date: 2026-11-25\n\n"
            "Please push the updated docai branch today.",
            encoding="utf-8",
        )
        email_res = process_document(email_file)
        assert email_res.doc_type == "email"
        assert email_res.structured_data["subject"] == "DocAI Pipeline Review"

        generic_file = Path(tmpdir) / "notes.txt"
        generic_file.write_text(
            "Random internal meeting notes without specific structure.",
            encoding="utf-8",
        )
        generic_res = process_document(generic_file)
        assert generic_res.doc_type == "generic"
        assert "raw_preview" in generic_res.structured_data


def test_error_handling_contracts():
    """Verify DocAIError returns standard contract error codes."""
    with pytest.raises(DocAIError) as not_found_err:
        process_document("tests/data/non_existent_file_xyz.pdf")
    assert not_found_err.value.error_code == "ERR_DOC_NOT_FOUND"

    with tempfile.TemporaryDirectory() as tmpdir:
        bad_file = Path(tmpdir) / "archive.zip"
        bad_file.write_bytes(b"PK\x03\x04")
        with pytest.raises(DocAIError) as format_err:
            process_document(bad_file)
        assert format_err.value.error_code == "ERR_UNSUPPORTED_FORMAT"


def test_batch_processing():
    """Verify process_batch runs cleanly across multiple files."""
    files = [
        p
        for p in [DATA_DIR / "invoice_001.pdf", DATA_DIR / "cv_11850315.pdf"]
        if p.exists()
    ]
    if not files:
        pytest.skip("No sample files available for batch test")

    results = process_batch(files)
    assert len(results) == len(files)
    assert all(isinstance(r, DocumentResult) for r in results)
