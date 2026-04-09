# cv2text - Công cụ trích xuất nội dung CV
Đây là một CLI được viết bằng Python, thiết kế để tự động hóa việc quét và trích xuất nội dung văn bản từ hàng loạt CV với các định dạng phổ biến: `.pdf`, `.docx`.

## 🛠 Cấu trúc hệ thống
`main.py`: Chịu trách nhiệm cấu hình CLI (argparse), quản lý luồng thực thi chính và báo cáo kết quả.

`extractor.py`: Sử dụng tính năng Abstraction để xây dựng các bộ trích xuất riêng biệt cho từng loại file, giúp dễ dàng mở rộng thêm các định dạng mới trong tương lai.

`models.py`: Định nghĩa cấu trúc dữ liệu bằng Pydantic. Việc này giúp đảm bảo dữ liệu trích xuất luôn đúng định dạng và hỗ trợ gợi ý code tốt hơn.

## 🚀 Các kỹ thuật đã dùng

### **1. Decorators** ###
   
Chúng ta sử dụng Decorator để can thiệp vào hành vi của hàm một cách linh hoạt:

`@timer`: Là một Custom Decorator dùng để đo thời gian thực thi của các tác vụ bất đồng bộ.

`@abstractmethod`: Đóng vai trò như một quy định bắt buộc. Khi bạn đặt nó ở lớp cha (`BaseExtractor`), bạn đang ra lệnh cho tất cả các lớp con (như `PdfExtractor`, `DocxExtractor`) là: "Bắt buộc phải có hàm extract thì mới được hoạt động!". Điều này giúp kiến trúc code luôn nhất quán.

### **2. Áp dụng BaseModel để chuẩn hóa dữ liệu (Pydantic)** ###
   
Để đảm bảo dữ liệu xuất ra luôn đồng nhất và không bị lỗi vặt, chương trình sử dụng `CVResult(BaseModel)` làm một chiếc "khuôn đúc" dữ liệu:

Bắt buộc nhập đủ và đúng (Data Validation): Các trường như `file_name`, `file_path`, `extension`, và `status` được đánh dấu là bắt buộc (ký hiệu `...`). Nếu thiếu bất kỳ thông tin nào hoặc nhập sai kiểu dữ liệu (ví dụ: truyền số vào ô chữ), Pydantic sẽ chặn lại và báo lỗi ngay lập tức.

### **3. Lập trình bất đồng bộ (Asyncio)** ###

Vì việc đọc file và ghi đĩa là các tác vụ I/O Bound (tiêu tốn thời gian chờ đợi phần cứng hơn là tính toán), chương trình sử dụng thư viện asyncio:

`asyncio.gather(*tasks)`: Thay vì đọc từng file một theo trình tự (file A xong mới đến file B), chúng ta tung tất cả các yêu cầu vào một "vòng lặp sự kiện" (event loop). Các file sẽ được đọc song song, giúp giảm tổng thời gian chờ đợi xuống mức tối thiểu.

`asyncio.to_thread`: Đẩy các công việc nặng nề (như đọc file dung lượng lớn) sang một luồng (thread) phụ chạy ngầm. Việc này giúp giải phóng luồng chính của chương trình, giúp ứng dụng luôn mượt mà, sẵn sàng xử lý hàng loạt file cùng lúc mà không bao giờ bị đứng hình (Blocking).

## 📦 Cài đặt
Khởi tạo môi trường ảo (Virtual Environment):

```Bash
python -m venv venv
venv\Scripts\activate.bat
```
Cài đặt thư viện:

```Bash
pip install -r requirements.txt
```

## 📖 Hướng dẫn sử dụng

```Bash
# Chạy với cấu hình mặc định (Quét folder sample_CV)
python main.py

# Chỉ định folder cụ thể và file xuất kết quả
python main.py --folder [FOLDER] --output [OUTPUT FILE .JSON]
```
## 📊 Kết quả đầu ra
Dữ liệu sẽ được xuất ra file JSON với cấu trúc chuẩn hóa:

`file_name`: Tên file.

`status`: success hoặc error.

`text`: Nội dung thô đã lọc bỏ các cảnh báo hoặc định dạng thừa.

`error_message`: Lý do lỗi chi tiết (nếu file bị hỏng hoặc không đọc được).
