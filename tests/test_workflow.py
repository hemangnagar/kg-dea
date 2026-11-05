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
