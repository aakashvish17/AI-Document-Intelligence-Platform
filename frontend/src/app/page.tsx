"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  FileText,
  UploadCloud,
  MessageSquare,
  Database,
  Sparkles,
  Layers,
  Search,
  CheckCircle2,
  AlertCircle,
  Clock,
  Trash2,
  Eye,
  Code2,
  Copy,
  Check,
  Send,
  RefreshCw,
  ExternalLink,
  BookOpen,
  Image as ImageIcon,
  FileSpreadsheet,
  ShieldCheck,
  ShieldAlert,
  Fingerprint,
  Activity,
  Menu,
  X,
  ChevronRight,
  Maximize2,
  Download
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, DocumentItem, DocumentDetail, Citation, ExtractionResponse, AIDetectionResponse } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function DocumentIntelligenceDashboard() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<DocumentDetail | null>(null);
  const [loadingDocs, setLoadingDocs] = useState<boolean>(true);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  // Center Pane Preview Mode: "visual" | "markdown" | "detector"
  const [previewMode, setPreviewMode] = useState<"visual" | "markdown" | "detector">("visual");
  const [markdownViewType, setMarkdownViewType] = useState<"rendered" | "raw">("rendered");
  const [copiedMarkdown, setCopiedMarkdown] = useState(false);

  // Right Workspace Tab: "chat" | "extract" | "detector" | "chunks"
  const [activeTab, setActiveTab] = useState<"chat" | "extract" | "detector" | "chunks">("chat");

  // Chat State
  const [messages, setMessages] = useState<Array<{
    role: "user" | "assistant";
    content: string;
    citations?: Citation[];
    model?: string;
  }>>([
    {
      role: "assistant",
      content: "Hello! Upload any PDF, Word document, Excel spreadsheet, or Image (PNG/JPG). I will perform OCR layout analysis, extract structured tables, test for AI-generated authenticity, and answer your questions via Local Qwen 2.5.",
    },
  ]);
  const [queryInput, setQueryInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Extraction State
  const [extractionSchema, setExtractionSchema] = useState("invoice");
  const [customFields, setCustomFields] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [latestExtraction, setLatestExtraction] = useState<ExtractionResponse | null>(null);
  const [copiedJson, setCopiedJson] = useState(false);

  // LLM Provider State: "groq" | "ollama"
  const [llmProvider, setLlmProvider] = useState<"groq" | "ollama">("groq");
  const [llmModel, setLlmModel] = useState<string>("openai/gpt-oss-20b");

  // AI Image Detector State
  const [aiDetection, setAiDetection] = useState<AIDetectionResponse | null>(null);
  const [detectingAI, setDetectingAI] = useState(false);
  const [detectionError, setDetectionError] = useState<string | null>(null);

  // Load documents on mount
  useEffect(() => {
    loadDocuments();
  }, []);

  useEffect(() => {
    if (selectedDocId) {
      loadDocumentDetails(selectedDocId);
    } else {
      setSelectedDoc(null);
      setAiDetection(null);
    }
  }, [selectedDocId]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadDocuments = async () => {
    try {
      setLoadingDocs(true);
      const data = await api.listDocuments();
      setDocuments(data);
      if (data.length > 0 && !selectedDocId) {
        setSelectedDocId(data[0].id);
      }
    } catch (err) {
      console.error("Failed to load documents:", err);
    } finally {
      setLoadingDocs(false);
    }
  };

  const loadDocumentDetails = async (id: string) => {
    try {
      const doc = await api.getDocument(id);
      setSelectedDoc(doc);
      setAiDetection(null);
      setDetectionError(null);
      
      const isImg = doc.mime_type && doc.mime_type.includes("image");
      const isPdf = doc.mime_type && doc.mime_type.includes("pdf");
      if (isPdf || isImg) {
        setPreviewMode("visual");
      } else {
        setPreviewMode("markdown");
      }

      // Fetch existing extractions
      try {
        const extractions = await api.getExtractions(id);
        if (extractions.length > 0) {
          setLatestExtraction(extractions[0]);
        } else {
          setLatestExtraction(null);
        }
      } catch {
        setLatestExtraction(null);
      }
    } catch (err) {
      console.error("Failed to load document detail:", err);
    }
  };

  const runAIDetection = async () => {
    if (!selectedDocId) return;
    try {
      setDetectingAI(true);
      setDetectionError(null);
      const result = await api.detectAIDocument(selectedDocId);
      setAiDetection(result);
    } catch (err: any) {
      setDetectionError(err.message || "Failed to analyze image authenticity");
    } finally {
      setDetectingAI(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const file = files[0];

    try {
      setUploading(true);
      setUploadError(null);
      const uploaded = await api.uploadDocument(file);
      await loadDocuments();
      setSelectedDocId(uploaded.id);
      
      const isImage = file.type.startsWith("image/");
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `${isImage ? "Image" : "Document"} **${file.name}** processed and indexed! OCR extracted layout & tables. You can now chat, extract JSON fields, or scan for AI generation.`,
        },
      ]);
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload file");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this document?")) return;
    try {
      await api.deleteDocument(id);
      const updated = documents.filter((d) => d.id !== id);
      setDocuments(updated);
      if (selectedDocId === id) {
        setSelectedDocId(updated.length > 0 ? updated[0].id : null);
      }
    } catch (err) {
      console.error("Failed to delete document:", err);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryInput.trim() || chatLoading) return;

    const userText = queryInput.trim();
    setQueryInput("");
    setMessages((prev) => [...prev, { role: "user", content: userText }]);
    setChatLoading(true);

    try {
      const response = await api.chat(userText, selectedDocId || undefined, llmProvider, llmModel);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.answer,
          citations: response.citations,
          model: response.model_used,
        },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `⚠️ Error: ${err.message || "Failed to get response"}`,
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleExtract = async () => {
    if (!selectedDocId || extracting) return;
    try {
      setExtracting(true);
      let fields: string[] | undefined = undefined;
      if (extractionSchema === "custom" && customFields.trim()) {
        fields = customFields.split(",").map((s) => s.trim()).filter(Boolean);
      }
      const res = await api.extractData(selectedDocId, extractionSchema, fields, llmProvider, llmModel);
      setLatestExtraction(res);
      setActiveTab("extract");
    } catch (err: any) {
      alert(`Extraction failed: ${err.message}`);
    } finally {
      setExtracting(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  };

  const filteredDocs = documents.filter((doc) =>
    doc.original_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  const isImageFile = (mime?: string, name?: string) => {
    if (mime && mime.includes("image")) return true;
    if (name) {
      const ext = name.split(".").pop()?.toLowerCase();
      return ["png", "jpg", "jpeg", "webp", "tiff", "bmp"].includes(ext || "");
    }
    return false;
  };

  const isPdfFile = (mime?: string, name?: string) => {
    if (mime && mime.includes("pdf")) return true;
    if (name) return name.toLowerCase().endsWith(".pdf");
    return false;
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#090d16] text-[#e2e8f0] font-sans">
      {/* Mobile Sidebar Overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/70 z-40 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* =========================================================================
          LEFT SIDEBAR: Documents Library & Ingestion
          ========================================================================= */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-80 bg-[#0f172a] border-r border-[#1e293b] flex flex-col transition-transform duration-200 ease-in-out ${
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        {/* Header */}
        <div className="p-4 border-b border-[#1e293b] flex items-center justify-between bg-[#111c33]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded bg-[#2563eb] flex items-center justify-center text-white font-bold shadow-sm">
              AI
            </div>
            <div>
              <h1 className="font-semibold text-sm text-white tracking-wide">DOC INTELLIGENCE</h1>
              <p className="text-[11px] text-[#94a3b8]">Ollama Qwen 2.5 + Docling</p>
            </div>
          </div>
          <button
            onClick={() => setMobileMenuOpen(false)}
            className="lg:hidden p-1 text-[#94a3b8] hover:text-white rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Upload Action Box */}
        <div className="p-3.5 border-b border-[#1e293b] bg-[#0c1322]">
          <label className="relative flex flex-col items-center justify-center p-3.5 border border-dashed border-[#334155] hover:border-[#3b82f6] rounded bg-[#131d31] hover:bg-[#17233c] cursor-pointer transition-colors group">
            <input
              type="file"
              onChange={handleFileUpload}
              disabled={uploading}
              className="hidden"
              accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.tsv,.pptx,.txt,.md,.png,.jpg,.jpeg,.tiff,.bmp,.webp"
            />
            <div className="flex items-center gap-2 text-[#38bdf8]">
              {uploading ? (
                <RefreshCw className="w-5 h-5 animate-spin text-[#38bdf8]" />
              ) : (
                <UploadCloud className="w-5 h-5 group-hover:scale-110 transition-transform" />
              )}
              <span className="text-xs font-semibold text-white">
                {uploading ? "Ingesting & Parsing..." : "Upload Document / Image"}
              </span>
            </div>
            <p className="text-[10px] text-[#94a3b8] mt-1 text-center">
              PDF, DOCX, XLSX, PPTX, Images (OCR)
            </p>
          </label>
          {uploadError && (
            <div className="mt-2 p-2 bg-[#450a0a] border border-[#ef4444] rounded text-[11px] text-[#fca5a5]">
              {uploadError}
            </div>
          )}
        </div>

        {/* Search Documents */}
        <div className="p-3 border-b border-[#1e293b]">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[#64748b]" />
            <input
              type="text"
              placeholder="Filter library..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#131d31] border border-[#1e293b] rounded pl-8 pr-3 py-1.5 text-xs text-white placeholder-[#64748b] focus:outline-none focus:border-[#2563eb]"
            />
          </div>
        </div>

        {/* Documents List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {loadingDocs ? (
            <div className="p-4 text-center text-xs text-[#64748b]">Loading documents...</div>
          ) : filteredDocs.length === 0 ? (
            <div className="p-6 text-center text-xs text-[#64748b]">
              No documents found. Upload a file above to begin.
            </div>
          ) : (
            filteredDocs.map((doc) => {
              const isSelected = doc.id === selectedDocId;
              const isImg = isImageFile(doc.mime_type, doc.original_name);
              const isSheet = doc.original_name.match(/\.(xlsx|xls|csv)$/i);

              return (
                <div
                  key={doc.id}
                  onClick={() => {
                    setSelectedDocId(doc.id);
                    setMobileMenuOpen(false);
                  }}
                  className={`group relative flex items-start justify-between p-2.5 rounded cursor-pointer border transition-colors ${
                    isSelected
                      ? "bg-[#1e293b] border-[#2563eb] text-white"
                      : "bg-[#0f172a] hover:bg-[#131d31] border-[#1e293b] text-[#cbd5e1]"
                  }`}
                >
                  <div className="flex items-start gap-2.5 overflow-hidden">
                    <div className={`p-1.5 rounded mt-0.5 ${
                      isImg ? "bg-[#14532d] text-[#4ade80]" : isSheet ? "bg-[#164e63] text-[#38bdf8]" : "bg-[#1e3a8a] text-[#60a5fa]"
                    }`}>
                      {isImg ? (
                        <ImageIcon className="w-3.5 h-3.5" />
                      ) : isSheet ? (
                        <FileSpreadsheet className="w-3.5 h-3.5" />
                      ) : (
                        <FileText className="w-3.5 h-3.5" />
                      )}
                    </div>
                    <div className="overflow-hidden">
                      <p className="text-xs font-medium truncate" title={doc.original_name}>
                        {doc.original_name}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5 text-[10px] text-[#94a3b8]">
                        <span>{formatFileSize(doc.file_size)}</span>
                        <span>•</span>
                        <span>{doc.page_count || 1} {isImg ? "img" : "pg"}</span>
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDelete(doc.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 text-[#94a3b8] hover:text-[#ef4444] rounded transition-opacity"
                    title="Delete document"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* System Footer Status */}
        <div className="p-3 border-t border-[#1e293b] bg-[#0c1322] flex items-center justify-between text-[11px] text-[#94a3b8]">
          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${llmProvider === "groq" ? "bg-[#f97316]" : "bg-[#10b981]"}`} />
            <span className="truncate">
              {llmProvider === "groq" ? "Groq (GPT-OSS 20B)" : "Local Qwen (3B)"}
            </span>
          </div>
          <span className="text-[10px] px-1.5 py-0.5 bg-[#1e293b] rounded text-[#94a3b8] font-mono">
            {llmProvider === "groq" ? "⚡ Cloud" : "RTX 1650"}
          </span>
        </div>
      </aside>

      {/* =========================================================================
          MAIN WORKSPACE (CENTER PREVIEW + RIGHT INTERACTIVE PANE)
          ========================================================================= */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Navbar */}
        <header className="h-13 bg-[#0f172a] border-b border-[#1e293b] flex items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="lg:hidden p-1.5 text-[#94a3b8] hover:text-white bg-[#1e293b] rounded"
            >
              <Menu className="w-4 h-4" />
            </button>
            {selectedDoc ? (
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-white truncate max-w-xs md:max-w-md">
                  {selectedDoc.original_name}
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-[#1e293b] text-[#38bdf8] font-mono">
                  {selectedDoc.metadata_json?.parser || "Docling"}
                </span>
              </div>
            ) : (
              <span className="text-xs text-[#94a3b8]">Select a document to begin</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Quick Action: Open AI Detector */}
            {selectedDoc && (
              <button
                onClick={() => {
                  setPreviewMode("detector");
                  setActiveTab("detector");
                  if (!aiDetection) runAIDetection();
                }}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium bg-[#1e293b] hover:bg-[#2563eb] text-[#38bdf8] hover:text-white rounded border border-[#334155] transition-colors"
              >
                <Fingerprint className="w-3.5 h-3.5" />
                <span>AI Authenticity Scan</span>
              </button>
            )}
            <a
              href="https://huggingface.co/umm-maybe/AI-image-detector"
              target="_blank"
              rel="noreferrer"
              className="text-[11px] text-[#94a3b8] hover:text-white flex items-center gap-1 bg-[#131d31] px-2.5 py-1 rounded border border-[#1e293b]"
            >
              <span>ViT AI Image Detector</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </header>

        {/* Dynamic Dual-Pane Workspace */}
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
          
          {/* =========================================================================
              CENTER PANE: Document Preview / Extracted Markdown / AI Detector
              ========================================================================= */}
          <div className="flex-1 lg:w-3/5 border-r border-[#1e293b] flex flex-col bg-[#090d16] overflow-hidden">
            {/* Center Tabs */}
            <div className="h-10 bg-[#0f172a] border-b border-[#1e293b] flex items-center justify-between px-3">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPreviewMode("visual")}
                  className={`px-3 py-1 text-xs font-medium rounded ${
                    previewMode === "visual"
                      ? "bg-[#2563eb] text-white"
                      : "text-[#94a3b8] hover:text-white hover:bg-[#1e293b]"
                  }`}
                >
                  <span className="flex items-center gap-1.5">
                    <Eye className="w-3.5 h-3.5" />
                    Visual Preview
                  </span>
                </button>
                <button
                  onClick={() => setPreviewMode("markdown")}
                  className={`px-3 py-1 text-xs font-medium rounded ${
                    previewMode === "markdown"
                      ? "bg-[#2563eb] text-white"
                      : "text-[#94a3b8] hover:text-white hover:bg-[#1e293b]"
                  }`}
                >
                  <span className="flex items-center gap-1.5">
                    <Code2 className="w-3.5 h-3.5" />
                    Extracted Structure (OCR)
                  </span>
                </button>
                <button
                  onClick={() => {
                    setPreviewMode("detector");
                    setActiveTab("detector");
                    if (!aiDetection) runAIDetection();
                  }}
                  className={`px-3 py-1 text-xs font-medium rounded ${
                    previewMode === "detector"
                      ? "bg-[#2563eb] text-white"
                      : "text-[#94a3b8] hover:text-white hover:bg-[#1e293b]"
                  }`}
                >
                  <span className="flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    AI Detector & Forensics
                  </span>
                </button>
              </div>

              {selectedDoc && (
                <a
                  href={`${API_BASE}/documents/${selectedDoc.id}/file`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[11px] text-[#94a3b8] hover:text-white flex items-center gap-1"
                >
                  <span>Raw File</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>

            {/* Center Content Body */}
            <div className="flex-1 overflow-y-auto p-4 bg-[#090d16]">
              {!selectedDoc ? (
                <div className="h-full flex flex-col items-center justify-center text-center text-[#64748b] space-y-2">
                  <FileText className="w-12 h-12 text-[#334155]" />
                  <p className="text-sm font-medium">No document selected</p>
                  <p className="text-xs">Upload or pick a document from the library to inspect.</p>
                </div>
              ) : previewMode === "visual" ? (
                <div className="w-full h-full flex flex-col items-center justify-center bg-[#0d1322] border border-[#1e293b] rounded p-2 overflow-hidden">
                  {isPdfFile(selectedDoc.mime_type, selectedDoc.original_name) ? (
                    <iframe
                      src={`${API_BASE}/documents/${selectedDoc.id}/file`}
                      className="w-full h-full rounded border-0"
                      title="PDF Visual Preview"
                    />
                  ) : isImageFile(selectedDoc.mime_type, selectedDoc.original_name) ? (
                    <div className="w-full h-full flex items-center justify-center overflow-auto p-2">
                      <img
                        src={`${API_BASE}/documents/${selectedDoc.id}/file`}
                        alt={selectedDoc.original_name}
                        className="max-h-full max-w-full object-contain rounded border border-[#1e293b] shadow-md"
                      />
                    </div>
                  ) : (
                    <div className="text-center p-8 text-[#94a3b8] space-y-3">
                      <FileSpreadsheet className="w-10 h-10 mx-auto text-[#38bdf8]" />
                      <p className="text-xs font-semibold text-white">{selectedDoc.original_name}</p>
                      <p className="text-xs text-[#94a3b8]">
                        Structured text and tables extracted for this document format. Switch to the <strong>Extracted Structure</strong> tab to inspect.
                      </p>
                      <button
                        onClick={() => setPreviewMode("markdown")}
                        className="px-3 py-1.5 bg-[#2563eb] text-white text-xs rounded hover:bg-[#1d4ed8]"
                      >
                        View Structured OCR
                      </button>
                    </div>
                  )}
                </div>
              ) : previewMode === "markdown" ? (
                <div className="flex flex-col h-full bg-[#0d1322] border border-[#1e293b] rounded overflow-hidden">
                  {/* Markdown Sub-toolbar */}
                  <div className="h-9 bg-[#0f172a] border-b border-[#1e293b] px-3 flex items-center justify-between">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setMarkdownViewType("rendered")}
                        className={`px-2.5 py-1 text-[11px] font-medium rounded ${
                          markdownViewType === "rendered"
                            ? "bg-[#1e293b] text-[#38bdf8] border border-[#334155]"
                            : "text-[#94a3b8] hover:text-white hover:bg-[#131d31]"
                        }`}
                      >
                        Formatted Document & Tables
                      </button>
                      <button
                        onClick={() => setMarkdownViewType("raw")}
                        className={`px-2.5 py-1 text-[11px] font-medium rounded ${
                          markdownViewType === "raw"
                            ? "bg-[#1e293b] text-[#38bdf8] border border-[#334155]"
                            : "text-[#94a3b8] hover:text-white hover:bg-[#131d31]"
                        }`}
                      >
                        Raw Markdown (.md)
                      </button>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          if (!selectedDoc?.markdown_content) return;
                          navigator.clipboard.writeText(selectedDoc.markdown_content);
                          setCopiedMarkdown(true);
                          setTimeout(() => setCopiedMarkdown(false), 2000);
                        }}
                        className="flex items-center gap-1 px-2 py-0.5 text-[11px] bg-[#1e293b] hover:bg-[#2563eb] text-[#cbd5e1] hover:text-white rounded border border-[#334155] transition-colors"
                        title="Copy Markdown text"
                      >
                        {copiedMarkdown ? <Check className="w-3 h-3 text-[#4ade80]" /> : <Copy className="w-3 h-3" />}
                        <span>{copiedMarkdown ? "Copied!" : "Copy MD"}</span>
                      </button>
                      <button
                        onClick={() => {
                          if (!selectedDoc?.markdown_content) return;
                          const blob = new Blob([selectedDoc.markdown_content], { type: "text/markdown;charset=utf-8" });
                          const url = URL.createObjectURL(blob);
                          const link = document.createElement("a");
                          link.href = url;
                          link.download = `${selectedDoc.original_name.replace(/\.[^/.]+$/, "")}_extracted.md`;
                          link.click();
                          URL.revokeObjectURL(url);
                        }}
                        className="flex items-center gap-1 px-2 py-0.5 text-[11px] bg-[#1e293b] hover:bg-[#2563eb] text-[#cbd5e1] hover:text-white rounded border border-[#334155] transition-colors"
                        title="Download extracted Markdown file"
                      >
                        <Download className="w-3 h-3" />
                        <span>Download .md</span>
                      </button>
                    </div>
                  </div>

                  {/* Markdown Content Area */}
                  <div className="flex-1 overflow-y-auto p-5 select-text">
                    {markdownViewType === "rendered" ? (
                      <div className="max-w-4xl mx-auto space-y-3 leading-relaxed text-[#cbd5e1]">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            table: ({ node, ...props }) => (
                              <div className="overflow-x-auto my-4 border border-[#334155] rounded-md shadow-sm bg-[#090d16]">
                                <table className="w-full border-collapse text-xs text-left" {...props} />
                              </div>
                            ),
                            thead: ({ node, ...props }) => (
                              <thead className="bg-[#1e293b] text-white border-b border-[#334155]" {...props} />
                            ),
                            th: ({ node, ...props }) => (
                              <th className="px-3.5 py-2.5 font-semibold text-white border-r border-[#334155] last:border-r-0 whitespace-nowrap" {...props} />
                            ),
                            td: ({ node, ...props }) => (
                              <td className="px-3.5 py-2 border-t border-[#1e293b] border-r border-[#1e293b] last:border-r-0 text-[#cbd5e1] hover:bg-[#131d31] transition-colors" {...props} />
                            ),
                            h1: ({ node, ...props }) => (
                              <h1 className="text-base font-bold text-white mt-6 mb-2 pb-1 border-b border-[#1e293b]" {...props} />
                            ),
                            h2: ({ node, ...props }) => (
                              <h2 className="text-sm font-bold text-[#38bdf8] mt-5 mb-2" {...props} />
                            ),
                            h3: ({ node, ...props }) => (
                              <h3 className="text-xs font-bold text-[#93c5fd] mt-4 mb-1" {...props} />
                            ),
                            p: ({ node, ...props }) => (
                              <p className="text-xs text-[#cbd5e1] my-2 leading-relaxed" {...props} />
                            ),
                            ul: ({ node, ...props }) => (
                              <ul className="list-disc list-inside text-xs text-[#cbd5e1] my-2 space-y-1 pl-2" {...props} />
                            ),
                            ol: ({ node, ...props }) => (
                              <ol className="list-decimal list-inside text-xs text-[#cbd5e1] my-2 space-y-1 pl-2" {...props} />
                            ),
                            blockquote: ({ node, ...props }) => (
                              <blockquote className="border-l-3 border-[#2563eb] pl-3 py-1.5 text-xs text-[#94a3b8] italic my-3 bg-[#131d31]/60 rounded-r" {...props} />
                            ),
                            strong: ({ node, ...props }) => (
                              <strong className="font-semibold text-white" {...props} />
                            ),
                            hr: ({ node, ...props }) => (
                              <hr className="border-[#1e293b] my-4" {...props} />
                            )
                          }}
                        >
                          {selectedDoc.markdown_content || "*(No extracted text found.)*"}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <pre className="p-4 bg-[#090d16] border border-[#1e293b] rounded text-xs font-mono text-[#cbd5e1] whitespace-pre-wrap leading-relaxed overflow-x-auto">
                        {selectedDoc.markdown_content || "No extracted text found."}
                      </pre>
                    )}
                  </div>
                </div>
              ) : (
                /* AI Image Detector & Forensics View */
                <div className="space-y-4">
                  <div className="bg-[#111827] border border-[#1e293b] rounded p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Fingerprint className="w-5 h-5 text-[#38bdf8]" />
                        <div>
                          <h3 className="text-sm font-semibold text-white">AI-Generated vs Authentic Image Detector</h3>
                          <p className="text-[11px] text-[#94a3b8]">Google ViT-Base (umm-maybe/AI-image-detector, 3.5M+ Downloads)</p>
                        </div>
                      </div>
                      <button
                        onClick={runAIDetection}
                        disabled={detectingAI}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-xs font-medium rounded transition-colors"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${detectingAI ? "animate-spin" : ""}`} />
                        <span>{detectingAI ? "Analyzing..." : "Re-Scan"}</span>
                      </button>
                    </div>

                    {detectionError && (
                      <div className="p-3 bg-[#450a0a] border border-[#ef4444] rounded text-xs text-[#fca5a5]">
                        {detectionError}
                      </div>
                    )}

                    {detectingAI ? (
                      <div className="py-12 text-center text-xs text-[#94a3b8] space-y-2">
                        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-[#38bdf8]" />
                        <p>Computing 2D Fast Fourier Transform & Laplacian sensor noise distribution...</p>
                      </div>
                    ) : aiDetection ? (
                      <div className="space-y-4 mt-4">
                        {/* Primary Verdict Card */}
                        <div className={`p-4 rounded border flex items-center justify-between ${
                          aiDetection.is_ai_generated
                            ? "bg-[#450a0a] border-[#ef4444] text-[#fca5a5]"
                            : "bg-[#064e3b] border-[#10b981] text-[#6ee7b7]"
                        }`}>
                          <div className="flex items-center gap-3">
                            {aiDetection.is_ai_generated ? (
                              <ShieldAlert className="w-8 h-8 text-[#ef4444]" />
                            ) : (
                              <ShieldCheck className="w-8 h-8 text-[#10b981]" />
                            )}
                            <div>
                              <p className="text-xs uppercase tracking-wider font-bold">Detection Verdict</p>
                              <h2 className="text-base font-bold text-white">{aiDetection.verdict}</h2>
                              <p className="text-[11px] opacity-90">
                                Confidence: <strong>{aiDetection.confidence_pct}%</strong>
                              </p>
                            </div>
                          </div>
                          <div className="text-right font-mono text-xs">
                            <span className="px-2.5 py-1 rounded bg-black/40 border border-white/10 text-white font-bold">
                              {aiDetection.is_ai_generated ? "SYNTHETIC / AI" : "AUTHENTIC"}
                            </span>
                          </div>
                        </div>

                        {/* Probability Score Bars */}
                        <div className="grid grid-cols-2 gap-3">
                          <div className="p-3 bg-[#1e293b] border border-[#334155] rounded">
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-[#94a3b8]">AI Synthetic Score</span>
                              <span className="text-[#ef4444] font-bold font-mono">
                                {(aiDetection.ai_score * 100).toFixed(1)}%
                              </span>
                            </div>
                            <div className="w-full bg-[#0f172a] h-2 rounded-full overflow-hidden">
                              <div
                                className="bg-[#ef4444] h-full transition-all duration-500"
                                style={{ width: `${aiDetection.ai_score * 100}%` }}
                              />
                            </div>
                          </div>

                          <div className="p-3 bg-[#1e293b] border border-[#334155] rounded">
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-[#94a3b8]">Authentic / Real Score</span>
                              <span className="text-[#10b981] font-bold font-mono">
                                {(aiDetection.real_score * 100).toFixed(1)}%
                              </span>
                            </div>
                            <div className="w-full bg-[#0f172a] h-2 rounded-full overflow-hidden">
                              <div
                                className="bg-[#10b981] h-full transition-all duration-500"
                                style={{ width: `${aiDetection.real_score * 100}%` }}
                              />
                            </div>
                          </div>
                        </div>

                        {/* Neural Forensic Metrics */}
                        <div className="p-3.5 bg-[#131d31] border border-[#1e293b] rounded space-y-2">
                          <h4 className="text-xs font-semibold text-white flex items-center gap-1.5">
                            <Activity className="w-3.5 h-3.5 text-[#38bdf8]" />
                            SigLIP Neural Classification Breakdown
                          </h4>
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
                            <div className="p-2 bg-[#0f172a] rounded border border-[#1e293b]">
                              <p className="text-[#94a3b8] text-[10px]">Deepfake Probability</p>
                              <p className="text-[#ef4444] font-bold mt-0.5">
                                {((aiDetection.ai_score || 0) * 100).toFixed(1)}%
                              </p>
                            </div>
                            <div className="p-2 bg-[#0f172a] rounded border border-[#1e293b]">
                              <p className="text-[#94a3b8] text-[10px]">Authentic Probability</p>
                              <p className="text-[#10b981] font-bold mt-0.5">
                                {((aiDetection.real_score || 0) * 100).toFixed(1)}%
                              </p>
                            </div>
                            <div className="p-2 bg-[#0f172a] rounded border border-[#1e293b]">
                              <p className="text-[#94a3b8] text-[10px]">Model Architecture</p>
                              <p className="text-white font-bold mt-0.5 truncate">SigLIP Vision</p>
                            </div>
                            <div className="p-2 bg-[#0f172a] rounded border border-[#1e293b]">
                              <p className="text-[#94a3b8] text-[10px]">Metadata Provenance</p>
                              <p className="text-white font-bold mt-0.5 truncate">{aiDetection.forensics?.metadata_provenance || "Clean"}</p>
                            </div>
                          </div>
                        </div>

                        {/* Analysis Indicators */}
                        <div className="p-3 bg-[#131d31] border border-[#1e293b] rounded space-y-1.5">
                          <h4 className="text-xs font-semibold text-white">Detection Evidence & Indicators:</h4>
                          <ul className="space-y-1 text-xs text-[#cbd5e1]">
                            {aiDetection.indicators.map((ind, i) => (
                              <li key={i} className="flex items-start gap-2">
                                <span className="text-[#38bdf8]">•</span>
                                <span>{ind}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    ) : (
                      <div className="py-8 text-center text-xs text-[#94a3b8] space-y-2">
                        <Fingerprint className="w-8 h-8 mx-auto text-[#334155]" />
                        <p>Click "Re-Scan" to evaluate document visual authenticity with the CvT-13 model.</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* =========================================================================
              RIGHT PANE: Interactive Workspace (Chat, Structured Extract, Chunks)
              ========================================================================= */}
          <div className="flex-1 lg:w-2/5 flex flex-col bg-[#0f172a] overflow-hidden">
            {/* Right Tabs Header */}
            <div className="h-11 bg-[#111827] border-b border-[#1e293b] flex items-center justify-between px-3">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setActiveTab("chat")}
                  className={`px-3 py-1 text-xs font-medium rounded ${
                    activeTab === "chat"
                      ? "bg-[#2563eb] text-white"
                      : "text-[#94a3b8] hover:text-white hover:bg-[#1e293b]"
                  }`}
                >
                  <span className="flex items-center gap-1.5">
                    <MessageSquare className="w-3.5 h-3.5" />
                    Chat
                  </span>
                </button>
                <button
                  onClick={() => setActiveTab("extract")}
                  className={`px-3 py-1 text-xs font-medium rounded ${
                    activeTab === "extract"
                      ? "bg-[#2563eb] text-white"
                      : "text-[#94a3b8] hover:text-white hover:bg-[#1e293b]"
                  }`}
                >
                  <span className="flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    JSON Extractor
                  </span>
                </button>
                <button
                  onClick={() => setActiveTab("chunks")}
                  className={`px-3 py-1 text-xs font-medium rounded ${
                    activeTab === "chunks"
                      ? "bg-[#2563eb] text-white"
                      : "text-[#94a3b8] hover:text-white hover:bg-[#1e293b]"
                  }`}
                >
                  <span className="flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5" />
                    Vectors ({selectedDoc?.chunks?.length || 0})
                  </span>
                </button>
              </div>

              {/* AI Provider Switcher */}
              <div className="flex items-center gap-1.5 bg-[#0b1120] p-1 rounded-md border border-[#1e293b]">
                <button
                  onClick={() => {
                    setLlmProvider("groq");
                    setLlmModel("openai/gpt-oss-20b");
                  }}
                  className={`px-2 py-0.5 text-[11px] font-medium rounded transition-colors flex items-center gap-1 ${
                    llmProvider === "groq"
                      ? "bg-[#f97316] text-white shadow-sm font-semibold"
                      : "text-[#94a3b8] hover:text-white"
                  }`}
                  title="Ultra-fast Cloud Groq inference with openai/gpt-oss-20b"
                >
                  <span>⚡ Groq Cloud</span>
                </button>
                <button
                  onClick={() => {
                    setLlmProvider("ollama");
                    setLlmModel("qwen2.5:3b");
                  }}
                  className={`px-2 py-0.5 text-[11px] font-medium rounded transition-colors flex items-center gap-1 ${
                    llmProvider === "ollama"
                      ? "bg-[#059669] text-white shadow-sm font-semibold"
                      : "text-[#94a3b8] hover:text-white"
                  }`}
                  title="Local Ollama inference with Qwen 2.5 (3B) on GPU"
                >
                  <span>🤖 Local Qwen</span>
                </button>
              </div>
            </div>

            {/* Right Tab Contents */}
            <div className="flex-1 flex flex-col overflow-hidden">
              
              {/* TAB 1: CHAT WITH DOCUMENT */}
              {activeTab === "chat" && (
                <div className="flex-1 flex flex-col h-full overflow-hidden">
                  <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {messages.map((m, i) => (
                      <div
                        key={i}
                        className={`flex flex-col ${
                          m.role === "user" ? "items-end" : "items-start"
                        }`}
                      >
                        <div
                          className={`max-w-[92%] rounded p-3 text-xs leading-relaxed ${
                            m.role === "user"
                              ? "bg-[#2563eb] text-white"
                              : "bg-[#1e293b] border border-[#334155] text-[#e2e8f0]"
                          }`}
                        >
                          {m.role === "assistant" && m.model && (
                            <div className="mb-2 flex items-center justify-between border-b border-[#334155]/60 pb-1.5">
                              <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold ${
                                m.model.includes("gpt") || m.model.includes("groq")
                                  ? "bg-[#7c2d12] text-[#fed7aa] border border-[#ea580c]"
                                  : "bg-[#064e3b] text-[#a7f3d0] border border-[#059669]"
                              }`}>
                                {m.model.includes("gpt") ? "⚡ Groq: " : "🤖 Ollama: "} {m.model}
                              </span>
                              <button
                                onClick={() => {
                                  navigator.clipboard.writeText(m.content);
                                }}
                                className="text-[10px] text-[#94a3b8] hover:text-white flex items-center gap-1"
                                title="Copy answer"
                              >
                                <Copy className="w-3 h-3" />
                                <span>Copy</span>
                              </button>
                            </div>
                          )}

                          {m.role === "assistant" ? (
                            <div className="chat-markdown select-text space-y-2">
                              <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                  table: ({ node, ...props }) => (
                                    <div className="overflow-x-auto my-2.5 border border-[#334155] rounded shadow-sm bg-[#090d16]">
                                      <table className="w-full border-collapse text-[11px] text-left" {...props} />
                                    </div>
                                  ),
                                  thead: ({ node, ...props }) => (
                                    <thead className="bg-[#0f172a] text-white border-b border-[#334155]" {...props} />
                                  ),
                                  th: ({ node, ...props }) => (
                                    <th className="px-2.5 py-1.5 font-semibold text-white border-r border-[#334155] last:border-r-0 whitespace-nowrap" {...props} />
                                  ),
                                  td: ({ node, ...props }) => (
                                    <td className="px-2.5 py-1.5 border-t border-[#1e293b] border-r border-[#1e293b] last:border-r-0 text-[#cbd5e1] hover:bg-[#131d31]/50 transition-colors" {...props} />
                                  ),
                                  h1: ({ node, ...props }) => (
                                    <h1 className="text-sm font-bold text-white mt-3 mb-1 pb-1 border-b border-[#334155]" {...props} />
                                  ),
                                  h2: ({ node, ...props }) => (
                                    <h2 className="text-xs font-bold text-[#38bdf8] mt-2.5 mb-1" {...props} />
                                  ),
                                  h3: ({ node, ...props }) => (
                                    <h3 className="text-xs font-semibold text-[#93c5fd] mt-2 mb-0.5" {...props} />
                                  ),
                                  p: ({ node, ...props }) => (
                                    <p className="my-1.5 leading-relaxed text-[#e2e8f0]" {...props} />
                                  ),
                                  ul: ({ node, ...props }) => (
                                    <ul className="list-disc list-outside ml-4 my-1.5 space-y-1 text-[#cbd5e1]" {...props} />
                                  ),
                                  ol: ({ node, ...props }) => (
                                    <ol className="list-decimal list-outside ml-4 my-1.5 space-y-1 text-[#cbd5e1]" {...props} />
                                  ),
                                  li: ({ node, ...props }) => (
                                    <li className="leading-relaxed pl-0.5" {...props} />
                                  ),
                                  blockquote: ({ node, ...props }) => (
                                    <blockquote className="border-l-2 border-[#2563eb] pl-2.5 py-1 text-[#94a3b8] italic my-2 bg-[#090d16]/50 rounded-r" {...props} />
                                  ),
                                  strong: ({ node, ...props }) => (
                                    <strong className="font-semibold text-white" {...props} />
                                  ),
                                  code: ({ node, ...props }) => (
                                    <code className="px-1 py-0.5 bg-[#090d16] border border-[#334155] rounded text-[10px] font-mono text-[#38bdf8]" {...props} />
                                  ),
                                }}
                              >
                                {m.content.replace(/^\s*\*+Answer\**\s*:?\s*/i, "")}
                              </ReactMarkdown>
                            </div>
                          ) : (
                            <div className="whitespace-pre-wrap">{m.content}</div>
                          )}
                          
                          {/* Citations */}
                          {m.citations && m.citations.length > 0 && (
                            <div className="mt-2.5 pt-2 border-t border-[#334155] space-y-1">
                              <p className="text-[10px] font-semibold text-[#38bdf8] flex items-center gap-1">
                                <BookOpen className="w-3 h-3" /> Grounded Source Citations:
                              </p>
                              {m.citations.map((c, ci) => (
                                <div
                                  key={ci}
                                  className="text-[10px] bg-[#0f172a] p-1.5 rounded border border-[#1e293b] text-[#94a3b8]"
                                >
                                  <span className="font-semibold text-white">Page {c.page_number}</span>:{" "}
                                  <span className="italic">"{c.chunk_content.slice(0, 90)}..."</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                    {chatLoading && (
                      <div className="flex items-center gap-2 text-xs text-[#94a3b8] bg-[#1e293b] p-2.5 rounded max-w-[60%]">
                        <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#38bdf8]" />
                        <span>{llmProvider === "groq" ? "Groq Cloud (openai/gpt-oss-20b) answering..." : "Local Qwen 2.5 reasoning..."}</span>
                      </div>
                    )}
                    <div ref={chatBottomRef} />
                  </div>

                  {/* Chat Input */}
                  <form onSubmit={handleSendMessage} className="p-3 border-t border-[#1e293b] bg-[#111827]">
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        placeholder={
                          selectedDoc
                            ? `Ask anything about ${selectedDoc.original_name}...`
                            : "Upload/select a document to chat..."
                        }
                        value={queryInput}
                        onChange={(e) => setQueryInput(e.target.value)}
                        disabled={chatLoading}
                        className="flex-1 bg-[#1e293b] border border-[#334155] rounded px-3 py-2 text-xs text-white placeholder-[#64748b] focus:outline-none focus:border-[#2563eb]"
                      />
                      <button
                        type="submit"
                        disabled={chatLoading || !queryInput.trim()}
                        className="px-3.5 py-2 bg-[#2563eb] hover:bg-[#1d4ed8] disabled:opacity-50 text-white rounded text-xs font-medium flex items-center gap-1 transition-colors"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>Ask</span>
                      </button>
                    </div>
                  </form>
                </div>
              )}

              {/* TAB 2: STRUCTURED JSON EXTRACTOR */}
              {activeTab === "extract" && (
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  <div className="bg-[#111827] border border-[#1e293b] rounded p-3.5 space-y-3">
                    <h3 className="text-xs font-semibold text-white flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-[#38bdf8]" />
                      Schema-Guided Information Extraction
                    </h3>
                    <div className="space-y-2">
                      <label className="text-[11px] text-[#94a3b8]">Extraction Template</label>
                      <select
                        value={extractionSchema}
                        onChange={(e) => setExtractionSchema(e.target.value)}
                        className="w-full bg-[#1e293b] border border-[#334155] rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-[#2563eb]"
                      >
                        <option value="invoice">Invoice / Billing (Vendor, Total, Line Items, Tax)</option>
                        <option value="receipt">Receipt (Merchant, Date, Items, Grand Total)</option>
                        <option value="contract">Contract (Parties, Dates, Liabilities, Clauses)</option>
                        <option value="resume">Resume / CV (Candidate, Skills, Education, Experience)</option>
                        <option value="id_document">ID / Passport (Name, ID Number, DOB, Expiry)</option>
                        <option value="custom">Custom JSON Schema</option>
                      </select>
                    </div>

                    {extractionSchema === "custom" && (
                      <div className="space-y-1">
                        <label className="text-[11px] text-[#94a3b8]">Custom Target Fields (comma separated)</label>
                        <input
                          type="text"
                          placeholder="e.g. invoice_id, due_date, bank_account, total_amount"
                          value={customFields}
                          onChange={(e) => setCustomFields(e.target.value)}
                          className="w-full bg-[#1e293b] border border-[#334155] rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-[#2563eb]"
                        />
                      </div>
                    )}

                    <button
                      onClick={handleExtract}
                      disabled={!selectedDocId || extracting}
                      className="w-full py-2 bg-[#2563eb] hover:bg-[#1d4ed8] disabled:opacity-50 text-white rounded text-xs font-medium flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${extracting ? "animate-spin" : ""}`} />
                      <span>{extracting ? `Extracting JSON with ${llmProvider === "groq" ? "Groq (GPT-OSS 20B)" : "Qwen 2.5"}...` : `Run Extraction (${llmProvider === "groq" ? "Groq Cloud" : "Local Qwen"})`}</span>
                    </button>
                  </div>

                  {/* Extraction JSON Results */}
                  {latestExtraction && (
                    <div className="bg-[#111827] border border-[#1e293b] rounded p-3.5 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-white">Extracted JSON Payload</span>
                        <button
                          onClick={() => copyToClipboard(JSON.stringify(latestExtraction.extracted_data, null, 2))}
                          className="flex items-center gap-1 text-[11px] text-[#38bdf8] hover:text-white bg-[#1e293b] px-2 py-0.5 rounded border border-[#334155]"
                        >
                          {copiedJson ? <Check className="w-3 h-3 text-[#10b981]" /> : <Copy className="w-3 h-3" />}
                          <span>{copiedJson ? "Copied" : "Copy JSON"}</span>
                        </button>
                      </div>
                      <pre className="bg-[#090d16] border border-[#1e293b] rounded p-3 text-[11px] font-mono text-[#38bdf8] overflow-x-auto max-h-96">
                        {JSON.stringify(latestExtraction.extracted_data, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: VECTOR CHUNKS INSPECTOR */}
              {activeTab === "chunks" && (
                <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
                  <div className="flex items-center justify-between text-xs text-[#94a3b8] mb-2">
                    <span>FastEmbed 384-dim Vector Chunks</span>
                    <span>{selectedDoc?.chunks?.length || 0} Chunks Indexed</span>
                  </div>
                  {!selectedDoc?.chunks || selectedDoc.chunks.length === 0 ? (
                    <div className="p-6 text-center text-xs text-[#64748b]">No chunks available for this document.</div>
                  ) : (
                    selectedDoc.chunks.map((chunk) => (
                      <div
                        key={chunk.id}
                        className="bg-[#111827] border border-[#1e293b] rounded p-3 space-y-1 text-xs"
                      >
                        <div className="flex items-center justify-between text-[10px] text-[#94a3b8] font-mono">
                          <span>Chunk #{chunk.chunk_index}</span>
                          <span>Page {chunk.page_number}</span>
                        </div>
                        <p className="text-[#cbd5e1] font-mono text-[11px] whitespace-pre-wrap leading-relaxed">
                          {chunk.content}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              )}

            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
