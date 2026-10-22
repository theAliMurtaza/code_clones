# Run Type-4 detection on your Windows laptop

Render keeps the application API; Neon keeps accounts and results. GraphCodeBERT
runs on the laptop. A free Cloudflare Quick Tunnel forwards HTTPS requests to the
authenticated model service listening only on `127.0.0.1:8765`. No Oracle VM,
domain, router port forwarding, Docker, or paid Hugging Face account is needed.
Uploaded code fragments travel from Render through Cloudflare to your laptop.
The model service does not save them. The base model reports Type-4 candidates,
not proof of equivalent behavior or calibrated probabilities.

## Detection responsibilities and accuracy

- Render extracts and compares Python and Java code regions for Types 1–3,
  requests semantic inference from the model service, and combines the results.
- Neon stores accounts, jobs and results; it does not execute clone detection.
- The laptop runs GraphCodeBERT for Type-4 candidate scoring. Moving the same
  authenticated service to another host later requires updating
  `SEMANTIC_API_URL` and `SEMANTIC_API_KEY` on Render.

Single-file, multiple-file and recursive folder uploads use the same comparison
pipeline. Separate regions within a file and regions across files are compared;
overlapping regions are excluded. A pair is assigned one clone type.

Detection is not guaranteed to be 100% accurate. Type-1 and Type-2 are token-based
rules; Type-3 depends on a similarity threshold; Type-4 currently uses uncalibrated
base-model embeddings. A similarity score of 100% is not an accuracy measurement
or proof that two programs behave identically. False positives and missed clones
remain possible. Functions/methods and source blocks are compared, not every
possible substring. Long regions are chunked, and model token limits still apply.
The current job limit is 200 extracted fragments; larger jobs fail explicitly.

Use `examples/all-types-demo` for single-file, multiple-file and nested-folder
checks. These are regression examples, not a representative accuracy benchmark.
To measure precision and recall, use independently labelled positive and negative
pairs representative of the languages and code you intend to analyse, including
examples outside these fixtures. Do not report a test pass rate as model accuracy.

## Start on this laptop

The existing `backend/.venv311` has the dependencies and cached model weights.
From Windows PowerShell:

```powershell
Set-Location D:\code_clone_detector
.\backend\deploy\Install-LaptopTunnel.ps1
.\backend\deploy\Laptop-Model.ps1 start
.\backend\deploy\Laptop-Model.ps1 status
```

If Windows blocks scripts in that terminal, use
`powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\deploy\Laptop-Model.ps1 start`.
This applies only to that invocation, not the machine's execution policy.

Startup runs in the background with hidden windows. It loads real GraphCodeBERT,
starts a temporary tunnel, checks HTTPS and authentication, and performs a real
embedding request. Wait for `phase: ready`. First startup can take several minutes.
The status command never prints the model secret.

Runtime files are under `backend/deploy/.laptop-model/`, excluded from Git and
Docker build contexts. `model.log`, `tunnel.log` and `launcher.log` contain startup
diagnostics. `model-key.txt` is a private, persistent random secret. Do not upload
or share this directory. Only the model API is exposed, not your local application
database or development server.

## Connect the existing Render backend

Your backend is `https://code-clones.onrender.com`. In its Render dashboard:

1. Deploy repository code containing `graphcodebert/remote.py`, `config.py`, and
   the remote-engine branch in `graphcodebert/engine.py`. Local uncommitted files
   are not automatically available to Render. Keep the existing backend Docker
   deployment and Neon `DATABASE_URL`.
2. Open **Environment**. Add or update these four variables individually, using
   the values in `.laptop-model/render.env` once the launcher says ready:

   ```dotenv
   DETECTION_ENGINE=remote
   SEMANTIC_API_URL=https://YOUR_CURRENT_TUNNEL.trycloudflare.com
   SEMANTIC_API_KEY=YOUR_PRIVATE_MODEL_KEY
   SEMANTIC_API_TIMEOUT=180
   ```

3. To copy the key without displaying it in logs or chat:

   ```powershell
   .\backend\deploy\Laptop-Model.ps1 copy-key
   ```

   Paste it into the backend's `SEMANTIC_API_KEY`. Never put this key in frontend
   variables or source control. These four variables do not replace your existing
   database, signing key, allowed origins, or other environment settings.
4. Choose **Save and deploy**. Apply the same settings to a separate worker if
   one exists. There is no frontend API URL change.
5. Upload the files in `examples/type4-demo` for a NEW analysis. The results should
   report semantic comparisons performed and embedding mode. The demo's factorial
   and cross-language sorting examples are candidates with the base model. Old
   analyses are not recomputed. Other inputs may legitimately yield no candidates.

## Every demonstration

Keep the laptop on, awake, and connected. Plug it into power and temporarily set
sleep while plugged in to Never if needed; restore your preference afterward.
The launcher does not modify Windows power settings. CPU inference can be slow;
start with a small set of files. Concurrent model requests return an explicit busy
error rather than loading additional model copies.

The HTTPS URL changes whenever the tunnel is restarted. Run `status`, copy the new
URL to Render's `SEMANTIC_API_URL`, and redeploy. The model key stays the same.
While the laptop is offline, remote semantic jobs fail explicitly; there is no
silent downgrade to structural detection.

```powershell
.\backend\deploy\Laptop-Model.ps1 status
.\backend\deploy\Laptop-Model.ps1 stop
```

