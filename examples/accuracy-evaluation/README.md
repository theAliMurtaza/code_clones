# Targeted detection regression evaluation

`results.json` records actual local GraphCodeBERT inference on 13 hand-authored
development cases. Source definitions and the reproducible evaluator are in
`backend/evaluate_detection_quality.py` and `backend/test_detection_quality.py`.
The two screenshot cases were reconstructed with the numeric literals that the
old viewer hid. They are not copies of the user's original uploaded files.

The previous rules matched 8 of 13 intended labels; the revised rules matched 13
of 13. The same actual embeddings are used for both rule sets. The revision removes
the frequency/sum, sum/factorial and reversal/sorting false positives and recovers
two missed semantic matches using bounded sample agreement. Types 1–3 and the
other semantic positives in this set are retained.

**This is a development regression result, not measured general accuracy.** These
examples informed the changes; they are not an independent held-out benchmark.
The thresholds and syntax weights are heuristics. The stricter Type-3 policy may
exclude legitimate near misses under broader clone definitions. Some Type-3 and
Type-2 clones legitimately have different behavior. No universal claim follows
from these labels or counts.

The model is still `microsoft/graphcodebert-base`, with no fine-tuned classification
checkpoint. Its cosine scores are not probabilities. Microsoft's
[clone-detection implementation](https://github.com/microsoft/CodeBERT/tree/master/GraphCodeBERT/clonedetection)
uses task-specific training for classification. This update improves preprocessing
and detection rules, not model weights.

Behavior checks use a small AST interpreter, never normal execution of uploaded
code. Unsupported Python and Java remain unverified candidates at the standard
score floor. Even supported functions can differ outside the tested inputs.
Input-domain contracts are not inferred. Real precision/recall requires a separate,
representative labelled dataset and a fixed operating threshold.

The v2 checker also preserves list aliases during augmented assignment, skips
out-of-domain scalar samples when checking container mutation, and treats generator
expressions and shadowed builtin bindings as inconclusive. It never converts a
generator to a list and claims the resulting behavior is equivalent. Each accepted
Type-4 pair now states whether bounded samples agreed or behavior was unverified.

Reproduce from `backend` after setting `HF_HUB_OFFLINE=1`,
`TRANSFORMERS_OFFLINE=1`, `OMP_NUM_THREADS=2` and `MKL_NUM_THREADS=2`:

```powershell
.\.venv311\Scripts\python.exe evaluate_detection_quality.py
```
