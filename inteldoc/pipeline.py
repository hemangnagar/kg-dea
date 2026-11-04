import json
import random
import re
import unicodedata
from datetime import date, timedelta
import yaml
from .world import ROOT, load_world
from .models import Cable, Paragraph, Fact
from .store import connect
from .xmlio import render

VERBS={'participated_in':'participated in','linked_to':'was linked to','supported':'supported','uses':'used','involved_in':'was involved in','occurred_at':'occurred at','leads':'led'}
FILLER=('This fictional reporting is intended solely for a controlled demonstration of document processing. '
        'The reporting office distinguishes observed activity from analytical judgment and does not infer an additional relationship from a shared location. '
        'The source provided a limited account of the activity. Details outside that account remain unconfirmed. '
        'This paragraph should be evaluated with its stated handling controls and the original reporting context. '
        'Additional independent reporting would be required before drawing a broader conclusion about the network. '
        'The demonstration preserves the distinction between a recorded claim and a verified conclusion throughout the entire review and retrieval process. ')

def canonical(s):
    return ''.join(c for c in unicodedata.normalize('NFKD',s).casefold() if not unicodedata.combining(c))

def plan(count=5000,seed=42):
    world=load_world(); rng=random.Random(seed); cfg=yaml.safe_load((ROOT/'config/corpus.yaml').read_text())
    if cfg['provider']!='offline':raise ValueError('This pipeline supports offline generation only; provider adapters are not yet integrated')
    entities={e['id']:e for e in world['entities']}; agencies=list(cfg['agencies'])
    records=[]
    for i in range(count):
        e=world['events'][i%len(world['events'])]; agency=rng.choices(agencies,weights=list(cfg['agencies'].values()))[0]
        secret=agency!='OSINT' and rng.random()<cfg['secret_fraction']/0.9
        core=rng.random()<cfg['core_fraction']
        # Only narrative facts in each paragraph are assigned its portion mark.
        fs=[Fact(**f) for f in e['facts']] if core else []
        if core and not secret and int(e['id'].split('-')[1])%3==0:
            fs=fs[:2]  # Stable restricted details are absent from all public reporting for this event.
        if core:
            leader=next((f for f in world['leadership'] if f['object']==e['org'] and f['date']<=e['date']<f['until']),None)
            if leader and (secret or leader['date']<'2020-01-01'):fs.append(Fact(**leader))
        groups=[fs[:2],fs[2:4],fs[4:]]
        paragraphs=[]
        for j,facts in enumerate(groups):
            cls='S' if secret and j>0 else 'U'; controls=['NF'] if cls=='S' else ([] if secret or agency=='OSINT' else ['FOUO'])
            paragraphs.append(Paragraph(number=j+1,classification=cls,controls=controls,facts=facts))
        source_index=(agencies.index(agency)+7*(i%7))%50
        report=date.fromisoformat(e['date'])+timedelta(days=i%14)
        cable=Cable(cable_id=f'{agency}-{i+1:06}-IIR-{report.year%100:02}',agency=agency,office=f'{agency} Synthetic Reporting Office',report_date=report,subject=f'{e["type"]} reporting in {e["place"]}',event_id=e['id'],source_id=entities[f'source-{source_index:03}']['name'],reliability=['A2','B2','C3'][source_index%3],place=e['place'],keywords=[e['type'],e['place']],ntk=[agency],relevance='core' if core else 'background',paragraphs=paragraphs)
        records.append(cable)
    with connect() as db:
        identity=json.dumps(dict(count=count,seed=seed,world_seed=world['seed']))
        old=db.execute("SELECT value FROM metadata WHERE key='plan'").fetchone()
        if old and old[0]!=identity:raise ValueError('Existing manifest has a different plan. Use a separate corpus directory or remove generated corpus deliberately.')
        db.execute("INSERT OR IGNORE INTO metadata VALUES('plan',?)",(identity,))
        db.executemany('INSERT OR IGNORE INTO cables(id,state,record) VALUES(?,?,?)',[(c.cable_id,'planned',c.model_dump_json()) for c in records])
    return len(records)

def draft(cable,world):
    names={e['id']:e['name'] for e in world['entities']}
    for p in cable.paragraphs:
        sentences=[]
        for f in p.facts:
            suffix=f' until {f.until}' if f.until else ''
            sentences.append(f'{names[f.subject]} {VERBS[f.predicate]} {names[f.object]} on {f.date}{suffix}.')
        p.text=' '.join(sentences)+(' ' if sentences else '')+FILLER
    return cable

