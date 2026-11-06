# IntelDoc KG demo runbook

A complete script for presenting the demo to a law-enforcement audience. It assumes the presenter has never run the system. Everything named in the demo is fictional except the geography; say that out loud in the first minute and again at the end.

The demo takes 12 to 15 minutes plus questions. Rehearse it once end to end the day before; the whole script is deterministic, so what you see in rehearsal is what you will see in the room.

## 1. What the audience should leave believing

1. The ingest understands real IC document structure: PUBS.XML, ISM portion marks, NTK profiles.
2. The graph answers questions that keyword search cannot: multi-hop, temporal, cross-agency.
3. The whole thing can be measured, because the corpus was built from a known world with ground truth.

Every step below serves one of those three. If you are short on time, cut steps 6 and 10, never steps 3, 4, 7 or 9.

## 2. Setup, the day before

On a laptop with Python 3.12 or newer and a Chromium-based browser:

```sh
git clone https://github.com/hemangnagar/kg-dea.git && cd kg-dea
bash scripts/setup.sh
```

Setup installs dependencies, expands the fictional world, verifies the published corpus archive against its checksum and unpacks it. It takes two to three minutes and needs no API key and no network beyond the clone and the Python packages. Then:

```sh
bash scripts/start.sh
```

Open `http://127.0.0.1:8000` in the browser. For a cleaner stage, run the browser in app mode instead:

```sh
chromium --app=http://127.0.0.1:8000
```

**Pre-flight checklist.** Do all of these the day before and again 15 minutes before the talk.

| Check | Expected |
|---|---|
| `curl http://127.0.0.1:8000/api/health` | `{"status":"ok","validated":5000,...}` |
| Top of the Investigate page, persona Secret // NOFORN | 5,000 accessible cables, 958 connected entities, 15,041 distinct accessible facts (3,241 from cables plus the call edges) |
| Same, persona Unclassified // FOUO | 5,000 cables, 784 entities, 2,256 facts |
| The notice line under the search box | "Narratives by anthropic plus 51 hand-written" |
| Click a citation chip in any answer | a dialog with the cable, the highlighted paragraph and portion marks |
| Graph explorer tab | a network draws within two seconds |

If any check fails, see section 7 before changing anything else.

**Stage settings.** Browser at 110 percent zoom, window at least 1400 pixels wide, persona set to **Secret // NOFORN**, Investigate tab selected, no dialog open, search box empty. Have the projector show the browser only.

## 3. The script

Each step gives you what to do, what appears, and what to say. The numbers are the measured results of the published corpus; if you see different numbers, the corpus is not the published one (section 7).

### Step 0. Open (45 seconds)

Do nothing yet. Point at the stats row.

Say: "Five thousand synthetic intelligence cables about fictional Mexican cartels, 2010 to 2026, in real PUBS XML with real portion marks. Every organization, person, nickname, company and vessel is invented; only the geography is real. We built the world first and generated the cables from it, so we know the complete truth behind the corpus, which is what lets us measure the graph at the end. The analyst sees one search box."

### Step 1. A multi-hop question (90 seconds)

Click the chip **Which companies connect to Bruma del Cobre?** or type it and press Investigate.

Appears: "Found 24 supported relationships." Each line is a company, a relationship (supported, owns, designated in) and an event or the organization, with a dated citation chip. The right panel draws the organization's neighborhood.

Say: "No cable says 'company X is connected to Bruma del Cobre'. The graph walked organization to event to company, two hops, across cables from different agencies, and brought back every path with the paragraph behind it. Keyword search on the organization name would have returned a thousand cables and no answer."

Point at the chips: "Every bracket is a cable and a paragraph number with its portion mark."

### Step 2. Open a citation (60 seconds)

Click the first citation chip in the first result.

Appears: a dialog with the cable header (agency, date, subject, source and reliability grade), the numbered paragraphs with their portion marks, and the cited paragraph highlighted.

Say: "This is the actual document. The paragraph the graph cited is highlighted. The marks on each paragraph are what the ingest read, and the roll-up at the document level was computed from them, not templated." Scroll once to show it reads like reporting: source access, caveats, aliases. "Four thousand nine hundred of these were written by a model from the planted facts, fifty-one by hand as exemplars, and every one passed the same checker: planted facts present, no invented names, no invented numbers."

