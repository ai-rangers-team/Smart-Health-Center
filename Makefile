# Smart Health — dev convenience targets.
# Uses the api/.venv binaries directly so it works even when the shell's default
# `python` points at anaconda rather than the project venv.
SHELL := /bin/bash
API   := api
WEB   := web
# Invoke tools as `python -m <tool>`: the venv's console-script wrappers (uvicorn,
# pip) have a broken shebang on this machine, but the python binary itself works.
PY    := $(API)/.venv/bin/python
PIP   := $(API)/.venv/bin/python -m pip

.PHONY: help install install-api install-web venv preview dev api web seed reset test build

help:
	@echo "Smart Health — dev commands:"
	@echo "  make install   Set up backend venv + deps and frontend deps (run once)"
	@echo "  make preview   Frontend only, canned fixtures — no backend or credentials → :5173"
	@echo "  make dev       Backend (:8000) + frontend (:5173) together; Ctrl-C stops both"
	@echo "  make api       Backend only (uvicorn --reload) → :8000"
	@echo "  make web       Frontend only, proxies /api to a running backend → :5173"
	@echo "  make seed      Seed the Pune Rural demo (needs api/.env + service account)"
	@echo "  make reset     Wipe + reseed the demo"
	@echo "  make test      Backend pytest"
	@echo "  make build     Production frontend build"
	@echo ""
	@echo "No backend credentials yet? Use 'make preview' — it demos all features offline:"
	@echo "  /?role=admin   /?role=operator   /p/phc_mulshi   /sms-demo"

venv:
	@test -d $(API)/.venv || python3 -m venv $(API)/.venv

install-api: venv
	$(PIP) install -q -r $(API)/requirements.txt

install-web:
	cd $(WEB) && npm install

install: install-api install-web

preview:
	cd $(WEB) && VITE_PREVIEW=1 npm run dev

api:
	cd $(API) && .venv/bin/python -m uvicorn app.main:app --reload

web:
	cd $(WEB) && npm run dev

# Run backend + frontend together. `trap 'kill 0'` tears down both on Ctrl-C.
dev:
	@echo "Backend → http://localhost:8000   Frontend → http://localhost:5173"
	@echo "(needs api/.env configured; otherwise use 'make preview'). Ctrl-C stops both."
	@trap 'kill 0' EXIT INT TERM; \
		( cd $(API) && .venv/bin/python -m uvicorn app.main:app --reload ) & \
		( cd $(WEB) && npm run dev ) & \
		wait

seed:
	cd $(API) && ../$(PY) -m scripts.seed

reset:
	cd $(API) && ../$(PY) -m scripts.seed --reset

test:
	cd $(API) && ../$(PY) -m pytest -q

build:
	cd $(WEB) && npm run build
