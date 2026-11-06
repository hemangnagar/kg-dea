# Claude Haiku 5.5 full corpus: 5,000 cables

Completed 2026-11-06 against the hand-authored world (`world/seed.yaml`, schema 3, seed 42) with `config/anthropic-haiku.yaml`.

- **5,000 validated cables**: 4,949 rendered and extracted by Claude Haiku 5.5 (draft, critique, revise, extract; structured JSON output; thinking off at low effort; two hand-written exemplars of the same agency in a cached system prompt) and 51 hand-written under `exemplars/narratives/`.
- Every cable passed the same deterministic checker as the offline baseline. Model extraction kept only claims whose quote and relation the anchor grammar confirms; 173 claims were dropped and are counted in the scorecard.
- Accounted spend: **$12.17** for 20,411 requests (58.2M input tokens, 12.7M output tokens at $0.10 / $0.50 per million), including the 20-cable pilot, probes and every retry. The $40 cap was never approached. This is the local ledger, not a provider bill.
- Wall clock: about 2.5 hours at eight concurrent workers, including retries.
- Scorecard: planted recall 0.999, world recall 0.971, precision 1.0 excluding the 178 deliberately planted contradiction edges. See [scorecard.json](scorecard.json) and [run-report.json](run-report.json).

The archive [`../haiku-5000-results.zip`](../haiku-5000-results.zip) (SHA-256 in the sidecar) holds `xml/` (5,000 PUBS-style documents), `truth/` (the typed records with planted facts, marks, quantities, disputes and corrections), `scorecard.json`, this run report, and a manifest without the model stage checkpoints. To serve it:

```sh
mkdir -p corpus/haiku && unzip -q artifacts/haiku-5000-results.zip -d corpus/haiku
INTELDOC_CORPUS_DIR=corpus/haiku INTELDOC_MODEL_CONFIG=config/anthropic-haiku.yaml bash scripts/start.sh
```

The world must be the committed seed expanded with seed 42 (`scripts/setup.sh` or `python -m scripts.demo world` does this); the manifest records the world hash and refuses a different one. Query answers stay offline in that configuration; the persona switch, citations, graph and timeline all run against this corpus.

These are fictional demonstration records. Portion marks describe synthetic content. Official XSD/Schematron conformance is unverified because no schema package is bundled.
