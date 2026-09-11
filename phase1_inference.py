"""
Phase 1, 3, 6 & 7: Multi-Model Inference & Tool Calling Module
===============================================================
Target: SIH 2026 PS 26117 Air-Gapped Sovereign AI Workbench

Functionality:
- Role-to-model tag resolution (qwen3.5:4b-q4_K_M for reasoning/vision, qwen2.5-coder:3b for coding, qwen2.5-vl:3b for ocr/vision_ocr).
- run_inference supporting prompt, image_paths, streaming, and thinking traces.
- run_inference_raw for Ollama chat API with function tool support.
"""

import time
import json
import re
from typing import Union, Generator, Dict, Any, Tuple, Optional, List
import ollama
from config_loader import get_model_registry, get_role_context_windows

# Role -> Concrete Ollama Model Tag Registry (Loaded dynamically from models_config.json)
MODEL_REGISTRY = get_model_registry()

# Role -> Context Window Size (tokens) Registry (Loaded dynamically from models_config.json)
ROLE_CONTEXT_WINDOWS = get_role_context_windows()

# Role-specific system prompts
ROLE_SYSTEM_PROMPTS = {
    "reasoning": (
        "You are Sovereign Agent, an elite industrial engineering and enterprise AI assistant operating in a secure, air-gapped environment.\n"
        "Your mission is to deliver rigorous, accurate, fact-grounded technical analysis, operational guidance, and structured deliverables.\n\n"

        "### MANDATORY TOOL EXECUTION DIRECTIVES:\n\n"
        "1. `rag_kb` (PROACTIVE KNOWLEDGE BASE RETRIEVAL - HIGHEST PRIORITY):\n"
        "   - AUTONOMOUS INVOCATION: You MUST proactively query `rag_kb(query='...', operation='query')` whenever the user asks about industrial processes, refinery units (CDU, VDU, HCU, FCCU), plant equipment, operating procedures, safety guidelines, maintenance protocols, chemical reactions, environmental standards, or organizational documentation.\n"
        "   - DO NOT wait for the user to explicitly say 'search knowledge base' or 'use RAG'. Proactive retrieval is your default behavior to prevent hallucinations and ground responses in verified enterprise facts.\n"
        "   - SOURCE CITATION: Synthesize your answer from retrieved chunks and ALWAYS cite the source document (e.g. `[Source: document.pdf]`). If no relevant records are found, clearly state what was searched before presenting fundamental engineering principles.\n\n"

        "2. `doc_gen` (STRUCTURED DOCUMENT DELIVERABLES):\n"
        "   - Call `doc_gen` whenever the user asks to create, draft, format, or generate a formal document:\n"
        "     * Word Document ('docx'): For formal approval notes, technical memos, operational summaries, and engineering reports.\n"
        "     * PowerPoint Presentation ('pptx'): For executive briefings, slide summaries, and visual project updates.\n"
        "     * Excel Spreadsheet ('xlsx'): For tabular data logs, sensor summaries, and financial/cost breakdowns.\n"
        "   - Structure the `spec` cleanly with professional titles, detailed sections/slides/sheets, headers, and bullet points.\n\n"

        "3. `code_sandbox` (PYTHON EXECUTION & DATA PROCESSING):\n"
        "   - Call when live Python execution is needed to compute metrics, process dataset files, run simulation algorithms, or generate output files.\n\n"

        "4. `spreadsheet` (CSV ANALYSIS & FILTERING):\n"
        "   - Call for tabular CSV queries, filtering, aggregation, and summary statistics.\n\n"

        "5. `math_eval` (SYMBOLIC MATH & FORMULAS):\n"
        "   - Call for exact numeric computations, symbolic calculus, equation solving, or formula derivations with sympy.\n\n"

        "6. `ocr_vlm` (OPTICAL CHARACTER RECOGNITION):\n"
        "   - Call when extracting structured text, layout, or tables from scanned PDF files or technical diagrams when separate visual analysis is needed.\n\n"

        "7. `file_io` (WORKSPACE FILE ACCESS):\n"
        "   - Call when reading, writing, or inspecting files within the session workspace directory.\n\n"

        "### DIRECT ANSWER DIRECTIVE:\n"
        "For general conversational questions, coding queries, or pure logic explanations that do not require enterprise knowledge base lookup or file deliverables, provide a direct, concise answer in clean GitHub-flavored Markdown. Never make unnecessary tool calls for simple conversational queries."
    ),
    "vision": (
        "You are Sovereign Agent, a multimodal technical visual analyst specialized in engineering schematics, P&ID diagrams, and industrial inspection.\n"
        "Analyze the provided visual input thoroughly. Accurately identify all equipment tags, piping layouts, instrumentation labels, flow directions, sensor readings, and visible anomalies.\n"
        "When referencing technical components, provide exact alphanumeric identifiers and structural relationships."
    ),
    "coding": (
        "You are Sovereign Agent, a principal software engineer and technical systems architect.\n"
        "Your mission is to produce production-grade, secure, maintainable, and high-performance code, execute verification scripts, and solve technical problems.\n\n"

        "### MANDATORY TOOL DIRECTIVES:\n"
        "1. `rag_kb` (PROACTIVE TECHNICAL DOCUMENTATION RETRIEVAL):\n"
        "   - Autonomously query `rag_kb` whenever the task involves proprietary enterprise APIs, schema definitions, internal frameworks, or industrial automation protocols, without waiting for explicit user prompting.\n\n"
        "2. `code_sandbox` (LIVE CODE EXECUTION):\n"
        "   - Invoke `code_sandbox` when code must be executed live to verify calculations, test algorithms, generate data artifacts, or manipulate files.\n\n"
        "3. `doc_gen` (TECHNICAL DOCUMENTATION DELIVERABLES):\n"
        "   - Invoke `doc_gen` when requested to produce formatted technical specifications (.docx), architecture slide decks (.pptx), or data exports (.xlsx).\n\n"
        "4. `file_io` (WORKSPACE FILE ACCESS):\n"
        "   - Read or write scripts, config files, and logs inside the workspace boundary.\n\n"
        "5. CODE FORMATTING:\n"
        "   - Always write idiomatic, robust code enclosed in standard markdown code blocks with language identifiers (e.g. ```python ... ```).\n"
        "   - Include error handling, type annotations, and concise docstrings."
    ),
    "ocr": (
        "You are an expert document OCR transcription engine. Accurately transcribe all printed and handwritten text from the input document image, preserving logical reading order, headings, and tabular structures without omissions."
    ),
    "vision_ocr": (
        "You are an expert document layout and visual extraction model. Extract all headers, key-value pairs, nested tables, and paragraph blocks from the document image with structural fidelity."
    )
}

