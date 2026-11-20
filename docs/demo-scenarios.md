# Demo scenarios

Eight short stories to test and present the workbench. Each one uses a different part of the system and every name, date and count below was checked against the published corpus. Run them in order the first time; after that, pick the ones that fit the audience.

Site: https://knowledgegraph1.eastus.cloudapp.azure.com/ · user `demo`. Set the header to **Developer view** when you want citations and raw data on screen, **Analyst view** when you want prose only. Persona **Secret // NOFORN** unless a step says otherwise. All names are fictional; only the geography is real.

---

## 1. Succession at the top

**What it shows:** time-aware answers, the same question answered differently per year, and the persona filter.

1. Workspace, Developer view. Ask **Who led Bruma del Cobre in 2012?** The brief names Rogelio Anzures Tapia, the founder, known on the docks as El Portuario.
2. Ask **Who led Bruma del Cobre in 2018?** Now it is Damián Olivares Rendón, who took over when Anzures was arrested in Operation Marea Baja on 2014-08-02. The brief notes that cables disagree on the exact start date; that disagreement is planted on purpose and the graph keeps every version with its citation.
3. Ask **Who led Bruma del Cobre in 2021?** Exactly one relationship: Yesenia Anzures Ibarra, from 2020-02-27, the day Olivares was killed. Three Treasury citations, all S//NF.
4. Switch the persona to **Unclassified // FOUO**. The same question returns nothing, and the stats drop from 958 entities to 784. Her leadership exists only in Secret paragraphs.
5. Switch back. Click **Investigate** in the left menu, ask the 2021 question again, and click **Timeline** on the right panel to see the three leadership windows end to end.

Say: "Leadership is a window, not a fact. The question names a year and the graph finds the window that contains it."

## 2. Follow the money

**What it shows:** two-hop reasoning, nominee ownership, sanctions, and the raw-data buttons.

1. Workspace. Ask **Which companies connect to Bruma del Cobre?** Twenty-four relationships: eight companies tied to the organization through sanctions designations, shipments, seizures and payments. No cable states "company X is connected to Bruma del Cobre"; the graph walked organization to event to company.
2. Click **Source cables (66)**: the cables behind the text, each with a link to its PUBS XML. Click **Graph facts (24)** to see the raw relationships. Click **Call records**: 300 of the 1,200 calls among the people behind these companies.
3. Ask **Who owns Transportes Cerro Pardo?** Three relationships: Saúl Berumen Ledesma, called El Notario, is the real owner; Carolina Medrano Siller is the registered nominee, and the cables disagree on the dates. Say: "Owner and front are two different edges, and the brief says which is which."
4. Switch to **Unclassified // FOUO** and ask it again: nothing. Ownership structure is Secret-only reporting.

## 3. The phone that changed hands

**What it shows:** partner data from a second agency, identifiers resolved by the date they were held, and corroboration inside a cable.

1. Secret persona, Workspace, Developer view. Ask **Who did Yesenia Anzures Ibarra call in 2022?** Twenty-four calls, all from FBI call records marked U//LES. Nicanor Abundis Fregoso is her most frequent contact.
2. Click **Call records (64)**. The table lists the 24 cited calls first, then 40 more among the same people in 2022. Open any row: the record shows the phone label, the person it resolves to, and the dates that person held it.
3. Now the handover. In the Investigate page, open any cable and click a chip, or simply open these two records from the Call records table of any question that lists them: **005578** (2019-03-07, label DEMO-TEL-00011, held by Ulises Gamboa Nájera from 2019-03-06) and **003730** (2025-02-23, the same label, now held by Bonifacio Ornelas Tovar from 2021-03-28). Say: "Same number, two people. Resolving by who held it that day, not by the number, is what makes the fusion right. The scorecard measures this at 99.9 percent."
4. Ask **Who led Bruma del Cobre in 2021?** and click the first citation, a Treasury cable. Above the paragraphs an amber box reads: 3 calls between Yesenia Anzures Ibarra and Nicanor Abundis Fregoso between 2022-05-05 and 2022-05-13, the week before the event the cable reports. Say: "Nobody read the spreadsheet against the cable. The graph did."
5. Switch to **Unclassified // FOUO**: the call question returns nothing and the amber box is gone. LES-handled partner data is not available to this persona.

## 4. Crossing from one organization's graph into another

**What it shows:** each organization is its own sub-graph, and the search follows a relationship across the boundary.