Stop closes only this launcher's own model/tunnel processes. It can take a short
time if a startup network probe is finishing. Starting again while it is running
does not create another model copy. Stopping removes the generated `render.env`
so an expired tunnel is not presented as usable configuration.

Cloudflare Quick Tunnels are for testing/development with no uptime guarantee.
They have a 200 in-flight request limit and do not support SSE; this service uses
ordinary JSON requests. The launcher uses HTTP/2 transport and an isolated empty
configuration so it does not consume any unrelated named-tunnel configuration.
If the laptop's DNS resolver cannot find the new tunnel hostname, the launcher's
HTTPS checks resolve that hostname through Google Public DNS over HTTPS, retaining
the original hostname and normal TLS certificate verification. Windows DNS settings
are not changed. Render continues to use its own DNS resolver.
See [Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
and [official downloads](https://developers.cloudflare.com/tunnel/downloads/).

## If setup fails

- `loading model` then `failed`: inspect `model.log`. Keep the Python 3.11 environment;
  the system Python 3.14 is not the tested model environment.
- `starting tunnel` then `failed`: inspect `tunnel.log`; allow cloudflared outbound
  connections in your firewall. No inbound router port needs to be opened.
- HTTP 401: the Render key does not match `model-key.txt`.
- HTTP 503: the model is busy, unavailable, or failed during inference.
- Tunnel errors after sleep or network changes: stop, start, and update Render's URL.
- Address already in use: another process owns port 8765. Stop the known conflicting
  service before retrying; the launcher intentionally will not terminate it.

On another Windows x64 laptop, install Python 3.11, then prepare dependencies:

```powershell
py -3.11 -m venv backend/.venv311
.\backend\.venv311\Scripts\python.exe -m pip install torch==2.3.0 --index-url https://download.pytorch.org/whl/cpu
.\backend\.venv311\Scripts\python.exe -m pip install -r backend/deploy/requirements-semantic.txt
```

The model weights download from Hugging Face on first start. Allow sufficient
memory for the model and Windows (8 GB total RAM is a reasonable starting point;
available memory and workload still need checking).

## Verification

The protocol and real-model integration fixtures can run from `backend`:

```powershell
.\.venv311\Scripts\python.exe -m unittest test_laptop_model test_remote_semantics test_folder_detection -q
$env:RUN_MODEL_TESTS='1'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.\.venv311\Scripts\python.exe -m unittest test_remote_semantics.RealRemoteModelTests -v
```

These check authentication, lifecycle handling, real semantic candidates, renamed
clones and an unrelated negative example. They are not an accuracy benchmark.

## Detection-quality update

Deploy the updated backend (including `behavior_check.py`, `classifier.py`,
`detector.py` and `config.py`) and frontend. Restart the laptop model to load the
updated GraphCodeBERT input reader. A tunnel restart creates a new URL: copy it
from `Laptop-Model.ps1 status` into Render's `SEMANTIC_API_URL`. Then run a new
analysis; saved results are not recomputed.

Type-3 now uses weighted syntax overlap, retaining literal values and giving
punctuation less influence. This favors precision but may miss some near misses.
Types 1–2 retain their existing exact/normalized-token rules.

For Type-4, a restricted AST interpreter looks for different outputs on the same
bounded inputs. It supports a subset of pure Python, with strict step, recursion,
container and integer limits. It cannot execute imports, attributes, files, network
calls, `eval` or `exec`. Different observed outputs reject a semantic candidate.
Disjoint tested input domains can also reject a candidate. These checks assume
the functions' domains are not restricted by an external contract; domain-specific
functions may need review. Java, unsupported syntax and exhausted budgets are
reported as inconclusive, never as behaviorally verified.

The base model normally needs a cosine score of 0.85. A candidate with at least
five agreeing checks and three distinct outputs may use the separate 0.70 floor
(`TYPE4_CORROBORATED_EMBEDDING_SIM`). The user's chosen threshold still applies.
This is an experimental decision rule, not a learned/calibrated probability.
Constant outputs alone cannot lower the floor. Unchecked high-score candidates
still require review. No model weights were trained or replaced by this update.

Model input extraction now handles UTF-8 byte offsets correctly. A missing parser
or a region over 509 model subword tokens fails explicitly rather than producing
scores from corrupted or truncated input; split an oversized region into smaller
units. The earlier 80-line chunking is not a guarantee of fitting that token limit.

For the targeted real-model comparison:

```powershell
.\.venv311\Scripts\python.exe evaluate_detection_quality.py
```

Run this from `backend` with the same offline and thread environment settings used
for the integration tests. See `examples/accuracy-evaluation` for the results and
their limitations. These development fixtures do not establish general accuracy.

### Apply the revised detector

Deploy the updated backend and frontend, including `behavior_check.py`. Restart
the laptop model service so it loads the updated model-input reader:

```powershell
.\Laptop-Model.ps1 stop
.\Laptop-Model.ps1 start
.\Laptop-Model.ps1 status
```

Run these from `backend/deploy`. Once ready, update Render's `SEMANTIC_API_URL`
to the new tunnel URL and save/deploy. Keep the existing private key. Start a new
analysis: stored results are not automatically recomputed. New results expose
`detector_revision: weighted-syntax-counterexamples-v2` and per-pair Type-4
descriptions distinguish agreeing bounded samples from unverified behavior.
