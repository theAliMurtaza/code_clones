"""A candidate head is not eligible for serving merely because weights exist."""
import hashlib
import json
import math
from pathlib import Path

FORMAT = 'graphcodebert-symmetric-head-v1'


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def load_head_artifact(path):
    import torch
    path = Path(path)
    metadata = json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
    if (metadata.get('format') != FORMAT or metadata.get('encoder') != 'microsoft/graphcodebert-base'
            or metadata.get('eligible_for_serving') is not True):
        raise ValueError('Checkpoint has not passed the held-out evaluation gate')
    threshold = metadata.get('threshold')
    if type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0 < threshold <= 1:
        raise ValueError('Invalid classifier threshold')
    pairs = metadata.get('validated_language_pairs')
    if not pairs or any(p not in ['java:java', 'python:python', 'java:python'] for p in pairs):
        raise ValueError('No supported evaluated language pairs')
    if file_hash(path) != metadata.get('weights_sha256'):
        raise ValueError('Checkpoint weights do not match evaluation metadata')
    state = torch.load(path, map_location='cpu', weights_only=True)
    return state, metadata
