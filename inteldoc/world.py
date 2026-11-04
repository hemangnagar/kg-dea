import json
import os
import random
from datetime import date, timedelta
from pathlib import Path
import yaml
from .models import Fact

ROOT = Path(__file__).resolve().parents[1]

def _expand_legacy(seed=42):
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

WORLD_DIR = Path(os.environ['INTELDOC_WORLD_DIR']).resolve() if os.getenv('INTELDOC_WORLD_DIR') else None

def world_dir():
    return WORLD_DIR or ROOT/'world'

def use_world_dir(path):
    global WORLD_DIR
    WORLD_DIR = Path(path).resolve()

def expand(seed=42):
    bible=yaml.safe_load((ROOT/'world/seed.yaml').read_text())
    if bible.get('schema_version')!=2:
        return _expand_legacy(seed)
    from .seed import validate_seed
    validate_seed(bible)
    rng=random.Random(seed)
    entities=[]
    def add(id,name,kind,place,aliases=None,**fields):
        entities.append(dict(id=id,name=name,kind=kind,place=place,aliases=aliases or [],**fields))
    for o in bible['organizations']:add(o['id'],o['name'],'organization',o['base_city'],founded_year=o['founded_year'])
    for i,place in enumerate(bible['places']):add(f'place-{i:02}',place,'place',place)
    for p in bible['people']:
        fields={k:v for k,v in p.items() if k not in ['id','name','places','aliases']}
        add(p['id'],p['name'],'person',p['places'][0],p['aliases'],**fields)
    for i in range(len(bible['people']),200):
        add(f'person-{i:03}',f'Operador Vitranelo {i:03}','person',bible['places'][i%25],
            [f'El Farol {i%40:02}',f'Operador Niebla {i:03}'],organization=f'org-{i%5+1:02}',
            tier=['logistics','lieutenant','launderer','plaza-boss'][i%4],arrest_date=None,death_date=None)
    for group,kind in [('companies','company'),('assets','asset'),('sources','source')]:
        for row in bible[group]:
            fields={k:v for k,v in row.items() if k not in ['id','name','places','kind']}
            if 'kind' in row:fields['asset_type']=row['kind']
            add(row['id'],row['name'],kind,row['places'][0],**fields)
    for i in range(len(bible['companies']),80):add(f'company-{i:03}',f'Casa Vitraleza {i:03}','company',bible['places'][i%25])
    for i in range(len(bible['assets']),45):add(f'asset-{i:03}',f'Unidad Nacarino {i:03}','asset',bible['places'][i%25],registration=f'DEMO-REG-{i:04}')
    for i in range(360):add(f'contact-{i:03}',f'DEMO-{ "TEL" if i%2 else "ACCT"}-{i:05}','identifier',bible['places'][i%25])
    for c in bible['corridors']:add(c['id'],c['name'],'corridor',c['places'][0],control_history=c['control_history'])
    people=[e for e in entities if e['kind']=='person']
    events=[]
    def alive(p,day):
        return all(not p.get(k) or day<=p[k] for k in ['arrest_date','death_date'])
    def event(id,type,day,place,org,person,i,**fields):
        return dict(id=id,type=type,date=day,place=place,org=org,person=person,
                    company=f'company-{i%80:03}',asset=f'asset-{i%45:03}',contact=f'contact-{i%360:03}',quantity=fields.pop('quantity',None),**fields)
    for i,e in enumerate(bible['timeline']):
        participants=e['participants']
        p=next((p['id'] for p in participants if p['id'].startswith('person-')),None)
        if p is None:p=next(p['id'] for p in people if p.get('organization')==e['organization'] and alive(p,e['date']))
        fields={k:v for k,v in e.items() if k not in ['id','type','date','place','organization']}
        events.append(event(f'event-{i:04}',e['type'],e['date'],e['place'],e['organization'],p,i,seed_event=e['id'],**fields))
    while len(events)<600:
        i=len(events);org=f'org-{i%5+1:02}'
        day=str(date(2010,1,1)+timedelta(days=rng.randrange((date(2026,11,4)-date(2010,1,1)).days)))
        candidates=[p for p in people if p.get('organization')==org and alive(p,day)]
        p=rng.choice(candidates)
        events.append(event(f'event-{i:04}',['Shipment','Seizure','Meeting','Payment','Operation','Designation','Election'][i%7],day,bible['places'][i%25],org,p['id'],i,
                            participants=[{'id':p['id'],'role':'reported-participant'},{'id':org,'role':'organization'}]))
    facts=[];leadership=[]
    def fact(s,p,o,d,u=None):
        f=Fact(subject=s,predicate=p,object=o,date=d,until=u).model_dump(mode='json');facts.append(f);return f
    for o in bible['organizations']:
        for w in o['leadership']:leadership.append(fact(w['person'],'leads',o['id'],w['from'],w['to']))
    for e in events:
        add(e['id'],f"{e['type']} {e['id'].split('-')[1]}",'event',e['place'])
        e['facts']=[fact(e['person'],'participated_in',e['id'],e['date']),fact(e['org'],'linked_to',e['id'],e['date']),
                    fact(e['company'],'supported',e['id'],e['date']),fact(e['person'],'uses',e['contact'],e['date']),
                    fact(e['asset'],'involved_in',e['id'],e['date']),fact(e['id'],'occurred_at',f"place-{bible['places'].index(e['place']):02}",e['date'])]
        for part in e.get('participants',[]):
            if part['id'] not in [e['person'],e['org']]:
                e['facts'].append(fact(part['id'],'linked_to' if part['id'].startswith('org-') else 'participated_in',e['id'],e['date']))
    world=dict(schema_version=2,seed=seed,status=bible['status'],entities=entities,events=events,leadership=leadership)
    validate_world(world)
    by_id={e['id']:e for e in entities}
    for e in events:
        for part in [{'id':e['person']}]+e.get('participants',[]):
            p=by_id[part['id']]
            if p['kind']=='person' and not alive(p,e['date']) and e['type']!='Release':raise ValueError('Expanded event after incapacitation')
    output=world_dir();output.mkdir(parents=True,exist_ok=True)
    (output/'expanded.json').write_text(json.dumps(world,indent=2))
    (output/'graph_truth.json').write_text(json.dumps(facts,indent=2))
    return world

def load_world():
    path=world_dir()/'expanded.json'
    return json.loads(path.read_text()) if path.exists() else expand()
