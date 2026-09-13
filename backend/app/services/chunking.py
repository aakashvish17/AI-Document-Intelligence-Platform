import re
from typing import List, Dict, Any

class Chunk:
    def __init__(self, content: str, page_number: int, chunk_type: str = "text", metadata: Dict[str, Any] = None):
        self.content = content
        self.page_number = page_number
        self.chunk_type = chunk_type
        self.metadata = metadata or {}

class DocumentChunker:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, markdown_text: str, default_page: int = 1) -> List[Chunk]:
        """
        Chunks markdown by sections, tables, and paragraphs while preserving 
        table formats and page markers.
        """
        # Split by page annotations if present (e.g. ## Page X or <!-- Page X -->)
        page_splits = re.split(r'(?:<!-- Page (\d+) -->|## Page (\d+))', markdown_text)
        
        chunks: List[Chunk] = []
        current_page = default_page
        
        # If there are explicit page delimiters
        if len(page_splits) > 1:
            idx = 0
            while idx < len(page_splits):
                segment = page_splits[idx]
                if segment is None:
                    idx += 1
                    continue
                if segment.isdigit():
                    current_page = int(segment)
                    idx += 1
                    continue
                
                # Chunk this page's segment
                page_chunks = self._chunk_text(segment, current_page)
                chunks.extend(page_chunks)
                idx += 1
        else:
            chunks = self._chunk_text(markdown_text, default_page)
            
        return chunks

    def _chunk_text(self, text: str, page_number: int) -> List[Chunk]:
        paragraphs = text.split("\n\n")
        chunks: List[Chunk] = []
        current_chunk_text = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Detect table chunks (e.g., markdown table)
            is_table = "|" in para and "-|-" in para

            if is_table:
                # Flush pending chunk
                if current_chunk_text:
                    chunks.append(Chunk(content=current_chunk_text.strip(), page_number=page_number, chunk_type="text"))
                    current_chunk_text = ""
                # Add table as an atomic chunk
                chunks.append(Chunk(content=para, page_number=page_number, chunk_type="table"))
                continue

            if len(current_chunk_text) + len(para) > self.chunk_size:
                if current_chunk_text:
                    chunks.append(Chunk(content=current_chunk_text.strip(), page_number=page_number, chunk_type="text"))
                    # Overlap with end of current chunk
                    overlap = current_chunk_text[-self.chunk_overlap:] if len(current_chunk_text) > self.chunk_overlap else ""
                    current_chunk_text = overlap + "\n\n" + para
                else:
                    chunks.append(Chunk(content=para[:self.chunk_size], page_number=page_number, chunk_type="text"))
                    current_chunk_text = para[self.chunk_size:]
            else:
                if current_chunk_text:
                    current_chunk_text += "\n\n" + para
                else:
                    current_chunk_text = para

        if current_chunk_text.strip():
            chunks.append(Chunk(content=current_chunk_text.strip(), page_number=page_number, chunk_type="text"))

        return chunks

chunker_service = DocumentChunker()
