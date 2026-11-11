"""Trip destination snapshot and unload evidence acceptance checks."""
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient
from app.asgi import app
from app.db import SessionLocal
from app.models import Asset, Participant, Trip
from app.operations import TripDestination, DailyAssignment


def test_trip_requires_daily_assignment_and_preserves_destination():
    with TestClient(app) as client:
        assert client.post("/login",data={"password":"ci-test-only"},follow_redirects=False).status_code==303
        with SessionLocal() as db:
            db.query(DailyAssignment).delete()
            db.commit()
            truck=db.query(Asset).filter_by(asset_type="dump_truck").order_by(Asset.code.desc()).first()
            driver=Participant(id=str(uuid.uuid4()),organization_id=truck.organization_id,project_id=truck.project_id,display_name="Trip test driver",role="driver",asset_id=truck.id)
            db.add(driver); db.commit()
            truck_id,driver_id=truck.id,driver.id
        assert client.post("/api/trips/new").status_code==409
        site=client.post("/api/operations/disposal-sites",json={"name":"Approved pilot site","address":"Sofia pilot disposal site","latitude":42.7,"longitude":23.3})
        assert site.status_code==201,site.text
        sid=site.json()["id"]
        assert client.post(f"/api/operations/disposal-sites/{sid}/approve").status_code==200
        day=datetime.now(ZoneInfo("Europe/Sofia")).date().isoformat()
        assignment=client.post("/api/operations/daily-assignments",json={"work_date":day,"truck_asset_id":truck_id,"driver_participant_id":driver_id,"disposal_site_id":sid})
        assert assignment.status_code==201,assignment.text
        created=client.post("/api/trips/new")
        assert created.status_code==200,created.text
        tid=created.json()["trip_id"]
        assert created.json()["disposal_site"]["id"]==sid
        rows=client.get("/api/trips").json()
        assert next(x for x in rows if x["id"]==tid)["disposal_site"]["name"]=="Approved pilot site"
        with SessionLocal() as db:
            snapshot=db.get(TripDestination,tid)
            assert snapshot.site_name=="Approved pilot site"
            assert snapshot.assignment_id==assignment.json()["id"]
        for action in ["loading_start","loaded","depart","arrived_disposal","unloaded"]:
            response=client.post(f"/api/trips/{tid}/action",json={"action":action})
            assert response.status_code==200,(action,response.text)
        rows=client.get("/api/trips").json()
        item=next(x for x in rows if x["id"]==tid)
        assert item["unload_verification"]=="gps_unavailable"
        assert item["unload_distance_m"] is None
        with SessionLocal() as db:
            assert db.get(TripDestination,tid).disposal_site_id==sid
