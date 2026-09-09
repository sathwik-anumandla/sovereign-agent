"""
tools/rag_kb.py (SIH PS 26117)
=============================
Phase 8: RAG / Knowledge Base Vector Retrieval & Ingestion Pipeline.
Vector Store: PostgreSQL + pgvector (rag_embeddings table)
Embedding Engine: nomic-embed-text via Ollama (direct call, not routed through P4)
Chunking Engine: RecursiveCharacterTextSplitter (layout-aware for OCR & text documents)
"""

import os
import shutil
import datetime
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal
from pydantic import Field

from tool_interface import ToolInput, ToolResult, ToolStatus, audited_tool, validate_workspace_path
from phase1_inference import get_embedding
from tools.db import execute_query

logger = logging.getLogger(__name__)

# Project Root & Persistence Paths
ROOT_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REFERENCE_FILES_DIR = ROOT_DIR / "reference_files"
REFERENCE_FILES_DIR.mkdir(parents=True, exist_ok=True)


def extract_sections_from_file(file_path: Path) -> List[Dict[str, str]]:
    """
    Extracts layout-aware structural sections (paragraphs, tables, headings) from document files.
    Routes scanned/image/PDF documents through P7 ocr_vlm pipeline.
    """
    ext = file_path.suffix.lower()
    is_ocr_target = ext in [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"]

    sections = []

    if is_ocr_target:
        try:
            from tools.ocr_vlm import ocr_vlm, OCRVLMInput
            res = ocr_vlm(OCRVLMInput(file_path=str(file_path), input_type="printed", extract_mode="text"))
            if res.status == ToolStatus.SUCCESS:
                ocr_text = str(res.metadata.get("result", "")).strip()
                if ocr_text:
                    blocks = [b.strip() for b in ocr_text.split("\n\n") if b.strip()]
                    for b in blocks:
                        sec_type = "table" if "|" in b or "\t" in b else ("heading" if len(b) < 60 and b.isupper() else "paragraph")
                        sections.append({"text": b, "section_type": sec_type})
        except Exception:
            pass

    if not sections:
        try:
            raw_text = ""
            if ext == ".docx":
                import docx
                doc = docx.Document(str(file_path))
                raw_text = "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            else:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    raw_text = f.read()

            blocks = [b.strip() for b in raw_text.split("\n\n") if b.strip()]
            for b in blocks:
                sec_type = "table" if "|" in b or ("," in b and "\n" in b) else ("heading" if b.startswith("#") or (len(b) < 80 and not b.endswith(".")) else "paragraph")
                sections.append({"text": b, "section_type": sec_type})
        except Exception:
            sections = [{"text": f"Document content from {file_path.name}", "section_type": "text"}]

    return sections if sections else [{"text": file_path.name, "section_type": "text"}]


def chunk_sections(sections: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Splits text WITHIN each structural section using RecursiveCharacterTextSplitter.
    Preserves document structure without flattening OCR or layout segments.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = []
    chunk_index = 0
    for sec in sections:
        sec_text = sec["text"].strip()
        sec_type = sec.get("section_type", "paragraph")
        if not sec_text:
            continue

        split_texts = splitter.split_text(sec_text)
        for text_part in split_texts:
            if text_part.strip():
                chunks.append({
                    "text": text_part.strip(),
                    "section_type": sec_type,
                    "chunk_index": chunk_index
                })
                chunk_index += 1

    return chunks


def _format_vector(vec: List[float]) -> str:
    """Formats float list to PostgreSQL vector syntax string '[0.1,0.2,...]'."""
    return '[' + ','.join(str(float(v)) for v in vec) + ']'


def ingest_document(file_path: str, session_id: str = "default_session") -> Dict[str, Any]:
    """
    Full UI & Tool ingestion pipeline storing vectors into PostgreSQL pgvector table:
    1. Load & extract (layout-aware sections or P7 OCR pipeline)
    2. Chunk per section
    3. Batch embed via nomic-embed-text
    4. Store to PostgreSQL rag_embeddings table (with overwrite cleanup)
    5. Save copy to reference_files/<filename>
    """
    if Path(file_path).exists():
        abs_path = Path(file_path).resolve()
    else:
        try:
            abs_path = validate_workspace_path(file_path, session_id)
        except Exception:
            abs_path = Path(file_path).resolve()

    if not abs_path.exists():
        raise FileNotFoundError(f"Reference file not found: {file_path}")

    filename = abs_path.name

    ref_copy_path = REFERENCE_FILES_DIR / filename
    shutil.copy2(abs_path, ref_copy_path)

    sections = extract_sections_from_file(abs_path)
    chunks = chunk_sections(sections)
    if not chunks:
        return {"status": "error", "message": f"No text could be extracted from {filename}"}

    chunk_texts = [c["text"] for c in chunks]
    embeddings = get_embedding(chunk_texts)

    # Clean up prior document embeddings
    execute_query("DELETE FROM rag_embeddings WHERE source_filename = %s", (filename,), commit=True)

    # Insert new embeddings
    for c, emb in zip(chunks, embeddings):
        vec_str = _format_vector(emb)
        execute_query(
            """
            INSERT INTO rag_embeddings (source_filename, chunk_index, content, embedding)
            VALUES (%s, %s, %s, %s::vector)
            """,
            (filename, c["chunk_index"], c["text"], vec_str),
            commit=True
        )

    return {
        "status": "success",
        "source": filename,
        "chunks_ingested": len(chunks),
        "ref_copy_path": str(ref_copy_path)
    }


def delete_document(filename: str) -> bool:
    """Deletes document vector chunks from PostgreSQL and removes reference disk copy."""
    try:
        execute_query("DELETE FROM rag_embeddings WHERE source_filename = %s", (filename,), commit=True)
    except Exception as e:
        logger.error(f"Error deleting rag_embeddings for '{filename}': {e}")

    ref_file = REFERENCE_FILES_DIR / filename
    if ref_file.exists():
        try:
            ref_file.unlink()
        except Exception:
            pass

    return True


def get_reference_files() -> List[Dict[str, Any]]:
    """Returns live list of reference files from PostgreSQL rag_embeddings table."""
    try:
        rows = execute_query(
            """
            SELECT source_filename, COUNT(*) as chunk_count, MAX(created_at) as last_ingested
            FROM rag_embeddings
            GROUP BY source_filename
            """,
            fetch_all=True
        ) or []

        file_list = []
        for r in rows:
            file_list.append({
                "source": r[0],
                "chunk_count": r[1],
                "section_types": ["paragraph"],
                "last_ingested": str(r[2]) if r[2] else ""
            })
        return file_list
    except Exception as e:
        logger.error(f"Error getting reference files: {e}")
        return []


class RagKbInput(ToolInput):
    """
    RAG Knowledge Base Document Retrieval and Ingestion Tool.
    Searches or manages vector database of technical reference documents and manuals.
    """
    query: str = ""
    file_path: Optional[str] = None
    top_k: int = 5
    metadata_filter: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filter")
    operation: Literal["query", "ingest", "delete", "list"] = "query"
    session_id: Optional[str] = None


@audited_tool
def rag_kb(input_data: RagKbInput) -> ToolResult:
    """Executes RAG Knowledge Base operation (query, ingest, delete, list)."""
    try:
        session_id = input_data.session_id or "default_session"

        if input_data.operation == "ingest":
            if not input_data.file_path:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="file_path is required for RAG ingestion operation.",
                    metadata={"session_id": session_id}
                )
            res = ingest_document(input_data.file_path, session_id=session_id)
            res["result"] = f"Successfully ingested reference document '{res.get('source')}' ({res.get('chunks_ingested')} chunks)."
            return ToolResult(
                status=ToolStatus.SUCCESS,
                metadata=res
            )

        elif input_data.operation == "delete":
            filename = input_data.file_path or input_data.query
            if not filename:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Target filename is required for delete operation.",
                    metadata={"session_id": session_id}
                )
            delete_document(filename)
            msg = f"Successfully deleted document '{filename}' from Knowledge Base."
            return ToolResult(
                status=ToolStatus.SUCCESS,
                metadata={"filename": filename, "deleted": True, "result": msg}
            )

        elif input_data.operation == "list":
            files = get_reference_files()
            msg = f"Retrieved {len(files)} active reference documents from Knowledge Base."
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=files,
                metadata={"count": len(files), "result": msg}
            )

        else: # operation == "query"
            if not input_data.query:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Query string cannot be empty for RAG query operation.",
                    metadata={"session_id": session_id}
                )

            query_vector = get_embedding(input_data.query)
            vec_str = _format_vector(query_vector[0] if isinstance(query_vector[0], list) else query_vector)
            limit = min(input_data.top_k, 20)

            rows = execute_query(
                """
                SELECT source_filename, chunk_index, content, 1 - (embedding <=> %s::vector) AS score
                FROM rag_embeddings
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (vec_str, vec_str, limit),
                fetch_all=True
            ) or []

            retrieved_chunks = []
            for r in rows:
                retrieved_chunks.append({
                    "source": r[0],
                    "chunk_index": r[1],
                    "text": r[2],
                    "section_type": "paragraph",
                    "score": round(float(r[3]), 4) if r[3] is not None else 1.0
                })

            summary_lines = []
            for item in retrieved_chunks:
                summary_lines.append(f"[Source: {item['source']} | Chunk {item['chunk_index']} | Score {item['score']}]\n{item['text']}")
            summary_str = "\n\n---\n\n".join(summary_lines) if summary_lines else "No relevant documents found in Knowledge Base."

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=retrieved_chunks,
                metadata={
                    "query": input_data.query,
                    "count": len(retrieved_chunks),
                    "top_k": input_data.top_k,
                    "session_id": session_id,
                    "result": summary_str
                }
            )

    except Exception as ex:
        return ToolResult(
            status=ToolStatus.ERROR,
            error=f"RAG Knowledge Base tool execution error: {str(ex)}",
            metadata={"session_id": input_data.session_id}
        )
