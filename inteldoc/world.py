import json
import random
from datetime import date, timedelta
from pathlib import Path
import yaml
from .models import Fact

ROOT = Path(__file__).resolve().parents[1]

def expand(seed=42):
    rng = random.Random(seed)
    bible = yaml.safe_load((ROOT/'world/seed.yaml').read_text())
    entities = []
    def add(id, name, kind, place, aliases=None):
        entities.append(dict(id=id, name=name, kind=kind, place=place, aliases=aliases or []))
        return id
    for org in bible['organizations']:
        add(org['id'], org['name'], 'organization', org['base'])
    for i, place in enumerate(bible['places']):
        add(f'place-{i:02}', place, 'place', place)
    first = ['Aureliano', 'Teodoro', 'Leandro', 'Octavio', 'Silvano', 'Celestino', 'Dario', 'Nereo', 'Amador', 'Lisandro']
    last = ['Cendal', 'Velario', 'Monteluz', 'Solvante', 'Valmora', 'Calderiz', 'Rioluz', 'Terravela', 'Lunaverde', 'Boscareno', 'Altavela', 'Cobrizo', 'Vental', 'Nival', 'Sereno', 'Azur', 'Riscado', 'Piedral', 'Nebral', 'Olmaverde']
    for i in range(200):
        add(f'person-{i:03}', f'{first[i%10]} {last[i//10]}', 'person', bible['places'][i%25], [f'El Farol {i%40:02}', f'Operador {i:03}'])
    sectors = ['Transportes', 'Frutas', 'Cambio', 'Motores', 'Minerales', 'Hoteles', 'Servicios', 'Comercio']
    for i in range(80):
        add(f'company-{i:03}', f'{sectors[i%8]} Nube de Vidrio {i:03}', 'company', bible['places'][i%25])
    for i in range(45):
        add(f'asset-{i:03}', f'Unidad Prisma {i:03}', 'asset', bible['places'][i%25])
    for i in range(360):
        # Deliberately non-dialable/non-bank synthetic identifiers.
        add(f'contact-{i:03}', f'DEMO-{"TEL" if i%2 else "ACCT"}-{i:05}', 'identifier', bible['places'][i%25])
    agencies = ['DEA', 'FBI', 'HSI', 'CBP', 'DIA', 'TREASURY', 'OSINT']
    for i in range(50):
        add(f'source-{i:03}', f'SYN-{agencies[i%7]}-{i:03}', 'source', bible['places'][i%25])
    events, facts = [], []
    def fact(s,p,o,d,u=None):
        f = Fact(subject=s,predicate=p,object=o,date=d,until=u)
        facts.append(f.model_dump(mode='json'))
        return f.model_dump(mode='json')
    for j, org in enumerate(bible['organizations']):
        for n,(start,end) in enumerate([(2010,2012),(2012,2020),(2020,2027)]):
            fact(f'person-{j*40+n:03}', 'leads', org['id'], f'{start}-01-01', f'{end}-01-01')
        for beat in bible['arc_template']:
            events.append(dict(id=f'event-{len(events):04}',type=beat['type'],date=f"{beat['year']}-01-01",place=org['base'],org=org['id'],person=f'person-{j*40:03}',company=f'company-{j:03}',asset=f'asset-{j:03}',contact=f'contact-{j:03}',quantity=0))
    types = ['Shipment','Seizure','Meeting','Payment','Operation','Designation','Election']
    while len(events)<600:
        i=len(events); j=i%5
        d=date(2010,1,1)+timedelta(days=rng.randrange((date(2026,11,4)-date(2010,1,1)).days))
        events.append(dict(id=f'event-{i:04}',type=types[i%7],date=str(d),place=bible['places'][i%25],org=f'org-{j+1:02}',person=f'person-{j*40+3+i%37:03}',company=f'company-{i%80:03}',asset=f'asset-{i%45:03}',contact=f'contact-{i%360:03}',quantity=10+i%90))
    for e in events:
        add(e['id'], f"{e['type']} {e['id'].split('-')[1]}", 'event', e['place'])
        e['facts'] = [fact(e['person'],'participated_in',e['id'],e['date']),fact(e['org'],'linked_to',e['id'],e['date']),fact(e['company'],'supported',e['id'],e['date']),fact(e['person'],'uses',e['contact'],e['date']),fact(e['asset'],'involved_in',e['id'],e['date']),fact(e['id'],'occurred_at',f"place-{bible['places'].index(e['place']):02}",e['date'])]
    world=dict(seed=seed,status=bible['status'],entities=entities,events=events,leadership=facts[:15])
    validate_world(world)
    (ROOT/'world/expanded.json').write_text(json.dumps(world,indent=2))
    (ROOT/'world/graph_truth.json').write_text(json.dumps(facts,indent=2))
    return world

def validate_world(world):
    ids=[e['id'] for e in world['entities']]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate entity ID')
    known=set(ids)
    for e in world['events']:
        for f in e['facts']:
            if f['subject'] not in known or f['object'] not in known: raise ValueError('Dangling fact')
    windows={}
    for f in world['leadership']:
        for lo,hi in windows.setdefault(f['object'],[]):
            if f['date']<hi and f['until']>lo: raise ValueError('Overlapping leadership')
        windows[f['object']].append((f['date'],f['until']))

def load_world():
    path=ROOT/'world/expanded.json'
    return json.loads(path.read_text()) if path.exists() else expand()
