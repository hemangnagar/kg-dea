from copy import deepcopy
from collections import Counter
import pytest
import yaml
from inteldoc.world import ROOT
from inteldoc.seed import validate_seed


def seed():
    return yaml.safe_load((ROOT/'world/seed.yaml').read_text())


def test_authored_seed_is_complete():
    bible=seed();result=validate_seed(bible)
    assert result['people']==50 and result['events']==35 and result['sources']==56
    assert len(bible['corridors'])==25
    assert all(n==8 for n in Counter(s['agency'] for s in bible['sources']).values())
    assert len([a for p in bible['people'] for a in p['alias_history'] if a.get('inherited_from')])==5


@pytest.mark.parametrize('fault', ['dangling','overlap','after-arrest','real-name','inheritance','no-place'])
def test_seed_rejects_integrity_faults(fault):
    bible=seed()
    if fault=='dangling':bible['timeline'][0]['participants'][0]['id']='person-undefined'
    if fault=='overlap':bible['organizations'][0]['leadership'][1]['from']='2011-01-01'
    if fault=='after-arrest':bible['timeline'][2]['participants'][0]['id']='person-000'
    if fault=='real-name':bible['people'][0]['name']='Joaquin Guzman'
    if fault=='inheritance':bible['people'][1]['alias_history'][0]['from']='2011-01-01'
    if fault=='no-place':bible['people'][0]['places']=[]
    with pytest.raises(ValueError):validate_seed(bible)
