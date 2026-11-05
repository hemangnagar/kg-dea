# IntelDoc KG

A local evidence workbench built from the **IntelDoc KG Demo — Handoff Brief**. All actors and reporting are fictional. Real geography only. The default dataset is the **offline demo with a draft world seed**. OpenAI and Ollama are also wired into narrative generation, constrained relationship extraction, and source-grounded query answers. Offline mode spends no API money.

The original specification is included in [IntelDoc KG Demo — Handoff Brief](docs/IntelDoc-KG-Demo-Handoff-Brief.pdf).

## Run

Python 3.12+ is required. From this checkout:

```sh
bash scripts/setup.sh
bash scripts/start.sh
```

Setup installs exact dependency versions, expands the world if absent, plans 5,000 cables, generates XML and truth files, extracts relationships, and writes the measured scorecard. Generation takes a few minutes and resumes on rerun. The server binds to loopback port 8000 (override with `PORT`). Open the running app in a browser on the same machine. For a desktop-style window on a machine with a display, Chromium supports `chromium --app=http://127.0.0.1:8000`. This is a local web app, not a packaged native desktop application.

Use the existing checkout in cloud tasks. Tasks are already isolated; do not create a Git worktree unless explicitly requested.

## Demo sequence

1. Ask **Which companies connect to Bruma del Cobre?** The graph traverses organization → event → front company.
2. Click a bracketed citation to open the exact cable and highlighted paragraph. Click an entity to see its one-hop neighborhood; switch to Timeline.
3. Ask **Who led Bruma del Cobre in 2021?** Then switch from Secret // NOFORN to Unclassified // FOUO. The newer leadership relationship is withheld. The same question now has no supported answer. Changing persona clears the prior graph, answer, and document before fetching.
4. Open **Extraction scorecard**. Precision, whole-world recall, and planted-fact recall are computed from extracted text relationships, not hard-coded scores.
5. Open **World bible** to explain the fictional seed and limitations.

The query engine uses deterministic entity matching and at most two graph hops. It supports relationship, geography, leadership and year queries, not arbitrary natural-language reasoning. Ambiguous shared nicknames prompt disambiguation. Offline answers are evidence statements with citations. Online answers use the model to select relevant source quotations, then verify each quotation and cited relation deterministically.

## Restore the original state in a new task

The generated artifacts and `.venv` were ignored by Git. A new checkout therefore needs both the state snapshot and dependency installation before resuming. A verified recovery snapshot is now included at `artifacts/pilot-recovery-2026-11-05.tar.gz` with a SHA-256 sidecar. It contains only synthetic worlds/documents, both SQLite manifests, the selection, scorecard and spend ledger. It contains no API key, `.env`, or virtual environment.

From a clean checkout of the latest `origin/main`:

```sh
python3 scripts/restore_pilot.py
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
bash scripts/pilot50.sh
```

The restore command uses only Python's standard library, so it works before `.venv` exists. It verifies every archived file and database, restores the exact original state, and refuses to overwrite differing existing files. A repeated identical restore is safe. If it reports a conflict, preserve and inspect that existing state; do not delete a ledger to make the command pass.

Expected restored state: 5,000 validated **offline** cables, 5,000 planned pilot records, zero API-validated pilot records, and the original ledger recording **$0 historical API spend**. Restoring makes no API requests and does not expand the world or regenerate documents. The archive is a point-in-time snapshot from before live generation; never restore it over a later run's spend ledger.

The new task must separately have `INTELDOC_OPENAI_API_KEY2` (or a supported fallback) and allowed HTTPS access to `api.openai.com`. If its allowlist draft is pending, review/save/publish that change in environment settings and verify the task's actual network policy before the paid run. The snapshot cannot grant network access or inject credentials.

## 50-document API pilot

The detailed Claude-style seed requirements are now represented in `world/seed.yaml` (schema v2): five organizations with exact leadership windows, dated fractures/alliances, 25 corridor control histories, 50 people across all required tiers and official roles, 15 shared aliases including five inherited aliases, 18 companies with nominee ownership, 12 registered assets, 56 sources (eight per agency), and 35 dated timeline beats. It remains **draft-unreviewed**; automated integrity checks are not editorial approval or proof that every invented name is globally unique.

