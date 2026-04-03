import argparse
import asyncio
import functools
import json
import os
import sys
import time

from extractor import CVExtractorService
from models import CVResult, CVStatus

# Hàm decorator để đo thời gian thực thi của hàm bất đồng bộ
def timer(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        print(f"\nThời gian xử lý: {time.perf_counter() - start:.2f}s")
        return result
    return wrapper

# Hàm để in status ra console
def _print_status(results: list[CVResult]) -> None:
    for r in results:
        if r.status == CVStatus.SUCCESS:
            status = "SUCCESS" 
            print(f"[{status}] {r.file_name}")
        else:
            status = "FAILED"
            print(f"[{status}] {r.file_name} - {r.error_message}")
    
# Hàm để lưu kết quả vào file JSON
def _save_json(results: list[CVResult], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([r.model_dump() for r in results], f, ensure_ascii=False, indent=4)

# Hàm để xây dựng parser cho CLI
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cv_reader",
        description="Đọc và trích xuất nội dung từ các file CV trong một folder.",
    )
    parser.add_argument("--folder", default="sample_CV", help="Folder chứa CV")
    parser.add_argument("--output", default="output.json", help="File JSON xuất kết quả")
    return parser

# Hàm chính để chạy chương trình
@timer
async def run(args: argparse.Namespace) -> int:
    """Kiểm tra folder, chạy service trích xuất và xử lý kết quả."""
    if not os.path.isdir(args.folder):
        print(f"[LỖI] Folder không tồn tại: {args.folder}", file=sys.stderr)
        return 1

    # Bắt đầu quét folder và trích xuất văn bản từ các file CV
    print(f"Đang quét folder: {os.path.abspath(args.folder)}")
    results = await CVExtractorService().extract_all(args.folder) 

    # Nếu không tìm thấy file nào được hỗ trợ thì thông báo và kết thúc
    if not results:
        print("Không tìm thấy file CV nào được hỗ trợ (.pdf, .docx, .doc).")
        return 0

    # Lưu kết quả vào file JSON và in ra console
    _save_json(results, args.output)
    print(f"Đã lưu {len(results)} kết quả → {args.output}\n")
    _print_status(results)

    success = sum(1 for r in results if r.status == CVStatus.SUCCESS)
    print(f"\nTổng kết: {success} thành công, {len(results) - success} lỗi.")
    return 0

# Hàm main để chạy chương trình
def main() -> None:
    sys.exit(asyncio.run(run(build_parser().parse_args())))


if __name__ == "__main__":
    main()

