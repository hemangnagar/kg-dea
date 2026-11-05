"""Cable planning, offline narrative drafting, deterministic checking and extraction.

The planner samples every cable from the expanded world. The offline drafter
writes anchor sentences in a fixed grammar plus world-derived context; the
checker and the regex extractor share that grammar so the offline scorecard is
an easy baseline by construction. Model-written prose goes through the same
checker (see llm.py).
"""
import hashlib
import json
import random
import re
import unicodedata
from collections import Counter
from datetime import date, timedelta
import yaml
from .world import ROOT, load_world, world_dir, quantity_text
from .models import Cable, Paragraph, Fact
from .store import connect, data_root
from .settings import load_config
from .providers import provider_from_config, BudgetExceeded
from .xmlio import render

VERBS = {'participated_in': 'participated in', 'linked_to': 'was linked to', 'supported': 'supported', 'uses': 'used',
         'involved_in': 'was involved in', 'occurred_at': 'occurred at', 'leads': 'led', 'member_of': 'was a member of',
         'controls': 'controlled', 'owns': 'owned', 'nominee_for': 'was the nominee owner of', 'allied_with': 'was allied with',
         'split_from': 'split from', 'transited': 'transited', 'arrested_in': 'was arrested in', 'killed_in': 'was killed in',
         'extradited_in': 'was extradited in', 'released_in': 'was released in', 'elected_in': 'took office after',
         'removed_in': 'lost office after', 'paid_in': 'was paid in', 'designated_in': 'was designated in'}
# Facts that only appear in Secret paragraphs: identifiers, finances, structure and corridor control.
SECRET_PREDICATES = {'uses', 'controls', 'member_of', 'owns', 'nominee_for', 'paid_in'}
# Facts an open-source summary can plausibly carry.
PUBLIC_PREDICATES = {'participated_in', 'linked_to', 'occurred_at', 'arrested_in', 'killed_in', 'extradited_in', 'released_in',
                     'elected_in', 'removed_in', 'designated_in', 'split_from', 'allied_with'}
# What each reporting agency tends to see: its partial view of an event.
AGENCY_FOCUS = {'DEA': {'uses', 'member_of', 'transited', 'controls', 'supported'},
                'FBI': {'member_of', 'uses', 'participated_in', 'paid_in'},
                'HSI': {'supported', 'involved_in', 'transited', 'owns'},
                'CBP': {'involved_in', 'transited', 'controls'},
                'DIA': {'controls', 'allied_with', 'member_of', 'split_from'},
                'TREASURY': {'supported', 'owns', 'nominee_for', 'designated_in', 'paid_in'},
                'OSINT': set()}
FILLER = ['The reporting office assesses the source as having direct access to the activity described.',
          'The source did not provide the full identity of every participant and the gaps are noted here.',
          'This information has not been corroborated by a second independent source at the time of writing.',
          'The reporting office does not infer an additional relationship from shared location alone.',
          'Analysts should treat the sequence of events as reported rather than as independently confirmed.',
          'The source characterized the activity as routine for the network in that period.',
          'No operational tasking should be based on this reporting without further validation.',
          'The reporting office continues to collect on the entities named in this report.',
          'The source has provided reporting of comparable quality over the preceding reporting cycle.',
          'Details outside the account given by the source remain unconfirmed.',
          'The reporting office notes that nicknames in this reporting may be shared by more than one person.',
          'The handling controls on each paragraph reflect the source and method behind it.',
          'A consumer with a related investigation should contact the originating office before dissemination.',
          'The source was not in a position to observe the final destination of the material described.',
          'Earlier reporting on the same network is available from the originating office on request.',
          'The reporting office has no information indicating that the source is aware of this report.',
          'Place names in this report refer to the municipality unless a crossing or port is specified.',
          'The quantities reported here are the source estimates and have not been weighed by the reporting office.',
          'The source reporting was received through the standard liaison channel for this agency.',
          'The reporting office assesses that the network described remains active in the area of reporting.',
          'Further reporting is expected as the source maintains contact with the individuals named.',
          'The individuals named in this report have appeared in prior reporting under different nicknames.',
          'This report is one of several on the same event and may differ in detail from other agency reporting.',
          'Readers should note that identifiers in this report are labels assigned by the reporting office.',
          'The source has no known motive to fabricate the details reported here.',
          'The reporting office cannot exclude that other participants were present and not named.',
          'This reporting is consistent with the pattern of activity observed on the corridor in prior months.',
          'The company and vessel names in this report were provided by the source and checked against registry extracts.',
          'The reporting office requests that any related seizure data be shared with the originating desk.',
          'The source account was recorded within days of the activity and is considered timely.']
