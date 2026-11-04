"""Integrity validation for the authored fictional seed. No network or model calls."""
from collections import Counter, defaultdict
from datetime import date
import unicodedata
import yaml
import re


def day(value):
    return date.fromisoformat(str(value))


def validate_seed(seed):
    groups=['organizations','corridors','people','companies','assets','sources','timeline']
    all_records=[row for group in groups for row in seed[group]]
    ids=[row['id'] for row in all_records]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate seed ID')
    if not all(re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*',id) for id in ids):
        raise ValueError('IDs must be kebab-case')
    from .world import ROOT
    blocklist=yaml.safe_load((ROOT/'config/blocklist.yaml').read_text())
    def norm(value):
        return ''.join(c for c in unicodedata.normalize('NFKD',value).casefold() if not unicodedata.combining(c))
    names=' '.join(row.get('name','') for row in all_records)+' '+' '.join(a for p in seed['people'] for a in p['aliases'])
    if any(norm(name) in norm(names) for name in blocklist['people']+blocklist['organizations']):
        raise ValueError('Blocklisted real name in seed')
    known=set(ids); people={p['id']:p for p in seed['people']}
    organizations={o['id']:o for o in seed['organizations']}
    timeline={e['id']:e for e in seed['timeline']}
    places=set(seed['places'])
    def ref(id):
        if id is not None and id not in known:raise ValueError('Dangling seed reference: '+str(id))
    def windows(rows, owner):
        periods=sorted((day(w['from']),day(w['to'])) for w in rows)
        for start,end in periods:
            if start>=end:raise ValueError('Invalid interval: '+owner)
        if any(left[1]>right[0] for left,right in zip(periods,periods[1:])):
            raise ValueError('Overlapping intervals: '+owner)
    if len(organizations)!=5:raise ValueError('Expected five organizations')
    if not 20<=len(seed['corridors'])<=30 or not 30<=len(timeline)<=40:raise ValueError('Seed scale')
    for p in people.values():
        ref(p['organization'])
        if not p['places'] or not set(p['places'])<=places:raise ValueError('Unknown/missing person geography')
        if not 2<=len(p['aliases'])<=4:raise ValueError('Alias count')
        for alias in p.get('alias_history',[]):
            ref(alias.get('inherited_from'))
            if alias['alias'] not in p['aliases'] or day(alias['from'])>=day(alias['to']):raise ValueError('Invalid alias history')
            if alias.get('inherited_from'):
                donor=people[alias['inherited_from']]
                fall=donor.get('death_date') or donor.get('arrest_date')
                if not fall or day(alias['from'])<day(fall) or alias['alias'] not in donor['aliases']:
                    raise ValueError('Invalid alias inheritance')
    tiers={p['tier'] for p in people.values()}
    if not {'boss','lieutenant','plaza-boss','sicario-chief','launderer','logistics','lawyer','corrupt-official'}<=tiers:raise ValueError('Missing people tier')
    if not {'police','customs','mayor','prosecutor','military'}<={p.get('official_role') for p in people.values()}:raise ValueError('Missing official roles')
    aliases=Counter(a for p in people.values() for a in p['aliases'])
    if sum(v>=2 for v in aliases.values())<5:raise ValueError('Expected shared aliases')
    if sum(bool(a.get('inherited_from')) for p in people.values() for a in p.get('alias_history',[]))<3:raise ValueError('Expected inherited aliases')
    for org in organizations.values():
        if org['base_city'] not in places:raise ValueError('Organization geography')
        if org['founding']['type'] not in ['new','split']:raise ValueError('Founding type')
        ref(org['founding'].get('split_from'))
        if not 3<=len(org['leadership'])<=5:raise ValueError('Expected 2-4 leadership changes')
        windows(org['leadership'],org['id'])
        for w in org['leadership']:
            ref(w['person']);p=people[w['person']]
            for key in ['arrest_date','death_date']:
                if p.get(key) and day(w['to'])>day(p[key]):raise ValueError('Leadership after incapacitation')
        if not org['fractures'] or not org['alliances']:raise ValueError('Missing organizational arc')
        for f in org['fractures']:
            ref(f['event']);ref(f['departing_leader']);ref(f['destination_org'])
            if timeline[f['event']]['type']!='Split' or str(timeline[f['event']]['date'])!=str(f['date']):raise ValueError('Fracture event mismatch')
        for a in org['alliances']:
            ref(a['with']);ref(a['formed_event']);ref(a['broken_event'])
            if day(a['from'])>=day(a['to']):raise ValueError('Alliance interval')
            if timeline[a['formed_event']]['type']!='Alliance' or timeline[a['broken_event']]['type']!='AllianceBreak':raise ValueError('Alliance event mismatch')
    for corridor in seed['corridors']:
        if not set(corridor['places'])<=places:raise ValueError('Corridor geography')
        windows(corridor['control_history'],corridor['id'])
        if len({w['organization'] for w in corridor['control_history']})<2:raise ValueError('Corridor must change control')
        for w in corridor['control_history']:ref(w['organization'])
    for e in timeline.values():
        ref(e['organization'])
        if e['place'] not in places or not 2010<=day(e['date']).year<=2026:raise ValueError('Timeline geography/date')
        for part in e['participants']:
            ref(part['id'])
            p=people.get(part['id'])
            if p:
                for key in ['arrest_date','death_date']:
                    if p.get(key) and day(e['date'])>day(p[key]) and e['type']!='Release':raise ValueError('Event after incapacitation')
    for row in seed['companies']:
        ref(row['owner']);ref(row.get('nominee'))
    for group in ['companies','assets','sources']:
        for row in seed[group]:
            if not row['places'] or not set(row['places'])<=places:raise ValueError('Unknown entity geography')
    counts=Counter(s['agency'] for s in seed['sources'])
    if set(counts)!={'DEA','FBI','HSI','CBP','DIA','TREASURY','OSINT'} or any(not 6<=n<=10 for n in counts.values()):raise ValueError('Agency source counts')
    if not 40<=len(people)<=60 or not 15<=len(seed['companies'])<=20 or not 10<=len(seed['assets'])<=15:raise ValueError('Seed entity scale')
    return {'people':len(people),'events':len(timeline),'sources':len(seed['sources']),'shared_aliases':sum(v>=2 for v in aliases.values())}
