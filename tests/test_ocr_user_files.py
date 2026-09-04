"""
tests/test_ocr_user_files.py (SIH PS 26117)
============================================
Test script to run ocr_vlm confidence-gated pipeline against user-provided PDF files:
  - ignore-files/ocr-test/test-1.pdf
  - ignore-files/ocr-test/test-2.pdf
  - ignore-files/ocr-test/test-3.pdf
"""

import sys
import os
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from tool_interface import ToolStatus
from tools.ocr_vlm import ocr_vlm, OCRVLMInput, OCR_CONFIDENCE_THRESHOLD

TEST_FILES = [
    "ignore-files/ocr-test/test-1.pdf",
    "ignore-files/ocr-test/test-2.pdf",
    "ignore-files/ocr-test/test-3.pdf",
]


def test_user_ocr_pdfs():
    print("\n" + "=" * 75)
    print("RUNNING CONFIDENCE-GATED OCR PIPELINE ON USER TEST PDFS")
    print("=" * 75)

    for pdf_path in TEST_FILES:
        full_path = Path(ROOT_DIR) / pdf_path
        if not full_path.exists():
            print(f"[SKIP] File not found: {pdf_path}")
            continue

        print(f"\n--- Testing Document: {pdf_path} ---")
        inp = OCRVLMInput(file_path=str(pdf_path), input_type="printed", extract_mode="text")
        res = ocr_vlm(inp)

        status_str = "[PASS]" if res.status == ToolStatus.SUCCESS else "[FAIL]"
        engine_used = res.metadata.get("engine_used", "N/A")
        confidence = res.metadata.get("confidence", 0.0)
        pages = res.metadata.get("pages_processed", 1)
        extracted_result = res.metadata.get("result", "")

        print(f"Status           : {status_str} ({res.status})")
        print(f"Engine Used      : {engine_used}")
        print(f"Confidence Score : {confidence} (Threshold: {OCR_CONFIDENCE_THRESHOLD})")
        print(f"Pages Processed  : {pages}")
        
        result_preview = str(extracted_result or "").strip()
        if result_preview:
            preview = result_preview[:150] + "..." if len(result_preview) > 150 else result_preview
            print(f"Extracted Output : '{preview}'")
        elif res.error:
            print(f"Error            : {res.error}")

    print("\n" + "=" * 75 + "\n")


if __name__ == "__main__":
    test_user_ocr_pdfs()