NUMBER = re.compile(r'\d[\d,.]*')
DATE = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')
CAPITALIZED = re.compile(r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+\b')


def canonical(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s).casefold() if not unicodedata.combining(c))


def stable(*parts):
    return int(hashlib.sha256('|'.join(str(p) for p in parts).encode()).hexdigest()[:8], 16)


_TABLES = {}


def tables(world):
    """Per-world lookup tables, cached by object identity: name/alias -> id, scrub list, alias counts."""
    key = id(world)
    if key not in _TABLES or _TABLES[key][0] is not world:
        counts = Counter(canonical(a) for e in world['entities'] for a in e['aliases'])
        lookup = {canonical(e['name']): e['id'] for e in world['entities']}
        for e in world['entities']:
            for a in e['aliases']:
                if counts[canonical(a)] == 1 and canonical(a) not in lookup:
                    lookup[canonical(a)] = e['id']
        allowed = sorted({e['name'] for e in world['entities']} | {a for e in world['entities'] for a in e['aliases']}, key=len, reverse=True)
        scrub = re.compile('|'.join(re.escape(n) for n in allowed))
        _TABLES.clear()
        _TABLES[key] = (world, lookup, scrub, counts, yaml.safe_load((ROOT / 'config/blocklist.yaml').read_text()))
    return _TABLES[key][1:]


def name_lookup(world):
    """Canonical name or unique alias -> entity id. Shared aliases resolve to nothing on purpose."""
    return tables(world)[0]