def check(cable,world):
    names={e['id']:e['name'] for e in world['entities']}
    blocked=yaml.safe_load((ROOT/'config/blocklist.yaml').read_text())
    combined=canonical(cable.subject+' '+' '.join(p.text for p in cable.paragraphs))
    for name in blocked['organizations']+blocked['people']:
        if canonical(name) in combined:raise ValueError('Blocklisted real name')
    if [p.number for p in cable.paragraphs]!=list(range(1,len(cable.paragraphs)+1)):raise ValueError('Paragraph numbering')
    if not 3<=len(cable.paragraphs)<=8:raise ValueError('Paragraph count')
    if not 250<=sum(len(p.text.split()) for p in cable.paragraphs)<=900:raise ValueError('Narrative word count')
    known_dates={str(f.date) for p in cable.paragraphs for f in p.facts}|{str(f.until) for p in cable.paragraphs for f in p.facts if f.until}
    allowed_names=set(names.values())|{cable.place}
    for p in cable.paragraphs:
        for f in p.facts:
            if names[f.subject] not in p.text or names[f.object] not in p.text or str(f.date) not in p.text:raise ValueError('Missing planted fact')
        for d in re.findall(r'\b\d{4}-\d{2}-\d{2}\b',p.text):
            if d not in known_dates:raise ValueError('Unplanned date')
        scrub=p.text
        for name in sorted(allowed_names,key=len,reverse=True):scrub=scrub.replace(name,'entity')
        if re.search(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b',scrub):raise ValueError('Unknown capitalized proper name')
    # Validate extracted claims exactly: catches changed relations, extra dates/quantities in the baseline grammar.
    extracted={f.key() for p in cable.paragraphs for f in extract(p.text,world)}
    expected={f.key() for p in cable.paragraphs for f in p.facts}
    if extracted!=expected:raise ValueError('Narrative relation mismatch')

def extract(text,world):
    # Independent text-only baseline. Never reads planted-fact arrays.
    names={e['name']:e['id'] for e in world['entities']}
    results=[]
    for predicate,verb in VERBS.items():
        pattern=r'([^.!?]+?) '+re.escape(verb)+r' (.+?) on (\d{4}-\d{2}-\d{2})(?: until (\d{4}-\d{2}-\d{2}))?\.'
        for m in re.finditer(pattern,text):
            left,right=m[1].strip(),m[2].strip()
            if left in names and right in names:results.append(Fact(subject=names[left],predicate=predicate,object=names[right],date=m[3],until=m[4]))
    return results

def run(limit=None,retry_failed=False):
    world=load_world(); done=failed=0
    (ROOT/'corpus/xml').mkdir(parents=True,exist_ok=True);(ROOT/'corpus/truth').mkdir(parents=True,exist_ok=True)
    with connect() as db:
        rows=db.execute("SELECT * FROM cables WHERE state!='validated'"+('' if retry_failed else " AND state!='failed'")+ ' ORDER BY id'+(' LIMIT ?' if limit else ''),(limit,) if limit else ()).fetchall()
    for row in rows:
        c=Cable.model_validate_json(row['record'])
        try:
            with connect() as db:db.execute("UPDATE cables SET state='drafted',attempts=attempts+1 WHERE id=?",(c.cable_id,))
            c=draft(c,world)
            check(c,world)
            with connect() as db:db.execute("UPDATE cables SET state='critiqued' WHERE id=?",(c.cable_id,))
            # Offline mode uses a deterministic checker; no LLM critique or revision is claimed.
            xml=render(c)
            number=int(c.cable_id.split('-')[1]); stem=f'{number:04}-{c.report_date.year:06}'
            (ROOT/f'corpus/xml/{stem}.xml').write_bytes(xml)
            (ROOT/f'corpus/truth/{stem}.json').write_text(c.model_dump_json(indent=2))
            with connect() as db:
                db.execute('DELETE FROM evidence WHERE cable=?',(c.cable_id,))
                for p in c.paragraphs:
                    for f in extract(p.text,world):db.execute('INSERT OR IGNORE INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?)',(c.cable_id,p.number,f.subject,f.predicate,f.object,str(f.date),str(f.until or ''),p.classification,','.join(p.controls),c.agency))
                db.execute("UPDATE cables SET state='validated',record=?,error=NULL WHERE id=?",(c.model_dump_json(),c.cable_id))
            done+=1
        except Exception as exc:
            with connect() as db:db.execute("UPDATE cables SET state='failed',error=? WHERE id=?",(str(exc),c.cable_id))
            failed+=1
    return dict(validated=done,failed=failed)

def score():
    truth={Fact(**f).key() for f in json.loads((ROOT/'world/graph_truth.json').read_text())}
    with connect() as db:
        recovered={tuple(r) for r in db.execute('SELECT DISTINCT subject,predicate,object,date,until_date FROM evidence')}
        planted=set()
        for r in db.execute("SELECT record FROM cables WHERE state='validated'"):
            c=Cable.model_validate_json(r[0]); planted.update(f.key() for p in c.paragraphs for f in p.facts)
        counts=dict(db.execute('SELECT state,count(*) FROM cables GROUP BY state').fetchall())
    tp=len(recovered&truth)
    return dict(method='Deterministic text-pattern extraction on templated offline narratives',truth_edges=len(truth),planted_edges=len(planted),extracted_edges=len(recovered),true_positives=tp,precision=tp/len(recovered) if recovered else 0,world_recall=tp/len(truth) if truth else 0,planted_recall=len(recovered&planted)/len(planted) if planted else 0,states=counts,limitations='Baseline only. Does not measure LLM extraction or generalization to independently authored prose.',schema_validated=(ROOT/'schemas/pubs.xsd').exists())
