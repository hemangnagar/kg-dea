# IntelDoc KG world bible

Status: **draft, unreviewed**. Everything named here is invented: every faction, person, nickname, company, vessel, registration, source and operation name. Only the geography is real. Anyone in the room can check any name against the public record and find nothing.

The authoritative seed is `world/seed.yaml`. The expanded world (`world/expanded.json`) and the graph truth (`world/graph_truth.json`) are derived from it by `inteldoc/world.py` and are never edited by hand. The seed validator (`python -m scripts.validate_seed`) enforces the structural rules listed at the end of this document.

## 1. The world in one page

Six factions fight over the real plazas and routes of the Mexico–US drug trade between 2010 and 2026.

| Faction | Base | Founded | Business | Fate |
|---|---|---|---|---|
| **Bruma del Cobre** ("los Brumas") | Manzanillo, Colima | 2010-03-14 | Precursor chemicals through the Manzanillo docks, north on Highway 15, across at Nogales and San Luis Río Colorado | Founder arrested 2014 and extradited 2016; second boss killed 2020; run since by the founder's niece, whose role appears only in Secret reporting |
| **Pacto del Faro Gris** ("los Faros") | Veracruz | 2011-01-22 | Gulf port pact: Veracruz, Tuxpan and Tampico docks, Highway 180 to Tamaulipas | Founder killed 2016; successor arrested 2023; current boss known only in Secret reporting |
| **Círculo del Valle Quieto** ("el Círculo") | Monterrey | 2010-09-01 | Trucking network holding Nuevo Laredo and Piedras Negras through corrupt customs; takes Reynosa in 2015 | Founder arrested 2019; niece leads since |
| **Red del Horizonte Azul** ("los Azules") | Tijuana | 2010-05-30 | Tunnels at Otay Mesa, pangas from Ensenada, vehicle loads at Tijuana, Tecate and Mexicali | Founder arrested 2014 and extradited 2015; loses Mexicali and Nogales to Bruma in 2022 |
| **Liga del Cedro Lunar** ("la Liga") | Guadalajara | 2010-11-18 | Synthetic laboratories in the Tierra Caliente; takes the Lázaro Cárdenas port in 2012 | Founder arrested 2018 and released 2024; splits in 2018 |
| **Los del Cedro Partido** ("los Partidos") | Apatzingán | 2018-06-30 | Split-off from the Liga holding Apatzingán, Uruapan and Lázaro Cárdenas; reaches Texas through Ojinaga under a 2020 accord | Alliance with the Círculo collapses 2024; sicario chief defects back 2025 |

### The arcs

- **Bruma del Cobre** is the demo's main thread. Rogelio Anzures Tapia ("El Portuario") founds it, allies with Horizonte Azul in the Hermosillo accord of 2013, and is arrested in Operation Marea Baja in 2014. Damián Olivares Rendón ("El Contador") inherits both the network and the nickname El Portuario. He loses his Lázaro Cárdenas lieutenant Fermín Loera to the Liga in 2017, loses Nogales when the accord collapses in 2019, and is killed on the Colima road in 2020. Yesenia Anzures Ibarra ("La Doctora") takes over; her leadership is a **Secret-only** fact. She gains the Mexicali and Nogales crossings when Irene Sandoval defects from the Azules in 2022, is designated by Treasury the same year, and loses her launderer Saúl Berumen in Operation Vidrio Negro in 2025.
- **Pacto del Faro Gris** shares Reynosa with the Círculo (2012 to 2015), allies with the Liga over the Highway 180 route (2014 to 2016), loses its founder in 2016, its Tampico crew in 2017 and its boss in 2023. Joel Pedraza, the Reynosa plaza boss, changes sides twice and is killed in 2021.
- **Círculo del Valle Quieto** is the steady northeastern power: it loses an 870 kg load at Laredo in Operation Cauce Seco (2016), its founder to arrest in 2019, and briefly Reynosa and Nuevo Laredo to the Faros in 2020, then recovers both. It allies with the Cedro Partido in the Saltillo accord of 2020 and breaks it in 2024.
- **Red del Horizonte Azul** loses its founder early (2014), a tunnel with 4,100 kg at Otay Mesa (2017), the Hermosillo accord (2019) and its Mexicali plaza boss (2022).
- **Liga del Cedro Lunar** takes Lázaro Cárdenas by killing the Bruma plaza boss in 2012, allies with the Faros in Puebla (2014), loses its founder in Operation Luna Nueva (2018) and splits that summer. It buys protection from a state police commander in Uruapan (2021). The founder is released in 2024.
- **Los del Cedro Partido** is the youngest faction: founded by the defector Fermín Loera, who inherits the Liga founder's nickname El Cirujano. It loses a laboratory with 15,000 L of chemicals in 2022 and its sicario chief in 2025.

