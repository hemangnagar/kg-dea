"""Password login for the demo workbench.

Enabled when INTELDOC_PASSWORD is set (the deploy kit writes it to /etc/inteldoc.env). With it unset, as in local
development and the tests, every request passes. The login replaces HTTP basic authentication, whose browser prompt
some corporate proxies suppress. One shared password, one session cookie, no accounts: it keeps the synthetic demo
off the open internet and nothing more.
"""
import hashlib
import hmac
import html
import os
import secrets
from urllib.parse import parse_qs, quote, urlparse
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

COOKIE = 'inteldoc_session'
MAX_AGE = 12 * 3600
OPEN_PATHS = {'/login', '/logout', '/api/health', '/favicon.ico'}
_SALT = secrets.token_bytes(16)  # per-process: restarting the service signs everyone out


def password():
    return os.environ.get('INTELDOC_PASSWORD') or ''


def token():
    return hmac.new(_SALT, hashlib.sha256(password().encode()).digest(), hashlib.sha256).hexdigest()


def authenticated(request):
    return not password() or hmac.compare_digest(request.cookies.get(COOKIE, ''), token())


def secure(request):
    return request.headers.get('x-forwarded-proto', request.url.scheme) == 'https'


def safe_next(value):
    """Only same-site paths, so the login page cannot be used as an open redirect."""
    value = value or '/'
    parsed = urlparse(value)
    return value if value.startswith('/') and not value.startswith('//') and not parsed.netloc else '/'


PAGE = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>IntelDoc KG · Sign in</title><style>
:root{--bg:#0d1117;--panel:#141b23;--line:#29323e;--muted:#91a0b2;--text:#e5ebf1;--accent:#b9e681}
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--bg);color:var(--text);font:14px system-ui,-apple-system,sans-serif;padding:16px}
.card{width:100%;max-width:400px;background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:34px 32px}
.brand{font-size:22px;font-weight:650;letter-spacing:-1px;margin-bottom:6px}.brand span{color:var(--muted);font-weight:350}
.eyebrow{font:10px monospace;letter-spacing:2px;color:var(--accent);margin-bottom:22px}label{display:block;color:var(--muted);font-size:12px;margin:18px 0 6px}
input{width:100%;background:#1b242e;border:1px solid var(--line);color:var(--text);padding:11px;border-radius:5px;font:inherit}input:focus{outline:2px solid var(--accent);outline-offset:2px}
button{width:100%;margin-top:22px;background:var(--accent);color:#182111;border:0;border-radius:5px;padding:12px;font:inherit;font-weight:600;cursor:pointer}
.error{color:#ffaf99;font-size:12px;margin-top:14px}.note{color:var(--muted);font-size:11px;line-height:1.7;margin-top:22px}
</style></head><body><form class="card" method="post" action="/login"><div class="brand">IntelDoc <span>/ KG</span></div><div class="eyebrow">SYNTHETIC ENVIRONMENT · SIGN IN</div>
<label for="username">Username</label><input id="username" name="username" value="demo" autocomplete="username">
<label for="password">Password</label><input id="password" name="password" type="password" autocomplete="current-password" autofocus required>
<input type="hidden" name="next" value="{next}"><button type="submit">Sign in ↗</button>{error}
<p class="note">Fictional training data. Every organization, person, company and document is invented; only the geography is real.</p></form></body></html>'''


def render(next_path, error=''):
    body = PAGE.replace('{next}', html.escape(next_path)).replace('{error}', f'<div class="error">{html.escape(error)}</div>' if error else '')
    return HTMLResponse(body, status_code=401 if error else 200, headers={'Cache-Control': 'no-store'})


def install(app):
    @app.middleware('http')
    async def require_login(request: Request, call_next):
        path = request.url.path
        if path in OPEN_PATHS or authenticated(request):
            return await call_next(request)
        if path.startswith('/api/'):
            return JSONResponse({'detail': 'Sign in required'}, status_code=401)
        target = path + ('?' + request.url.query if request.url.query else '')
        return RedirectResponse(f'/login?next={quote(target, safe="")}', status_code=303)

    @app.get('/login', response_class=HTMLResponse)
    def login_form(request: Request, next: str = '/'):
        if authenticated(request):
            return RedirectResponse(safe_next(next), status_code=303)
        return render(safe_next(next))

    @app.post('/login')
    async def login(request: Request):
        form = parse_qs((await request.body()).decode('utf-8', 'replace'))
        supplied = form.get('password', [''])[0]
        next_path = safe_next(form.get('next', ['/'])[0])
        if not password() or not hmac.compare_digest(supplied, password()):
            return render(next_path, 'That password was not accepted.')
        response = RedirectResponse(next_path, status_code=303)
        response.set_cookie(COOKIE, token(), max_age=MAX_AGE, httponly=True, samesite='lax', secure=secure(request))
        return response

    @app.get('/logout')
    def logout():
        response = RedirectResponse('/login', status_code=303)
        response.delete_cookie(COOKIE)
        return response
