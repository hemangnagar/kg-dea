import types
import pytest
from inteldoc import store
from inteldoc.providers import AnthropicProvider, BudgetExceeded


class FakeMessages:
    def __init__(self, log, stop='end_turn', text='{"ok": true}'):
        self.log, self.stop, self.text = log, stop, text

    def create(self, **request):
        self.log.append(request)
        usage = types.SimpleNamespace(input_tokens=1000, output_tokens=200, cache_creation_input_tokens=500, cache_read_input_tokens=0)
        block = types.SimpleNamespace(type='text', text=self.text)
        return types.SimpleNamespace(usage=usage, stop_reason=self.stop, content=[block])


def client(log, **kw):
    return types.SimpleNamespace(messages=FakeMessages(log, **kw))


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB', tmp_path / 'spend.sqlite')
    monkeypatch.setattr(store, 'SPEND_DB', None)
    monkeypatch.delenv('MAX_SPEND_USD', raising=False)


def test_structured_request_and_settlement(ledger):
    log = []
    p = AnthropicProvider('claude-haiku-5-5', 0.10, 0.50, cap=1, client=client(log))
    out = p.complete('prompt', max_tokens=300, schema={'type': 'object'}, system='style')
    assert out == '{"ok": true}'
    req = log[0]
    assert req['model'] == 'claude-haiku-5-5' and req['max_tokens'] == 300
    assert req['output_config'] == {'effort': 'low', 'format': {'type': 'json_schema', 'schema': {'type': 'object'}}}
    assert req['system'][0]['cache_control'] == {'type': 'ephemeral'}
    with store.connect_spend() as db:
        row = db.execute('SELECT input_tokens,output_tokens,actual,status FROM spend').fetchone()
    assert tuple(row) == (1500, 200, pytest.approx((1500 * 0.10 + 200 * 0.50) / 1e6), 'settled')


def test_refusal_and_truncation_are_errors_but_accounted(ledger):
    for stop in ['refusal', 'max_tokens']:
        p = AnthropicProvider('claude-haiku-5-5', 0.10, 0.50, cap=1, client=client([], stop=stop))
        with pytest.raises(RuntimeError):
            p.complete('prompt', max_tokens=100)
    with store.connect_spend() as db:
        assert db.execute("SELECT count(*) FROM spend WHERE status='settled'").fetchone()[0] == 2


def test_cap_blocks_before_network(ledger, monkeypatch):
    log = []
    monkeypatch.setenv('MAX_SPEND_USD', '0.0000001')
    p = AnthropicProvider('claude-haiku-5-5', 0.10, 0.50, client=client(log))
    with pytest.raises(BudgetExceeded):
        p.complete('prompt', max_tokens=100)
    assert log == []


def test_key_required_without_client(monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False); monkeypatch.delenv('NOPE_KEY', raising=False)
    with pytest.raises(ValueError, match='No Anthropic key'):
        AnthropicProvider('claude-haiku-5-5', 0.10, 0.50, key_env='NOPE_KEY')
