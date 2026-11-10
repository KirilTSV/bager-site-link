import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('BAGER_ADMIN_PASSWORD','test-only-password-2026')
os.environ.setdefault('DATABASE_URL','sqlite:///'+os.environ['BAGER_TEST_DB'])
from fastapi.testclient import TestClient
from app.main import app
from tests.test_pilot_flow import invite_and_join

def test_gps_idempotency_and_owner():
    with TestClient(app) as admin:
        assert admin.post('/login',data={'password':'test-only-password-2026'},follow_redirects=False).status_code==303
        assets=admin.get('/api/assets').json()
        truck1=next(a['id'] for a in assets if a['code']=='KAMION-01')
        truck2=next(a['id'] for a in assets if a['code']=='KAMION-02')
        d1=invite_and_join(admin,'GPS Driver A','driver',truck1)
        d2=invite_and_join(admin,'GPS Driver B','driver',truck2)
        assert d1.post('/api/shift/start').status_code==200
        assert d2.post('/api/shift/start').status_code==200
        point={'latitude':42.7,'longitude':23.3,'accuracy_m':8,'device_event_id':'gps-integrity-id-001'}
        assert d1.post('/api/gps',json=point).status_code==200
        dup=d1.post('/api/gps',json=point)
        assert dup.status_code==200 and dup.json()['duplicate'] is True
        collision=d2.post('/api/gps',json=point)
        assert collision.status_code==409
        assert d1.post('/api/gps',json={**point,'device_event_id':'x'*81}).status_code==422
        assert d1.post('/api/shift/end').status_code==200
        # Retry of an already persisted event must still be acknowledged after shift end.
        after_close=d1.post('/api/gps',json=point)
        assert after_close.status_code==200 and after_close.json()['duplicate'] is True
        # Reusing the ID with a different payload is a conflict, never an ACK.
        collision_payload=d1.post('/api/gps',json={**point,'latitude':42.8})
        assert collision_payload.status_code==409
        assert d1.post('/api/shift/start').status_code==200
        assert d1.post('/api/gps',json={**point,'device_event_id':'old-before-shift','recorded_at':'2026-01-01T00:00:00Z'}).status_code in (409,422)
        assert d1.post('/api/shift/end').status_code==200
        assert d1.post('/api/gps',json={**point,'device_event_id':'gps-new-after-end'}).status_code==409
