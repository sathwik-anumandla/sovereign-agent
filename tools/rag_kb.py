"""
tools/rag_kb.py (SIH PS 26117)
=============================
Phase 8: RAG / Knowledge Base Vector Retrieval & Ingestion Pipeline.
Vector Store: ChromaDB (PersistentClient - embedded disk-backed)
Embedding Engine: nomic-embed-text via Ollama (direct call, not routed through P4)
Chunking Engine: RecursiveCharacterTextSplitter (layout-aware for OCR & text documents)
"""

import os
import shutil
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal
from pydantic import Field

from tool_interface import ToolInput, ToolResult, ToolStatus, audited_tool, validate_workspace_path
from phase1_inference import get_embedding
import chromadb

# Project Root & Persistence Paths
ROOT_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROMA_PERSIST_DIR = ROOT_DIR / "chroma_db"
REFERENCE_FILES_DIR = ROOT_DIR / "reference_files"

# Ensure directories exist
CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
REFERENCE_FILES_DIR.mkdir(parents=True, exist_ok=True)

# Shared ChromaDB PersistentClient & Collection
_chroma_client = None
_chroma_collection = None


def get_chroma_collection():
    """Lazy loader for ChromaDB persistent collection."""
    global _chroma_client, _chroma_collection
    if _chroma_collection is None:
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
        _chroma_collection = _chroma_client.get_or_create_collection(name="sovereign_kb")
    return _chroma_collection


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
                    # Break into structural sections by double newlines or block headers
                    blocks = [b.strip() for b in ocr_text.split("\n\n") if b.strip()]
                    for b in blocks:
                        sec_type = "table" if "|" in b or "\t" in b else ("heading" if len(b) < 60 and b.isupper() else "paragraph")
                        sections.append({"text": b, "section_type": sec_type})
        except Exception:
            pass

    if not sections:
        # Text-based document extraction fallback (.txt, .md, .py, .json, .csv, .docx, or readable text)
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
        except Exception as e:
            sections = [{"text": f"Document content from {file_path.name}", "section_type": "text"}]

    return sections if sections else [{"text": file_path.name, "section_type": "text"}]


