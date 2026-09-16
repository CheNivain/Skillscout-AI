.PHONY: setup dev build start test evaluate smoke
PYTHON = .venv/bin/python

setup:
	python3 scripts/setup.py

dev:
	$(PYTHON) scripts/dev.py

build:
	cd frontend && npm run build

start: build
	$(PYTHON) scripts/dev.py --production

test:
	$(PYTHON) -m pytest

evaluate:
	$(PYTHON) -m backend.evaluation

smoke:
	$(PYTHON) scripts/smoke.py