def plan(count=5000, seed=42, config=None):
    world = load_world(); rng = random.Random(seed); cfg = config or load_config(ROOT / 'config/corpus.yaml')
    if count <= 0:
        raise ValueError('count must be positive')
    if cfg.get('extraction') == 'model' and cfg.get('provider', 'offline') == 'offline':
        raise ValueError('Model extraction requires an online provider')
    entities = {e['id']: e for e in world['entities']}; agencies = list(cfg['agencies'])
    events = world['events']
    sources = {a: [s for s in world['entities'] if s['kind'] == 'source' and s.get('agency') == a] for a in agencies}
    membership = [Fact(**f) for f in world.get('membership', [])]
    ownership = [Fact(**f) for f in world.get('ownership', [])]
    records = []
    for i in range(count):
        e = events[i % len(events)]
        agency = rng.choices(agencies, weights=list(cfg['agencies'].values()))[0]
        secret = agency != 'OSINT' and rng.random() < cfg['secret_fraction'] / 0.9
        core = rng.random() < cfg['core_fraction']
        when = date.fromisoformat(e['date'])
        facts, quantities, description = [], [], ''
        if core:
            event_facts = [Fact(**f) for f in e['facts']]
            public, rest = event_facts[:3], event_facts[3:]
            focus = AGENCY_FOCUS[agency]
            chosen = [f for f in rest if rng.random() < (0.95 if f.predicate in focus else 0.45)]
            if not secret:
                chosen = [f for f in chosen if f.predicate not in SECRET_PREDICATES]
            if agency == 'OSINT':
                chosen = [f for f in chosen if f.predicate in PUBLIC_PREDICATES]
            facts = public + chosen
            leader = next((f for f in world['leadership'] if f['object'] == e['org'] and f['date'] <= e['date'] < f['until']), None)
            if leader and (secret or not leader.get('secret_only')):
                facts.append(Fact(**{k: leader[k] for k in ['subject', 'predicate', 'object', 'date', 'until']}))
            member = next((f for f in membership if f.subject == e['person'] and f.object == e['org'] and str(f.date) <= e['date'] < str(f.until)), None)
            if member and secret and rng.random() < 0.6:
                facts.append(member)
            if e.get('company') and secret and (agency == 'TREASURY' or rng.random() < 0.4):
                facts += [f for f in ownership if f.object == e['company']]
            description = e['description']
            if e.get('quantity'):
                quantities = [quantity_text(e['quantity']), str(e['quantity']['value'])]
        else:
            facts = [Fact(**e['facts'][2])]  # background: routine reporting that only places the event
            description = f"Routine reporting on activity around {e['place']} in the period covered by this cable."
        seen, deduped = set(), []
        for f in facts:
            if f.key() not in seen:
                seen.add(f.key()); deduped.append(f)
        facts = deduped[:3 + 3 * 7]
        groups = [facts[:3]] + [facts[k:k + 3] for k in range(3, len(facts), 3)]
        while len(groups) < 3:
            groups.append([])
        paragraphs = []
        for j, group in enumerate(groups):
            cls = 'S' if secret and j > 0 else 'U'
            controls = ['NF'] if cls == 'S' else ([] if secret or agency == 'OSINT' else ['FOUO'])
            paragraphs.append(Paragraph(number=j + 1, classification=cls, controls=controls, facts=group))
        dispute = None
        if core and i % 20 == 7 and len(facts) > 3:
            k = 3 + i % (len(facts) - 3)
            original = facts[k]
            shifted = original.model_copy(update={'date': original.date + timedelta(days=2 + i % 29)})
            for p in paragraphs:
                p.facts = [shifted if f is original else f for f in p.facts]
            dispute = {'subject': original.subject, 'predicate': original.predicate, 'object': original.object,
                       'reported_date': str(shifted.date), 'world_date': str(original.date)}
        corrects = None
        report = when + timedelta(days=i % 14)
        if i >= len(events) and i % 67 == 33:
            earlier = records[i - len(events)]
            corrects = earlier.cable_id
            report = earlier.report_date + timedelta(days=1 + i % 6)
        source = sources[agency][i % len(sources[agency])]
        cable = Cable(cable_id=f'{agency}-{i + 1:06}-IIR-{report.year % 100:02}', agency=agency, office=f'{agency} Synthetic Reporting Office',
                      report_date=report, subject=f'{e["type"]} reporting in {e["place"]}', event_id=e['id'], source_id=source['name'],
                      reliability=source['reliability'], place=e['place'], keywords=[e['type'], e['place']], ntk=[agency],
                      relevance='core' if core else 'background', paragraphs=paragraphs, corrects=corrects, disputed=dispute is not None,
                      dispute=dispute, description=description, quantities=quantities)
        records.append(cable)
    with connect() as db:
        identity = json.dumps(dict(count=count, seed=seed, world_seed=world['seed']))
        old = db.execute("SELECT value FROM metadata WHERE key='plan'").fetchone()
        if old and old[0] != identity:
            raise ValueError('Existing manifest has a different plan. Use a separate corpus directory or remove generated corpus deliberately.')
        db.execute("INSERT OR IGNORE INTO metadata VALUES('plan',?)", (identity,))
        settings = json.dumps({k: cfg.get(k) for k in ['provider', 'extraction', 'openai_model', 'ollama_model']}, sort_keys=True)
        old_settings = db.execute("SELECT value FROM metadata WHERE key='generation_settings'").fetchone()
        if old_settings and old_settings[0] != settings:
            raise ValueError('Dataset provider changed; choose a new --output-dir')
        if not old_settings and old and cfg.get('provider', 'offline') != 'offline':
            raise ValueError('Existing baseline corpus cannot be relabeled as model-generated; choose a new --output-dir')
        db.execute("INSERT OR IGNORE INTO metadata VALUES('generation_settings',?)", (settings,))
        world_hash = hashlib.sha256(json.dumps(world, sort_keys=True).encode()).hexdigest()
        old_hash = db.execute("SELECT value FROM metadata WHERE key='world_hash'").fetchone()
        if old_hash and old_hash[0] != world_hash:
            raise ValueError('World changed underneath this dataset')
        db.execute("INSERT OR IGNORE INTO metadata VALUES('world_hash',?)", (world_hash,))
        db.executemany('INSERT OR IGNORE INTO cables(id,state,record) VALUES(?,?,?)', [(c.cable_id, 'planned', c.model_dump_json()) for c in records])
    return len(records)


