"""
Tool: math_eval (SIH PS 26117)
==============================
Safe, symbolic math evaluation and derivation engine using SymPy.
Never uses raw eval(). Provides step-by-step intermediate output and LaTeX formatting.
"""

from typing import Optional
from pydantic import Field
import sympy as sp
from tool_interface import ToolInput, ToolResult, ToolStatus, audited_tool


class MathEvalInput(ToolInput):
    expression: str
    variables: dict[str, float] = Field(default_factory=dict)
    mode: str = "evaluate"  # "evaluate" | "solve" | "simplify" | "differentiate" | "integrate"


class MathEvalResult(ToolResult):
    result: Optional[str] = None
    steps: list[str] = Field(default_factory=list)
    latex: Optional[str] = None


ALLOWED_MODES = {"evaluate", "solve", "simplify", "differentiate", "integrate"}


@audited_tool
def math_eval(input: MathEvalInput) -> MathEvalResult:
    mode = input.mode.lower().strip()
    if mode not in ALLOWED_MODES:
        return MathEvalResult(
            status=ToolStatus.ERROR,
            error=f"Invalid mode '{input.mode}'. Allowed modes: {ALLOWED_MODES}"
        )

    expr_str = input.expression.strip()
    steps = []
    
    symbol_names = set(input.variables.keys()).union({"x", "y", "z", "t"})
    sympy_symbols = {s: sp.Symbol(s) for s in symbol_names}

    try:
        parsed_expr = sp.sympify(expr_str, locals=sympy_symbols, evaluate=False)
        steps.append(f"Parsed Expression: {parsed_expr}")
    except Exception as e:
        return MathEvalResult(
            status=ToolStatus.ERROR,
            error=f"Failed to parse mathematical expression '{expr_str}': {str(e)}"
        )

    final_result_obj = None

    if mode == "evaluate":
        if input.variables:
            steps.append(f"Substitutions: {input.variables}")
            substituted = parsed_expr.subs({sp.Symbol(k): v for k, v in input.variables.items()})
            final_result_obj = substituted.evalf()
            steps.append(f"Evaluated Result: {final_result_obj}")
        else:
            final_result_obj = parsed_expr.evalf()
            steps.append(f"Evaluated Result: {final_result_obj}")

    elif mode == "simplify":
        steps.append("Applying algebraic simplification rules...")
        final_result_obj = sp.simplify(parsed_expr)
        steps.append(f"Simplified Expression: {final_result_obj}")

    elif mode == "differentiate":
        diff_var = sp.Symbol('x')
        for var_name in input.variables:
            diff_var = sp.Symbol(var_name)
            break
        steps.append(f"Applying differentiation rule with respect to variable '{diff_var}'")
        steps.append(f"d/d{diff_var} [ {parsed_expr} ]")
        final_result_obj = sp.diff(parsed_expr, diff_var)
        steps.append(f"Derivative Result: {final_result_obj}")

    elif mode == "integrate":
        int_var = sp.Symbol('x')
        for var_name in input.variables:
            int_var = sp.Symbol(var_name)
            break
        steps.append(f"Applying indefinite integration rule with respect to variable '{int_var}'")
        steps.append(f"∫ ( {parsed_expr} ) d{int_var}")
        final_result_obj = sp.integrate(parsed_expr, int_var)
        steps.append(f"Antiderivative Result: {final_result_obj} + C")

    elif mode == "solve":
        solve_var = sp.Symbol('x')
        for var_name in input.variables:
            solve_var = sp.Symbol(var_name)
            break
        steps.append(f"Setting expression = 0 and solving for '{solve_var}'")
        is_relational = isinstance(parsed_expr, (sp.Eq, sp.Ne, sp.Gt, sp.Lt, sp.Ge, sp.Le))
        equation = parsed_expr if is_relational else sp.Eq(parsed_expr, 0)
        steps.append(f"Equation: {equation}")
        final_result_obj = sp.solve(equation, solve_var)
        steps.append(f"Solutions: {final_result_obj}")

    latex_str = sp.latex(final_result_obj) if final_result_obj is not None else sp.latex(parsed_expr)

    return MathEvalResult(
        status=ToolStatus.SUCCESS,
        result=str(final_result_obj),
        steps=steps,
        latex=latex_str
    )
