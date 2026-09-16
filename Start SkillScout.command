#!/bin/zsh
cd "$(dirname "$0")" || exit 1
if [[ ! -x .venv/bin/python ]]; then
  print "Please run make setup first. See README.md."
  read "?Press Enter to close."
  exit 1
fi
.venv/bin/python scripts/dev.py
read "?Press Enter to close."
