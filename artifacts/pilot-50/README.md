# IntelDoc API pilot results

Run completed 2026-11-05 against the original fixed document numbers 1–50.

- **39 successful documents; 11 rejected outputs.** The other 4,950 records remain planned.
- [Readable documents](text/), [XML documents](xml/), and [matching JSON records](truth/).
- [Authored world bible](../../world/seed.yaml), [pilot expanded world](world/pilot/expanded.json), and [world relationships](world/pilot/graph_truth.json).
- [Validation and failures](run-report.json), [scorecard](scorecard.json), [fixed selection](selection.json), and [spend ledger](spend-ledger.json).
- [Download the complete results ZIP](../pilot-50-results.zip). The ZIP also preserves the pilot manifest and paid-stage checkpoints.

Accounted API spend is **$0.2766388**: $0.2644876 settled usage plus $0.0121512 retained reservations from two earlier failed requests. The $5 cap was preserved, and no document beyond number 50 was attempted. These are local token-price calculations, not a provider billing statement.

All 39 stored XML files matched their typed records and passed well-formedness and internal narrative/marking checks. All 192 extracted fact citations matched exact source paragraphs and the planted/world facts (180 unique facts; 100% constrained precision and planted recall). No official XSD/Schematron package is bundled, so official schema conformance is unverified. The 11 rejected outputs failed narrative grounding, proper-name, or strict JSON checks; none is presented as a successful document.

The pilot critique allowance was increased from 900 to 2,400 tokens after an accounted incomplete response. The cap and fixed subset were unchanged. Fourteen relevant mocked model/provider tests passed; two query tests were excluded after the TestClient run stalled. The run audit is included as `audit-run.py` for reference; run it from the repository root against the live restored corpus using `PYTHONPATH=. .venv/bin/python artifacts/pilot-50/audit-run.py`.

These are fictional demonstration records. Portion marks describe synthetic content.
The earlier recovery archive is a pre-generation snapshot; do not restore it over this run's paid ledger. Keep the paid ledger when resuming.
