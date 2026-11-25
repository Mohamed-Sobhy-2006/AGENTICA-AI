# Pydantic data contracts and DocumentResult schema for DocAI

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

DocType = Literal["invoice", "cv", "email", "generic"]


class InvoiceData(BaseModel):
    """Structured fields extracted from an invoice document."""

    invoice_number: str | None = None
    vendor: str | None = None
    vendor_name: str | None = None
    date: str | None = None
    amount: float | None = None
    total_amount: float | None = None
    currency: str | None = None


class ContactInfo(BaseModel):
    """Contact details section for a CV."""

    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None


class ExperienceItem(BaseModel):
    """Single work experience entry in a CV."""

    title: str | None = None
    company: str | None = None
    duration: str | None = None
    description: str | None = None


class EducationItem(BaseModel):
    """Single education entry in a CV."""

    degree: str | None = None
    institution: str | None = None
    date: str | None = None


class CVData(BaseModel):
    """Unified 9-field structured schema extracted from a CV/Resume."""

    file_name: str | None = None
    layout_type: str | None = None
    name: str | None = None
    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: str | None = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class EmailData(BaseModel):
    """Structured fields extracted from an email document."""

    subject: str | None = None
    sender: str | None = None
    recipient: str | None = None
    date: str | None = None
    body: str | None = None


class DocumentResult(BaseModel):
    """
    Core Document AI output contract (P4) shared with Supervisor (P1) and RAG (P3).
    """

    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    doc_type: DocType = "generic"
    extracted_text: str = ""
    structured_data: dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    processed_at: str = Field(
        default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