Close the dialog with the × button.

### Step 3. A temporal question (60 seconds)

Click the chip **Who led Bruma del Cobre in 2021?**

Appears: one relationship. "Yesenia Anzures Ibarra leads Bruma del Cobre, 2020-02-27 to 2027-01-01 (exclusive)", three citation chips, all marked S//NF. The right panel shows the neighborhood; click **Timeline** on that panel to see the dated windows.

Say: "Leadership is a window, not a fact. The question asked about 2021; the graph found the window that contains it. The previous boss was killed on the Colima road in February 2020 and she took over. Six agencies reported it, 112 citations in total, every one of them Secret."

Leave this question in the box.

### Step 4. The persona switch (90 seconds, the most important step)

At the top right, change **Persona** from Secret // NOFORN to **Unclassified // FOUO**.

Appears: the page clears and re-runs the same question. "No supported relationships were found in the accessible reporting." The stats row drops to 784 entities and 2,256 facts.

Say: "Same question, same corpus, a user without Secret access. The answer is not redacted after the fact; the graph was filtered before traversal, so the paragraphs this user cannot see were never on the table. Her leadership exists only in S//NF paragraphs, so for this user it does not exist."

Click the chip **Which companies connect to Bruma del Cobre?** while still Unclassified: 24 results again, now without the owns edges, and every chip reads U or U//FOUO. Click one chip: the dialog shows a notice that paragraphs were withheld under this persona.

Say: "Public facts survive, financial structure does not. Each paragraph carried its own mark, and that is the unit of access."

Switch the persona back to **Secret // NOFORN**.

### Step 5. Corridor control over time (60 seconds)

Click the chip **Which corridors did Bruma del Cobre control?**

Appears: 24 controls relationships, each a plaza or route with a from and until date: Manzanillo port plaza, the Highway 15 Pacific route, Nogales crossing, San Luis Río Colorado, Mexicali.

Say: "Plazas change hands. Nogales went to this organization in 2013 under an accord, back to its rival in 2019 when the accord collapsed, and back again in 2022 when a plaza boss defected. Those are four dated windows in the graph, each backed by reporting." Optionally: "At Unclassified this question has no answer either; corridor control is Secret-only reporting."

### Step 6. Partner data: the FBI call records (2 minutes)

Click the chip **Who did Yesenia Anzures Ibarra call in 2022?**

Appears: 24 call relationships, each "A called B" with a date and an amber chip reading "FBI call record" with the mark U//LES.

Say: "This is a second source from a second agency: a spreadsheet of call records, not a document. The numbers in it are labels that change hands. The graph resolved each one to the person who held it on the day of the call, and fused the result with the cable-derived graph, keeping the provenance separate: amber chips are partner records, green chips are cable paragraphs."

Click one amber chip.

Appears: the record with its time and duration, and under Caller and Callee the label, the person it resolves to, and the dates that person held it.

Say: "Same number, different holder a year earlier. Resolving by the window rather than by the number is what makes the fusion right." Close the dialog.

Now click the chip **Who led Bruma del Cobre in 2021?** and open the first citation chip (a Treasury cable).

Appears: above the paragraphs, an amber notice: "Partner data (FBI call records, U//LES): 3 calls between Yesenia Anzures Ibarra and Nicanor Abundis Fregoso" in the week before the event, each a chip.

Say: "The cable says these two were involved in the same event. The partner agency's records show them talking three times in the days before. Nobody read the spreadsheet against the cable; the graph did." Close the dialog.

Switch the persona to **Unclassified // FOUO** and click the call question chip again: no results. Say: "LES-handled partner data is not available to this user, and neither are the corroborations." Switch back to **Secret // NOFORN**.

### Step 7. The alias trap (45 seconds, optional)

Click the chip **Who is El Relojero?**

Appears: "This alias identifies more than one fictional person." Two buttons: Fermín Loera Arriaga and Rubén Montes Galindo.

Say: "Nicknames are shared, inherited when a boss falls, and reused across organizations. The graph does not guess. Pick one." Click Fermín Loera Arriaga: his relationships appear, including his defection from one organization to another with dated membership windows.

