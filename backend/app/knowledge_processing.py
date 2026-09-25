"""Private document extraction and durable knowledge indexing."""
from datetime import UTC, datetime
import csv
import io
import os
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

from docx import Document
from PIL import Image
from pypdf import PdfReader
import pytesseract
from sqlalchemy import delete, select

from .database import SessionLocal
from .models import KnowledgeChunk, KnowledgeDocument

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./private_uploads"))
MAX_EXTRACTED_CHARACTERS = 2_000_000
MAX_DOCX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 25_000_000


def _update(document: KnowledgeDocument, session, *, status: str, stage: str, progress: int) -> None:
    document.status = status
    document.stage = stage
    document.progress = progress
    session.commit()


def _validate_docx(path: Path) -> None:
    try:
        with ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > 2_000 or sum(member.file_size for member in members) > MAX_DOCX_UNCOMPRESSED_BYTES:
                raise ValueError("The DOCX archive is too complex to process safely")
    except BadZipFile as error:
        raise ValueError("The DOCX file is not a valid document archive") from error


def _extract_text(path: Path, content_type: str) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        _validate_docx(path)
        document = Document(path)
        return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
    if suffix == ".pdf":
        reader = PdfReader(path, strict=True)
        if len(reader.pages) > 500:
            raise ValueError("PDF files may contain no more than 500 pages")
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            return pytesseract.image_to_string(image.convert("RGB"))
    raw = path.read_bytes()
    if len(raw) > 10 * 1024 * 1024:
        raise ValueError("Text files may be no larger than 10 MB")
    text = raw.decode("utf-8-sig", errors="strict")
    if suffix == ".csv":
        rows = csv.reader(io.StringIO(text))
        return "\n".join(" | ".join(cell.strip() for cell in row) for row in rows)
    return text


def _clean_text(text: str) -> str:
    text = re.sub(r"[^\x09\x0A\x0D\x20-\uFFFF]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > MAX_EXTRACTED_CHARACTERS:
        raise ValueError("The extracted document text exceeds the safe processing limit")
    return text


def _chunks(text: str, target: int = 1_200, overlap: int = 160) -> list[str]:
    chunks: list[str] = []
    cursor = 0
    while cursor < len(text):
        end = min(len(text), cursor + target)
        if end < len(text):
            boundary = max(text.rfind("\n", cursor, end), text.rfind(". ", cursor, end))
            if boundary > cursor + target // 2:
                end = boundary + 1
        chunk = text[cursor:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        cursor = max(cursor + 1, end - overlap)
    return chunks


def process_knowledge_document(document_id: str) -> None:
    with SessionLocal() as session:
        document = session.get(KnowledgeDocument, document_id)
        if document is None:
            return
        path = UPLOAD_DIR / document.storage_key
        try:
            _update(document, session, status="processing", stage="Opening and validating the file", progress=15)
            if not path.is_file():
                raise FileNotFoundError("The private upload is unavailable")
            text = _extract_text(path, document.content_type)
            _update(document, session, status="processing", stage="Cleaning and understanding the content", progress=48)
            text = _clean_text(text)
            if len(text) < 20:
                raise ValueError("No usable text could be extracted from this file")
            chunks = _chunks(text)
            _update(document, session, status="processing", stage="Building the employee knowledge index", progress=72)
            session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id))
            session.add_all([
                KnowledgeChunk(document_id=document.id, assistant_id=document.assistant_id, workspace_id=document.workspace_id, sequence=index, content=chunk, token_estimate=max(1, len(chunk) // 4))
                for index, chunk in enumerate(chunks)
            ])
            document.chunk_count = len(chunks)
            _update(document, session, status="processing", stage="Verifying indexed knowledge", progress=92)
            document.status = "ready"
            document.stage = "Training material ready"
            document.progress = 100
            document.processed_at = datetime.now(UTC)
            word_count = len(text.split())
            document.feedback = f"Training complete. Indexed {word_count:,} words into {len(chunks)} secure knowledge sections. The material is ready for this AI employee to retrieve during assigned work."
            session.commit()
        except Exception as error:
            session.rollback()
            document = session.get(KnowledgeDocument, document_id)
            if document is None:
                return
            document.status = "failed"
            document.stage = "Training needs attention"
            document.progress = 100
            detail = str(error)[:240] if isinstance(error, ValueError) else "The file could not be processed securely. Confirm it is readable and retry."
            document.feedback = f"Training could not be completed: {detail}"
            session.commit()


def resume_pending_documents() -> None:
    with SessionLocal() as session:
        ids = list(session.scalars(select(KnowledgeDocument.id).where(KnowledgeDocument.status.in_(["queued", "processing"]))))
    for document_id in ids:
        process_knowledge_document(document_id)
