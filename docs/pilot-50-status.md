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
