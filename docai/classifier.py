# Document type classification and structured data extraction module

import re
from typing import Any, Dict, List, Optional

from docai.schemas import (
    CVData,
    ContactInfo,
    DocType,
    EducationItem,
    EmailData,
    ExperienceItem,
    InvoiceData,
)


def classify_document(text: str, filename: str = "") -> DocType:
    """
    Classify raw document text into one of the contract types:
    'invoice' | 'cv' | 'email' | 'generic'.
    """
    sample = f"{filename}\n{text[:3500]}".lower()

    # _________________________________________________________________________________________________________
    invoice_keywords = [
        "invoice", "invoice no", "invoice #", "bill to", "subtotal",
        "total amount", "amount due", "tax", "vat", "receipt", "seller:",
        "date of issue", "grand total",
    ]
    invoice_score = sum(1 for kw in invoice_keywords if kw in sample)

    # _________________________________________________________________________________________________________
    cv_keywords = [
        "curriculum vitae", "resume", "work experience", "experience",
        "education", "skills", "certifications", "projects", "linkedin.com",
        "summary", "objective", "languages",
    ]
    cv_score = sum(1 for kw in cv_keywords if kw in sample)

    # _________________________________________________________________________________________________________
    email_headers = ["from:", "to:", "subject:", "sent:", "cc:", "bcc:"]
    email_score = sum(1 for h in email_headers if re.search(rf"^{re.escape(h)}", sample, re.MULTILINE))

    if invoice_score >= 2 and invoice_score >= cv_score:
        return "invoice"
    if cv_score >= 2 and cv_score > invoice_score:
        return "cv"
    if email_score >= 3:
        return "email"

    return "generic"


