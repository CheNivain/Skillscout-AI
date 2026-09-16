#!/usr/bin/env python3
"""Install the project into its own virtual environment; safe to run again."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.version_info < (3, 12):
        raise SystemExit("Python 3.12 or newer is required.")
    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("Install Node.js 22.12+ (including npm), then run setup again.")
    os.chdir(ROOT)
    python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(ROOT / ".venv")
    subprocess.run([str(python), "-m", "pip", "install", "-r", "requirements-dev.txt"], check=True)
    subprocess.run([npm, "ci"], cwd=ROOT / "frontend", check=True)
    if not (ROOT / ".env").exists():
        shutil.copyfile(ROOT / ".env.example", ROOT / ".env")
    print("\nSetup complete. Run: python3 scripts/dev.py")
    print("For actual LLM inference: python3 scripts/model.py --pull")
    print("Or in VS Code: Terminal > Run Task > SkillScout: start")


if __name__ == "__main__":
    main()
