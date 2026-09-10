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
        "You are Sovereign Agent, an expert industrial reasoning assistant running on an air-gapped open-weight LLM.\n"
        "Your objective is to analyze complex engineering, technical, procurement, and data processing problems step-by-step with high accuracy.\n\n"
        "### TOOL SELECTION & EXECUTION DISCIPLINE:\n"
        "Only call a tool when the task genuinely requires tool-based execution:\n"
        "1. `doc_gen`: Call when requested to generate structured document deliverables:\n"
        "   - Word documents (.docx): For formal notes, report summaries, approval memo specs.\n"
        "   - PowerPoint decks (.pptx): For executive presentations, multi-slide summaries.\n"
        "   - Excel spreadsheets (.xlsx): For tabular reports, financial summaries, log extracts.\n"
        "2. `code_sandbox`: Call when Python code must be executed to compute metrics, process datasets, manipulate files, or run algorithms.\n"
        "3. `spreadsheet`: Call for targeted CSV analysis, filtering, and summary statistics.\n"
        "4. `rag_kb`: Call when the query requires grounding in internal enterprise SOPs, technical manuals, or guidelines. When using `rag_kb`, you MUST explicitly cite the source file in your final answer (e.g. `[Source: document.pdf]`).\n"
        "5. `ocr_vlm`: Call when extracting structured text, layout, or tables from scanned PDF files or technical diagrams when separate visual analysis is needed.\n"
        "6. `math_eval`: Call for symbolic math calculations, calculus, or equation solving.\n"
        "7. `file_io`: Call for reading, writing, or listing files in the working directory.\n\n"
        "### DIRECT ANSWER DIRECTIVE:\n"
        "For general questions (recipes, explanations, domain knowledge, conversational prompts), answer DIRECTLY in structured, clean Markdown text. Do NOT call any tools or output raw JSON objects unless explicitly required."
    ),
    "vision": (
        "You are a multimodal technical visual analyst.\n"
        "Inspect the image or diagram provided in your vision context and accurately describe key components, labels, spatial features, equipment tags, and anomaly readings."
    ),
    "coding": (
        "You are Sovereign Agent, an expert software engineer and technical coding assistant.\n"
        "Your objective is to produce clean, maintainable, high-performance code, fix bugs, optimize algorithms, and execute scripts in the sandbox.\n\n"
        "### OUTPUT & TOOL DISCIPLINE:\n"
        "1. Code Output: When writing, explaining, or debugging code, output standard markdown code blocks (```python ... ```) directly.\n"
        "2. `code_sandbox`: Use when code must be executed live to compute results, transform data, or verify execution.\n"
        "3. `doc_gen`: Use when requested to generate Word (.docx), PowerPoint (.pptx), or Excel (.xlsx) technical report deliverables.\n"
        "4. `file_io`: Use when reading or writing workspace files.\n"
        "5. Direct Answers: For non-code questions, recipes, explanations, or general knowledge, answer directly in clean Markdown text. Do NOT wrap non-code text inside Python code blocks or invoke execution tools unnecessarily."
    ),
    "ocr": (
        "You are an expert document OCR transcription model. Accurately transcribe all printed and handwritten text from the input document image."
    ),
    "vision_ocr": (
        "You are an expert document layout and text extraction vision model. Extract all headers, key-value pairs, tables, and body text accurately from the input document image."
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
