#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
INTELDOC_CORPUS_DIR="$PWD/corpus" .venv/bin/python -m scripts.demo build --config config/corpus.yaml --count 5000 --retry-failed
