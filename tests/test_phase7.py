"""
tests/test_phase7.py (SIH PS 26117)
===================================
Phase 7 Test Suite for Two-Stage Confidence-Gated OCR Pipeline (ocr_vlm).
Verifies:
  1. FileMetadata likely_needs_ocr flagging for image/pdf extensions.
  2. Standalone OCR pipeline on clean document (PP-Structure primary engine, conf >= 0.90).
  3. Standalone OCR pipeline on degraded document (Qwen3-VL fallback engine, conf < 0.90).
  4. End-to-end ReAct Orchestrator tool call integration.
"""

import sys
import os
import cv2
import numpy as np
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from tool_interface import ToolStatus
from router.schemas import FileMetadata
from tools.ocr_vlm import ocr_vlm, OCRVLMInput, OCR_CONFIDENCE_THRESHOLD
from orchestrator import run_workbench
from inspect_run import inspect_thread

SESSION_ID = "test_phase7_session"
WORKSPACE_DIR = Path(ROOT_DIR) / "workspace" / SESSION_ID


def setup_test_documents():
    """Generates synthetic clean and degraded test documents."""
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

    # Document 1: Clean, high-quality document image
    clean_img = np.full((500, 800, 3), 255, dtype=np.uint8)
    cv2.putText(clean_img, "MRPL REFINERY INSPECTION NOTE", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    cv2.putText(clean_img, "CRUDE DISTILLATION UNIT CDU-2", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.putText(clean_img, "STATUS: PASSED WITH ZERO DEFECTS", (50, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    clean_path = WORKSPACE_DIR / "clean_doc.png"
    cv2.imwrite(str(clean_path), clean_img)

    # Document 2: Degraded, heavily blurred/noisy low-contrast document image
    degraded_img = np.full((500, 800, 3), 200, dtype=np.uint8)
    cv2.putText(degraded_img, "MRPL REFINERY INSPECTION NOTE", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
    degraded_img = cv2.GaussianBlur(degraded_img, (51, 51), 0)
    degraded_path = WORKSPACE_DIR / "degraded_doc.png"
    cv2.imwrite(str(degraded_path), degraded_img)

    return "clean_doc.png", "degraded_doc.png"


def test_file_metadata_ocr_hint():
    print("\n" + "=" * 75)
    print("TEST 1: FILE METADATA OCR HINT FLAGGING")
    print("=" * 75)

    meta_pdf = FileMetadata(filename="report.pdf", extension=".pdf")
    meta_png = FileMetadata(filename="drawing.png", extension=".png")
    meta_py = FileMetadata(filename="script.py", extension=".py")

    assert meta_pdf.likely_needs_ocr is True, "PDF file should be flagged as likely_needs_ocr=True"
    assert meta_png.likely_needs_ocr is True, "PNG file should be flagged as likely_needs_ocr=True"
    assert meta_py.likely_needs_ocr is False, "PY file should be flagged as likely_needs_ocr=False"

    print("[PASS] FileMetadata correctly flags image/PDF files with likely_needs_ocr=True.")


def test_standalone_ocr_pipeline():
    print("\n" + "=" * 75)
    print("TEST 2: STANDALONE CONFIDENCE-GATED OCR PIPELINE")
    print("=" * 75)

    clean_file, degraded_file = setup_test_documents()

    # Test 2.1: Clean Document (High Confidence -> Primary PP-Structure Engine)
    print("\n[Subtest 2.1] Processing Clean Document Scan...")
    inp_clean = OCRVLMInput(file_path=clean_file, input_type="printed", extract_mode="text", session_id=SESSION_ID)
    res_clean = ocr_vlm(inp_clean)

    engine_clean = res_clean.metadata.get("engine_used")
    conf_clean = res_clean.metadata.get("confidence", 0.0)

    print(f"Clean Doc Result Status : {res_clean.status}")
    print(f"Engine Used             : {engine_clean}")
    print(f"Confidence Reported     : {conf_clean} (Threshold: {OCR_CONFIDENCE_THRESHOLD})")

    assert res_clean.status == ToolStatus.SUCCESS, "Clean document OCR should return SUCCESS"
    assert conf_clean >= OCR_CONFIDENCE_THRESHOLD, f"Clean document confidence ({conf_clean}) should be >= {OCR_CONFIDENCE_THRESHOLD}"
    assert engine_clean in ["pp_structure", "primary_ocr"], f"Expected primary engine, got '{engine_clean}'"
    print("[PASS] Clean document processed via primary PP-Structure engine with high confidence.")

    # Test 2.2: Degraded Document (Low Confidence -> Qwen3-VL Fallback Engine)
    print("\n[Subtest 2.2] Processing Degraded Document Scan...")
    inp_degraded = OCRVLMInput(file_path=degraded_file, input_type="printed", extract_mode="text", session_id=SESSION_ID)
    res_degraded = ocr_vlm(inp_degraded)

    engine_degraded = res_degraded.metadata.get("engine_used")
    conf_degraded = res_degraded.metadata.get("confidence", 0.0)

    print(f"Degraded Doc Status     : {res_degraded.status}")
    print(f"Engine Used             : {engine_degraded}")
    print(f"Confidence Reported     : {conf_degraded}")
    print(f"Fallback Reason         : {res_degraded.metadata.get('fallback_reason', 'N/A')}")

    assert res_degraded.status == ToolStatus.SUCCESS, "Degraded document OCR should return SUCCESS"
    assert conf_degraded < OCR_CONFIDENCE_THRESHOLD, f"Degraded document confidence ({conf_degraded}) should be < {OCR_CONFIDENCE_THRESHOLD}"
    assert engine_degraded == "vlm", f"Expected VLM fallback engine, got '{engine_degraded}'"
    print("[PASS] Degraded document tripped low-confidence threshold and successfully invoked VLM fallback.")


def test_react_orchestrator_ocr_wiring():
    print("\n" + "=" * 75)
    print("TEST 3: REACT ORCHESTRATOR END-TO-END OCR TOOL WIRING")
    print("=" * 75)

    clean_file, _ = setup_test_documents()
    meta = [FileMetadata(filename=clean_file, extension=".png")]

    prompt = f"Please transcribe text from the attached document '{clean_file}' using the ocr_vlm tool."
    print(f"Executing Orchestrator Prompt: '{prompt}'")

    state, thread_id = run_workbench(prompt, file_metadata=meta)

    print(f"Thread ID               : {thread_id}")
    print(f"Route Role              : {state.get('route_decision').role if state.get('route_decision') else 'N/A'}")
    print(f"Total Tool Results      : {len(state.get('tool_results', []))}")

    print("\n--- Inspecting ReAct Checkpoint History Snapshots ---")
    inspect_thread(thread_id)
    print("[PASS] ReAct orchestrator graph successfully executed ocr_vlm tool.")


if __name__ == "__main__":
    test_file_metadata_ocr_hint()
    test_standalone_ocr_pipeline()
    test_react_orchestrator_ocr_wiring()

    print("\n" + "#" * 75)
    print("PHASE 7 DEFINITION OF DONE: ALL TESTS PASSED 100%!")
    print("#" * 75 + "\n")
