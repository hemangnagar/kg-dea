# API pilot status

Prepared: 2026-11-04.

- World: schema-v2 draft seed, independently expanded under `world/pilot`.
- Manifest: `corpus/api-pilot/manifest.sqlite`; 5,000 planned, zero API-generated/validated.
- Fixed eligible subset: original record numbers 1–50. Resumption cannot drift to the next 50.
- Mix: DEA 30, FBI 5, HSI 1, CBP 2, DIA 2, Treasury 3, OSINT 7; Secret 33 / U 17; core 38 / background 12.
- Model: `gpt-4.1-mini`; four stages per document (draft, critique, revise, extract).
- Local estimated-spend cap: $5. Prices are from OpenAI's published April-2025 guide; reconfirm current provider pricing.
- Attempted command: `bash scripts/pilot50.sh`.
- Result: stopped before network I/O because `INTELDOC_OPENAI_API_KEY` / `OPENAI_API_KEY` is not configured.
- Live API requests: zero. No pilot XML has been produced or represented as generated.

Add the key securely in environment settings for `api.openai.com`, apply the settings, and rerun the same command. Keep the key out of Git and chat. Review and publish environment configuration if the UI requires it. Existing validated stages will resume; failed records are retried explicitly by the script.

See README.md for the seed contents, validation constraints, model-price reference, and matching corpus/world startup configuration.

## Recovery for the new task

The original workspace retained the state. A SHA-256 indexed recovery snapshot now ships in `artifacts/pilot-recovery-2026-11-05.tar.gz`, together with the standard-library restore command `python3 scripts/restore_pilot.py`. The snapshot was tested by restoring all 10,008 files, verifying both databases, checking a repeat restore, and rejecting a conflicting local file. Its historical spend ledger records zero API requests and $0 spend.

The new task reports that KEY2 is present but API network access and `.venv` are missing. Restore the archive, create `.venv`, install `requirements.lock`, then resume `bash scripts/pilot50.sh` after its API allowlist change is applied. See README.md for exact commands. The snapshot contains no credentials, and the original live task's absent-key observations do not describe the new task's credentials.
