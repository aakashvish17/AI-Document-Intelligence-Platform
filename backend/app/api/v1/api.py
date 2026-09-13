from fastapi import APIRouter
from app.api.v1.endpoints import documents, chat, extract, detector

api_router = APIRouter()

api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(extract.router, prefix="/extract", tags=["extract"])
api_router.include_router(detector.router, prefix="/detector", tags=["detector"])
