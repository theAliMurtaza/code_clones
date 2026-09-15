"""
classifier.py
Determines the clone type (Type-1 through Type-4) for a pair of
code fragments given their GraphCodeBERT embeddings and tokens.

Classification taxonomy:
  Type-1: Token similarity ≥ TYPE1_TOKEN_SIM (exact copy / whitespace/comment only)
  Type-2: Sem ≥ TYPE2_SEM_SIM AND tok ≥ TYPE2_TOK_SIM (structurally same, renamed)
  Type-3: Sem ≥ TYPE3_SEM_SIM AND tok ≥ TYPE3_TOK_SIM (near-miss — syntactic overlap)
  Type-4: Cross-language OR tok < TYPE3_TOK_SIM (pure semantic clone — different syntax)
  None:   Sem < threshold (not a clone)

Each threshold is configurable via settings.
"""

from __future__ import annotations
import re
import difflib
import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from config import get_settings
from fragmenter import Fragment

logger   = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class CloneResult:
    clone_type:     str         # "Type-1" … "Type-4"
    similarity:     float       # cosine similarity of embeddings
    token_sim:      float       # difflib token ratio
    description:    str
    cross_language: bool


# ── Similarity helpers ────────────────────────────────────────────────
def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-D vectors."""
    return float(cosine_similarity(a.reshape(1, -1), b.reshape(1, -1))[0][0])


def _normalise(code: str) -> str:
    """Strip whitespace and lower-case for token comparison."""
    return re.sub(r'\s+', ' ', code.strip().lower())


def token_similarity(code_a: str, code_b: str) -> float:
    """
    difflib SequenceMatcher ratio on token lists.
    Tokens are split on word boundaries after normalisation.
    """
    tokens_a = re.findall(r'\w+', _normalise(code_a))
    tokens_b = re.findall(r'\w+', _normalise(code_b))
    if not tokens_a or not tokens_b:
        return 0.0
    return difflib.SequenceMatcher(None, tokens_a, tokens_b).ratio()


KEYWORDS = {
    'def', 'return', 'if', 'else', 'elif', 'while', 'for', 'in', 'class',
    'try', 'except', 'finally', 'with', 'as', 'import', 'from', 'pass',
    'break', 'continue', 'and', 'or', 'not', 'is', 'lambda', 'yield',
    'public', 'private', 'protected', 'static', 'void', 'int', 'float',
    'double', 'boolean', 'char', 'interface', 'extends',
    'implements', 'new', 'this', 'super', 'null', 'true', 'false'
}


def parameterize_tokens(code: str) -> list[str]:
    tokens = re.findall(r'\w+', _normalise(code))
    param_tokens = []
    id_map = {}
    for tok in tokens:
        if tok in KEYWORDS or tok.isdigit():
            param_tokens.append(tok)
        else:
            if tok not in id_map:
                id_map[tok] = f'ID_{len(id_map)}'
            param_tokens.append(id_map[tok])
    return param_tokens


def parameterized_token_similarity(code_a: str, code_b: str) -> float:
    """
    Computes token similarity after normalizing identifier names (parameterization).
    Identical AST/syntax structures with renamed variables achieve high score.
    """
    pt_a = parameterize_tokens(code_a)
    pt_b = parameterize_tokens(code_b)
    if not pt_a or not pt_b:
        return 0.0
    return difflib.SequenceMatcher(None, pt_a, pt_b).ratio()


def _clone_description(clone_type: str, cross_lang: bool) -> str:
    descs = {
        "Type-1": "Exact copy — only whitespace or comment differences",
        "Type-2": "Same structure, identifiers or literals renamed",
        "Type-3": "Near-miss — statements added, removed, or modified",
        "Type-4": "Semantic clone — different implementation, same behaviour",
    }
    if cross_lang:
        return "Semantic clone — cross-language implementation" if clone_type == "Type-4" else f"{descs.get(clone_type, '')} · cross-language"
    return descs.get(clone_type, "")


# ── Main classifier ───────────────────────────────────────────────────
def classify_pair(
    frag_a:    Fragment,
    frag_b:    Fragment,
    vec_a:     np.ndarray,
    vec_b:     np.ndarray,
    threshold: float = None,
) -> Optional[CloneResult]:
    """
    Classify a pair of fragments.
    Returns None if the pair does not meet the minimum threshold.
    """
    threshold = threshold or settings.DEFAULT_THRESHOLD
    sem       = cosine_sim(vec_a, vec_b)

    if sem < threshold:
        return None   # not a clone

    tok         = token_similarity(frag_a.code, frag_b.code)
    cross_lang  = frag_a.language != frag_b.language

    # ── Cross-language pairs are Type-4 semantic clones by definition ───
    if cross_lang:
        clone_type = "Type-4"

    # ── Type-1: exact (or whitespace-only) copy ───────────────────────
    elif tok >= settings.TYPE1_TOKEN_SIM:
        clone_type = "Type-1"

    else:
        param_tok = parameterized_token_similarity(frag_a.code, frag_b.code)
        lines_a = [l.strip() for l in frag_a.code.splitlines() if l.strip()]
        lines_b = [l.strip() for l in frag_b.code.splitlines() if l.strip()]
        same_stmt_count = (len(lines_a) == len(lines_b))

        # ── Type-2: structurally identical, identifiers/literals renamed
        if same_stmt_count and (tok >= settings.TYPE2_TOK_SIM or param_tok >= 0.85) and sem >= settings.TYPE2_SEM_SIM:
            clone_type = "Type-2"

        # ── Type-3: near-miss — syntactic modifications, substantial token overlap
        elif (tok >= settings.TYPE3_TOK_SIM or param_tok >= 0.55) and sem >= settings.TYPE3_SEM_SIM:
            clone_type = "Type-3"

        # ── Type-4: purely semantic equivalence (different syntax / implementation)
        else:
            clone_type = "Type-4"

    return CloneResult(
        clone_type   = clone_type,
        similarity   = round(sem, 6),
        token_sim    = round(tok, 6),
        description  = _clone_description(clone_type, cross_lang),
        cross_language = cross_lang,
    )