### Step 8. The graph explorer (2 minutes)

Click **Graph explorer** in the left navigation.

Appears: a force-directed network of the six organizations and their structural edges, about 130 nodes, with the label "300 of N edges". Organizations are the large green nodes.

Say: "This is the extracted graph itself, filtered to structure: who leads, who belongs, who controls which corridor, who owns which company. Every line was extracted from a cable paragraph you can open."

Type **Yesenia Anzures Ibarra** in the Center box, set Hops to **2**, click **Everything**, then click her node (the large one in the middle).

Appears on the right: her aliases (La Doctora, Anzures Ibarra, La Sobrina), her leadership edge with 112 citations across six agencies, her company ownership, her designation by Treasury.

Point at the two "owns Cambios del Pacífico Norte" edges with different dates. Say: "Two cables disagree on the date. About five percent of the corpus carries a deliberate contradiction like this, because real reporting does. The graph keeps both claims with their citations instead of silently picking one."

Mention, without clicking: "The accessible graph exports as GraphML or Neo4j CSV from the links under the canvas, respecting the persona."

### Step 9. The scorecard (2 minutes)

Click **Extraction scorecard**.

Appears: four metrics, then the evidence paragraph, then recall by edge type.

| Metric | Value |
|---|---|
| Precision | 94.5 percent |
| Precision excluding planted contradictions | 100 percent |
| World recall | 97.1 percent |
| Planted-fact recall | 99.9 percent |

Say: "This is measured, not claimed. We know every relationship the world contains, 3,156 of them. The extractor recovered 97 percent from the text. The 5.5 percent precision gap is the planted contradictions: the extractor correctly reported what the contradicting cables said, and those claims are wrong on purpose. Excluding them, nothing extracted was false."

Point at the table: "Membership and ownership are the hardest edges, because they live only in Secret paragraphs and appear in fewer cables."

Scroll to the panel **Partner data: FBI call records**. Say: "Fourteen thousand synthetic records. Number-to-person resolution by the dated holder windows is right 99.9 percent of the time, including on the 8,700 records involving a number that changed hands; resolving every number to its first known holder would be right 76 percent of the time. The errors are numbers still used by a previous holder for a few weeks after a handover, which is in the data on purpose."

Then say the honest sentence, because someone will ask otherwise: "These numbers describe a constrained setting. The planted facts are written as explicit sentences and the extractor is checked against the world's vocabulary. On real, unconstrained prose the numbers will be lower, and measuring that is the next phase."

### Step 10. The world bible (45 seconds, optional)

Click **World bible**. Scroll slowly past the six factions and the corridors.

Say: "Everything you saw is here: six invented factions with their arcs, 23 real plazas and routes with dated control histories, 53 named people. Anyone in this room can check any name against the public record and find nothing, because none of it is real. The geography is."

### Close (30 seconds)

Return to **Investigate**. Say: "Real document structure, questions keyword search cannot answer, and a number you can audit. Synthetic data only; a production deployment would put real authentication and NTK enforcement in front of this."

## 4. Questions you will get, and honest answers

**Is any of this real?** No person, organization, company, vessel, nickname or document is real. The places are. A blocklist of real organization and official names is enforced on both the world and every cable.

**Who wrote the cables?** 4,949 by Claude Haiku 5.5 from the planted facts and the hand-written exemplars, 51 by hand. Every cable passed a deterministic checker: planted entities and dates present, no names outside the world, no numbers outside the planted quantities, portion marks valid, 250 to 900 words.

**What did it cost?** About twelve dollars of API spend for the full corpus, including retries, in about two and a half hours.

**Why is precision 100 percent?** Because the extractor's claims are verified against the paragraph before they count: a claim whose quote or relation the checker cannot confirm is dropped (173 were). That is constrained extraction, and the scorecard says so. The world-recall figure is the one that measures how much the pipeline found.

**Can it ingest our PUBS feed?** The XML follows the public ODNI structure, but official schema conformance has not been verified because no schema package was available. Supply the XSD and the validation hook already exists.

