# Hosting after Oracle signup failed

**Updated preference:** You have accepted losing existing data. Use the
[fresh-database steps in the complete setup guide](COMPLETE-SETUP.md) instead of
the export/restore instructions below. Those migration instructions are only
needed if you later decide to preserve existing data.

Checked on October 10, 2026. This is a deployment guide, not confirmation of a
live migration. The selected budget is FREE ONLY. Free allowances and policies can change.
The user confirmed that codes-clones-instance (PostgreSQL) will be suspended on
October 16, 2026; the email does not announce expiry of the web service.

## What the two problems mean

- The application defaults to structural detection on small Render instances.
  Structural mode does not check Type-4 clones. The existing remote model client
  can use any compatible HTTPS model server; it is not tied to Oracle.
- A 30-day expiry on Render normally refers to Free Postgres. Confirm the service
  named in the October 16 notice. Render's free web service has different limits.
- Hosting the model enables semantic comparisons. The base GraphCodeBERT model
  produces candidates, not proven semantic equivalence. A larger server does not
  train the model or establish its accuracy.

## First: preserve the database before October 16

Render documents that free Postgres becomes inaccessible after 30 days and is
deleted after a further 14-day upgrade grace period. Export before expiry.
Source: <https://render.com/docs/free>.

Use **Neon Free** for the database and retain the existing Render API. This
removes the Render 30-day database deadline, but remains subject to Neon's
free-plan quotas and policies. It is not a promise of permanent free hosting.
Complete the migration before October 16, preferably by October 15.

Neon's published allowance currently includes 1 GB storage and 100 CU-hours per
project per month. Check the console before creating the project.
Source: <https://neon.com/blog/neon-free-plan-1-gb-per-project>.

### Migrate existing accounts and results to Neon

1. Create a Neon account and a Free Postgres project. Choose a region near your
   Render API and a Postgres major version at least as new as the source.
2. In Render, open the **Postgres database**, then its connection details. Copy
   the **external** database URL for migration from your laptop.
3. In Neon, open **Connect**, disable connection pooling for the restore, and copy
   the direct connection URL. Preserve its SSL parameters.
4. Install PostgreSQL client tools if `pg_dump`, `pg_restore` and `psql` are not
   available. Use tools matching the target major version and no older than the
   source. Do not put database URLs or exports in Git or chat.
5. Schedule a short maintenance window. Let analyses finish and stop application
   writes, including workers, before the final dump. Keep writes stopped through
   restore, verification and switching the application to Neon.
6. In PowerShell, use an empty destination database and store the backup outside
   the repository. Run each command separately and stop on any error:

   ```powershell
   $sourceUrl = Read-Host 'Render external Postgres URL (private)'
   $targetUrl = Read-Host 'Neon DIRECT Postgres URL (private)'
   $dumpPath = Join-Path $env:USERPROFILE ('clonescope-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.dump')
   pg_dump --dbname "$sourceUrl" --format=custom --file "$dumpPath"
   if ($LASTEXITCODE -ne 0) { throw 'Backup failed; do not continue' }
   pg_restore --list "$dumpPath"
   pg_restore --dbname "$targetUrl" --no-owner --no-acl --exit-on-error --single-transaction "$dumpPath"
   if ($LASTEXITCODE -ne 0) { throw 'Restore failed; do not switch the application' }
   ```

   PostgreSQL restore reference:
   <https://www.postgresql.org/docs/17/app-pgrestore.html>.

7. Compare table row counts on the source and destination, especially users,
   jobs and saved results. Verify relationships and representative saved code.
8. Set Render's backend `DATABASE_URL` to the Neon connection URL, including
   `sslmode=require` and any other provided SSL parameters. Use a URL beginning
   `postgresql://`. Update a separate worker too, if one is deployed. Leave the
   existing application `SECRET_KEY` unchanged.
9. Redeploy. Verify an existing login, old job history, a new analysis, and that
   the new job actually appears in Neon. Only then reopen access to users.
10. Retain the old database and export until verification is complete. Returning
    to the old URL after accepting new writes on Neon would lose those new writes
    unless they are reconciled first.

**Project-specific check:** `backend/database.py` currently falls back to local
SQLite if PostgreSQL cannot connect. `/health` does not check database connectivity.
If logs contain `Falling back to local SQLite`, do not consider the migration
successful. Fix the connection before reopening access. Render's local filesystem
is ephemeral, so this fallback cannot preserve production data. If the old app
was already using SQLite, a Postgres export will not contain that SQLite data;
identify and preserve the actual data source before restarting it.

## Then: choose where GraphCodeBERT runs

### Lowest infrastructure cost: your own computer

For local demonstrations, run the backend on a computer with enough available
RAM, and set `DETECTION_ENGINE=full`, `USE_GPU=false`, and `BATCH_SIZE=1`.
Use the frontend locally as described in the repository README.

