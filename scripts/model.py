#!/usr/bin/env python3
"""Download/check the configured model, using installed or project-local Ollama."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


def main():
    python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if python.exists() and Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        return subprocess.call([str(python), __file__, *sys.argv[1:]])
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pull", action="store_true", help="Download the configured model (about 1.9 GB for qwen2.5:3b)")
    args = parser.parse_args()
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    portable = ROOT / ".local/ollama/ollama"
    binary = str(portable) if portable.exists() else shutil.which("ollama")
    process = None
    log = None
    env = dict(os.environ, OLLAMA_HOST=url, OLLAMA_NO_CLOUD="1")
    if binary == str(portable):
        env.setdefault("OLLAMA_MODELS", str(ROOT / ".local/models"))

    def models():
        with urlopen(url + "/api/tags", timeout=2) as response:
            return [item["name"] for item in json.load(response).get("models", [])]

    try:
        try:
            names = models()
        except Exception:
            if not binary or urlparse(url).hostname not in ("localhost", "127.0.0.1"):
                raise SystemExit("Install Ollama from https://ollama.com/download and start it, then rerun this command.")
            (ROOT / ".local/logs").mkdir(parents=True, exist_ok=True)
            log = open(ROOT / ".local/logs/model-setup.log", "a")
            process = subprocess.Popen([binary, "serve"], env=env, stdout=log, stderr=log)
            for _ in range(40):
                try:
                    names = models()
                    break
                except Exception:
                    if process.poll() is not None:
                        raise SystemExit("Ollama could not start. Read .local/logs/model-setup.log")
                    time.sleep(0.5)
            else:
                raise SystemExit("Ollama did not become ready. Read .local/logs/model-setup.log")
        if model in names:
            print(f"Ready: {model} is installed. Start SkillScout to use it.")
        elif args.pull:
            if not binary:
                raise SystemExit("Install the Ollama CLI from https://ollama.com/download first.")
            subprocess.run([binary, "pull", model], env=env, check=True)
            print(f"Ready: {model} is installed.")
        else:
            print(f"{model} is not installed. Run this script with --pull to download it.")
            return 1
    finally:
        if process:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        if log:
            log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
