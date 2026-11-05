import json
import re
from functools import lru_cache
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel, Field
from .world import ROOT, load_world
from .store import connect, connect_spend
from .models import Cable
from .pipeline import score
from .xmlio import render
from .settings import load_config
from .providers import provider_from_config, BudgetExceeded
from .llm import answer_question

app=FastAPI(title='IntelDoc / Synthetic intelligence workbench',version='0.1.0')
Persona=Literal['secret','unclassified']

@lru_cache
def world():return load_world()
@lru_cache
def entities():return {e['id']:e for e in world()['entities']}

def visible(persona):
    with connect() as db:
        # Both demo personas share agency NTK profiles. No client-provided clearance or agency SQL.
        rows=db.execute("SELECT * FROM evidence"+(' WHERE classification=\'U\'' if persona=='unclassified' else '')).fetchall()
    return [dict(r) for r in rows]

def public_entity(id):return entities()[id]

def neighborhood(rows,ids,hops=2):
    reached=set(ids); selected=[]
    for _ in range(hops):
        nxt=[r for r in rows if r['subject'] in reached or r['object'] in reached]
        selected=nxt; reached|={r[k] for r in nxt for k in ['subject','object']}
    return selected

def compact(rows,limit=60):
    grouped={}
    for r in sorted(rows,key=lambda r:(r['date'],r['cable'],r['paragraph']),reverse=True):
        key=(r['subject'],r['predicate'],r['object'],r['date'],r['until_date'])
        if key not in grouped:grouped[key]={**r,'citations':[]}
        item=grouped[key]
        citation={'cable':r['cable'],'paragraph':r['paragraph'],'mark':r['classification']+('//'+r['controls'].replace(',','//') if r['controls'] else '')}
        if len(item['citations'])<3 and citation not in item['citations']:item['citations'].append(citation)
    return list(grouped.values())[:limit]

@app.get('/',response_class=HTMLResponse)
def home():return (ROOT/'inteldoc/static/index.html').read_text()

@app.get('/api/health')
def health():
    with connect() as db:n=db.execute("SELECT count(*) FROM cables WHERE state='validated'").fetchone()[0]
    return {'status':'ok' if n else 'empty','validated':n,'synthetic':True}

@app.get('/api/stats')
def stats(persona:Persona='secret'):
    rows=visible(persona)
    with connect() as db:
        states=dict(db.execute('SELECT state,count(*) FROM cables GROUP BY state'))
    with connect_spend() as db:
        spend=db.execute('SELECT COALESCE(sum(COALESCE(actual,reserved)),0) FROM spend').fetchone()[0]
    return {'documents':states.get('validated',0),'entities':len({r[k] for r in rows for k in ['subject','object']}),'facts':len(compact(rows,100000)),'states':states,'spend':round(spend,4),'events':len(world()['events'])}

@app.get('/api/entities')
def list_entities(q:str='',persona:Persona='secret'):
    allowed={r[k] for r in visible(persona) for k in ['subject','object']}
    return [e for e in entities().values() if e['id'] in allowed and (not q or q.casefold() in (e['name']+' '+' '.join(e['aliases'])).casefold())][:50]

class Question(BaseModel):
    question:str=Field(min_length=1,max_length=1000)
    persona:Persona='secret'
    entity_id:str|None=None

