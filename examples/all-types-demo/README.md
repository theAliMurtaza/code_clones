# All four clone types in one analysis

Run either example with the laptop model running and Render configured for
`DETECTION_ENGINE=remote`, or a local backend using the full GraphCodeBERT model.
Use a similarity threshold of 0.50 for this demonstration. The base-model Type-4
cutoff remains at least 0.85; the UI threshold does not lower that minimum.

- **Single file:** upload `single_file.py` alone. Its two `add` definitions are
  intentionally duplicated source for analysis; do not use this file as a library.
- **Folder:** choose the `folder` subdirectory, which includes nested files. The
  same six functions are spread across files to exercise recursive uploads.

Expected examples (other pairs can also match):

| Pair | Category |
|---|---|
| First `add` / second `add` | Type-1: identical tokens despite the comment |
| `add` / `sum_values` | Type-2: renamed identifiers |
| `add` / `adjusted_sum` | Type-3: similar syntax with an added operation |
| `factorial` / `fact` | Type-4 candidate: recursive and iterative implementations |

Results show both original line ranges, even when both paths are the same.
Select **All** to view every detected category, or use the individual type filters.
Each pair receives one classification. A file or folder need not contain every
category, and detection is not a guarantee of finding every possible clone.
The base model's Type-4 matches need review; this fixture is not an accuracy benchmark.

If the laptop is offline, a remote-mode job fails explicitly. In lightweight mode,
Types 1–3 remain available, but Type-4 is not checked. Deploy the updated backend
and frontend and start a new analysis; old saved results do not change.
