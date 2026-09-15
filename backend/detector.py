"""
detector.py  —  Two-stage clone detection pipeline (GraphCodeBERT)

Stage 1: Embed all fragments → cosine similarity → candidate pairs
Stage 2: If fine-tuned model exists → pairwise classifier
         Otherwise                  → use Stage-1 cosine similarity directly

This means the system works correctly out-of-the-box with the base model.
Fine-tuning on BigCloneBench gives an additional ~3% F1 improvement.
"""

from __future__ import annotations
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity as cos_sim

from config import get_settings
from fragmenter import Fragment, extract_fragments
from classifier import token_similarity, _clone_description, parameterized_token_similarity

logger   = logging.getLogger(__name__)
settings = get_settings()

# Stage-1 cosine similarity threshold for candidate pre-filtering.
# Set lower than the final threshold so we don't miss borderline clones.
STAGE1_THRESHOLD = 0.40

# Use FAISS index above this many fragments
FAISS_THRESHOLD  = 150


@dataclass
class UploadedFile:
    filename: str
    content:  str


@dataclass
class DetectedClone:
    file_a:         str
    file_b:         str
    lines_a:        list
    lines_b:        list
    clone_lines_a:  list
    clone_lines_b:  list
    clone_type:     str
    similarity:     float
    token_sim:      float
    cross_language: bool
    description:    str
    code_a:         str
    code_b:         str


@dataclass
class DetectionResult:
    clone_pairs:     list  = field(default_factory=list)
    total_fragments: int   = 0
    runtime_seconds: float = 0.0
    stage1_pairs:    int   = 0
    stage2_pairs:    int   = 0
    errors:          list  = field(default_factory=list)
    mode:            str   = "embedding"   # "embedding" | "classifier"


# ── Candidate search ──────────────────────────────────────────────────
def _candidates_faiss(vectors: np.ndarray, threshold: float):
    try:
        import faiss
        vecs  = vectors.astype(np.float32).copy()
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        vecs /= (norms + 1e-9)
        n, d  = vecs.shape
        index = faiss.IndexFlatIP(d)
        index.add(vecs)
        k       = min(50, n)
        sims, I = index.search(vecs, k)
        seen, pairs, scores = set(), [], {}
        for i in range(n):
            for rank in range(k):
                j   = int(I[i, rank])
                sim = float(sims[i, rank])
                if j <= i or sim < threshold:
                    continue
                key = (i, j)
                if key not in seen:
                    seen.add(key)
                    pairs.append(key)
                    scores[key] = sim
        return pairs, scores
    except ImportError:
        return _candidates_brute(vectors, threshold)


def _candidates_brute(vectors: np.ndarray, threshold: float):
    mat    = cos_sim(vectors)
    n      = len(vectors)
    pairs  = []
    scores = {}
    for i in range(n):
        for j in range(i + 1, n):
            if mat[i, j] >= threshold:
                pairs.append((i, j))
                scores[(i, j)] = float(mat[i, j])
    return pairs, scores


# ── Clone type classifier ─────────────────────────────────────────────
def _classify(prob: float, tok: float, threshold: float,
              lang_a: str, lang_b: str,
              code_a: str = "", code_b: str = "") -> Optional[str]:
    if prob < threshold:
        return None
    if lang_a != lang_b:
        return "Type-4"
    if tok >= settings.TYPE1_TOKEN_SIM:
        return "Type-1"

    param_tok = parameterized_token_similarity(code_a, code_b) if (code_a and code_b) else tok
    lines_a = [l.strip() for l in code_a.splitlines() if l.strip()] if code_a else []
    lines_b = [l.strip() for l in code_b.splitlines() if l.strip()] if code_b else []
    same_stmt_count = (len(lines_a) == len(lines_b)) if (lines_a and lines_b) else False

    # ── Type-2: structurally identical, identifiers/literals renamed
    if same_stmt_count and (tok >= settings.TYPE2_TOK_SIM or param_tok >= 0.85) and prob >= settings.TYPE2_SEM_SIM:
        return "Type-2"
    # ── Type-3: near-miss — syntactic modifications, substantial token overlap
    elif (tok >= settings.TYPE3_TOK_SIM or param_tok >= 0.55) and prob >= settings.TYPE3_SEM_SIM:
        return "Type-3"
    # ── Type-4: purely semantic equivalence (different syntax / implementation)
    else:
        return "Type-4"


