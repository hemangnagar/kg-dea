# IntelDoc API pilot: exactly 50 documents

Completed 2026-11-05: **50 validated documents, zero failed documents**, covering exactly the original record numbers 1–50. The remaining 4,950 manifest records are planned and were not attempted. The original world and fixed selection are unchanged; the earlier 39 successful documents were preserved.

- [Readable documents](text/), [XML documents](xml/), and [matching JSON records](truth/) — 50 documents in each representation.
- [Authored world bible](../../world/seed.yaml), [expanded pilot world](world/pilot/expanded.json), and [world relationships](world/pilot/graph_truth.json).
- [Validation report](run-report.json), [scorecard](scorecard.json), [fixed selection](selection.json), and [spend ledger](spend-ledger.json).
- [Download complete results ZIP](../pilot-50-results.zip), including the pilot manifest and model-stage checkpoints.

## Validation and spend

All 50 stored XML files match the typed JSON records and passed well-formedness, internal narrative, grounding and marking checks. All **248 extracted fact citations** match exact source paragraphs and world facts. The **231 unique extracted facts** match all planted facts in the successful documents: 100% constrained precision and planted recall. This measures the demonstration's constrained anchor grammar, not unrestricted extraction quality.

Official XSD/Schematron conformance remains unverified: the schema package is not bundled.

Total accounted API spend: **$0.3259604**, consisting of **$0.3138092 settled usage** and **$0.0121512 retained reservations** from two earlier failed requests. The total includes the retries that completed the final 11 documents. The original **$5 cap** remains unchanged. This is the local token-price ledger, not a provider billing statement.

## Synthetic telephone identifiers and CDR

The expanded world contains **180 non-dialable telephone labels** (`DEMO-TEL-00001`, for example) and **180 account labels**. The prose contains person-to-identifier `uses` relationships. These labels are synthetic placeholders, not dialable phone numbers. There is **no call detail record dataset**: no caller/callee pairs, call timestamps, durations, IMEI/IMSI or cell-site records are generated.

## Resume and checks

Retries reused saved stages and preserved the 39 previously validated records. The critique output allowance is 2,400 tokens. Prompts now make explicit that metadata/portion marks are rendered separately and that mandatory grounding constraints override mistaken model critique. One misleading cached critique was preserved as `critique_before_constraint_fix` and regenerated; grounding checks were not relaxed.

Fourteen model/provider tests passed; the two query tests were excluded after the earlier TestClient run stalled. The audit is preserved in `audit-run.py`; from the repository root run `PYTHONPATH=. .venv/bin/python artifacts/pilot-50/audit-run.py` against the live corpus.

These are fictional demonstration records; portion marks describe synthetic content. The older recovery archive is a pre-generation snapshot: never restore it over the paid run ledger.
