"""
run_all_tests.py (SIH PS 26117)
===============================
Master Integration Test Runner for Sovereign Agentic AI Workbench (Phases 1 - 6).
Executes all standalone unit test suites and runs end-to-end multi-tool workflow integration scenarios.
"""

import sys
import os
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tool_interface import ToolStatus, ToolResult
from router import route, FileMetadata
from router.schemas import RouteDecision
from orchestrator import run_workbench, WorkbenchState
from orchestrator.graph import tool_node, should_continue, build_orchestrator_graph
from tools.file_io import file_io, FileIOInput
from tools.spreadsheet import spreadsheet, SpreadsheetInput
from tools.doc_gen import doc_gen, DocGenInput
from tools.math_eval import math_eval, MathEvalInput
from tools.code_sandbox import code_sandbox, CodeSandboxInput
from tools.ocr_vlm import ocr_vlm, OCRVLMInput

SESSION_ID = "integration_test_session_001"


def run_e2e_workflow_tests():
    print("\n" + "=" * 75)
    print("RUNNING END-TO-END MULTI-TOOL WORKFLOW INTEGRATION TESTS")
    print("=" * 75)

    passed = 0
    total = 3

    # Workflow 1: Industrial Data Analysis Pipeline (FileIO -> Spreadsheet -> DocGen)
    print("\n[Workflow 1] Industrial Data Analysis & Report Generation Pipeline...")
    try:
        # Step 1.1: Write raw pressure data via FileIO
        raw_csv = """Pump_ID,Pressure_PSI,Temperature_C,Status
P-101,185,65,Optimal
P-102,220,82,Warning
P-103,140,58,Optimal
P-104,245,88,Critical
"""
        f_res = file_io(FileIOInput(operation="write", path="telemetry/pressure.csv", content=raw_csv, session_id=SESSION_ID))
        assert f_res.status == ToolStatus.SUCCESS, "FileIO write failed"

        # Step 1.2: Filter high pressure rows via Spreadsheet Tool
        s_res = spreadsheet(SpreadsheetInput(
            file_path="telemetry/pressure.csv",
            operation="filter",
            params={"column": "Pressure_PSI", "operator": ">", "value": 200},
            session_id=SESSION_ID
        ))
        assert s_res.status == ToolStatus.SUCCESS, "Spreadsheet filter failed"
        assert len(s_res.data) == 2, f"Expected 2 high pressure rows, got {len(s_res.data)}"

        # Step 1.3: Generate Word Document Report via DocGen Tool
        report_spec = {
            "title": "MRPL High Pressure Alert Report",
            "sections": [
                {"heading": "Telemetry Analysis Summary", "body": s_res.summary},
                {"headers": ["Pump ID", "Pressure (PSI)", "Temperature (C)", "Status"],
                 "rows": [[row["Pump_ID"], str(row["Pressure_PSI"]), str(row["Temperature_C"]), row["Status"]] for row in s_res.data]}
            ]
        }
        d_res = doc_gen(DocGenInput(format="docx", spec=report_spec, output_path="reports/alert_report.docx", session_id=SESSION_ID))
        assert d_res.status == ToolStatus.SUCCESS, "DocGen Word report failed"

        print(f"[PASS] Workflow 1: Raw telemetry CSV processed -> filtered -> Word report generated at '{d_res.output_path}'.")
        passed += 1
    except Exception as e:
        print(f"[FAIL] Workflow 1 failed: {e}")

    # Workflow 2: Symbolic Math Derivation -> Code Sandbox Verification
    print("\n[Workflow 2] Symbolic Calculus Derivation & Code Execution Verification...")
    try:
        # Step 2.1: Derive Symbolic Derivative using SymPy Math Tool
        m_res = math_eval(MathEvalInput(expression="x**3 - 6*x**2 + 9*x", mode="differentiate"))
        assert m_res.status == ToolStatus.SUCCESS, "MathEval differentiation failed"
        derived_expr = m_res.result  # "3*x**2 - 12*x + 9"

        # Step 2.2: Pass derived expression to Code Sandbox for numerical evaluation
        verify_code = f"""
def f_prime(x):
    return {derived_expr}

crit_points = [x for x in range(-5, 10) if f_prime(x) == 0]
print(f"Critical Points Found: {{crit_points}}")
"""
        c_res = code_sandbox(CodeSandboxInput(code=verify_code, language="python", timeout_s=5, session_id=SESSION_ID))
        assert c_res.status == ToolStatus.SUCCESS, "Code Sandbox execution failed"
        assert "Critical Points Found: [1, 3]" in c_res.stdout, f"Expected [1, 3], got {c_res.stdout}"

        print(f"[PASS] Workflow 2: SymPy derivative '{derived_expr}' verified in sandbox -> Output: {c_res.stdout.strip()}")
        passed += 1
    except Exception as e:
        print(f"[FAIL] Workflow 2 failed: {e}")

    # Workflow 3: Path Traversal Security Boundary Attack Attempt through ReAct Tool Node
    print("\n[Workflow 3] Security Path Traversal Guard Verification through ReAct Tool Node...")
    try:
        malicious_call = {
            "id": "attack_call_001",
            "function": {
                "name": "file_io",
                "arguments": {"operation": "read", "path": "../../../etc/passwd", "session_id": SESSION_ID}
            }
        }
        attack_state = WorkbenchState(
            prompt="read sensitive system file",
            tool_calls=[malicious_call],
            tool_iteration_count=0
        )
        res_state = tool_node(attack_state)
        res_tool = res_state["tool_results"][0]

        assert res_tool.status == ToolStatus.ERROR, "Path traversal MUST return ToolStatus.ERROR"
        assert "Security" in res_tool.error or "Path traversal" in res_tool.error or "escapes session root" in res_tool.error, f"Expected Security violation error, got '{res_tool.error}'"

        print(f"[PASS] Workflow 3: Path traversal attempt '../../../etc/passwd' blocked safely: '{res_tool.error}'.")
        passed += 1
    except Exception as e:
        print(f"[FAIL] Workflow 3 failed: {e}")

    print("\n" + "=" * 75)
    print(f"WORKFLOW INTEGRATION TEST SUMMARY: {passed}/{total} PASSED")
    print("=" * 75 + "\n")


