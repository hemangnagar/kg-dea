import json
import shutil
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from lxml import etree
from inteldoc import world, store, pipeline, xmlio
from inteldoc.models import Cable, Paragraph
from inteldoc.providers import TokenAccountant, BudgetExceeded

@pytest.fixture
def corpus(tmp_path,monkeypatch):
    for directory in ['world','config','schemas']:
        (tmp_path/directory).mkdir()
    for name in ['world/seed.yaml','config/blocklist.yaml','config/corpus.yaml']:
        shutil.copy(world.ROOT/name,tmp_path/name)
    for module in [world,pipeline,xmlio]:monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(store,'DB',tmp_path/'corpus/manifest.sqlite')
    w=world.expand(42,total_events=120)
    pipeline.plan(120,42)
    outcome=pipeline.run()
    assert outcome=={'validated':120,'failed':0}
    return w,tmp_path

def test_resume_and_reproducibility(corpus):
    w,path=corpus
    first=(path/'corpus/xml').glob('*.xml')
    before={p.name:p.read_bytes() for p in first}
    pipeline.plan(120,42)
    assert pipeline.run()=={'validated':0,'failed':0}
    assert before=={p.name:p.read_bytes() for p in (path/'corpus/xml').glob('*.xml')}
    with pytest.raises(ValueError,match='different plan'):pipeline.plan(120,43)
    score=pipeline.score()
    assert score['precision_excluding_contradictions']==1 and score['planted_recall']==1
    assert score['contradiction_edges']>0 and score['precision']<1  # deliberate 5% contradictions are measured, not hidden
    assert 0<score['world_recall']<1 and set(score['recall_by_predicate'])>={'member_of','controls','owns','allied_with','leads'}

def test_xml_rollup_and_metadata(corpus):
    _,path=corpus
    seen=set()
    for p in (path/'corpus/xml').glob('*.xml'):
        doc=etree.parse(str(p)); root=doc.getroot(); cls=root.get(xmlio.q('ism:classification'));seen.add(cls)
        for tag in ['pubs:DocumentBody','pubs:PreformattedText']:
            el=root.find('.//'+xmlio.q(tag));assert el.get(xmlio.q('ism:classification'))==cls
            assert el.get(xmlio.q('ism:disseminationControls'))==root.get(xmlio.q('ism:disseminationControls'))
        if cls=='S':assert root.get(xmlio.q('ism:declassDate'))
        else:assert root.get(xmlio.q('ism:declassDate')) is None
        assert len(root.findall('.//'+xmlio.q('ntk:AccessProfile')))==2
        assert 'SYNTHETIC DEMO' in p.read_text()
    assert seen=={'S','U'}

def test_checker_rejects_mutations(corpus):
    w,_=corpus
    with store.connect() as db:r=db.execute("SELECT record FROM cables WHERE record LIKE '%participated%' LIMIT 1").fetchone()
    c=Cable.model_validate_json(r[0]); original=deepcopy(c)
    c.paragraphs[0].text+=' Joaquin Guzman.'
    with pytest.raises(ValueError,match='Blocklisted'):pipeline.check(c,w)
    c=deepcopy(original); c.paragraphs[0].text=c.paragraphs[0].text.replace('participated in','avoided')
    with pytest.raises(ValueError,match='relation mismatch'):pipeline.check(c,w)
    c=deepcopy(original);c.paragraphs[0].text+=' Mystery Criminal Company.'
    with pytest.raises(ValueError,match='Unknown capitalized'):pipeline.check(c,w)
    c=deepcopy(original);c.paragraphs[0].text+=' Investigators later counted 999 kg.'
    with pytest.raises(ValueError,match='Unplanned number'):pipeline.check(c,w)
    c=deepcopy(original);c.paragraphs[0].text+=' A meeting followed on 2011-02-02.'
    with pytest.raises(ValueError,match='Unplanned date'):pipeline.check(c,w)
    with pytest.raises(ValueError):Paragraph(number=1,classification='U',controls=['NF'])

