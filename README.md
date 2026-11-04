# IntelDoc KG

A local evidence workbench built from the **IntelDoc KG Demo — Handoff Brief**. All actors and reporting are fictional. Real geography only. This first version is the **offline demo with a draft world seed**, as requested. It spends no API money.

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

The query engine uses deterministic entity matching and at most two graph hops. It supports relationship, geography, leadership and year queries, not arbitrary natural-language reasoning. Ambiguous shared nicknames prompt disambiguation. Answers are evidence statements with citations, not LLM-written summaries.

## Pipeline and files

```sh
.venv/bin/python -m scripts.demo world --seed 42
.venv/bin/python -m scripts.demo plan --count 5000 --seed 42
.venv/bin/python -m scripts.demo generate
.venv/bin/python -m scripts.demo generate --retry-failed
.venv/bin/python -m scripts.demo evaluate
.venv/bin/python -m pytest -q
```

`world/seed.yaml` is the draft editorial input. Scripted expansion creates 200 people, 80 companies, 45 assets, 360 non-operational identifiers, 50 sources, 25 places, five organizations, 600 events and non-overlapping leadership windows. There are 35 seed arc beats. Shared nicknames are intentional. This is a mechanical synthetic baseline, not a hand-authored geopolitical simulation.

Generated outputs are ignored by Git and reproducible:

- `world/expanded.json`: full fictional world.
- `world/graph_truth.json`: world relationships, derived by code.
- `corpus/manifest.sqlite`: planned/drafted/critiqued/validated/failed state, records, indexed evidence, spend reservations and optional batch-job registry.
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

The running corpus pipeline is offline and needs no credentials. The optional adapters are **OpenAI** (ChatGPT-family API models) and **Ollama**; Anthropic is not required. These adapters share `complete(prompt, max_tokens)`. They are not yet wired into cable generation, extraction or query answering.

OpenAI uses the Responses API. A ChatGPT subscription does not include OpenAI API usage: use a separately billed API project and an `OPENAI_API_KEY` supplied securely through the process environment. No ChatGPT browser session or subscription credentials are used. Never commit keys or paste them into chat.

To make an explicit, optional single model call:

1. Copy `config/corpus.yaml` to an ignored local path such as `corpus/model.yaml` after setup.
2. In that copy, set `provider: openai`, `openai_model` to an available API model ID, and both token prices to current published USD per million tokens. Choose a small model for inexpensive rendering and a stronger model for QA when those stages are implemented. No model names or prices are guessed here.
3. Set `OPENAI_API_KEY` securely in the environment. The network must allow `api.openai.com`; cloud environments may need this destination added in environment settings.
4. Put your prompt into a local text file, then run:

```sh
.venv/bin/python -m scripts.model_prompt --config corpus/model.yaml --prompt-file /path/to/prompt.txt
```

That command is a billable call and is never invoked by setup, startup or tests. It defaults to at most 1,600 output tokens. Keep the original `config/corpus.yaml` in offline mode for corpus commands. For a locally running Ollama service, the same command accepts `provider: ollama` and `ollama_model` instead; no OpenAI key is needed.

The accountant atomically reserves a conservative request bound before network I/O, records returned input and output usage (including billed reasoning output), and retains reservations after uncertain failures. Incomplete responses and refusals are accounted and reported as errors. `MAX_SPEND_USD` defaults to $40, with config `max_spend_usd` as the fallback. This is a local ledger guard based on configured pricing, not a provider billing limit. Set a provider-side limit as well before paid use. No automatic retry, batch submission or recovery workflow is implemented yet. Responses use `store: false`; this does not by itself guarantee provider-side zero retention.

## Validation

`pytest` exercises the generation/resume path, XML roll-up, mutable narrative failures, budget enforcement, citation-to-paragraph fidelity, public/secret access, temporal queries and alias disambiguation using isolated temporary corpora.

For optional real-browser tests, install Playwright outside the checkout and use an installed Chromium:

```sh
npm install --prefix /tmp/kg-browser playwright@1.56.1
PLAYWRIGHT_MODULE=/tmp/kg-browser/node_modules/playwright node tests/browser.cjs
```

Start the server first. The script checks search, citation dialogs, persona switching, graph/timeline, scorecard, bible and mobile overflow. It writes a desktop screenshot to `/tmp/kg-dea-desktop.png`.

## Remaining brief work

The offline first version intentionally defers editorial seed approval, richer lifetime/membership/corridor semantics, alias usage in narrative prose, event quantities in extraction, 5% contradiction and 1–2% correction sampling, 3-pass/best-of LLM narrative rendering, actual batch resumption, general LLM extraction and QA grading, real NTK authorization, official schema confirmation and native desktop packaging. Model adapters, optional relation fields and tables are extension points, not completed features. The UI, corpus and scorecard identify the baseline so it cannot be mistaken for completion of these phases.
