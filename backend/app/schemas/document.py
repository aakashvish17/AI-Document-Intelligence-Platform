from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class DocumentChunkResponse(BaseModel):
    id: str
    chunk_index: int
    content: str
    page_number: int
    chunk_type: str
    metadata_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class ExtractionResultResponse(BaseModel):
    id: str
    schema_name: str
    extracted_data: Dict[str, Any]
    confidence_score: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_name: str
    file_size: int
    mime_type: str
    page_count: int
    status: str
    error_message: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DocumentDetailResponse(DocumentResponse):
    markdown_content: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    chunks: List[DocumentChunkResponse] = []
    extractions: List[ExtractionResultResponse] = []

class ChatMessageRequest(BaseModel):
    document_id: Optional[str] = None # None means query across all documents
    query: str
    top_k: int = 5
    stream: bool = False
    provider: Optional[str] = "groq" # "groq" or "ollama"
    model: Optional[str] = None

class Citation(BaseModel):
    document_id: str
    document_name: str
    page_number: int
    chunk_content: str
    similarity: float

class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation] = []
    model_used: str

class ExtractionRequest(BaseModel):
    document_id: str
    schema_name: str = "custom" # "invoice", "receipt", "contract", "financial_statement", "resume", "purchase_order", "custom"
    target_fields: Optional[List[str]] = Field(
        default=None, 
        description="List of specific fields to extract, e.g. ['invoice_number', 'total_amount', 'date', 'line_items']"
    )
    custom_instructions: Optional[str] = None
    provider: Optional[str] = "groq"
    model: Optional[str] = None
