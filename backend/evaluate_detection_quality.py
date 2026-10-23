"""Targeted real-model evaluation; never executes fixture source as Python.

Run from backend: .\.venv311\Scripts\python.exe evaluate_detection_quality.py
Produces examples/accuracy-evaluation/results.json. Not a broad accuracy benchmark.
"""
import json
from pathlib import Path
from difflib import SequenceMatcher
import numpy as np

from config import get_settings
from classifier import code_tokens, parameterize_tokens
from detector import UploadedFile, run_detection
from graphcodebert.engine import GraphCodeBERTEngine
from test_detection_quality import (TOTAL, SUM, FREQUENCY, FACTORIAL, RECURSIVE,
                                    MAXIMUM, FILTER_EVEN, FREQUENCY_GET, DEDUPLICATE)


CASES = [
    ('exact_with_comment', TOTAL, TOTAL.replace('total = 0', 'total = 0 # start'), 'Type-1'),
    ('renamed_total', TOTAL, TOTAL.replace('calculate_total', 'add_items').replace('prices', 'values').replace('price', 'item').replace('total', 'amount'), 'Type-2'),
    ('near_miss_extra_operation', 'def add(a, b):\n    return a + b', 'def adjusted(a, b):\n    return a + b + 1', 'Type-3'),
    ('factorial_recursion', FACTORIAL, RECURSIVE, 'Type-4'),
    ('sum_builtin', TOTAL, 'def total(xs):\n    return sum(xs)', 'Type-4'),
    ('abs_branch_vs_builtin', 'def magnitude(x):\n    if x < 0:\n        return -x\n    return x', 'def absolute(n):\n    return abs(n)', 'Type-4'),
    ('sum_while_vs_builtin', 'def total(xs):\n    i = 0\n    out = 0\n    while i < len(xs):\n        out += xs[i]\n        i += 1\n    return out', 'def total(xs):\n    return sum(xs)', 'Type-4'),
    ('frequency_vs_sum', FREQUENCY, SUM, None),
    ('sum_vs_factorial', TOTAL, FACTORIAL, None),
    ('reversal_vs_sorting', 'def reverse(xs):\n    return xs[::-1]', 'def ordered(xs):\n    return sorted(xs)', None),
    ('frequency_vs_factorial', FREQUENCY, FACTORIAL, None),
    ('sum_vs_greeting', SUM, 'def greet(name):\n    return "Hello " + name', None),
    ('factorial_vs_greeting', RECURSIVE, 'def greet(name):\n    return "Hello " + name', None),
    ('maximum_vs_even_filter', MAXIMUM, FILTER_EVEN, None),
    ('sum_vs_frequency_get', SUM, FREQUENCY_GET, None),
    ('deduplicate_vs_frequency', DEDUPLICATE, FREQUENCY, None),
    ('even_loop_vs_comprehension', FILTER_EVEN,
     'def even(xs):\n    return [x for x in xs if x % 2 == 0]', 'Type-4'),
    ('frequency_branches_vs_get', FREQUENCY, FREQUENCY_GET, 'Type-4'),
]


def main():
    get_settings().DETECTION_ENGINE = 'full'
    real = GraphCodeBERTEngine()
    if not real.supports_semantics or real.is_fine_tuned:
        raise RuntimeError('This comparison requires the actual base model')
    codes = list(dict.fromkeys(code for _, a, b, _ in CASES for code in (a, b)))
    vectors = real.embed_batch(codes, ['python'] * len(codes))
    cached = dict(zip(codes, vectors))

    class CachedEngine:
        supports_semantics = True
        is_fine_tuned = False
        def embed_batch(self, source, langs):
            return np.asarray([cached[code] for code in source])

    rows = []
    for name, a, b, expected in CASES:
        ta, tb = code_tokens(a), code_tokens(b)
        pa, pb = parameterize_tokens(a), parameterize_tokens(b)
        raw = SequenceMatcher(None, ta, tb, autojunk=False).ratio()
        normalized = SequenceMatcher(None, pa, pb, autojunk=False).ratio()
        cosine = float(np.dot(cached[a], cached[b]) / (np.linalg.norm(cached[a]) * np.linalg.norm(cached[b])))
        # Previous production rules, applied to the same real model embeddings.
        previous = ('Type-1' if ta == tb else 'Type-2' if pa == pb else
                    'Type-3' if max(raw, normalized) >= .75 else
                    'Type-4' if cosine >= get_settings().TYPE4_EMBEDDING_SIM else None)
        result = run_detection([UploadedFile('a.py', a), UploadedFile('b.py', b)], .5, CachedEngine())
        actual = result.clone_pairs[0].clone_type if result.clone_pairs else None
        rows.append({'case': name, 'expected': expected, 'previous': previous,
                     'current': actual, 'cosine': round(cosine, 6),
                     'behavioral_rejections': result.behavioral_rejections,
                     'behavioral_inconclusive': result.behavioral_inconclusive,
                     'behavioral_consistent': result.behavioral_consistent})
        print(json.dumps(rows[-1]), flush=True)
    report = {'scope': f'{len(CASES)} hand-authored regression examples; not a representative accuracy benchmark',
              'detector_revision': result.analysis_info['detector_revision'],
              'weights': 'microsoft/graphcodebert-base, no fine-tuned checkpoint',
              'cases': rows,
              'previous_exact_labels': sum(r['previous'] == r['expected'] for r in rows),
              'current_exact_labels': sum(r['current'] == r['expected'] for r in rows)}
    output = Path(__file__).resolve().parents[1] / 'examples/accuracy-evaluation/results.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'cases'}))


if __name__ == '__main__':
    main()
