import json
from pathlib import Path
import re
from functools import lru_cache
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response, PlainTextResponse
from pydantic import BaseModel, Field
from .world import ROOT, load_world
from .store import connect, connect_spend
from .models import Cable
from .pipeline import score
from .xmlio import render
from .settings import load_config
from .providers import provider_from_config, BudgetExceeded
from .llm import answer_question
from . import auth, marks, narrate
import os

app=FastAPI(title='Knowledge Graph / Synthetic intelligence workbench',version='0.1.0')
auth.install(app)
Persona=Literal['secret','unclassified']

@lru_cache
def world():return load_world()
@lru_cache
def entities():return {e['id']:e for e in world()['entities']}

def visible(persona):
    with connect() as db:
        rows=[dict(r) for r in db.execute("SELECT * FROM evidence").fetchall()]
    # Runtime re-marks (demo control) apply before the persona filter, so a downgraded paragraph becomes visible
    # and an upgraded one disappears for the Unclassified persona. Both demo personas share agency NTK profiles;
    # partner data under LES handling is modelled as unavailable to the Unclassified // FOUO demo persona.
    rows=marks.apply(rows)
    if persona=='unclassified':
        rows=[r for r in rows if r['classification']=='U' and 'LES' not in (r['controls'] or '')]
    return rows

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
        if key not in grouped:grouped[key]={**r,'citations':[],'count':0,'agencies':[]}
        item=grouped[key]
        citation={'cable':r['cable'],'paragraph':r['paragraph'],'mark':r['classification']+('//'+r['controls'].replace(',','//') if r['controls'] else '')}
        item['count']+=1
        if r['agency'] not in item['agencies']:item['agencies'].append(r['agency'])
        if len(item['citations'])<3 and citation not in item['citations']:item['citations'].append(citation)
    return list(grouped.values())[:limit]

@app.get('/',response_class=HTMLResponse)
def home():return (Path(__file__).parent/'static/index.html').read_text()  # package-relative, independent of the data ROOT

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

def retrieve(body:Question):
    """Deterministic two-hop retrieval shared by the Investigate and Workspace pages."""
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
    if any(t in text for t in ['call','called','calls','phone','spoke']):selected=[r for r in (rows if ids else selected) if r['predicate']=='called' and (not ids or r['subject'] in ids or r['object'] in ids)]
    facts=compact(selected,24)
    ambiguity=len(matches)>1 and not body.entity_id and any(len([e for e in matches if alias in e['aliases']])>1 for entity in matches for alias in entity['aliases'] if alias.casefold() in text)
    if ambiguity:facts=[]
    summary=('This alias identifies more than one fictional person. Select an entity below to disambiguate.' if ambiguity else f'Found {len(facts)} supported relationships in the accessible reporting. Each statement below links to its original paragraph.' if facts else 'No supported relationships were found in the accessible reporting. Try a canonical entity name, place, or a sample question.')
    return {'summary':summary,'facts':facts,'entities':matches,'related_entities':[entities()[id] for id in sorted({f[k] for f in facts for k in ['subject','object']})],'ambiguous':ambiguity,'allowed':allowed}

@app.post('/api/query')
def query(body:Question):
    r=retrieve(body); facts,matches,ambiguity,allowed,summary=r['facts'],r['entities'],r['ambiguous'],r['allowed'],r['summary']
    answer=[]
    mode='Deterministic graph retrieval · 2 hops · offline answer'
    cfg=load_config()
    query_provider=cfg.get('query_provider','offline')
    if query_provider not in ('offline','authored') and facts and not ambiguity:
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
    return {'summary':summary,'answer':answer,'facts':facts,'entities':matches,'related_entities':r['related_entities'],'ambiguous':ambiguity,'mode':mode,'persona':body.persona}

def brief_provider(cfg):
    """The model that writes workspace briefs: anthropic when a key is present (or brief_provider says so), else none."""
    choice=cfg.get('brief_provider','auto')
    key_env=cfg.get('anthropic_key_env','CORPUSCLE_ANTHROPIC_KEY')
    if choice=='offline' or (choice=='auto' and not (os.getenv(key_env) or os.getenv('ANTHROPIC_API_KEY'))):return None,None
    settings={**cfg,'provider':'anthropic','anthropic_model':cfg.get('anthropic_model') or 'claude-haiku-5-5',
              'input_usd_per_million':cfg.get('input_usd_per_million') or 0.10,'output_usd_per_million':cfg.get('output_usd_per_million') or 0.50,
              'max_spend_usd':cfg.get('brief_spend_cap_usd',25),'anthropic_key_env':key_env,'anthropic_effort':'low','anthropic_thinking':'disabled'}
    return provider_from_config(settings),settings

