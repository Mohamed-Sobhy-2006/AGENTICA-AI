from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from docai.classifier import classify_document, extract_structured_data
from docai.extractor import extract_text
from docai.schemas import DocumentResult


class DocAIError(Exception):
    """Structured exception aligned with CONTRACTS.md ErrorResponse schema."""

    def __init__(self, error_code: str, message: str, details: str = ""):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details
        self.timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


def process_document(file_path: str | Path) -> DocumentResult:
    """
    End-to-end DocAI (P4) pipeline entry point:
    1. Validate file existence.
    2. Extract raw text & character-weighted confidence (PyMuPDF / PaddleOCR / python-docx).
    3. Classify document type ('invoice' | 'cv' | 'email' | 'generic').
    4. Extract structured fields according to document type.
    5. Return a validated DocumentResult contract object.
    """
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise DocAIError(
            error_code="ERR_DOC_NOT_FOUND",
            message=f"Document file not found: {path.name}",
            details=str(path),
        )

    try:
        raw_text, confidence = extract_text(str(path))
    except ValueError as exc:
        raise DocAIError(
            error_code="ERR_UNSUPPORTED_FORMAT",
            message=f"Unsupported file format for {path.name}.",
            details=str(exc),
        ) from exc
    except Exception as exc:
        raise DocAIError(
            error_code="ERR_DOC_PARSING_FAILED",
            message=f"Failed to parse document {path.name}.",
            details=str(exc),
        ) from exc

    doc_type = classify_document(raw_text, filename=path.name)
    structured = extract_structured_data(
        raw_text, doc_type=doc_type, filename=path.name
    )

    return DocumentResult(
        filename=path.name,
        doc_type=doc_type,
        extracted_text=raw_text,
        structured_data=structured,
        confidence_score=confidence,
    )


def process_batch(
    file_paths: list[str | Path],
    skip_errors: bool = False,
) -> list[DocumentResult]:
    """
    Process multiple documents sequentially and return a list of DocumentResult objects.
    If skip_errors=True, failed files are skipped instead of halting the batch.
    """
    results: list[DocumentResult] = []
    for fp in file_paths:
        try:
            results.append(process_document(fp))
        except DocAIError:
            if not skip_errors:
                raise
    return results
