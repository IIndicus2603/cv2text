import argparse
import asyncio
import functools
import json
import logging
import os
import sys
import time

from extractor import CVExtractorService
from models import CVResult, CVStatus


_NOISY_LIBS = ("pdfminer", "pdfplumber", "docx", "PIL", "fonttools")

_RED   = "\033[31m"
_RESET = "\033[0m"


class _ColorFormatter(logging.Formatter):
    # Change log color based on level: red for ERROR and above, default for others
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        if record.levelno >= logging.ERROR:
            return f"{_RED}{msg}{_RESET}"
        return msg


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(_ColorFormatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    ))
    # Pass handler explicitly
    logging.basicConfig(level=level, handlers=[handler])
    
    # Libs flood DEBUG with internal parsing details so cap them at WARNING
    for lib in _NOISY_LIBS:
        logging.getLogger(lib).setLevel(logging.WARNING)


# Decorator that measures and prints how long an async function takes to run
def timer(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        print(f"\nRuntime: {time.perf_counter() - start:.2f}s")
        return result
    return wrapper


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
    parser.add_argument("--folder", "-f", default="sample_CV", help="Folder chứa CV")
    parser.add_argument("--output", "-o", default="output.json", help="File JSON xuất kết quả")
    parser.add_argument("--verbose", "-v", action="store_true", help="Hiển thị log chi tiết (DEBUG)")
    return parser


@timer
async def run(args: argparse.Namespace) -> int:
    # Make sure the input folder exists before doing anything
    if not os.path.isdir(args.folder):
        print(f"[ERROR] Folder không tồn tại: {args.folder}", file=sys.stderr)
        return 1

    # Start the extraction process and print the folder being scanned
    print(f"Đang quét folder: {os.path.abspath(args.folder)}")
    results = await CVExtractorService().extract_all(args.folder) 

    # If no supported files were found, print a message and exit without creating an output file
    if not results:
        print("Không tìm thấy file CV nào được hỗ trợ (.pdf, .docx).")
        return 0

    _save_json(results, args.output)
    print(f"Đã lưu {len(results)} kết quả vào {args.output}\n")

    # Print a final summary of how many files succeeded vs failed
    success = sum(1 for r in results if r.status == CVStatus.SUCCESS)
    print(f"Tổng kết: {success}/{len(results)} [SUCCESS], {len(results) - success}/{len(results)} [FAILED]")
    return 0


def main() -> None:
    args = build_parser().parse_args()
    _setup_logging(args.verbose)
    sys.exit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()

