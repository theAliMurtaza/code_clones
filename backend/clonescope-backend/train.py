"""
train.py
Fine-tune GraphCodeBERT on BigCloneBench for highest Type-4 accuracy.

This is optional — the base model (microsoft/graphcodebert-base) works
without fine-tuning.  Fine-tuned weights push F1 from ~0.85 to ~0.94.

Usage:
    # 1. Download BigCloneBench dataset
    #    https://github.com/clonebench/BigCloneBench
    #    Place train.jsonl / valid.jsonl / test.jsonl in data/

    # 2. Run fine-tuning (GPU strongly recommended)
    python train.py \
        --data_dir   data/ \
        --output_dir saved_models/ \
        --epochs     2 \
        --batch_size 16

    # 3. The fine-tuned weights are saved to saved_models/model.bin
    #    The engine auto-loads them on next startup.

BigCloneBench JSONL format (one line per clone pair):
    {"label": 1, "func1": "public void foo() {...}", "func2": "void bar(){...}"}
"""

from __future__ import annotations
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader, RandomSampler, SequentialSampler
from transformers import (
    RobertaTokenizer, RobertaConfig,
    RobertaForSequenceClassification,
    AdamW, get_linear_schedule_with_warmup,
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
from graphcodebert.model   import Model
from graphcodebert.engine  import GraphCodeBERTEngine, _DummyArgs, MAX_SEQ_LEN

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

MODEL_NAME = "microsoft/graphcodebert-base"


# ── Dataset ────────────────────────────────────────────────────────────
class CloneDataset(Dataset):
    def __init__(self, jsonl_path: str, engine: GraphCodeBERTEngine):
        self.examples = []
        self.engine   = engine
        logger.info(f"Loading {jsonl_path}...")
        with open(jsonl_path) as f:
            for i, line in enumerate(f):
                item = json.loads(line.strip())
                self.examples.append({
                    "label": int(item["label"]),
                    "func1": item.get("func1", item.get("code1", "")),
                    "func2": item.get("func2", item.get("code2", "")),
                    "lang1": item.get("lang1", "java"),
                    "lang2": item.get("lang2", "java"),
                })
                if (i + 1) % 10000 == 0:
                    logger.info(f"  Loaded {i+1} examples")
        logger.info(f"Dataset size: {len(self.examples)}")

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        ex  = self.examples[idx]
        enc1 = self.engine._encode_fragment(ex["func1"], ex.get("lang1", "java"))
        enc2 = self.engine._encode_fragment(ex["func2"], ex.get("lang2", "java"))
        mask1 = self.engine._build_attn_mask(enc1)
        mask2 = self.engine._build_attn_mask(enc2)
        return (
            torch.tensor(enc1["input_ids"],    dtype=torch.long),
            torch.tensor(enc1["position_idx"], dtype=torch.long),
            torch.tensor(mask1,                dtype=torch.bool),
            torch.tensor(enc2["input_ids"],    dtype=torch.long),
            torch.tensor(enc2["position_idx"], dtype=torch.long),
            torch.tensor(mask2,                dtype=torch.bool),
            torch.tensor(ex["label"],          dtype=torch.long),
        )


# ── Evaluation ────────────────────────────────────────────────────────
def evaluate(model, loader, device):
    model.eval()
    preds, labels = [], []
    with torch.no_grad():
        for batch in loader:
            ids1, pos1, msk1, ids2, pos2, msk2, lbl = [b.to(device) for b in batch]
            probs = model(ids1, pos1, msk1, ids2, pos2, msk2)
            preds.extend(probs[:, 1].cpu().numpy().tolist())
            labels.extend(lbl.cpu().numpy().tolist())

    preds_bin = [1 if p >= 0.5 else 0 for p in preds]
    tp = sum(p == 1 and l == 1 for p, l in zip(preds_bin, labels))
    fp = sum(p == 1 and l == 0 for p, l in zip(preds_bin, labels))
    fn = sum(p == 0 and l == 1 for p, l in zip(preds_bin, labels))

    precision = tp / (tp + fp + 1e-9)
    recall    = tp / (tp + fn + 1e-9)
    f1        = 2 * precision * recall / (precision + recall + 1e-9)
    return {"precision": precision, "recall": recall, "f1": f1}


# ── Training loop ─────────────────────────────────────────────────────
def train(args):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Device: {device.upper()}")

    # Load engine (for encoding, parsers, etc.)
    engine = GraphCodeBERTEngine(device=device)

    # Build model
    config    = RobertaConfig.from_pretrained(MODEL_NAME)
    tokenizer = RobertaTokenizer.from_pretrained(MODEL_NAME)
    encoder   = RobertaForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=2
    )
    model = Model(encoder, config, tokenizer, args=_DummyArgs())
    model.to(device)

    # Load existing weights if resuming
    ckpt = os.path.join(args.output_dir, "model.bin")
    if os.path.isfile(ckpt):
        model.load_state_dict(torch.load(ckpt, map_location=device), strict=False)
        logger.info(f"Resumed from {ckpt}")

    # Datasets
    train_dataset = CloneDataset(os.path.join(args.data_dir, "train.jsonl"), engine)
    valid_dataset = CloneDataset(os.path.join(args.data_dir, "valid.jsonl"), engine)

    train_loader = DataLoader(
        train_dataset,
        sampler    = RandomSampler(train_dataset),
        batch_size = args.batch_size,
        num_workers= 2,
    )
    valid_loader = DataLoader(
        valid_dataset,
        sampler    = SequentialSampler(valid_dataset),
        batch_size = args.batch_size * 2,
        num_workers= 2,
    )

    # Optimizer & scheduler
    no_decay = ["bias", "LayerNorm.weight"]
    params   = [
        {"params": [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)], "weight_decay": 0.01},
        {"params": [p for n, p in model.named_parameters() if     any(nd in n for nd in no_decay)], "weight_decay": 0.0},
    ]
    optimizer = AdamW(params, lr=args.lr)
    total_steps   = len(train_loader) * args.epochs
    warmup_steps  = int(0.1 * total_steps)
    scheduler     = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    # Train
    best_f1 = 0.0
    os.makedirs(args.output_dir, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        t0         = time.time()

        for step, batch in enumerate(train_loader):
            ids1, pos1, msk1, ids2, pos2, msk2, lbl = [b.to(device) for b in batch]
            loss, _ = model(ids1, pos1, msk1, ids2, pos2, msk2, lbl)

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            total_loss += loss.item()

            if (step + 1) % 100 == 0:
                logger.info(
                    f"Epoch {epoch} step {step+1}/{len(train_loader)} "
                    f"loss={total_loss/(step+1):.4f} "
                    f"elapsed={time.time()-t0:.0f}s"
                )

        # Validate
        metrics = evaluate(model, valid_loader, device)
        logger.info(
            f"Epoch {epoch} — P={metrics['precision']:.4f} "
            f"R={metrics['recall']:.4f} F1={metrics['f1']:.4f}"
        )

        if metrics["f1"] > best_f1:
            best_f1 = metrics["f1"]
            torch.save(model.state_dict(), ckpt)
            logger.info(f"  Saved new best model (F1={best_f1:.4f}) → {ckpt}")

    logger.info(f"Training done. Best F1: {best_f1:.4f}")
    logger.info(f"Model saved to {ckpt} — will be auto-loaded by GraphCodeBERTEngine.")


# ── Entry point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune GraphCodeBERT on BigCloneBench")
    parser.add_argument("--data_dir",   default="data/",          help="Directory with train/valid/test.jsonl")
    parser.add_argument("--output_dir", default="saved_models/",  help="Where to save model.bin")
    parser.add_argument("--epochs",     type=int,   default=2,    help="Number of training epochs")
    parser.add_argument("--batch_size", type=int,   default=16,   help="Batch size per GPU/CPU")
    parser.add_argument("--lr",         type=float, default=2e-5, help="Learning rate")
    args = parser.parse_args()
    train(args)