# _________________________________________________________________________________________________________
def _parse_invoice(text: str) -> Dict[str, Any]:
    """Extract structured invoice fields matching both dataset labels and CONTRACTS.md."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # (Invoice Number)
    inv_no_match = re.search(
        r"(?:invoice\s*(?:no|number|#|id)[:.\s-]*)\s*([A-Za-z0-9-]+)",
        text,
        re.IGNORECASE,
    )
    invoice_number = inv_no_match.group(1).strip() if inv_no_match else None

    # (Date)
    date_match = re.search(
        r"(?:date(?:\s+of\s+issue)?[:.\s-]*)\s*(\d{1,4}[-/]\d{1,2}[-/]\d{1,4}|\w+\s+\d{1,2},?\s+\d{4})",
        text,
        re.IGNORECASE,
    )
    if not date_match:
        date_match = re.search(r"\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b", text)
    date_val = date_match.group(1).strip() if date_match else None

    # (Vendor / Vendor Name)
    vendor: Optional[str] = None
    for idx, line in enumerate(lines):
        if re.match(r"^seller\s*:?$", line, re.IGNORECASE):
            for next_line in lines[idx + 1 : idx + 4]:
                if not re.match(r"^(client|bill\s*to)\s*:?$", next_line, re.IGNORECASE):
                    vendor = next_line
                    break
            break

    if not vendor:
        skip_prefixes = ("invoice", "tax invoice", "receipt", "date", "bill to", "seller", "client")
        for line in lines[:6]:
            low = line.lower()
            if (
                not any(low.startswith(p) for p in skip_prefixes)
                and not re.match(r"^\d{1,4}[-/]\d{1,2}[-/]\d{1,4}$", line)
                and len(line) > 2
            ):
                vendor = line
                break

    # (Amount & Currency)
    amount: Optional[float] = None
    currency: Optional[str] = None

    total_block_match = re.search(
        r"(?:grand\s+total|total\s+amount|amount\s+due|balance\s+due|total)\b(.{0,120})",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if total_block_match:
        block_str = total_block_match.group(1)
        amounts_found = re.findall(
            r"([\$€£]|USD|EUR|GBP|EGP)?\s*(\d[\d.,]*\d|\d+)",
            block_str,
            re.IGNORECASE,
        )
        if amounts_found:
            raw_curr, raw_amt = amounts_found[-1]
            if "," in raw_amt and "." not in raw_amt:
                raw_amt = raw_amt.replace(",", ".")
            else:
                raw_amt = raw_amt.replace(",", "")
            try:
                amount = float(raw_amt)
            except ValueError:
                amount = None
            if raw_curr:
                curr_map = {"$": "USD", "€": "EUR", "£": "GBP"}
                currency = curr_map.get(raw_curr, raw_curr.upper())

    if not currency:
        if "$" in text or "USD" in text.upper():
            currency = "USD"
        elif "€" in text or "EUR" in text.upper():
            currency = "EUR"
        elif "£" in text or "GBP" in text.upper():
            currency = "GBP"
        elif "EGP" in text.upper():
            currency = "EGP"

    invoice_obj = InvoiceData(
        invoice_number=invoice_number,
        vendor=vendor,
        vendor_name=vendor,
        date=date_val,
        amount=amount,
        total_amount=amount,
        currency=currency,
    )
    return invoice_obj.model_dump()


# _________________________________________________________________________________________________________
def _extract_cv_section(text: str, section_names: List[str]) -> str:
    """Helper to slice out the body of a specific CV section until the next major heading."""
    all_headings = (
        r"summary|profile|objective|skills|technical\s+skills|core\s+competencies|"
        r"experience|work\s+experience|employment\s+history|education|academic|"
        r"certifications|certificates|projects|languages|awards|references"
    )
    target_pattern = "|".join(re.escape(name) for name in section_names)
    pattern = rf"(?:^|\n)\s*(?:{target_pattern})[:\s]*\n(.+?)(?=\n\s*(?:{all_headings})[:\s]*\n|$)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


# _________________________________________________________________________________________________________
def _parse_cv(text: str, filename: str = "") -> Dict[str, Any]:
    """Extract structured 9-field schema from a CV/Resume into CVData."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # (name)
    name: Optional[str] = None
    for line in lines[:5]:
        if (
            "@" not in line
            and "http" not in line.lower()
            and not re.search(r"\d{3,}", line)
            and 1 <= len(line.split()) <= 5
        ):
            name = line
            break

    # (ContactInfo)
    email_m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phone_m = re.search(r"(\+?\d[\d\s().-]{7,}\d)", text)
    linkedin_m = re.search(
        r"(https?://(?:www\.)?linkedin\.com/in/[^\s|]+|linkedin\.com/in/[^\s|]+)",
        text,
        re.IGNORECASE,
    )

    contact = ContactInfo(
        email=email_m.group(0) if email_m else None,
        phone=phone_m.group(0).strip() if phone_m else None,
        linkedin=linkedin_m.group(0) if linkedin_m else None,
    )

    # (Summary)
    raw_summary = _extract_cv_section(text, ["summary", "profile", "objective"])
    summary = " ".join(raw_summary.split())[:600]

    # (Skills)
    raw_skills_block = _extract_cv_section(text, ["skills", "technical skills", "core competencies"])
    skills: List[str] = []
    if raw_skills_block:
        tokens = re.split(r"[,|•·▪\n]", raw_skills_block)
        skills = [t.strip(" -–:\t") for t in tokens if 1 < len(t.strip(" -–:\t")) <= 40][:30]

    # (Experience)
    raw_exp_block = _extract_cv_section(text, ["work experience", "experience", "employment history"])
    experience: List[ExperienceItem] = []
    if raw_exp_block:
        exp_chunks = [c.strip() for c in re.split(r"\n\s*\n", raw_exp_block) if c.strip()][:5]
        for chunk in exp_chunks:
            chunk_lines = [l.strip() for l in chunk.splitlines() if l.strip()]
            title_line = chunk_lines[0] if chunk_lines else None
            dur_m = re.search(
                r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{4}).{0,25}(?:Present|Current|\d{4}))",
                chunk,
                re.IGNORECASE,
            )
            experience.append(
                ExperienceItem(
                    title=title_line,
                    duration=dur_m.group(1).strip() if dur_m else None,
                    description=" ".join(chunk_lines[1:])[:300] if len(chunk_lines) > 1 else None,
                )
            )

    # (Education)
    raw_edu_block = _extract_cv_section(text, ["education", "academic"])
    education: List[EducationItem] = []
    if raw_edu_block:
        edu_chunks = [c.strip() for c in re.split(r"\n\s*\n", raw_edu_block) if c.strip()][:3]
        for chunk in edu_chunks:
            chunk_lines = [l.strip() for l in chunk.splitlines() if l.strip()]
            year_m = re.search(r"\b(19\d{2}|20\d{2})\b", chunk)
            education.append(
                EducationItem(
                    degree=chunk_lines[0] if chunk_lines else None,
                    institution=chunk_lines[1] if len(chunk_lines) > 1 else None,
                    date=year_m.group(1) if year_m else None,
                )
            )

    # (Certifications)
    raw_cert_block = _extract_cv_section(text, ["certifications", "certificates"])
    certifications: List[str] = []
    if raw_cert_block:
        certifications = [
            line.strip(" -–•·\t")
            for line in raw_cert_block.splitlines()
            if line.strip(" -–•·\t")
        ][:10]

    layout_type = "enhancv_2col" if "enhancv" in filename.lower() else "standard"

    cv_obj = CVData(
        file_name=filename or None,
        layout_type=layout_type,
        name=name,
        contact=contact,
        summary=summary,
        skills=skills,
        experience=experience,
        education=education,
        certifications=certifications,
    )
    return cv_obj.model_dump()


# _________________________________________________________________________________________________________
def _parse_email(text: str) -> Dict[str, Any]:
    """Extract headers and body preview from an email document."""
    subject_m = re.search(r"^subject:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    sender_m = re.search(r"^from:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    recipient_m = re.search(r"^to:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    date_m = re.search(r"^(?:date|sent):\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)

    email_obj = EmailData(
        subject=subject_m.group(1).strip() if subject_m else None,
        sender=sender_m.group(1).strip() if sender_m else None,
        recipient=recipient_m.group(1).strip() if recipient_m else None,
        date=date_m.group(1).strip() if date_m else None,
        body=text[:2000],
    )
    return email_obj.model_dump()


# _________________________________________________________________________________________________________
def extract_structured_data(text: str, doc_type: DocType, filename: str = "") -> Dict[str, Any]:
    """Route raw text to the appropriate structured parser based on doc_type."""
    if doc_type == "invoice":
        return _parse_invoice(text)
    if doc_type == "cv":
        return _parse_cv(text, filename=filename)
    if doc_type == "email":
        return _parse_email(text)
    return {"raw_preview": text[:500]}