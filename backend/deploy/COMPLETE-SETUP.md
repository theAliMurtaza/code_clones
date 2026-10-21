# CloneScope: complete free deployment with Neon, Oracle and Render

Prepared October 10, 2026; project settings reviewed October 14, 2026 for
`D:\code_clone_detector`.

This guide uses your existing repository and free-only budget. It prepares the
deployment; it does not mean your cloud accounts or services have been changed.
The confirmed Render PostgreSQL deadline is **October 16, 2026**. Complete the
database switch by October 15 if possible, independently of Oracle signup.
You have accepted losing the existing data: this guide now starts with an empty
Neon database. Old accounts and analyses will not be copied; register again.

Recommended order: complete steps 1–4 (fresh Neon database) today, then Oracle
and DNS in steps 5–9, application deployment in steps 10–12, and the end-to-end
checks in step 13. An Oracle signup failure must not delay the database switch.

```text
Browser -> React frontend (existing host or Render Static Site)
        -> FastAPI backend (Render Free)
             -> accounts, source files and results: Neon PostgreSQL
             -> semantic inference: Oracle A1 -> GraphCodeBERT
```

DuckDNS supplies a free hostname for Oracle. Caddy, already included in the model
Compose configuration, provides HTTPS. The model runs on Oracle, so your laptop
can be off after deployment. Source fragments travel from Render to Oracle.

This is a small-project deployment with free-tier limitations. Render can sleep,
Oracle can reclaim idle VMs, and Neon has quotas. No fixed database trial expiry
does not mean guaranteed permanent uptime. Hosting enables Type-4 candidate
detection; it does not prove general semantic equivalence or train your model.

## 1. Record the settings you will need

Keep these privately in a password manager or local notes outside Git:

| Name used below | Where to get it |
|---|---|
| Neon direct database URL | Neon project -> Connect -> pooling disabled |
| Existing app `SECRET_KEY` | Render backend -> Environment |
| Backend URL | Existing Render web service's HTTPS URL |
| Frontend URL | Your existing frontend's HTTPS URL |
| Oracle public IPv4 | Oracle instance details, once created |
| SSH private key path | Key saved when creating the Oracle instance |
| Model hostname | A unique name you create on DuckDNS |
| Model API key | Generate in step 9; same value on Oracle and Render |

Values such as `YOUR_BACKEND` and `YOUR_MODEL_NAME` are placeholders: replace them.
Use PowerShell blocks on your Windows laptop and Bash blocks only after SSH to
Oracle. Do not paste database URLs, API keys or private SSH keys into chat.

## 2. Start fresh instead of migrating old data

You have accepted losing the existing accounts, uploaded source files and saved
analyses. Skip PostgreSQL tool installation, exports, restores, source-version
matching and old-data comparisons. There is no need to delete or reset the old
database to connect the app to a new empty database.

Keep your current frontend and backend services. Only the backend's database
connection changes. Users must register again after the switch. Existing browser
sessions may contain an old login token; sign out and use a newly created account.

## 3. Create an empty Neon Free database