def draft(cable, world):
    """Offline narrative: anchor sentences, world-derived context and varied boilerplate."""
    entities = {e['id']: e for e in world['entities']}
    counts = tables(world)[2]
    mentioned = set()
    main = next((f.subject for p in cable.paragraphs for f in p.facts if entities[f.subject]['kind'] == 'person'), None)

    def display(id):
        e = entities[id]
        unique = [a for a in e['aliases'] if counts[canonical(a)] == 1]
        if e['kind'] == 'person' and id in mentioned and unique:
            return unique[0]
        mentioned.add(id)
        return e['name']

    number = int(cable.cable_id.split('-')[1])
    for p in cable.paragraphs:
        sentences = []
        for f in p.facts:
            subject, obj = display(f.subject), display(f.object)
            sentences.append(f'{subject} {VERBS[f.predicate]} {obj} {"from" if f.until else "on"} {f.date}{f" until {f.until}" if f.until else ""}.')
        if p.number == 1:
            if cable.description:
                sentences.append(cable.description)
            if main and entities[main]['aliases']:
                sentences.append(f"Reporting on this activity refers to {entities[main]['name']} as {entities[main]['aliases'][0]}.")
            if cable.corrects:
                sentences.append(f'This report corrects and supersedes {cable.corrects}.')
        start = stable(cable.cable_id, p.number) % len(FILLER)
        sentences += [FILLER[(start + k) % len(FILLER)] for k in range(2)]
        p.text = ' '.join(sentences)
    used = {s for p in cable.paragraphs for s in FILLER if s in p.text}
    cursor = stable(cable.cable_id) % len(FILLER)
    while sum(len(p.text.split()) for p in cable.paragraphs) < 265:
        candidate = FILLER[cursor % len(FILLER)]; cursor += 1
        if candidate in used:
            continue
        used.add(candidate)
        shortest = min(cable.paragraphs, key=lambda p: len(p.text.split()))
        shortest.text += ' ' + candidate
    return cable


def authored_narrative(cable, cfg):
    """Hand-written narrative for this cable, if one exists under narratives_dir. Checked like model output."""
    folder = cfg.get('narratives_dir')
    if not folder:
        return None
    path = ROOT / folder / f'{cable.cable_id}.json'
    if not path.exists():
        if cfg.get('provider') == 'authored':
            raise ValueError('No authored narrative for ' + cable.cable_id)
        return None
    data = json.loads(path.read_text())
    paragraphs = data['paragraphs']
    if [p['number'] for p in paragraphs] != [p.number for p in cable.paragraphs]:
        raise ValueError('Authored narrative paragraph numbering does not match the record')
    result = cable.model_copy(deep=True, update={'authored': True})
    for target, source in zip(result.paragraphs, paragraphs):
        target.text = ' '.join(source['text'].split())
    return result


def check(cable, world):
    entities = {e['id']: e for e in world['entities']}
    _, scrubber, _, blocked = tables(world)
    combined = canonical(cable.subject + ' ' + ' '.join(p.text for p in cable.paragraphs))
    for name in blocked['organizations'] + blocked['people']:
        if canonical(name) in combined:
            raise ValueError('Blocklisted real name')
    if [p.number for p in cable.paragraphs] != list(range(1, len(cable.paragraphs) + 1)):
        raise ValueError('Paragraph numbering')
    if not 3 <= len(cable.paragraphs) <= 8:
        raise ValueError('Paragraph count')
    if not 250 <= sum(len(p.text.split()) for p in cable.paragraphs) <= 900:
        raise ValueError('Narrative word count')
    allowed_numbers = {str(y) for y in range(2010, 2028)} | set(NUMBER.findall(' '.join(cable.quantities)))
    if cable.corrects:
        allowed_numbers |= set(NUMBER.findall(cable.corrects))
    for p in cable.paragraphs:
        text_c = canonical(p.text)
        known_dates = {str(f.date) for f in p.facts} | {str(f.until) for f in p.facts if f.until}
        for f in p.facts:
            for id in [f.subject, f.object]:
                e = entities[id]
                if not any(canonical(n) in text_c for n in [e['name']] + e['aliases']):
                    raise ValueError('Missing planted fact')
            if str(f.date) not in p.text:
                raise ValueError('Missing planted fact')
        for d in DATE.findall(p.text):
            if d not in known_dates:
                raise ValueError('Unplanned date')
        scrub = DATE.sub(' ', p.text)
        if cable.corrects:
            scrub = scrub.replace(cable.corrects, ' ')
        scrub = scrubber.sub('entity', scrub)
        if CAPITALIZED.search(scrub):
            raise ValueError('Unknown capitalized proper name')
        for token in NUMBER.findall(scrub):
            if token.strip('.,') not in allowed_numbers:
                raise ValueError('Unplanned number or quantity')
        extracted = {f.key() for f in extract(p.text, world)}
        expected = {f.key() for f in p.facts}
        if extracted != expected:
            raise ValueError('Narrative relation mismatch in paragraph ' + str(p.number))


