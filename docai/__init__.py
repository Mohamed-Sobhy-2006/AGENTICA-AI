# DocAI Package Initialization - Exports public interfaces
from docai.pipeline import DocAIError, process_batch, process_document
from docai.schemas import CVData, DocumentResult, EmailData, InvoiceData

__all__ = [
    "CVData",
    "DocAIError",
    "DocumentResult",
    "EmailData",
    "InvoiceData",
    "process_batch",
    "process_document",
]
