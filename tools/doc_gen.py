"""
Tool: doc_gen (SIH PS 26117)
============================
Output deliverable generator layer for Word (.docx), PowerPoint (.pptx), and Excel (.xlsx).
Uses format-agnostic content primitives (TextBlock, TableBlock, ImageBlock, ChartBlock)
composed into format-specific specs (DocxSpec, PptxSpec, XlsxSpec).
"""

from pathlib import Path
from typing import Union, Optional, Any
from pydantic import BaseModel, Field
import docx
from docx.shared import Inches, Pt, RGBColor
from pptx import Presentation
from pptx.util import Inches as PptxInches, Pt as PptxPt
import openpyxl
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from tool_interface import ToolInput, ToolResult, ToolStatus, audited_tool, validate_workspace_path


# --- Shared Content Primitives ---

class TextBlock(BaseModel):
    heading: Optional[str] = None
    body: str


class TableBlock(BaseModel):
    headers: list[str]
    rows: list[list[str]]


class ImageBlock(BaseModel):
    path: str
    caption: Optional[str] = None


class ChartBlock(BaseModel):
    chart_type: str = "bar"  # "bar" | "line" | "pie"
    data: dict[str, list[Any]] = Field(default_factory=dict)
    title: Optional[str] = None


# --- Format-Specific Top-Level Specs ---

class DocxSpec(BaseModel):
    title: str
    sections: list[Union[TextBlock, TableBlock, ImageBlock]]


class SlideSpec(BaseModel):
    title: str
    blocks: list[Union[TextBlock, TableBlock, ImageBlock, ChartBlock]]


class PptxSpec(BaseModel):
    slides: list[SlideSpec]


class SheetSpec(BaseModel):
    name: str
    data: list[list[Any]]
    chart: Optional[ChartBlock] = None


class XlsxSpec(BaseModel):
    sheets: list[SheetSpec]


# --- Tool Input & Result Models ---

class DocGenInput(ToolInput):
    format: str  # "docx" | "pptx" | "xlsx"
    spec: dict
    output_path: str
    session_id: str


class DocGenResult(ToolResult):
    output_path: Optional[str] = None
    format: Optional[str] = None


# --- Renderers ---

def _render_docx(spec: DocxSpec, output_file: Path, session_id: str):
    doc = docx.Document()
    doc.add_heading(spec.title, level=0)

    for block in spec.sections:
        if isinstance(block, TextBlock):
            if block.heading:
                doc.add_heading(block.heading, level=1)
            doc.add_paragraph(block.body)

        elif isinstance(block, TableBlock):
            table = doc.add_table(rows=1, cols=len(block.headers))
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            for idx, header in enumerate(block.headers):
                hdr_cells[idx].text = str(header)

            for row_data in block.rows:
                row_cells = table.add_row().cells
                for idx, cell_val in enumerate(row_data):
                    if idx < len(row_cells):
                        row_cells[idx].text = str(cell_val)

        elif isinstance(block, ImageBlock):
            try:
                img_path = validate_workspace_path(block.path, session_id, create_parents=False)
                if img_path.exists():
                    doc.add_picture(str(img_path), width=Inches(5))
                    if block.caption:
                        p = doc.add_paragraph(block.caption)
                        p.runs[0].font.italic = True
            except Exception as e:
                doc.add_paragraph(f"[Image Error: {e}]")

    doc.save(str(output_file))


