from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.document import Document, ExtractionResult
from app.schemas.document import ExtractionRequest, ExtractionResultResponse
from app.services.extractor import extractor_service

router = APIRouter()

@router.post("", response_model=ExtractionResultResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ExtractionResultResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def extract_document_data(
    payload: ExtractionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Extract structured JSON data (e.g. invoice line items, tax IDs, dates, clauses)
    from the target document or OCR image using Local Qwen 2.5 schema parser.
    """
    query = select(Document).where(Document.id == payload.document_id)
    result = await db.execute(query)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    content = doc.markdown_content or ""
    if not content.strip():
        raise HTTPException(status_code=400, detail="Document has no parsed content available for extraction")

    extracted = await extractor_service.extract_structured_data(
        markdown_content=content,
        schema_name=payload.schema_name,
        target_fields=payload.target_fields,
        custom_instructions=payload.custom_instructions,
        provider=payload.provider,
        model=payload.model
    )

    extraction_record = ExtractionResult(
        document_id=doc.id,
        schema_name=payload.schema_name,
        extracted_data=extracted.get("extracted_data", {}),
        confidence_score=extracted.get("status", "completed")
    )
    db.add(extraction_record)
    await db.commit()
    await db.refresh(extraction_record)

    return extraction_record

@router.get("/{document_id}", response_model=list[ExtractionResultResponse])
async def list_extractions_for_document(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    query = select(ExtractionResult).where(ExtractionResult.document_id == document_id).order_by(ExtractionResult.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()
