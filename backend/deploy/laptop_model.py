"""Run the authenticated model and a temporary HTTPS tunnel on a Windows laptop.

Uses the existing Python 3.11 environment; no database, Docker or Oracle needed.
Runtime files (including the shared secret) are excluded from Git and Docker.
"""
import argparse
import contextlib
import http.client
import json
import os
from pathlib import Path
import re
import secrets
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

BACKEND = Path(__file__).resolve().parents[1]
RUNTIME = Path(__file__).resolve().parent / ".laptop-model"
PORT = 8765
LOCAL_URL = f"http://127.0.0.1:{PORT}"


def write_private(path, text):
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)


def api(url, path, key=None, payload=None, timeout=5):
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    request = urllib.request.Request(url + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.URLError as exc:
        parsed = urlsplit(url)
        if (not isinstance(exc.reason, socket.gaierror) or parsed.scheme != "https"
                or not parsed.hostname.endswith(".trycloudflare.com")):
            raise
        # Some ISP DNS servers cache NXDOMAIN for a new Quick Tunnel. Resolve only
        # our tunnel via HTTPS; keep the original hostname for Host/SNI and TLS checks.
        return tunnel_api_with_public_dns(parsed.hostname, path, headers, data, timeout)


def tunnel_api_with_public_dns(host, path, headers, data, timeout):
    with urllib.request.urlopen(
            "https://dns.google/resolve?name=" + host + "&type=A", timeout=timeout) as response:
        answers = json.load(response).get("Answer", [])
    addresses = [record["data"] for record in answers if record.get("type") == 1]
    if not addresses:
        raise OSError("The tunnel hostname is not available in public DNS yet")

    class ResolvedHTTPSConnection(http.client.HTTPSConnection):
        def connect(self):
            raw = socket.create_connection((addresses[0], self.port), self.timeout)
            try:
                self.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=self.host)
            except Exception:
                raw.close()
                raise

    connection = ResolvedHTTPSConnection(host, timeout=timeout)
    try:
        connection.request("POST" if data is not None else "GET", path, body=data, headers=headers)
        response = connection.getresponse()
        if response.status >= 400:
            raise urllib.error.HTTPError("https://" + host + path, response.status,
                                         response.reason, response.headers, None)
        return json.loads(response.read())
    finally:
        connection.close()


def verify_model(url, key):
    info = api(url, "/info", key, timeout=15)
    if info.get("protocol") != 1 or info.get("mode") not in {"embedding", "classifier"}:
        raise RuntimeError("The endpoint is not a compatible semantic model")
    try:
        api(url, "/info", timeout=15)
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            raise
    else:
        raise RuntimeError("The endpoint did not reject an unauthenticated request")
    return info


def model_environment(key):
    env = os.environ.copy()
    env.update(DETECTION_ENGINE="full", SEMANTIC_API_KEY=key,
               BATCH_SIZE="1", USE_GPU="false", CUDA_VISIBLE_DEVICES="",
               OMP_NUM_THREADS="2", MKL_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2",
               TOKENIZERS_PARALLELISM="false", PYTHONUNBUFFERED="1",
               PYTHONUTF8="1")
    return env


@contextlib.contextmanager
def session_lock():
    """OS-held lock releases on crashes; never kill processes by stale PID."""
    with (RUNTIME / "session.lock").open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError("A laptop model session is already running") from None
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def is_running():
    try:
        with session_lock():
            return False
    except RuntimeError:
        return True


def state(phase, **extra):
    data = {"phase": phase, "updated": time.strftime("%Y-%m-%d %H:%M:%S"), **extra}
    temporary = RUNTIME / "status.tmp"
    temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temporary.replace(RUNTIME / "status.json")
    print(phase, flush=True)


def check_children(children):
    if (RUNTIME / "stop").exists():
        raise InterruptedError("Stop requested")
    for name, process in children:
        if process.poll() is not None:
            raise RuntimeError(f"{name} exited ({process.returncode}); check {name}.log")


def wait_until(check, children, seconds, description):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        check_children(children)
        try:
            result = check()
            if result:
                return result
        except (OSError, ValueError):
            pass  # DNS, TLS and model startup can take time; deadline remains bounded.
        time.sleep(2)
    raise RuntimeError(f"Timed out waiting for {description}; inspect the runtime logs")


def render_settings(url, key):
    return (f"DETECTION_ENGINE=remote\nSEMANTIC_API_URL={url}\n"
            f"SEMANTIC_API_KEY={key}\nSEMANTIC_API_TIMEOUT=180\n")


