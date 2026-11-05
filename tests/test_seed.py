from collections import Counter
import pytest
import yaml
from inteldoc.world import ROOT
from inteldoc.seed import validate_seed


def seed():
    return yaml.safe_load((ROOT / 'world/seed.yaml').read_text())


def test_authored_seed_is_complete():
    bible = seed(); result = validate_seed(bible)
    assert 40 <= result['people'] <= 60 and 30 <= result['events'] <= 45 and result['organizations'] in (5, 6)
    assert 20 <= result['corridors'] <= 30 and 15 <= result['companies'] <= 20 and 10 <= result['assets'] <= 15
    assert result['shared_aliases'] >= 5 and result['inherited_aliases'] >= 3
    assert all(6 <= n <= 10 for n in Counter(s['agency'] for s in bible['sources']).values())
    # Arcs are distinct: no two organizations share their full set of beat dates.
    dates = {o['id']: sorted(str(e['date']) for e in bible['timeline'] if e['organization'] == o['id']) for o in bible['organizations']}
    assert len({tuple(v) for v in dates.values()}) == len(dates)
    assert all(e.get('description') and e.get('name') for e in bible['timeline'])
    # Every corridor is real geography with a dated control history that changes hands.
    places = {p['id'] for p in bible['geography']['places']}
    for c in bible['corridors']:
        assert set(c['places']) <= places and len({w['organization'] for w in c['control_history']}) >= 2


@pytest.mark.parametrize('fault', ['dangling', 'overlap', 'after-death', 'real-name', 'inheritance', 'no-place', 'asymmetric-alliance',
                                   'leadership-outside-membership', 'shared-by-three', 'dated-description', 'control-gap'])
def test_seed_rejects_integrity_faults(fault):
    bible = seed()
    people = {p['id']: p for p in bible['people']}
    if fault == 'dangling':
        bible['timeline'][0]['participants'][0]['id'] = 'p-undefined'
    if fault == 'overlap':
        bible['organizations'][0]['leadership'][1]['from'] = '2011-01-01'
    if fault == 'after-death':
        bible['timeline'][-1]['participants'].append({'id': 'p-zepeda-h', 'role': 'reported-participant'})
    if fault == 'real-name':
        bible['people'][0]['name'] = 'Joaquin Guzman'
    if fault == 'inheritance':
        people['p-olivares-d']['alias_history'][0]['from'] = '2011-01-01'
    if fault == 'no-place':
        bible['people'][0]['places'] = []
    if fault == 'asymmetric-alliance':
        bible['organizations'][0]['alliances'][0]['to'] = '2019-10-01'
    if fault == 'leadership-outside-membership':
        people['p-anzures-r']['membership'][0]['to'] = '2013-01-01'
    if fault == 'shared-by-three':
        people['p-cervera-n']['aliases'].append('La Garza')
    if fault == 'dated-description':
        bible['timeline'][3]['description'] += ' It happened on 2010-11-18.'
    if fault == 'control-gap':
        bible['corridors'][0]['control_history'][1]['from'] = '2014-09-01'
    with pytest.raises(ValueError):
        validate_seed(bible)
