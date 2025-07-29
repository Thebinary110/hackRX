import fitz 
import docx
import email
from bs4 import BeautifulSoup
import chardet
from typing import Union

def load_and_clean(file_bytes: bytes, filename: str) -> str:
    if filename.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif filename.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    elif filename.endswith(".eml") or filename.endswith(".msg"):
        return extract_text_from_email(file_bytes)
    else:
        raise ValueError(f"Unsupported file format: {filename}")

def extract_text_from_pdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    return "\n".join([page.get_text() for page in doc])

def extract_text_from_docx(file_bytes: bytes) -> str:
    from io import BytesIO
    doc = docx.Document(BytesIO(file_bytes))
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_email(file_bytes: bytes) -> str:
    encoding = chardet.detect(file_bytes)["encoding"]
    msg = email.message_from_bytes(file_bytes)
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body += part.get_payload(decode=True).decode(encoding or "utf-8", errors="ignore")
            elif part.get_content_type() == "text/html":
                html = part.get_payload(decode=True).decode(encoding or "utf-8", errors="ignore")
                body += BeautifulSoup(html, "html.parser").get_text()
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(encoding or "utf-8", errors="ignore")

    return body
