import asyncio
import glob
import logging
import os
import time
from abc import ABC, abstractmethod

from docx import Document
import pdfplumber

from models import CVResult, CVStatus

logger = logging.getLogger(__name__)


# Base class for all extractors — defines the common interface
class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: str) -> str: ...

    # Run extract() in a separate thread so it doesn't block the event loop
    async def extract_async(self, file_path: str) -> str:
        name = os.path.basename(file_path)
        logger.debug("[extract_async] transferring '%s' to a separate thread", name)
        result = await asyncio.to_thread(self.extract, file_path)
        return result


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


# Maps file extensions to the correct extractor instance
EXTRACTOR_MAP: dict[str, BaseExtractor] = {
    ".pdf": PdfExtractor(),
    ".docx": DocxExtractor(),
}

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(EXTRACTOR_MAP)


# Main service that scans a folder and extracts text from all CV files
class CVExtractorService:
    def __init__(self):
        self._extractors = EXTRACTOR_MAP

    # Recursively find all files inside the folder
    def _scan_files(self, folder_path: str) -> list[str]:
        pattern = os.path.join(folder_path, "**", "*")
        all_files = [f for f in glob.glob(pattern, recursive=True) if os.path.isfile(f)]

        # filter out unsupported files
        supported, skipped = [], []
        for f in all_files:
            if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS:
                supported.append(f)
            else:
                skipped.append(f)

        # Log the skipped files
        if skipped:
            logger.info("Skipped %d unsupported file(s): %s", len(skipped), [os.path.basename(f) for f in skipped])

        # Log the supported files found and return them sorted
        logger.info("Found %d supported file(s) to process.", len(supported))
        return sorted(supported)

    # Process a single file — picks the right extractor based on extension
    async def _process_file(self, file_path: str) -> CVResult:
        ext = os.path.splitext(file_path)[1].lower()
        common = dict(
            file_name=os.path.basename(file_path),
            file_path=os.path.abspath(file_path), 
            extension=ext,
        )
        fname = common["file_name"]
        logger.debug("[_process_file] awaiting extract_async('%s')", fname)
        
        try:
            # Measure how long the extraction takes for this file
            t0 = time.perf_counter()
            text = await self._extractors[ext].extract_async(file_path)
            elapsed = time.perf_counter() - t0
            logger.debug("[_process_file] Completed extract '%s' Runtime: %.2fs (%d chars)", fname, elapsed, len(text))
            return CVResult(**common, status=CVStatus.SUCCESS, text=text)
        
        except Exception as exc:
            # Log the error if extraction fails
            logger.error("[_process_file] Failed to extract '%s'", fname)
            return CVResult(**common, status=CVStatus.ERROR, error_message=str(exc))

    # Process all files concurrently and return the results
    async def extract_all(self, folder_path: str) -> list[CVResult]:
        files = self._scan_files(folder_path)
        if not files:
            return []

        tasks = [self._process_file(fp) for fp in files]
        logger.debug("[extract_all] gathering %d tasks to run concurrently", len(tasks))
        t0 = time.perf_counter()
        results = list(await asyncio.gather(*tasks))
        logger.debug("[extract_all] all %d tasks completed in %.2fs", len(tasks), time.perf_counter() - t0)

        success = sum(1 for r in results if r.status == CVStatus.SUCCESS)
        logger.info("Extraction complete: %d/%d succeeded.", success, len(results))
        return results