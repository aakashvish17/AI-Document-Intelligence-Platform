import os
import re
import base64
import numpy as np
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.document import Document, DocumentChunk
from app.schemas.document import Citation, ChatResponse
from app.services.embeddings import embedding_service
from app.services.llm import llm_service

def keyword_score(query: str, text: str) -> float:
    """Compute lexical keyword relevance score."""
    q_words = set(re.findall(r'\w+', query.lower()))
    if not q_words:
        return 0.0
    t_words = set(re.findall(r'\w+', text.lower()))
    intersection = q_words.intersection(t_words)
    return len(intersection) / len(q_words)

def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))

class RAGService:
    async def query_documents(
        self,
        db: AsyncSession,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 6,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> ChatResponse:
        # 1. Fetch targeted document if specified
        target_doc: Optional[Document] = None
        if document_id:
            doc_res = await db.execute(select(Document).where(Document.id == document_id))
            target_doc = doc_res.scalar_one_or_none()

        # 2. Retrieve chunks for search
        stmt = select(DocumentChunk, Document.original_name).join(
            Document, Document.id == DocumentChunk.document_id
        )
        if document_id:
            stmt = stmt.where(DocumentChunk.document_id == document_id)

        result = await db.execute(stmt)
        rows = result.all()

        query_vector = embedding_service.embed_query(query)

        # Hybrid Scoring: Vector Similarity (70%) + Keyword Lexical Match (30%)
        scored_chunks = []
        for chunk, doc_name in rows:
            vec_sim = cosine_similarity(query_vector, chunk.embedding) if chunk.embedding else 0.0
            kw_sim = keyword_score(query, chunk.content)
            hybrid_score = (vec_sim * 0.6) + (kw_sim * 0.4)
            scored_chunks.append((chunk, doc_name, hybrid_score, vec_sim, kw_sim))

        scored_chunks.sort(key=lambda x: x[2], reverse=True)
        top_chunks = scored_chunks[:top_k]

        citations: List[Citation] = []
        context_blocks: List[str] = []

        for chunk, doc_name, score, vec_s, kw_s in top_chunks:
            citations.append(Citation(
                document_id=chunk.document_id,
                document_name=doc_name,
                page_number=chunk.page_number,
                chunk_content=chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                similarity=float(round(score, 3))
            ))
            context_blocks.append(f"[Document: {doc_name} | Page {chunk.page_number}]\n{chunk.content}")

        # 3. Formulate Rich Grounded Prompt
        if target_doc and target_doc.markdown_content and len(target_doc.markdown_content) < 8000:
            # For documents that fit directly in context, provide full markdown for 100% precision
            context_content = f"--- COMPLETE EXTRACTED DOCUMENT: {target_doc.original_name} ---\n{target_doc.markdown_content}"
        else:
            context_content = "\n\n---\n\n".join(context_blocks) if context_blocks else "No matching chunks found in database."

        doc_name_hint = f" for '{target_doc.original_name}'" if target_doc else ""

        system_prompt = (
            "You are an expert AI Document Intelligence analyst. "
            "Your task is to provide accurate, well-structured, and helpful answers based STRICTLY on the document context provided. "
            "Formatting guidelines:\n"
            "- Use clean Markdown formatting with clear bullet points, bold key terms, and markdown tables where suitable.\n"
            "- Do NOT include conversational filler or prefix meta-labels like '**Answer:**' or '*Answer**' at the beginning.\n"
            "- When presenting comparisons or data tables, use standard markdown table syntax.\n"
            "- Always cite facts and page numbers accurately."
        )

        user_prompt = f"""Context from ingested document(s){doc_name_hint}:
{context_content}

User Question:
{query}

Direct Answer:"""

        llm_result = await llm_service.generate_response(
            system_prompt,
            user_prompt,
            temperature=0.1,
            provider=provider,
            model=model
        )

        return ChatResponse(
            answer=llm_result["text"],
            citations=citations,
            model_used=llm_result["model"]
        )

rag_service = RAGService()
