"""
router/keyword_check.py (SIH PS 26117)
=======================================
Stage 2: Heuristic keyword inspection guard (~35 high-precision terms).
Matches user prompt against code debugging, syntax, action verb, and tooling terms.
Uses word-boundary regex matching to prevent false positives (e.g. 'repo' in 'report').
"""

import re
from typing import Optional
from router.schemas import RouteDecision

CODING_KEYWORDS = [
    # Error/debugging signals
    "debug", "traceback", "stack trace", "stacktrace", "exception", 
    "error message", "compile error", "syntax error", "null pointer", "segfault", "crash",
    
    # Code action verbs
    "refactor", "optimize this function", "fix this code", "write a script", 
    "write a function", "implement", "unit test", "test case",
    
    # Code structure/syntax literals
    "def ", "class ", "import ", "function(", "return ", "```", 
    "console.log", "print(", "for loop", "while loop",
    
    # File/repo/dev-tooling terms (with word boundaries)
    "repo", "repository", "pull request", "commit", "merge conflict", 
    "dependency", "package.json", "requirements.txt", "dockerfile", 
    "api endpoint", "database query", "sql query", "regex",
    
    # Language names
    "python", "javascript", "java", "typescript", "sql", "bash script", "shell script"
]


def check_keywords(prompt: str) -> Optional[RouteDecision]:
    """
    Stage 2 Waterfall check.
    Checks prompt for strong coding-intent keyword signals using word boundary precision.
    """
    if not prompt or not prompt.strip():
        return None

    prompt_lower = prompt.lower()

    # Pure language names
    LANGUAGE_NAMES = {"python", "javascript", "java", "typescript", "sql", "bash script", "shell script"}
    CONCEPTUAL_WORDS = {"what", "why", "how", "explain", "compare", "list", "describe", "summarize", "advantage", "advantages", "disadvantage", "disadvantages"}
    ACTION_VERBS = {"write", "script", "code", "fix", "debug", "run", "execute", "create", "implement", "build", "refactor", "test", "optimize", "def", "class", "import"}

    is_conceptual = any(word in prompt_lower for word in CONCEPTUAL_WORDS)
    has_action = any(verb in prompt_lower for verb in ACTION_VERBS)

    for kw in CODING_KEYWORDS:
        # If it's just a language name in a conceptual query without action verbs, skip forcing coding role
        if kw in LANGUAGE_NAMES and is_conceptual and not has_action:
            continue

        # Check literal match if contains punctuation/spaces (e.g. "def ", "```", "function(")
        if any(char in kw for char in [" ", "(", "`", "."]):
            if kw in prompt_lower:
                return RouteDecision(role="coding", confidence=0.85, method="keyword")
        else:
            # Word boundary regex match for single words (e.g. "repo", "crash", "python")
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, prompt_lower):
                return RouteDecision(role="coding", confidence=0.85, method="keyword")

    return None
