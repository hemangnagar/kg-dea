"""Optional provider boundary. Offline pipeline never invokes these adapters.

Every paid request reserves an upper bound BEFORE network I/O. Uncertain failures
retain reservations. Prices must be explicitly configured from current provider pricing.
"""
import os
import math
import httpx
from .store import connect

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
    def __init__(self,model,input_price,output_price,cap=40):
        if not model or not all(math.isfinite(p) and p>0 for p in [input_price,output_price]):raise ValueError('Explicit model and verified positive token prices required')
        if not os.getenv('ANTHROPIC_API_KEY'):raise ValueError('ANTHROPIC_API_KEY is not configured')
        self.model,self.ip,self.op=model,input_price,output_price
        self.accountant=TokenAccountant(cap)

    def complete(self,prompt,max_tokens=1600):
        # UTF-8 byte count conservatively bounds input tokens; output has an enforced ceiling.
        cost=((len(prompt.encode())+len(self.model.encode())+1024)*self.ip+max_tokens*self.op)/1e6
        reservation=self.accountant.reserve('anthropic','messages',cost)
        response=httpx.post('https://api.anthropic.com/v1/messages',headers={'x-api-key':os.environ['ANTHROPIC_API_KEY'],'anthropic-version':'2023-06-01'},json={'model':self.model,'max_tokens':max_tokens,'messages':[{'role':'user','content':prompt}]},timeout=120)
        response.raise_for_status(); data=response.json(); usage=data['usage']
        self.accountant.settle(reservation,usage['input_tokens'],usage['output_tokens'],self.ip,self.op)
        return ''.join(block.get('text','') for block in data['content'])

class OllamaProvider:
    def __init__(self,model,base_url='http://127.0.0.1:11434'):
        self.model,self.base_url=model,base_url
    def complete(self,prompt,max_tokens=1600):
        response=httpx.post(self.base_url+'/api/generate',json={'model':self.model,'prompt':prompt,'stream':False,'options':{'num_predict':max_tokens}},timeout=120)
        response.raise_for_status(); return response.json()['response']
