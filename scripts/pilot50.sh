#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then
  echo 'Run bash scripts/setup.sh first.' >&2
  exit 1
fi
.venv/bin/python -m scripts.validate_seed
if [[ ! -f world/pilot/expanded.json ]]; then
  .venv/bin/python -m scripts.demo world --world-dir world/pilot
fi
.venv/bin/python -m scripts.demo build --config config/pilot-50.yaml --world-dir world/pilot --output-dir corpus/api-pilot --count 5000 --retry-failed