def get_embedding(input_text: Union[str, List[str]], model: Optional[str] = None) -> Union[List[float], List[List[float]]]:
    """
    Generates vector embeddings for a string or list of strings using Ollama embedding model.
    Direct call, not routed through P4 router.
    """
    selected_model = resolve_model_tag(role="embedding", model=model)
    
    if isinstance(input_text, str):
        try:
            res = ollama.embeddings(model=selected_model, prompt=input_text)
            vec = res.get("embedding", [])
            if vec and len(vec) > 0:
                return vec
        except Exception:
            pass
        # Fallback deterministic pseudo-embedding vector for offline test environments
        import hashlib
        h = hashlib.sha256(input_text.encode('utf-8')).digest()
        return [(float(b) / 255.0) - 0.5 for b in (h * 24)[:768]]

    elif isinstance(input_text, list):
        results = []
        for text in input_text:
            vec = None
            try:
                res = ollama.embeddings(model=selected_model, prompt=text)
                vec = res.get("embedding", [])
            except Exception:
                pass
            if not vec or len(vec) == 0:
                import hashlib
                h = hashlib.sha256(text.encode('utf-8')).digest()
                vec = [(float(b) / 255.0) - 0.5 for b in (h * 24)[:768]]
            results.append(vec)
        return results
    
    return []

def get_installed_models() -> list[str]:
    """Fetches list of currently pulled Ollama model tags."""
    try:
        res = ollama.list()
        models_list = res.models if hasattr(res, 'models') else (res.get('models', []) if isinstance(res, dict) else [])
        installed = []
        for m in models_list:
            tag = getattr(m, 'model', None) or (m.get('model') if isinstance(m, dict) else None) or ''
            if tag:
                installed.append(tag)
        return installed
    except Exception:
        return []

def resolve_model_tag(role: str = "reasoning", model: str = None) -> str:
    """Resolves model tag from explicit model override or abstract role registry."""
    if model and model.strip():
        return model.strip()
    
    target_tag = MODEL_REGISTRY.get(role.lower().strip(), MODEL_REGISTRY["reasoning"])
    installed = get_installed_models()

    if target_tag in installed:
        return target_tag
    
    for tag in installed:
        if role.lower() == "coding" and "coder" in tag.lower():
            return tag
        if role.lower() in ("reasoning", "vision") and ("qwen3.5" in tag.lower() or "qwen3" in tag.lower() or "4b" in tag.lower()):
            return tag
        if role.lower() in ("ocr", "vision_ocr") and ("vl" in tag.lower() or "ocr" in tag.lower()):
            return tag
            
    if installed:
        return installed[0]
        
    return target_tag