**Is the persona switch real security?** No. It demonstrates portion-level filtering before traversal. Production needs authenticated, server-assigned clearances, NTK enforcement, audit logging and transport hardening.

**Is it a graph database?** The graph is an edge list with provenance in SQLite, traversed in Python. It exports to GraphML and Neo4j CSV. For this scale that is sufficient; for a real feed you would put it behind a graph store.

**How does it handle aliases?** Unique nicknames resolve automatically. Shared nicknames ask the analyst to choose. Family surnames shared across generations are a known trap the demo includes on purpose.

**Does it do free-text questions?** It recognizes entity names and aliases, places, years, and the words companies, corridors, members, owns and led. It is deterministic retrieval with two hops, not an LLM answering freely. That is a feature for an audience that needs every answer traceable.

**Where did the call records come from?** Generated from the same fictional world, so every record has a known true caller and callee; that is what makes the resolution measurable. The file has the shape of a provider extract (time, duration, labels) with non-dialable labels and no cell-site data. In a real deployment the partner's file would be ingested through the same resolver against the agency's own identifier holdings.

**Can it do link analysis on the calls?** It fuses them into the graph and shows them per person and per cable; frequency, community and pattern analysis are deliberately out of scope for this demo.

**What is next?** Unconstrained prose and extraction to get real precision and recall numbers; cross-agency questions; an editorial review of the world; official schema validation.

## 5. Safe questions beyond the script

All tested on the published corpus at Secret // NOFORN:

| Question | Result |
|---|---|
| Who is La Garza? | disambiguation between Lorena Mijares Ocampo and Irene Sandoval Quiroga |
| Who was a member of Los del Cedro Partido? | 24 relationships, leadership and membership windows |
| Who owns Transportes Cerro Pardo? | 7 relationships, owner and nominee (Secret only; empty at Unclassified) |
| Who did Fermín Loera Arriaga call in 2018? | 20 call relationships (Secret only) |
| Who did Lorena Mijares Ocampo call in 2016? | 24 call relationships (Secret only) |
| What happened in Reynosa in 2020? | 6 relationships around the Reynosa plaza events of that year |

Questions that will not work well: anything without an entity name, place or year in it; "why" questions; questions about agencies as subjects. Say "the engine is deterministic retrieval" and move on.

## 6. Timing

| Step | Minutes |
|---|---|
| 0 Open | 0.75 |
| 1 Multi-hop | 1.5 |
| 2 Citation | 1 |
| 3 Temporal | 1 |
| 4 Persona | 1.5 |
| 5 Corridors | 1 |
| 6 Partner call records | 2 |
| 7 Alias (optional) | 0.75 |
| 8 Explorer | 2 |
| 9 Scorecard | 2 |
| 10 World bible (optional) | 0.75 |
| Close | 0.5 |
| Total | about 14 |

## 7. Troubleshooting

**The page does not load.** The server is not running or is on another port. Run `bash scripts/start.sh` in the repository; if it reports the port in use, run `PORT=8010 bash scripts/start.sh` and open that port.

**Stats show zero cables.** The corpus was not installed. Check that `corpus/manifest.sqlite` exists; if not, run `bash scripts/setup.sh` again. If the checksum step fails, the archive is corrupt; re-clone.

**Stats show different numbers from this runbook.** You are serving a different corpus (for instance one built offline). Move `corpus/` aside and run `bash scripts/setup.sh`.

**An answer says "Check that the local API is running."** The server died. Restart it; the browser needs no reload.

**The persona switch seems stuck.** Reload the page; the persona resets to Secret and the state clears.

**A dialog will not close.** Press Escape.

**Accounted API spend shows $0.00.** Expected. The published corpus ships without the generation ledger; the spend is documented in `artifacts/haiku-5000/run-report.json`.

**The call question returns nothing.** The partner records were not ingested. Run `.venv/bin/python -m scripts.demo cdr` once (ten seconds) and reload.

**Do not** run any `scripts/demo` command during the demo, and do not change files under `world/`; the corpus is pinned to the world it was generated from and will refuse a different one.

## 8. After the demo

Nothing to clean up. The server stops with Ctrl-C. The corpus and world are regenerable from the repository at any time.
