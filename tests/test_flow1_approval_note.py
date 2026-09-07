"""
P9 - Flow 1 Integration Test Harness: Scanned Report -> Approval Note Document.
Confirms ReAct orchestrator handles scanned PDF document processing via ocr_vlm,
queries rag_kb vectorstore, and generates an approval note .docx via doc_gen tool.
"""

import sys
import os
import uuid
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from orchestrator import build_orchestrator_graph, DB_FILENAME, WorkbenchState
from router.schemas import FileMetadata
try:
    from scripts.inspect_run import inspect_thread
except ImportError:
    from scripts.inspect_run import inspect_thread

EXPECTED_TOOLS = ["ocr_vlm", "rag_kb", "doc_gen"]


def main():
    thread_id = str(uuid.uuid4())

    pdf_path = str(Path("ignore-files/ocr-test/test-1.pdf").resolve())

    prompt = (
        f"I have a scanned report at {pdf_path}. Extract its contents, then generate a formal "
        "approval note in Word format based on our standard approval note template, incorporating "
        "the key details from the report. Save it as an approval note document."
    )

    initial_state = WorkbenchState(
        prompt=prompt,
        file_metadata=[
            FileMetadata(
                filename=Path(pdf_path).name,
                extension=Path(pdf_path).suffix,
                filepath=pdf_path,
                path=pdf_path,
            )
        ],
    )

    config = {"configurable": {"thread_id": thread_id}}
    builder = build_orchestrator_graph()

    print(f"--- Invoking graph | thread_id={thread_id} ---")
    with SqliteSaver.from_conn_string(DB_FILENAME) as checkpointer:
        compiled_graph = builder.compile(checkpointer=checkpointer)
        result = compiled_graph.invoke(initial_state, config=config)

    print("\n--- Final Response ---")
    print(result.get("response"))

    print("\n--- Route Decision ---")
    print(result.get("route_decision"))

    print("\n--- Checkpoint History ---")
    inspect_thread(thread_id)

    # Tool execution sequence and Pass/Fail verification
    tool_results = result.get("tool_results", []) or []
    called_tools = []
    docx_file_path = None

    print("\n" + "=" * 75)
    print("TOOL EXECUTION SEQUENCE & RESULT SUMMARY")
    print("=" * 75)

    for idx, tr in enumerate(tool_results, 1):
        status = getattr(tr, "status", None) or (tr.get("status") if isinstance(tr, dict) else "N/A")
        metadata = getattr(tr, "metadata", {}) or (tr.get("metadata") if isinstance(tr, dict) else {})
        tool_name = metadata.get("tool_name") or metadata.get("tool") or "unknown"
        error = getattr(tr, "error", None) or (tr.get("error") if isinstance(tr, dict) else None)
        called_tools.append((tool_name, status, error))

        print(f"Step {idx}: Tool='{tool_name}' | Status={status}")
        if error:
            print(f"  Error: {error}")

        # Search metadata / result for docx output path
        res_data = metadata.get("result")
        if isinstance(res_data, dict):
            path_val = res_data.get("file_path") or res_data.get("path") or res_data.get("output_path")
            if path_val and str(path_val).endswith(".docx"):
                docx_file_path = str(path_val)

    if not docx_file_path:
        # Check workspace directory for any created docx files
        workspace_dir = Path("workspace")
        if workspace_dir.exists():
            docx_files = list(workspace_dir.rglob("*.docx"))
            if docx_files:
                latest_docx = max(docx_files, key=lambda f: f.stat().st_mtime)
                docx_file_path = str(latest_docx.resolve())

    # Audit PASS/FAIL criteria
    tool_names_called = [ct[0] for ct in called_tools]
    all_3_fired = all(t in tool_names_called for t in EXPECTED_TOOLS)
    reached_end = result.get("response") is not None
    docx_exists = docx_file_path is not None and Path(docx_file_path).exists()

    print("\n" + "=" * 75)
    print("PASS / FAIL SUMMARY AUDIT")
    print("=" * 75)
    print(f"1. Expected tools fired ({', '.join(EXPECTED_TOOLS)}) : {'PASS' if all_3_fired else 'FAIL'}")
    print(f"   Tools called in sequence: {tool_names_called}")
    print(f"2. Graph reached END cleanly                      : {'PASS' if reached_end else 'FAIL'}")
    print(f"3. Generated Word (.docx) document created         : {'PASS' if docx_exists else 'FAIL'}")
    if docx_exists:
        print(f"   Generated document saved at                     : {docx_file_path}")
    else:
        print("   Generated document saved at                     : None")
    print("=" * 75)

    if all_3_fired and reached_end and docx_exists:
        print("\n>>> FLOW 1 TEST SUITE RESULT: SUCCESS (PASS)")
    else:
        print("\n>>> FLOW 1 TEST SUITE RESULT: FAILURE (FAIL)")


if __name__ == "__main__":
    main()
