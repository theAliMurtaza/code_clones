"""Strict reader for labelled Linux C clone-pair datasets.

The accepted JSONL schema is intentionally small and auditable:

  {"split":"train", "label":1, "code_a":"...", "code_b":"...",
   "source_a":"linux/foo.c:10", "source_b":"linux/bar.c:20"}

``label`` is 1 for a clone and 0 for a non-clone.  Splits must be function
disjoint; a source function occurring in more than one split is rejected.
The reader does not execute source code and does not manufacture semantic labels
from superficial token similarity.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from classifier import code_tokens


SPLITS = ("train", "valid", "test")


def _fingerprint(code: str) -> str:
    tokens = code_tokens(code, "c")
    if len(tokens) < 3:
        raise ValueError("Each training snippet needs at least three C tokens")
    return hashlib.sha256(json.dumps(tokens, separators=(",", ":")).encode()).hexdigest()


def read_labeled_pairs(path: str | Path):
    """Return ``(functions, pairs, audit)`` after validating a JSONL dataset."""
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"Dataset not found: {path}")

    functions, pairs = {}, {split: [] for split in SPLITS}
    function_owner, pair_labels = {}, {}
    source_count = Counter()

    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
            split, label = row["split"], row["label"]
            code_a, code_b = row["code_a"], row["code_b"]
        except (TypeError, KeyError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid JSONL record at line {line_number}") from exc
        if split not in SPLITS or type(label) is not int or label not in (0, 1):
            raise ValueError(f"Invalid split or binary label at line {line_number}")
        if not all(isinstance(code, str) and code.strip() for code in (code_a, code_b)):
            raise ValueError(f"Both code snippets must be non-empty strings at line {line_number}")

        a, b = _fingerprint(code_a), _fingerprint(code_b)
        if a == b and label == 0:
            raise ValueError(f"Identical snippets cannot be labelled non-clones at line {line_number}")
        for identifier, code in ((a, code_a), (b, code_b)):
            owner = function_owner.setdefault(identifier, split)
            if owner != split:
                raise ValueError(
                    f"Function leakage between {owner} and {split} at line {line_number}; "
                    "split by function or source file before training"
                )
            functions[identifier] = code
            source_count[split] += 1

        key = (split, *sorted((a, b)))
        previous = pair_labels.get(key)
        if previous is not None and previous != label:
            raise ValueError(f"Contradictory pair labels at line {line_number}")
        if previous is None:
            pair_labels[key] = label
            pairs[split].append((a, b, label))

    audit = {"dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "splits": {}}
    for split in SPLITS:
        counts = Counter(label for _, _, label in pairs[split])
        if set(counts) != {0, 1}:
            raise ValueError(f"{split} must contain at least one clone and one non-clone pair")
        audit["splits"][split] = {
            "pairs": len(pairs[split]),
            "labels": {str(label): count for label, count in sorted(counts.items())},
            "function_references": source_count[split],
        }
    return functions, pairs, audit

