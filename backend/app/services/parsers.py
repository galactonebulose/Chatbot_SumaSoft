import csv
from io import StringIO, BytesIO
from typing import List, Dict, Any

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

PDF_AVAILABLE = PYMUPDF_AVAILABLE or PYPDF_AVAILABLE

try:
    import docx2txt
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


def parse_txt(content: bytes) -> str:
    """Extract text from TXT file"""
    return content.decode("utf-8", errors="ignore")


def parse_csv(content: bytes) -> str:
    """Extract and format rows from CSV file into descriptive strings"""
    text_data = []
    try:
        csv_file = StringIO(content.decode("utf-8", errors="ignore"))
        reader = csv.reader(csv_file)
        headers = next(reader, None)
        
        for row in reader:
            if not row:
                continue
            if headers:
                row_str = " | ".join(f"{h}: {val}" for h, val in zip(headers, row) if val.strip())
            else:
                row_str = " | ".join(val for val in row if val.strip())
            if row_str:
                text_data.append(row_str)
    except Exception as e:
        print(f"Error parsing CSV: {e}")
    return "\n".join(text_data)


def parse_pdf(content: bytes) -> str:
    """Extract text from PDF pages using PyMuPDF (fitz) with fallback to pypdf"""
    if not PDF_AVAILABLE:
        raise ImportError("Neither PyMuPDF nor pypdf is installed. Run: pip install pymupdf or pip install pypdf")
    
    text = ""
    if PYMUPDF_AVAILABLE:
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            for page in doc:
                page_text = page.get_text()
                if page_text:
                    text += page_text + "\n"
            return text
        except Exception as e:
            print(f"Error parsing PDF with PyMuPDF: {e}. Falling back to pypdf...")
            
    if PYPDF_AVAILABLE:
        try:
            pdf_file = BytesIO(content)
            reader = PdfReader(pdf_file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        except Exception as e:
            print(f"Error parsing PDF with pypdf: {e}")
            
    return text


def parse_docx(content: bytes) -> str:
    """Extract text from DOCX using docx2txt"""
    if not DOCX_AVAILABLE:
        raise ImportError("docx2txt is not installed. Run: pip install docx2txt")
        
    try:
        docx_file = BytesIO(content)
        return docx2txt.process(docx_file)
    except Exception as e:
        print(f"Error parsing DOCX: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 80) -> List[str]:
    """Split text into overlapping text fragments"""
    chunks = []
    text = text.strip()
    if not text:
        return chunks
        
    # Split text by character lengths, keeping words intact where possible
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        # If we aren't at the end of the text, back up to find the last space/newline
        # so we don't sever words in half.
        if end < len(text):
            space_idx = text.rfind(" ", start + int(chunk_size * 0.8), end)
            if space_idx != -1 and space_idx > start:
                end = space_idx
                
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
            
        start = end - overlap
        if start >= len(text) or (end == len(text)):
            break
            
    return chunks
