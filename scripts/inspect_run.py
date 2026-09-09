"""
scripts/inspect_run.py (SIH PS 26117)
=====================================
Standalone thread inspector helper script.
Inspects persistent PostgreSQL checkpoint history for any given thread_id.
Pretty-prints checkpoint snapshots, node transitions, tool calls, tool results, and iteration counts.
"""

import sys
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from langgraph.checkpoint.postgres import PostgresSaver
from orchestrator import build_orchestrator_graph
from tools.db import get_db_url, execute_query


def list_recent_thread_ids(limit: int = 10) -> list[str]:
    """Queries PostgreSQL checkpoints table for recent thread IDs. Pass limit <= 0 to fetch all."""
    try:
        query = "SELECT DISTINCT thread_id FROM checkpoints ORDER BY thread_id DESC"
        if limit > 0:
            query += " LIMIT %s"
            rows = execute_query(query, (limit,), fetch_all=True)
        else:
            rows = execute_query(query, fetch_all=True)
        return [r[0] for r in rows] if rows else []
    except Exception:
        return []


def inspect_thread(thread_id: str):
    """Prints full checkpoint history for a specified thread_id."""
    print("\n" + "=" * 75)
    print(f"INSPECTING ORCHESTRATOR THREAD ID: {thread_id}")
    print("=" * 75)

    builder = build_orchestrator_graph()
    config = {"configurable": {"thread_id": thread_id}}

    try:
        with PostgresSaver.from_conn_string(get_db_url()) as checkpointer:
            graph = builder.compile(checkpointer=checkpointer)
            history = list(graph.get_state_history(config))

            if not history:
                print(f"No checkpoint state history found for thread '{thread_id}'.")
                return

            print(f"Found {len(history)} persistent checkpoint snapshots:\n")

            for idx, snapshot in enumerate(reversed(history), 1):
                values = snapshot.values or {}
                next_nodes = snapshot.next
                c_id = snapshot.config.get("configurable", {}).get("checkpoint_id", "N/A")

                print(f"--- [Step {idx}] Snapshot Checkpoint ID: {c_id} ---")
                print(f"Next Target Node : {next_nodes}")
                if "prompt" in values and values["prompt"]:
                    print(f"Prompt           : '{values['prompt']}'")
                if "route_decision" in values and values["route_decision"]:
                    rd = values["route_decision"]
                    role = getattr(rd, "role", None) or (rd.get("role") if isinstance(rd, dict) else "N/A")
                    method = getattr(rd, "method", None) or (rd.get("method") if isinstance(rd, dict) else "N/A")
                    conf = getattr(rd, "confidence", None) or (rd.get("confidence") if isinstance(rd, dict) else 0.0)
                    print(f"Route Decision   : Role='{role}', Method='{method}', Confidence={conf}")
                if "tool_iteration_count" in values:
                    print(f"Iteration Count  : {values['tool_iteration_count']} / {values.get('max_tool_iterations', 5)}")
                if "tool_calls" in values and values["tool_calls"]:
                    print(f"Pending Tool Calls: {len(values['tool_calls'])}")
                    for tc in values["tool_calls"]:
                        fn = tc.get("function", {}) if isinstance(tc, dict) else {}
                        t_name = fn.get("name") or tc.get("name") or "unknown"
                        print(f"  • Tool Name: {t_name} | Args: {fn.get('arguments') or tc.get('arguments')}")
                if "tool_results" in values and values["tool_results"]:
                    print(f"Tool Results     : {len(values['tool_results'])}")
                    for tr in values["tool_results"]:
                        st = getattr(tr, "status", None) or (tr.get("status") if isinstance(tr, dict) else "N/A")
                        meta = getattr(tr, "metadata", {}) or (tr.get("metadata") if isinstance(tr, dict) else {})
                        tname = meta.get("tool_name") or meta.get("tool") or "unknown"
                        print(f"  • Result [{tname}]: Status={st}")
                if "response" in values and values["response"]:
                    res_preview = values["response"].strip()
                    res_line = res_preview[:120] + ("..." if len(res_preview) > 120 else "")
                    print(f"Response Output  : '{res_line}'")
                print()

    except Exception as e:
        print(f"Error inspecting thread checkpoint in PostgreSQL: {e}")

    print("=" * 75 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Inspect persistent PostgreSQL checkpoint history for Sovereign Workbench thread.")
    parser.add_argument("thread_id", nargs="?", help="Specific thread_id to inspect")
    parser.add_argument("--recent", type=int, default=5, help="Number of recent threads to list if thread_id is omitted")
    args = parser.parse_args()

    if args.thread_id:
        inspect_thread(args.thread_id)
    else:
        recent = list_recent_thread_ids(args.recent)
        if not recent:
            print("No active thread checkpoints found in PostgreSQL. Run 'python server.py' or 'python cli.py' to generate runs.")
        else:
            print(f"\nRecent {len(recent)} Thread IDs in PostgreSQL:")
            for tid in recent:
                print(f"  • {tid}")
            print("\nTo inspect a thread, run:")
            print("  python scripts/inspect_run.py <thread_id>\n")


if __name__ == "__main__":
    main()