## 2. Geography

Sixty-two real places, each with state, country and kind (port, border crossing, city, hub, highway, region). Twenty-three corridors are modelled: plazas (a crossing or port and its approaches) and routes (a highway or maritime lane). Each corridor lists the real places it spans, the US hubs it feeds and the commodities that move on it, and carries a **dated control history**. Examples:

- *Nogales crossing* (Nogales, Sonora; Nogales, Arizona; Tucson): Azules 2010, Brumas from the Hermosillo accord 2013, Azules again from the 2019 collapse, Brumas again from the Sandoval defection 2022.
- *Reynosa plaza* (Reynosa; McAllen): Faros 2011, Círculo 2015, Faros 2020, Círculo 2021.
- *Highway 15 Pacific route* (Guadalajara to Hermosillo): Liga 2010, Brumas from 2013.

Control windows are contiguous and non-overlapping; the validator rejects gaps and overlaps.

## 3. People

Fifty-three hand-authored people across all tiers (boss, lieutenant, plaza boss, sicario chief, launderer, logistics, lawyer, corrupt official) and all official roles (police, customs, mayor, prosecutor, military). One hundred generated lower-tier members fill out the rosters; they have plausible names, one nickname and one surname alias each, and routine events only.

Each authored person has:

- two to four aliases: nicknames and short forms (surname, partial name);
- **membership windows** per organization (the `member_of` edges), which move when a person defects;
- arrest, death, extradition and release dates where relevant;
- an alias history where a nickname is inherited.

Deliberate alias-resolution traps:

| Trap | Instances |
|---|---|
| Nickname shared by exactly two people | El Relojero (Loera, Montes), La Garza (Mijares, Sandoval), El Sastre (Sarabia, Quiroz), El Diez (Pedraza, Ledezma), El Búho (Ibáñez, Lemus) |
| Nickname inherited when a boss falls | El Portuario, El Faro, El Cartógrafo, El Timonel, El Cirujano |
| Family surname shared across generations | Anzures (uncle and niece), Vidaurri (uncle and niece), Ruvalcaba (cousins) |
| Identifier shared by two people over time | about one in ten of the 360 DEMO-TEL / DEMO-ACCT labels |

The query engine resolves unique aliases and asks for disambiguation when a shared one is used.

## 4. Companies, assets, identifiers, sources

- **17 authored front companies** (trucking, produce export, currency exchange, used cars, mining, hospitality, agricultural supply), each with an owner and, for some, a nominee; 43 generated ones. Ownership becomes `owns` and `nominee_for` edges dated at registration.
- **12 authored assets** (vessels, a semi-submersible, aircraft, tractor-trailers, vehicles, a tanker truck) with DEMO-prefixed registrations; 28 generated ones. Each is operated by one organization.
- **360 identifiers** (DEMO-TEL-nnnnn, DEMO-ACCT-nnnnn) held by people over dated windows. They are labels, not dialable numbers or bank accounts. Holder windows are derived from the events that use each identifier, extended into continuous spans, and 59 of the 180 phones are handed to a colleague after their last use, so the same number resolves to different people in different years. Ten cited numbers resolve to someone other than the person a cable attributes them to, which is left in as a realistic inconsistency.
- **49 sources**, seven per agency (DEA, FBI, HSI, CBP, DIA, Treasury, OSINT), each with a stable reliability grade and a kind (port worker, customs broker, inspection record, financial filing, press digest, and so on).

## 5. Timeline and events

Forty-two authored beats, each with a name, a date, a place, an organization, a corridor where relevant, participants with roles, a quantity where relevant and a one-paragraph description used as narrative context. Beat types: Founding, Alliance, AllianceBreak, Split, Arrest, Extradition, Release, Killing, Seizure, Payment, Designation, Election.

