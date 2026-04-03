import asyncio
import glob
import os
import tempfile
from abc import ABC, abstractmethod

from docx import Document
import pdfplumber
from spire.doc import Document as SpireDocument, FileFormat as SpireFileFormat

from models import CVResult, CVStatus


class BaseExtractor(ABC):
    """Lớp trừu tượng định nghĩa giao diện chung cho tất cả extractor."""
    @abstractmethod
    def extract(self, file_path: str) -> str: ...
    """Hàm đồng bộ để đọc file và trả về chuỗi văn bản."""

    """Hàm bất đồng bộ để gọi hàm extract trong một luồng riêng biệt."""
    async def extract_async(self, file_path: str) -> str:
        return await asyncio.to_thread(self.extract, file_path)


class PdfExtractor(BaseExtractor):
    """Sử dụng pdfplumber để trích xuất văn bản từ file PDF."""
    def extract(self, file_path: str) -> str:
        parts = []
        # Mở file PDF
        with pdfplumber.open(file_path) as pdf:
            # Duyệt qua từng trang và trích xuất văn bản
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    parts.append(page_text)
        # Kết hợp tất cả văn bản từ các trang lại với nhau và loại bỏ khoảng trắng thừa
        return "\n".join(parts).strip()


class DocxExtractor(BaseExtractor):
    """Sử dụng python-docx để trích xuất văn bản từ file DOCX."""
    def extract(self, file_path: str) -> str:
        doc = Document(file_path)
        # Kết hợp tất cả văn bản từ các đoạn (paragraph) lại với nhau và loại bỏ khoảng trắng thừa
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()


class DocExtractor(BaseExtractor):
    """Dùng spire.doc để convert file DOC sang PDF tạm, sau đó dùng PdfExtractor để trích xuất văn bản."""
    def extract(self, file_path: str) -> str:
        # Tạo file PDF tạm để lưu kết quả convert từ DOC
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            doc = SpireDocument()
            doc.LoadFromFile(file_path)
            doc.SaveToFile(tmp_path, SpireFileFormat.PDF)
            doc.Close()
            text = PdfExtractor().extract(tmp_path)
            # Loại bỏ dòng cảnh báo evaluation của Spire.Doc
            lines = [
                line for line in text.splitlines()
                if "Evaluation Warning" not in line and "Spire.Doc for Python" not in line
            ]
            return "\n".join(lines).strip()
        finally:
            # Xóa file PDF tạm sau khi đã trích xuất xong
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


# Dictionary phân loại file với extractor tương ứng
EXTRACTOR_MAP: dict[str, BaseExtractor] = {
    ".pdf": PdfExtractor(),
    ".docx": DocxExtractor(),
    ".doc": DocExtractor(),
}


class CVExtractorService:
    """Service chính để quét folder, xác định loại file và trích xuất văn bản."""
    def __init__(self):
        self._extractors = EXTRACTOR_MAP

    def _scan_files(self, folder_path: str) -> list[str]:
        """Quét folder và trả về danh sách đường dẫn tuyệt đối của tất cả file được hỗ trợ."""
        pattern = os.path.join(folder_path, "**", "*")
        # Sử dụng glob để tìm tất cả file phù hợp với pattern, sau đó lọc ra chỉ những file thực sự tồn tại
        return sorted(
            f for f in glob.glob(pattern, recursive=True) if os.path.isfile(f)
        )

    async def _process_file(self, file_path: str) -> CVResult | None:
        """Xác định loại file, trích xuất văn bản và trả về kết quả."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self._extractors:
            # Nếu đuôi file không được hỗ trợ thì bỏ qua
            return None
        try:
            # Gọi hàm trích xuất bất đồng bộ của extractor tương ứng
            text = await self._extractors[ext].extract_async(file_path)
            # Trả về kết quả thành công
            return CVResult(
                file_name=os.path.basename(file_path),
                file_path=os.path.abspath(file_path),
                extension=ext,
                status=CVStatus.SUCCESS,
                text=text,
            )
        except Exception as exc:
            # Trả về kết quả lỗi nếu có ngoại lệ xảy ra trong quá trình trích xuất
            return CVResult(
                file_name=os.path.basename(file_path),
                file_path=os.path.abspath(file_path),
                extension=ext,
                status=CVStatus.ERROR,
                text="",
                error_message=str(exc),
            )

    async def extract_all(self, folder_path: str) -> list[CVResult]:
        """Quét folder, trích xuất văn bản từ tất cả file được hỗ trợ và trả về danh sách kết quả."""
        # 1. Quét folder để lấy danh sách file
        # 2. Tạo một task bất đồng bộ cho mỗi file để xử lý song song
        tasks = [self._process_file(fp) for fp in self._scan_files(folder_path)]

        # 3. Chạy ĐỒNG THỜI tất cả các task bằng asyncio.gather
        results = await asyncio.gather(*tasks)

        # 4. Lọc bỏ những kết quả None (tức là những file không được hỗ trợ) và trả về danh sách kết quả cuối cùng
        return [r for r in results if r is not None]
