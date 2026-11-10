import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('BAGER_ADMIN_PASSWORD','test-only-password-2026')
_test_db_dir = tempfile.mkdtemp(prefix='bager_site_link_test_')
os.environ.setdefault('DATABASE_URL', 'sqlite:///' + str(Path(_test_db_dir) / 'pilot.db'))
os.environ.setdefault('COOKIE_SECURE','0')
from fastapi.testclient import TestClient
from app.main import app


def invite_and_join(dispatcher, name, role, asset_id=None):
    payload={'display_name':name,'phone':'','role':role}
    if asset_id: payload['asset_id']=asset_id
    r=dispatcher.post('/api/invitations',json=payload)
    assert r.status_code==200, r.text
    path=r.json()['invite_url']
    client=TestClient(app)
    preview=client.get(path,follow_redirects=False)
    assert preview.status_code==200, preview.text
    repeated_preview=client.get(path,follow_redirects=False)
    assert repeated_preview.status_code==200
    joined=client.post(path,follow_redirects=False)
    assert joined.status_code==303, joined.text
    assert client.post(path,follow_redirects=False).status_code==410
    return client


def test_end_to_end_pilot():
    with TestClient(app) as dispatcher:
        login=dispatcher.post('/login',data={'password':'test-only-password-2026'},follow_redirects=False)
        assert login.status_code==303
        assets=dispatcher.get('/api/assets').json()
        truck1=next(a['id'] for a in assets if a['code']=='KAMION-01')
        excavator=next(a['id'] for a in assets if a['code']=='BAGER-01')
        driver=invite_and_join(dispatcher,'Тестов шофьор 01','driver',truck1)
        truck2=next(a['id'] for a in assets if a['code']=='KAMION-02')
        driver2=invite_and_join(dispatcher,'Тестов шофьор 02','driver',truck2)
        operator=invite_and_join(dispatcher,'Тестов оператор','operator',excavator)
        assert driver.get('/api/me').json()['role']=='driver'
        assert operator.get('/api/me').json()['role']=='operator'
        assert driver.post('/api/shift/start').status_code==200
        gps=driver.post('/api/gps',json={'latitude':42.6977,'longitude':23.3219,'accuracy_m':8,'device_event_id':'test-gps-001'})
        assert gps.status_code==200, gps.text
        trip=dispatcher.post('/api/trips/new')
        assert trip.status_code==200, trip.text
        trip_id=trip.json()['trip_id']
        trip2=dispatcher.post('/api/trips/new')
        assert trip2.status_code==200, trip2.text
        assert trip2.json()['truck']=='KAMION-02'
        assert driver2.get('/api/trips').json()[0]['id']==trip2.json()['trip_id']
        assert driver.get('/api/trips').json()[0]['id']==trip_id
        for action in ['loading_start','loaded']:
            r=driver.post(f'/api/trips/{trip_id}/action',json={'action':action})
            assert r.status_code==200, r.text
        assert operator.post(f'/api/trips/{trip_id}/action',json={'action':'depart'}).status_code==403
        ticket=operator.post('/api/load-ticket',json={'trip_id':trip_id,'volume_m3':8.5,'volume_basis':'operator_estimate'})
        assert ticket.status_code==200, ticket.text
        for action in ['depart','arrived_disposal','unloaded','returned']:
            r=driver.post(f'/api/trips/{trip_id}/action',json={'action':action})
            assert r.status_code==200, r.text
        dash=dispatcher.get('/api/dashboard').json()
        assert dash['confirmed_m3']==8.5
        assert dash['trips_completed']==1
        assert dash['gps_points']==1
