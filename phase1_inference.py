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

# Role -> Concrete Ollama Model Tag Registry
MODEL_REGISTRY = {
    "reasoning": "qwen3.5:4b-q4_K_M",
    "vision": "qwen3.5:4b-q4_K_M",      # Shared with reasoning model -> 0s VRAM swap
    "coding": "qwen2.5-coder:3b",
    "ocr": "qwen2.5-vl:3b",
    "vision_ocr": "qwen2.5-vl:3b",       # Dedicated Vision-OCR fallback model
    "embedding": "nomic-embed-text"      # Embedding model for RAG KB
}

# Role -> Context Window Size (tokens) Registry
ROLE_CONTEXT_WINDOWS = {
    "reasoning": 8192,
    "vision": 8192,
    "coding": 8192,
    "ocr": 8192,
    "vision_ocr": 8192
}

# Role-specific system prompts
ROLE_SYSTEM_PROMPTS = {
    "reasoning": (
        "You are an expert technical reasoning assistant. Analyze the problem step-by-step "
        "and use tools when available to calculate, read, query knowledge bases, or generate documents. "
        "When answering using information retrieved via knowledge base query tools (rag_kb), "
        "you MUST explicitly cite the source filename (e.g. [Source: document.pdf]) in your final response.\n\n"
        "TOOL USE DISCIPLINE:\n"
        "Only call a tool when the task genuinely requires it:\n"
        "- Use `rag_kb` only when the question needs grounding in ingested reference documents (e.g. company-specific standards, uploaded reports, internal procedures) — not for general domain knowledge you already know.\n"
        "- Use `code_sandbox` only when code must actually be written and executed.\n"
        "- Use `ocr_vlm` only when a scanned/structured document image is present in this request.\n"
        "- If an image has already been provided to you directly in this conversation (i.e. you can see it as part of your input), do NOT call `ocr_vlm` or any other tool to \"retrieve\" it — you already have it. Only call `ocr_vlm` when you need to extract structured text from a scanned document that has NOT already been shown to you visually.\n"
        "- Use `math_eval` only for calculations you cannot reliably do directly.\n"
        "- Use `file_io` only when reading/writing/listing files is explicitly needed.\n\n"
        "If a question can be answered directly from your own knowledge, answer directly without calling any tool. Do not call a tool \"just in case\" — each unnecessary tool call adds latency and noise to the audit trail."
    ),
    "vision": (
        "You are a multimodal technical visual analyst. Inspect the image/diagram "
        "and describe key components, labels, and measurements accurately."
    ),
    "coding": (
        "You are an expert Python software engineer. Execute Python code via the `code_sandbox` tool "
        "to perform calculations, process data files, and solve tasks.\n\n"
        "TOOL USE DISCIPLINE:\n"
        "Only call a tool when the task genuinely requires it:\n"
        "- Use `code_sandbox` when Python code needs to be executed.\n"
        "- If an input file is specified in the prompt or workspace context (e.g. `sensor_logs.csv`), it is already staged in your working execution directory — open it directly with a relative file path inside `code_sandbox` without needing extra `file_io` calls."
    ),
    "ocr": (
        "You are an expert document OCR transcription model. Accurately transcribe all printed "
        "and handwritten text from the document image."
    ),
    "vision_ocr": (
        "You are an expert document layout and text extraction vision model. Extract all text, "
        "headers, key-value pairs, and table data accurately from the input document image."
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
    images: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Executes a raw Ollama chat completion returning the full message dict (content, tool_calls).
    Supports optional images attachment for multimodal models.
    """
    selected_model = resolve_model_tag(role=role, model=model)
    num_ctx = ROLE_CONTEXT_WINDOWS.get(role.lower().strip(), 8192)
    options = {
        "temperature": 0.7 if role == "reasoning" else 0.2,
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
            return msg.model_dump()
        elif isinstance(msg, dict):
            return msg
        else:
            return {"role": "assistant", "content": str(msg)}
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
        system_prompt = f"{base_sys_prompt} Provide direct, concise output."

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
