"""
test_flow4_memory.py
====================
Flow 4 End-to-End Test Script: Multi-Turn Conversation Memory & SQLite Checkpointing.

Test Steps:
1. Turn 1: Provides specific technical telemetry details for a thread_id.
2. Turn 2: Asks a follow-up recall question relying on Turn 1 context.
3. Turn 3: Requests a cumulative action relying on Turn 1 & 2 history.
4. Verifies persistent state restoration from workbench_checkpoints.db via SqliteSaver.
"""

import sys
import os
import time
import uuid

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from orchestrator import run_workbench
try:
    from scripts.inspect_run import inspect_thread
except ImportError:
    from scripts.inspect_run import inspect_thread


def run_turn(thread_id: str, prompt: str, turn_num: int) -> str:
    print(f"\n--- Turn {turn_num}: User Prompt: '{prompt}' ---")
    
    start = time.time()
    final_state, _ = run_workbench(
        prompt=prompt,
        thread_id=thread_id,
        max_tool_iterations=2,
        thinking=False
    )
    elapsed = time.time() - start

    response = final_state.get("response", "").strip()
    print(f"Time Taken : {elapsed:.2f}s")
    print(f"Response   :\n{response}")
    print("-" * 65)

    return response


def main():
    thread_id = str(uuid.uuid4())

    print("=========================================================================")
    print(f" FLOW 4 END-TO-END TEST: Multi-Turn Conversation Memory & Checkpointing")
    print(f" Thread ID : {thread_id}")
    print("=========================================================================")

    # Turn 1: Store context
    t1_prompt = "Remember this telemetry data for our session: Heat Exchanger HX-301 has a temperature reading of 210C and a pressure reading of 140 PSI."
    r1 = run_turn(thread_id, t1_prompt, 1)
    assert r1 and len(r1) > 0, "Turn 1 response should not be empty"

    # Turn 2: Follow-up recall
    t2_prompt = "What is the temperature reading of Heat Exchanger HX-301 that I gave you in my previous message?"
    r2 = run_turn(thread_id, t2_prompt, 2)
    assert r2 and len(r2) > 0, "Turn 2 response should not be empty"
    assert "210" in r2, f"Turn 2 response MUST recall '210' from Turn 1 conversation memory. Got: {r2}"

    # Turn 3: Cumulative summary
    t3_prompt = "Summarize the operational status of Heat Exchanger HX-301 in 1 concise sentence using both temperature and pressure values."
    r3 = run_turn(thread_id, t3_prompt, 3)
    assert r3 and len(r3) > 0, "Turn 3 response should not be empty"
    assert "210" in r3 or "140" in r3, f"Turn 3 response MUST incorporate context values from conversation history. Got: {r3}"

    print("\n--- SQLite Thread Checkpoint Inspection ---")
    inspect_thread(thread_id)

    print("\nSUCCESS: All 3 multi-turn conversation memory assertions passed!")
    print("FLOW 4 MULTI-TURN MEMORY TEST COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
