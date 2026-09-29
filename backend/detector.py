"""Compare every cross-file fragment pair, with optional trained semantic scoring."""

from __future__ import annotations
import logging
import time
from dataclasses import dataclass, field

import numpy as np

from config import get_settings
from fragmenter import Fragment, extract_fragments
from classifier import code_tokens, parameterize_tokens, _clone_description
from difflib import SequenceMatcher
from itertools import combinations

logger   = logging.getLogger(__name__)
settings = get_settings()

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
    mode:            str   = "structural"


def run_detection(files: list, threshold: float = None, engine=None) -> DetectionResult:
    threshold = settings.DEFAULT_THRESHOLD if threshold is None else threshold
    result = DetectionResult()
    started = time.perf_counter()
    fragments = []
    for source in files:
        # An extraction failure must fail the job, not silently report zero clones.
        fragments.extend(extract_fragments(source.content, source.filename))

    tokens = [code_tokens(f.code, f.language) for f in fragments]
    # Ignore empty/comment-only fragments and isolated closing braces.
    usable = [(f, t) for f, t in zip(fragments, tokens)
              if len(t) >= 3 and any(token.isidentifier() for token in t)
              and not (t[-1] in ("{", ":") and any(k in t for k in ("class", "interface", "enum")))]
    fragments = [f for f, _ in usable]
    tokens = [t for _, t in usable]
    result.total_fragments = len(fragments)
    if len(fragments) > settings.MAX_FRAGMENTS_PER_JOB:
        raise ValueError(
            f"Analysis is limited to {settings.MAX_FRAGMENTS_PER_JOB} code fragments per job; "
            f"received {len(fragments)}. Split the folder into smaller uploads."
        )
    candidates = [(i, j) for i, j in combinations(range(len(fragments)), 2)
                  if fragments[i].file != fragments[j].file]
    result.stage1_pairs = len(candidates)
    if not candidates:
        result.runtime_seconds = round(time.perf_counter() - started, 3)
        return result

    if engine is None:
        from graphcodebert.engine import get_engine
        engine = get_engine()
    result.mode = "classifier" if engine.is_fine_tuned else "structural"
    parameterized = [parameterize_tokens(f.code, f.language) for f in fragments]
    scored, semantic_candidates = {}, []
    for i, j in candidates:
        a, b = fragments[i], fragments[j]
        tok = SequenceMatcher(None, tokens[i], tokens[j], autojunk=False).ratio()
        param = SequenceMatcher(None, parameterized[i], parameterized[j], autojunk=False).ratio()
        ctype, score = None, max(tok, param)
        if a.language == b.language:
            if tokens[i] == tokens[j]:
                ctype, score = "Type-1", 1.0
            elif parameterized[i] == parameterized[j]:
                ctype, score = "Type-2", 1.0
            elif score >= max(threshold, 0.75):
                ctype = "Type-3"
        if ctype and score >= threshold:
            scored[(i, j)] = (ctype, score, tok)
        elif engine.is_fine_tuned:
            semantic_candidates.append((i, j))

    # Raw base-model or hashed-vector cosine scores are not clone probabilities.
    # Only a trained pair classifier can add semantic/cross-language matches.
    # Score all remaining pairs in bounded batches without a top-k cutoff.
    for offset in range(0, len(semantic_candidates), 32):
        batch = semantic_candidates[offset:offset + 32]
        probabilities = engine.predict_batch([
            (fragments[i].code, fragments[i].language,
             fragments[j].code, fragments[j].language) for i, j in batch
        ])
        if len(probabilities) != len(batch) or not np.all(np.isfinite(probabilities)):
            raise RuntimeError("The semantic classifier returned invalid scores")
        for (i, j), prob in zip(batch, probabilities):
            if prob >= max(threshold, settings.TYPE4_SEM_SIM):
                tok = SequenceMatcher(None, tokens[i], tokens[j], autojunk=False).ratio()
                scored[(i, j)] = ("Type-4", float(prob), tok)

    for (i, j), (ctype, score, tok) in scored.items():
        a, b = fragments[i], fragments[j]
        cross = a.language != b.language
        result.clone_pairs.append(DetectedClone(
            file_a=a.file, file_b=b.file,
            lines_a=[a.start_line, a.end_line], lines_b=[b.start_line, b.end_line],
            clone_lines_a=a.line_range, clone_lines_b=b.line_range,
            clone_type=ctype, similarity=round(score, 6), token_sim=round(tok, 6),
            cross_language=cross, description=_clone_description(ctype, cross),
            code_a=a.code, code_b=b.code,
        ))
    result.clone_pairs.sort(key=lambda p: (-p.similarity, p.file_a, p.file_b, p.lines_a, p.lines_b))
    result.stage2_pairs = len(result.clone_pairs)
    result.runtime_seconds = round(time.perf_counter() - started, 3)
    return result