BRIEFS={}

@app.post('/api/brief')
def brief(body:Question):
    """Workspace answer: plain-English paragraphs, each backed by the facts (and citations) it was written from, plus the raw data behind them."""
    r=retrieve(body); facts=r['facts']
    names={**entities()}
    cited=[c for f in facts for c in f['citations']]
    cable_ids=sorted({c['cable'] for c in cited if not c['cable'].startswith('FBI-CDR-')})
    call_ids=sorted({c['cable'] for c in cited if c['cable'].startswith('FBI-CDR-')})
    agencies=sorted({a for f in facts for a in f['agencies']})
    cables=[]
    if cable_ids:
        with connect() as db:
            for cid in cable_ids:
                row=db.execute("SELECT record FROM cables WHERE id=? AND state='validated'",(cid,)).fetchone()
                if not row:continue
                c=Cable.model_validate_json(row[0])
                open_doc=body.persona=='secret' or c.classification=='U'
                cables.append({'id':cid,'agency':c.agency,'date':str(c.report_date),'subject':c.subject if open_doc else 'Accessible portion of synthetic reporting','paragraphs':len(c.paragraphs),'classification':c.classification})
    # Partner call records for the raw-data view: those cited by the facts, plus calls among the people behind the
    # answer (people named in the facts and participants of its events), within the question's years when it names any.
    call_records=[]
    if body.persona=='secret' and facts:
        by_event={e['id']:e for e in world()['events']}
        people=set()
        for f in facts:
            for k in ('subject','object'):
                e=entities()[f[k]]
                if e['kind']=='person':people.add(e['id'])
                elif e['kind']=='event':people|={x['id'] for x in by_event.get(e['id'],{}).get('participants',[]) if entities().get(x['id'],{}).get('kind')=='person'}
        years=re.findall(r'\b(?:201\d|202[0-7])\b',body.question)
        lo,hi=(min(years)+'-01-01',max(years)+'-12-31T23:59:59') if years else ('0000','9999')
        cited_ids={c.replace('FBI-CDR-','') for c in call_ids}
        with connect() as db:
            rows=[]; total_related=0
            if people:
                q=','.join('?'*len(people))
                # Calls among the people behind the answer; when only one person is involved, that person's calls.
                where=(f'caller_person IN ({q}) AND callee_person IN ({q})' if len(people)>1 else f'(caller_person IN ({q}) OR callee_person IN ({q}))')+" AND caller_person IS NOT NULL AND callee_person IS NOT NULL AND call_start BETWEEN ? AND ?"
                args=list(people)*2+[lo,hi]
                total_related=db.execute(f'SELECT count(*) FROM cdr WHERE {where}',args).fetchone()[0]
                rows=db.execute(f'SELECT record_id,call_start,duration_seconds,caller_person,callee_person FROM cdr WHERE {where} ORDER BY call_start DESC LIMIT 300',args).fetchall()
            if cited_ids:
                q=','.join('?'*len(cited_ids))
                rows=list(db.execute(f'SELECT record_id,call_start,duration_seconds,caller_person,callee_person FROM cdr WHERE record_id IN ({q})',list(cited_ids)).fetchall())+[x for x in rows if x['record_id'] not in cited_ids]
        for row in rows:
            call_records.append({'id':'FBI-CDR-'+row['record_id'],'call_start':row['call_start'],'duration_seconds':row['duration_seconds'],'caller':row['caller_person'],'caller_name':entities()[row['caller_person']]['name'],'callee':row['callee_person'],'callee_name':entities()[row['callee_person']]['name'],'cited':row['record_id'] in cited_ids})
    paragraphs=[]; mode='Composed from the graph facts'; model=None
    if facts and not r['ambiguous']:
        cfg=load_config(); provider,settings=brief_provider(cfg)
        key=(body.question.strip().casefold(),body.persona,marks.version(),bool(provider))
        if key in BRIEFS:
            paragraphs,mode,model=BRIEFS[key]
        else:
            if provider is not None:
                try:
                    paragraphs=narrate.write(body.question,facts,names,body.persona,provider,settings)
                    model=settings['anthropic_model']; mode=f'Written by {model} from the graph facts, checked against them'
                except BudgetExceeded:
                    mode='Model spend cap reached; composed from the graph facts instead'
                except Exception as e:
                    mode=f'Model brief unavailable ({type(e).__name__}); composed from the graph facts instead'
            if not paragraphs:
                paragraphs=narrate.compose(body.question,facts,names,body.persona,len(cable_ids),agencies,len(call_ids))
            if len(BRIEFS)>500:BRIEFS.clear()
            BRIEFS[key]=(paragraphs,mode,model)
    related=[r for r in call_records if not r['cited']]
    if related and not any(f['predicate']=='called' for f in facts):
        names_in=sorted({n for r in related for n in (r['caller_name'],r['callee_name'])})
        dates=sorted(r['call_start'][:10] for r in related)
        total=max(total_related,len(related)); span=f'between {dates[0]} and {dates[-1]}' if dates[0]!=dates[-1] else f'on {dates[0]}'
        paragraphs=paragraphs+[{'title':'Partner call records','text':f'Separately, FBI call records (U//LES) hold {total} call{"s" if total!=1 else ""} {"among" if len(people)>1 else "involving"} the people connected to this answer{" in the years the question names" if years else ""}, {span}: {", ".join(names_in[:8])}{", and others" if len(names_in)>8 else ""}. {"The " + str(len(related)) + " most recent are" if total>len(related) else "They are"} listed under Call records.','facts':[],'citations':[{'cable':r['id'],'paragraph':0,'mark':'U//LES'} for r in related[:3]]}]
    for p in paragraphs:
        seen=[]
        for i in p['facts']:
            for c in facts[i]['citations']:
                if c not in seen:seen.append(c)
        p['citations']=seen[:8]
    return {'question':body.question,'persona':body.persona,'summary':r['summary'],'paragraphs':paragraphs,'facts':facts,'entities':r['entities'],'related_entities':r['related_entities'],'ambiguous':r['ambiguous'],
            'cables':cables,'call_records':call_records,'agencies':agencies,'mode':mode,'model':model,'remarked':len(marks.overrides())}

