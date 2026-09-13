import os
import io
import csv
import json
import re
from typing import Dict, Any, List
from pypdf import PdfReader
from PIL import Image

class ParsedPage:
    def __init__(self, page_number: int, text: str, tables: List[str] = None):
        self.page_number = page_number
        self.text = text
        self.tables = tables or []

class ParsedDocument:
    def __init__(self, markdown_content: str, pages: List[ParsedPage], metadata: Dict[str, Any], page_count: int):
        self.markdown_content = markdown_content
        self.pages = pages
        self.metadata = metadata
        self.page_count = page_count

class UniversalDocumentParser:
    """
    Universal Parser supporting:
    - PDFs (Native & Scanned OCR)
    - Word (.docx, .doc)
    - Excel / Spreadsheets (.xlsx, .xls, .csv, .tsv)
    - PowerPoint (.pptx)
    - Images (.png, .jpg, .jpeg, .tiff, .bmp, .webp) with RapidOCR / Docling
    - Plaintext & Code (.txt, .md, .json, .html)
    """
    def __init__(self):
        self._rapid_ocr = None
        self._easy_ocr = None

    def _get_ocr(self):
        if self._rapid_ocr is None:
            try:
                from rapidocr import RapidOCR
                self._rapid_ocr = RapidOCR()
            except Exception:
                try:
                    from rapidocr_onnxruntime import RapidOCR
                    self._rapid_ocr = RapidOCR()
                except Exception:
                    self._rapid_ocr = "unavailable"
        return self._rapid_ocr

    def _get_easy_ocr(self):
        if self._easy_ocr is None:
            try:
                import easyocr
                self._easy_ocr = easyocr.Reader(['hi', 'en'], verbose=False, gpu=False)
            except Exception as e:
                print(f"[!] EasyOCR (Hindi/English) load notice: {e}")
                self._easy_ocr = "unavailable"
        return self._easy_ocr

    def _run_ocr_on_pil_image(self, img_pil: Image.Image) -> List[Any]:
        """
        Run OCR on any PIL Image safely.
        Combines RapidOCR (fast layout, tables & English) + EasyOCR (Hindi Devanagari script).
        """
        import numpy as np
        import re
        arr = np.array(img_pil.convert("RGB"))
        items = []

        # 1. Fast RapidOCR (Primary ~0.5s per page)
        ocr = self._get_ocr()
        if ocr != "unavailable":
            try:
                out = ocr(arr)
                if isinstance(out, tuple) and len(out) >= 1 and out[0]:
                    items.extend(out[0])
                elif isinstance(out, list):
                    items.extend(out)
                elif hasattr(out, "boxes") and out.boxes is not None and hasattr(out, "txts") and out.txts is not None:
                    boxes = out.boxes
                    txts = out.txts
                    scores = out.scores if hasattr(out, "scores") and out.scores is not None else [1.0] * len(txts)
                    for b, t, s in zip(boxes, txts, scores):
                        if str(t).strip() and float(s) >= 0.20:
                            items.append([b, str(t).strip(), float(s)])
            except Exception as e:
                print(f"[!] RapidOCR image parse error: {e}")

        # 2. EasyOCR Fallback (only if RapidOCR found very few items or missed content)
        if len(items) < 8:
            easy_reader = self._get_easy_ocr()
            if easy_reader != "unavailable":
                try:
                    w, h = img_pil.size
                    scale_factor = 1.0
                    if max(w, h) > 1200:
                        scale_factor = 1200.0 / max(w, h)
                        target_size = (int(w * scale_factor), int(h * scale_factor))
                        arr_easy = np.array(img_pil.resize(target_size, Image.Resampling.BILINEAR).convert("RGB"))
                    else:
                        arr_easy = arr

                    results = easy_reader.readtext(arr_easy)
                    if results:
                        for r in results:
                            text_str = str(r[1]).strip()
                            if text_str:
                                if scale_factor != 1.0:
                                    box = [[pt[0] / scale_factor, pt[1] / scale_factor] for pt in r[0]]
                                else:
                                    box = r[0]
                                items.append([box, text_str, float(r[2]) if len(r) > 2 else 0.8])
                except Exception as e:
                    print(f"[!] EasyOCR parse error: {e}")

        # Clean out isolated non-Latin/Chinese artifact glyphs from RapidOCR if any
        clean_items = []
        for it in items:
            if len(it) >= 3:
                t = str(it[1]).strip()
                if re.match(r'^[\u4e00-\u9fff\s]+$', t):
                    continue
                clean_items.append(it)

        return clean_items

    def _format_ocr_to_markdown(self, ocr_res: List[Any], section_title: str = "Extracted Content") -> str:
        """
        Convert OCR bounding boxes and text into clean, structured Markdown.
        Supports multi-column exam papers/articles, tables, headings, and lists.
        """
        valid_items = [
            item for item in ocr_res 
            if len(item) >= 3 and float(item[2]) >= 0.18 and str(item[1]).strip()
        ]
        if not valid_items:
            return f"## {section_title}\n\n*(No readable text detected.)*"

        processed = []
        for item in valid_items:
            box = item[0]
            text = str(item[1]).strip()
            ymin = min(p[1] for p in box)
            ymax = max(p[1] for p in box)
            xmin = min(p[0] for p in box)
            xmax = max(p[0] for p in box)
            processed.append({
                "ymin": ymin, "ymax": ymax, "xmin": xmin, "xmax": xmax,
                "height": ymax - ymin, "width": xmax - xmin, "text": text
            })

        min_x = min(p["xmin"] for p in processed)
        max_x = max(p["xmax"] for p in processed)
        total_width = max_x - min_x
        mid_x = min_x + (total_width / 2.0)

        # Detect if document has a 2-column layout (e.g. exam papers, articles, side-by-side pages)
        left_items = [p for p in processed if p["xmax"] < (mid_x + 40)]
        right_items = [p for p in processed if p["xmin"] > (mid_x - 40)]
        
        is_multi_column = len(left_items) >= 4 and len(right_items) >= 4 and (len(left_items) + len(right_items)) >= (len(processed) * 0.85)

        if is_multi_column:
            # Process Column 1 then Column 2 in natural reading order
            col1_md = self._format_column_lines(left_items)
            col2_md = self._format_column_lines(right_items)
            return f"## {section_title}\n\n{col1_md}\n\n---\n\n{col2_md}".strip()
        else:
            col_md = self._format_column_lines(processed)
            return f"## {section_title}\n\n{col_md}".strip()

    def _format_column_lines(self, items: List[Dict[str, Any]]) -> str:
        if not items:
            return ""

        avg_height = sum(p["height"] for p in items) / max(len(items), 1)

        # Group items into lines based on vertical overlap
        lines: List[List[Dict[str, Any]]] = []
        items_sorted = sorted(items, key=lambda p: p["ymin"])

        for item in items_sorted:
            placed = False
            for line in lines:
                line_avg_y = sum(i["ymin"] for i in line) / len(line)
                if abs(item["ymin"] - line_avg_y) <= (avg_height * 0.65):
                    line.append(item)
                    placed = True
                    break
            if not placed:
                lines.append([item])

        # Sort items inside each line horizontally and deduplicate overlapping boxes
        cleaned_lines: List[str] = []
        for line in lines:
            line.sort(key=lambda item: item["xmin"])
            
            merged_tokens: List[str] = []
            prev_item = None
            for item in line:
                t = item["text"].strip()
                # Skip pure OCR noise glyphs
                if not t or re.match(r'^[\s\-_•*|,\.¿?()~+=/\\可市af]+$', t) and len(t) <= 3:
                    continue
                if re.match(r'^[A-Za-z\u4e00-\u9fff]{1,2}[可市][A-Za-z\u4e00-\u9fff]{1,2}$', t):
                    continue

                if prev_item is not None:
                    # Check horizontal overlap
                    overlap = min(prev_item["xmax"], item["xmax"]) - max(prev_item["xmin"], item["xmin"])
                    min_w = min(prev_item["width"], item["width"])
                    if min_w > 0 and (overlap / min_w) > 0.5:
                        # Overlapping box: Keep the one with richer or Hindi text
                        if re.search(r'[\u0900-\u097F]', t) and not re.search(r'[\u0900-\u097F]', merged_tokens[-1]):
                            merged_tokens[-1] = t
                        continue

                merged_tokens.append(t)
                prev_item = item

            if merged_tokens:
                line_text = " ".join(merged_tokens)
                # Clean multiple spaces and dangling punctuation
                line_text = re.sub(r'\s{2,}', ' ', line_text).strip()
                if line_text:
                    cleaned_lines.append(line_text)

        md_output: List[str] = []
        for idx, single_text in enumerate(cleaned_lines):
            # 1. Heading Detection: Title / Big font or Standalone Uppercase header
            if (len(single_text) < 45 and single_text.isupper() and idx < 4) or re.match(r'^(?:BT\d{2,4}\s*\([A-Z]+\)|B\.Tech\b|Examination\b)', single_text):
                md_output.append(f"\n### {single_text}\n")
            
            # 2. Key-Value Detection: e.g. "Time: Three Hours" or "Maximum Marks: 70"
            elif re.match(r'^(?:Time|Maximum Marks|Total No|Total Marks|Note|Enrolment)\b', single_text, re.IGNORECASE) and ":" in single_text:
                parts = single_text.split(":", 1)
                md_output.append(f"**{parts[0].strip()}:** {parts[1].strip()}")
            
            # 3. Question Numbering Detection: "1. (i)", "2. (i)", "(i)", "(ii)", "Note: (i)"
            elif re.match(r'^(?:\d+\.|\([a-z0-9ivxIVX]+\)|Note:)', single_text):
                md_output.append(f"\n{single_text}")
            
            # 4. Standard sentence / Hindi translation
            else:
                md_output.append(f"{single_text}")

        return "\n".join(md_output).strip()

    def parse_document(self, file_path: str, mime_type: str = "") -> ParsedDocument:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        # 1. Images (.png, .jpg, .jpeg, .tiff, .bmp, .webp)
        if ext in [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"] or "image" in mime_type:
            return self._parse_image_ocr(file_path)

        # 2. Word Documents (.docx)
        elif ext in [".docx", ".doc"]:
            return self._parse_docx(file_path)

        # 3. Excel Spreadsheets & CSV (.xlsx, .csv, .tsv)
        elif ext in [".xlsx", ".xls", ".csv", ".tsv"]:
            return self._parse_spreadsheet(file_path, ext)

        # 4. PowerPoint Presentations (.pptx)
        elif ext in [".pptx", ".ppt"]:
            return self._parse_pptx(file_path)

        # 5. PDFs (.pdf) - Native & Scanned Image PDFs
        elif ext == ".pdf" or "pdf" in mime_type:
            return self._parse_pdf(file_path)

        # 6. Plain Text / Markdown / JSON / Code
        else:
            return self._parse_text(file_path, ext)

    def _parse_image_ocr(self, file_path: str) -> ParsedDocument:
        """Extract structured text & tables from images with rich Markdown formatting."""
        # 1. Try Docling for native high-accuracy Markdown layout export
        try:
            from docling.document_converter import DocumentConverter
            converter = DocumentConverter()
            result = converter.convert(file_path)
            doc = result.document
            markdown_text = doc.export_to_markdown()
            if markdown_text and len(markdown_text.strip()) > 30:
                return ParsedDocument(
                    markdown_content=markdown_text,
                    pages=[ParsedPage(page_number=1, text=markdown_text)],
                    metadata={"parser": "docling", "format": "image"},
                    page_count=1
                )
        except Exception:
            pass

        # 2. Fast RapidOCR with Spatial Markdown Layout Reconstruction
        try:
            with Image.open(file_path) as raw_img:
                raw_ocr_items = self._run_ocr_on_pil_image(raw_img)
                if raw_ocr_items:
                    markdown_content = self._format_ocr_to_markdown(raw_ocr_items, section_title="Image Extracted Content")
                    return ParsedDocument(
                        markdown_content=markdown_content,
                        pages=[ParsedPage(page_number=1, text=markdown_content)],
                        metadata={"parser": "RapidOCR-Markdown", "format": "image"},
                        page_count=1
                    )
        except Exception as e:
            print(f"[!] Error in image OCR: {e}")

        # 3. Fallback to pytesseract
        fallback_text = ""
        try:
            import pytesseract
            img = Image.open(file_path)
            fallback_text = pytesseract.image_to_string(img).strip()
        except Exception:
            pass

        if fallback_text:
            md = f"## Image Extracted Content\n\n{fallback_text}"
        else:
            md = "## Image Uploaded\n\n*(No machine-readable text detected in this image.)*"

        return ParsedDocument(
            markdown_content=md,
            pages=[ParsedPage(page_number=1, text=md)],
            metadata={"parser": "pytesseract", "format": "image"},
            page_count=1
        )

    def _parse_docx(self, file_path: str) -> ParsedDocument:
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(file_path)
            md_lines = []
            
            for p in doc.paragraphs:
                text = p.text.strip()
                if not text:
                    continue
                if p.style.name.startswith("Heading 1"):
                    md_lines.append(f"# {text}\n")
                elif p.style.name.startswith("Heading 2"):
                    md_lines.append(f"## {text}\n")
                elif p.style.name.startswith("Heading 3"):
                    md_lines.append(f"### {text}\n")
                else:
                    md_lines.append(f"{text}\n")

            # Extract tables
            for table in doc.tables:
                md_lines.append("\n")
                for row_idx, row in enumerate(table.rows):
                    row_cells = [cell.text.replace("\n", " ").strip() for cell in row.cells]
                    md_lines.append("| " + " | ".join(row_cells) + " |")
                    if row_idx == 0:
                        md_lines.append("| " + " | ".join(["---"] * len(row_cells)) + " |")
                md_lines.append("\n")

            full_text = "\n".join(md_lines)
            return ParsedDocument(
                markdown_content=full_text,
                pages=[ParsedPage(page_number=1, text=full_text)],
                metadata={"parser": "python-docx", "format": "docx"},
                page_count=1
            )
        except Exception as e:
            print(f"[!] docx parse failed: {e}. Fallback to plaintext.")
            return self._parse_text(file_path, ".docx")

    def _parse_spreadsheet(self, file_path: str, ext: str) -> ParsedDocument:
        md_lines = []
        if ext == ".csv" or ext == ".tsv":
            delimiter = "\t" if ext == ".tsv" else ","
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f, delimiter=delimiter)
                for idx, row in enumerate(reader):
                    clean_row = [c.strip() for c in row]
                    md_lines.append("| " + " | ".join(clean_row) + " |")
                    if idx == 0:
                        md_lines.append("| " + " | ".join(["---"] * len(clean_row)) + " |")
        else:
            try:
                import openpyxl
                wb = openpyxl.load_workbook(file_path, data_only=True)
                for sheet in wb.sheetnames:
                    ws = wb[sheet]
                    md_lines.append(f"### Sheet: {sheet}\n")
                    for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
                        if not any(row):
                            continue
                        row_cells = [str(c).strip() if c is not None else "" for c in row]
                        md_lines.append("| " + " | ".join(row_cells) + " |")
                        if row_idx == 0:
                            md_lines.append("| " + " | ".join(["---"] * len(row_cells)) + " |")
                    md_lines.append("\n")
            except Exception as e:
                print(f"[!] openpyxl failed: {e}")

        full_text = "\n".join(md_lines)
        return ParsedDocument(
            markdown_content=full_text,
            pages=[ParsedPage(page_number=1, text=full_text)],
            metadata={"parser": "spreadsheet", "format": ext},
            page_count=1
        )

    def _parse_pptx(self, file_path: str) -> ParsedDocument:
        try:
            from pptx import Presentation
            prs = Presentation(file_path)
            pages = []
            full_md = []

            for slide_num, slide in enumerate(prs.slides, start=1):
                slide_lines = [f"## Slide {slide_num}"]
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_lines.append(shape.text.strip())
                slide_content = "\n\n".join(slide_lines)
                pages.append(ParsedPage(page_number=slide_num, text=slide_content))
                full_md.append(slide_content)

            full_text = "\n\n---\n\n".join(full_md)
            return ParsedDocument(
                markdown_content=full_text,
                pages=pages,
                metadata={"parser": "python-pptx", "format": "pptx"},
                page_count=len(prs.slides)
            )
        except Exception as e:
            return self._parse_text(file_path, ".pptx")

    def _parse_pdf(self, file_path: str) -> ParsedDocument:
        """
        Parse PDFs with automatic detection and OCR for scanned documents, 
        physical paper captures, and camera photo PDFs.
        """
        # 1. Try Docling if available
        try:
            from docling.document_converter import DocumentConverter
            converter = DocumentConverter()
            result = converter.convert(file_path)
            doc = result.document
            markdown_text = doc.export_to_markdown()
            if markdown_text and len(markdown_text.strip()) > 40:
                num_pages = len(doc.pages) if hasattr(doc, "pages") and doc.pages else 1
                return ParsedDocument(
                    markdown_content=markdown_text,
                    pages=[ParsedPage(page_number=1, text=markdown_text)],
                    metadata={"parser": "docling", "format": "pdf"},
                    page_count=num_pages
                )
        except Exception:
            pass

        # 2. High-Fidelity PyPDFium2 Rasterization + RapidOCR for Scanned & Digital Pages
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(file_path)
            num_pages = len(pdf)
            pages: List[ParsedPage] = []
            full_md = []

            for idx, page in enumerate(pdf, start=1):
                # Try extracting digital text first
                textpage = page.get_textpage()
                page_text = textpage.get_text_range().strip() if textpage else ""

                # If page is a scan / photo / image (digital text is empty or < 30 chars)
                if len(page_text) < 30:
                    try:
                        # Render high-resolution page bitmap (1.75x scale ~ 150 DPI)
                        rendered_img = page.render(scale=1.75).to_pil()
                        ocr_items = self._run_ocr_on_pil_image(rendered_img)
                        if ocr_items:
                            page_md = self._format_ocr_to_markdown(ocr_items, section_title=f"Page {idx}")
                        else:
                            page_md = f"## Page {idx}\n\n*(Scanned page with no readable text detected.)*"
                    except Exception as e:
                        print(f"[!] PDF page {idx} OCR rasterization error: {e}")
                        page_md = f"## Page {idx}\n\n{page_text}" if page_text else f"## Page {idx}\n\n*(Blank page)*"
                else:
                    # Clean digital page text
                    page_md = f"## Page {idx}\n\n{page_text}"

                pages.append(ParsedPage(page_number=idx, text=page_md))
                full_md.append(page_md)

            complete_markdown = "\n\n---\n\n".join(full_md)
            return ParsedDocument(
                markdown_content=complete_markdown,
                pages=pages,
                metadata={"parser": "pypdfium2+RapidOCR", "format": "pdf"},
                page_count=num_pages
            )
        except Exception as e:
            print(f"[!] PyPDFium2 parse failed: {e}. Falling back to PyPDF...")

        # 3. Fallback: Native PyPDF
        reader = PdfReader(file_path)
        num_pages = len(reader.pages)
        pages: List[ParsedPage] = []
        full_md = []

        for idx, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            page_md = f"## Page {idx}\n\n{page_text.strip()}"
            pages.append(ParsedPage(page_number=idx, text=page_md))
            full_md.append(page_md)

        return ParsedDocument(
            markdown_content="\n\n---\n\n".join(full_md),
            pages=pages,
            metadata={"parser": "pypdf-fallback", "format": "pdf"},
            page_count=num_pages
        )

    def _parse_text(self, file_path: str, ext: str) -> ParsedDocument:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return ParsedDocument(
            markdown_content=content,
            pages=[ParsedPage(page_number=1, text=content)],
            metadata={"parser": "plaintext", "format": ext},
            page_count=1
        )

parser_service = UniversalDocumentParser()