1. Secret persona, Workspace. Ask **Who did Lorena Mijares Ocampo call in 2016?** The strip above the brief reads "Graphs touched: Pacto del Faro Gris, Círculo del Valle Quieto" and "Hops across: Pacto del Faro Gris → Círculo del Valle Quieto via called ×4". The last paragraph, "Across organizations", explains the hop: four calls to Benito Sarabia Olguín of the other organization.
2. Ask **Who did Benito Sarabia Olguín call in 2016?** The same boundary from the other side: seven hops into Pacto del Faro Gris and three back.
3. Ask **What happened in Reynosa in 2020?** Six relationships, and the strip shows the two organizations meeting at one event, with hops via "linked to" and "participated in".
4. Open **Graph explorer**, set **Color by** to **organization**, type **Lorena Mijares Ocampo** in Center, choose **Calls**, and set Hops to 2. Orange nodes are her organization, blue are the other; the dashed call edges cross between them. Hover any edge for its dates and citations.

Say: "Two organizations, two graphs. The question started in one, a call record crossed into the other, and the search kept going there. Every hop is listed."

## 5. The same nickname, two people

**What it shows:** alias resolution, deliberate traps, and the analyst teaching the graph a new name.

1. Workspace. Ask **Who is El Relojero?** The graph refuses to guess: it offers Fermín Loera Arriaga and Rubén Montes Galindo. Pick Loera: his relationships appear, including his move from one organization to another with dated membership windows.
2. Ask **Who is El Portuario?** Also two people, Rogelio Anzures Tapia and Damián Olivares Rendón: the nickname was inherited when the first boss fell. Ask **Who is La Doctora?** One person, Yesenia Anzures Ibarra, resolved immediately because the alias is unique.
3. Click her name in the "In this answer" row under the brief. The entity card shows her organization's graph, her three published aliases, and a box for a new one. Type **The Doctor** and click **Add alias**.
4. Ask **Who did The Doctor call in 2022?** It resolves. Say: "An analyst can teach the graph a name from a partner file or a wiretap, and it works everywhere at once: questions, the explorer, the typeahead."
5. Add **The Doctor** to a second person from their card, then ask the question again: the graph now asks which one, exactly as with the published nicknames. Remove both with the × to leave the graph as you found it.

## 6. Plazas change hands

**What it shows:** control windows over 17 years and the explorer's year filters.

1. Workspace. Ask **Who controlled the Nogales crossing?** The brief gives the four windows: Red del Horizonte Azul until 2013-06-11, Bruma del Cobre under the accord until 2019-09-30, Red del Horizonte Azul again when the accord collapsed, and Bruma del Cobre since 2022-08-16 after a plaza boss defected.
2. Ask **Which corridors did Bruma del Cobre control?** Eighteen windows across Manzanillo, Lázaro Cárdenas, the Highway 15 Pacific route, Nogales, San Luis Río Colorado and Mexicali.
3. Graph explorer: Center **Bruma del Cobre**, preset **Structure**, From **2015** To **2018**, Draw. Only the corridors and people of that period remain. Change to From **2023**: the picture changes.
4. Hover the edge between Bruma del Cobre and Nogales crossing: the tooltip gives the window, the citation count and the agencies.

## 7. Re-marking a paragraph at runtime

**What it shows:** access follows the mark on the paragraph, and the graph re-filters immediately.

1. Secret persona, Developer view. Ask **Who led Bruma del Cobre in 2021?** and open the first citation chip.
2. On the highlighted paragraph, change the selector from **S//NF** to **U//FOUO**. The paragraph gets a "re-marked at runtime" badge and the question re-runs.
3. Switch the persona to **Unclassified // FOUO**. The leadership answer now appears for this user, cited to that one paragraph.
4. Switch back, click **Re-marked paragraphs**, and click **Reset all to the published marks**. Say: "The corpus was never rewritten. Access is decided per paragraph, every time, from the mark it carries now."

## 8. Audit the machine

**What it shows:** nothing here is claimed without a number behind it.

1. Click **Extraction scorecard** (Developer view). Precision 94.5 percent, 100 percent excluding the planted contradictions, world recall 97.1 percent, planted-fact recall 99.9 percent. Below, the partner-data panel: 14,000 call records, 99.9 percent resolution against 76.3 percent for a naive approach.
2. Say the honest sentence: "These numbers describe a constrained setting. The planted facts are explicit sentences in the cables. On real, unconstrained prose the numbers will be lower, and measuring that is the next phase."
3. Graph explorer: the links under the canvas export the accessible graph as GraphML or Neo4j CSV, respecting the persona. Open a Source cable's **PUBS XML** link to show the document as ingested, portion marks and all.
4. **World bible**: six invented factions, 23 real places and routes, 53 named people. Anyone can check a name against the public record and find nothing.

---

## Questions that will not work, and why

- Anything without an entity name, a place or a year: the engine is deterministic retrieval, not a chat model. "Why did the accord collapse?" returns nothing.
- Questions about agencies as subjects ("What did the DEA report?"): agencies are provenance, not nodes.
- Spelling a name differently from the world: add the spelling as an alias first (scenario 5).

## Resetting between demos

Re-marks: Workspace → **Re-marked paragraphs** → Reset. Aliases: open the entity card and remove with ×. Both leave the published corpus untouched; nothing else needs resetting.
