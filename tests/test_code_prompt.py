"""
P9 - Flow 2: Coding task in sandbox.
Confirms router picks coding role, agent invokes code_sandbox,
and the executed script actually returns sane output.
"""

import sys
import os
import uuid

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from orchestrator import build_orchestrator_graph, DB_FILENAME, WorkbenchState
try:
    from scripts.inspect_run import inspect_thread
except ImportError:
    from scripts.inspect_run import inspect_thread


def main():
    thread_id = str(uuid.uuid4())

    from pathlib import Path
    from router.schemas import FileMetadata

    log_path = str(Path("ignore-files/sensor_logs.csv").resolve())

    initial_state = WorkbenchState(
        prompt=(
            "Write and run a Python script that reads the sensor log file 'sensor_logs.csv' "
            "and flags any readings that are anomalous (e.g. more than 3 standard deviations "
            "from the mean, or physically implausible values). Print the flagged rows."
        ),
        file_metadata=[
            FileMetadata(
                filename=Path(log_path).name,
                extension=Path(log_path).suffix,
                filepath=log_path,
                path=log_path,
            )
        ],
    )

    config = {"configurable": {"thread_id": thread_id}}
    builder = build_orchestrator_graph()

    print(f"--- Invoking graph | thread_id={thread_id} ---")
    with SqliteSaver.from_conn_string(DB_FILENAME) as checkpointer:
        compiled_graph = builder.compile(checkpointer=checkpointer)
        result = compiled_graph.invoke(initial_state, config=config)

    print("\n--- Final response ---")
    print(result.get("response"))

    print("\n--- Route decision ---")
    print(result.get("route_decision"))

    print("\n--- Checkpoint history ---")
    inspect_thread(thread_id)


if __name__ == "__main__":
    main()