# ── Main detection pipeline ───────────────────────────────────────────
def run_detection(
    files:     list,
    threshold: float = None,
    engine    = None,
) -> DetectionResult:
    threshold = threshold or settings.DEFAULT_THRESHOLD
    result    = DetectionResult()
    t0        = time.perf_counter()

    if engine is None:
        from graphcodebert.engine import get_engine
        engine = get_engine()

    # ── Step 1: Fragment extraction ───────────────────────────────────
    all_frags: list[Fragment] = []
    for f in files:
        try:
            frags = extract_fragments(f.content, f.filename)
            logger.info(f"{f.filename}: {len(frags)} fragments")
            all_frags.extend(frags)
        except Exception as exc:
            logger.error(f"Fragment extraction failed for {f.filename}: {exc}")
            result.errors.append(f"{f.filename}: {exc}")

    result.total_fragments = len(all_frags)
    if len(all_frags) < 2:
        result.runtime_seconds = round(time.perf_counter() - t0, 3)
        return result

    # ── Step 2: Embed all fragments ───────────────────────────────────
    codes = [f.code     for f in all_frags]
    langs = [f.language for f in all_frags]
    logger.info(f"Embedding {len(codes)} fragments...")
    try:
        vectors = engine.embed_batch(codes, langs)  # (N, 768)
    except Exception as exc:
        result.errors.append(f"Embedding failed: {exc}")
        result.runtime_seconds = round(time.perf_counter() - t0, 3)
        return result

    # ── Step 3: Stage-1 candidate filtering ──────────────────────────
    if len(all_frags) > FAISS_THRESHOLD:
        candidates, cosine_scores = _candidates_faiss(vectors, STAGE1_THRESHOLD)
    else:
        candidates, cosine_scores = _candidates_brute(vectors, STAGE1_THRESHOLD)

    # Remove self-matches
    candidates = [
        (i, j) for i, j in candidates
        if not (all_frags[i].file == all_frags[j].file
                and all_frags[i].start_line == all_frags[j].start_line)
    ]
    result.stage1_pairs = len(candidates)
    logger.info(f"Stage 1: {len(candidates)} candidate pairs (cosine >= {STAGE1_THRESHOLD})")

    if not candidates:
        result.runtime_seconds = round(time.perf_counter() - t0, 3)
        logger.warning(
            "No candidates passed Stage-1 filter. "
            f"Try lowering the threshold below {threshold}."
        )
        return result

    # ── Step 4: Score each candidate ─────────────────────────────────
    # If a fine-tuned model exists → use GraphCodeBERT pairwise classifier (Stage 2).
    # Otherwise → use Stage-1 cosine similarity as the clone probability directly.
    # Cosine similarity of GraphCodeBERT embeddings is already highly effective.

    use_classifier = engine.is_fine_tuned
    result.mode    = "classifier" if use_classifier else "embedding"

    if use_classifier:
        logger.info(f"Stage 2 (pairwise classifier): scoring {len(candidates)} pairs...")
        try:
            pair_tuples = [
                (all_frags[i].code, all_frags[i].language,
                 all_frags[j].code, all_frags[j].language)
                for i, j in candidates
            ]
            probs = engine.predict_batch(pair_tuples)
        except Exception as exc:
            logger.warning(f"Classifier failed ({exc}), falling back to cosine similarity")
            probs = [cosine_scores.get((i, j), 0.0) for i, j in candidates]
            result.mode = "embedding_fallback"
    else:
        logger.info(
            "No fine-tuned model found — using GraphCodeBERT embedding cosine similarity. "
            "Run train.py on BigCloneBench for the pairwise classifier."
        )
        probs = [cosine_scores.get((i, j), 0.0) for i, j in candidates]

    # ── Step 5: Classify and assemble results ─────────────────────────
    for (i, j), prob in zip(candidates, probs):
        frag_a = all_frags[i]
        frag_b = all_frags[j]
        tok    = token_similarity(frag_a.code, frag_b.code)
        cross  = frag_a.language != frag_b.language
        ctype  = _classify(prob, tok, threshold, frag_a.language, frag_b.language, frag_a.code, frag_b.code)
        if ctype is None:
            continue
        result.clone_pairs.append(DetectedClone(
            file_a        = frag_a.file,
            file_b        = frag_b.file,
            lines_a       = [frag_a.start_line, frag_a.end_line],
            lines_b       = [frag_b.start_line, frag_b.end_line],
            clone_lines_a = frag_a.line_range,
            clone_lines_b = frag_b.line_range,
            clone_type    = ctype,
            similarity    = round(prob, 6),
            token_sim     = round(tok, 6),
            cross_language= cross,
            description   = _clone_description(ctype, cross),
            code_a        = frag_a.code,
            code_b        = frag_b.code,
        ))

    result.stage2_pairs    = len(result.clone_pairs)
    result.runtime_seconds = round(time.perf_counter() - t0, 3)
    result.clone_pairs.sort(key=lambda p: p.similarity, reverse=True)

    logger.info(
        f"Detection done [{result.mode}]: {result.stage2_pairs} clones "
        f"in {result.runtime_seconds}s  (stage1={result.stage1_pairs})"
    )
    return result
