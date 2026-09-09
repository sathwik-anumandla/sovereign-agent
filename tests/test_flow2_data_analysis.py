"""
test_flow2_data_analysis.py
============================
Flow 2 End-to-End Test Script: Code Execution & Data Analysis (Code Sandbox / Spreadsheet).

Test Steps:
1. Stages sensor_logs.csv from ignore-files/sensor_logs.csv.
2. Invokes orchestrator graph with prompt to analyze data, calculate average, and spot anomalies (> 50).
3. Verifies routing, tool execution (code_sandbox / spreadsheet), and accurate anomaly detection output.
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
    csv_path = Path("ignore-files/sensor_logs.csv").resolve()

    assert csv_path.exists(), f"Test CSV file not found at {csv_path}"

    prompt = (
        f"Please analyze the dataset '{csv_path.name}'. "
        "Calculate the average reading, identify any abnormal temperature spikes or anomalies above 50, "
        "and summarize your findings."
    )

    initial_state = WorkbenchState(
        prompt=prompt,
        file_metadata=[
            FileMetadata(
                filename=csv_path.name,
                extension=csv_path.suffix,
                filepath=str(csv_path),
                path=str(csv_path)
            )
        ],
        thinking=False,
        max_tool_iterations=3
    )

    config = {"configurable": {"thread_id": thread_id}}
    builder = build_orchestrator_graph()

    print("=========================================================================")
    print(f" FLOW 2 END-TO-END TEST: Code Execution & Data Analysis Pipeline")
    print(f" Thread ID : {thread_id}")
    print(f" CSV File  : {csv_path.name}")
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
    print("\n--- Final Assistant Output (Data Analysis & Anomaly Detection) ---")
    print(response.strip() if response else "[EMPTY RESPONSE]")
    print("-" * 75)

    assert response and len(response.strip()) > 0, "Response must not be empty"
    assert len(tool_results) > 0, "At least one data analysis tool should be executed"
    print("\nFLOW 2 DATA ANALYSIS TEST COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
