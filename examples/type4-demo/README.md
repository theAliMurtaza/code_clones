# Local Type-4 smoke test

Select this folder in the app and run analysis with threshold 0.50.
With the cached GraphCodeBERT base model and semantic cutoff 0.85, observed results:

- recursive.py / iterative.py: Type-4 candidate (recursive vs iterative factorial).
- sort.py / Sort.java: Type-4 candidate (Python vs Java quicksort).
- renamed.py / Sort.java: Type-4 candidate.
- sort.py / renamed.py: Type-2 (renamed implementation).
- greet.py: no matches.

Expand results to inspect code and line numbers, then choose View full code.
These examples are a smoke test, not a general accuracy benchmark.
