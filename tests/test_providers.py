import httpx
import pytest

from inteldoc import store
from inteldoc.providers import OpenAIProvider, BudgetExceeded, provider_from_config


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB', tmp_path / 'spend.sqlite')
    monkeypatch.delenv('INTELDOC_OPENAI_API_KEY2', raising=False)
    monkeypatch.delenv('INTELDOC_OPENAI_API_KEY', raising=False)
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key-not-a-real-credential')
    monkeypatch.delenv('MAX_SPEND_USD', raising=False)


def response(data, status=200):
    return httpx.Response(status, json=data, request=httpx.Request('POST', 'https://api.openai.com/v1/responses'))


def successful():
    return {
        'status': 'completed',
        'usage': {'input_tokens': 100, 'output_tokens': 60,
                  'output_tokens_details': {'reasoning_tokens': 20}},
        'output': [
            {'type': 'reasoning', 'summary': []},
            {'type': 'message', 'content': [{'type': 'output_text', 'text': 'Fictional '},
                                            {'type': 'output_text', 'text': 'test response.'}]},
        ],
    }


def test_openai_response_and_billed_reasoning(ledger, monkeypatch):
    def post(url, *, headers, json, timeout):
        assert url == 'https://api.openai.com/v1/responses'
        assert headers['Authorization'] == 'Bearer test-key-not-a-real-credential'
        assert json == {'model': 'test-model', 'input': 'A synthetic prompt.',
                        'max_output_tokens': 128, 'store': False}
        with store.connect() as db:
            assert db.execute("SELECT status FROM spend").fetchone()[0] == 'reserved'
        return response(successful())
    monkeypatch.setattr(httpx, 'post', post)
    provider = provider_from_config({'provider': 'openai', 'openai_model': 'test-model',
                                    'input_usd_per_million': 2, 'output_usd_per_million': 8})
    assert provider.complete('A synthetic prompt.', max_tokens=128) == 'Fictional test response.'
    with store.connect() as db:
        row = db.execute('SELECT * FROM spend').fetchone()
        assert row['provider'] == 'openai'
        assert row['operation'] == 'responses'
        assert row['actual'] == pytest.approx((100 * 2 + 60 * 8) / 1e6)
        assert row['output_tokens'] == 60  # Includes the 20 reasoning tokens, once.
        assert row['status'] == 'settled'


def test_cap_prevents_network_and_invalid_requests(ledger, monkeypatch):
    def never(*args, **kwargs):
        pytest.fail('No network request should be made')
    monkeypatch.setattr(httpx, 'post', never)
    provider = OpenAIProvider('test-model', 2, 8, cap=.001)
    with pytest.raises(BudgetExceeded): provider.complete('Example', 128)
    for limit in [0, -1, True, 1.5]:
        with pytest.raises(ValueError): provider.complete('Example', limit)
    with pytest.raises(ValueError): provider.complete(' ')
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM spend').fetchone()[0] == 0


def test_key_and_pricing_required(ledger, monkeypatch):
    for price in [None, 0, -1, float('nan'), float('inf')]:
        with pytest.raises(ValueError, match='prices'): OpenAIProvider('test-model', price, 8)
    monkeypatch.delenv('OPENAI_API_KEY')
    with pytest.raises(ValueError, match='OPENAI_API_KEY'): OpenAIProvider('test-model', 2, 8)
    with pytest.raises(ValueError, match='Offline'): provider_from_config({'provider': 'offline'})
    with pytest.raises(ValueError, match='Unsupported'): provider_from_config({'provider': 'anthropic'})


@pytest.mark.parametrize('status', ['incomplete', 'refusal'])
def test_partial_and_refusal_are_charged_but_not_returned(ledger, monkeypatch, status):
    data = successful()
    if status == 'incomplete': data['status'] = 'incomplete'
    else: data['output'] = [{'type': 'message', 'content': [{'type': 'refusal', 'refusal': 'Refused.'}]}]
    monkeypatch.setattr(httpx, 'post', lambda *a, **k: response(data))
    with pytest.raises(RuntimeError, match='accounted'):
        OpenAIProvider('test-model', 2, 8).complete('Example')
    with store.connect() as db:
        assert db.execute('SELECT status FROM spend').fetchone()[0] == 'settled'


def test_failure_keeps_reservation_without_retry(ledger, monkeypatch):
    calls = []
    def post(*args, **kwargs):
        calls.append(1)
        return response({'error': {'message': 'Unavailable'}}, status=503)
    monkeypatch.setattr(httpx, 'post', post)
    with pytest.raises(httpx.HTTPStatusError): OpenAIProvider('test-model', 2, 8).complete('Example')
    assert len(calls) == 1
    with store.connect() as db:
        row = db.execute('SELECT * FROM spend').fetchone()
        assert row['status'] == 'reserved'
        assert row['actual'] is None


def test_replacement_key2_is_used_in_request(ledger, monkeypatch):
    monkeypatch.setenv('INTELDOC_OPENAI_API_KEY2', 'replacement-test-key')
    monkeypatch.setenv('INTELDOC_OPENAI_API_KEY', 'older-test-key')
    def post(url, *, headers, json, timeout):
        assert headers['Authorization'] == 'Bearer replacement-test-key'
        return response(successful())
    monkeypatch.setattr(httpx, 'post', post)
    assert OpenAIProvider('test-model', 2, 8).complete('Example') == 'Fictional test response.'
