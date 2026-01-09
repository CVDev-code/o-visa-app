import fitz  # PyMuPDF

def extract_text_from_pdf_bytes(pdf_bytes: bytes, max_chars: int = 120_000) -> str:
    """
    Extract text from a PDF provided as bytes.
    Truncates to max_chars to avoid excessive token usage.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts = []

    for page in doc:
        parts.append(page.get_text("text"))

    doc.close()

    text = "\n\n".join(parts).strip()

    if len(text) > max_chars:
        text = text[:max_chars]

    return text
