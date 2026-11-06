#!/usr/bin/env bash
# One-time setup: dependencies, the expanded world, and the demo corpus.
# The demo corpus is the published Claude Haiku run (artifacts/haiku-5000-results.zip) when present;
# otherwise the offline template corpus is built locally. Set INTELDOC_BUILD_OFFLINE=1 to force the latter.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m scripts.demo world --seed 42
if [[ -f corpus/manifest.sqlite ]]; then
  echo "corpus/manifest.sqlite exists; keeping the existing corpus. Move corpus/ aside to rebuild." >&2
elif [[ -f artifacts/haiku-5000-results.zip && "${INTELDOC_BUILD_OFFLINE:-0}" != "1" ]]; then
  sha256sum -c artifacts/haiku-5000-results.zip.sha256
  mkdir -p corpus && unzip -q artifacts/haiku-5000-results.zip -d corpus
  echo "Installed the published Haiku corpus: 5,000 cables under corpus/." >&2
else
  .venv/bin/python -m scripts.demo build --count 5000 --retry-failed
fi
