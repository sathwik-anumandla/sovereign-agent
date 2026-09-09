"""
P9 - Flow 3: Multimodal (non-document) image reasoning.
Confirms run_inference's images= param (P7 amendment) works standalone,
with NO tool call (especially no ocr_vlm) — file_metadata should not
trip likely_needs_ocr since this isn't a structured document.
"""

import sys
import os
import uuid

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from orchestrator import build_orchestrator_graph, WorkbenchState
from langgraph.checkpoint.postgres import PostgresSaver
from tools.db import get_db_url
try:
    from scripts.inspect_run import inspect_thread
except ImportError:
    from scripts.inspect_run import inspect_thread


def main():
    thread_id = str(uuid.uuid4())

    from pathlib import Path
    from router.schemas import FileMetadata

    image_path = str(Path("ignore-files/test-img.png").resolve())

    initial_state = WorkbenchState(
        prompt="What do you see in this image? Are there any visible issues or points of concern?",
        file_metadata=[
            FileMetadata(
                filename=Path(image_path).name,
                extension=Path(image_path).suffix,
                filepath=image_path,
            )
        ],
    )

    config = {"configurable": {"thread_id": thread_id}}
    builder = build_orchestrator_graph()

    print(f"--- Invoking graph | thread_id={thread_id} ---")
    with PostgresSaver.from_conn_string(get_db_url()) as checkpointer:
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