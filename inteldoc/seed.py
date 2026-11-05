"""Integrity validation for the hand-authored fictional seed (schema 3).

No network or model calls. These checks are structural: they prove the seed is
internally consistent, not that it has been editorially reviewed.
"""
from collections import Counter
from datetime import date
import re
import unicodedata
import yaml

SENTINEL = '2027-01-01'
TIERS = {'boss', 'lieutenant', 'plaza-boss', 'sicario-chief', 'launderer', 'logistics', 'lawyer', 'corrupt-official'}
OFFICIAL_ROLES = {'police', 'customs', 'mayor', 'prosecutor', 'military'}
AGENCIES = {'DEA', 'FBI', 'HSI', 'CBP', 'DIA', 'TREASURY', 'OSINT'}
EVENT_TYPES = {'Founding', 'Shipment', 'Seizure', 'Arrest', 'Extradition', 'Release', 'Killing', 'Meeting',
               'Payment', 'Operation', 'Designation', 'Election', 'Split', 'Alliance', 'AllianceBreak'}
ROLES = {'reported-participant', 'organization', 'counterparty', 'departing-leader', 'arrested', 'victim',
         'extradited', 'released', 'incoming-official', 'outgoing-official', 'payee', 'designated', 'company', 'asset'}
# Events an arrested (not dead) person may still appear in after the arrest date.
AFTER_ARREST = {'Extradition', 'Release', 'Designation'}


def day(value):
    return date.fromisoformat(str(value))


def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value).casefold() if not unicodedata.combining(c))


def fail(message):
    raise ValueError(message)


def windows(rows, owner, key_from='from', key_to='to'):
    periods = sorted((day(w[key_from]), day(w[key_to])) for w in rows)
    for start, end in periods:
        if start >= end:
            fail('Invalid interval: ' + owner)
    if any(left[1] > right[0] for left, right in zip(periods, periods[1:])):
        fail('Overlapping intervals: ' + owner)
    return periods


def fallen(person):
    """Date from which a person is incapacitated (arrest or death), or None."""
    dates = [day(person[k]) for k in ['arrest_date', 'death_date'] if person.get(k)]
    return min(dates) if dates else None


