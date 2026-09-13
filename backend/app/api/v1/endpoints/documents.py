import os
import shutil
import uuid
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.config import settings
from app.models.document import Document, DocumentChunk, DocumentStatus, ExtractionResult
from app.schemas.document import DocumentResponse, DocumentDetailResponse
from app.services.parser import parser_service
from app.services.chunking import chunker_service
from app.services.embeddings import embedding_service

router = APIRouter()

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
@router.post("/upload/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document (PDF, DOCX, TXT, Image), parse its layout and tables,
    generate semantic embeddings, and store in the database.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No valid file uploaded.")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_ext = os.path.splitext(file.filename)[1].lower()
    doc_id = str(uuid.uuid4())
    stored_filename = f"{doc_id}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, stored_filename)

    # Save file to disk
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = os.path.getsize(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Create document record
    doc = Document(
        id=doc_id,
        filename=stored_filename,
        original_name=file.filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type or "application/pdf",
        status=DocumentStatus.PROCESSING
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Parse and chunk document asynchronously without blocking event loop
    try:
        import asyncio
        parsed = await asyncio.to_thread(parser_service.parse_document, file_path, doc.mime_type)
        chunks = await asyncio.to_thread(chunker_service.chunk_document, parsed.markdown_content)
        
        # Generate embeddings in worker thread
        chunk_texts = [c.content for c in chunks]
        embeddings = await asyncio.to_thread(embedding_service.embed_texts, chunk_texts)

        # Create chunk records with vector embeddings
        for idx, (c, emb) in enumerate(zip(chunks, embeddings)):
            chunk_record = DocumentChunk(
                document_id=doc.id,
                chunk_index=idx,
                content=c.content,
                page_number=c.page_number,
                chunk_type=c.chunk_type,
                metadata_json=c.metadata,
                embedding=emb
            )
            db.add(chunk_record)

        doc.page_count = parsed.page_count
        doc.markdown_content = parsed.markdown_content
        doc.metadata_json = parsed.metadata
        doc.status = DocumentStatus.COMPLETED
        await db.commit()
        await db.refresh(doc)

    except Exception as e:
        print(f"[!] Error processing document: {e}")
        doc.status = DocumentStatus.FAILED
        doc.error_message = str(e)
        await db.commit()
        await db.refresh(doc)

    return doc

@router.get("", response_model=List[DocumentResponse])
@router.get("/", response_model=List[DocumentResponse], include_in_schema=False)
async def list_documents(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    query = select(Document).order_by(Document.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Document)
        .options(selectinload(Document.chunks), selectinload(Document.extractions))
        .where(Document.id == document_id)
    )
    result = await db.execute(query)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.get("/{document_id}/file")
async def view_document_file(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Serve original file inline for in-browser PDF/image rendering."""
    query = select(Document).where(Document.id == document_id)
    result = await db.execute(query)
    doc = result.scalar_one_or_none()
    if not doc or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    headers = {"Content-Disposition": f'inline; filename="{doc.original_name}"'}
    return FileResponse(doc.file_path, media_type=doc.mime_type, headers=headers)

@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    query = select(Document).where(Document.id == document_id)
    result = await db.execute(query)
    doc = result.scalar_one_or_none()
    if not doc or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    return FileResponse(doc.file_path, filename=doc.original_name, media_type=doc.mime_type)

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    query = select(Document).where(Document.id == document_id)
    result = await db.execute(query)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass

    await db.delete(doc)
    await db.commit()
    return None
