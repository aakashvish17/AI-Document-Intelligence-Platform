# 🚀 AI Document Intelligence Platform

A high-performance, enterprise-ready Document Intelligence and RAG platform powered by **Docling**, **pgvector (PostgreSQL)**, **Local Qwen 2.5 (GTX 1650)**, and **Next.js**.

---

## ⚡ 1-Step Quick Launch

Simply run:

```bash
python start.py
```

The script will automatically:
1. Check that local **Ollama (`qwen2.5:3b`)** is reachable.
2. Spin up **PostgreSQL (`pgvector`) & Redis** in Docker.
3. Verify backend and frontend dependencies (`npm install` if required).
4. Launch both **FastAPI** (`http://localhost:8000`) and **Next.js** (`http://localhost:3000`) in unified live-logging mode and open your browser!

---

## 🌟 Key Architecture & Stack

- **Frontend**: Next.js 14 (App Router) + Tailwind CSS + Lucide Icons
- **Backend API**: FastAPI (Python 3.11+) + SQLAlchemy (Async)
- **Document & Table Parsing**: Docling (IBM) + PyPDF / PaddleOCR
- **Vector Database**: PostgreSQL 16 + `pgvector` extension
- **Embeddings**: `fastembed` (BGE small / local CPU embeddings)
- **LLM Reasoning & Extraction**: Localhost Ollama (**`qwen2.5:3b`** on GPU) with optional Groq API fallback
- **Task Queue / Cache**: Redis

---

## 📋 Key Features

1. **Multi-Format Ingestion**: Upload PDFs, scanned documents, images, DOCX files.
2. **Docling Structural Parser**: Preserves table structures, section headers, and multi-page layouts.
3. **Hybrid pgvector Retrieval**: Cosine similarity search combined with metadata filters.
4. **Local Qwen RAG Q&A**: Fast local GPU answers with exact source citations (Document name + Page number).
5. **Schema-Driven JSON Extractor**: Extract structured data (Invoices, Receipts, Contracts, Tax forms) into JSON with one click.
