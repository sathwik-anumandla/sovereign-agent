"""
Phase 2 Test Harness: tests/test_tools.py (SIH PS 26117)
=========================================================
Runs standalone test cases per tool to establish a known-good baseline 
prior to orchestrator integration.
"""

import sys
import os
import cv2
import numpy as np
from pathlib import Path

# Add project root directory to python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from tool_interface import ToolStatus
from tools.math_eval import math_eval, MathEvalInput
from tools.file_io import file_io, FileIOInput
from tools.code_sandbox import code_sandbox, CodeSandboxInput
from tools.spreadsheet import spreadsheet, SpreadsheetInput
from tools.doc_gen import doc_gen, DocGenInput
from tools.ocr_vlm import ocr_vlm, OCRVLMInput

SESSION_ID = "test_session_001"
TEST_RESULTS = []


def record_result(tool_name: str, test_name: str, passed: bool, details: str = ""):
    status_str = "[PASS]" if passed else "[FAIL]"
    TEST_RESULTS.append((tool_name, test_name, status_str, details))
    print(f"{status_str} {tool_name} -> {test_name} {f'({details})' if details else ''}")


def test_math_eval_tool():
    print("\n" + "=" * 60)
    print("TESTING TOOL 1: math_eval")
    print("=" * 60)

    # Test 1.1: Evaluation with substitutions
    inp1 = MathEvalInput(expression="2 * x + 5", variables={"x": 10}, mode="evaluate")
    res1 = math_eval(inp1)
    record_result("math_eval", "Evaluate 2*x + 5 (x=10)", res1.status == ToolStatus.SUCCESS and res1.result == "25.0000000000000", f"Result: {res1.result}, Latex: {res1.latex}")

    # Test 1.2: Symbolic Differentiation
    inp2 = MathEvalInput(expression="x**2 + 3*x + 7", variables={"x": 0}, mode="differentiate")
    res2 = math_eval(inp2)
    record_result("math_eval", "Differentiate x^2 + 3x + 7", res2.status == ToolStatus.SUCCESS and "2*x + 3" in res2.result, f"Result: {res2.result}, Steps: {len(res2.steps)}")

    # Test 1.3: Solve Equation
    inp3 = MathEvalInput(expression="x**2 - 16", variables={"x": 0}, mode="solve")
    res3 = math_eval(inp3)
    record_result("math_eval", "Solve x^2 - 16 = 0", res3.status == ToolStatus.SUCCESS and "[-4, 4]" in res3.result, f"Result: {res3.result}")


def test_file_io_tool():
    print("\n" + "=" * 60)
    print("TESTING TOOL 2: file_io")
    print("=" * 60)

    # Test 2.1: Write File in Session Workspace
    inp1 = FileIOInput(operation="write", path="notes/memo.txt", content="Refinery Unit 2 Inspection Report\nStatus: Approved", session_id=SESSION_ID)
    res1 = file_io(inp1)
    record_result("file_io", "Write workspace file (notes/memo.txt)", res1.status == ToolStatus.SUCCESS, f"Path: {res1.path}")

    # Test 2.2: Read File from Workspace
    inp2 = FileIOInput(operation="read", path="notes/memo.txt", session_id=SESSION_ID)
    res2 = file_io(inp2)
    record_result("file_io", "Read workspace file", res2.status == ToolStatus.SUCCESS and "Refinery Unit 2" in (res2.content or ""), f"Content length: {len(res2.content or '')}")

    # Test 2.3: Security Boundary Check (Path Traversal Attempt MUST FAIL)
    inp3 = FileIOInput(operation="read", path="../../etc/passwd", session_id=SESSION_ID)
    res3 = file_io(inp3)
    record_result("file_io", "Path Traversal Security Boundary Guard", res3.status == ToolStatus.ERROR and "Security" in (res3.error or ""), f"Caught Error: {res3.error}")


