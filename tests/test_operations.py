"""Isolated acceptance checks for daily assignments and scoped disposal sites."""
import uuid
from datetime import date
from fastapi.testclient import TestClient
from app.asgi import app
from app.db import SessionLocal
from app.models import Asset, Participant, Organization, Project

def test_daily_assignments_approval_and_access():
    with TestClient(app) as client:
        assert client.get("/api/operations/disposal-sites").status_code == 401
        assert client.post("/login", data={"password": "ci-test-only"}, follow_redirects=False).status_code == 303
        site = client.post("/api/operations/disposal-sites", json={
            "name": "Тестова площадка", "address": "София, тестов адрес",
            "latitude": 42.7, "longitude": 23.3})
        assert site.status_code == 201, site.text
        sid = site.json()["id"]
        assert site.json()["status"] == "pending_verification"
        with SessionLocal() as db:
            org = db.query(Organization).first()
            project = db.query(Project).filter_by(organization_id=org.id).first()
            truck = db.query(Asset).filter_by(project_id=project.id, asset_type="dump_truck").first()
            driver = Participant(id=str(uuid.uuid4()), organization_id=org.id,
                                 project_id=project.id, display_name="Тестов шофьор",
                                 role="driver", asset_id=truck.id)
            db.add(driver)
            db.commit()
            truck_id, driver_id = truck.id, driver.id
        data = {"work_date": date.today().isoformat(), "truck_asset_id": truck_id,
                "driver_participant_id": driver_id, "disposal_site_id": sid}
        assert client.post("/api/operations/daily-assignments", json=data).status_code == 400
        assert client.post(f"/api/operations/disposal-sites/{sid}/approve").status_code == 200
        created = client.post("/api/operations/daily-assignments", json=data)
        assert created.status_code == 201, created.text
        assert created.json()["disposal_site"]["id"] == sid
        assert client.post("/api/operations/daily-assignments", json=data).status_code == 409
        listed = client.get("/api/operations/daily-assignments", params={"work_date": data["work_date"]})
        assert listed.status_code == 200
        assert any(x["id"] == created.json()["id"] for x in listed.json())
        assert client.get("/api/operations/disposal-sites").status_code == 200
        alternate = client.post("/api/operations/disposal-sites", json={
            "name": "Резервна площадка", "address": "София, резервен адрес",
            "latitude": 42.72, "longitude": 23.32})
        assert alternate.status_code == 201
        other_id = alternate.json()["id"]
        assert client.post(f"/api/operations/daily-assignments/{created.json()['id']}/change-site", json={
            "new_disposal_site_id": other_id, "reason": "Смяна заради ограничен достъп"}).status_code == 400
        assert client.post(f"/api/operations/disposal-sites/{other_id}/approve").status_code == 200
        changed = client.post(f"/api/operations/daily-assignments/{created.json()['id']}/change-site", json={
            "new_disposal_site_id": other_id, "reason": "Смяна заради ограничен достъп"})
        assert changed.status_code == 200, changed.text
        assert changed.json()["disposal_site"]["id"] == other_id
        history = client.get(f"/api/operations/daily-assignments/{created.json()['id']}/history")
        assert history.status_code == 200
        assert len(history.json()) == 1
        assert history.json()[0]["previous_site_id"] == sid
        assert history.json()[0]["new_site_id"] == other_id
        updated = client.get("/api/operations/daily-assignments", params={"work_date": data["work_date"]})
        assert next(x for x in updated.json() if x["id"] == created.json()["id"])["disposal_site"]["id"] == other_id
        assert client.post(f"/api/operations/daily-assignments/{created.json()['id']}/change-site", json={
            "new_disposal_site_id": other_id, "reason": "Повторна идентична промяна"}).status_code == 409
