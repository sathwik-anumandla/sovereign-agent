"""
tools/ocr_vlm.py (SIH PS 26117)
===============================
Phase 7: Two-Stage Confidence-Gated OCR Pipeline Tool.
Supports image formats (.png, .jpg, .jpeg, .tiff, .bmp) and PDF documents (.pdf via pypdfium2 rendering).
Primary Engine: PaddleOCR PP-Structure / PP-OCRv6 layout & text recognition engine.
Fallback Engine: Local Vision-Language Model (Qwen3-VL / Qwen2.5-VL via run_inference).
Confidence Threshold: OCR_CONFIDENCE_THRESHOLD = 0.90
"""

import os
import cv2
import tempfile
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any

from tool_interface import ToolInput, ToolResult, ToolStatus, audited_tool, validate_workspace_path
from phase1_inference import run_inference

# Module-level tunable confidence threshold
OCR_CONFIDENCE_THRESHOLD = 0.90

_paddle_ocr_engine = None


def _get_paddle_ppstructure_engine():
    """Lazy loader for PaddleOCR layout analysis and text recognition engine."""
    global _paddle_ocr_engine
    if _paddle_ocr_engine is None:
        try:
            from paddleocr import PaddleOCR
            _paddle_ocr_engine = PaddleOCR(lang="en")
        except Exception:
            _paddle_ocr_engine = None
    return _paddle_ocr_engine


def _convert_pdf_to_images(pdf_path: Path) -> List[Path]:
    """Converts PDF document pages into temporary PNG image files using pypdfium2."""
    image_paths = []
    try:
        import pypdfium2
        pdf = pypdfium2.PdfDocument(str(pdf_path))
        temp_dir = Path(tempfile.gettempdir()) / "ocr_vlm_pdf_cache"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        for idx, page in enumerate(pdf):
            pil_img = page.render(scale=2.0).to_pil()
            img_path = temp_dir / f"{pdf_path.stem}_page_{idx+1}.png"
            pil_img.save(str(img_path))
            image_paths.append(img_path)
    except Exception:
        image_paths = []
    return image_paths


class OCRVLMInput(ToolInput):
    """
    Multimodal OCR, Layout Analysis, and Diagram Inspection Tool.
    Extracts text, table structures, and reading order from document images or PDFs.
    Uses PP-Structure layout analysis as primary engine, falling back to Vision-Language Model
    if confidence is below OCR_CONFIDENCE_THRESHOLD (0.90).
    """
    file_path: str
    input_type: str = "printed"  # "printed", "handwritten", "diagram", "table"
    extract_mode: str = "text"   # "text", "describe", "table"
    session_id: Optional[str] = None


