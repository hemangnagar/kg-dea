from fastapi.testclient import TestClient


def client():
    from inteldoc import app as web
    return TestClient(web.app)


def test_without_password_everything_is_open(monkeypatch):
    monkeypatch.delenv('INTELDOC_PASSWORD', raising=False)
    c = client()
    assert c.get('/').status_code == 200
    assert c.get('/api/health').status_code == 200
    assert c.get('/login', follow_redirects=False).status_code == 303


def test_login_gates_pages_and_api(monkeypatch):
    monkeypatch.setenv('INTELDOC_PASSWORD', 'correct horse')
    c = client()
    r = c.get('/?x=1', follow_redirects=False)
    assert r.status_code == 303 and r.headers['location'] == '/login?next=%2F%3Fx%3D1'
    assert c.get('/api/stats').status_code == 401
    assert c.get('/api/health').status_code == 200
    page = c.get('/login?next=/api/stats')
    assert page.status_code == 200 and 'Sign in' in page.text
    bad = c.post('/login', data={'password': 'wrong', 'next': '/'})
    assert bad.status_code == 401 and 'not accepted' in bad.text and 'inteldoc_session' not in c.cookies
    ok = c.post('/login', data={'password': 'correct horse', 'next': '/api/stats'}, follow_redirects=False)
    assert ok.status_code == 303 and ok.headers['location'] == '/api/stats' and 'inteldoc_session' in c.cookies
    assert c.get('/').status_code == 200
    assert c.get('/api/stats').status_code == 200
    assert c.get('/logout', follow_redirects=False).status_code == 303
    assert c.get('/', follow_redirects=False).status_code == 303


def test_next_cannot_leave_the_site(monkeypatch):
    monkeypatch.setenv('INTELDOC_PASSWORD', 'pw')
    c = client()
    r = c.post('/login', data={'password': 'pw', 'next': 'https://evil.example/'}, follow_redirects=False)
    assert r.headers['location'] == '/'
    r = c.post('/login', data={'password': 'pw', 'next': '//evil.example/'}, follow_redirects=False)
    assert r.headers['location'] == '/'