def chunk_sections(sections: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Splits text WITHIN each structural section using RecursiveCharacterTextSplitter.
    Preserves document structure without flattening OCR or layout segments.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,  # ~512 tokens
        chunk_overlap=150, # ~50 tokens
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


def ingest_document(file_path: str, session_id: str = "default_session") -> Dict[str, Any]:
    """
    Full UI & Tool ingestion pipeline:
    1. Load & extract (layout-aware sections or P7 OCR pipeline)
    2. Chunk per section
    3. Batch embed via nomic-embed-text
    4. Store to ChromaDB with overwrite safety (collection.delete where source=filename)
    5. Save copy to reference_files/<filename>
    """
    # Validate file path
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

    # Copy to reference_files/<filename>
    ref_copy_path = REFERENCE_FILES_DIR / filename
    shutil.copy2(abs_path, ref_copy_path)

    # 1. Extract layout-aware sections
    sections = extract_sections_from_file(abs_path)

    # 2. Chunk sections
    chunks = chunk_sections(sections)
    if not chunks:
        return {"status": "error", "message": f"No text could be extracted from {filename}"}

    # 3. Batch embed texts
    chunk_texts = [c["text"] for c in chunks]
    embeddings = get_embedding(chunk_texts)

    # 4. Overwrite prior chunks in Chroma collection
    collection = get_chroma_collection()
    try:
        collection.delete(where={"source": filename})
    except Exception:
        pass

    # Prepare ids and metadatas
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ids = [f"{filename}_{c['chunk_index']}" for c in chunks]
    metadatas = [
        {
            "source": filename,
            "chunk_index": c["chunk_index"],
            "section_type": c["section_type"],
            "ingestion_timestamp": timestamp
        }
        for c in chunks
    ]

    collection.add(
        ids=ids,
        documents=chunk_texts,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return {
        "status": "success",
        "source": filename,
        "chunks_ingested": len(chunks),
        "ref_copy_path": str(ref_copy_path)
    }


def delete_document(filename: str) -> bool:
    """
    Deletes all vector chunks for a document from Chroma collection and removes disk copy.
    """
    collection = get_chroma_collection()
    try:
        collection.delete(where={"source": filename})
    except Exception:
        pass

    ref_file = REFERENCE_FILES_DIR / filename
    if ref_file.exists():
        try:
            ref_file.unlink()
        except Exception:
            pass

    return True


def get_reference_files() -> List[Dict[str, Any]]:
    """
    Derives live reference file list directly from Chroma collection metadata.
    Prevents drift between manifest files and vector database.
    """
    collection = get_chroma_collection()
    try:
        res = collection.get(include=["metadatas"])
    except Exception:
        return []

    sources = {}
    if res and "metadatas" in res and res["metadatas"]:
        for meta in res["metadatas"]:
            if meta:
                src = meta.get("source")
                if src:
                    if src not in sources:
                        sources[src] = {
                            "source": src,
                            "chunk_count": 0,
                            "section_types": set(),
                            "last_ingested": meta.get("ingestion_timestamp", "")
                        }
                    sources[src]["chunk_count"] += 1
                    if meta.get("section_type"):
                        sources[src]["section_types"].add(meta.get("section_type"))

    file_list = []
    for src, info in sources.items():
        file_list.append({
            "source": info["source"],
            "chunk_count": info["chunk_count"],
            "section_types": list(info["section_types"]),
            "last_ingested": info["last_ingested"]
        })
    return file_list


class RagKbInput(ToolInput):
    """
    RAG Knowledge Base Document Retrieval and Ingestion Tool.
    Searches or manages vector database of technical reference documents and manuals.
    Operations:
    - 'query': Embeds query string and retrieves top-k semantically relevant structured document chunks.
    - 'ingest': Extracts, chunks, embeds, and stores reference document from file_path.
    - 'delete': Removes document and associated vector chunks from knowledge base by source filename.
    - 'list': Returns live list of ingested reference files currently stored in collection.
    """
    query: str = ""
    file_path: Optional[str] = None
    top_k: int = 5
    metadata_filter: Optional[Dict[str, Any]] = Field(default=None, description="Metadata key-value where filter for Chroma query")
    operation: Literal["query", "ingest", "delete", "list"] = "query"
    session_id: Optional[str] = None


@audited_tool
def rag_kb(input_data: RagKbInput) -> ToolResult:
    """
    Executes RAG Knowledge Base operation (query, ingest, delete, list).
    """
    try:
        session_id = input_data.session_id or "default_session"
        collection = get_chroma_collection()

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

            # Embed query vector
            query_vector = get_embedding(input_data.query)

            kwargs = {
                "query_embeddings": [query_vector],
                "n_results": min(input_data.top_k, 20),
                "include": ["documents", "metadatas", "distances"]
            }
            if input_data.metadata_filter:
                kwargs["where"] = input_data.metadata_filter

            query_res = collection.query(**kwargs)

            retrieved_chunks = []
            if query_res and "documents" in query_res and query_res["documents"]:
                docs = query_res["documents"][0]
                metas = query_res["metadatas"][0] if "metadatas" in query_res else [{}] * len(docs)
                dists = query_res["distances"][0] if "distances" in query_res else [0.0] * len(docs)

                for text, meta, dist in zip(docs, metas, dists):
                    score = round(1.0 - float(dist), 4) if dist is not None else 1.0
                    retrieved_chunks.append({
                        "text": text,
                        "source": meta.get("source", "unknown"),
                        "chunk_index": meta.get("chunk_index", 0),
                        "section_type": meta.get("section_type", "text"),
                        "score": score
                    })

            # Format summary text for agent consumption
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