@audited_tool
def ocr_vlm(input_data: OCRVLMInput) -> ToolResult:
    """
    Executes confidence-gated two-stage OCR pipeline on document image or PDF.
    Stage 1: PP-Structure / PaddleOCR layout analysis & text recognition.
    Stage 2: Qwen3-VL / Qwen2.5-VL fallback if PP-Structure average confidence < 0.90.
    """
    try:
        session_id = input_data.session_id or "default_session"
        
        # Check if direct path exists, otherwise validate relative workspace path
        if Path(input_data.file_path).exists():
            abs_path = Path(input_data.file_path).resolve()
        else:
            try:
                abs_path = validate_workspace_path(input_data.file_path, session_id)
            except Exception:
                abs_path = Path(input_data.file_path).resolve()

        if not abs_path.exists():
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Document file not found: {input_data.file_path}",
                metadata={"session_id": session_id}
            )

        target_image_paths = []
        is_pdf = abs_path.suffix.lower() == ".pdf"

        if is_pdf:
            target_image_paths = _convert_pdf_to_images(abs_path)
            if not target_image_paths:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Failed to render PDF pages for file: {input_data.file_path}",
                    metadata={"session_id": session_id}
                )
        else:
            target_image_paths = [abs_path]

        # Force VLM engine if explicitly requesting visual diagram description
        if input_data.input_type == "diagram" or input_data.extract_mode == "describe":
            vlm_prompt = (
                "You are an expert industrial engineering drawing and P&ID diagram analyzer. "
                "Inspect this image and describe all components, valve tags, flow directions, "
                "labels, and key structural parameters in detail."
            )
            vlm_output = run_inference(
                prompt=vlm_prompt,
                role="vision_ocr",
                image_paths=[str(p) for p in target_image_paths]
            )
            return ToolResult(
                status=ToolStatus.SUCCESS,
                metadata={
                    "result": str(vlm_output).strip(),
                    "engine_used": "vlm",
                    "confidence": 1.0,
                    "pages_processed": len(target_image_paths),
                    "input_type": input_data.input_type,
                    "extract_mode": input_data.extract_mode
                }
            )

        # Stage 1: Try PaddleOCR Layout & Text Recognition on page image(s)
        engine = _get_paddle_ppstructure_engine()
        extracted_text_blocks = []
        all_confidences = []

        for img_path in target_image_paths:
            if engine is not None:
                try:
                    raw_res = engine.ocr(str(img_path))
                    if raw_res and len(raw_res) > 0 and raw_res[0] is not None:
                        res_obj = raw_res[0]
                        # Check dict format (PaddleOCR 3.7+ / paddlex)
                        if isinstance(res_obj, dict) and "rec_texts" in res_obj:
                            texts = res_obj.get("rec_texts", [])
                            scores = res_obj.get("rec_scores", [])
                            for txt, score in zip(texts, scores):
                                txt_str = str(txt).strip()
                                if txt_str:
                                    extracted_text_blocks.append(txt_str)
                                    all_confidences.append(float(score))
                        # Check list format (PaddleOCR 2.x)
                        elif isinstance(res_obj, (list, tuple)):
                            for item in res_obj:
                                if isinstance(item, (list, tuple)) and len(item) >= 2 and isinstance(item[1], (list, tuple)):
                                    text_str = str(item[1][0]).strip()
                                    conf_score = float(item[1][1])
                                    if text_str:
                                        extracted_text_blocks.append(text_str)
                                        all_confidences.append(conf_score)
                except Exception:
                    pass

            # Stage 1 Quality Check if PaddleOCR returned empty
            if engine is None or not extracted_text_blocks:
                img = cv2.imread(str(img_path))
                if img is not None:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
                    quality_score = min(round(laplacian_var / 500.0, 2), 1.0)
                    all_confidences.append(quality_score)

        avg_confidence = (sum(all_confidences) / len(all_confidences)) if all_confidences else 0.0

        # Stage 1 Pass Check: Avg Confidence >= Threshold (0.90)
        if avg_confidence >= OCR_CONFIDENCE_THRESHOLD and extracted_text_blocks:
            full_extracted_text = "\n".join(extracted_text_blocks)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                metadata={
                    "result": full_extracted_text,
                    "engine_used": "pp_structure",
                    "confidence": round(avg_confidence, 2),
                    "threshold": OCR_CONFIDENCE_THRESHOLD,
                    "pages_processed": len(target_image_paths),
                    "blocks_count": len(extracted_text_blocks)
                }
            )

        # Stage 2: Low Confidence (< 0.90) -> Trigger Qwen3-VL / Qwen2.5-VL Fallback
        vlm_prompt = (
            "You are an expert document OCR and layout transcription model. "
            "The primary fast OCR engine reported low confidence for this document. "
            "Please transcribe all visible text, section headings, numbers, key-value pairs, "
            "and table data accurately from the input document image."
        )
        vlm_output = run_inference(
            prompt=vlm_prompt,
            role="vision_ocr",
            image_paths=[str(p) for p in target_image_paths]
        )

        return ToolResult(
            status=ToolStatus.SUCCESS,
            metadata={
                "result": str(vlm_output).strip(),
                "engine_used": "vlm",
                "confidence": round(avg_confidence, 2),
                "threshold": OCR_CONFIDENCE_THRESHOLD,
                "pages_processed": len(target_image_paths),
                "fallback_reason": f"PP-Structure confidence ({avg_confidence:.2f}) < threshold ({OCR_CONFIDENCE_THRESHOLD})"
            }
        )

    except PermissionError as pe:
        return ToolResult(
            status=ToolStatus.ERROR,
            error=str(pe),
            metadata={"session_id": input_data.session_id}
        )
    except Exception as ex:
        return ToolResult(
            status=ToolStatus.ERROR,
            error=f"OCR tool execution error: {str(ex)}",
            metadata={"session_id": input_data.session_id}
        )
