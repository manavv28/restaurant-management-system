#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
npm --cache "${TMPDIR:-/tmp}/biteai-npm-cache" --prefix frontend ci
npm --prefix frontend run build
PYTHONPATH=backend .venv/bin/pytest backend/tests -q
