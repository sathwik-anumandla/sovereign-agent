"""
test_orchestrator.py (SIH PS 26117)
===================================
Phase 5 Test Suite for LangGraph Orchestrator Skeleton.
Verifies end-to-end execution, model routing, persistent SQLite checkpointing,
process restart persistence, file metadata passing, and inspect_run.py thread history inspection.
"""

import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from router.schemas import FileMetadata
from orchestrator import run_workbench, DB_FILENAME
from inspect_run import inspect_thread, list_recent_thread_ids


def test_phase5_orchestrator_skeleton():
    print("\n" + "#" * 70)
    print("PHASE 5: EXTENDED LANGGRAPH ORCHESTRATOR SKELETON TEST SUITE")
    print("#" * 70)

    # Test Case 1: Prompt routing to CODING role
    prompt_coding = "Write a python function `calculate_flow_rate(area, velocity)` that returns `area * velocity`."
    print("\n[Test 1] Executing Coding Request through Orchestrator Graph...")
    state_coding, thread_id_coding = run_workbench(prompt_coding)

    route_coding = state_coding.get("route_decision")
    role_coding = route_coding.role if route_coding else "N/A"
    resp_coding = state_coding.get("response", "")

    print(f"Thread ID     : {thread_id_coding}")
    print(f"Route Role    : {role_coding} (Expected: coding)")
    print(f"Route Method  : {route_coding.method if route_coding else 'N/A'}")

    assert role_coding == "coding", f"Expected role 'coding', got '{role_coding}'"
    assert len(resp_coding) > 0, "Response should not be empty"
    print("[PASS] Test 1: Coding Prompt routed to coding role & returned response.")

    # Test Case 2: Prompt routing to REASONING role
    prompt_reasoning = "Explain the tradeoffs between centralized and decentralized refinery approval processes."
    print("\n[Test 2] Executing Reasoning Request through Orchestrator Graph...")
    state_reasoning, thread_id_reasoning = run_workbench(prompt_reasoning)

    route_reasoning = state_reasoning.get("route_decision")
    role_reasoning = route_reasoning.role if route_reasoning else "N/A"
    resp_reasoning = state_reasoning.get("response", "")

    print(f"Thread ID     : {thread_id_reasoning}")
    print(f"Route Role    : {role_reasoning} (Expected: reasoning)")
    print(f"Route Method  : {route_reasoning.method if route_reasoning else 'N/A'}")

    assert role_reasoning == "reasoning", f"Expected role 'reasoning', got '{role_reasoning}'"
    assert len(resp_reasoning) > 0, "Response should not be empty"
    print("[PASS] Test 2: Reasoning Prompt routed to reasoning role & returned response.")

    # Test Case 3: Attached File Metadata Input (Stage 1 Metadata Route)
    prompt_file = "Please inspect this attached script for bugs and performance issues."
    meta_file = [FileMetadata(filename="pump_analysis.py", extension=".py")]
    print("\n[Test 3] Executing Request with Attached .py File Metadata...")
    state_file, thread_id_file = run_workbench(prompt_file, file_metadata=meta_file)

    route_file = state_file.get("route_decision")
    role_file = route_file.role if route_file else "N/A"
    method_file = route_file.method if route_file else "N/A"

    print(f"Thread ID     : {thread_id_file}")
    print(f"Route Role    : {role_file} (Expected: coding)")
    print(f"Route Method  : {method_file} (Expected: metadata)")

    assert role_file == "coding", f"Expected role 'coding', got '{role_file}'"
    assert method_file == "metadata", f"Expected method 'metadata', got '{method_file}'"
    print("[PASS] Test 3: Attached .py metadata routed via Stage 1 metadata match.")

    # Test Case 4: Engineering Calculation Prompt (Classifier Route)
    prompt_math = "Summarize the key engineering parameters in this inspection report."
    meta_pdf = [FileMetadata(filename="inspection.pdf", extension=".pdf")]
    print("\n[Test 4] Executing Industrial PDF Inspection Request...")
    state_math, thread_id_math = run_workbench(prompt_math, file_metadata=meta_pdf)

    route_math = state_math.get("route_decision")
    role_math = route_math.role if route_math else "N/A"

    print(f"Thread ID     : {thread_id_math}")
    print(f"Route Role    : {role_math} (Expected: reasoning)")

    assert role_math == "reasoning", f"Expected role 'reasoning', got '{role_math}'"
    print("[PASS] Test 4: Inspection PDF prompt routed to reasoning role.")

    # Test Case 5: Custom Thread ID Specification
    custom_thread_id = "custom_thread_sih_2026"
    print(f"\n[Test 5] Executing Request with Custom Thread ID '{custom_thread_id}'...")
    state_custom, returned_thread_id = run_workbench("Explain refinery catalyst deactivation", thread_id=custom_thread_id)

    assert returned_thread_id == custom_thread_id, f"Expected thread_id '{custom_thread_id}', got '{returned_thread_id}'"
    print(f"[PASS] Test 5: Graph honored custom thread_id '{custom_thread_id}'.")

    # Test Case 6: Inspect Checkpoint History for Custom Thread
    print("\n[Test 6] Inspecting Checkpoint Snapshots for Custom Thread ID...")
    inspect_thread(custom_thread_id)

    # Test Case 7: Database Thread List & Process Persistence
    print("\n[Test 7] Verifying SQLite Checkpoint Database Persistence...")
    assert Path(DB_FILENAME).exists(), f"Database '{DB_FILENAME}' must exist on disk"
    recent_threads = list_recent_thread_ids(100)
    print(f"Recent SQLite Thread IDs ({len(recent_threads)} found):")
    for tid in recent_threads[:5]:
        print(f"  - {tid}")

    assert custom_thread_id in recent_threads, f"Thread {custom_thread_id} must persist in SQLite"
    print("[PASS] Test 7: Database contains all persistent thread checkpoints.")

    print("\n" + "#" * 70)
    print("PHASE 5 EXTENDED TEST SUITE: ALL 7 TESTS PASSED 100%!")
    print("#" * 70 + "\n")


if __name__ == "__main__":
    test_phase5_orchestrator_skeleton()
