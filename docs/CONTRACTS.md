# AGENTICA - System Data Contracts & Schemas (T1)

This document defines the strict data contracts and Pydantic schemas shared across all components (P1 through P7) in the AGENTICA platform. All modules must adhere to these interfaces.

---

## 1. Core Document Structure (`DocumentResult`)
Used by DocAI (P4) and passed to P1 Supervisor and RAG (P3).

```json
{
  "document_id": "uuid-str",
  "filename": "invoice_001.pdf",
  "doc_type": "invoice | cv | email | generic",
  "extracted_text": "Full raw OCR text...",
  "structured_data": {
    "vendor_name": "Company X",
    "total_amount": 1500.00,
    "currency": "USD",
    "date": "2026-11-18"
  },
  "confidence_score": 0.98,
  "processed_at": "2026-11-18T08:00:00Z"
}


2. Agent Execution Payload (AgentRequest & AgentResponse)
Used by P1 Supervisor (LangGraph) to orchestrate tasks across sub-agents.

Request
{
  "task_id": "uuid-str",
  "session_id": "session-uuid",
  "user_query": "Analyze this invoice and check company policy.",
  "target_agent": "supervisor | docai_agent | rag_agent | validation_agent",
  "payload": {
    "document_id": "uuid-str"
  }
}

Response
{
  "task_id": "uuid-str",
  "status": "success | failed | requires_review",
  "agent_name": "supervisor",
  "result": {
    "summary": "Invoice verified successfully against policy guidelines.",
    "actions_taken": ["OCR Extracted", "RAG Policy Checked", "Approved"]
  },
  "error": null,
  "execution_time_ms": 420
}

3. RAG Retrieval Schema (RetrievalQuery & ChunkResult)
Used by P3 RAG & Vector Database (Qdrant).

Query
{
  "query_text": "What is the travel expense reimbursement limit?",
  "top_k": 5,
  "filters": {
    "department": "finance"
  }
}

Chunk Result
{
  "chunk_id": "chunk-uuid",
  "source_document": "Company_Policy_2026.pdf",
  "page_number": 14,
  "content": "Reimbursement for travel expenses shall not exceed...",
  "score": 0.89
}


4. Standard Error Schema (ErrorResponse)
Unified error handling format across FastAPI Backend (P5) and Agents.
{
  "error_code": "ERR_DOC_PARSING_FAILED",
  "message": "Failed to parse PDF file using PaddleOCR.",
  "details": "Corrupted file header at byte 0.",
  "timestamp": "2026-11-18T08:00:00Z"
}