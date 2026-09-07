"""
cli.py - Sovereign On-Premise AI Workbench Interactive CLI
=========================================================
Run single text prompts or start an interactive prompt session with multi-turn conversation memory.

Usage:
  python3 cli.py "What is 15 * 24?"
  python3 cli.py --file ignore-files/sensor_logs.csv "Analyze this dataset"
  python3 cli.py --fast (starts interactive fast-mode chat session)
  python3 cli.py --thinking (starts interactive deep-thinking session)
"""

import sys
import uuid
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, List

from orchestrator import run_workbench
from router.schemas import FileMetadata


def check_ollama_running() -> bool:
    """Verifies if the Ollama server is running locally."""
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def execute_prompt(prompt_text: str, file_path: Optional[str] = None, thread_id: Optional[str] = None, fast: bool = True):
    """Executes a single prompt through the workbench orchestrator."""
    if not check_ollama_running():
        print("\n[WARNING] Ollama server is not running!")
        print("Please start Ollama in a separate terminal window by running:\n")
        print("    ollama serve\n")
        return None, None

    file_metadata_list: Optional[List[FileMetadata]] = None
    if file_path:
        p = Path(file_path)
        if not p.exists():
            print(f"\n[Error] File not found: {file_path}")
            return None, None
        ext = p.suffix.lower().lstrip(".")
        file_metadata_list = [FileMetadata(filename=p.name, extension=ext, filepath=str(p.resolve()), path=str(p.resolve()))]

    print(f"\nProcessing prompt: '{prompt_text}'")
    if file_metadata_list:
        print(f"Attached file    : {file_path}")
    print(f"Mode             : {' Fast Mode' if fast else ' Thinking Mode'}")
    print("=" * 60)

    try:
        final_state, active_thread_id = run_workbench(
            prompt=prompt_text,
            file_metadata=file_metadata_list,
            thread_id=thread_id,
            max_tool_iterations=2 if fast else 5,
            thinking=not fast
        )
        
        response_text = final_state.get("response", "")
        
        # Display Router Decision Info
        route_dec = final_state.get("route_decision")
        role = getattr(route_dec, "role", None) or (route_dec.get("role") if isinstance(route_dec, dict) else "N/A")
        method = getattr(route_dec, "method", None) or (route_dec.get("method") if isinstance(route_dec, dict) else "N/A")
        conf = getattr(route_dec, "confidence", None) or (route_dec.get("confidence") if isinstance(route_dec, dict) else 1.0)

        model_map = {
            "reasoning": "qwen3.5:4b-q4_K_M",
            "coding": "qwen2.5-coder:3b",
            "vision": "qwen3.5:4b-q4_K_M",
            "ocr": "qwen2.5-vl:3b"
        }
        model_name = model_map.get(str(role).lower(), "qwen3.5:4b-q4_K_M")

        print("\n[ROUTER DECISION]")
        print(f"  • Assigned Role : {role} ({model_name})")
        print(f"  • Route Method  : {method}")
        print(f"  • Confidence    : {float(conf):.2f}")

        tool_results = final_state.get("tool_results", [])
        if tool_results:
            print(f"  • Tools Called  : {len(tool_results)} tool execution(s)")

        print("\n[SOVEREIGN AGENT RESPONSE]")
        print("-" * 60)
        print(response_text if response_text else "[No text returned]")
        print("-" * 60)
        print(f"[Thread ID]: {active_thread_id}\n")

        return final_state, active_thread_id

    except Exception as e:
        print(f"\n[Error executing workbench]: {e}\n")
        return None, None


def interactive_mode(file_path: Optional[str] = None, fast: bool = True):
    """Interactive loop for entering prompts continuously with persistent thread memory."""
    if not check_ollama_running():
        print("\n[WARNING] Ollama server is not running!")
        print("Please start Ollama in a separate terminal window by running:\n")
        print("    ollama serve\n")
        return

    session_thread_id = str(uuid.uuid4())

    print("\n" + "=" * 60)
    print(" Sovereign Agentic AI Workbench - Interactive CLI")
    print(f" Thread ID : {session_thread_id}")
    print(f" Mode      : {' Fast Mode (Default)' if fast else ' Deep Thinking Mode'}")
    if file_path:
        print(f" Attachment: {file_path}")
    print(" Type your prompt below. Type 'exit' or 'quit' to stop.")
    print("=" * 60 + "\n")

    while True:
        try:
            user_input = input("User > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("Exiting interactive workbench. Goodbye!")
                break

            execute_prompt(user_input, file_path=file_path, thread_id=session_thread_id, fast=fast)

        except (KeyboardInterrupt, EOFError):
            print("\nExiting interactive workbench. Goodbye!")
            break


def main():
    parser = argparse.ArgumentParser(description="Sovereign Agentic AI Workbench CLI")
    parser.add_argument("prompt", nargs="?", help="Text prompt to pass to the workbench")
    parser.add_argument("--file", "-f", help="Optional file path attachment (e.g. PDF, CSV, Python file)")
    parser.add_argument("--thinking", action="store_true", help="Enable deep step-by-step thinking mode (default is fast mode)")
    parser.add_argument("--fast", action="store_true", help="Enable fast mode without long thinking delays (default)")
    
    args = parser.parse_args()
    fast_mode = not args.thinking

    if args.prompt:
        execute_prompt(args.prompt, file_path=args.file, fast=fast_mode)
    else:
        interactive_mode(file_path=args.file, fast=fast_mode)


if __name__ == "__main__":
    main()
