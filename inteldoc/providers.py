"""Budget-accounted provider boundary for narrative, extraction and query stages.

Every paid request reserves an upper bound BEFORE network I/O. Uncertain failures
retain reservations. Prices must be explicitly configured from current provider pricing.
"""
import os
import math
import httpx
from .store import connect_spend as connect

class BudgetExceeded(RuntimeError):pass

class TokenAccountant:
    def __init__(self,cap=40):
        self.cap=float(os.getenv('MAX_SPEND_USD',cap))
        if not math.isfinite(self.cap) or self.cap<=0:raise ValueError('Spend cap must be positive')

    def reserve(self,provider,operation,amount):
        if not math.isfinite(amount) or amount<=0:raise ValueError('Reservation must be positive')
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            used=db.execute('SELECT COALESCE(sum(COALESCE(actual,reserved)),0) FROM spend').fetchone()[0]
            if used+amount>self.cap:raise BudgetExceeded(f'Request would exceed ${self.cap:.2f} cap')
            return db.execute("INSERT INTO spend(provider,operation,reserved,status) VALUES(?,?,?,'reserved')",(provider,operation,amount)).lastrowid

    def settle(self,id,input_tokens,output_tokens,input_price,output_price):
        actual=(input_tokens*input_price+output_tokens*output_price)/1e6
        with connect() as db:
            reserved=db.execute('SELECT reserved FROM spend WHERE id=?',(id,)).fetchone()[0]
            # A conservative reservation should exceed actual usage. Retain the real charge if it does not.
            db.execute("UPDATE spend SET actual=?,input_tokens=?,output_tokens=?,status='settled' WHERE id=?",(actual,input_tokens,output_tokens,id))
        if actual>reserved:raise BudgetExceeded('Provider charge exceeded reservation; stop and correct prices')


class AnthropicProvider:
    """Claude Messages API through the official SDK. Structured JSON output, low effort, cached system prompt."""

    def __init__(self, model, input_price, output_price, cap=40, key_env='ANTHROPIC_API_KEY', effort='low', thinking='disabled', client=None):
        if not model or not all(isinstance(p, (int, float)) and math.isfinite(p) and p > 0 for p in [input_price, output_price]):
            raise ValueError('Explicit Anthropic model and verified positive token prices required')
        key = os.getenv(key_env) or os.getenv('ANTHROPIC_API_KEY')
        if client is None and not key:
            raise ValueError(f'No Anthropic key configured: set {key_env} or ANTHROPIC_API_KEY')
        if client is None:
            import anthropic
            client = anthropic.Anthropic(api_key=key)
        self.client, self.model, self.ip, self.op, self.effort, self.thinking = client, model, input_price, output_price, effort, thinking
        self.accountant = TokenAccountant(cap)

    def complete(self, prompt, max_tokens=1600, schema=None, system=None):
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError('Prompt must be nonempty text')
        if type(max_tokens) is not int or max_tokens <= 0:
            raise ValueError('max_tokens must be a positive integer')
        # UTF-8 bytes conservatively bound input tokens (the tokenizer averages ~3-4 bytes per token); output is capped.
        cost = ((len(prompt.encode()) + len((system or '').encode()) + len(self.model.encode()) + 2048) * self.ip + max_tokens * self.op) / 1e6
        reservation = self.accountant.reserve('anthropic', 'messages', cost)
        request = dict(model=self.model, max_tokens=max_tokens, output_config={'effort': self.effort},
                       messages=[{'role': 'user', 'content': prompt}])
        if self.thinking == 'disabled':
            request['thinking'] = {'type': 'disabled'}  # Haiku 5.5 allows this at effort high or below; saves ~2,500 hidden tokens per call
        if system:
            request['system'] = [{'type': 'text', 'text': system, 'cache_control': {'type': 'ephemeral'}}]
        if schema is not None:
            request['output_config']['format'] = {'type': 'json_schema', 'schema': schema}
        # Failed/uncertain requests retain their reservation; the SDK's own retries cover 429/5xx.
        response = self.client.messages.create(**request)
        usage = response.usage
        billed_input = (usage.input_tokens + (getattr(usage, 'cache_creation_input_tokens', 0) or 0)
                        + (getattr(usage, 'cache_read_input_tokens', 0) or 0))
        self.accountant.settle(reservation, billed_input, usage.output_tokens, self.ip, self.op)
        if response.stop_reason == 'refusal':
            raise RuntimeError('Anthropic declined the request; usage was accounted')
        if response.stop_reason == 'max_tokens':
            raise RuntimeError('Anthropic response was truncated at max_tokens; usage was accounted')
        text = ''.join(block.text for block in response.content if block.type == 'text')
        if not text:
            raise RuntimeError('Anthropic returned no text; usage was accounted')
        return text

