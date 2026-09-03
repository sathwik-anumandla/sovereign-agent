"""
Phase 1 & 3: Multi-Model Inference & Role Registry Module
=========================================================
Target: SIH 2026 PS 26117 Air-Gapped Sovereign AI Workbench

Compute Optimization Strategy:
- "reasoning" & "vision" share the same Multimodal reasoning model tag: qwen3.5:4b-q4_K_M (0s VRAM swap cost)
- "coding" uses dedicated fast coding model: qwen2.5-coder:3b
- "ocr" uses dedicated specialized OCR pipeline model: qwen2.5-vl:3b
"""

import time
import json
import re
from typing import Union, Generator, Dict, Any, Tuple
import ollama

# Role -> Concrete Ollama Model Tag Registry (Explicit Qwen3.5 4B model)
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
        "and provide clear, structured explanations."
    ),
    "vision": (
        "You are a multimodal technical visual analyst. Inspect the image/diagram "
        "and describe key components, labels, and measurements accurately."
    ),
    "coding": (
        "You are an expert Python software engineer. Output clean, self-contained, executable Python code "
        "without unnecessary conversational filler."
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
    """
    Resolves model tag from explicit model override or abstract role registry.
    Falls back gracefully if the requested model is not installed.
    """
    if model and model.strip():
        return model.strip()
    
    target_tag = MODEL_REGISTRY.get(role.lower().strip(), MODEL_REGISTRY["reasoning"])
    installed = get_installed_models()

    if target_tag in installed:
        return target_tag
    
    # Try fuzzy match for tag
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

def run_inference(
    prompt: str,
    role: str = "reasoning",
    stream: bool = False,
    thinking: bool = False,
    model: str = None,
    image_paths: list[str] = None,
    keep_alive: str = "5m"
) -> Union[str, Generator[str, None, None]]:
    """
    Multi-model Python inference function for Ollama models with Vision support.
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
                    keep_alive=keep_alive
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
                keep_alive=keep_alive
            )
            raw_text = res.get("message", {}).get("content", "")
            if not thinking:
                return strip_thinking_block(raw_text)
            else:
                return raw_text
        except Exception as e:
            return f"[Inference Error: {e}]"

def run_inference_with_benchmark(
    prompt: str,
    role: str = "reasoning",
    stream: bool = False,
    thinking: bool = False,
    model: str = None,
    keep_alive: str = "5m"
) -> Tuple[Union[str, Generator[str, None, None]], Dict[str, Any]]:
    selected_model = resolve_model_tag(role=role, model=model)
    start_time = time.time()
    
    if stream:
        gen = run_inference(prompt=prompt, role=role, stream=True, thinking=thinking, model=selected_model, keep_alive=keep_alive)
        return gen, {"prompt_len": len(prompt), "role": role, "stream": True, "model": selected_model}
    else:
        res_text = run_inference(prompt=prompt, role=role, stream=False, thinking=thinking, model=selected_model, keep_alive=keep_alive)
        elapsed = time.time() - start_time
        
        stats = {
            "prompt_len": len(prompt),
            "response_len": len(res_text),
            "elapsed_sec": round(elapsed, 2),
            "role": role,
            "stream": False,
            "model": selected_model,
            "keep_alive": keep_alive
        }
        return res_text, stats


def benchmark_model_swap():
    print("\n" + "=" * 65)
    print("PHASE 3: EMPIRICAL MODEL SWAP COST BENCHMARK")
    print("=" * 65)

    reasoning_tag = resolve_model_tag(role="reasoning")
    coding_tag = resolve_model_tag(role="coding")

    print(f"Role 'reasoning' mapped to: {reasoning_tag}")
    print(f"Role 'coding' mapped to:    {coding_tag}")
    print("-" * 65)

    # Call 1: Cold/Reasoning Call
    prompt1 = "Explain why on-premise AI sovereignty matters for oil refineries in 1 sentence."
    print(f"\n[Step 1] Executing Role 'reasoning' ({reasoning_tag})...")
    t0 = time.time()
    ans1 = run_inference(prompt1, role="reasoning", keep_alive="5m")
    t1 = time.time()
    dur1 = round(t1 - t0, 2)
    print(f"Output: {ans1.strip()[:100]}...")
    print(f"[Duration]: {dur1}s")

    # Call 2: Model Swap -> Coding Role
    prompt2 = "Write a Python function `add(a, b)` returning `a + b`."
    print(f"\n[Step 2] SWAPPING MODEL: Executing Role 'coding' ({coding_tag})...")
    t2 = time.time()
    ans2 = run_inference(prompt2, role="coding", keep_alive="5m")
    t3 = time.time()
    swap_dur1 = round(t3 - t2, 2)
    print(f"Output:\n{ans2.strip()}")
    print(f"[Swap Cost (Reasoning -> Coding)]: {swap_dur1}s")

    # Call 3: Warm Call -> Coding Role
    prompt3 = "Write a Python function `multiply(a, b)` returning `a * b`."
    print(f"\n[Step 3] WARM CACHED CALL: Executing Role 'coding' ({coding_tag}) again...")
    t4 = time.time()
    ans3 = run_inference(prompt3, role="coding", keep_alive="5m")
    t5 = time.time()
    warm_dur = round(t5 - t4, 2)
    print(f"Output:\n{ans3.strip()}")
    print(f"[Warm Call Duration]: {warm_dur}s")

    # Call 4: Reverse Swap -> Reasoning Role
    print(f"\n[Step 4] REVERSE SWAP: Executing Role 'reasoning' ({reasoning_tag})...")
    t6 = time.time()
    ans4 = run_inference("What is 15 + 27?", role="reasoning", keep_alive="5m")
    t7 = time.time()
    swap_dur2 = round(t7 - t6, 2)
    print(f"Output: {ans4.strip()}")
    print(f"[Swap Cost (Coding -> Reasoning)]: {swap_dur2}s")

    print("\n" + "=" * 65)
    print("SWAP COST BENCHMARK SUMMARY")
    print("=" * 65)
    print(f"Reasoning Tag:                      {reasoning_tag}")
    print(f"Coding Tag:                         {coding_tag}")
    print(f"Swap Cost (Reasoning -> Coding):    {swap_dur1} seconds")
    print(f"Warm Cached Call:                  {warm_dur} seconds")
    print(f"Reverse Swap (Coding -> Reasoning): {swap_dur2} seconds")
    print(f"Keep-Alive TTL:                    5m (5 minutes)")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    benchmark_model_swap()
