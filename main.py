import argparse
import asyncio
import functools
import json
import os
import sys
import time

from extractor import CVExtractorService
from models import CVResult, CVStatus


# Decorator that measures and prints how long an async function takes to run
def timer(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        print(f"\nRuntime: {time.perf_counter() - start:.2f}s")
        return result
    return wrapper


# Print SUCCESS or FAILED status for each file
def _print_status(results: list[CVResult]) -> None:
    for r in results:
        if r.status == CVStatus.SUCCESS:
            status = "SUCCESS"
            print(f"[{status}] {r.file_name}")
        else:
            status = "FAILED"
            print(f"[{status}] {r.file_name} - {r.error_message}")


# Save all results to a JSON file
def _save_json(results: list[CVResult], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([r.model_dump() for r in results], f, ensure_ascii=False, indent=4)


# Set up CLI arguments: --folder (input) and --output (result file)
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cv2text",
        description="Đọc và trích xuất nội dung từ các file CV trong một folder.",
    )
    parser.add_argument("--folder", default="sample_CV", help="Folder chứa CV")             # Thêm tham số --folder để chỉ định folder chứa CV
    parser.add_argument("--output", default="output.json", help="File JSON xuất kết quả")   # thêm tham số --output để chỉ định file JSON xuất kết quả
    return parser


@timer
async def run(args: argparse.Namespace) -> int:
    # Make sure the input folder exists before doing anything
    if not os.path.isdir(args.folder):
        print(f"[LỖI] Folder không tồn tại: {args.folder}", file=sys.stderr)
        return 1

    # Start the extraction process and print the folder being scanned
    print(f"Đang quét folder: {os.path.abspath(args.folder)}")
    results = await CVExtractorService().extract_all(args.folder) 

    # If no supported files were found, print a message and exit without creating an output file
    if not results:
        print("Không tìm thấy file CV nào được hỗ trợ (.pdf, .docx, .doc).")
        return 0

    _save_json(results, args.output)
    print(f"Đã lưu {len(results)} kết quả → {args.output}\n")
    _print_status(results)

    # Print a final summary of how many files succeeded vs failed
    success = sum(1 for r in results if r.status == CVStatus.SUCCESS)
    print(f"\nTổng kết: {success}/{len(results)} [SUCCESS], {len(results) - success}/{len(results)} [FAILED]")
    return 0


def main() -> None:
    sys.exit(asyncio.run(run(build_parser().parse_args())))


if __name__ == "__main__":
    main()

