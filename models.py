from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CVStatus(str, Enum):
    """Trạng thái của kết quả trích xuất CV."""
    SUCCESS = "success"
    ERROR = "error"


class CVResult(BaseModel):
    """Mô hình dữ liệu cho kết quả trích xuất CV."""
    file_name: str = Field(..., description="Tên file CV")                                 
    file_path: str = Field(..., description="Đường dẫn tuyệt đối đến file")                    
    extension: str = Field(..., description="Phần mở rộng của file (.pdf, .docx, .doc)")    
    status: CVStatus = Field(..., description="Trạng thái trích xuất")                      
    text: str = Field(default="", description="Nội dung văn bản đã trích xuất")       
    error_message: Optional[str] = Field(default=None, description="Thông báo lỗi nếu có")

