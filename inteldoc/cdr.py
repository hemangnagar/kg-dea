"""Synthetic call detail records from a partner agency, generated from the world and ingested as a second evidence source.

The world's identifiers (DEMO-TEL-nnnnn labels) are held by named people over dated windows, and about one in ten
changes hands. Calls are sampled around the world's events and among members of the same organization, always using
the label each person held at the time, so every record has a known true caller and callee. Ingestion resolves
labels to people by the holder windows and writes `called` edges with the record as provenance. The scorecard
compares the resolution with the truth, including on the numbers that changed hands.

Labels are deliberately non-dialable. No cell-site or location data is generated.
"""
import csv
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from .world import ROOT, load_world
from .store import connect, data_root

PROVIDER = 'FBI'
HANDLING = ('U', 'LES')  # classification, dissemination control
NOISE_PREFIX = 'DEMO-TEL-9'  # labels outside the world: unresolvable on purpose


def cdr_dir():
    return data_root() / 'cdr'


def holder_at(identifier, when):
    for h in identifier['holders']:
        if h['from'] <= when < h['to']:
            return h['person']
    return None


def generate(seed=42, count=14000, world=None, out=None):
    """Write <out>/fbi-cdr.csv (what the partner agency hands over) and <out>/fbi-cdr-truth.json (who really spoke)."""
    world = world or load_world()
    rng = random.Random(seed * 7 + 1)
    by_id = {e['id']: e for e in world['entities']}
    phones = [e for e in world['entities'] if e['kind'] == 'identifier' and 'TEL' in e['name']]
    people = [e for e in world['entities'] if e['kind'] == 'person']
    held = {}  # person -> phones
    for ph in phones:
        for h in ph['holders']:
            held.setdefault(h['person'], []).append(ph)

    def label_for(person_id, when):
        """The label this person held on that day; None if they held none, in which case no call is generated."""
        options = [ph for ph in held.get(person_id, []) if holder_at(ph, when) == person_id]
        return rng.choice(options)['name'] if options else None

    def alive(p, when):
        if p.get('death_date') and when > str(p['death_date']):
            return False
        if p.get('arrest_date') and when > str(p['arrest_date']):
            return bool(p.get('release_date')) and when >= str(p['release_date'])
        return True

    def member_at(p, org, when):
        return any(m['organization'] == org and m['from'] <= when < m['to'] for m in p.get('membership', []))

    records, truth = [], {}

    def add(day, a, b, kind):
        when = str(day)
        la, lb = label_for(a, when), label_for(b, when)
        if not la or not lb or la == lb:
            return
        start = datetime.combine(day, datetime.min.time()) + timedelta(seconds=rng.randrange(6 * 3600, 23 * 3600))
        rid = f'{len(records) + 1:06d}'
        records.append({'record_id': rid, 'provider': PROVIDER, 'handling': '//'.join(HANDLING), 'call_start': start.isoformat(timespec='seconds'),
                        'duration_seconds': rng.choice([20, 45, 70, 110, 180, 260, 400, 600, 900]), 'caller_label': la, 'callee_label': lb, 'call_type': kind})
        truth[rid] = {'caller': a, 'callee': b}

    # 1. Calls around events: the main participant speaks with the other participants in the week before and the day after.
    for e in world['events']:
        day = date.fromisoformat(e['date'])
        others = [p['id'] for p in e.get('participants', []) if p['id'].startswith(('p-', 'person-')) and p['id'] != e['person']]
        crew = [p['id'] for p in people if member_at(p, e['org'], e['date']) and alive(p, e['date']) and p['id'] != e['person']]
        others += rng.sample(crew, min(len(crew), 3))
        leader = next((f['subject'] for f in world['leadership'] if f['object'] == e['org'] and f['date'] <= e['date'] < f['until']), None)
        if leader and leader != e['person'] and rng.random() < 0.8:
            others.append(leader)  # the boss is in the loop around most events
        for other in dict.fromkeys(others):
            for _ in range(rng.randint(2, 5)):
                when = day + timedelta(days=rng.randint(-7, 1))
                a, b = (e['person'], other) if rng.random() < 0.6 else (other, e['person'])
                add(when, a, b, 'event-related')
    # 2. Handover coverage: every shared number gets calls on both sides of the change of hands.
    for ph in phones:
        if len(ph['holders']) > 1:
            for h in ph['holders']:
                lo, hi = date.fromisoformat(h['from']), date.fromisoformat(min(h['to'], '2026-10-31'))
                if hi <= lo:
                    continue
                holder = by_id[h['person']]
                crew = [p['id'] for p in people if p['organization'] == holder['organization'] and p['id'] != holder['id']]
                for _ in range(3):
                    when = lo + timedelta(days=rng.randrange((hi - lo).days))
                    other = rng.choice(crew)
                    add(when, holder['id'], other, 'routine') if rng.random() < 0.5 else add(when, other, holder['id'], 'routine')
    # 2b. Stale use: for a share of handed-over phones the previous holder keeps using the number for a few weeks.
    for ph in phones:
        for prev, nxt in zip(ph['holders'], ph['holders'][1:]):
            if rng.random() < 0.5:
                continue
            holder = by_id[prev['person']]
            crew = [p['id'] for p in people if p['organization'] == holder['organization'] and p['id'] != holder['id']]
            for _ in range(rng.randint(1, 3)):
                when = date.fromisoformat(nxt['from']) + timedelta(days=rng.randrange(1, 30))
                other = rng.choice(crew)
                lb = label_for(other, str(when))
                if not lb or lb == ph['name']:
                    continue
                begin = datetime.combine(when, datetime.min.time()) + timedelta(seconds=rng.randrange(6 * 3600, 23 * 3600))
                rid = f'{len(records) + 1:06d}'
                records.append({'record_id': rid, 'provider': PROVIDER, 'handling': '//'.join(HANDLING), 'call_start': begin.isoformat(timespec='seconds'),
                                'duration_seconds': rng.choice([20, 45, 70, 110]), 'caller_label': ph['name'], 'callee_label': lb, 'call_type': 'routine'})
                truth[rid] = {'caller': holder['id'], 'callee': other}
    # 3. Routine calls among members of the same organization.
    start, end = date(2010, 3, 14), date(2026, 10, 31)
    attempts = 0
    while len(records) < count - count // 7 and attempts < count * 20:
        attempts += 1
        when = start + timedelta(days=rng.randrange((end - start).days))
        a = rng.choice(people)
        if not alive(a, str(when)) or not label_for(a['id'], str(when)):
            continue
        crew = [p for p in people if p['id'] != a['id'] and member_at(p, a['organization'], str(when)) and alive(p, str(when))]
        if not crew:
            continue
        add(when, a['id'], rng.choice(crew)['id'], 'routine')
    # 4. Noise: calls to and from labels the world does not know (wrong numbers, unrelated subscribers).
    attempts = 0
    while len(records) < count and attempts < count * 20:
        attempts += 1
        when = start + timedelta(days=rng.randrange((end - start).days))
        a = rng.choice(people)
        la = label_for(a['id'], str(when))
        if not la:
            continue
        unknown = f'{NOISE_PREFIX}{rng.randrange(10000, 99999)}'
        rid = f'{len(records) + 1:06d}'
        caller, callee = (la, unknown) if rng.random() < 0.5 else (unknown, la)
        begin = datetime.combine(when, datetime.min.time()) + timedelta(seconds=rng.randrange(6 * 3600, 23 * 3600))
        records.append({'record_id': rid, 'provider': PROVIDER, 'handling': '//'.join(HANDLING), 'call_start': begin.isoformat(timespec='seconds'),
                        'duration_seconds': rng.choice([5, 12, 30, 60]), 'caller_label': caller, 'callee_label': callee, 'call_type': 'unrelated'})
        truth[rid] = {'caller': a['id'] if caller == la else None, 'callee': a['id'] if callee == la else None}
    records.sort(key=lambda r: r['call_start'])
    out = Path(out) if out else cdr_dir()
    out.mkdir(parents=True, exist_ok=True)
    with open(out / 'fbi-cdr.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['record_id', 'provider', 'handling', 'call_start', 'duration_seconds', 'caller_label', 'callee_label', 'call_type'])
        w.writeheader(); w.writerows(records)
    (out / 'fbi-cdr-truth.json').write_text(json.dumps(truth, indent=0))
    return {'records': len(records), 'path': str(out / 'fbi-cdr.csv')}


def resolve(label, when, phones_by_name):
    """Label -> (person, holder window) by the dated holder windows; None for unknown labels or times outside every window."""
    ph = phones_by_name.get(label)
    if not ph:
        return None, None
    for h in ph['holders']:
        if h['from'] <= when < h['to']:
            return h['person'], h
    return None, None


def ingest(path=None, world=None):
    """Load the partner CSV, resolve each record, store it, and write `called` edges into the evidence table."""
    world = world or load_world()
    path = Path(path) if path else cdr_dir() / 'fbi-cdr.csv'
    phones = {e['name']: e for e in world['entities'] if e['kind'] == 'identifier'}
    with open(path, newline='') as f:
        rows = list(csv.DictReader(f))
    with connect() as db:
        db.execute("DELETE FROM evidence WHERE cable LIKE 'FBI-CDR-%'")
        db.execute('DELETE FROM cdr')
        resolved = 0
        for r in rows:
            day = r['call_start'][:10]
            caller, cw = resolve(r['caller_label'], day, phones)
            callee, ew = resolve(r['callee_label'], day, phones)
            classification, controls = r['handling'].split('//', 1) if '//' in r['handling'] else (r['handling'], '')
            db.execute('INSERT INTO cdr VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                       (r['record_id'], r['provider'], r['call_start'], int(r['duration_seconds']), r['caller_label'], r['callee_label'], r['call_type'],
                        caller, callee, json.dumps(cw) if cw else None, json.dumps(ew) if ew else None, r['handling']))
            if caller and callee:
                resolved += 1
                db.execute('INSERT OR IGNORE INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?)',
                           (f"FBI-CDR-{r['record_id']}", 0, caller, 'called', callee, day, '', classification, controls, r['provider']))
    return {'records': len(rows), 'resolved_both_parties': resolved}


