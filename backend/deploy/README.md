# Type-4 on Render Free with an Oracle Always Free model server

For the current free laptop setup, use [LAPTOP-SETUP.md](LAPTOP-SETUP.md).
It runs the same model locally and connects Render through an authenticated
Cloudflare Quick Tunnel, without an Oracle VM.

For the complete sequence including a fresh Neon database before October 16, Oracle
signup, free DNS, Windows commands, frontend deployment and acceptance checks,
start with [the complete Neon + Oracle + Render guide](COMPLETE-SETUP.md).

The existing frontend and Render API remain in place. Render performs structural
comparisons and sends code fragments over authenticated HTTPS to GraphCodeBERT on
Oracle. Source fragments leave Render for your Oracle server during analysis;
the model service does not save them. No database or Redis is needed on Oracle.

The base model produces semantic candidates, not proof of equivalent behavior.
These changes do not train the model or change the detection thresholds.

## 1. Create the Oracle VM

Create an [Oracle Free Tier account](https://www.oracle.com/cloud/free/).
In your home region, open **Compute → Instances → Create instance** and choose:

- Ubuntu 22.04 or 24.04, ARM image.
- Shape **VM.Standard.A1.Flex**, **2 OCPUs**, **12 GB RAM**.
- A 50 GB boot volume, within your total Always Free storage allocation.
- A public subnet with a public IPv4 address and an internet gateway route.
- Save the SSH private key locally; never put it in Git or send its contents in chat.

As checked on September 30, 2026, Oracle documents a total Always Free allowance
of 2 A1 OCPUs and 12 GB RAM, shared across your A1 instances. Verify the console's
Always Free eligibility before creating resources. Signup requires card
verification. Capacity can be unavailable; try another availability domain in
your home region or retry later. Idle free instances can be reclaimed, so this
is not guaranteed always-on hosting. Do not select paid shapes to bypass capacity.

Source: [Oracle Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

Allow inbound TCP 22 from your own IP and TCP 80/443 for HTTPS in the VM's network
security list or network security group. The OS firewall must also permit these
ports. Keep the internal model port 8000 closed to the internet.

Point a domain/subdomain's DNS A record at the VM's public IP. Caddy will request
and renew its HTTPS certificate. A hostname you already control is sufficient;
if you have no domain, obtain a free DNS hostname before proceeding. The supplied
configuration requires a publicly resolvable hostname and reachable ports 80/443.

## 2. Copy and start the model service

Connect with SSH (Ubuntu images normally use `ubuntu`) and install Docker Engine
with the Compose plugin using the [official Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/).
Those instructions support ARM64. Use `sudo docker` if your account is not in the
Docker group.

Copy the updated backend files to the VM, preserving this structure:

```text
backend/
  config.py
  semantic_service.py
  graphcodebert/       # Python source, including parser/
  deploy/
    compose.oracle.yml
    Dockerfile.semantic
    requirements-semantic.txt
    Caddyfile
    .env.example
```

Use your updated repository checkout or transfer these files over SSH. An older
remote Git commit will not include uncommitted local changes. Do not copy your
application's backend/.env, databases, Python environments, or SSH keys.

On the VM:

```bash
cd backend/deploy
cp .env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
nano .env
```

Set `MODEL_DOMAIN` to your hostname (without `https://`) and `SEMANTIC_API_KEY`
to the generated value. Keep this value private; Render needs the same key.

```bash
chmod 600 .env
sudo docker compose -f compose.oracle.yml up -d --build
sudo docker compose -f compose.oracle.yml logs --tail=80 model
```

The initial startup downloads GraphCodeBERT and loads it before the service is
ready. Weights are retained in a Docker volume across restarts. A download failure
causes startup to fail visibly; inspect logs and retry after resolving it.

```bash
curl --fail https://YOUR_MODEL_HOSTNAME/health
```

Expect `{"status":"ready"}`. An authenticated `/info` request should return
`{"protocol":1,"mode":"embedding"}` with the base model. An unauthenticated
request to `/info`, `/embed`, or `/predict` must return HTTP 401.

The container uses one model process and one inference request at a time. A busy
server returns 503 rather than running extra copies. Fine-tuned classification
is also supported; to use it, mount a compatible trusted checkpoint read-only at
`/app/saved_models/model.bin` and restart. It is not required for base inference.

## 3. Connect Render

Deploy the updated application code to Render first. In the backend service's
Environment settings, configure:

```dotenv
DETECTION_ENGINE=remote
SEMANTIC_API_URL=https://YOUR_MODEL_HOSTNAME
SEMANTIC_API_KEY=THE_SAME_KEY_AS_ON_ORACLE
SEMANTIC_API_TIMEOUT=180
```

Choose **Save and deploy**. If detection runs in a separate Celery worker, deploy
the changes and set these variables there too. Keep the key out of frontend
environment variables. No frontend URL change is needed. Remote mode overrides
the Docker image's default lightweight setting and does not load torch on Render.

Upload files again to start a **new analysis**. Existing saved jobs will not
change. The results should report base-model semantic analysis with comparisons
performed, instead of “Type-4 was NOT checked.” A successful analysis can still
contain no Type-4 matches when no pair meets the similarity threshold.

Remote failures stop the job with a clear error; there is no silent structural
fallback. HTTP 401 means mismatched keys; 503 can mean a busy, starting, or failed
model; timeouts require checking DNS, firewalls, certificates and server logs.
`/health` on Render alone does not verify model readiness.

## Validation

From `backend`, using the project's Python 3.11 environment:

```powershell
.\.venv311\Scripts\python.exe -m unittest test_remote_semantics test_folder_detection -q
```

The protocol tests use a test model to verify authentication, batching, Type-4
pipeline integration and error handling. They do not measure model accuracy or
verify a live Oracle deployment. Cloud deployment requires the VM, DNS and keys
above, and an ARM image build must be verified on that host.

To additionally check the full service/client path using real cached weights:

```powershell
$env:RUN_MODEL_TESTS='1'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.\.venv311\Scripts\python.exe -m unittest test_remote_semantics.RealRemoteModelTests -v
```

This small fixture checks recursive/iterative factorial and Python/Java quicksort
as semantic candidates, a renamed Type-2 pair, and an unrelated negative. It
passed locally with the cached base model; it is not an accuracy benchmark.