def extract(text, world):
    """Independent text-only baseline. Resolves canonical names and unique aliases; never reads planted-fact arrays."""
    lookup = name_lookup(world)
    results = []
    for predicate, verb in VERBS.items():
        pattern = r'([^.!?;]+?) ' + re.escape(verb) + r' ([^.!?;]+?) (?:on|from) (\d{4}-\d{2}-\d{2})(?: until (\d{4}-\d{2}-\d{2}))?\.'
        for m in re.finditer(pattern, text):
            left, right = canonical(m[1].strip()), canonical(m[2].strip())
            if left in lookup and right in lookup:
                results.append(Fact(subject=lookup[left], predicate=predicate, object=lookup[right], date=m[3], until=m[4]))
    return results


def run(limit=None, retry_failed=False, config=None):
    from .llm import render_narrative, extract_claims
    cfg = config or load_config(ROOT / 'config/corpus.yaml')
    if limit is not None and limit <= 0:
        raise ValueError('limit must be positive')
    with connect() as db:
        saved = db.execute("SELECT value FROM metadata WHERE key='plan'").fetchone()
    if saved:
        identity = json.loads(saved[0])
        plan(identity['count'], identity['seed'], cfg)
    world = load_world(); done = failed = 0
    output = data_root()
    (output / 'xml').mkdir(parents=True, exist_ok=True); (output / 'truth').mkdir(parents=True, exist_ok=True)
    with connect() as db:
        sql = "SELECT * FROM cables WHERE state!='validated'" + ('' if retry_failed else " AND state!='failed'")
        args = []
        if cfg.get('max_cables') is not None:
            if type(cfg['max_cables']) is not int or cfg['max_cables'] <= 0:
                raise ValueError('max_cables must be a positive integer')
            sql += " AND CAST(substr(id,instr(id,'-')+1,6) AS INTEGER)<=?"
            args.append(cfg['max_cables'])
        sql += ' ORDER BY rowid'
        if limit:
            sql += ' LIMIT ?'; args.append(limit)
        rows = db.execute(sql, args).fetchall()
    provider = provider_from_config(cfg) if rows and cfg.get('provider', 'offline') not in ('offline', 'authored') else None
    for row in rows:
        c = Cable.model_validate_json(row['record'])
        try:
            with connect() as db:
                db.execute("UPDATE cables SET attempts=attempts+1 WHERE id=?", (c.cable_id,))
            if provider:
                c = render_narrative(c, world, provider, cfg, row['error'])
            else:
                authored = authored_narrative(c, cfg)
                c = authored or draft(c, world)
                check(c, world)
                with connect() as db:
                    db.execute("UPDATE cables SET state=? WHERE id=?", ('authored' if authored else 'critiqued', c.cable_id))
            xml = render(c)
            claims = (extract_claims(c, world, provider, cfg) if cfg.get('extraction') == 'model' else
                      [(p.number, f) for p in c.paragraphs for f in extract(p.text, world)])
            number = int(c.cable_id.split('-')[1]); stem = f'{number:04}-{c.report_date.year:06}'
            for path, content in [(output / f'xml/{stem}.xml', xml), (output / f'truth/{stem}.json', c.model_dump_json(indent=2).encode())]:
                temporary = path.with_suffix(path.suffix + '.tmp'); temporary.write_bytes(content); temporary.replace(path)
            with connect() as db:
                db.execute('DELETE FROM evidence WHERE cable=?', (c.cable_id,))
                marks = {p.number: p for p in c.paragraphs}
                for number, f in claims:
                    p = marks[number]
                    db.execute('INSERT OR IGNORE INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?)',
                               (c.cable_id, p.number, f.subject, f.predicate, f.object, str(f.date), str(f.until or ''), p.classification, ','.join(p.controls), c.agency))
                db.execute("UPDATE cables SET state='validated',record=?,error=NULL WHERE id=?", (c.model_dump_json(), c.cable_id))
            done += 1
        except Exception as exc:
            message = str(exc) if isinstance(exc, (ValueError, BudgetExceeded)) else type(exc).__name__
            with connect() as db:
                db.execute("UPDATE cables SET state='failed',error=? WHERE id=?", (message, c.cable_id))
            failed += 1
            if isinstance(exc, BudgetExceeded):
                return dict(validated=done, failed=failed, stopped='spend_cap')
            if provider and not isinstance(exc, ValueError):
                return dict(validated=done, failed=failed, stopped='provider_error')
    return dict(validated=done, failed=failed)


