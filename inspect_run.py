"""
inspect_run.py (SIH PS 26117)
=============================
Standalone thread inspector helper script.
Inspects persistent SQLite checkpoint history for any given thread_id.
Pretty-prints checkpoint snapshots, node transitions, state values, and step timestamps.
"""

import sys
import sqlite3
import argparse
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver
from orchestrator import build_orchestrator_graph, DB_FILENAME


def list_recent_thread_ids(limit: int = 10) -> list[str]:
    """Queries SQLite checkpoints table for recent thread IDs."""
    if not Path(DB_FILENAME).exists():
        return []
    try:
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()
        # Query distinct thread_ids from checkpoints table
        cursor.execute("SELECT DISTINCT thread_id FROM checkpoints ORDER BY checkpoint_id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def inspect_thread(thread_id: str):
    """Prints full checkpoint history for a specified thread_id."""
    print("\n" + "=" * 70)
    print(f"INSPECTING ORCHESTRATOR THREAD ID: {thread_id}")
    print("=" * 70)

    if not Path(DB_FILENAME).exists():
        print(f"Error: Checkpoint database '{DB_FILENAME}' not found.")
        return

    builder = build_orchestrator_graph()
    config = {"configurable": {"thread_id": thread_id}}

    with SqliteSaver.from_conn_string(DB_FILENAME) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        history = list(graph.get_state_history(config))

    if not history:
        print(f"No checkpoint snapshots found for thread_id '{thread_id}'.")
        return

    print(f"Found {len(history)} persistent checkpoint snapshots:\n")

    for idx, snapshot in enumerate(reversed(history), 1):
        next_nodes = snapshot.next if snapshot.next else ("END",)
        values = snapshot.values or {}
        checkpoint_id = snapshot.config.get("configurable", {}).get("checkpoint_id", "N/A")
        
        print(f"--- [Step {idx}] Snapshot Checkpoint ID: {checkpoint_id} ---")
        print(f"Next Target Node : {next_nodes}")
        
        if "prompt" in values:
            print(f"Prompt           : '{values.get('prompt')}'")
        if "route_decision" in values and values.get("route_decision"):
            rd = values.get("route_decision")
            role = getattr(rd, "role", None) or (rd.get("role") if isinstance(rd, dict) else "N/A")
            method = getattr(rd, "method", None) or (rd.get("method") if isinstance(rd, dict) else "N/A")
            conf = getattr(rd, "confidence", None) or (rd.get("confidence") if isinstance(rd, dict) else "N/A")
            print(f"Route Decision   : Role='{role}', Method='{method}', Confidence={conf}")
        if "response" in values and values.get("response"):
            resp = str(values.get("response")).strip()
            preview = resp[:120] + "..." if len(resp) > 120 else resp
            print(f"Response Output  : '{preview}'")
            
        print()

    print("=" * 70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect LangGraph orchestrator persistent checkpoint history.")
    parser.add_argument("thread_id", nargs="?", help="Specific thread_id to inspect")
    parser.add_argument("--list", action="store_true", help="List recent thread IDs in database")
    args = parser.parse_args()

    if args.list or not args.thread_id:
        recent_threads = list_recent_thread_ids(10)
        if recent_threads:
            print("\nRecent Checkpoint Thread IDs:")
            for t in recent_threads:
                print(f"  - {t}")
            if not args.thread_id:
                print(f"\nInspecting most recent thread: {recent_threads[0]}")
                inspect_thread(recent_threads[0])
        else:
            print("\nNo threads found in database yet.")
    else:
        inspect_thread(args.thread_id)
