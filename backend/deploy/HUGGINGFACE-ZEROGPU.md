# Host CloneScope's model on Hugging Face ZeroGPU

Render continues to run the backend and Types 1–3 detection. Neon continues to
store application data. The Space runs GraphCodeBERT inference for Type 4, using
Gradio's queued API. Once deployment is verified, your laptop can be turned off.

This change moves inference; it does not improve the model's accuracy by itself.
The recent Java training pilot failed its validation targets, so its weights are
not included. This package uses base GraphCodeBERT and the backend's stricter
semantic acceptance checks. A model similarity score is not an accuracy percentage.

## 1. Create the Space

Open <https://huggingface.co/new-space> while signed into your eligible account.

| Setting | Select |
| --- | --- |
| Owner | Your account with ZeroGPU eligibility |
| Space name | `clonescope-model` (or another name you choose) |
| SDK | **Gradio** |
| Template | **Blank** |
| Hardware | **ZeroGPU** |
| Visibility | **Private**, if available for your account |

If hardware is not shown during creation, select ZeroGPU in **Settings → Hardware**
after creation. Confirm it is ZeroGPU before proceeding. Docker and Static are not
the SDKs for this package. If you choose Public, the model service source will be
visible; its inference endpoints still require the shared key below.

## 2. Add the model secret

In the Space, open **Settings → Variables and secrets → New secret**.

* Name: `SEMANTIC_API_KEY`
* Value: the **same key** already used by your Render backend.

If Render still uses the laptop-generated key, copy it without printing it by
running this in PowerShell:

```powershell
Set-Location D:\code_clone_detector
.\backend\deploy\Laptop-Model.ps1 copy-key
```

Paste that value into the Space secret. If the key has since been changed in
Render, use Render's current value instead. The key must contain at least 32
characters. Do not put it in source files, the README, or chat. Do not add your
Neon database URL to the Space.

## 3. Upload the prepared model package

The prepared upload folder is:

```text
D:\code_clone_detector\backend\deploy\.hf-space
```

It contains `app.py`, `README.md`, `requirements.txt`, the model modules, and a
file manifest. Upload **the contents** so `app.py` is at the Space repository root.
Do not upload the entire project or the backend's main `requirements.txt`.

The following script preserves nested directories and verifies the export before
uploading. First create a token at <https://huggingface.co/settings/tokens> with
write access to this Space (a fine-grained token scoped to this Space is preferable).
Replace `YOUR_USERNAME/clonescope-model` below with your real Space ID:

```powershell
Set-Location D:\code_clone_detector
.\backend\.venv311\Scripts\python.exe .\backend\deploy\upload_hf_space.py --space YOUR_USERNAME/clonescope-model
```

Paste the write token at the hidden prompt. It is not saved by the script. You can
also use the Space's **Files → Add files → Upload files** interface, preserving
the `graphcodebert` and `graphcodebert/parser` directories.

For a later code update, build a fresh export rather than editing generated files:

```powershell
.\backend\.venv311\Scripts\python.exe .\backend\deploy\build_hf_space.py --output D:\code_clone_detector\backend\deploy\.hf-space-next
.\backend\.venv311\Scripts\python.exe .\backend\deploy\upload_hf_space.py --space YOUR_USERNAME/clonescope-model --folder D:\code_clone_detector\backend\deploy\.hf-space-next
```

Use a different, nonexistent output folder for each export. The builder refuses to
overwrite a previous export. Keep exports private locally; never add secrets to them.

## 4. Wait for the Space to run

Watch the Space's build and runtime logs. The first startup downloads
`microsoft/graphcodebert-base`. The page should eventually say **Running** and show
“CloneScope model service.” It intentionally has no code-upload form; users upload
files through your existing CloneScope app.

The included README pins Gradio 6.9.0 and Python 3.10; requirements pin a compatible
ZeroGPU/torch stack. The app imports `spaces` first and initializes the model on
CUDA at startup, as required by the current ZeroGPU runtime. GPU inference runs
inside `@spaces.GPU` functions.

Open the running app in a new tab and copy its actual direct URL:

```text
https://YOUR-ACTUAL-SPACE-HOST.hf.space
```

Use that URL, not `https://huggingface.co/spaces/USERNAME/NAME`, and not a guessed
hostname. It remains stable across ordinary Space restarts.

## 5. Deploy the backend changes to Render

