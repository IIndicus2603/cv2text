from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

        
# Indicates whether text extraction succeeded or failed
class CVStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


# Holds the result of extracting text from one CV file
class CVResult(BaseModel):
    file_name: str = Field(..., description="Tên file CV")                                 
    file_path: str = Field(..., description="Đường dẫn tuyệt đối đến file")                    
    extension: str = Field(..., description="Phần mở rộng của file (.pdf, .docx, .doc)")    
    status: CVStatus = Field(..., description="Trạng thái trích xuất")                      
    text: str = Field(default="", description="Nội dung văn bản đã trích xuất")       
    error_message: Optional[str] = Field(default=None, description="Thông báo lỗi nếu có")