@app.post('/api/query')
def query(body:Question):
    rows=visible(body.persona)
    allowed={r[k] for r in rows for k in ['subject','object']}
    text=body.question.casefold()
    hits={}
    for e in entities().values():
        if e['id'] in allowed:
            found=[n for n in [e['name']]+e['aliases'] if n.casefold() in text]
            if found:hits[e['id']]=max(found,key=len)
    # Prefer the longest matching name: "Anzures Ibarra" must not also match the entity known only as "Anzures".
    matches=[entities()[id] for id,n in hits.items() if not any(o!=id and n.casefold()!=m.casefold() and n.casefold() in m.casefold() for o,m in hits.items())]
    if body.entity_id:
        matches=[entities()[body.entity_id]] if body.entity_id in allowed else []
    ids=[e['id'] for e in matches]
    years=re.findall(r'\b(?:201\d|202[0-7])\b',text)
    if years:
        lo,hi=min(years)+'-01-01',max(years)+'-12-31'
        rows=[r for r in rows if (r['date']<=hi and (r['until_date']>lo if r['until_date'] else r['date']>=lo))]
    if ids:
        selected=neighborhood(rows,ids,2)
    else:
        tokens=set(re.findall(r'[a-z]{4,}',text))-{'what','which','show','with','from','about','does','have','that','were','their','when','where'}
        selected=[r for r in rows if any(t in (entities()[r['subject']]['name']+' '+entities()[r['object']]['name']+' '+r['predicate']).casefold() for t in tokens)]
    if any(t in text for t in ['company','companies','front']):selected=[r for r in selected if any(entities()[r[k]]['kind']=='company' for k in ['subject','object'])]
    if any(t in text for t in ['leader','leads','led','leadership']):selected=[r for r in selected if r['predicate']=='leads']
    if any(t in text for t in ['corridor','plaza','crossing','route']):selected=[r for r in selected if any(entities()[r[k]]['kind']=='corridor' for k in ['subject','object'])]
    if any(t in text for t in ['control','controls','controlled']):selected=[r for r in selected if r['predicate']=='controls']
    if any(t in text for t in ['member','members','membership']):selected=[r for r in selected if r['predicate'] in ('member_of','leads')]
    if any(t in text for t in ['owner','owns','owned','nominee']):selected=[r for r in selected if r['predicate'] in ('owns','nominee_for')]
    facts=compact(selected,24)
    ambiguity=len(matches)>1 and not body.entity_id and any(len([e for e in matches if alias in e['aliases']])>1 for entity in matches for alias in entity['aliases'] if alias.casefold() in text)
    if ambiguity:facts=[]
    summary=('This alias identifies more than one fictional person. Select an entity below to disambiguate.' if ambiguity else f'Found {len(facts)} supported relationships in the accessible reporting. Each statement below links to its original paragraph.' if facts else 'No supported relationships were found in the accessible reporting. Try a canonical entity name, place, or a sample question.')
    answer=[]
    mode='Deterministic graph retrieval · 2 hops · offline answer'
    cfg=load_config()
    query_provider=cfg.get('query_provider','offline')
    if query_provider!='offline' and facts and not ambiguity:
        try:
            provider=provider_from_config({**cfg,'provider':query_provider})
            accessible_names={id:entities()[id] for id in allowed}
            answer=answer_question(body.question,facts,accessible_names,provider,cfg)
            mode=f'{query_provider} evidence selection · quote-verified citations'
            summary=('The model selected the following source-grounded answer.' if answer else
                     'The model found no answer supported by the retrieved evidence.')
        except BudgetExceeded:
            raise HTTPException(402,'Model spend cap reached; no unverified answer returned')
        except ValueError:
            raise HTTPException(502,'Model configuration or evidence validation failed; no unverified answer returned')
        except Exception:
            raise HTTPException(503,'Model provider unavailable; no unverified answer returned')
    return {'summary':summary,'answer':answer,'facts':facts,'entities':matches,'related_entities':[entities()[id] for id in sorted({f[k] for f in facts for k in ['subject','object']})],'ambiguous':ambiguity,'mode':mode,'persona':body.persona}

@app.get('/api/graph/{id}')
def graph(id:str,persona:Persona='secret'):
    rows=visible(persona); allowed={r[k] for r in rows for k in ['subject','object']}
    if id not in allowed:raise HTTPException(404,'No accessible entity')
    facts=compact(neighborhood(rows,[id],1),40)
    ids={r[k] for r in facts for k in ['subject','object']}|{id}
    return {'nodes':[public_entity(i) for i in sorted(ids)],'edges':facts,'center':id,'truncated':len(facts)==40}

