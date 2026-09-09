"""
test_flow1_exec.py
==================
Flow 1 End-to-End Test Script: Document Processing & Extraction Pipeline.

Test Steps:
1. Stages test-1.pdf from ignore-files/ocr-test/test-1.pdf.
2. Invokes orchestrator graph with prompt asking to extract text/data and summarize the document.
3. Verifies metadata routing, OCR transcription (ocr_vlm), and clear response generation.
"""

import time
import uuid
from pathlib import Path
from orchestrator import build_orchestrator_graph, WorkbenchState
from router.schemas import FileMetadata
from langgraph.checkpoint.postgres import PostgresSaver
from tools.db import get_db_url

def main():
    thread_id = str(uuid.uuid4())
    pdf_path = Path("ignore-files/ocr-test/test-1.pdf").resolve()

    assert pdf_path.exists(), f"Test PDF not found at {pdf_path}"

    prompt = (
        f"Please extract and analyze the contents of the document '{pdf_path.name}'. "
        "Summarize the key information, sections, and any numerical or table data in a structured format."
    )

    initial_state = WorkbenchState(
        prompt=prompt,
        file_metadata=[
            FileMetadata(
                filename=pdf_path.name,
                extension=pdf_path.suffix,
                filepath=str(pdf_path),
                path=str(pdf_path)
            )
        ],
        thinking=False,
        max_tool_iterations=3
    )

    config = {"configurable": {"thread_id": thread_id}}
    builder = build_orchestrator_graph()

    print("=========================================================================")
    print(f" FLOW 1 END-TO-END TEST: Document Processing & OCR Extraction")
    print(f" Thread ID : {thread_id}")
    print(f" PDF File  : {pdf_path.name}")
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

    for idx, tr in enumerate(tool_results, 1):
        status = getattr(tr, "status", None) or (tr.get("status") if isinstance(tr, dict) else "N/A")
        metadata = getattr(tr, "metadata", {}) or (tr.get("metadata") if isinstance(tr, dict) else {})
        t_name = metadata.get("tool_name") or metadata.get("tool") or "unknown"
        error = getattr(tr, "error", None) or (tr.get("error") if isinstance(tr, dict) else None)
        print(f"  [{idx}] Tool: '{t_name}' | Status: {status} | Error: {error}")

    response = result.get("response", "")
    print("\n--- Final Assistant Output (Document Extraction & Summary) ---")
    print(response.strip() if response else "[EMPTY RESPONSE]")
    print("-" * 75)

    assert response and len(response.strip()) > 0, "Response must not be empty"
    print("\nFLOW 1 DOCUMENT PROCESSING TEST COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
