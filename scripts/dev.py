#!/usr/bin/env python3
"""Start SkillScout's gateway, four HTTP agents, frontend, and local Ollama.

Only child processes created by this command are stopped on exit. Existing
Ollama servers are reused. No model is silently downloaded by this launcher.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def healthy(url: str) -> bool:
    try:
        with urlopen(url, timeout=1) as response:
            return response.status == 200
    except Exception:
        return False


def port_available(port: int) -> bool:
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def main() -> int:
    venv_python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if venv_python.exists() and Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        return subprocess.call([str(venv_python), __file__, *sys.argv[1:]])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production", action="store_true", help="Serve built UI on :8000 (no Vite)")
    parser.add_argument("--no-ollama", action="store_true", help="Do not start a model server automatically")
    args = parser.parse_args()
    os.chdir(ROOT)
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        import uvicorn  # noqa: F401 — fail early with actionable setup instruction
    except ImportError:
        print("Missing Python packages. Run: .venv/bin/python -m pip install -r requirements-dev.txt", file=sys.stderr)
        return 1

    if args.production and not (ROOT / "frontend/dist/index.html").exists():
        print("Build the UI first: cd frontend && npm run build", file=sys.stderr)
        return 1
    if not args.production and not (ROOT / "frontend/node_modules/vite").exists():
        print("Install the frontend first: cd frontend && npm ci", file=sys.stderr)
        return 1
    for port in [8000, 8101, 8102, 8103, 8104] + ([] if args.production else [5173]):
        if not port_available(port):
            print(f"Port {port} is already in use. Stop the existing SkillScout process or free that port.", file=sys.stderr)
            return 1

    local = ROOT / ".local"
    logs = local / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    key_file = local / "agent.key"
    if not key_file.exists():
        fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as file:
            file.write(secrets.token_urlsafe(48))
    env = dict(os.environ)
    env.setdefault("SKILLSCOUT_AGENT_KEY", key_file.read_text().strip())
    env.setdefault("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    env.setdefault("OLLAMA_MODEL", "qwen2.5:3b")
    env.setdefault("PYTHONUNBUFFERED", "1")
    children: list[tuple[str, subprocess.Popen, object]] = []
    stopping = False

    def cleanup(*_):
        nonlocal stopping
        if stopping:
            return
        stopping = True
        print("\nStopping SkillScout services…", flush=True)
        for _, child, _ in reversed(children):
            if child.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"], capture_output=True)
                else:
                    try:
                        os.killpg(child.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
        deadline = time.monotonic() + 8
        for _, child, log in reversed(children):
            try:
                child.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                if os.name != "nt":
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    child.kill()
            log.close()

    def start(name: str, command: list[str], child_env=None, cwd=ROOT):
        log = open(logs / f"{name}.log", "a", buffering=1)
        log.write(f"\n--- start {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        child = subprocess.Popen(command, cwd=cwd, env=child_env or env, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=os.name != "nt")
        children.append((name, child, log))
        return child

    def await_ready(name: str, url: str, child: subprocess.Popen, timeout=35):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not stopping:
            if healthy(url):
                print(f"  ✓ {name}", flush=True)
                return
            if child.poll() is not None:
                raise RuntimeError(f"{name} stopped; inspect .local/logs/{name}.log")
            time.sleep(0.3)
        raise RuntimeError(f"{name} did not become ready; inspect .local/logs/{name}.log")

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    try:
        print("\n  SkillScout AI · starting your learning workspace\n", flush=True)
        model_url = env["OLLAMA_BASE_URL"].rstrip("/")
        if not args.no_ollama and not healthy(model_url + "/api/tags"):
            portable = ROOT / ".local/ollama/ollama"
            binary = str(portable) if portable.is_file() else shutil.which("ollama")
            parsed = urlparse(model_url)
            if binary and parsed.hostname in ("127.0.0.1", "localhost"):
                ollama_env = dict(env)
                ollama_env["OLLAMA_HOST"] = f"127.0.0.1:{parsed.port or 11434}"
                ollama_env["OLLAMA_NO_CLOUD"] = "1"
                ollama_env.setdefault("OLLAMA_NUM_PARALLEL", "1")
                if binary == str(portable):
                    ollama_env.setdefault("OLLAMA_MODELS", str(local / "models"))
                model_process = start("ollama", [binary, "serve"], ollama_env)
                await_ready("ollama", model_url + "/api/tags", model_process)
            else:
                print("  · Ollama is not running. Core search/scoring will use the clearly labelled fallback.", flush=True)
        if healthy(model_url + "/api/tags"):
            with urlopen(model_url + "/api/tags", timeout=2) as response:
                names = [m["name"] for m in json.load(response).get("models", [])]
            if env["OLLAMA_MODEL"] not in names:
                print("  · Download the model before an LLM demo: python3 scripts/model.py --pull", flush=True)
        for kind, port in [("profile", 8101), ("trends", 8102), ("retrieval", 8103), ("recommendations", 8104)]:
            child_env = dict(env, AGENT_KIND=kind)
            child = start(kind, [sys.executable, "-m", "uvicorn", "backend.worker:app", "--host", "127.0.0.1", "--port", str(port), "--no-access-log"], child_env)
            await_ready(kind, f"http://127.0.0.1:{port}/health", child)
        child = start("gateway", [sys.executable, "-m", "uvicorn", "backend.api:app", "--host", "127.0.0.1", "--port", "8000", "--no-access-log"])
        await_ready("gateway", "http://127.0.0.1:8000/api/health", child)
        if not args.production:
            npm = shutil.which("npm")
            if not npm:
                raise RuntimeError("npm is required. Install Node.js 22.12+ or 24+")
            child = start("frontend", [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort"], cwd=ROOT / "frontend")
            await_ready("frontend", "http://127.0.0.1:5173", child)
        url = "http://127.0.0.1:8000" if args.production else "http://127.0.0.1:5173"
        print(f"\n  Open {url}\n  Demo: alex@skillscout.demo / SkillScout123!\n  Logs: .local/logs/ · Ctrl+C stops all services started here.\n", flush=True)
        while not stopping:
            for name, child, _ in children:
                if child.poll() is not None:
                    raise RuntimeError(f"{name} exited ({child.returncode}); inspect .local/logs/{name}.log")
            time.sleep(0.5)
    except Exception as exc:
        print(f"\n{exc}", file=sys.stderr)
        cleanup()
        return 1
    finally:
        cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
