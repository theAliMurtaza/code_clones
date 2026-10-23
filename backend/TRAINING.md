# Train and evaluate the clone classifier

The base GraphCodeBERT encoder is a representation model. Its cosine similarity
is not a calibrated clone probability. This training path learns a symmetric
pairwise classification head on its real CLS vectors. The encoder remains frozen;
this is **not full transformer fine-tuning**. It is a bounded CPU training option
for this laptop, whose installed PyTorch has no CUDA support.

Microsoft's [clone detection task](https://github.com/microsoft/CodeBERT/tree/master/GraphCodeBERT/clonedetection)
uses task-specific training. Published benchmark scores do not describe this
application, Python behavior, or a guarantee of Type-4 equivalence.

## Dataset scope

The supplied `clonedetection/dataset.zip` contains `dataset/data.jsonl` (function
IDs and Java source) and `train.txt`, `valid.txt`, `test.txt` (ID pairs and binary
labels). It contains 9,126 functions, 901,028 training pairs, 415,416 validation
pairs and 415,416 test pairs. The official splits have disjoint function IDs.

It is a **Java binary clone benchmark**, not a Python dataset, a four-type labeled
dataset, or a proof of behavioral equivalence for every positive pair. Training
on it does not validate the Python examples from the screenshots. Types 1–3
continue to use structural rules; model labels do not replace that taxonomy.

The pilot samples functions before looking at their pair labels, retains pairs
between those functions, removes reversed duplicates and checks conflicting
labels. Exact token-sequence copies crossing sampled splits are excluded.
Function-disjoint is not necessarily project- or algorithm-disjoint: the archive
does not supply those grouping labels. Further evaluation needs independently
labeled target-project Python/Java examples, with shared algorithm families and
generated variants kept in one split. Include hard negatives such as maximum vs
filtering, sum vs frequency counting, and sorting vs reversal.

## Run a bounded pilot

From the backend directory, using the existing Python 3.11 environment:

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.\.venv311\Scripts\python.exe train.py --dataset_zip 'C:\path\to\dataset.zip' --output_dir training_runs\java-pilot --train_functions 256 --eval_functions 128 --epochs 20
```

The output directory must be new. It never overwrites `saved_models` or a previous
experiment. `--threads 2` limits training CPU threads. The default loads one frozen
encoder in the training process; `--encoder_process local-service` instead reuses
the authenticated base model at `127.0.0.1:8765`, reading its key locally without
printing it. That option requires the laptop service to be running in embedding
mode and can contend with live analyses. The default does not restart the tunnel.

Use `--train_functions 0 --eval_functions 0` for all functions only after sizing
the run. This may take substantial time. It is still head training, not encoder
fine-tuning. Overlength code is recorded and excluded, never silently truncated;
reported metrics therefore cover only the eligible subset. No uploaded source is
executed. Source is read locally; no dataset is uploaded to an external trainer.

## What is learned and measured

- Production tokenization and data-flow extraction produce frozen CLS vectors.
- The head learns from `[abs(left-right), left*right]`, so evaluation is invariant
  to file order. Gradient updates change actual head weights, not score constants.
- Epoch and operating threshold selection use validation data only. Defaults seek
  empirical precision of at least 0.95 and recall of at least 0.50; these are
  operating targets, not accuracy promises.
- The selected head is evaluated once on the test pairs. Do not tune another run
  using these test results and continue calling the same set untouched.
- `model.json` reports TP/FP/FN/TN, precision, recall, F1, counts and exclusions.
  `audit.json`, `pairs.json`, `history.json`, `selection.json` and
  `test_predictions.json` record the experiment. Local numeric feature caches
  and weights are ignored by Git and excluded from container build context.

## Serving gate and activation

Candidates are separate from the live model even if they pass. The gate requires
at least 100 positive and 100 negative examples in each evaluation split, minimum
recall, and a 95% Wilson lower precision estimate meeting the target in both
validation and test. Pairs sharing functions are correlated, so that estimate is
an approximate diagnostic, not a rigorous independent-sample confidence guarantee.
Review target-project performance and the dataset scope before activation.

An ineligible checkpoint cannot be loaded by the serving loader. Eligible weights
need their matching `model.json`; the loader checks format, SHA-256, operating
threshold and evaluated language pairs, then loads tensor-only state strictly.
Legacy unvalidated `model.bin` files are incompatible with the new symmetric head.

For a reviewed eligible candidate, copy **both** `model.bin` and `model.json` into
`backend/saved_models/`, then restart the model service. Restarting a Quick Tunnel
changes its URL; update Render accordingly. Deploy the updated backend first so
it honors the classifier's threshold and evaluated language scope. The current
pilot never installs itself or changes Render settings.

The remote API carries the selected threshold. The application uses the maximum
of that threshold, its configured classifier floor and the user's slider. A
Java-only evaluated head does not bypass behavioral requirements for Python or
cross-language pairs. Observed counterexamples override classifier scores.

No finite dataset or training run establishes 100% correctness on arbitrary
programs. Model-only benchmark results and the application's final filtered
results are different measurements; neither should be presented as the other.
