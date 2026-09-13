# 🚀 AI Document Intelligence Platform

A high-performance, enterprise-grade Document Intelligence, Multimodal Extraction, and RAG platform powered by **Docling**, **pgvector (PostgreSQL)**, **Local Qwen 2.5**, **Open-Source AI Image/Deepfake Detection**, and **Next.js**.

---

## ⚡ Quick Start (Clone & Run)

### 1. Clone the repository
```bash
git clone https://github.com/aakashvish17/AI-Document-Intelligence-Platform.git
cd AI-Document-Intelligence-Platform
```

### 2. Configure Environment (`.env`)
Copy the example environment file:
```bash
cp .env.example .env
```

You can choose either:
- **Option A: 100% Local & Free (Default)**:
  - Install [Ollama](https://ollama.com/) and run:
    ```bash
    ollama run qwen2.5:3b
    ```
  - No external API keys required! Auto-falls back to built-in SQLite & local CPU embeddings (`fastembed`).

- **Option B: Cloud LLM via Groq**:
  - Add your free [Groq API Key](https://console.groq.com/) to `.env`:
    ```env
    GROQ_API_KEY=gsk_your_groq_api_key_here
    ```

### 3. Run with 1 Command
```bash
python start.py
```

The startup script will automatically:
1. Detect Python virtual environment & install backend dependencies.
2. Install frontend dependencies (`npm install`).
3. Check Ollama / Groq and Database (Docker PostgreSQL or local SQLite).
4. Launch FastAPI (`http://localhost:8000`) and Next.js UI (`http://localhost:3000`) and open your browser!

---

## 🌟 Key Architecture & Stack

- **Frontend**: Next.js 14 (App Router) + Tailwind CSS + Lucide Icons + Glassmorphism UI
- **Backend API**: FastAPI (Python 3.11+) + SQLAlchemy (Async) + Pydantic v2
- **Document & Table Parsing**: Docling (IBM) + PyPDF + Markdown Structure Engine
- **Vector Database**: PostgreSQL 16 + `pgvector` (with automatic SQLite fallback)
- **Embeddings**: `fastembed` (BGE small / local CPU embeddings)
- **LLM Reasoning & Extraction**: Localhost Ollama (**`qwen2.5:3b`**) with seamless Groq API fallback
- **AI Image & Deepfake Detector**: HuggingFace Vision Transformer (Google ViT) + Deep EXIF/PNG Forensic Analysis

---

## 📋 Key Features

1. **Multi-Format Ingestion**: Upload PDFs, scanned documents, images, DOCX files.
2. **Docling Structural Parser**: Preserves table structures, section headers, and multi-page layouts into clean Markdown.
3. **Hybrid Vector Retrieval**: Cosine similarity search with page-level citations.
4. **Local / Cloud RAG Q&A**: Real-time streaming and answers with exact document & page references.
5. **Schema-Driven JSON Extractor**: Extract structured data (Invoices, Receipts, W2/1099, Contracts) into JSON with one click.
6. **Open-Source AI Image/Deepfake Detector**: Instantly analyze uploaded images to detect AI generation (Midjourney, Stable Diffusion, DALL-E, Flux) with forensic breakdown.
