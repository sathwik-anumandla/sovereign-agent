"""
Phase 1, 3 & 6: Multi-Model Inference & Tool Calling Module
===========================================================
Target: SIH 2026 PS 26117 Air-Gapped Sovereign AI Workbench

Functionality:
- Implement run_inference and run_inference_raw for Ollama chat API with function tool support.
- Role-to-model tag resolution (qwen3.5:4b-q4_K_M for reasoning/vision, qwen2.5-coder:3b for coding).
- keep_alive VRAM caching ("5m").
"""

import time
import json
import re
from typing import Union, Generator, Dict, Any, Tuple, Optional, List
import ollama

# Role -> Concrete Ollama Model Tag Registry
MODEL_REGISTRY = {
    "reasoning": "qwen3.5:4b-q4_K_M",
    "vision": "qwen3.5:4b-q4_K_M",    # Shared with reasoning model -> 0s VRAM swap
    "coding": "qwen2.5-coder:3b",
    "ocr": "qwen2.5-vl:3b"
}

# Role-specific system prompts
ROLE_SYSTEM_PROMPTS = {
    "reasoning": (
        "You are an expert technical reasoning assistant. Analyze the problem step-by-step "
        "and use tools when available to calculate, read, or generate documents."
    ),
    "vision": (
        "You are a multimodal technical visual analyst. Inspect the image/diagram "
        "and describe key components, labels, and measurements accurately."
    ),
    "coding": (
        "You are an expert Python software engineer. Output clean, self-contained, executable Python code "
        "or execute tools to perform calculations and data operations."
    ),
    "ocr": (
        "You are an expert document OCR transcription model. Accurately transcribe all printed "
        "and handwritten text from the document image."
    )
}

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
        if role.lower() == "ocr" and ("vl" in tag.lower() or "ocr" in tag.lower()):
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
    keep_alive: str = "5m"
) -> Dict[str, Any]:
    """
    Executes a raw Ollama chat completion returning the full message dict (content, tool_calls).
    """
    selected_model = resolve_model_tag(role=role, model=model)
    options = {
        "temperature": 0.7 if role == "reasoning" else 0.2
    }
    
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
        # Convert message object/dict to dict
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
    image_paths: list[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    keep_alive: str = "5m"
) -> Union[str, Generator[str, None, None]]:
    """
    Multi-model Python inference function for Ollama models with Vision and Tool support.
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
    
    if image_paths:
        messages[1]["images"] = image_paths
    
    options = {
        "temperature": 0.7 if (thinking or role == "reasoning") else 0.2
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
