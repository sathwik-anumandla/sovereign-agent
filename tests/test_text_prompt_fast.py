"""
test_text_prompt_fast.py
========================
Test text-only prompt execution with Thinking OFF (Fast Mode).
"""

import time
import uuid
from langgraph.checkpoint.postgres import PostgresSaver
from orchestrator import build_orchestrator_graph, WorkbenchState
from tools.db import get_db_url


def run_single_test(prompt: str):
    thread_id = str(uuid.uuid4())

    initial_state = WorkbenchState(
        prompt=prompt,
        thinking=False,
        max_tool_iterations=2
    )

    config = {"configurable": {"thread_id": thread_id}}
    builder = build_orchestrator_graph()

    print(f"\n--- Test Prompt: '{prompt}' ---")
    start_time = time.time()
    with PostgresSaver.from_conn_string(get_db_url()) as checkpointer:
        compiled_graph = builder.compile(checkpointer=checkpointer)
        result = compiled_graph.invoke(initial_state, config=config)
    elapsed = time.time() - start_time

    route_dec = result.get("route_decision")
    role = getattr(route_dec, "role", None) or (route_dec.get("role") if isinstance(route_dec, dict) else "N/A")
    response = result.get("response", "")

    print(f"Time Taken       : {elapsed:.2f}s")
    print(f"Role Assigned    : {role}")
    print(f"Tool Calls Count : {len(result.get('tool_calls', []))}")
    print("Response Output  :")
    print(response.strip())
    print("-" * 50)

    assert response and len(response.strip()) > 0
    assert "<think>" not in response


def main():
    print("=== Testing Text-Only Prompts (Thinking OFF / Fast Mode) ===")
    prompts = [
        "Explain what an air-gapped computer system is in 2 concise sentences.",
        "What are 3 main advantages of Python for rapid software prototyping?"
    ]

    for p in prompts:
        run_single_test(p)

    print("\nALL TEXT-ONLY FAST MODE TESTS PASSED!")


if __name__ == "__main__":
    main()
