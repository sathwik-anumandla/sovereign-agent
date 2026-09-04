"""
tests/test_router.py (SIH PS 26117)
===================================
Standalone test harness for Phase 4 Router / Classifier.
Tests 16 sample requests across Stage 1 (Metadata), Stage 2 (Keyword), and Stage 3 (Classifier).
"""

import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from router import route, FileMetadata

TEST_CASES = [
    # Stage 1: Metadata Hits
    ("Please inspect this script for bugs", [FileMetadata(filename="pipeline.py", extension=".py")], "coding", "metadata"),
    ("Can you review this notebook?", [FileMetadata(filename="data_analysis.ipynb", extension=".ipynb")], "coding", "metadata"),
    ("Summarize this document", [FileMetadata(filename="incident_report.pdf", extension=".pdf")], "reasoning", "classifier"),

    # Stage 2: Keyword Hits
    ("How do I fix this null pointer exception in my code?", None, "coding", "keyword"),
    ("Can you refactor this function to make it faster?", None, "coding", "keyword"),
    ("Where do I set up my dockerfile dependencies?", None, "coding", "keyword"),
    ("Write a python script to process CSV files", None, "coding", "keyword"),

    # Stage 3: Classifier Ambiguous Cases (Coding)
    ("this function isn't returning what I expect, can you look at it", None, "coding", "classifier"),
    ("how should I structure the folder layout for this project", None, "coding", "classifier"),
    ("I want to automate this task, where do I start", None, "coding", "classifier"),
    ("how do I test whether this is working correctly", None, "coding", "classifier"),

    # Stage 3: Classifier Ambiguous Cases (Reasoning)
    ("explain the tradeoffs between two different approval workflows", None, "reasoning", "classifier"),
    ("summarize the key risks in this incident report", None, "reasoning", "classifier"),
    ("help me think through how to present this to the review committee", None, "reasoning", "classifier"),
    ("what factors should I weigh before recommending this approach", None, "reasoning", "classifier"),
    ("explain the implications of this policy on daily operations", None, "reasoning", "classifier"),
]


def run_tests():
    print("\n" + "=" * 75)
    print("PHASE 4 ROUTER / CLASSIFIER TEST SUITE")
    print("=" * 75)

    passed = 0
    total = len(TEST_CASES)

    for idx, (prompt, metadata, expected_role, expected_method) in enumerate(TEST_CASES, 1):
        decision = route(prompt, metadata)
        
        role_match = decision.role == expected_role
        
        is_pass = role_match
        status_icon = "[PASS]" if is_pass else "[FAIL]"
        if is_pass:
            passed += 1

        file_info = f"[{metadata[0].filename}] " if metadata else ""
        print(f"Test {idx:02d} | {status_icon} | Role: {decision.role:<9} | Method: {decision.method:<10} | Conf: {decision.confidence:.2f} | Prompt: {file_info}'{prompt[:45]}...'")

    print("\n" + "=" * 75)
    print(f"FINAL ROUTER TEST RESULT: {passed}/{total} PASSED")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_tests()