def serve():
    with session_lock():
        (RUNTIME / "stop").unlink(missing_ok=True)
        (RUNTIME / "render.env").unlink(missing_ok=True)
        children = []
        with contextlib.ExitStack() as stack:
            try:
                state("starting")
                executable = RUNTIME / "cloudflared.exe"
                if not executable.exists():
                    raise RuntimeError("Run Install-LaptopTunnel.ps1 first")
                # Do not accidentally expose another service already listening here.
                with socket.socket() as probe:
                    probe.bind(("127.0.0.1", PORT))
                key_file = RUNTIME / "model-key.txt"
                if not key_file.exists():
                    write_private(key_file, secrets.token_urlsafe(48))
                key = key_file.read_text(encoding="utf-8").strip()
                if len(key) < 32:
                    raise RuntimeError("model-key.txt must contain at least 32 characters")
                flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

                def launch(name, command, env=None):
                    log = stack.enter_context((RUNTIME / f"{name}.log").open("w", encoding="utf-8"))
                    process = subprocess.Popen(command, cwd=BACKEND, env=env,
                                               stdin=subprocess.DEVNULL, stdout=log,
                                               stderr=subprocess.STDOUT, creationflags=flags)
                    children.append((name, process))

                launch("model", [sys.executable, "-m", "uvicorn", "semantic_service:app",
                                 "--host", "127.0.0.1", "--port", str(PORT),
                                 "--workers", "1", "--no-access-log"], model_environment(key))
                state("loading model")
                wait_until(lambda: api(LOCAL_URL, "/health").get("status") == "ready",
                           children, 600, "GraphCodeBERT to load")
                verify_model(LOCAL_URL, key)
                state("starting tunnel")
                # Explicit empty config avoids consuming an unrelated named-tunnel config.
                config = RUNTIME / "tunnel.yml"
                config.write_text("{}\n", encoding="utf-8")
                launch("tunnel", [str(executable), "tunnel", "--config", str(config),
                                  "--no-autoupdate", "--protocol", "http2",
                                  "--url", LOCAL_URL])

                def tunnel_url():
                    text = (RUNTIME / "tunnel.log").read_text(encoding="utf-8", errors="replace")
                    match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", text)
                    return match.group(0) if match else None

                url = wait_until(tunnel_url, children, 120, "a tunnel URL")
                state("checking public endpoint", url=url)
                wait_until(lambda: api(url, "/health").get("status") == "ready",
                           children, 180, "public HTTPS connectivity")
                info = verify_model(url, key)
                answer = api(url, "/embed", key,
                             {"fragments": [{"code": "print(1 + 1)", "language": "python"}]},
                             timeout=120)
                if len(answer.get("vectors", [[]])[0]) != 768:
                    raise RuntimeError("The public model did not return a 768-dimensional embedding")
                write_private(RUNTIME / "render.env", render_settings(url, key))
                state("ready", url=url, mode=info["mode"],
                      render_settings=str(RUNTIME / "render.env"))
                while True:
                    check_children(children)
                    time.sleep(1)
            except (InterruptedError, KeyboardInterrupt):
                state("stopped")
            except Exception as exc:
                state("failed", error=str(exc))
                raise
            finally:
                for _, process in reversed(children):
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=10)
                # A stopped tunnel URL is not a usable Render configuration.
                (RUNTIME / "render.env").unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["start", "serve", "status", "stop"])
    command = parser.parse_args().command
    RUNTIME.mkdir(exist_ok=True)
    if command == "serve":
        serve()
    elif command == "start":
        if is_running():
            print("Already running. Use the status command.")
            return
        flags = (subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
                 if os.name == "nt" else 0)
        with (RUNTIME / "launcher.log").open("w", encoding="utf-8") as log:
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "serve"],
                             stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                             creationflags=flags, start_new_session=os.name != "nt")
        print("Starting in the background. Check status in about a minute.")
        print("Keep this laptop awake and connected during analyses.")
    elif command == "stop":
        if is_running():
            (RUNTIME / "stop").touch()
            print("Stop requested. The model and tunnel will close after any startup probe finishes.")
        else:
            print("No laptop model session is running.")
    else:
        running = is_running()
        print(f"Launcher running: {running}")
        status_file = RUNTIME / "status.json"
        if status_file.exists():
            print(status_file.read_text(encoding="utf-8"))
        if not running:
            print("Any previous URL is offline. Run start to create a new session.")


if __name__ == "__main__":
    main()
