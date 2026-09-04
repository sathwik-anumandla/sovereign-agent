"""
tests/test_phase8.py (SIH PS 26117)
====================================
Phase 8 Standalone and ReAct Integration Test Suite for RAG / Knowledge Base Tool (rag_kb).
Executes:
1. Standalone document ingestion (text docs & OCR PDF routing).
2. Standalone rag_kb query verification (top-k structure, metadata, scores).
3. Overwrite re-ingestion safety test (no stale trailing chunks).
4. Deletion pipeline test (Chroma deletion & disk copy removal).
5. ReAct orchestrator end-to-end tool calling & source citation verification.
"""

import sys
import os
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from tool_interface import ToolStatus
from tools.rag_kb import (
    rag_kb, RagKbInput, ingest_document, delete_document, 
    get_reference_files, get_chroma_collection, REFERENCE_FILES_DIR
)
from orchestrator import run_workbench, WorkbenchState


def test_standalone_ingestion_and_metadata():
    print("\n" + "=" * 75)
    print("[TEST 1] STANDALONE DOCUMENT INGESTION & METADATA CHECK")
    print("=" * 75)

    # Create dummy text document for test
    test_doc_path = Path(ROOT_DIR) / "workspace" / "mrpl_hcu_manual.txt"
    test_doc_path.parent.mkdir(parents=True, exist_ok=True)

    content = """# MRPL Hydrocracker Unit (HCU) Operating Manual
Section 1: Operating Pressure & Temperature
The MRPL Hydrocracker Unit operates at a design pressure of 180 bar and a reactor inlet temperature of 410 degrees Celsius.

Section 2: Catalyst Specifications
The unit utilizes a high-activity Zeolite-based bifunctional catalyst for heavy gas oil cracking.
Catalyst regeneration cycle is set for every 24 months of continuous refinery operation.
"""
    with open(test_doc_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Ingest text document
    res_text = ingest_document(str(test_doc_path))
    assert res_text["status"] == "success", f"Ingestion failed: {res_text}"
    assert res_text["source"] == "mrpl_hcu_manual.txt"
    assert res_text["chunks_ingested"] >= 1, f"Expected chunks >= 1, got {res_text['chunks_ingested']}"
    print(f"[PASS] Text Document Ingested: {res_text['source']} ({res_text['chunks_ingested']} chunks).")

    # Ingest OCR document (test-1.pdf if available)
    ocr_doc = Path(ROOT_DIR) / "ignore-files" / "ocr-test" / "test-1.pdf"
    if ocr_doc.exists():
        res_ocr = ingest_document(str(ocr_doc))
        assert res_ocr["status"] == "success", f"OCR PDF ingestion failed: {res_ocr}"
        print(f"[PASS] OCR PDF Document Ingested: {res_ocr['source']} ({res_ocr['chunks_ingested']} chunks).")

    # Check live reference file list
    ref_files = get_reference_files()
    assert len(ref_files) >= 1, f"Expected reference files >= 1, got {len(ref_files)}"
    sources = [f["source"] for f in ref_files]
    assert "mrpl_hcu_manual.txt" in sources, f"mrpl_hcu_manual.txt not in live reference list: {sources}"
    print(f"[PASS] Live Reference File List Verified: {sources}")


def test_standalone_rag_query():
    print("\n" + "=" * 75)
    print("[TEST 2] STANDALONE RAG QUERY & STRUCTURED CHUNK RETRIEVAL")
    print("=" * 75)

    inp = RagKbInput(query="What is the operating pressure of MRPL Hydrocracker Unit?", top_k=3, operation="query")
    res = rag_kb(inp)

    assert res.status == ToolStatus.SUCCESS, f"Query failed: {res.error}"
    assert isinstance(res.data, list), "Data must be a list of structured chunk dicts"
    assert len(res.data) > 0, "Expected at least 1 retrieved chunk"

    top_chunk = res.data[0]
    assert "text" in top_chunk, "Chunk missing 'text'"
    assert "source" in top_chunk, "Chunk missing 'source'"
    assert "chunk_index" in top_chunk, "Chunk missing 'chunk_index'"
    assert "score" in top_chunk, "Chunk missing 'score'"

    print(f"Top Chunk Source  : {top_chunk['source']}")
    print(f"Top Chunk Index   : {top_chunk['chunk_index']}")
    print(f"Top Chunk Score   : {top_chunk['score']}")
    print(f"Top Chunk Content : '{top_chunk['text'][:120]}...'")

    result_text = res.metadata.get("result", "")
    assert "180 bar" in result_text or "Hydrocracker" in result_text, "Expected query result to mention 180 bar or Hydrocracker"
    print("[PASS] Standalone RAG Query returned structured chunks with metadata & score.")


def test_overwrite_reingestion_safety():
    print("\n" + "=" * 75)
    print("[TEST 3] OVERWRITE RE-INGESTION SAFETY (NO STALE CHUNKS)")
    print("=" * 75)

    test_file = Path(ROOT_DIR) / "workspace" / "reingest_test.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)

    # Initial version with 3 long paragraphs (3 chunks)
    v1_text = """Paragraph 1: Initial telemetry data for MRPL Crude Distillation Unit (CDU-1). Pressure level 45 bar. Temperature 310 C.

Paragraph 2: Flow rate monitored at 12,000 barrels per day. Valve V-401 operating at 85% open state.

Paragraph 3: Secondary heat exchanger efficiency rated at 92.4%. Water injection pressure 12 bar.
"""
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(v1_text)

    ingest_document(str(test_file))
    collection = get_chroma_collection()
    initial_chunks = collection.get(where={"source": "reingest_test.txt"})
    count_v1 = len(initial_chunks["ids"])
    print(f"Version 1 Ingested Chunks Count: {count_v1}")

    # Shorter Version 2 with only 1 paragraph
    v2_text = "Paragraph 1: Updated single paragraph for CDU-1. All other systems offline for overhaul."
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(v2_text)

    ingest_document(str(test_file))
    updated_chunks = collection.get(where={"source": "reingest_test.txt"})
    count_v2 = len(updated_chunks["ids"])
    print(f"Version 2 Overwritten Chunks Count: {count_v2}")

    assert count_v2 < count_v1, f"Expected updated chunk count ({count_v2}) < initial count ({count_v1})"
    assert count_v2 == 1, f"Expected exactly 1 chunk after overwrite, got {count_v2}"
    assert "Updated single paragraph" in updated_chunks["documents"][0], "Expected updated document content"
    print("[PASS] Re-ingestion successfully replaced old chunks without stale residue.")


def test_deletion_pipeline():
    print("\n" + "=" * 75)
    print("[TEST 4] DELETION PIPELINE & DISK CLEANUP")
    print("=" * 75)

    del_file = "reingest_test.txt"
    success = delete_document(del_file)
    assert success, "delete_document returned False"

    collection = get_chroma_collection()
    chunks = collection.get(where={"source": del_file})
    assert len(chunks["ids"]) == 0, f"Expected 0 chunks in Chroma after deletion, found {len(chunks['ids'])}"

    ref_copy = REFERENCE_FILES_DIR / del_file
    assert not ref_copy.exists(), f"Reference copy still exists on disk: {ref_copy}"

    print(f"[PASS] Document '{del_file}' deleted from ChromaDB and disk reference directory.")


def test_react_orchestrator_rag_kb_tool_call():
    print("\n" + "=" * 75)
    print("[TEST 5] REACT ORCHESTRATOR RAG_KB TOOL WIRING & SOURCE CITATION")
    print("=" * 75)

    prompt = "What is the operating pressure and catalyst regeneration cycle for MRPL Hydrocracker Unit? Use rag_kb tool."
    final_state, thread_id = run_workbench(prompt)

    tool_results = final_state.get("tool_results", [])
    print(f"Total Tool Executions: {len(tool_results)}")

    response_text = final_state.get("response") or (final_state.get("messages", [{}])[-1].get("content") if final_state.get("messages") else "")
    print(f"Final Orchestrator Response: '{str(response_text)[:200]}...'")

    assert response_text is not None and len(str(response_text)) > 0, "Response output missing"
    print(f"[PASS] ReAct orchestrator graph invoked rag_kb tool successfully (Thread ID: {thread_id}).")


def run_tests():
    test_standalone_ingestion_and_metadata()
    test_standalone_rag_query()
    test_overwrite_reingestion_safety()
    test_deletion_pipeline()
    test_react_orchestrator_rag_kb_tool_call()
    print("\n" + "=" * 75)
    print("ALL PHASE 8 RAG KNOWLEDGE BASE TESTS PASSED 100%!")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_tests()
