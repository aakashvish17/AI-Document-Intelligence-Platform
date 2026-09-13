import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.document import Document
from app.services.image_detector import image_detector_service

router = APIRouter()

@router.get("/document/{document_id}")
async def detect_document_ai(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Analyze an existing uploaded document or image to detect if it is AI-generated / synthetic."""
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Document physical file missing")
        
    analysis = image_detector_service.analyze_image(doc.file_path)
    analysis["document_id"] = doc.id
    analysis["filename"] = doc.original_name
    return analysis

@router.post("/detect")
async def detect_uploaded_image(
    file: UploadFile = File(...)
):
    """Directly upload and test any image or document for AI-generated / synthetic detection."""
    import tempfile
    
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"detect_{file.filename}")
    
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    try:
        analysis = image_detector_service.analyze_image(temp_path)
        analysis["filename"] = file.filename
        return analysis
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
