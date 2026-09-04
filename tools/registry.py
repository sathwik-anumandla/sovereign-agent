"""
tools/registry.py (SIH PS 26117)
================================
Central tool registry for Phase 6 Orchestrator Tool Integration.
Maps tool names to functions, Pydantic input types, and generates Ollama tool schemas.
"""

from typing import Dict, Any, Callable, Type
from tool_interface import ToolInput, ToolResult

from tools.math_eval import math_eval, MathEvalInput
from tools.file_io import file_io, FileIOInput
from tools.code_sandbox import code_sandbox, CodeSandboxInput
from tools.spreadsheet import spreadsheet, SpreadsheetInput
from tools.doc_gen import doc_gen, DocGenInput
from tools.ocr_vlm import ocr_vlm, OCRVLMInput
from tools.rag_kb import rag_kb, RagKbInput

# Tool Function Registry
TOOL_REGISTRY: Dict[str, Callable[[Any], ToolResult]] = {
    "math_eval": math_eval,
    "file_io": file_io,
    "code_sandbox": code_sandbox,
    "spreadsheet": spreadsheet,
    "doc_gen": doc_gen,
    "ocr_vlm": ocr_vlm,
    "rag_kb": rag_kb,
}

# Tool Input Class Registry for Pydantic coercion & validation
TOOL_INPUT_TYPES: Dict[str, Type[ToolInput]] = {
    "math_eval": MathEvalInput,
    "file_io": FileIOInput,
    "code_sandbox": CodeSandboxInput,
    "spreadsheet": SpreadsheetInput,
    "doc_gen": DocGenInput,
    "ocr_vlm": OCRVLMInput,
    "rag_kb": RagKbInput,
}


def build_tool_schemas() -> list[dict[str, Any]]:
    """
    Computes Ollama-compatible function tool schemas from Pydantic models.
    Cached in memory at import time.
    """
    schemas = []
    for tool_name, input_cls in TOOL_INPUT_TYPES.items():
        docstring = (input_cls.__doc__ or f"Execute {tool_name} tool").strip()
        schema = input_cls.model_json_schema()
        
        # Clean title / $defs if present
        schema.pop("title", None)
        
        schemas.append({
            "type": "function",
            "function": {
                "name": tool_name,
                "description": docstring,
                "parameters": schema
            }
        })
    return schemas


# Pre-computed tool schemas for Ollama chat API
OLLAMA_TOOL_SCHEMAS = build_tool_schemas()