def validate_seed(seed):
    if seed.get('schema_version') != 3:
        fail('Expected seed schema_version 3')
    from .world import ROOT
    places = {p['id']: p for p in seed['geography']['places']}
    groups = ['organizations', 'corridors', 'people', 'companies', 'assets', 'sources', 'timeline']
    records = [row for group in groups for row in seed[group]] + list(places.values())
    ids = [row['id'] for row in records]
    if len(ids) != len(set(ids)):
        fail('Duplicate seed ID')
    if not all(re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*', i) for i in ids):
        fail('IDs must be kebab-case')
    names = [row['name'] for row in records]
    if len(names) != len(set(names)):
        fail('Duplicate entity name')
    blocklist = yaml.safe_load((ROOT / 'config/blocklist.yaml').read_text())
    text = norm(' '.join(names + [a for p in seed['people'] for a in p['aliases']]))
    for name in blocklist['people'] + blocklist['organizations']:
        if norm(name) in text:
            fail('Blocklisted real name in seed: ' + name)
    known = set(ids)
    people = {p['id']: p for p in seed['people']}
    organizations = {o['id']: o for o in seed['organizations']}
    timeline = {e['id']: e for e in seed['timeline']}

    def ref(value, kinds=None):
        if value is None:
            return
        if value not in known:
            fail('Dangling seed reference: ' + str(value))
        if kinds and not any(value.startswith(k) for k in kinds):
            fail('Reference of wrong kind: ' + value)

    def place_refs(values, owner):
        if not values or not set(values) <= set(places):
            fail('Unknown or missing geography: ' + owner)

    # --- geography ---------------------------------------------------------
    codes = [p['code'] for p in places.values()]
    if len(codes) != len(set(codes)):
        fail('Duplicate place code')
    for p in places.values():
        if p['kind'] not in {'port', 'border-crossing', 'city', 'hub', 'highway', 'region'} or p['country'] not in {'MX', 'US'}:
            fail('Place kind or country: ' + p['id'])

    # --- people ------------------------------------------------------------
    if not 40 <= len(people) <= 60:
        fail('Expected 40-60 people')
    for p in people.values():
        place_refs(p['places'], p['id'])
        if p['tier'] not in TIERS:
            fail('Unknown tier: ' + p['id'])
        if (p['tier'] == 'corrupt-official') != ('official_role' in p) or p.get('official_role', 'police') not in OFFICIAL_ROLES:
            fail('Official role mismatch: ' + p['id'])
        if not 2 <= len(p['aliases']) <= 4 or len(set(p['aliases'])) != len(p['aliases']):
            fail('Alias count: ' + p['id'])
        if not p.get('membership'):
            fail('Missing membership: ' + p['id'])
        windows(p['membership'], p['id'])
        for m in p['membership']:
            ref(m['organization'], ['org-'])
        fall = fallen(p)
        for key in ['arrest_date', 'death_date', 'extradition_date', 'release_date']:
            if p.get(key):
                day(p[key])
        if p.get('release_date') and (not p.get('arrest_date') or day(p['release_date']) <= day(p['arrest_date'])):
            fail('Release without earlier arrest: ' + p['id'])
        if p.get('extradition_date') and (not p.get('arrest_date') or day(p['extradition_date']) < day(p['arrest_date'])):
            fail('Extradition without earlier arrest: ' + p['id'])
        for m in p['membership']:
            end = day(m['to'])
            if fall and end > fall and not (p.get('release_date') and day(m['from']) >= day(p['release_date'])):
                fail('Membership after incapacitation: ' + p['id'])
        for alias in p.get('alias_history', []):
            if alias['alias'] not in p['aliases'] or day(alias['from']) >= day(alias['to']):
                fail('Invalid alias history: ' + p['id'])
            donor_id = alias.get('inherited_from')
            if donor_id:
                ref(donor_id, ['p-'])
                donor = people[donor_id]
                donor_fall = fallen(donor)
                if not donor_fall or day(alias['from']) < donor_fall or alias['alias'] not in donor['aliases']:
                    fail('Invalid alias inheritance: ' + p['id'])
    if not TIERS <= {p['tier'] for p in people.values()}:
        fail('Missing people tier')
    if not OFFICIAL_ROLES <= {p.get('official_role') for p in people.values()}:
        fail('Missing official roles')
    alias_count = Counter(a for p in people.values() for a in p['aliases'])
    shared = {a: n for a, n in alias_count.items() if n >= 2}
    if len(shared) < 5:
        fail('Expected at least five shared aliases')
    if any(n > 2 for n in shared.values()):
        fail('A shared alias must belong to exactly two people')
    inherited = [a for p in people.values() for a in p.get('alias_history', []) if a.get('inherited_from')]
    if len(inherited) < 3:
        fail('Expected at least three inherited aliases')

    # --- organizations -----------------------------------------------------
    if not 5 <= len(organizations) <= 6:
        fail('Expected five or six organizations')
    for org in organizations.values():
        place_refs([org['base']], org['id'])
        founding = org['founding']
        if founding['type'] not in ['new', 'split'] or (founding['type'] == 'split') != bool(founding.get('split_from')):
            fail('Founding type: ' + org['id'])
        ref(founding.get('split_from'), ['org-'])
        ref(founding['event'], ['beat-'])
        event = timeline[founding['event']]
        if str(event['date']) != str(org['founded']) or event['type'] not in {'Founding', 'Split'}:
            fail('Founding event mismatch: ' + org['id'])
        if not 1 <= len(org['leadership']) <= 5:
            fail('Expected one to five leadership windows: ' + org['id'])
        windows(org['leadership'], org['id'])
        if str(org['leadership'][0]['from']) != str(org['founded']):
            fail('Leadership must start at founding: ' + org['id'])
        for w in org['leadership']:
            ref(w['person'], ['p-'])
            person = people[w['person']]
            start, end = day(w['from']), day(w['to'])
            if not any(m['organization'] == org['id'] and day(m['from']) <= start and end <= day(m['to']) for m in person['membership']):
                fail('Leadership outside membership: ' + w['person'])
        if not org['alliances']:
            fail('Missing alliance: ' + org['id'])
        for f in org['fractures']:
            ref(f['event'], ['beat-']); ref(f['departing_leader'], ['p-']); ref(f['destination_org'], ['org-'])
            event = timeline[f['event']]
            if event['type'] != 'Split' or str(event['date']) != str(f['date']) or event['organization'] != org['id']:
                fail('Fracture event mismatch: ' + org['id'])
            leaver = people[f['departing_leader']]
            if not any(m['organization'] == org['id'] and str(m['to']) == str(f['date']) for m in leaver['membership']):
                fail('Departing leader membership does not end at the split: ' + f['departing_leader'])
            if not any(m['organization'] == f['destination_org'] and str(m['from']) == str(f['date']) for m in leaver['membership']):
                fail('Departing leader does not join the destination at the split: ' + f['departing_leader'])
        for a in org['alliances']:
            ref(a['with'], ['org-']); ref(a['formed_event'], ['beat-']); ref(a['broken_event'], ['beat-'])
            if day(a['from']) >= day(a['to']):
                fail('Alliance interval: ' + org['id'])
            formed, broken = timeline[a['formed_event']], timeline[a['broken_event']]
            if formed['type'] != 'Alliance' or broken['type'] != 'AllianceBreak':
                fail('Alliance event mismatch: ' + org['id'])
            if str(formed['date']) != str(a['from']) or str(broken['date']) != str(a['to']):
                fail('Alliance dates do not match events: ' + org['id'])
            partner = organizations[a['with']]
            if not any(b['with'] == org['id'] and str(b['from']) == str(a['from']) and str(b['to']) == str(a['to']) for b in partner['alliances']):
                fail('Alliance is not symmetric: ' + org['id'])

    # --- corridors ---------------------------------------------------------
    if not 20 <= len(seed['corridors']) <= 30:
        fail('Expected 20-30 corridors')
    for corridor in seed['corridors']:
        place_refs(corridor['places'], corridor['id'])
        place_refs(corridor['hubs'], corridor['id'])
        if corridor['kind'] not in {'plaza', 'route'} or not corridor.get('commodities'):
            fail('Corridor kind or commodities: ' + corridor['id'])
        periods = windows(corridor['control_history'], corridor['id'])
        if any(left[1] != right[0] for left, right in zip(periods, periods[1:])):
            fail('Control history must be contiguous: ' + corridor['id'])
        if len({w['organization'] for w in corridor['control_history']}) < 2:
            fail('Corridor must change control: ' + corridor['id'])
        for w in corridor['control_history']:
            ref(w['organization'], ['org-'])
            if day(w['from']) < day(organizations[w['organization']]['founded']):
                fail('Corridor controlled before organization existed: ' + corridor['id'])

    # --- companies, assets, sources ---------------------------------------
    if not 15 <= len(seed['companies']) <= 20:
        fail('Expected 15-20 companies')
    for row in seed['companies']:
        ref(row['owner'], ['p-']); ref(row.get('nominee'), ['p-'])
        place_refs(row['places'], row['id'])
        day(row['registered'])
        if row.get('nominee') == row['owner']:
            fail('Nominee equals owner: ' + row['id'])
    if not 10 <= len(seed['assets']) <= 15:
        fail('Expected 10-15 assets')
    for row in seed['assets']:
        ref(row['operator'], ['org-'])
        place_refs(row['places'], row['id'])
        if 'DEMO' not in row['registration']:
            fail('Asset registration must be marked DEMO: ' + row['id'])
    counts = Counter(s['agency'] for s in seed['sources'])
    if set(counts) != AGENCIES or any(not 6 <= n <= 10 for n in counts.values()):
        fail('Expected six to ten sources per agency')
    for row in seed['sources']:
        place_refs(row['places'], row['id'])
        if not re.fullmatch(r'[A-F][1-6]', row['reliability']):
            fail('Source reliability grade: ' + row['id'])

    # --- timeline ----------------------------------------------------------
    if not 30 <= len(timeline) <= 45:
        fail('Expected 30-45 timeline beats')
    for e in timeline.values():
        if e['type'] not in EVENT_TYPES:
            fail('Event type: ' + e['id'])
        ref(e['organization'], ['org-']); ref(e.get('corridor'), ['cor-'])
        place_refs([e['place']], e['id'])
        when = day(e['date'])
        if not 2010 <= when.year <= 2026:
            fail('Timeline date out of range: ' + e['id'])
        if when < day(organizations[e['organization']]['founded']):
            fail('Event before organization founding: ' + e['id'])
        if not e.get('name') or not e.get('description'):
            fail('Beat needs a name and description: ' + e['id'])
        if re.search(r'\b\d{4}-\d{2}-\d{2}\b', e['description']) or ' on 20' in e['description']:
            fail('Beat description must not contain dates: ' + e['id'])
        if e.get('quantity') and not (isinstance(e['quantity'].get('value'), (int, float)) and e['quantity'].get('unit') and e['quantity'].get('commodity')):
            fail('Quantity shape: ' + e['id'])
        roles = Counter(part['role'] for part in e['participants'])
        if roles['organization'] != 1 or not set(roles) <= ROLES:
            fail('Participant roles: ' + e['id'])
        for part in e['participants']:
            ref(part['id'])
            person = people.get(part['id'])
            if person:
                if person.get('death_date') and when > day(person['death_date']):
                    fail('Event after death: ' + e['id'])
                if person.get('arrest_date') and when > day(person['arrest_date']) and e['type'] not in AFTER_ARREST:
                    released = person.get('release_date') and when >= day(person['release_date'])
                    if not released:
                        fail('Event after arrest: ' + e['id'])
            if part['role'] == 'arrested' and str(person['arrest_date']) != str(e['date']):
                fail('Arrest date mismatch: ' + e['id'])
            if part['role'] == 'victim' and str(person['death_date']) != str(e['date']):
                fail('Death date mismatch: ' + e['id'])
            if part['role'] == 'extradited' and str(person['extradition_date']) != str(e['date']):
                fail('Extradition date mismatch: ' + e['id'])
            if part['role'] == 'released' and str(person['release_date']) != str(e['date']):
                fail('Release date mismatch: ' + e['id'])
    dates = [str(e['date']) for e in timeline.values()]
    if len(set(dates)) < len(dates) - 2:
        fail('Timeline beats cluster on identical dates')
    return {'people': len(people), 'organizations': len(organizations), 'corridors': len(seed['corridors']),
            'companies': len(seed['companies']), 'assets': len(seed['assets']), 'sources': len(seed['sources']),
            'events': len(timeline), 'shared_aliases': len(shared), 'inherited_aliases': len(inherited)}
