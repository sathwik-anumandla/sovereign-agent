"""
cli.py - Sovereign On-Premise AI Workbench Interactive CLI
=========================================================
Run single text prompts or start an interactive prompt session.

Usage:
  python3 cli.py "What is 15 * 24?"
  python3 cli.py --file /path/to/doc.pdf "Summarize this document"
  python3 cli.py (starts interactive chat mode)
"""

import sys
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


def execute_prompt(prompt_text: str, file_path: Optional[str] = None):
    """Executes a single prompt through the workbench orchestrator."""
    if not check_ollama_running():
        print("\n[WARNING] Ollama server is not running!")
        print("Please start Ollama in a separate terminal window by running:\n")
        print("    ollama serve\n")
        print("After starting Ollama, try running your prompt again.\n")
        return

    file_metadata_list: Optional[List[FileMetadata]] = None
    if file_path:
        p = Path(file_path)
        if not p.exists():
            print(f"\n[Error] File not found: {file_path}")
            return
        ext = p.suffix.lower().lstrip(".")
        file_metadata_list = [FileMetadata(filename=p.name, extension=ext, filepath=str(p.resolve()))]

    print(f"\nProcessing prompt: '{prompt_text}'")
    if file_metadata_list:
        print(f"Attached file    : {file_path}")
    print("=" * 60)

    try:
        final_state, thread_id = run_workbench(prompt=prompt_text, file_metadata=file_metadata_list)
        
        # Display response
        response_text = final_state.get("response", "")
        print("\n[RESPONSE]")
        print("-" * 60)
        print(response_text)
        print("-" * 60)
        print(f"\n[Thread ID]: {thread_id}\n")

    except Exception as e:
        print(f"\n[Error executing workbench]: {e}\n")


def interactive_mode():
    """Interactive loop for entering prompts continuously."""
    if not check_ollama_running():
        print("\n[WARNING] Ollama server is not running!")
        print("Please start Ollama in a separate terminal window by running:\n")
        print("    ollama serve\n")
        return

    print("\n" + "=" * 60)
    print(" Sovereign Agentic AI Workbench - Interactive CLI")
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
            
            execute_prompt(user_input)

        except (KeyboardInterrupt, EOFError):
            print("\nExiting interactive workbench. Goodbye!")
            break


def main():
    parser = argparse.ArgumentParser(description="Sovereign Agentic AI Workbench CLI")
    parser.add_argument("prompt", nargs="?", help="Text prompt to pass to the workbench")
    parser.add_argument("--file", "-f", help="Optional file path attachment (e.g. PDF, Python file)")
    
    args = parser.parse_args()

    if args.prompt:
        execute_prompt(args.prompt, file_path=args.file)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
