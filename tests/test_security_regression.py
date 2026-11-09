"""Security and failure-path checks for the isolated pilot database."""
from tests.test_pilot_flow import app
from fastapi.testclient import TestClient


def test_security_and_boundaries():
    with TestClient(app) as dispatcher:
        assert dispatcher.get('/api/dashboard').status_code == 401
        assert dispatcher.post('/login', data={'password': 'incorrect'}, follow_redirects=False).status_code == 401
        assert dispatcher.post('/login', data={'password': 'test-only-password-2026'}, follow_redirects=False).status_code == 303
        assert dispatcher.get('/health').json()['database'] == 'connected'
        assets = dispatcher.get('/api/assets').json()
        truck = next(a['id'] for a in assets if a['code'] == 'KAMION-01')
        assert dispatcher.post('/api/invitations', json={'display_name':'Bad','role':'driver','asset_id':'invalid'}).status_code == 400
        assert dispatcher.post('/api/trips/not-a-real-trip/action', json={'action':'depart'}).status_code == 404
        assert dispatcher.post('/api/trips/new', headers={'Origin':'https://attacker.example'}).status_code == 403
        assert dispatcher.post('/logout', follow_redirects=False).status_code == 303
        assert dispatcher.get('/api/me').status_code == 401
