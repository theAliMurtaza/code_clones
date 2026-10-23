"""Audited indexed BigCloneBench input and validation-only threshold selection.

The archive has binary Java clone labels, not four-way types or Python labels.
No source is executed. Function-disjoint splits do not prove project independence.
"""
import hashlib
import json
import random
from collections import Counter
from zipfile import ZipFile
import numpy as np


def read_archive(path):
    functions, splits, audit = {}, {}, {}
    with ZipFile(path) as archive:
        for line in archive.open('dataset/data.jsonl'):
            row = json.loads(line)
            identifier, code = str(row['idx']), row['func']
            if identifier in functions or not isinstance(code, str) or not code.strip():
                raise ValueError('Duplicate function id or empty code in archive')
            functions[identifier] = code
        identities = {}
        for split in ('train', 'valid', 'test'):
            rows, ids, labels = [], set(), Counter()
            for line in archive.open(f'dataset/{split}.txt'):
                a, b, label = line.decode('utf-8').split()
                if a not in functions or b not in functions or label not in ('0', '1'):
                    raise ValueError(f'Invalid pair in {split}')
                rows.append((a, b, int(label)))
                ids.update((a, b))
                labels[label] += 1
            if set(labels) != {'0', '1'}:
                raise ValueError(f'{split} must contain both labels')
            splits[split], identities[split] = rows, ids
            audit[split] = {'pairs': len(rows), 'functions': len(ids), 'labels': dict(labels)}
        for a, b in [('train', 'valid'), ('train', 'test'), ('valid', 'test')]:
            if identities[a] & identities[b]:
                raise ValueError(f'Function-id leakage between {a} and {b}')
    return functions, splits, audit


def select_functions(functions, splits, limits, seed):
    """Sample functions without consulting labels; preserve induced prevalence."""
    selected = {}
    for index, (split, pairs) in enumerate(splits.items()):
        ids = sorted({v for a, b, _ in pairs for v in (a, b)})
        random.Random(seed + index).shuffle(ids)
        selected[split] = ids[:limits[split]] if limits[split] else ids
    from classifier import code_tokens
    seen, excluded = {}, {}
    for split in ('train', 'valid', 'test'):
        kept = []
        for identifier in selected[split]:
            digest = hashlib.sha256(json.dumps(code_tokens(functions[identifier], 'java')).encode()).hexdigest()
            owner = seen.get(digest)
            if owner is not None and owner != split:
                excluded[identifier] = 'duplicate token sequence across splits'
                continue
            seen[digest] = split
            kept.append(identifier)
        selected[split] = kept
    return selected, excluded


def induced_pairs(splits, selected, eligible):
    result, seen_labels = {}, {}
    for split, pairs in splits.items():
        ids = set(selected[split]) & set(eligible)
        rows = {}
        for a, b, label in pairs:
            if a not in ids or b not in ids or a == b:
                continue
            key = tuple(sorted((a, b)))
            if key in seen_labels and seen_labels[key] != label:
                raise ValueError('Contradictory labels for the same unordered pair')
            seen_labels[key] = label
            rows[key] = (a, b, label)
        result[split] = list(rows.values())
        if {row[2] for row in result[split]} != {0, 1}:
            raise ValueError(f'{split}: insufficient eligible pairs; increase function sample size')
    return result


def metrics(labels, scores, threshold):
    labels, scores = np.asarray(labels), np.asarray(scores)
    if (len(labels) == 0 or labels.shape != scores.shape or not np.all(np.isfinite(scores))
            or np.any((scores < 0) | (scores > 1)) or not set(labels.tolist()) <= {0, 1}):
        raise ValueError('Invalid evaluation labels/scores')
    pred = scores >= threshold
    tp = int(np.sum(pred & (labels == 1)))
    fp = int(np.sum(pred & (labels == 0)))
    fn = int(np.sum(~pred & (labels == 1)))
    tn = int(np.sum(~pred & (labels == 0)))
    precision = tp / (tp + fp) if tp + fp else 0.
    recall = tp / (tp + fn) if tp + fn else 0.
    n, z = tp + fp, 1.96
    lower = ((precision + z*z/(2*n) - z*np.sqrt(precision*(1-precision)/n + z*z/(4*n*n)))
             / (1 + z*z/n)) if n else 0.
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, precision=precision, recall=recall,
                f1=2*precision*recall/(precision+recall) if precision+recall else 0.,
                precision_wilson_lower_95=float(lower), examples=len(labels))


def select_threshold(labels, scores, target_precision, min_recall):
    # Test labels must never enter this function.
    metrics(labels, scores, .5)  # Validate shape/range before sorting.
    labels, scores = np.asarray(labels), np.asarray(scores)
    order = np.argsort(-scores, kind='stable')
    ordered, positives = scores[order], labels[order]
    ends = np.r_[np.flatnonzero(ordered[:-1] != ordered[1:]), len(ordered)-1]
    tp = np.cumsum(positives)[ends]
    precision = tp / (ends + 1)
    recall = tp / max(1, np.sum(positives))
    candidates = [(float(recall[i]), float(precision[i]), float(ordered[end]))
                  for i, end in enumerate(ends) if ordered[end] > 0
                  and precision[i] >= target_precision and recall[i] >= min_recall]
    if not candidates:
        return None, metrics(labels, scores, 1.000001)
    _, _, threshold = max(candidates)
    return threshold, metrics(labels, scores, threshold)


def serving_gate(validation, test, target_precision, min_recall):
    reasons = []
    for name, result in [('validation', validation), ('test', test)]:
        if result['tp'] + result['fn'] < 100 or result['tn'] + result['fp'] < 100:
            reasons.append(f'{name}: fewer than 100 examples of each class')
        if result['precision_wilson_lower_95'] < target_precision:
            reasons.append(f'{name}: precision confidence bound below target')
        if result['recall'] < min_recall:
            reasons.append(f'{name}: recall below target')
    return reasons
