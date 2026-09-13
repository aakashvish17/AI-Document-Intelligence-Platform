from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.document import ChatMessageRequest, ChatResponse
from app.services.rag import rag_service

router = APIRouter()

@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse, include_in_schema=False)
async def chat_with_documents(
    payload: ChatMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Perform semantic search on ingested documents/images,
    and generate a personalized grounded answer using Local Qwen 2.5.
    """
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    response = await rag_service.query_documents(
        db=db,
        query=payload.query,
        document_id=payload.document_id,
        top_k=payload.top_k,
        provider=payload.provider,
        model=payload.model
    )
    return response