Deploy this updated backend through the same repository/branch or deployment
method your Render service already uses. The changes include
`graphcodebert/gradio_remote.py`, the engine/config updates, and
`gradio-client==2.3.0` in `backend/requirements.txt`. Changing only the URL on an
old deployment will not work: the old client speaks the laptop HTTP protocol.

Create a separate Hugging Face **read** token, or a fine-grained token with access
to the Space, for Render. This token authenticates the private Space and attributes
ZeroGPU requests to your HF account. It is different from `SEMANTIC_API_KEY`.

In **Render → your backend → Environment**, set:

| Variable | Value |
| --- | --- |
| `DETECTION_ENGINE` | `remote` |
| `SEMANTIC_API_TRANSPORT` | `gradio` |
| `SEMANTIC_API_URL` | Your actual `https://...hf.space` URL |
| `SEMANTIC_API_KEY` | Exactly the same key as the Space secret |
| `HF_TOKEN` | Your Hugging Face read/scoped token |
| `SEMANTIC_API_TIMEOUT` | `300` |

Save and redeploy. Leave the Neon connection and frontend backend URL unchanged.
Do not put either token in the frontend or a `VITE_` variable.

## 6. Verify, then stop the laptop service

Run a **new** analysis in CloneScope with a small Python example containing a
known semantic clone; existing saved results do not rerun automatically. Check
that the job completes and its coverage reports Type-4 analysis rather than a
service error. Check the Space logs for the inference request. Then stop the
laptop service and repeat a new analysis to confirm the migration:

```powershell
Set-Location D:\code_clone_detector
.\backend\deploy\Laptop-Model.ps1 stop
```

You no longer need to update a Cloudflare tunnel URL after laptop restarts.

## Limits and troubleshooting

* **Quota / queue:** ZeroGPU is shared, quota-limited inference. Current documented
  free-account GPU quota is 5 minutes/day; requests through one Render `HF_TOKEN`
  share that account's allowance. A busy Space, quota exhaustion, or a cold start
  can delay or fail an analysis. This is not unlimited, always-available hosting.
* **Type-4 service failure:** check that the Space is Running, hardware is ZeroGPU,
  both model keys match, the HF token has Space access, the direct URL is correct,
  and Render deployed the new client. A failed GPU request must not be presented
  as a completed Type-4 scan.
* **`SEMANTIC_API_KEY` startup error:** add the Space secret and restart the Space.
* **`Could not get API info` after an `SSR (experimental)` startup message:**
  upload the latest package, which explicitly sets `ssr_mode=False`. This disables
  the extra server-side page renderer. If the error persists, inspect Container
  logs and verify the queued API; this message alone does not prove model failure.
* **Build conflict with `pydantic-settings==2.3.0`:** upload the corrected Space
  package, which pins `pydantic-settings==2.5.2`. Hugging Face installs
  `gradio[mcp,oauth]`; the MCP extra requires settings version 2.5.2 or newer.
  The main backend requirements are separate from the Space requirements.
* **No Type-4 matches:** a successful request is not proof that every possible
  semantic clone was detected. The base model's checks deliberately reject
  unverified candidates; the current Java pilot is not a validated replacement.
* **Laptop rollback:** start the laptop service, set Render's
  `SEMANTIC_API_TRANSPORT=http`, and set `SEMANTIC_API_URL` to its newly generated
  tunnel URL. Keep the matching model key and redeploy.

Local tests exercise authentication, payload limits, a real Gradio client/server
queue round trip, response validation, and the export allowlist. Actual HF GPU
allocation, account quota, and private-Space authorization must be verified after
upload; they cannot be confirmed by the local CPU-only tests.

To reproduce the Space API checks in the isolated test environment, include the
extras Hugging Face adds, rather than testing plain Gradio alone:

```powershell
Set-Location D:\code_clone_detector\backend
.\.venv-hf\Scripts\python.exe -m pip install "gradio[mcp,oauth]==6.9.0" "pydantic-settings==2.5.2"
.\.venv-hf\Scripts\python.exe -m pip check
.\.venv-hf\Scripts\python.exe -m unittest test_zerogpu -q
```

Official references (checked October 23, 2026):
[ZeroGPU](https://huggingface.co/docs/hub/spaces-zerogpu),
[Space configuration](https://huggingface.co/docs/hub/spaces-config-reference),
[access tokens](https://huggingface.co/docs/hub/security-tokens).
