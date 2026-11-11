# Linux C training and serving

The web API automatically accepts `.c` and `.h` files.  It detects Type-1,
Type-2 and Type-3 copied code without a new screen, mode, or model dependency.
This is immediately useful for Linux-kernel-style source files.

Type-4 is deliberately disabled for C until a C:C classifier has passed a
held-out evaluation. GraphCodeBERT was not pretrained on C, and no score from
an unvalidated C model should be presented as an accurate semantic clone.

## Dataset

Provide a UTF-8 JSONL file of function-level labelled pairs. Every record needs
`split` (`train`, `valid`, or `test`), `label` (`1` clone, `0` non-clone),
`code_a`, and `code_b`. Add source/version fields for auditability.

```json
{"split":"train","label":1,"code_a":"int sum(int *a, int n) { ... }","code_b":"int total(int *b, int n) { ... }","source_a":"linux/v6.12/a.c:10","source_b":"linux/v6.12/b.c:20"}
```

Split by function or source file before creating pairs: the same normalised
function is rejected if it appears in more than one split. Use a Linux version
and licence that you are entitled to process, retain provenance, and keep the
test split untouched while making choices.

## Train

From `backend` with the full model dependencies available:

```powershell
.\.venv311\Scripts\python.exe .\train_linux_c.py `
  --dataset_jsonl D:\datasets\linux-c-clones.jsonl `
  --output_dir .\training_runs\linux-c-v1
```

The command writes the checkpoint, hashes, metrics, threshold-selection record,
and test predictions into the new output directory. It does **not** change a
running service. A model must meet the configured precision/recall gate on both
validation and the untouched test split to set `eligible_for_serving: true`.

## Deploy an evaluated candidate

Only if `training_runs/linux-c-v1/model.json` says `eligible_for_serving: true`:

1. Copy its `model.bin` and `model.json` to the semantic model host's
   `saved_models/model.bin` and `saved_models/model.json`.
2. Update/redeploy the Hugging Face Space (or another full-model host) with the
   revised backend files and `tree-sitter-c` requirement.
3. Confirm authenticated `/info` reports `mode: "classifier"` and includes
   `"c:c"` in `validated_language_pairs`.
4. Set `ENABLE_LINUX_C_CLASSIFIER=true` on the API service and redeploy it.

Until all four steps are complete, C/header files still receive reliable
structural copied-code detection, but they do not receive Type-4 output.