The expansion adds routine events to reach 500, sampled from the world rather than invented: a Shipment moves a commodity the corridor actually carries, from a place on that corridor, by a member of the organization that controlled it on that date, using an asset that organization operates and a company one of its members owns. A Payment goes from a launderer to a corrupt official of the same organization. A Seizure happens at a crossing or port on a controlled corridor. An Arrest removes a generated member from later events. Thirty-five percent of routine events cluster within 45 days of an authored beat so the corpus shows reporting bumps.

## 5b. Partner data: FBI call records

A second, structured source generated from the same world: 14,000 synthetic call records between phone labels, sampled around the events (including calls with the organization's boss in the week before) and among members of the same organization, plus 2,000 calls involving numbers the world does not know. A share of handed-over numbers is still used by the previous holder for a few weeks, so resolution has genuine errors. Records carry `U//LES` handling from FBI. Ingestion resolves labels through the holder windows and adds `called` edges (person → person, dated) with the record as provenance; the scorecard reports resolution accuracy against the generator's truth.

## 6. The knowledge graph

Nodes: organization, person, place, corridor, company, asset, identifier, source, event. Every node has a canonical name, a stable id and an alias list.

Edges (all dated; windowed edges carry `until`):

| Edge | From → To | Window |
|---|---|---|
| participated_in, arrested_in, killed_in, extradited_in, released_in, elected_in, removed_in, paid_in, designated_in | person → event (role-specific) | point |
| linked_to | organization → event | point |
| occurred_at | event → place | point |
| transited | event → corridor | point |
| supported | company → event | point |
| involved_in | asset → event | point |
| uses | person → identifier | point |
| called | person → person (from partner call records) | point |
| leads | person → organization | window |
| member_of | person → organization | window |
| controls | organization → corridor | window |
| allied_with | organization → organization | window |
| split_from | organization → organization | point |
| owns, nominee_for | person → company | point (registration) |

Graph truth is the deduplicated union of structural edges (leadership, membership, ownership, corridor control, alliances, splits) and event edges. The 500-event world has roughly 3,100 truth edges.

## 7. How cables sample the world

Each cable takes one event and the reporting agency's partial view of it. The first three facts (actor, organization, place) are public and always included. The rest are kept with high probability if they match the agency's focus (Treasury sees ownership and payments, CBP sees vehicles and crossings, DIA sees structure and alliances, and so on) and with lower probability otherwise. Identifiers, corridor control, membership, ownership and payments never appear in Unclassified paragraphs. A leadership window marked `secret_only` appears only in Secret cables; this is what makes "Who led Bruma del Cobre in 2021?" answerable at Secret // NOFORN and unanswerable at Unclassified // FOUO.

Five percent of core cables carry one fact with a deliberately shifted date (recorded in the cable's `dispute` field). One to two percent are follow-up cables that correct an earlier DocumentID on the same event (`corrects`, rendered as a PUBS `Relation`). The scorecard reports contradiction edges and precision excluding them.

## 8. Validator rules

`inteldoc/seed.py` rejects a seed that has any of: duplicate ids or names; a blocklisted real name (accent- and case-insensitive); a dangling reference; a person with no real place; overlapping membership or leadership windows; leadership outside the leader's membership; an organization founding event whose date differs from `founded`; a fracture whose departing leader does not leave one organization and join the other on the split date; an alliance that is not symmetric or whose dates differ from its events; a corridor whose control history has gaps, overlaps or a single controller; a person appearing in an event after death, or after arrest except for extradition, release or designation; an inherited alias that starts before the donor fell; a shared alias held by more than two people; a beat without a name and description, or with a date in its description; fewer than five shared and three inherited aliases; counts outside the brief's ranges.

## 9. Known limitations

- The seed is a draft. Nobody has reviewed the names for accidental resemblance beyond the starter blocklist.
- Generated events use templated descriptions. The offline narrative is anchor sentences plus context plus boilerplate, not prose; the model-assisted path writes prose around the same anchors.
- Event quantities are planted and checked in text but are not graph edges.
- Aliases appear in prose (second mentions use a unique alias) but the forty-percent alias-usage target from the brief is not measured.
- Membership of generated people is a single open window; only authored people move between factions.