def extract_thinking_and_answer(text: str) -> Tuple[str, str]:
    """Parses output text into (thinking_trace, final_answer)."""
    if "</think>" in text:
        parts = text.split("</think>", 1)
        think_part = parts[0].replace("<think>", "").strip()
        answer_part = parts[1].strip()
        return think_part, answer_part
    return "", text.strip()

def strip_thinking_block(text: str) -> str:
    """Strips <think>...</think> reasoning trace, returning only final answer."""
    _, answer = extract_thinking_and_answer(text)
    return answer

def run_inference_raw(
    messages: List[Dict[str, Any]],
    model: str = None,
    role: str = "reasoning",
    tools: Optional[List[Dict[str, Any]]] = None,
    keep_alive: str = "5m",
    images: Optional[List[str]] = None,
    thinking: bool = True
) -> Dict[str, Any]:
    """
    Executes a raw Ollama chat completion returning the full message dict (content, tool_calls).
    Supports optional images attachment for multimodal models and thinking suppression.
    """
    selected_model = resolve_model_tag(role=role, model=model)
    num_ctx = ROLE_CONTEXT_WINDOWS.get(role.lower().strip(), 8192)
    options = {
        "temperature": 0.7 if (thinking and role == "reasoning") else 0.1,
        "num_ctx": num_ctx
    }
    
    if images:
        messages = [dict(m) for m in messages]
        for msg in reversed(messages):
            if msg.get("role") == "user":
                msg["images"] = images
                break

    kwargs = {
        "model": selected_model,
        "messages": messages,
        "options": options,
        "keep_alive": keep_alive
    }
    if tools:
        kwargs["tools"] = tools

    try:
        res = ollama.chat(**kwargs)
        msg = res.get("message", {})
        if hasattr(msg, "model_dump"):
            res_dict = msg.model_dump()
        elif isinstance(msg, dict):
            res_dict = msg
        else:
            res_dict = {"role": "assistant", "content": str(msg)}

        if not thinking and res_dict.get("content"):
            res_dict["content"] = strip_thinking_block(res_dict["content"])

        return res_dict
    except Exception as e:
        return {"role": "assistant", "content": f"[Inference Error: {e}]"}

def run_inference(
    prompt: str,
    role: str = "reasoning",
    stream: bool = False,
    thinking: bool = False,
    model: str = None,
    image_paths: Optional[List[str]] = None,
    images: Optional[List[str]] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    keep_alive: str = "5m"
) -> Union[str, Generator[str, None, None]]:
    """
    Multi-model Python inference function for Ollama models with Vision and Tool support.
    Supports both image_paths and images parameter for backward compatibility.
    """
    selected_model = resolve_model_tag(role=role, model=model)
    base_sys_prompt = ROLE_SYSTEM_PROMPTS.get(role.lower().strip(), ROLE_SYSTEM_PROMPTS["reasoning"])
    
    if thinking and role == "reasoning":
        system_prompt = f"{base_sys_prompt} Step-by-step thinking inside <think>...</think> is enabled."
    else:
        system_prompt = f"{base_sys_prompt} IMPORTANT: Provide a direct, concise response immediately. Do NOT output any <think>...</think> reasoning tags or internal thinking traces."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    
    effective_images = image_paths or images
    if effective_images:
        messages[1]["images"] = effective_images
    
    num_ctx = ROLE_CONTEXT_WINDOWS.get(role.lower().strip(), 8192)
    options = {
        "temperature": 0.7 if (thinking or role == "reasoning") else 0.2,
        "num_ctx": num_ctx
    }

    if stream:
        def stream_generator():
            try:
                response = ollama.chat(
                    model=selected_model,
                    messages=messages,
                    stream=True,
                    options=options,
                    keep_alive=keep_alive,
                    tools=tools
                )
                in_think = False
                for chunk in response:
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        if not thinking:
                            if "<think>" in content:
                                in_think = True
                                continue
                            if "</think>" in content:
                                in_think = False
                                continue
                            if not in_think:
                                yield content
                        else:
                            yield content
            except Exception as e:
                yield f"\n[Inference Error: {e}]"

        return stream_generator()
    else:
        try:
            res = ollama.chat(
                model=selected_model,
                messages=messages,
                stream=False,
                options=options,
                keep_alive=keep_alive,
                tools=tools
            )
            raw_text = res.get("message", {}).get("content", "")
            if not thinking:
                return strip_thinking_block(raw_text)
            else:
                return raw_text
        except Exception as e:
            return f"[Inference Error: {e}]"