def _render_pptx(spec: PptxSpec, output_file: Path, session_id: str):
    prs = Presentation()
    blank_layout = prs.slide_layouts[6]  # Blank slide

    for slide_spec in spec.slides:
        slide = prs.slides.add_slide(blank_layout)
        
        # Add slide title
        txBox = slide.shapes.add_textbox(PptxInches(0.8), PptxInches(0.5), PptxInches(8.4), PptxInches(1))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = slide_spec.title
        p.font.size = PptxPt(28)
        p.font.bold = True

        top_offset = 1.6
        for block in slide_spec.blocks:
            if isinstance(block, TextBlock):
                tb = slide.shapes.add_textbox(PptxInches(0.8), PptxInches(top_offset), PptxInches(8.4), PptxInches(1.5))
                tf2 = tb.text_frame
                tf2.word_wrap = True
                if block.heading:
                    p_head = tf2.paragraphs[0]
                    p_head.text = block.heading
                    p_head.font.size = PptxPt(20)
                    p_head.font.bold = True
                    p_body = tf2.add_paragraph()
                else:
                    p_body = tf2.paragraphs[0]
                p_body.text = block.body
                p_body.font.size = PptxPt(16)
                top_offset += 1.8

            elif isinstance(block, TableBlock):
                rows = len(block.rows) + 1
                cols = len(block.headers)
                table_shape = slide.shapes.add_table(rows, cols, PptxInches(0.8), PptxInches(top_offset), PptxInches(8.4), PptxInches(1.8))
                table = table_shape.table

                for c_idx, header in enumerate(block.headers):
                    table.cell(0, c_idx).text = str(header)

                for r_idx, row_data in enumerate(block.rows):
                    for c_idx, val in enumerate(row_data):
                        if c_idx < cols:
                            table.cell(r_idx + 1, c_idx).text = str(val)

                top_offset += 2.2

            elif isinstance(block, ImageBlock):
                try:
                    img_path = validate_workspace_path(block.path, session_id, create_parents=False)
                    if img_path.exists():
                        slide.shapes.add_picture(str(img_path), PptxInches(0.8), PptxInches(top_offset), width=PptxInches(4.5))
                        top_offset += 3.0
                except Exception:
                    top_offset += 0.5

    prs.save(str(output_file))


def _render_xlsx(spec: XlsxSpec, output_file: Path):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove default sheet

    for sheet_spec in spec.sheets:
        ws = wb.create_sheet(title=sheet_spec.name)
        for row in sheet_spec.data:
            ws.append(row)

        if sheet_spec.chart:
            c = sheet_spec.chart
            if c.chart_type == "line":
                chart_obj = LineChart()
            elif c.chart_type == "pie":
                chart_obj = PieChart()
            else:
                chart_obj = BarChart()

            chart_obj.title = c.title or "Data Chart"
            max_row = len(sheet_spec.data)
            max_col = len(sheet_spec.data[0]) if sheet_spec.data else 1
            data_ref = Reference(ws, min_col=2, min_row=1, max_col=max_col, max_row=max_row)
            cats_ref = Reference(ws, min_col=1, min_row=2, max_row=max_row)
            chart_obj.add_data(data_ref, titles_from_data=True)
            chart_obj.set_categories(cats_ref)
            ws.add_chart(chart_obj, "E2")

    wb.save(str(output_file))


@audited_tool
def doc_gen(input: DocGenInput) -> DocGenResult:
    fmt = input.format.lower().strip()
    if fmt not in {"docx", "pptx", "xlsx"}:
        return DocGenResult(
            status=ToolStatus.ERROR,
            error=f"Unsupported format '{input.format}'. Allowed: docx, pptx, xlsx"
        )

    # Validate output path in workspace boundary
    try:
        output_file = validate_workspace_path(input.output_path, input.session_id, create_parents=True)
    except Exception as err:
        return DocGenResult(status=ToolStatus.ERROR, error=str(err))

    try:
        if fmt == "docx":
            spec_obj = DocxSpec.model_validate(input.spec)
            _render_docx(spec_obj, output_file, input.session_id)

        elif fmt == "pptx":
            spec_obj = PptxSpec.model_validate(input.spec)
            _render_pptx(spec_obj, output_file, input.session_id)

        elif fmt == "xlsx":
            spec_obj = XlsxSpec.model_validate(input.spec)
            _render_xlsx(spec_obj, output_file)

        return DocGenResult(
            status=ToolStatus.SUCCESS,
            output_path=str(output_file),
            format=fmt
        )

    except Exception as e:
        return DocGenResult(
            status=ToolStatus.ERROR,
            error=f"Failed generating '{fmt}' document: {str(e)}"
        )