class MarkChange(BaseModel):
    cable:str=Field(min_length=1,max_length=80)
    paragraph:int=Field(ge=1,le=50)
    classification:Literal['S','U']
    persona:Persona='secret'

@app.get('/api/marks')
def list_marks():return {'overrides':marks.listing()}

@app.post('/api/marks')
def set_mark(body:MarkChange):
    if body.persona!='secret':raise HTTPException(403,'Only the Secret // NOFORN persona may change portion marks in this demo')
    try:classification,controls=marks.set_mark(body.cable,body.paragraph,body.classification)
    except KeyError:raise HTTPException(404,'No such paragraph')
    BRIEFS.clear()
    return {'cable':body.cable,'paragraph':body.paragraph,'mark':marks.mark_text(classification,controls),'overrides':marks.listing()}

@app.delete('/api/marks')
def reset_marks(persona:Persona='secret'):
    if persona!='secret':raise HTTPException(403,'Only the Secret // NOFORN persona may change portion marks in this demo')
    marks.clear(); BRIEFS.clear()
    return {'overrides':[]}

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
    c=Cable.model_validate_json(r[0])
    current=marks.overrides(); remarked=set()
    for p in c.paragraphs:
        if (id,p.number) in current:
            p.classification,p.controls=current[(id,p.number)][0],[x for x in current[(id,p.number)][1].split(',') if x]; remarked.add(p.number)
    document_class='S' if any(p.classification=='S' for p in c.paragraphs) else 'U'
    visible_p=[p for p in c.paragraphs if persona=='secret' or p.classification=='U']
    if not visible_p:raise HTTPException(404,'No accessible cable')
    calls=[]
    if persona=='secret':
        from .cdr import corroboration
        event=next((e for e in world()['events'] if e['id']==c.event_id),None)
        people=[i for p in visible_p for f in p.facts for i in [f.subject,f.object] if entities().get(i,{}).get('kind')=='person']
        for item in corroboration(people,event['date'] if event else str(c.report_date)):
            calls.append({**item,'a_name':entities()[item['a']]['name'],'b_name':entities()[item['b']]['name'],'records':[{**r,'caller_name':entities()[r['caller']]['name'] if r['caller'] in entities() else r['caller']} for r in item['records']]})
    open_doc=persona=='secret' or document_class=='U'
    return {'id':id,'agency':c.agency,'date':str(c.report_date),'subject':c.subject if open_doc else 'Accessible portion of synthetic reporting','place':c.place,'source':c.source_id if open_doc else 'Withheld','reliability':c.reliability if open_doc else 'Withheld','paragraphs':[{'number':p.number,'mark':p.mark,'classification':p.classification,'text':p.text,'remarked':p.number in remarked} for p in visible_p],'redacted':len(c.paragraphs)-len(visible_p),'synthetic':True,'corroborating_calls':calls,'remarkable':persona=='secret'}