This avoids a model hosting bill. It is available only while the computer and
application are running. A Render backend cannot reach your laptop using
`localhost`; public access requires separately configured authenticated HTTPS.

### Use the Render website with a model running on your laptop

For a free demonstration, the route is:

```text
Frontend -> Render API -> Neon Postgres
                      -> HTTPS tunnel -> local GraphCodeBERT service
```

The following steps use the existing Python 3.11 environment in this workspace.
The real-model tests passed on this computer. No cloud tunnel was started or
verified as part of that test.

1. Open PowerShell and start only the model service. Generate a key once, then
   save it privately for reuse; do not generate a different key on every restart.

   ```powershell
   Set-Location D:\code_clone_detector\backend
   .\.venv311\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
   $env:SEMANTIC_API_KEY = Read-Host 'Paste the generated model key'
   $env:DETECTION_ENGINE = 'full'
   $env:USE_GPU = 'false'
   $env:BATCH_SIZE = '1'
   $env:OMP_NUM_THREADS = '2'
   $env:MKL_NUM_THREADS = '2'
   .\.venv311\Scripts\python.exe -m uvicorn semantic_service:app --host 127.0.0.1 --port 8001 --workers 1
   ```

2. Leave it running. In another PowerShell window, check readiness:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8001/health
   ```

   Expect `status: ready`. This service does not need the application's database.

3. Install `cloudflared` using the official Windows instructions:
   <https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/>.
   Then open a new PowerShell window if the installation changed PATH, and run:

   ```powershell
   cloudflared tunnel --url http://127.0.0.1:8001
   ```

4. Copy the generated `https://...trycloudflare.com` URL. Open its `/health`
   endpoint and expect the same ready response. `/info` without the shared key
   should return 401. The inference endpoints are protected by the application's
   bearer key. Do not use Cloudflare's interactive email gate for this API.
   Code fragments will travel through Cloudflare to your computer for inference.

5. Make sure the current remote-support code is deployed on Render. Several of
   these files are currently uncommitted: an older Git deployment will not
   contain them. Include the updated config and engine plus
   `graphcodebert/remote.py`; never commit `.env` or keys.
6. Set the Render backend environment to:

   ```dotenv
   DETECTION_ENGINE=remote
   SEMANTIC_API_URL=https://YOUR-GENERATED-HOST.trycloudflare.com
   SEMANTIC_API_KEY=THE_SAME_KEY_AS_YOUR_LOCAL_MODEL
   SEMANTIC_API_TIMEOUT=180
   ```

7. Save and redeploy. Apply the same settings to a separate detection worker if
   one is deployed. Keep the key out of frontend variables.
8. Upload `examples/type4-demo` for a new analysis. Confirm semantic comparisons
   are greater than zero and the result reports embedding mode. Prior saved
   analyses do not change automatically. Start with small inputs; CPU inference
   and proxy request limits can affect larger analyses.
9. Keep both the model and tunnel processes running, with your computer awake
   and connected. When you recreate a Quick Tunnel, update Render's URL and
   redeploy because the hostname changes. Remote-model outages cause analysis
   to fail explicitly; the app does not silently skip semantics.

Cloudflare Quick Tunnels need no account or domain, but are for testing and
have no uptime guarantee. This is a free demo setup, **not permanent always-on
hosting**. Source: <https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/>.

For continuous availability without a hosting subscription, you need access to
an existing always-on machine (for example, a university server with permission)
and a stable authenticated HTTPS endpoint. This moves the hardware and uptime
responsibility to that machine. The model container in this directory can run
on a compatible Linux server; it is not tied to Oracle. There is no verified
unconditional free, always-on replacement established by this guide.

### Why not promise a free Hugging Face Docker Space?

Current Hugging Face documentation says new Docker Spaces require a paid plan,
even though CPU Basic has no hourly hardware charge. The free ZeroGPU exception
is for eligible Gradio Spaces and is not a drop-in host for this FastAPI Docker
service. CPU Basic also sleeps. Source:
<https://huggingface.co/docs/hub/spaces-overview>.

## Detection validation is separate from hosting

The existing optional integration tests check recursive versus iterative
factorial, Python versus Java quicksort, a renamed Type-2 pair and an unrelated
negative. They are useful deployment smoke tests, not an accuracy benchmark.
For reliable Type-4 performance, evaluate labeled positive and hard-negative
pairs from the intended languages and tune or fine-tune using a separate
validation set. Do not lower thresholds merely to force every example to match.

## Checks completed in this workspace

On October 10, 2026, the following passed: 11 tests, including real cached model
inference and the local service/client integration. This does not verify Render,
Neon or a public tunnel, and is not a representative accuracy benchmark.

```powershell
Set-Location D:\code_clone_detector\backend
$env:RUN_MODEL_TESTS='1'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:DETECTION_ENGINE='full'
$env:DATABASE_URL='sqlite://'
.\.venv311\Scripts\python.exe -m unittest test_type4_model test_remote_semantics -q
```
