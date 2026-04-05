import asyncio
import glob
import os
import tempfile
from abc import ABC, abstractmethod

from docx import Document
import pdfplumber
from spire.doc import Document as SpireDocument, FileFormat as SpireFileFormat

from models import CVResult, CVStatus


# Base class for all extractors — defines the common interface
class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: str) -> str: ...

    # Run extract() in a thread so it doesn't block the event loop
    async def extract_async(self, file_path: str) -> str:
        return await asyncio.to_thread(self.extract, file_path)


# Extract text from PDF files using pdfplumber
class PdfExtractor(BaseExtractor):
    def extract(self, file_path: str) -> str:
        parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    parts.append(page_text)
        return "\n".join(parts).strip()


# Extract text from .docx files using python-docx
class DocxExtractor(BaseExtractor):
    def extract(self, file_path: str) -> str:
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()


# Extract text from legacy .doc files by converting to PDF first, then using PdfExtractor
class DocExtractor(BaseExtractor):
    def extract(self, file_path: str) -> str:
        # Create a temporary PDF file to hold the converted output
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            doc = SpireDocument()
            doc.LoadFromFile(file_path)
            doc.SaveToFile(tmp_path, SpireFileFormat.PDF)
            doc.Close()
            text = PdfExtractor().extract(tmp_path)
            # Remove watermark lines added by the free Spire.Doc license
            lines = [
                line for line in text.splitlines()
                if "Evaluation Warning" not in line and "Spire.Doc for Python" not in line
            ]
            return "\n".join(lines).strip()
        finally:
            # Always clean up the temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


# Maps file extensions to the correct extractor instance
EXTRACTOR_MAP: dict[str, BaseExtractor] = {
    ".pdf": PdfExtractor(),
    ".docx": DocxExtractor(),
    ".doc": DocExtractor(),
}


# Main service that scans a folder and extracts text from all CV files
class CVExtractorService:
    def __init__(self):
        self._extractors = EXTRACTOR_MAP

    # Recursively find all files inside the folder
    def _scan_files(self, folder_path: str) -> list[str]:
        pattern = os.path.join(folder_path, "**", "*")
        return sorted(
            f for f in glob.glob(pattern, recursive=True) if os.path.isfile(f)
        )

    # Process a single file — picks the right extractor based on extension
    async def _process_file(self, file_path: str) -> CVResult:
        ext = os.path.splitext(file_path)[1].lower()
        common = dict(
            file_name=os.path.basename(file_path),
            file_path=os.path.abspath(file_path),
            extension=ext,
        )
        try:
            text = await self._extractors[ext].extract_async(file_path)
            return CVResult(**common, status=CVStatus.SUCCESS, text=text)
        except Exception as exc:
            # If extraction fails, record the error instead of crashing
            return CVResult(**common, status=CVStatus.ERROR, error_message=str(exc))

    # Process all files concurrently and return the results
    async def extract_all(self, folder_path: str) -> list[CVResult]:
        tasks = [self._process_file(fp) for fp in self._scan_files(folder_path)]
        return list(await asyncio.gather(*tasks))
