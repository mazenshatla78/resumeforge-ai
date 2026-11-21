import io
from pdfminer.high_level import extract_text as pdf_extract_text
from docx import Document as DocxDocument


def extract_text_from_bytes(data: bytes, filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        try:
            return pdf_extract_text(io.BytesIO(data)) or ""
        except Exception:
            return ""
    if name.endswith(".docx"):
        try:
            doc = DocxDocument(io.BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return ""
    # txt / md / fallback
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def clean_text(text: str) -> str:
    if not text:
        return ""
    lines = [ln.rstrip() for ln in text.splitlines()]
    # collapse 3+ blank lines
    out = []
    blanks = 0
    for ln in lines:
        if ln.strip() == "":
            blanks += 1
            if blanks <= 2:
                out.append("")
        else:
            blanks = 0
            out.append(ln)
    return "\n".join(out).strip()