def test_budget_reserves_failed_calls(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DB',tmp_path/'spend.sqlite')
    monkeypatch.delenv('MAX_SPEND_USD',raising=False)
    a=TokenAccountant(1);id=a.reserve('test','draft',.8)
    with pytest.raises(BudgetExceeded):a.reserve('test','critique',.3)
    a.settle(id,100,100,1000,1000)  # .20 actual
    a.reserve('test','revise',.7)
    with pytest.raises(BudgetExceeded):a.reserve('test','draft',.2)

def test_portion_access_citations_and_xml(corpus):
    from inteldoc import app as web
    web.world.cache_clear();web.entities.cache_clear()
    client=TestClient(web.app)
    low=client.post('/api/query',json={'question':'Which companies connect to Bruma del Cobre?','persona':'unclassified'}).json()
    high=client.post('/api/query',json={'question':'Which companies connect to Bruma del Cobre?','persona':'secret'}).json()
    assert high['facts'] and low['facts']
    for f in low['facts']:
        assert f['classification']=='U'
        for citation in f['citations']:
            doc=client.get('/api/cables/'+citation['cable']+'?persona=unclassified').json()
            para=next(p for p in doc['paragraphs'] if p['number']==citation['paragraph'])
            assert para['mark'].startswith('U')
            extracted=pipeline.extract(para['text'],corpus[0])
            assert any(x.subject==f['subject'] and x.object==f['object'] and x.predicate==f['predicate'] for x in extracted)
    with store.connect() as db:
        secret=db.execute("SELECT cable,paragraph,subject FROM evidence WHERE classification='S' LIMIT 1").fetchone()
    doc=client.get('/api/cables/'+secret['cable']+'?persona=unclassified').json()
    assert secret['paragraph'] not in [p['number'] for p in doc['paragraphs']]
    assert doc['source']=='Withheld'
    assert client.get('/api/cables/'+secret['cable']+'/xml?persona=unclassified').status_code==403
    assert client.get('/api/cables/'+secret['cable']+'/xml?persona=secret').status_code==200
    assert client.get('/api/entities?persona=admin').status_code==422
    assert client.get('/api/graph/nonexistent').status_code==404
    for f in client.get('/api/graph/org-01?persona=unclassified').json()['edges']:assert f['classification']=='U'
    web.world.cache_clear();web.entities.cache_clear()

def test_temporal_query_and_shared_alias(corpus):
    from inteldoc import app as web
    web.world.cache_clear();web.entities.cache_clear()
    client=TestClient(web.app)
    result=client.post('/api/query',json={'question':'Who led Bruma del Cobre in 2021?'}).json()
    assert result['facts']
    assert all(f['predicate']=='leads' and f['date']<='2021-12-31'<f['until_date'] for f in result['facts'])
    result=client.post('/api/query',json={'question':'Who is El Relojero?'}).json()
    assert result['ambiguous'] and not result['facts'] and len(result['entities'])==2
    result=client.post('/api/query',json={'question':'Who is Anzures Ibarra?'}).json()
    assert [e['id'] for e in result['entities']]==['p-anzures-y']  # longest alias wins over the bare surname alias
    result=client.post('/api/query',json={'question':'Which corridors did Bruma del Cobre control?'}).json()
    assert result['facts'] and all(f['predicate']=='controls' or any(k.startswith('cor-') for k in [f['subject'],f['object']]) for f in result['facts'])
    assert client.get('/api/world').json()['organizations'][0]['leadership']
    web.world.cache_clear();web.entities.cache_clear()

def test_authored_narrative_replaces_template_and_is_checked(corpus,monkeypatch):
    import json
    w,path=corpus
    with store.connect() as db:r=db.execute("SELECT record FROM cables WHERE state='validated' ORDER BY rowid LIMIT 1").fetchone()
    c=Cable.model_validate_json(r[0])
    folder=path/'exemplars/narratives';folder.mkdir(parents=True)
    cfg={'narratives_dir':'exemplars/narratives'}
    assert pipeline.authored_narrative(c,cfg) is None
    paragraphs=[{'number':p.number,'text':p.text+' Written by hand for this test.'} for p in c.paragraphs]
    (folder/f'{c.cable_id}.json').write_text(json.dumps({'paragraphs':paragraphs}))
    authored=pipeline.authored_narrative(c,cfg)
    assert authored.authored and 'Written by hand' in authored.paragraphs[0].text
    pipeline.check(authored,w)
    paragraphs[1]['text']=paragraphs[1]['text'].replace('participated in','avoided') if 'participated in' in paragraphs[1]['text'] else paragraphs[1]['text']+' Someone met Joaquin Guzman.'
    (folder/f'{c.cable_id}.json').write_text(json.dumps({'paragraphs':paragraphs}))
    with pytest.raises(ValueError):pipeline.check(pipeline.authored_narrative(c,cfg),w)
    (folder/f'{c.cable_id}.json').write_text(json.dumps({'paragraphs':paragraphs[:-1]}))
    with pytest.raises(ValueError,match='numbering'):pipeline.authored_narrative(c,cfg)
    with pytest.raises(ValueError,match='No authored narrative'):pipeline.authored_narrative(c.model_copy(update={'cable_id':'X-000000-IIR-00'}),{**cfg,'provider':'authored'})

def test_graph_explorer_and_exports(corpus):
    from inteldoc import app as web
    from lxml import etree
    web.world.cache_clear();web.entities.cache_clear()
    client=TestClient(web.app)
    low=client.get('/api/explore?persona=unclassified&predicates=structure,events&limit=50').json()
    assert low['edges'] and all(e['classification']=='U' for e in low['edges']) and all(e['count']>=1 and e['agencies'] for e in low['edges'])
    assert len(low['edges'])<=50 and {n['id'] for n in low['nodes']}=={e[k] for e in low['edges'] for k in ['subject','object']}
    high=client.get('/api/explore?persona=secret&center=org-01&hops=2&predicates=controls').json()
    assert high['edges'] and all(e['predicate']=='controls' for e in high['edges']) and high['centers']==['org-01']
    assert client.get('/api/explore?center=nonexistent').status_code==404
    years=client.get('/api/explore?persona=secret&year_from=2020&year_to=2021&predicates=events').json()
    assert all(e['date']<='2021-12-31' and (e['until_date'] or e['date'])>='2020-01-01' for e in years['edges'])
    g=client.get('/api/export/graphml?persona=unclassified')
    assert g.status_code==200 and 'attachment' in g.headers['content-disposition']
    root=etree.fromstring(g.content); ns={'g':'http://graphml.graphdrawing.org/xmlns'}
    nodes=root.findall('.//g:node',ns); edges=root.findall('.//g:edge',ns)
    assert nodes and edges and all(e.get('source') and e.get('target') for e in edges)
    assert all(d.text=='U' for d in root.findall('.//g:edge/g:data[@key="classification"]',ns))
    csv_edges=client.get('/api/export/edges.csv?persona=secret').text.splitlines()
    assert csv_edges[0].startswith(':START_ID,subject_name,:TYPE,:END_ID') and len(csv_edges)>1
    assert client.get('/api/export/nodes.csv?persona=secret').text.startswith('id:ID,name,:LABEL')
    web.world.cache_clear();web.entities.cache_clear()

def test_workspace_brief_and_runtime_remarking(corpus,monkeypatch):
    from inteldoc import app as web, marks
    for var in ['CORPUSCLE_ANTHROPIC_KEY','ANTHROPIC_API_KEY']:monkeypatch.delenv(var,raising=False)  # briefs stay deterministic in tests
    web.world.cache_clear();web.entities.cache_clear();web.BRIEFS.clear()
    client=TestClient(web.app)
    q={'question':'Which companies connect to Bruma del Cobre?','persona':'secret'}
    b=client.post('/api/brief',json=q).json()
    assert b['facts'] and b['paragraphs'] and b['cables'] and b['mode'].startswith('Composed')
    assert all(p['facts']==sorted(p['facts']) and all(0<=i<len(b['facts']) for i in p['facts']) for p in b['paragraphs'])
    assert all('_' not in p['text'] for p in b['paragraphs'])  # no raw predicate names reach the reader
    assert {c['cable'] for p in b['paragraphs'] for c in p['citations']}<= {c['cable'] for f in b['facts'] for c in f['citations']}
    low=client.post('/api/brief',json={**q,'persona':'unclassified'}).json()
    assert low['paragraphs'][-1]['text'].startswith('Only Unclassified')
    # Re-mark a Secret paragraph down to U//FOUO: it becomes visible to the Unclassified persona, and only that persona may change marks.
    with store.connect() as db:
        secret=db.execute("SELECT cable,paragraph,subject,predicate,object FROM evidence WHERE classification='S' AND cable NOT LIKE 'FBI-CDR-%' LIMIT 1").fetchone()
    before=[f for f in web.visible('unclassified') if (f['cable'],f['paragraph'])==(secret['cable'],secret['paragraph'])]
    assert not before
    assert client.post('/api/marks',json={'cable':secret['cable'],'paragraph':secret['paragraph'],'classification':'U','persona':'unclassified'}).status_code==403
    r=client.post('/api/marks',json={'cable':secret['cable'],'paragraph':secret['paragraph'],'classification':'U'})
    assert r.status_code==200 and r.json()['mark']=='U//FOUO' and len(r.json()['overrides'])==1
    after=[f for f in web.visible('unclassified') if (f['cable'],f['paragraph'])==(secret['cable'],secret['paragraph'])]
    assert after and all(f['classification']=='U' and f['controls']=='FOUO' for f in after)
    doc=client.get('/api/cables/'+secret['cable']+'?persona=unclassified').json()
    para=next(p for p in doc['paragraphs'] if p['number']==secret['paragraph'])
    assert para['mark']=='U//FOUO' and para['remarked'] is True
    assert client.post('/api/marks',json={'cable':'NOPE-000000-IIR-20','paragraph':1,'classification':'U'}).status_code==404
    # Setting a paragraph back to its published mark removes the override; reset clears everything.
    assert client.post('/api/marks',json={'cable':secret['cable'],'paragraph':secret['paragraph'],'classification':'S'}).json()['overrides']==[]
    client.post('/api/marks',json={'cable':secret['cable'],'paragraph':secret['paragraph'],'classification':'U'})
    assert client.delete('/api/marks').json()=={'overrides':[]} and marks.overrides()=={}
    assert not [f for f in web.visible('unclassified') if (f['cable'],f['paragraph'])==(secret['cable'],secret['paragraph'])]
    web.world.cache_clear();web.entities.cache_clear();web.BRIEFS.clear()

def test_aliases_and_domain_trail(corpus,monkeypatch):
    from inteldoc import app as web, aliases
    for var in ['CORPUSCLE_ANTHROPIC_KEY','ANTHROPIC_API_KEY']:monkeypatch.delenv(var,raising=False)
    web.world.cache_clear();web.base_entities.cache_clear();web.domain_of.cache_clear();web.BRIEFS.clear();aliases.clear()
    client=TestClient(web.app)
    card=client.get('/api/entity/p-anzures-y?persona=secret').json()
    assert card['domain']=='org-01' and card['added_aliases']==[] and card['degree']>0
    assert client.post('/api/query',json={'question':'Who is The Doctor?','persona':'secret'}).json()['entities']==[]
    r=client.post('/api/aliases',json={'entity':'p-anzures-y','alias':'  The   Doctor '})
    assert r.status_code==200 and r.json()['added_aliases']==['The Doctor'] and 'The Doctor' in r.json()['aliases']
    q=client.post('/api/query',json={'question':'Who is The Doctor?','persona':'secret'}).json()
    assert [e['id'] for e in q['entities']]==['p-anzures-y'] and q['facts']
    assert 'The Doctor' in [a for e in client.get('/api/entities?persona=secret&q=doctor').json() for a in e['aliases']]
    assert client.post('/api/aliases',json={'entity':'p-anzures-y','alias':'<script>'}).status_code==422
    assert client.post('/api/aliases',json={'entity':'nobody','alias':'x'}).status_code==404
    # A name another entity carries becomes a shared alias: questions must disambiguate.
    other=next(e['id'] for e in web.base_entities().values() if e['kind']=='person' and e['id']!='p-anzures-y' and e['id'] in web.allowed_ids('secret'))
    client.post('/api/aliases',json={'entity':other,'alias':'The Doctor'})
    assert client.post('/api/query',json={'question':'Who is The Doctor?','persona':'secret'}).json()['ambiguous'] is True
    assert client.delete('/api/aliases?entity='+other+'&alias=The%20Doctor').json()['added_aliases']==[]
    assert client.delete('/api/aliases?entity=p-anzures-y&alias=The%20Doctor').json()['added_aliases']==[]
    assert client.post('/api/query',json={'question':'Who is The Doctor?','persona':'secret'}).json()['entities']==[]
    # Domain trail: every entity in an answer carries its organization's graph; cross-graph facts are reported as hops.
    b=client.post('/api/brief',json={'question':'Which companies connect to Bruma del Cobre?','persona':'secret'}).json()
    assert b['trail']['domains'] and b['trail']['domains'][0]['id']=='org-01'
    for h in b['trail']['hops']:assert h['from']!=h['to'] and 0<=h['fact_index']<len(b['facts'])
    assert all(e.get('domain') is not None for e in b['entities'])
    web.world.cache_clear();web.base_entities.cache_clear();web.domain_of.cache_clear();web.BRIEFS.clear()