@app.get('/api/cables/{id}/xml')
def xml(id:str,persona:Persona='secret'):
    with connect() as db:r=db.execute("SELECT record FROM cables WHERE id=? AND state='validated'",(id,)).fetchone()
    if not r:raise HTTPException(404)
    c=Cable.model_validate_json(r[0])
    if persona=='unclassified' and c.classification=='S':raise HTTPException(403,'Full XML contains inaccessible paragraphs')
    return Response(render(c),media_type='application/xml')

@app.get('/api/cdr/{record_id}')
def cdr_record(record_id:str,persona:Persona='secret'):
    if persona!='secret':raise HTTPException(403,'Partner call records carry LES handling and are not available to this persona')
    with connect() as db:r=db.execute('SELECT * FROM cdr WHERE record_id=?',(record_id.replace('FBI-CDR-',''),)).fetchone()
    if not r:raise HTTPException(404,'No such record')
    r=dict(r)
    def side(label,person,window):
        e=entities().get(person) if person else None
        return {'label':label,'person':person,'name':e['name'] if e else None,'kind':e['kind'] if e else None,'window':json.loads(window) if window else None}
    return {'record_id':r['record_id'],'provider':r['provider'],'handling':r['handling'],'call_start':r['call_start'],'duration_seconds':r['duration_seconds'],'call_type':r['call_type'],
            'caller':side(r['caller_label'],r['caller_person'],r['caller_window']),'callee':side(r['callee_label'],r['callee_person'],r['callee_window']),'synthetic':True}

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
    # The served corpus records how it was generated; that beats the serving config for the narrative labels.
    with connect() as db:
        row=db.execute("SELECT value FROM metadata WHERE key='generation_settings'").fetchone()
        authored=db.execute("SELECT count(*) FROM cables WHERE state='validated' AND record LIKE '%\"authored\":true%'").fetchone()[0]
    generated=json.loads(row[0]) if row else {}
    return {'query_provider':cfg.get('query_provider','offline'),
            'narrative_provider':generated.get('provider') or cfg.get('provider','offline'),
            'extraction':generated.get('extraction') or cfg.get('extraction','deterministic'),
            'authored':authored>0 or bool(cfg.get('narratives_dir')),'authored_count':authored,
            'generation_model':generated.get('anthropic_model') or generated.get('openai_model') or generated.get('ollama_model'),
            'model':cfg.get('openai_model') if cfg.get('query_provider')=='openai' else cfg.get('ollama_model')}


PREDICATE_GROUPS={'structure':['leads','member_of','controls','allied_with','split_from','owns','nominee_for'],
                  'events':['participated_in','linked_to','occurred_at','transited','supported','involved_in','arrested_in','killed_in','extradited_in','released_in','elected_in','removed_in','paid_in','designated_in'],
                  'identifiers':['uses'],'communications':['called']}

def filtered_rows(persona,predicates='',year_from=None,year_to=None,agencies='',kinds=''):
    rows=visible(persona)
    preds={x for x in predicates.split(',') if x}
    for group,members in PREDICATE_GROUPS.items():
        if group in preds:preds|=set(members)
    if preds:rows=[r for r in rows if r['predicate'] in preds]
    agency_set={x for x in agencies.split(',') if x}
    if agency_set:rows=[r for r in rows if r['agency'] in agency_set]
    if year_from or year_to:
        lo,hi=f'{year_from or 2010}-01-01',f'{year_to or 2027}-12-31'
        rows=[r for r in rows if r['date']<=hi and ((r['until_date']>lo) if r['until_date'] else (r['date']>=lo))]
    kind_set={x for x in kinds.split(',') if x}
    if kind_set:rows=[r for r in rows if entities()[r['subject']]['kind'] in kind_set and entities()[r['object']]['kind'] in kind_set]
    return rows

