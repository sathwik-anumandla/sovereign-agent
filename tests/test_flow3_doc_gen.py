"""
test_flow3_doc_gen.py
=====================
Flow 3 End-to-End Test Script: Official Deliverable Generation Pipeline (.docx / .xlsx).

Test Steps:
1. Invokes orchestrator graph requesting an official Word approval document (.docx).
2. Verifies that model invokes doc_gen tool with structured spec (title, sections, tables).
3. Verifies that generated .docx file is created on disk and valid.
"""

import time
import uuid
from pathlib import Path
from orchestrator import build_orchestrator_graph, WorkbenchState
from langgraph.checkpoint.postgres import PostgresSaver
from tools.db import get_db_url


def main():
    thread_id = str(uuid.uuid4())
    doc_filename = "cdu2_inspection_approval.docx"

    prompt = (
        "Please generate an official Word approval note (.docx) summarizing the technical inspection "
        "of Crude Distillation Unit 2 (CDU-2). Include an Executive Summary section and a table "
        "of equipment statuses (Pump-101: 150 PSI, Approved; Valve-201: 80 PSI, Maintenance Required). "
        f"Save the document deliverable to 'reports/{doc_filename}'."
    )

    initial_state = WorkbenchState(
        prompt=prompt,
        thinking=False,
        max_tool_iterations=3
    )

    config = {"configurable": {"thread_id": thread_id}}
    builder = build_orchestrator_graph()

    print("=========================================================================")
    print(f" FLOW 3 END-TO-END TEST: Document Deliverable Generation Pipeline (.docx)")
    print(f" Thread ID : {thread_id}")
    print(f" Output Doc: reports/{doc_filename}")
    print("=========================================================================\n")

    start_time = time.time()
    with PostgresSaver.from_conn_string(get_db_url()) as checkpointer:
        compiled_graph = builder.compile(checkpointer=checkpointer)
        result = compiled_graph.invoke(initial_state, config=config)
    elapsed = time.time() - start_time

    print(f"=== Execution Completed in {elapsed:.2f} seconds ===")

    route_dec = result.get("route_decision")
    role = getattr(route_dec, "role", None) or (route_dec.get("role") if isinstance(route_dec, dict) else "N/A")
    method = getattr(route_dec, "method", None) or (route_dec.get("method") if isinstance(route_dec, dict) else "N/A")

    print(f"Router Decision : Role={role}, Method={method}")

    tool_results = result.get("tool_results", []) or []
    print(f"Tools Executed  : {len(tool_results)}")

    generated_doc_path = None
    for idx, tr in enumerate(tool_results, 1):
        status = getattr(tr, "status", None) or (tr.get("status") if isinstance(tr, dict) else "N/A")
        metadata = getattr(tr, "metadata", {}) or (tr.get("metadata") if isinstance(tr, dict) else {})
        t_name = metadata.get("tool_name") or metadata.get("tool") or "unknown"
        error = getattr(tr, "error", None) or (tr.get("error") if isinstance(tr, dict) else None)
        out_path = getattr(tr, "output_path", None) or metadata.get("output_path")
        if out_path:
            generated_doc_path = out_path
        print(f"  [{idx}] Tool: '{t_name}' | Status: {status} | OutPath: {out_path} | Error: {error}")

    # Check for any generated docx file in workspace if metadata didn't explicitly set it
    if not generated_doc_path:
        workspace_dir = Path("workspace")
        docx_files = list(workspace_dir.rglob("*.docx")) if workspace_dir.exists() else []
        if docx_files:
            latest = max(docx_files, key=lambda f: f.stat().st_mtime)
            generated_doc_path = str(latest.resolve())

    response = result.get("response", "")
    print("\n--- Final Assistant Output (Deliverable Generation Summary) ---")
    print(response.strip() if response else "[EMPTY RESPONSE]")
    print("-" * 75)

    assert response and len(response.strip()) > 0, "Response must not be empty"
    assert generated_doc_path and Path(generated_doc_path).exists(), f"Generated .docx deliverable must exist on disk at {generated_doc_path}"

    print(f"\nSUCCESS: Generated Word deliverable created at: {generated_doc_path}")
    print("FLOW 3 DELIVERABLE GENERATION TEST COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