```sh
.venv/bin/python -m scripts.validate_seed
bash scripts/pilot50.sh
```

The pilot script plans all 5,000 records against a separate expanded world in `world/pilot`, then makes only original record numbers 1–50 eligible for generation. It uses `config/pilot-50.yaml`: OpenAI `gpt-4.1-mini`, a $5 local cap, 3-pass narratives plus model extraction. The configured $0.40 input / $1.60 output per million rates come from [OpenAI's published model-selection guide](https://github.com/openai/openai-cookbook/blob/main/examples/partners/model_selection_guide/model_selection_guide.ipynb), whose pricing table is dated April 2025. Reconfirm your account's current pricing before execution. The local accountant is not a provider billing limit.

Supply `INTELDOC_OPENAI_API_KEY2` (or `INTELDOC_OPENAI_API_KEY`) securely in environment settings, with HTTPS access to `api.openai.com`. There is no saved key binding or injected key in the current environment. **The first run was attempted and stopped before any API request.** Its manifest has 5,000 planned / zero API-validated records. No API-generated pilot documents are claimed yet.

The fixed selection contains DEA 30, FBI 5, HSI 1, CBP 2, DIA 2, Treasury 3, and OSINT 7 cables; 33 are Secret, 17 Unclassified, and 38 core / 12 background. Re-running the script resumes these same 50, not another 50. Output goes to `corpus/api-pilot`; the initial selection is recorded in `selection.json` there. Its XML/truth directories appear as successful records are validated. Remove or raise `max_cables` only when deliberately moving beyond the pilot.

The old offline dataset keeps its original expanded world at `world/expanded.json`. The v2 pilot uses `world/pilot/expanded.json`; never re-expand the baseline world under existing documents. Serve the API pilot with matching world and corpus profiles:

```sh
INTELDOC_WORLD_DIR=world/pilot INTELDOC_CORPUS_DIR=corpus/api-pilot INTELDOC_MODEL_CONFIG=config/pilot-50.yaml bash scripts/start.sh
```

Seed validation checks all references, leadership/control intervals, inherited-alias timing, required tiers, geography, source counts, and events after a participant's recorded arrest/death (except release events). Expansion selects eligible living/unconfined participants and preserves each agency source's stable reliability grade. These checks also run before the paid pilot. The planned sample is not a substitute for a live-generation quality review.

## Pipeline and files

```sh
.venv/bin/python -m scripts.demo world --seed 42 --world-dir world/pilot
.venv/bin/python -m scripts.demo plan --count 5000 --seed 42
.venv/bin/python -m scripts.demo generate
.venv/bin/python -m scripts.demo generate --retry-failed
.venv/bin/python -m scripts.demo evaluate
.venv/bin/python -m pytest -q
```

`world/seed.yaml` is the draft editorial input. Scripted expansion creates 200 people, 80 companies, 45 assets, 360 non-operational identifiers, 56 sources in v2 (50 in the preserved v1 baseline), 25 places, five organizations, 600 events and non-overlapping leadership windows. The v2 seed contains 35 exact-dated timeline beats; the preserved v1 baseline used 35 template arc beats. Shared nicknames are intentional. This is a mechanical synthetic baseline, not a hand-authored geopolitical simulation.

Generated outputs are ignored by Git and reproducible:

- `world/expanded.json`: full fictional world.
- `world/graph_truth.json`: world relationships, derived by code.
- `corpus/manifest.sqlite`: planned/drafted/critiqued/revised/validated/failed state, records, indexed evidence, per-stage model checkpoints, spend reservations and optional batch-job registry.
- `corpus/xml/NNNN-YYYYYY.xml`: deterministic PUBS-like XML.
- `corpus/truth/NNNN-YYYYYY.json`: per-cable facts and paragraph marks.
- `corpus/scorecard.json`: measured evaluation output.

The planner refuses a different count/seed against an existing manifest. Validated cables are never regenerated. Change the dataset deliberately by moving the generated corpus aside before rebuilding; never remove user data blindly. Stop a running generator before changing its code or world. Do not re-expand the world underneath an existing corpus. `--seed` on the planner seeds cable sampling; use the `world` command separately to change world expansion.

Every fact carries a cable and paragraph provenance. The baseline extractor parses narrative text independently and never reads the record's planted-fact list. Its vocabulary comes from the world. This is deliberately an easy baseline: high scores on templated prose do not imply accurate LLM extraction or real-world entity resolution. World recall and planted recall have separate denominators.

## XML and validation

XML is escaped through lxml; metadata is deterministic from the Pydantic record. Portion marks are assigned first. Root, DocumentBody and PreformattedText inherit maximum classification and the union of controls. Secret documents contain unmarked-control U paragraphs and S//NF details; U//FOUO is never mixed with S. OSINT is U. Secret declassification uses a 25-year calendar offset with leap-day handling.

The output includes the public namespaces, NTK profiles, publisher, identifiers, notices, coverage, sources, dissemination footer and the source feed's unusual CIA extension spellings. Official schema conformance is **not claimed**. Drop a trusted, self-contained schema package with entrypoint `schemas/pubs.xsd` and/or `schemas/pubs.sch` into the checkout to enable the validation hooks. The brief's uncertain DESVersion/COIProtectionLevel/policy-URI values remain as provided. No official schema was supplied or tested.

The checker rejects starter-blocklisted names, missing planted entities/dates, unknown capitalized multiword names, mismatched baseline relationships, numbering and length defects, and invalid portion marks. The blocklist is a small starter from public DEA/State organization names and publicly known officials; it is not exhaustive or proof that every invented name is unique. No real document text is used. IDs beginning DEMO-TEL/DEMO-ACCT are intentionally non-dialable/non-bank labels.

## Security model

**Only synthetic data belongs here.** The persona selector is a demonstration, not authentication. Both demo personas have the same agency NTK access; classification filtering happens before graph traversal and answering. Public cable responses omit secret paragraphs and withhold secret source/subject metadata; public requests for secret full XML fail. Entity/graph/timeline endpoints use only accessible evidence. No endpoint exposes local filesystem paths or arbitrary XML files.

A production deployment needs authenticated, server-assigned clearances, agency NTK enforcement, user/session authorization, audit logging, transport hardening and tested cache isolation. Do not expose this development server to untrusted networks or ingest real intelligence.

## Optional providers and spend

The default configuration is offline. For OpenAI, the corpus generator now calls the model for **draft → critique → revise → extract**, persists completed stages, runs deterministic validation, renders XML and indexes extracted evidence. Query answers use the configured model to choose relevant quotes from accessible evidence. Every answer quote is checked against its cited paragraph and relation before returning it. Invalid answers fail closed; there is no silent fallback from a broken online provider.

Narrative models must preserve canonical fact sentences inside otherwise model-authored prose. This lets the checker verify entities, dates, relationships and portion boundaries without trusting a second model's opinion. The extraction model receives narrative paragraphs and a text-derived entity vocabulary, **not planted-fact arrays**. It may omit facts (lowering measured recall), but unsupported claims are rejected. This is constrained model extraction, not unrestricted prose understanding. Query answers are extractive rather than freely paraphrased to keep their claims verifiable.

### Configure and run an online pilot

OpenAI uses the Responses API. ChatGPT subscriptions do not include API usage. Supply a separately billed API project's key securely as `INTELDOC_OPENAI_API_KEY2`, `INTELDOC_OPENAI_API_KEY`, or `OPENAI_API_KEY` (in that precedence order). The destination is `api.openai.com`. Do not commit keys or paste them into chat. No ChatGPT browser session credentials are used.

1. Copy `config/openai.example.yaml` to `corpus/openai.yaml`, which is ignored by Git.
2. Set `openai_model` to an available OpenAI API model ID and the two token prices to current published USD per million tokens. Keep `max_spend_usd` at or below your budget. Missing model, price or key fails before a request.
3. Start with a small pilot in a separate directory. Existing validated offline records are never overwritten or relabeled as model-generated:

```sh
.venv/bin/python -m scripts.demo build --config corpus/openai.yaml --output-dir corpus/pilot --count 5
```

A five-cable run makes up to 20 model calls. A retry with the same command preserves validated cables and completed draft/critique/revision/extraction stages. To retry failed records explicitly, add `--retry-failed`. A provider error or exhausted spend cap stops the run instead of attempting every remaining cable. The CLI returns nonzero on failed generation. Do not start with 5,000 paid cables before checking the pilot's spend and quality.

To use OpenAI for answers over the existing 5,000-cable baseline:

```sh
INTELDOC_MODEL_CONFIG=corpus/openai.yaml bash scripts/start.sh
```

To serve the model-generated pilot instead:

```sh
INTELDOC_MODEL_CONFIG=corpus/openai.yaml INTELDOC_CORPUS_DIR=corpus/pilot bash scripts/start.sh
```

The UI shows the query provider, verified model-selected answer quotes, and accounted spend. The scorecard reads generation/extraction method from the dataset manifest. Both demo personas still use the same agency NTK profiles; inaccessible paragraphs are filtered **before** constructing any query prompt. Empty or ambiguous retrieval makes no model request.

One-off requests remain available via `.venv/bin/python -m scripts.model_prompt --config corpus/openai.yaml --prompt-file /path/to/prompt.txt`. For a locally running Ollama service, use `provider: ollama`, `query_provider: ollama`, and `ollama_model` in the same configuration. No OpenAI key is needed for Ollama.

The accountant atomically reserves a conservative request bound before network I/O, records returned input and output usage (including billed reasoning output), and retains reservations after uncertain failures. All corpus directories share the baseline ledger at `corpus/manifest.sqlite`; switching to a pilot directory does not reset the spend cap. `MAX_SPEND_USD` overrides config `max_spend_usd`, defaulting to $40. This is a local ledger guard based on configured pricing, not a provider billing limit. Incomplete responses and refusals are accounted and reported as errors. No automatic retry or provider batch workflow is implemented. Responses use `store: false`; this does not guarantee provider-side zero retention.

No live OpenAI run has been validated in this environment: there is no configured API key. Tests exercise the full provider-backed pipeline through mocked HTTP Responses API replies, including failures, resume behavior, extraction omissions, persona isolation and invented citations. This distinction is intentional; simulated success is not a live model-quality measurement.

## Validation

`pytest` exercises the generation/resume path, XML roll-up, mutable narrative failures, budget enforcement, citation-to-paragraph fidelity, public/secret access, temporal queries and alias disambiguation using isolated temporary corpora.

For optional real-browser tests, install Playwright outside the checkout and use an installed Chromium:

```sh
npm install --prefix /tmp/kg-browser playwright@1.56.1
PLAYWRIGHT_MODULE=/tmp/kg-browser/node_modules/playwright node tests/browser.cjs
```

Start the server first. The script checks search, citation dialogs, persona switching, graph/timeline, scorecard, bible and mobile overflow. It writes a desktop screenshot to `/tmp/kg-dea-desktop.png`.

## Remaining brief work

The offline first version intentionally defers editorial seed approval, richer lifetime/membership/corridor semantics, alias usage in narrative prose, event quantities in extraction, 5% contradiction and 1–2% correction sampling, best-of LLM narrative selection, actual provider-batch resumption, unrestricted LLM extraction and QA grading, real NTK authorization, official schema confirmation and native desktop packaging. The model-backed draft/critique/revise pipeline, constrained extraction and quote-grounded query path are implemented; the deferred stages above are not. The UI, corpus and scorecard identify the baseline so it cannot be mistaken for completion of these phases.

The replacement variable `INTELDOC_OPENAI_API_KEY2` is supported and takes precedence over older key names. If a published variable is absent in this running task, reconnect/restart the task using the updated environment version; publishing another version does not prove an existing process received the variable. Keep HTTPS access to `api.openai.com` enabled. Do not create or paste duplicate keys to troubleshoot a stale runtime.