def test_code_sandbox_tool():
    print("\n" + "=" * 60)
    print("TESTING TOOL 3: code_sandbox")
    print("=" * 60)

    # Test 3.1: Python calculation script execution
    code1 = """
import math
radius = 6.0
area = math.pi * radius**2
print(f"Calculated Pipe Area: {area:.2f} sq inches")
"""
    inp1 = CodeSandboxInput(code=code1, language="python", timeout_s=5, session_id=SESSION_ID)
    res1 = code_sandbox(inp1)
    record_result("code_sandbox", "Execute Python Calculation Script", res1.status == ToolStatus.SUCCESS and "Calculated Pipe Area: 113.10" in res1.stdout, f"Stdout: {res1.stdout.strip()}")

    # Test 3.2: Timeout Protection Guard
    code2 = """
import time
print("Starting heavy processing...")
time.sleep(10)
print("Finished!")
"""
    inp2 = CodeSandboxInput(code=code2, language="python", timeout_s=2, session_id=SESSION_ID)
    res2 = code_sandbox(inp2)
    record_result("code_sandbox", "Hard Timeout Guard (2s)", res2.status in {ToolStatus.ERROR, ToolStatus.PARTIAL} and "timed out" in (res2.stderr or "").lower(), f"Stderr: {res2.stderr.strip()}")


def test_spreadsheet_tool():
    print("\n" + "=" * 60)
    print("TESTING TOOL 4: spreadsheet")
    print("=" * 60)

    # Setup test CSV file via file_io
    csv_content = """Equipment,Pressure_PSI,Flow_GPM,Status
Pump_101,150,450,Active
Pump_102,210,520,Active
Valve_201,80,120,Maintenance
Pump_103,180,490,Active
"""
    file_io(FileIOInput(operation="write", path="data/pumps.csv", content=csv_content, session_id=SESSION_ID))

    # Test 4.1: Read spreadsheet data
    inp1 = SpreadsheetInput(file_path="data/pumps.csv", operation="read", params={"limit": 5}, session_id=SESSION_ID)
    res1 = spreadsheet(inp1)
    record_result("spreadsheet", "Read CSV Data", res1.status == ToolStatus.SUCCESS and len(res1.data or []) == 4, f"Read {len(res1.data or [])} rows")

    # Test 4.2: Filter rows
    inp2 = SpreadsheetInput(file_path="data/pumps.csv", operation="filter", params={"column": "Pressure_PSI", "operator": ">", "value": 160}, session_id=SESSION_ID)
    res2 = spreadsheet(inp2)
    record_result("spreadsheet", "Filter rows (Pressure_PSI > 160)", res2.status == ToolStatus.SUCCESS and len(res2.data or []) == 2, f"Matching rows: {len(res2.data or [])}")

    # Test 4.3: Aggregate column
    inp3 = SpreadsheetInput(file_path="data/pumps.csv", operation="aggregate", params={"column": "Flow_GPM", "function": "sum"}, session_id=SESSION_ID)
    res3 = spreadsheet(inp3)
    record_result("spreadsheet", "Aggregate sum(Flow_GPM)", res3.status == ToolStatus.SUCCESS and res3.data[0]["sum_Flow_GPM"] == 1580.0, f"Summary: {res3.summary}")


