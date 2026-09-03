"""
Tool: spreadsheet (SIH PS 26117)
===============================
Tabular data analysis layer supporting read, filter, aggregate, and compute operations on CSV/Excel files.
Pure analysis layer (uses pandas/openpyxl). Formatting/presentation is deferred to doc_gen.
"""

from typing import Optional, Any
from pydantic import Field
import pandas as pd
from tool_interface import ToolInput, ToolResult, ToolStatus, audited_tool, validate_workspace_path


class SpreadsheetInput(ToolInput):
    file_path: str
    operation: str  # "read" | "filter" | "aggregate" | "compute"
    params: dict = Field(default_factory=dict)
    session_id: str


class SpreadsheetResult(ToolResult):
    data: Optional[list[dict[str, Any]]] = None
    summary: Optional[str] = None


ALLOWED_OPERATIONS = {"read", "filter", "aggregate", "compute"}


@audited_tool
def spreadsheet(input: SpreadsheetInput) -> SpreadsheetResult:
    op = input.operation.lower().strip()
    if op not in ALLOWED_OPERATIONS:
        return SpreadsheetResult(
            status=ToolStatus.ERROR,
            error=f"Unsupported spreadsheet operation '{input.operation}'. Allowed: {ALLOWED_OPERATIONS}"
        )

    # Validate workspace boundary
    try:
        validated_path = validate_workspace_path(input.file_path, input.session_id, create_parents=False)
    except Exception as err:
        return SpreadsheetResult(status=ToolStatus.ERROR, error=str(err))

    if not validated_path.exists():
        return SpreadsheetResult(
            status=ToolStatus.ERROR,
            error=f"Spreadsheet file '{input.file_path}' not found in workspace"
        )

    # Load dataframe
    try:
        if validated_path.suffix.lower() in [".xlsx", ".xls"]:
            df = pd.read_excel(validated_path, engine="openpyxl")
        elif validated_path.suffix.lower() in [".csv", ".txt"]:
            df = pd.read_csv(validated_path)
        else:
            return SpreadsheetResult(
                status=ToolStatus.ERROR,
                error=f"Unsupported file format '{validated_path.suffix}'. Expected .xlsx, .xls, or .csv"
            )
    except Exception as e:
        return SpreadsheetResult(
            status=ToolStatus.ERROR,
            error=f"Failed loading spreadsheet '{validated_path.name}': {str(e)}"
        )

    params = input.params or {}

    if op == "read":
        limit = params.get("limit", 100)
        df_sub = df.head(limit)
        data = df_sub.to_dict(orient="records")
        summary = f"Successfully read {len(df_sub)} rows of {len(df)} total rows across {len(df.columns)} columns."
        return SpreadsheetResult(status=ToolStatus.SUCCESS, data=data, summary=summary)

    elif op == "filter":
        col = params.get("column")
        val = params.get("value")
        operator = params.get("operator", "==")

        if not col or col not in df.columns:
            return SpreadsheetResult(
                status=ToolStatus.ERROR,
                error=f"Filter column '{col}' not found. Available columns: {list(df.columns)}"
            )

        if operator == "==":
            filtered_df = df[df[col] == val]
        elif operator == "!=":
            filtered_df = df[df[col] != val]
        elif operator == ">":
            filtered_df = df[df[col] > val]
        elif operator == "<":
            filtered_df = df[df[col] < val]
        elif operator == "contains":
            filtered_df = df[df[col].astype(str).str.contains(str(val), na=False)]
        else:
            return SpreadsheetResult(
                status=ToolStatus.ERROR,
                error=f"Unsupported filter operator '{operator}'. Allowed: ==, !=, >, <, contains"
            )

        data = filtered_df.to_dict(orient="records")
        summary = f"Filter on '{col} {operator} {val}' returned {len(filtered_df)} matching rows."
        return SpreadsheetResult(status=ToolStatus.SUCCESS, data=data, summary=summary)

    elif op == "aggregate":
        group_by = params.get("group_by")
        agg_col = params.get("column")
        agg_func = params.get("function", "sum")  # sum, mean, count, min, max

        if not agg_col or agg_col not in df.columns:
            return SpreadsheetResult(
                status=ToolStatus.ERROR,
                error=f"Aggregation column '{agg_col}' not found in spreadsheet"
            )

        if group_by:
            if group_by not in df.columns:
                return SpreadsheetResult(
                    status=ToolStatus.ERROR,
                    error=f"Group by column '{group_by}' not found in spreadsheet"
                )
            agg_df = df.groupby(group_by)[agg_col].agg(agg_func).reset_index()
            data = agg_df.to_dict(orient="records")
            summary = f"Aggregated '{agg_col}' ({agg_func}) grouped by '{group_by}'."
        else:
            val = float(df[agg_col].agg(agg_func))
            data = [{f"{agg_func}_{agg_col}": val}]
            summary = f"Overall aggregation '{agg_func}' for column '{agg_col}' = {val}."

        return SpreadsheetResult(status=ToolStatus.SUCCESS, data=data, summary=summary)

    elif op == "compute":
        new_col = params.get("target_column")
        formula_expr = params.get("formula")  # e.g., "colA + colB"

        if not new_col or not formula_expr:
            return SpreadsheetResult(
                status=ToolStatus.ERROR,
                error="Params 'target_column' and 'formula' are required for operation 'compute'"
            )

        try:
            df[new_col] = df.eval(formula_expr)
            data = df.head(100).to_dict(orient="records")
            summary = f"Successfully computed new column '{new_col}' using formula '{formula_expr}'."
            return SpreadsheetResult(status=ToolStatus.SUCCESS, data=data, summary=summary)
        except Exception as e:
            return SpreadsheetResult(
                status=ToolStatus.ERROR,
                error=f"Failed computing formula '{formula_expr}': {str(e)}"
            )

    return SpreadsheetResult(status=ToolStatus.ERROR, error="Unexpected operation error")