@app.get('/api/explore')
def explore_graph(persona:Persona='secret',center:str='',hops:int=1,predicates:str='',kinds:str='',year_from:int|None=None,year_to:int|None=None,agencies:str='',limit:int=300):
    """Persona-filtered subgraph for the explorer: deduplicated edges with citation counts, ranked around the centers."""
    hops=max(1,min(hops,3)); limit=max(10,min(limit,1500))
    rows=filtered_rows(persona,predicates,year_from,year_to,agencies,kinds)
    allowed={r[k] for r in visible(persona) for k in ['subject','object']}
    centers=[c for c in center.split(',') if c] if center else [e['id'] for e in entities().values() if e['kind']=='organization']
    centers=[c for c in centers if c in allowed]
    if center and not centers:raise HTTPException(404,'No accessible entity')
    selected=neighborhood(rows,centers,hops) if centers else rows
    if not selected and not center:selected=rows;touching_fallback=True  # e.g. calls never touch an organization: show the most-cited edges instead
    facts=compact(selected,10**6)
    touching=set(centers)
    facts.sort(key=lambda f:(not (f['subject'] in touching or f['object'] in touching),-f['count'],f['date']),reverse=False)
    unique=len(facts); truncated=unique>limit; facts=facts[:limit]
    degree={}
    for f in facts:
        for k in ['subject','object']:degree[f[k]]=degree.get(f[k],0)+1
    nodes=[{**entities()[i],'degree':degree[i],'center':i in touching} for i in sorted(degree)]
    return {'nodes':nodes,'edges':facts,'centers':centers,'total_edges':unique,'citations':len(selected),'truncated':truncated,'predicate_groups':PREDICATE_GROUPS}

@app.get('/api/export/graphml')
def export_graphml(persona:Persona='secret',predicates:str='',year_from:int|None=None,year_to:int|None=None,agencies:str=''):
    from lxml import etree as E
    facts=compact(filtered_rows(persona,predicates,year_from,year_to,agencies),10**6)
    ids=sorted({f[k] for f in facts for k in ['subject','object']})
    NS='http://graphml.graphdrawing.org/xmlns'
    root=E.Element('{%s}graphml'%NS,nsmap={None:NS})
    for key,for_,type_ in [('name','node','string'),('kind','node','string'),('place','node','string'),('predicate','edge','string'),('date','edge','string'),('until','edge','string'),('citations','edge','int'),('agencies','edge','string'),('classification','edge','string')]:
        E.SubElement(root,'{%s}key'%NS,id=key,attrib={'for':for_,'attr.name':key,'attr.type':type_})
    g=E.SubElement(root,'{%s}graph'%NS,id='inteldoc-'+persona,edgedefault='directed')
    for i in ids:
        e=entities()[i]; n=E.SubElement(g,'{%s}node'%NS,id=i)
        for key in ['name','kind','place']:E.SubElement(n,'{%s}data'%NS,key=key).text=str(e.get(key,''))
    for k,f in enumerate(facts):
        ed=E.SubElement(g,'{%s}edge'%NS,id=f'e{k}',source=f['subject'],target=f['object'])
        for key,val in [('predicate',f['predicate']),('date',f['date']),('until',f['until_date']),('citations',f['count']),('agencies',','.join(f['agencies'])),('classification',f['classification'])]:
            E.SubElement(ed,'{%s}data'%NS,key=key).text=str(val)
    return Response(E.tostring(root,xml_declaration=True,encoding='utf-8',pretty_print=True),media_type='application/xml',headers={'Content-Disposition':f'attachment; filename="inteldoc-{persona}.graphml"'})

@app.get('/api/export/edges.csv')
def export_edges(persona:Persona='secret',predicates:str='',year_from:int|None=None,year_to:int|None=None,agencies:str=''):
    import csv,io
    facts=compact(filtered_rows(persona,predicates,year_from,year_to,agencies),10**6)
    out=io.StringIO(); w=csv.writer(out)
    w.writerow([':START_ID','subject_name',':TYPE',':END_ID','object_name','date','until','citations:int','agencies','classification','sample_cable','sample_paragraph:int'])
    for f in facts:
        c=f['citations'][0]
        w.writerow([f['subject'],entities()[f['subject']]['name'],f['predicate'],f['object'],entities()[f['object']]['name'],f['date'],f['until_date'],f['count'],'|'.join(f['agencies']),f['classification'],c['cable'],c['paragraph']])
    return PlainTextResponse(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="inteldoc-{persona}-edges.csv"'})

@app.get('/api/export/nodes.csv')
def export_nodes(persona:Persona='secret'):
    import csv,io
    allowed={r[k] for r in visible(persona) for k in ['subject','object']}
    out=io.StringIO(); w=csv.writer(out)
    w.writerow(['id:ID','name',':LABEL','place','aliases'])
    for i in sorted(allowed):
        e=entities()[i]; w.writerow([i,e['name'],e['kind'],e['place'],'|'.join(e['aliases'])])
    return PlainTextResponse(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="inteldoc-{persona}-nodes.csv"'})