def openai_api_key():
    # Prefer the user's explicitly named replacement key. Never log key values.
    return (os.getenv('INTELDOC_OPENAI_API_KEY2') or
            os.getenv('INTELDOC_OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY'))


class OpenAIProvider:
    """Text-only Responses API adapter. No ChatGPT session cookies or subscriptions."""

    def __init__(self, model, input_price, output_price, cap=40):
        if not model or not all(isinstance(p, (int, float)) and math.isfinite(p) and p > 0
                                for p in [input_price, output_price]):
            raise ValueError('Explicit OpenAI model and verified positive token prices required')
        if not openai_api_key():
            raise ValueError('No OpenAI key configured: INTELDOC_OPENAI_API_KEY2, INTELDOC_OPENAI_API_KEY or OPENAI_API_KEY')
        self.model, self.ip, self.op = model, input_price, output_price
        self.accountant = TokenAccountant(cap)

    def complete(self, prompt, max_tokens=1600, **_):
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError('Prompt must be nonempty text')
        if type(max_tokens) is not int or max_tokens <= 0:
            raise ValueError('max_tokens must be a positive integer')
        # UTF-8 bytes conservatively bound text input tokens, with overhead allowance.
        # max_output_tokens also limits billed reasoning tokens on reasoning models.
        cost = ((len(prompt.encode()) + len(self.model.encode()) + 1024) * self.ip
                + max_tokens * self.op) / 1e6
        reservation = self.accountant.reserve('openai', 'responses', cost)
        response = httpx.post(
            'https://api.openai.com/v1/responses',
            headers={'Authorization': 'Bearer ' + openai_api_key()},
            json={'model': self.model, 'input': prompt,
                  'max_output_tokens': max_tokens, 'store': False},
            timeout=120,
        )
        # Failed/uncertain requests retain their reservation; do not retry automatically.
        response.raise_for_status()
        data = response.json()
        usage = data['usage']
        self.accountant.settle(reservation, usage['input_tokens'], usage['output_tokens'],
                               self.ip, self.op)
        if data.get('status') != 'completed':
            raise RuntimeError('OpenAI response did not complete; usage was accounted')
        text = ''.join(
            part['text'] for item in data.get('output', []) if item.get('type') == 'message'
            for part in item.get('content', []) if part.get('type') == 'output_text'
        )
        if not text:
            raise RuntimeError('OpenAI returned no text (possibly a refusal); usage was accounted')
        return text

class OllamaProvider:
    def __init__(self,model,base_url='http://127.0.0.1:11434'):
        self.model,self.base_url=model,base_url
    def complete(self,prompt,max_tokens=1600,**_):
        response=httpx.post(self.base_url+'/api/generate',json={'model':self.model,'prompt':prompt,'stream':False,'options':{'num_predict':max_tokens}},timeout=120)
        response.raise_for_status(); return response.json()['response']


def provider_from_config(config):
    """Create the adapter for a configured pipeline or query stage."""
    provider = config.get('provider', 'offline')
    if provider == 'anthropic':
        return AnthropicProvider(
            model=config.get('anthropic_model'),
            input_price=config.get('input_usd_per_million'),
            output_price=config.get('output_usd_per_million'),
            cap=config.get('max_spend_usd', 40),
            key_env=config.get('anthropic_key_env', 'ANTHROPIC_API_KEY'),
            effort=config.get('anthropic_effort', 'low'),
            thinking=config.get('anthropic_thinking', 'disabled'),
        )
    if provider == 'openai':
        return OpenAIProvider(
            model=config.get('openai_model'),
            input_price=config.get('input_usd_per_million'),
            output_price=config.get('output_usd_per_million'),
            cap=config.get('max_spend_usd', 40),
        )
    if provider == 'ollama':
        model = config.get('ollama_model')
        if not model:
            raise ValueError('ollama_model is required')
        return OllamaProvider(model, config.get('ollama_base_url', 'http://127.0.0.1:11434'))
    if provider in ('offline', 'authored'):
        raise ValueError('Offline mode makes no model calls; use scripts.demo for the local corpus')
    raise ValueError('Unsupported model provider; choose anthropic, openai or ollama')
