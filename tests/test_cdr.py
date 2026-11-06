import csv
import pytest
from fastapi.testclient import TestClient
from inteldoc import cdr, store
from tests.test_workflow import corpus  # noqa: F401  (shared fixture)


def test_partner_records_generate_ingest_score_and_fuse(corpus):
    from inteldoc import app as web
    w, path = corpus
    out = cdr.generate(42, 1500, world=w, out=path / 'corpus/cdr')
    rows = list(csv.DictReader(open(out['path'])))
    assert len(rows) == 1500 and all(r['handling'] == 'U//LES' and r['provider'] == 'FBI' for r in rows)
    assert all(r['caller_label'].startswith('DEMO-TEL-') and r['callee_label'].startswith('DEMO-TEL-') for r in rows)
    assert cdr.generate(42, 1500, world=w, out=path / 'corpus/cdr2') and open(path / 'corpus/cdr2/fbi-cdr.csv').read() == open(out['path']).read()  # deterministic
    result = cdr.ingest(out['path'], world=w)
    assert result['records'] == 1500 and 0 < result['resolved_both_parties'] < 1500
    score = cdr.score()
    assert score['records'] == 1500 and score['unresolved_records'] > 0
    assert 0.9 < score['resolution_accuracy'] <= 1 and score['naive_first_holder_accuracy'] < score['resolution_accuracy']
    assert score['shared_number_records'] > 0
    web.world.cache_clear(); web.entities.cache_clear()
    client = TestClient(web.app)
    high = client.get('/api/explore?persona=secret&predicates=communications&limit=50').json()
    assert high['edges'] and all(e['predicate'] == 'called' and e['controls'] == 'LES' for e in high['edges'])
    low = client.get('/api/explore?persona=unclassified&predicates=communications&limit=50').json()
    assert low['edges'] == []  # LES-handled partner data is Secret-persona only
    assert not any(e['predicate'] == 'called' for e in client.get('/api/explore?persona=unclassified&limit=1500').json()['edges'])
    first = high['edges'][0]
    record = first['citations'][0]['cable']
    assert record.startswith('FBI-CDR-')
    view = client.get('/api/cdr/' + record).json()
    assert view['caller']['person'] == first['subject'] and view['callee']['person'] == first['object'] and view['caller']['window']
    assert client.get('/api/cdr/' + record + '?persona=unclassified').status_code == 403
    name = web.entities()[first['subject']]['name']
    answer = client.post('/api/query', json={'question': f'Who did {name} call?', 'persona': 'secret'}).json()
    assert answer['facts'] and all(f['predicate'] == 'called' for f in answer['facts'])
    assert client.post('/api/query', json={'question': f'Who did {name} call?', 'persona': 'unclassified'}).json()['facts'] == []
    # Corroboration: some cable about two phone holders has calls in its window, visible at Secret only.
    with store.connect() as db:
        ids = [r[0] for r in db.execute("SELECT id FROM cables WHERE state='validated'")]
    found = [i for i in ids if client.get('/api/cables/' + i).json().get('corroborating_calls')]
    assert found, 'expected at least one cable with corroborating calls'
    doc = client.get('/api/cables/' + found[0]).json()
    assert doc['corroborating_calls'][0]['records'] and doc['corroborating_calls'][0]['count'] >= 1
    assert client.get('/api/cables/' + found[0] + '?persona=unclassified').json()['corroborating_calls'] == []
    g = client.get('/api/export/graphml?persona=unclassified').content
    assert b'called' not in g
    assert client.get('/api/scorecard').json()['partner_cdr']['records'] == 1500
    web.world.cache_clear(); web.entities.cache_clear()
