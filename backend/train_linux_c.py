"""Train and evaluate a C:C GraphCodeBERT pair head from labelled Linux code.

This command does not download a Linux tree, does not execute any uploaded code,
and does not install a candidate model.  A checkpoint is eligible only when it
passes the same held-out precision/recall gate as the existing classifier.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from transformers import RobertaConfig

from config import get_settings
from graphcodebert.engine import GraphCodeBERTEngine, MODEL_NAME
from graphcodebert.model import RobertaClassificationHead
from graphcodebert.training_artifact import FORMAT, file_hash
from linux_training_data import read_labeled_pairs
from training_data import metrics, serving_gate
from train import fit, score


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def encode(functions: dict[str, str], output: Path) -> tuple[dict[str, np.ndarray], dict[str, str]]:
    """Extract frozen production-model features using the C tree-sitter path."""
    settings = get_settings()
    settings.DETECTION_ENGINE = "full"
    settings.BATCH_SIZE = 1
    engine = GraphCodeBERTEngine(device="cpu", saved_model_path="")
    if not engine.supports_semantics:
        raise RuntimeError("GraphCodeBERT could not load for C training")

    cache = output / "features"
    cache.mkdir()
    vectors, excluded = {}, {}
    for number, (identifier, code) in enumerate(functions.items(), 1):
        cached_npy = None
        for run_dir in output.parent.glob("*/features"):
            cand = run_dir / f"{identifier}.npy"
            if cand.is_file():
                cached_npy = cand
                break
        if cached_npy is not None:
            vector = np.load(cached_npy)
            vectors[identifier] = vector
            np.save(cache / f"{identifier}.npy", vector)
            if number % 25 == 0:
                print(f"Encoded {number}/{len(functions)} C functions; usable={len(vectors)} (cached)", flush=True)
            continue

        try:
            vector = np.asarray(engine.embed_batch([code], ["c"]), dtype=np.float32)
            if vector.shape != (1, 768) or not np.all(np.isfinite(vector)) or np.linalg.norm(vector) <= 1e-9:
                raise ValueError("invalid encoder vector")
        except (RuntimeError, ValueError) as exc:
            excluded[identifier] = str(exc)
            continue
        vectors[identifier] = vector[0]
        np.save(cache / f"{identifier}.npy", vector[0])
        if number % 25 == 0:
            print(f"Encoded {number}/{len(functions)} C functions; usable={len(vectors)}", flush=True)
    return vectors, excluded


def eligible_pairs(pairs, vectors):
    result = {}
    for split, rows in pairs.items():
        result[split] = [(a, b, label) for a, b, label in rows if a in vectors and b in vectors]
        labels = {label for _, _, label in result[split]}
        if labels != {0, 1}:
            raise ValueError(f"{split}: encoder exclusions left fewer than both binary labels")
    return result


def train(args) -> None:
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    output = Path(args.output_dir).resolve()
    if output.exists():
        raise ValueError("Use a new output directory; existing experiments are preserved")
    if output == Path(__file__).resolve().parent / "saved_models":
        raise ValueError("Train in training_runs, not the live saved_models directory")
    output.mkdir(parents=True)
    started = time.time()

    functions, raw_pairs, audit = read_labeled_pairs(args.dataset_jsonl)
    write_json(output / "audit.json", {
        **audit,
        "scope": "C:C labelled Linux-source pairs only; no claim about other languages or universal equivalence",
        "seed": args.seed,
    })
    print("Dataset audited. Extracting frozen GraphCodeBERT C features.", flush=True)
    vectors, excluded = encode(functions, output)
    write_json(output / "encoding_exclusions.json", excluded)
    pairs = eligible_pairs(raw_pairs, vectors)
    write_json(output / "pairs.json", pairs)
    counts = {split: dict(Counter(str(row[2]) for row in rows)) for split, rows in pairs.items()}

    head = RobertaClassificationHead(RobertaConfig(hidden_size=768, hidden_dropout_prob=.1))
    fit(head, pairs, vectors, args, output)
    selection = json.loads((output / "selection.json").read_text(encoding="utf-8"))
    head.load_state_dict(torch.load(output / "model.bin", map_location="cpu", weights_only=True), strict=True)
    threshold = selection["threshold"]
    test_scores = score(head, pairs["test"], vectors, args.batch_size)
    test_metrics = metrics([label for _, _, label in pairs["test"]], test_scores,
                           threshold if threshold is not None else 1.000001)
    reasons = serving_gate(selection["validation"], test_metrics, args.target_precision, args.min_recall)
    if threshold is None:
        reasons.append("No validation operating point met precision/recall targets")
    report = {
        "format": FORMAT,
        "encoder": MODEL_NAME,
        "training_mode": "frozen_encoder_trained_pair_head_c_without_published_c_dfg",
        "threshold": threshold,
        "selected_epoch": selection["epoch"],
        "validation": selection["validation"],
        "test": test_metrics,
        "target_precision": args.target_precision,
        "min_recall": args.min_recall,
        "eligible_for_serving": not reasons,
        "gate_failures": reasons,
        "validated_language_pairs": ["c:c"] if not reasons else [],
        "weights_sha256": file_hash(output / "model.bin"),
        "pair_counts": counts,
        "encoded_functions": len(vectors),
        "excluded_functions": len(excluded),
        "elapsed_seconds": round(time.time() - started, 1),
        "limitations": "Evaluation applies only to the labelled Linux C source distribution. "
                       "It is a clone classifier, not a proof of behavior equivalence.",
    }
    write_json(output / "model.json", report)
    write_json(output / "test_predictions.json", [
        {"a": a, "b": b, "label": label, "score": value}
        for (a, b, label), value in zip(pairs["test"], test_scores)
    ])
    print(json.dumps(report, indent=2), flush=True)
    print("Candidate saved separately; the live semantic service has not changed.", flush=True)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset_jsonl", required=True)
    p.add_argument("--output_dir", required=True)
    p.add_argument("--epochs", type=int, default=20)
    p.add_argument("--batch_size", type=int, default=32)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--target_precision", type=float, default=.95)
    p.add_argument("--min_recall", type=float, default=.50)
    return p


if __name__ == "__main__":
    args = parser().parse_args()
    if (min(args.epochs, args.batch_size, args.threads) < 1 or args.lr <= 0
            or not 0 < args.target_precision <= 1 or not 0 < args.min_recall <= 1):
        raise SystemExit("Invalid training parameters")
    train(args)
