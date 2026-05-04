import io
import PyPDF2
import docx


def extract_text_from_pdf(file_obj) -> str:
    text_parts = []
    reader = PyPDF2.PdfReader(file_obj)
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return "\n".join(text_parts)


def extract_text_from_docx(file_obj) -> str:
    doc = docx.Document(file_obj)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_text(file_obj, filename: str) -> str:
    name = filename.lower()
    if name.endswith('.pdf'):
        return extract_text_from_pdf(file_obj)
    elif name.endswith('.docx'):
        return extract_text_from_docx(file_obj)
    elif name.endswith('.doc'):
        return extract_text_from_docx(file_obj)
    else:
        # Try reading as plain text
        try:
            content = file_obj.read()
            return content.decode('utf-8', errors='ignore')
        except Exception:
            return ""
