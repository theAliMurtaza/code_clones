"""
classifier.py
Determines the clone type (Type-1 through Type-4) for a pair of
code fragments given their CodeBERT embeddings.

Classification rules:
  Type-1: Token similarity ≥ 0.97  (exact / whitespace only)
  Type-2: Sem ≥ 0.93 AND tok ≥ 0.82  (structurally same, renamed)
  Type-3: Sem ≥ 0.84  (near-miss — some statements differ)
  Type-4: Sem ≥ threshold  (semantic equivalence only)
  None:   Sem < threshold  (not a clone)

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


def _clone_description(clone_type: str, cross_lang: bool) -> str:
    descs = {
        "Type-1": "Exact copy — only whitespace or comment differences",
        "Type-2": "Same structure, identifiers or literals renamed",
        "Type-3": "Near-miss — statements added, removed, or modified",
        "Type-4": "Semantic clone — different implementation, same behaviour",
    }
    base = descs.get(clone_type, "")
    return (base + " · cross-language") if cross_lang else base


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

    # ── Type-1: exact (or whitespace-only) copy ───────────────────────
    if tok >= settings.TYPE1_TOKEN_SIM:
        clone_type = "Type-1"

    # ── Type-2: structurally identical, surface names differ ──────────
    elif sem >= settings.TYPE2_SEM_SIM and tok >= settings.TYPE2_TOK_SIM:
        clone_type = "Type-2"

    # ── Type-3: near-miss — some lines added/removed/modified ─────────
    elif sem >= settings.TYPE3_SEM_SIM:
        clone_type = "Type-3"

    # ── Type-4: purely semantic equivalence ───────────────────────────
    else:
        clone_type = "Type-4"

    return CloneResult(
        clone_type   = clone_type,
        similarity   = round(sem, 6),
        token_sim    = round(tok, 6),
        description  = _clone_description(clone_type, cross_lang),
        cross_language = cross_lang,
    )