def score():
    truth = {Fact(**f).key() for f in json.loads((world_dir() / 'graph_truth.json').read_text())}
    with connect() as db:
        recovered = {tuple(r) for r in db.execute('SELECT DISTINCT subject,predicate,object,date,until_date FROM evidence')}
        planted, contradictions, corrections = set(), set(), 0
        for r in db.execute("SELECT record FROM cables WHERE state='validated'"):
            c = Cable.model_validate_json(r[0]); planted.update(f.key() for p in c.paragraphs for f in p.facts)
            if c.dispute:
                d = c.dispute; contradictions.add((d['subject'], d['predicate'], d['object'], d['reported_date']))
            corrections += bool(c.corrects)
        counts = dict(db.execute('SELECT state,count(*) FROM cables GROUP BY state').fetchall())
        settings_row = db.execute("SELECT value FROM metadata WHERE key='generation_settings'").fetchone()
        settings = json.loads(settings_row[0]) if settings_row else {}
    online = settings.get('provider', 'offline') not in ('offline', 'authored')
    with connect() as db:
        authored = db.execute("SELECT count(*) FROM cables WHERE state='validated' AND record LIKE '%\"authored\":true%'").fetchone()[0]
    tp = len(recovered & truth)
    disputed = {k for k in recovered if (k[0], k[1], k[2], k[3]) in contradictions}
    undisputed = recovered - disputed
    by_predicate = {}
    for predicate in sorted({k[1] for k in truth}):
        total = [k for k in truth if k[1] == predicate]
        by_predicate[predicate] = {'truth': len(total), 'recovered': len([k for k in total if k in recovered])}
    return dict(method=(f"{settings.get('provider')} narratives with {settings.get('extraction') or 'deterministic'} extraction" if online else 'Deterministic text-pattern extraction on templated offline narratives'),
                truth_edges=len(truth), planted_edges=len(planted), extracted_edges=len(recovered), true_positives=tp,
                precision=tp / len(recovered) if recovered else 0,
                precision_excluding_contradictions=len(undisputed & truth) / len(undisputed) if undisputed else 0,
                world_recall=tp / len(truth) if truth else 0, planted_recall=len(recovered & planted) / len(planted) if planted else 0,
                contradiction_edges=len(disputed), correction_cables=corrections, authored_narratives=authored, recall_by_predicate=by_predicate, states=counts,
                limitations=('Model-generated prose retains canonical fact-sentence anchors. Scores measure constrained extraction, not unrestricted real-world prose.' if online else
                             'Baseline only. The offline drafter and the extractor share one sentence grammar, so planted recall is high by construction. Deliberate contradictions are reported separately.'),
                schema_validated=(ROOT / 'schemas/pubs.xsd').exists())