1. Sign up at [Neon](https://neon.com/).
2. Create a project named `clonescope` on the **Free** plan.
3. Select a region geographically near your Render backend. A supported default
   PostgreSQL version is sufficient; there is no old-data restore to match.
4. Use the new project's empty database, such as `neondb`. Do not import old data.
5. Open **Connect**, select that database and its owner role, and disable pooling
   to get a direct connection URL for this small single-instance deployment.
6. Copy only the connection URL, beginning `postgresql://`, and keep all provided
   SSL parameters. Do not copy a surrounding `psql` command or quotation marks.

The published Free allowance currently includes 1 GB storage and 100 CU-hours per
project per month. Check the current console allowance.
Source: [Neon's Free-plan announcement](https://neon.com/blog/neon-free-plan-1-gb-per-project).

## 4. Connect Render and let the app create the tables

1. Open your existing Render **backend web service**, not the expiring PostgreSQL
   service. Let active analyses finish before redeploying.
2. Open **Environment**, edit `DATABASE_URL`, and paste the new Neon URL. Keep
   `sslmode=require` and any other supplied SSL parameters. Use `postgresql://`.
3. Keep your existing strong `SECRET_KEY`. The database password and app signing
   key are separate values. No signing-key change is required for a new database.
4. Leave detection settings as they are for this database-only step. Oracle model
   setup follows separately; it does not need to delay the database switch.
5. Click **Save and deploy** (or save, then deploy the latest commit). If a separate
   worker is deployed, update its `DATABASE_URL` as well.
6. Watch the logs for `Database tables ready`. The startup handler in
   `backend/main.py` calls `Base.metadata.create_all(bind=engine)` and creates
   `users`, `jobs`, `source_files` and `clone_pairs` automatically. You do not need
   to run SQL table-creation scripts yourself.
7. Open your frontend, sign out of any old session and **register a new account**.
8. In Neon SQL Editor, run:

   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public' ORDER BY table_name;
   SELECT id, name, created_at FROM users ORDER BY created_at DESC LIMIT 5;
   ```

   Confirm the four application tables and the new account exist in Neon.
9. Sign in with that new account. Old accounts and results will not appear.
10. After the model is configured, run a new analysis and verify it in Neon:

    ```sql
    SELECT id, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 5;
    ```

**Do not use `/health` or the startup log alone as proof of a successful switch.**
The current `database.py` silently falls back to local SQLite if PostgreSQL cannot
connect, and can create tables there. If logs say `Falling back to local SQLite`,
fix the Neon URL/SSL connection and redeploy. The new account must actually appear
in Neon; otherwise future records could disappear after a Render restart.

Complete this switch before October 16. Once the app is confirmed to use Neon,
expiry of the old Render database no longer affects its new accounts and results.
No export or restore is required, and this guide has not deleted any live database.
Proceed with Oracle independently of the old database.

## 5. Create the Oracle account and A1 VM

1. Visit [Oracle Free Tier signup](https://signup.cloud.oracle.com/).
2. Use accurate contact and billing information and an accepted physical card.
   Oracle uses card verification. If signup fails, use the support Chat linked
   from the [Free Tier FAQ](https://www.oracle.com/cloud/free/faq/); save the exact
   error text. Account approval cannot be guaranteed by project configuration.
3. Once approved, use your tenancy's **home region**.
4. Open **Compute -> Instances -> Create instance**.
5. Name it `clonescope-model` and select:

   | Setting | Value |
   |---|---|
   | Image | Ubuntu 24.04, ARM64/aarch64 |
   | Shape | `VM.Standard.A1.Flex` |
   | OCPUs | 2 |
   | RAM | 12 GB |
   | Boot volume | 50 GB, within the account's free total |
   | Network | Public subnet with an internet-gateway route |
   | Public IPv4 | Assign one |
   | SSH key | Save the generated private key, or supply your own public key |

6. Confirm these resources fit Always Free allowances; do not rely on trial
   credits or add paid volumes, shapes, support plans or extras.
7. Create the instance and wait for Running. Record its public IPv4.

Oracle currently documents 2 A1 OCPUs and 12 GB total memory for Always Free, plus
200 GB combined boot/block storage. If other VMs consume that allowance, account
for them. A1 is ARM, so use the ARM Ubuntu image. The 1 GB AMD Micro is too small
for this model setup. If A1 has no capacity, try another availability domain in
your home region or retry later. Do not buy a different shape to stay within a
free-only plan. [Oracle resource limits](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

## 6. Set Oracle networking and a free hostname

1. From the instance's primary VNIC/subnet, open its attached security list or
   network security group. Add stateful TCP ingress rules:

   | Source | Destination port | Purpose |
   |---|---|---|
   | Your public IPv4 followed by `/32` | 22 | SSH administration |
   | `0.0.0.0/0` | 80 | HTTPS certificate validation and redirects |
   | `0.0.0.0/0` | 443 | Authenticated model API over HTTPS |

2. Verify the subnet has `0.0.0.0/0` routed to an enabled internet gateway and
   permits outbound DNS/HTTPS for package and model downloads. Standard outbound
   rules normally already allow this.
3. Do not publish model port 8000 or database ports. The supplied Docker network
   keeps port 8000 internal; only Caddy publishes ports 80 and 443.
4. Sign in at [DuckDNS](https://www.duckdns.org/). Add an available name, for
   example `YOUR_MODEL_NAME`, which becomes `YOUR_MODEL_NAME.duckdns.org`.
5. Set its IPv4 explicitly to the Oracle public IPv4. Do not leave an automatically
   detected laptop IP there. Leave IPv6 empty unless you configured working IPv6.
6. On Windows, verify DNS after it propagates:

   ```powershell
   Resolve-DnsName YOUR_MODEL_NAME.duckdns.org -Type A
   ```

It must return the Oracle IP. DuckDNS is a free DNS service; no domain purchase
is needed. Its account token is not your model API key and is not needed by this
Caddy setup. Update the record if Oracle's public IP ever changes.
[DuckDNS documentation](https://www.duckdns.org/spec.jsp).

## 7. SSH into Oracle and install Docker

On **Windows PowerShell**, set your actual values:

```powershell
$sshKey = Read-Host 'Full path of saved Oracle SSH private key'
$oracleIp = Read-Host 'Oracle public IPv4'
ssh -i "$sshKey" "ubuntu@$oracleIp"
```

Check the host fingerprint when connecting for the first time. The following
commands run in the **Oracle Ubuntu shell**, not PowerShell. Confirm the machine:

```bash
uname -m
free -h
df -h /
```

Expect `aarch64`, roughly 12 GB assigned RAM, and available disk space.

Install from Docker's Ubuntu repository on this new VM:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker run --rm hello-world
sudo docker compose version
```

Stop if any installation command fails. These instructions assume a new VM with
no conflicting Docker packages. [Official Docker Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/).

The guest OS firewall also has to permit web traffic. Do not flush its rules or
disable the whole firewall. Check `sudo ufw status` and `sudo iptables -S` if web
ports remain unreachable after containers start. Docker publishes forwarded
ports, so inspect the forwarding chains as well as host INPUT rules. Keep Oracle's
network security rules as the outer restriction. Record any deliberate firewall
changes and make them persistent using the firewall manager actually installed.

## 8. Transfer only the model deployment files

Use a second **Windows PowerShell** window. Re-enter `$sshKey` and `$oracleIp` if
this is a new session. Build an archive from explicit source paths so application
secrets, databases, caches and virtual environments are excluded:

```powershell
Set-Location D:\code_clone_detector
$sshKey = Read-Host 'Full path of saved Oracle SSH private key'
$oracleIp = Read-Host 'Oracle public IPv4'
$modelArchive = Join-Path $env:TEMP 'clonescope-model.tar.gz'
tar -czf "$modelArchive" --exclude=__pycache__ --exclude=*.pyc --exclude=*.so -C backend config.py semantic_service.py graphcodebert deploy/Dockerfile.semantic deploy/requirements-semantic.txt deploy/compose.oracle.yml deploy/Caddyfile deploy/.env.example
if ($LASTEXITCODE -ne 0) { throw 'Archive creation failed.' }
tar -tzf "$modelArchive"
scp -i "$sshKey" "$modelArchive" "ubuntu@${oracleIp}:/home/ubuntu/clonescope-model.tar.gz"
if ($LASTEXITCODE -ne 0) { throw 'Upload failed.' }
```

The only environment file in that archive must be the placeholder `.env.example`.
The current parser uses installed language packages; old local `.so` binaries are
not needed on ARM. On **Oracle**, extract into a new directory:

```bash
mkdir -p /home/ubuntu/clonescope-model/backend
tar -xzf /home/ubuntu/clonescope-model.tar.gz -C /home/ubuntu/clonescope-model/backend
cd /home/ubuntu/clonescope-model/backend/deploy
```

This copies the current local model code even if your latest work is not yet in
GitHub. Step 10 separately publishes the application code Render needs.

## 9. Start the model with HTTPS

On **Oracle**, from `/home/ubuntu/clonescope-model/backend/deploy`:

```bash
cp .env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
nano .env
```

Set exactly these two values, replacing the examples:

```dotenv
MODEL_DOMAIN=YOUR_MODEL_NAME.duckdns.org
SEMANTIC_API_KEY=YOUR_GENERATED_RANDOM_KEY
```

Save the key privately for the Render step. `MODEL_DOMAIN` has no `https://` and
no path. Save nano with Ctrl+O, Enter; exit with Ctrl+X. Do not overwrite an
existing working `.env` on later updates.

```bash
chmod 600 .env
sudo docker compose -f compose.oracle.yml config --quiet
sudo docker compose -f compose.oracle.yml up -d --build
sudo docker compose -f compose.oracle.yml ps
sudo docker compose -f compose.oracle.yml logs --tail=100 model
sudo docker compose -f compose.oracle.yml logs --tail=100 https
```

First startup downloads model weights and may take several minutes. A successful
image build alone is not proof of model readiness. The model must load and pass
its health check. Caddy issues and renews the certificate once DNS and ports are
correct. [Caddy HTTPS requirements](https://caddyserver.com/docs/automatic-https).

From **Windows PowerShell**, test the public address:

```powershell
$modelUrl = 'https://YOUR_MODEL_NAME.duckdns.org'
Invoke-RestMethod "$modelUrl/health"
curl.exe -i "$modelUrl/info"
$modelKey = Read-Host 'Paste the model API key privately'
$modelHeaders = @{ Authorization = "Bearer $modelKey" }
Invoke-RestMethod "$modelUrl/info" -Headers $modelHeaders
```

Expected outcomes, in order:

- `/health`: `status` equals `ready`.
- `/info` without a key: HTTP **401**.
- `/info` with the correct key: `protocol: 1`, `mode: embedding`.

Then perform an actual small inference:

```powershell
$probe = @{ fragments = @(@{ code = 'print(1 + 1)'; language = 'python' }) } | ConvertTo-Json -Depth 5
$answer = Invoke-RestMethod "$modelUrl/embed" -Method Post -Headers $modelHeaders -ContentType 'application/json' -Body $probe -TimeoutSec 180
$answer.protocol
$answer.mode
$answer.vectors[0].Count
```

Expect `1`, `embedding`, and `768`. Keep the model key private. If the request
fails, fix this before connecting Render. The base-model warning about missing
fine-tuned classifier weights is expected in embedding mode. No GPU is required.

## 10. Publish the current application changes

Your local repository is `https://github.com/theAliMurtaza/code_clones.git`, on
branch `master` when this guide was prepared. Confirm Render deploys that branch.
Do not force-push or discard unrelated local changes.

On **Windows PowerShell**:

```powershell
Set-Location D:\code_clone_detector
git status --short
git diff --check
git diff -- backend/config.py backend/graphcodebert/engine.py
git add -- .gitignore README.md backend/.env.example backend/config.py backend/graphcodebert/engine.py backend/graphcodebert/remote.py backend/semantic_service.py backend/test_remote_semantics.py backend/deploy
git diff --cached --name-only
git diff --cached
```

Review the staged files. They must contain source/configuration templates, not
real `.env` files, keys, database dumps or local data. Commit only after reviewing:

```powershell
git commit -m "Configure remote semantic inference and deployment guides"
git push origin master
```

If Git reports a rejected push, resolve the branch divergence normally; do not
use `--force`. These commands are instructions only; this guide did not push or
commit your changes. Keep automatic deployment disabled until the next step's
environment values are ready.

## 11. Configure and deploy the Render backend

Prefer updating the existing web service so its URL stays unchanged. If creating
a replacement, use **New -> Web Service** and connect the repository above:

| Setting | Value |
|---|---|
| Branch | `master`, or the branch where you published the changes |
| Root directory | `backend` |
| Runtime | Docker |
| Dockerfile path | `./Dockerfile`, relative to `backend` |
| Docker build context | `.` within that root, if the field is shown |
| Compute | Free |
| Health-check path | `/health` |

The existing Dockerfile starts one Uvicorn process and honors Render's `PORT`.
Leave Docker command overrides empty unless your existing deployment requires
one. Do not start multiple workers on a 512 MB instance.

Set backend environment variables individually, without surrounding quotes:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Neon URL with its SSL parameters |
| `SECRET_KEY` | Existing strong app signing key; preserve during the database switch |
| `ALLOWED_ORIGINS` | Exact frontend origin, e.g. `https://YOUR_FRONTEND.onrender.com` |
| `DETECTION_ENGINE` | `remote` |
| `SEMANTIC_API_URL` | `https://YOUR_MODEL_NAME.duckdns.org` |
| `SEMANTIC_API_KEY` | Exact same secret as Oracle's `.env` |
| `SEMANTIC_API_TIMEOUT` | `180` |
| `DEFAULT_THRESHOLD` | `0.50` for the included demonstration |
| `TYPE4_EMBEDDING_SIM` | `0.85` |
| `MAX_FRAGMENTS_PER_JOB` | `80` to start with modest jobs |
| `DEBUG` | `false` |

For a new app without a signing key, generate a strong `SECRET_KEY` separately from the
model key. Do not replace an existing legitimate key unnecessarily. If your
existing key is still a shipped placeholder, replace it and expect users to log
in again. `ALLOWED_ORIGINS` is comma-separated for multiple actual frontend
origins; use no trailing slash and do not point it at the model hostname.

Use **Save and deploy** / **Deploy latest commit** and inspect logs. The remote
setting overrides the Docker image's lightweight default. Do not set `full` on
Render Free. The current upload endpoints execute FastAPI background tasks;
they do not require provisioning Redis or Celery for this setup.

Open `https://YOUR_BACKEND.onrender.com/health`. Expect `status: ok`. Follow with
database and model checks; this endpoint alone verifies neither dependency.

## 12. Connect the frontend

If your frontend is already deployed and the backend URL is unchanged, keep it.
For a new free deployment, create a **Render Static Site** from the same repo:

| Setting | Value |
|---|---|
| Branch | Same deployment branch as backend |
| Root directory | `frontend` |
| Build command | `npm ci && npm run build` |
| Publish directory | `dist` |
| Environment variable | `VITE_API_URL=https://YOUR_BACKEND.onrender.com` |

`VITE_API_URL` must be the backend origin, without `/api` and without a trailing
slash. The frontend appends `/api/...` itself. Rebuild the frontend after changing
this value because Vite embeds it at build time. Never put `DATABASE_URL`,
`SECRET_KEY` or `SEMANTIC_API_KEY` into a `VITE_` variable.

After Render gives you the static-site URL, set that exact origin in the backend's
`ALLOWED_ORIGINS` and redeploy the backend. If your frontend uses browser routes,
configure a rewrite from `/*` to `/index.html` (Rewrite, not Redirect) for direct
links. [Render static-site setup](https://render.com/docs/static-sites).

## 13. Verify the complete project

1. Open the backend `/health` and wait for Render to wake before opening the app.
2. Open the frontend. Confirm its browser network requests go to the Render
   backend URL, not `localhost` or the Oracle model directly.
3. Register a new account and log in. Confirm the account appears in Neon. Old
   accounts and analyses are intentionally absent after the fresh start.
4. Select/upload the folder `D:\code_clone_detector\examples\type4-demo` using
   the browser file/folder picker. A typed laptop path cannot be scanned by a
   cloud backend; the server-path option refers to the Render filesystem.
5. Select similarity threshold **0.50** and start a **new** analysis.
6. Confirm the result completes, reports `embedding` mode and shows
   `semantic_pairs_checked > 0`. The base-model cutoff remains 0.85.
7. Inspect these expected smoke-test results:

   | Pair | Expected |
   |---|---|
   | `recursive.py` / `iterative.py` | Type-4 candidate |
   | `sort.py` / `Sort.java` | Type-4 candidate |
   | `sort.py` / `renamed.py` | Type-2 |
   | `greet.py` with the other examples | No match |

8. Check the newest job in Neon and reopen it from the frontend's history.
9. Restart the backend after jobs finish, then verify the account and job remain.
10. Check Oracle containers recover after a planned VM reboot. The supplied
    containers use `restart: unless-stopped`, and Docker must be enabled at boot.
11. Once all checks pass, restore your desired automatic-deployment setting.

The current code passed 11 local checks earlier on October 10, including real
cached model inference and local remote-service integration. It has not been
tested on your live Oracle ARM VM, Neon project or Render deployment by this
guide. The cloud checks above are the acceptance criteria. Small examples do not
establish precision or recall on arbitrary Type-4 clones.

## 14. Troubleshooting

| Symptom | Check / corrective action |
|---|---|
| Oracle signup fails | Save the exact error and use Oracle signup-support Chat; the app code cannot repair account verification |
| A1 out of capacity | Another availability domain in the home region, or retry later; complete the fresh Neon setup now |
| SSH times out | Public IP, subnet route, port 22 source rule and current laptop public IP |
| SSH permission denied | Ubuntu username, correct private key and local private-key file permissions |
| Docker build fails | Read the first build error; confirm `aarch64`, available disk, outbound internet and pinned dependency wheel availability |
| Model health unavailable | `docker compose ... ps` and `logs --tail=100 model`; wait for successful model loading |
| HTTPS certificate fails | DuckDNS must point to Oracle, no wrong AAAA record, TCP 80/443 reachable, and Caddy logs |
| HTTPS 502 | Caddy is reachable but model container is unavailable or still loading |
| Model API 401 | Shared model key mismatch or wrong Authorization header; redeploy Render after fixing |
| Model API 503 | Busy inference or internal model failure; use one small job and inspect model logs |
| Timeout | Check DNS/TLS first, then logs and inference time; raising a client timeout cannot fix an intermediary timeout |
| Type-4 NOT checked | Wrong Render mode or old Git commit; verify `DETECTION_ENGINE=remote` and remote client deployed |
| Embedding mode, zero Type-4 matches | Not automatically a hosting failure; check semantic comparison count and use the known test folder |
| CORS / browser failed to fetch | Frontend API URL, exact backend allowed origin, cold start, and actual backend error |
| Old accounts are missing | Expected after the fresh start; register again |
| New accounts do not appear in Neon | Wrong database or silent SQLite fallback; verify URL, SSL and actual Neon writes |
| Job stays running after redeploy | In-process background jobs are not durable; rerun interrupted jobs after deployment completes |
| PostgreSQL tool version mismatch | Install client tools no older than source; use a compatible destination version |

On Oracle, run diagnostics from `/home/ubuntu/clonescope-model/backend/deploy`:

```bash
sudo docker compose -f compose.oracle.yml ps
sudo docker compose -f compose.oracle.yml logs --tail=100 model
sudo docker compose -f compose.oracle.yml logs --tail=100 https
sudo docker stats --no-stream
df -h /
```

Do not publish `.env` or expanded `docker compose config` output: it contains the
key. `config --quiet` validates without printing those values.

## 15. Keep it running within the free tiers

- Export Neon regularly with `pg_dump` and keep a copy outside the hosting
  account. Your database stores uploaded code, so monitor storage usage.
- Keep the VM's source, Compose configuration, secret and DNS details recoverable
  separately. Model and certificate caches persist in Docker volumes. Do not use
  `docker compose down -v` during routine updates because it removes volumes.
- Apply OS/container updates during a planned window; verify health and a test
  analysis afterwards. Never redeploy while expecting an in-process job to survive.
- Oracle Always Free differs from temporary trial credit and has no free-tier
  uptime SLA. Idle VMs can be reclaimed. Do not generate artificial load to avoid
  resource policies. [Oracle FAQ](https://www.oracle.com/cloud/free/faq/).
- Render Free sleeps after inactivity and has monthly usage and outbound-traffic
  limits. Remote inference and external database access use outbound traffic.
  Free hosting is suitable for a modest demo, not a promise of continuous service.
  [Render Free limits](https://render.com/docs/free).

The setup is complete when accounts/results are stored in Neon, Oracle's
authenticated inference works, the frontend uses the correct backend URL, and a
new analysis passes step 13 with semantic comparisons actually performed.