def score():
    """Resolution accuracy against the generator's truth, overall and on the numbers that changed hands; a naive baseline for contrast."""
    truth_path = cdr_dir() / 'fbi-cdr-truth.json'
    if not truth_path.exists():
        return None
    truth = json.loads(truth_path.read_text())
    world = load_world()
    phones = {e['name']: e for e in world['entities'] if e['kind'] == 'identifier'}
    shared = {name for name, e in phones.items() if len(e['holders']) > 1}
    with connect() as db:
        rows = db.execute('SELECT record_id,caller_label,callee_label,caller_person,callee_person FROM cdr').fetchall()
    if not rows:
        return None
    total = correct = shared_total = shared_correct = naive_correct = unresolved = 0
    for rid, la, lb, pa, pb in rows:
        t = truth.get(rid)
        if t is None:
            continue
        total += 1
        ok = (pa == t['caller'] and pb == t['callee'])
        correct += ok
        if la in shared or lb in shared:
            shared_total += 1; shared_correct += ok
        # Naive baseline: a label always belongs to its first known holder.
        first = lambda label: phones[label]['holders'][0]['person'] if label in phones else None
        naive_correct += (first(la) == t['caller'] and first(lb) == t['callee'])
        unresolved += (pa is None or pb is None)
    return {'provider': PROVIDER, 'handling': '//'.join(HANDLING), 'records': total, 'unresolved_records': unresolved,
            'resolution_accuracy': correct / total if total else 0,
            'shared_number_records': shared_total, 'shared_number_accuracy': shared_correct / shared_total if shared_total else 0,
            'naive_first_holder_accuracy': naive_correct / total if total else 0,
            'call_edges': db_count(), 'method': 'Labels resolved to people by dated holder windows; a call becomes a called edge only when both parties resolve.'}


def db_count():
    with connect() as db:
        return db.execute("SELECT count(DISTINCT subject||predicate||object||date) FROM evidence WHERE predicate='called'").fetchone()[0]


def corroboration(people, event_date, window_before=7, window_after=1):
    """Calls between the given people within a window around an event date: the fusion the demo shows."""
    people = sorted(set(people))
    if len(people) < 2:
        return []
    lo = str(date.fromisoformat(event_date) - timedelta(days=window_before)); hi = str(date.fromisoformat(event_date) + timedelta(days=window_after))
    out = []
    with connect() as db:
        for i, a in enumerate(people):
            for b in people[i + 1:]:
                calls = db.execute("SELECT record_id,call_start,duration_seconds,caller_person FROM cdr WHERE ((caller_person=? AND callee_person=?) OR (caller_person=? AND callee_person=?)) AND substr(call_start,1,10) BETWEEN ? AND ? ORDER BY call_start",
                                   (a, b, b, a, lo, hi)).fetchall()
                if calls:
                    out.append({'a': a, 'b': b, 'count': len(calls), 'from': lo, 'to': hi,
                                'records': [{'record_id': c[0], 'call_start': c[1], 'duration_seconds': c[2], 'caller': c[3]} for c in calls[:5]]})
    return out
