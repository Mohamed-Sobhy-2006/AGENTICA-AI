# Pydantic data contracts and DocumentResult schema for DocAI 

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
import uuid
from pydantic import BaseModel, Field


DocType = Literal["invoice", "cv", "email", "generic"]


class InvoiceData(BaseModel):
    """Structured fields extracted from an invoice document."""
    invoice_number: Optional[str] = None
    vendor: Optional[str] = None
    vendor_name: Optional[str] = None
    date: Optional[str] = None
    amount: Optional[float] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None


class ContactInfo(BaseModel):
    """Contact details section for a CV."""
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None


class ExperienceItem(BaseModel):
    """Single work experience entry in a CV."""
    title: Optional[str] = None
    company: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None


class EducationItem(BaseModel):
    """Single education entry in a CV."""
    degree: Optional[str] = None
    institution: Optional[str] = None
    date: Optional[str] = None


class CVData(BaseModel):
    """Unified 9-field structured schema extracted from a CV/Resume."""
    file_name: Optional[str] = None
    layout_type: Optional[str] = None
    name: Optional[str] = None
    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: Optional[str] = ""
    skills: List[str] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)


class EmailData(BaseModel):
    """Structured fields extracted from an email document."""
    subject: Optional[str] = None
    sender: Optional[str] = None
    recipient: Optional[str] = None
    date: Optional[str] = None
    body: Optional[str] = None


class DocumentResult(BaseModel):
    """
    Core Document AI output contract (P4) shared with Supervisor (P1) and RAG (P3).
    """
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    doc_type: DocType = "generic"
    extracted_text: str = ""
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    processed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )