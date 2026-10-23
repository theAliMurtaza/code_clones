# Targeted detection regression evaluation

`results.json` records actual local GraphCodeBERT inference on 18 hand-authored
development cases. Source definitions and the reproducible evaluator are in
`backend/evaluate_detection_quality.py` and `backend/test_detection_quality.py`.
Screenshot cases are reconstructed from the displayed functions (including numeric
literals hidden by the earlier viewer). They are not copies of the original uploads.

The report compares the original token/cosine rules with the current detector,
using the same actual embeddings for both. The revised checks reject frequency/sum,
sum/factorial, reversal/sorting, maximum/even-filter, sum/frequency-with-get and
deduplication/frequency pairs. Positive fixtures include Types 1–3, recursive and
iterative factorial, loop and builtin sum, even filtering by loop and comprehension,
and frequency counting by branches and dictionary get. See the report for counts.

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
code. The v3 detector withholds unsupported Python and Java semantic candidates,
even at a perfect model score. Every accepted Type-4 candidate needs at least five
agreeing samples and three distinct outputs, as well as the model threshold.
This deliberately sacrifices recall to reduce false positives. Even supported
functions can differ outside the tested inputs.
Input-domain contracts are not inferred. Real precision/recall requires a separate,
representative labelled dataset and a fixed operating threshold.

The v2 checker also preserves list aliases during augmented assignment, skips
out-of-domain scalar samples when checking container mutation, and treats generator
expressions and shadowed builtin bindings as inconclusive. It never converts a
generator to a list and claims the resulting behavior is equivalent. Each accepted
Type-4 pair in v3 states how many bounded samples agreed. Unverified pairs are
counted as withheld in analysis metadata and excluded from clone results.

The v3 interpreter adds explicit bounded `list.append` and `dict.get` operations.
No general attribute access or arbitrary method execution is allowed. Regression
tests force a perfect embedding score for each screenshot pair and check rejection
in single-file, multiple-file and nested-folder layouts. They also check that
supported semantic matches survive, and that mutations and resource limits remain
observable. These tests validate acceptance rules, not learned model accuracy.

Reproduce from `backend` after setting `HF_HUB_OFFLINE=1`,
`TRANSFORMERS_OFFLINE=1`, `OMP_NUM_THREADS=2` and `MKL_NUM_THREADS=2`:

```powershell
.\.venv311\Scripts\python.exe evaluate_detection_quality.py
```
