import json
import re
import shutil
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from inteldoc import world, store, pipeline, xmlio, app as web
from inteldoc.models import Cable


@pytest.fixture
def model_demo(tmp_path, monkeypatch):
    for folder in ['world', 'config', 'schemas']:
        (tmp_path / folder).mkdir()
    for file in ['world/seed.yaml', 'config/corpus.yaml', 'config/blocklist.yaml']:
        shutil.copy(world.ROOT / file, tmp_path / file)
    for module in [world, pipeline, xmlio]:
        monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(store, 'DB', tmp_path / 'corpus/manifest.sqlite')
    monkeypatch.setattr(store, 'SPEND_DB', None)
    monkeypatch.delenv('INTELDOC_OPENAI_API_KEY2', raising=False)
    monkeypatch.setenv('INTELDOC_OPENAI_API_KEY', 'test-key-not-real')
    monkeypatch.delenv('MAX_SPEND_USD', raising=False)
    bible = world.expand(42, total_events=120)
    cfg = pipeline.load_config(tmp_path / 'config/corpus.yaml')
    cfg.update(provider='openai', query_provider='openai', extraction='model',
               openai_model='test-model', input_usd_per_million=2, output_usd_per_million=8)
    calls = []
    state = {'bad_quote': False, 'interrupt': False, 'omit_claim': False}
    names = {e['id']: e['name'] for e in bible['entities']}

    ids = {v: k for k, v in names.items()}

    def quote_for(text, key):
        # The sentence in the narrative whose extraction yields exactly this fact (it may use an alias or a window).
        for s in re.split(r'(?<=\.)\s+', text):
            if any(x.key() == key for x in pipeline.extract(s, bible)):
                return s
        raise AssertionError('No supporting sentence for ' + str(key))

    def post(url, **kwargs):
        payload = kwargs['json']
        data = json.loads(payload['input'].split('\nDATA:\n', 1)[1])
        calls.append(data)
        request = httpx.Request('POST', url)
        if state['interrupt'] and 'constraints' in data and 'critique' not in data:
            state['interrupt'] = False
            return httpx.Response(503, json={'error': 'test interruption'}, request=request)
        if 'agency' in data:
            result = {'paragraphs': [{'number': p['number'], 'text': p['baseline']} for p in data['paragraphs']]}
        elif 'constraints' in data and 'critique' not in data:
            result = {'defects': []}
        elif 'critique' in data:
            result = data['draft']
        elif 'vocabulary' in data:
            claims = []
            for p in data['paragraphs']:
                for f in pipeline.extract(p['text'], bible):
                    claims.append({'paragraph': p['number'], **f.model_dump(mode='json'), 'quote': quote_for(p['text'], f.key())})
            result = {'claims': claims[1:] if state['omit_claim'] else claims}
        elif 'question' in data:
            e = data['evidence'][0]
            quote = quote_for(e['source_text'], (ids[e['subject']], e['predicate'], ids[e['object']], e['date'], e['until'] or ''))
            result = {'quotes': [{'fact_index': e['fact_index'],
                                  'quote': 'An invented unsupported sentence.' if state['bad_quote'] else quote}]}
        else:
            raise AssertionError('Unexpected stage input')
        return httpx.Response(200, request=request, json={
            'status': 'completed', 'usage': {'input_tokens': 100, 'output_tokens': 100},
            'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(result)}]}],
        })
    monkeypatch.setattr(httpx, 'post', post)
    monkeypatch.setattr(web, 'load_config', lambda: cfg)
    web.world.cache_clear(); web.entities.cache_clear()
    yield bible, cfg, calls, state, tmp_path
    web.world.cache_clear(); web.entities.cache_clear()


def test_model_corpus_stages_extraction_score_and_resume(model_demo):
    bible, cfg, calls, state, path = model_demo
    pipeline.plan(4, config=cfg)
    assert pipeline.run(config=cfg) == {'validated': 4, 'failed': 0}
    assert len(calls) == 16  # draft, critique, revision, independent extraction per cable
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM stages').fetchone()[0] == 16
        assert db.execute('SELECT count(*) FROM spend').fetchone()[0] == 16
    assert pipeline.run(config=cfg) == {'validated': 0, 'failed': 0}
    assert len(calls) == 16
    assert len(list((path / 'corpus/xml').glob('*.xml'))) == 4
    score = pipeline.score()
    assert score['precision'] == 1
    assert 'openai' in score['method'] and 'model extraction' in score['method']
    assert all('facts' not in json.dumps(call) for call in calls if 'vocabulary' in call)
    with pytest.raises(ValueError, match='provider changed'):
        pipeline.plan(4, config={**cfg, 'provider': 'offline', 'extraction':'deterministic'})


def test_interrupted_run_resumes_after_completed_draft(model_demo):
    _, cfg, calls, state, _ = model_demo
    pipeline.plan(1, config=cfg)
    state['interrupt'] = True
    assert pipeline.run(config=cfg)['stopped'] == 'provider_error'
    with store.connect() as db:
        assert db.execute('SELECT stage FROM stages').fetchone()[0] == 'draft'
        assert db.execute('SELECT count(*) FROM spend').fetchone()[0] == 2
    assert pipeline.run(config=cfg, retry_failed=True) == {'validated': 1, 'failed': 0}
    assert len(calls) == 5  # no duplicate draft charge


