# Controlled single-file clone test

Upload **clone_test.py only** to CloneScope. Start a new analysis with the UI
threshold at **75%**, and leave the detector/model settings unchanged. This is a
diagnostic test of the deployed system, not a request to adjust settings until
the expected number appears.

There are **10 functions, 45 possible unordered whole-function pairs, and 4
labeled positive pairs**. Each positive gets its most specific type once:

| Type | First function / lines | Second function / lines | Why |
|---|---|---|---|
| Type-1 | clean_label, 1–7 | clean_label, 10–17 | Identical code tokens; extra comment only. |
| Type-2 | squared_distance, 20–26 | separation_squared, 29–35 | Consistent renaming; operations and constants unchanged. |
| Type-3 | make_receipt, 38–49 | make_receipt_with_fee, 52–64 | Copied calculation with one added fee statement. |
| Type-4 | triangular_by_loop, 67–75 | triangular_by_formula, 78–84 | Iteration versus a closed formula for the same integer calculation. |

Expected labeled counts: **Type-1: 1, Type-2: 1, Type-3: 1, Type-4: 1; total: 4**.
The remaining 41 pairs are labeled negative under this fixture's intended
whole-function comparison. Small shared fragments or a broader near-miss policy
can produce different counts; compare the actual pairs, not just the total.

The two negative controls are `find_maximum` (87–94) and `filter_even` (97–102).
For `[1, 2, 3, 4]`, they return `4` and `[2, 4]` respectively. They are unrelated
functions and should not be reported as semantically equivalent.

The Type-4 input contract is **integers**. Both functions return zero for
nonpositive integers, and `n * (n + 1) // 2` otherwise. Their outputs were checked
for every integer from -100 through 500. This does not test floating-point inputs.
Type-3 intentionally changes the output by adding a fee: near-miss structural
clones do not need identical behavior.

Both Type-1 definitions deliberately have the same name. Upload this file as
source; do not import it as a library, because Python would retain only the second
definition under that name. The source analyzer can inspect both definitions.

## Share these results

1. The analysis overview and counts for all four types.
2. Every detected pair's function names or line ranges and assigned type.
3. The displayed model/structural scores and the threshold used.
4. Any error or Type-4 unavailable/not-checked status.

Use Export JSON if available, or send screenshots of all detected pairs. A total
of four alone is not sufficient: a missed true pair and an extra false pair can
cancel out. We will compare against `expected_pairs.json` to identify missing
pairs, extra pairs, and wrong type assignments.

This small hand-authored file is a regression diagnostic, not a measurement of
general accuracy on Python, Java, or arbitrary projects. It does not retrain or
change your model.
