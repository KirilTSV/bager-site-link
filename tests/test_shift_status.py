import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('BAGER_ADMIN_PASSWORD','test-only-password-2026')
os.environ.setdefault('DATABASE_URL','sqlite:///'+os.environ['BAGER_TEST_DB'])
from fastapi.testclient import TestClient
from app.main import app

def test_shift_status_and_auth():
    with TestClient(app) as c:
        assert c.get('/api/shift/status').status_code==401
        assert c.post('/login',data={'password':'test-only-password-2026'},follow_redirects=False).status_code==303
        assert c.get('/api/shift/status').status_code==200
        if c.get('/api/shift/status').json()['active']:
            assert c.post('/api/shift/end').status_code==200
        assert c.get('/api/shift/status').json()['active'] is False
        assert c.post('/api/shift/start').status_code==200
        assert c.get('/api/shift/status').json()['active'] is True
        assert c.post('/api/shift/end').status_code==200
        assert c.get('/api/shift/status').json()['active'] is False

def test_foreign_origin_still_blocked():
    with TestClient(app) as c:
        assert c.post('/api/shift/start',headers={'Origin':'https://foreign.invalid'}).status_code==403