def test_model_omissions_reduce_recall_instead_of_copying_truth(model_demo):
    _, cfg, _, state, _ = model_demo
    pipeline.plan(4, config=cfg)
    state['omit_claim'] = True
    pipeline.run(config=cfg)
    assert 0 < pipeline.score()['planted_recall'] < 1


def test_query_model_citations_and_persona_isolation(model_demo):
    bible, cfg, calls, _, _ = model_demo
    # Plan past the first Bruma del Cobre events under the Secret-only 2020 leadership window, so that at least one
    # Secret cable carries the leadership fact (Unclassified and OSINT cables never do).
    first = next(i for i, e in enumerate(bible['events']) if e['org'] == 'org-01' and e['date'] >= '2020-02-27')
    pipeline.plan(first + 20, config=cfg)
    pipeline.run(config=cfg)
    client = TestClient(web.app)
    before = len(calls)
    high = client.post('/api/query', json={'question': 'Who led Bruma del Cobre in 2021?', 'persona': 'secret'})
    assert high.status_code == 200, high.text
    data = high.json()
    assert data['answer'] and 'openai' in data['mode']
    citation = data['answer'][0]['citations'][0]
    source = client.get('/api/cables/' + citation['cable']).json()
    paragraph = next(p for p in source['paragraphs'] if p['number'] == citation['paragraph'])
    assert data['answer'][0]['text'] in paragraph['text']
    assert len(calls) == before + 1
    before = len(calls)
    low = client.post('/api/query', json={'question': 'Who led Bruma del Cobre in 2021?', 'persona': 'unclassified'})
    assert low.status_code == 200
    assert low.json()['answer'] == [] and low.json()['facts'] == []
    assert len(calls) == before  # no inaccessible content sent to the model
    public = client.post('/api/query', json={'question': 'Show Bruma del Cobre', 'persona': 'unclassified'})
    assert public.status_code == 200
    sent = calls[-1]['evidence']
    for e in sent:
        f = public.json()['facts'][e['fact_index']]
        assert all(c['mark'].startswith('U') for c in f['citations'])
        assert e['source_text']


def test_invented_query_quote_is_rejected(model_demo):
    _, cfg, _, state, _ = model_demo
    pipeline.plan(4, config=cfg); pipeline.run(config=cfg)
    state['bad_quote'] = True
    client = TestClient(web.app)
    result = client.post('/api/query', json={'question': 'Show Bruma del Cobre'})
    assert result.status_code == 502
    assert 'invented unsupported' not in result.text


def test_cap_stops_pipeline_without_attempting_remaining_records(model_demo, monkeypatch):
    _, cfg, calls, _, _ = model_demo
    monkeypatch.setenv('MAX_SPEND_USD', '.0000001')
    pipeline.plan(5, config=cfg)
    result = pipeline.run(config=cfg)
    assert result == {'validated': 0, 'failed': 1, 'stopped': 'spend_cap'}
    assert calls == []
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM cables WHERE state='planned'").fetchone()[0] == 4


def test_checker_rejects_secret_fact_duplicated_into_public_paragraph(model_demo):
    bible, cfg, _, _, _ = model_demo
    pipeline.plan(12, config=cfg); pipeline.run(config=cfg)
    with store.connect() as db:
        records = [Cable.model_validate_json(r[0]) for r in db.execute('SELECT record FROM cables')]
    cable = next(c for c in records if c.classification == 'S' and c.paragraphs[1].facts)
    moved = cable.paragraphs[1].text.split('. ')[0] + '.'
    cable.paragraphs[0].text += ' ' + moved
    with pytest.raises(ValueError): pipeline.check(cable, bible)


def test_dataset_switch_shares_spend_cap(model_demo):
    _, cfg, _, _, path = model_demo
    from inteldoc.providers import TokenAccountant, BudgetExceeded
    ledger = TokenAccountant(1)
    ledger.reserve('openai', 'test', .75)
    store.use_dataset(path / 'alternate')
    with pytest.raises(BudgetExceeded): ledger.reserve('openai', 'test', .5)
    with store.connect_spend() as db:
        assert db.execute('SELECT count(*) FROM spend').fetchone()[0] == 1


def test_pilot_cap_resumes_same_subset_and_preserves_source_grades(model_demo):
    bible, cfg, calls, _, _ = model_demo
    cfg={**cfg,'max_cables':3}
    pipeline.plan(10,config=cfg)
    assert pipeline.run(config=cfg)=={'validated':3,'failed':0}
    before=len(calls)
    assert pipeline.run(config=cfg)=={'validated':0,'failed':0}
    assert len(calls)==before
    sources={e['name']:e for e in bible['entities'] if e['kind']=='source'}
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM cables WHERE state='planned'").fetchone()[0]==7
        records=[Cable.model_validate_json(row[0]) for row in db.execute("SELECT record FROM cables WHERE state='validated' ORDER BY rowid")]
    assert [int(c.cable_id.split('-')[1]) for c in records]==[1,2,3]
    for c in records:
        assert sources[c.source_id]['agency']==c.agency
        assert sources[c.source_id]['reliability']==c.reliability