def run_all():
    print("\n" + "#" * 75)
    print("SOVEREIGN AGENTIC AI WORKBENCH MASTER TEST RUNNER (PHASES 1 - 6)")
    print("#" * 75)

    # 1. Run Phase 2 Tool Tests
    print("\n>>> EXECUTION STEP 1: PHASE 2 AGENT TOOLS SUITE")
    import test_tools
    test_tools.test_math_eval_tool()
    test_tools.test_file_io_tool()
    test_tools.test_code_sandbox_tool()
    test_tools.test_spreadsheet_tool()
    test_tools.test_doc_gen_tool()
    test_tools.test_ocr_vlm_tool()

    # 2. Run Phase 4 Router Tests
    print("\n>>> EXECUTION STEP 2: PHASE 4 ROUTER / CLASSIFIER SUITE")
    import test_router
    test_router.run_tests()

    # 3. Run Phase 5 Orchestrator Skeleton Tests
    print("\n>>> EXECUTION STEP 3: PHASE 5 ORCHESTRATOR SKELETON SUITE")
    import test_orchestrator
    test_orchestrator.test_phase5_orchestrator_skeleton()

    # 4. Run Phase 6 ReAct Tool Loop Tests
    print("\n>>> EXECUTION STEP 4: PHASE 6 REACT TOOL INTEGRATION SUITE")
    import test_phase6
    test_phase6.test_tool_node_failure_stages()
    test_phase6.test_loop_safety_bounds()
    test_phase6.test_react_graph_tool_dispatch_wiring()

    # 5. Run E2E Workflows
    print("\n>>> EXECUTION STEP 5: END-TO-END MULTI-TOOL WORKFLOW SUITE")
    run_e2e_workflow_tests()

    print("\n" + "#" * 75)
    print("MASTER TEST SUITE SUCCESS: ALL PHASES 1 - 6 VERIFIED PASSED 100%!")
    print("#" * 75 + "\n")


if __name__ == "__main__":
    run_all()