@app.get('/api/timeline/{id}')
def timeline(id:str,persona:Persona='secret'):
    data=graph(id,persona)
    return sorted(data['edges'],key=lambda f:f['date'])

@app.get('/api/cables/{id}')
def cable(id:str,persona:Persona='secret'):
    with connect() as db:r=db.execute("SELECT record FROM cables WHERE id=? AND state='validated'",(id,)).fetchone()
    if not r:raise HTTPException(404,'No accessible cable')
    c=Cable.model_validate_json(r[0]); visible_p=[p for p in c.paragraphs if persona=='secret' or p.classification=='U']
    if not visible_p:raise HTTPException(404,'No accessible cable')
    return {'id':id,'agency':c.agency,'date':str(c.report_date),'subject':c.subject if persona=='secret' or c.classification=='U' else 'Accessible portion of synthetic reporting','place':c.place,'source':c.source_id if persona=='secret' or c.classification=='U' else 'Withheld','reliability':c.reliability if persona=='secret' or c.classification=='U' else 'Withheld','paragraphs':[{'number':p.number,'mark':p.mark,'text':p.text} for p in visible_p],'redacted':len(c.paragraphs)-len(visible_p),'synthetic':True}

@app.get('/api/cables/{id}/xml')
def xml(id:str,persona:Persona='secret'):
    with connect() as db:r=db.execute("SELECT record FROM cables WHERE id=? AND state='validated'",(id,)).fetchone()
    if not r:raise HTTPException(404)
    c=Cable.model_validate_json(r[0])
    if persona=='unclassified' and c.classification=='S':raise HTTPException(403,'Full XML contains inaccessible paragraphs')
    return Response(render(c),media_type='application/xml')

@app.get('/api/scorecard')
def scorecard():return score()

@app.get('/api/world')
def world_summary():
    w=world(); by_id=entities()
    organizations=[]
    for o in w['entities']:
        if o['kind']!='organization':continue
        organizations.append({'id':o['id'],'name':o['name'],'base':o['place'],'founded':o.get('founded'),'profile':o.get('profile',''),
            'leadership':[{'person':by_id[l['person']]['name'],'from':l['from'],'to':l['to'],'secret_only':bool(l.get('secret_only'))} for l in o.get('leadership',[])],
            'alliances':[{'with':by_id[a['with']]['name'],'from':a['from'],'to':a['to']} for a in o.get('alliances',[])],
            'fractures':[{'leader':by_id[f['departing_leader']]['name'],'to':by_id[f['destination_org']]['name'],'date':f['date']} for f in o.get('fractures',[])]})
    kinds={}
    for e in w['entities']:kinds[e['kind']]=kinds.get(e['kind'],0)+1
    return {'status':w.get('status'),'notes':w.get('notes',''),'organizations':organizations,'entity_counts':kinds,'events':len(w['events']),
            'authored_people':sum(1 for e in w['entities'] if e['kind']=='person' and e.get('authored')),
            'authored_events':sum(1 for e in w['events'] if e.get('seed_event')),
            'corridors':[{'name':c['name'],'kind':c.get('corridor_kind'),'places':c.get('places',[]),'control':[{'organization':by_id[x['organization']]['name'],'from':x['from'],'to':x['to']} for x in c.get('control_history',[])]} for c in w['entities'] if c['kind']=='corridor']}


@app.get('/api/runtime')
def runtime():
    cfg=load_config()
    return {'query_provider':cfg.get('query_provider','offline'),
            'narrative_provider':cfg.get('provider','offline'),
            'extraction':cfg.get('extraction','deterministic'),
            'model':cfg.get('openai_model') if cfg.get('query_provider')=='openai' else cfg.get('ollama_model')}
