"""
test_images.py
==============
Test suite for multimodal image reasoning and vision capabilities across ignore-files/img-test images.
Tests:
1. Router Stage 0 Multimodal Override (role="reasoning", method="multimodal_override").
2. Direct vision inference with images attached to user message.
3. Fast mode execution (thinking=False).
"""

import time
import uuid
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver

from orchestrator import build_orchestrator_graph, DB_FILENAME, WorkbenchState
from router.schemas import FileMetadata


def test_single_image(img_filename: str):
    thread_id = str(uuid.uuid4())
    img_dir = Path("ignore-files/img-test").resolve()
    img_path = img_dir / img_filename

    assert img_path.exists(), f"Image file not found: {img_path}"

    prompt = f"Describe what you see in this image ({img_filename}) and summarize its main content or features."

    initial_state = WorkbenchState(
        prompt=prompt,
        file_metadata=[
            FileMetadata(
                filename=img_path.name,
                extension=img_path.suffix,
                filepath=str(img_path)
            )
        ],
        thinking=False,
        max_tool_iterations=2
    )

    config = {"configurable": {"thread_id": thread_id}}
    builder = build_orchestrator_graph()

    print(f"\n========================================================")
    print(f" TESTING IMAGE: {img_filename}")
    print(f" Filepath     : {img_path}")
    print(f"========================================================")

    start_time = time.time()
    with SqliteSaver.from_conn_string(DB_FILENAME) as checkpointer:
        compiled_graph = builder.compile(checkpointer=checkpointer)
        result = compiled_graph.invoke(initial_state, config=config)
    elapsed = time.time() - start_time

    route_dec = result.get("route_decision")
    role = getattr(route_dec, "role", None) or (route_dec.get("role") if isinstance(route_dec, dict) else "N/A")
    method = getattr(route_dec, "method", None) or (route_dec.get("method") if isinstance(route_dec, dict) else "N/A")
    response = result.get("response", "")

    print(f"Time Elapsed  : {elapsed:.2f} seconds")
    print(f"Route Role    : {role} (method: {method})")
    print(f"Tool Calls    : {len(result.get('tool_calls', []))}")
    print(f"\n--- Assistant Vision Output for {img_filename} ---")
    print(response.strip() if response else "[EMPTY RESPONSE]")
    print("-" * 56)

    assert role == "reasoning", f"Expected role 'reasoning' for multimodal image, got '{role}'"
    assert method == "multimodal_override", f"Expected method 'multimodal_override', got '{method}'"
    assert response and len(response.strip()) > 0, "Response should not be empty"


def main():
    print("=== STARTING MULTIMODAL IMAGE REASONING TEST SUITE ===")
    test_images = ["test1.png", "test2.png", "test3.png", "test4.png"]

    for img in test_images:
        try:
            test_single_image(img)
        except Exception as e:
            print(f"ERROR testing {img}: {e}")

    print("\nMULTIMODAL IMAGE REASONING TEST SUITE COMPLETED!")


if __name__ == "__main__":
    main()