def test_doc_gen_tool():
    print("\n" + "=" * 60)
    print("TESTING TOOL 5: doc_gen")
    print("=" * 60)

    # Test 5.1: Generate Word Document (.docx)
    docx_spec = {
        "title": "MRPL Refinery Inspection Approval Note",
        "sections": [
            {"heading": "Executive Summary", "body": "Inspection of Crude Distillation Unit (CDU-2) completed with zero critical defects."},
            {"headers": ["Equipment ID", "Pressure (PSI)", "Status"], "rows": [["Pump-101", "150", "Approved"], ["Valve-201", "80", "Maintenance Required"]]}
        ]
    }
    inp1 = DocGenInput(format="docx", spec=docx_spec, output_path="reports/approval_note.docx", session_id=SESSION_ID)
    res1 = doc_gen(inp1)
    record_result("doc_gen", "Generate Word (.docx) Deliverable", res1.status == ToolStatus.SUCCESS and res1.output_path is not None, f"Output: {res1.output_path}")

    # Test 5.2: Generate Excel Document (.xlsx)
    xlsx_spec = {
        "sheets": [
            {
                "name": "Pressure Data",
                "data": [
                    ["Unit", "Pressure_PSI"],
                    ["CDU-1", 140],
                    ["CDU-2", 185],
                    ["CDU-3", 210]
                ]
            }
        ]
    }
    inp2 = DocGenInput(format="xlsx", spec=xlsx_spec, output_path="reports/pressure_log.xlsx", session_id=SESSION_ID)
    res2 = doc_gen(inp2)
    record_result("doc_gen", "Generate Excel (.xlsx) Deliverable", res2.status == ToolStatus.SUCCESS and res2.output_path is not None, f"Output: {res2.output_path}")

    # Test 5.3: Generate PowerPoint Slides (.pptx)
    pptx_spec = {
        "slides": [
            {
                "title": "Quarterly Operations Review",
                "blocks": [
                    {"heading": "Key Milestones", "body": "Achieved 99.8% refinery uptime across all major processing loops."}
                ]
            }
        ]
    }
    inp3 = DocGenInput(format="pptx", spec=pptx_spec, output_path="reports/review_presentation.pptx", session_id=SESSION_ID)
    res3 = doc_gen(inp3)
    record_result("doc_gen", "Generate PowerPoint (.pptx) Deliverable", res3.status == ToolStatus.SUCCESS and res3.output_path is not None, f"Output: {res3.output_path}")


def test_ocr_vlm_tool():
    print("\n" + "=" * 60)
    print("TESTING TOOL 6: ocr_vlm")
    print("=" * 60)

    img_path = Path(ROOT_DIR) / "workspace" / SESSION_ID / "test_diagram.png"
    img_path.parent.mkdir(parents=True, exist_ok=True)

    dummy_img = np.full((300, 600, 3), 255, dtype=np.uint8)
    cv2.putText(dummy_img, "MRPL P&ID VALVE V-209", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    cv2.imwrite(str(img_path), dummy_img)

    # Test 6.1: Run Diagram Analysis
    inp1 = OCRVLMInput(file_path="test_diagram.png", input_type="diagram", extract_mode="describe", session_id=SESSION_ID)
    res1 = ocr_vlm(inp1)
    engine_used = res1.metadata.get("engine_used")
    conf = res1.metadata.get("confidence")
    record_result("ocr_vlm", "P&ID Diagram Analysis", res1.status == ToolStatus.SUCCESS and engine_used == "vlm", f"Engine: {engine_used}, Confidence: {conf}")

    # Test 6.2: Run Text Extraction
    inp2 = OCRVLMInput(file_path="test_diagram.png", input_type="printed", extract_mode="text", session_id=SESSION_ID)
    res2 = ocr_vlm(inp2)
    engine_used_2 = res2.metadata.get("engine_used")
    record_result("ocr_vlm", "Printed Document Text Extraction", res2.status == ToolStatus.SUCCESS, f"Engine: {engine_used_2}")


if __name__ == "__main__":
    print("\n" + "#" * 65)
    print("PHASE 2 STANDALONE AGENT TOOL LAYER SUITE - TEST HARNESS")
    print("#" * 65)

    test_math_eval_tool()
    test_file_io_tool()
    test_code_sandbox_tool()
    test_spreadsheet_tool()
    test_doc_gen_tool()
    test_ocr_vlm_tool()

    print("\n" + "#" * 65)
    print("FINAL TEST HARNESS SUMMARY")
    print("#" * 65)

    total_tests = len(TEST_RESULTS)
    passed_tests = sum(1 for r in TEST_RESULTS if "[PASS]" in r[2])
    failed_tests = total_tests - passed_tests

    for tool, name, status, details in TEST_RESULTS:
        print(f"{status} | {tool:<15} | {name:<45} | {details}")

    print("\n" + "-" * 65)
    print(f"Total: {total_tests} | Passed: {passed_tests} | Failed: {failed_tests}")
    if failed_tests == 0:
        print("ALL 6 STANDALONE AGENT TOOLS PASSED 100% OF TEST CASES!")
    print("-" * 65 + "\n")
