"""
embedder.py
Generates 768-dimensional vector embeddings for code fragments using
microsoft/codebert-base.

Features:
  - Lazy model loading (loaded once on first call, reused thereafter)
  - Redis embedding cache keyed by SHA-256(code) — NFR-03-03
  - Intelligent batching for GPU throughput — NFR-08-01
  - CPU fallback when no GPU available — NFR-08-02
  - Graceful mock fallback for dev environments without PyTorch
"""

from __future__ import annotations
import hashlib
import logging
import struct
from typing import Optional

import numpy as np
import redis

from config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()

EMBEDDING_DIM = 768   # CodeBERT CLS token dimension


# ── Redis client (lazy) ───────────────────────────────────────────────
_redis_client: Optional[redis.Redis] = None

def _get_redis() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        _redis_client = redis.from_url(settings.REDIS_URL)
        _redis_client.ping()
        return _redis_client
    except Exception as exc:
        logger.warning(f"Redis unavailable ({exc}); embedding cache disabled")
        return None


def _cache_key(code: str) -> str:
    return "emb:" + hashlib.sha256(code.encode()).hexdigest()


def _cache_get(code: str) -> Optional[np.ndarray]:
    r = _get_redis()
    if r is None:
        return None
    try:
        raw = r.get(_cache_key(code))
        if raw:
            arr = np.frombuffer(raw, dtype=np.float32)
            return arr if arr.shape == (EMBEDDING_DIM,) else None
    except Exception:
        pass
    return None


def _cache_set(code: str, vec: np.ndarray):
    r = _get_redis()
    if r is None:
        return
    try:
        r.set(_cache_key(code), vec.astype(np.float32).tobytes(),
              ex=settings.EMBEDDING_CACHE_TTL)
    except Exception:
        pass


# ── Model loader ──────────────────────────────────────────────────────
_tokenizer = None
_model     = None
_device    = None

def _load_model():
    global _tokenizer, _model, _device
    if _model is not None:
        return

    try:
        import torch
        from transformers import AutoTokenizer, AutoModel

        logger.info(f"Loading CodeBERT model: {settings.CODEBERT_MODEL}")
        _tokenizer = AutoTokenizer.from_pretrained(
            settings.CODEBERT_MODEL,
            cache_dir=settings.MODEL_CACHE_DIR,
        )
        _model = AutoModel.from_pretrained(
            settings.CODEBERT_MODEL,
            cache_dir=settings.MODEL_CACHE_DIR,
        )
        _model.eval()

        _device = "cuda" if (settings.USE_GPU and torch.cuda.is_available()) else "cpu"
        _model.to(_device)
        logger.info(f"CodeBERT loaded on {_device.upper()}")

    except ImportError:
        logger.warning("PyTorch/transformers not installed — using random mock embeddings")


def _embed_batch_real(codes: list[str]) -> np.ndarray:
    """Embed a list of code strings using CodeBERT. Returns (N, 768) array."""
    import torch
    enc = _tokenizer(
        codes,
        return_tensors="pt",
        max_length=settings.MAX_TOKEN_LENGTH,
        truncation=True,
        padding=True,
    )
    enc = {k: v.to(_device) for k, v in enc.items()}
    with torch.no_grad():
        out = _model(**enc)
    # Use the [CLS] token hidden state as the fragment embedding
    cls_vecs = out.last_hidden_state[:, 0, :].cpu().numpy()  # (N, 768)
    return cls_vecs.astype(np.float32)


def _embed_batch_mock(codes: list[str]) -> np.ndarray:
    """Deterministic random embeddings for dev/test without PyTorch."""
    vecs = []
    for code in codes:
        seed = int(hashlib.md5(code.encode()).hexdigest()[:8], 16)
        rng  = np.random.default_rng(seed)
        vec  = rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
        vec /= np.linalg.norm(vec) + 1e-9
        vecs.append(vec)
    return np.stack(vecs)


# ── Public API ────────────────────────────────────────────────────────
def embed_fragments(codes: list[str]) -> np.ndarray:
    """
    Generate embeddings for a list of code strings.

    Process:
      1. Check Redis cache for each code string.
      2. Batch-embed all cache misses through CodeBERT.
      3. Store new embeddings in Redis.
      4. Return (N, 768) numpy array in original order.
    """
    _load_model()

    results  = [None] * len(codes)
    miss_idx = []   # indices of cache misses

    # ── Cache lookup ──────────────────────────────────────────────────
    for i, code in enumerate(codes):
        hit = _cache_get(code)
        if hit is not None:
            results[i] = hit
        else:
            miss_idx.append(i)

    logger.debug(f"Embedding: {len(codes)} total, "
                 f"{len(codes)-len(miss_idx)} cache hits, "
                 f"{len(miss_idx)} misses")

    if not miss_idx:
        return np.stack(results)

    # ── Batch inference ───────────────────────────────────────────────
    miss_codes = [codes[i] for i in miss_idx]
    batch_size = settings.BATCH_SIZE
    all_vecs   = []

    for start in range(0, len(miss_codes), batch_size):
        batch = miss_codes[start : start + batch_size]
        try:
            vecs = _embed_batch_real(batch) if _model else _embed_batch_mock(batch)
        except Exception as exc:
            logger.error(f"Embedding batch failed: {exc}; using mock")
            vecs = _embed_batch_mock(batch)
        all_vecs.append(vecs)

    all_vecs = np.concatenate(all_vecs, axis=0)   # (N_miss, 768)

    # ── Store in cache & fill results ─────────────────────────────────
    for j, idx in enumerate(miss_idx):
        vec = all_vecs[j]
        _cache_set(codes[idx], vec)
        results[idx] = vec

    return np.stack(results)   # (N, 768)


def embed_single(code: str) -> np.ndarray:
    """Convenience wrapper for a single code string."""
    return embed_fragments([code])[0]
