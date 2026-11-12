"""Isolated API smoke test. Never connects to production database."""
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


class TripWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(cls.temp.name) / "test.db")
        os.environ["BAGER_ADMIN_PASSWORD"] = "test-only-not-production"
        from app.main import app
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.temp.cleanup()

    def test_trip_cycle_and_permissions(self):
        c = self.client
        self.assertEqual(c.get("/api/me").status_code, 401)
        self.assertEqual(c.post("/login", data={"password": "incorrect"}, follow_redirects=False).status_code, 401)
        response = c.post("/login", data={"password": "test-only-not-production"}, follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(c.get("/api/me").status_code, 200)

        # The seed creates two trucks. Invite a driver for each one.
        from app.db import SessionLocal
        from app.models import Asset
        with SessionLocal() as db:
            trucks = db.query(Asset).filter_by(asset_type="dump_truck").order_by(Asset.code).all()
            ids = [truck.id for truck in trucks]
        self.assertEqual(len(ids), 2)
        for i, asset_id in enumerate(ids):
            r = c.post("/api/invitations", json={
                "display_name": f"Test Driver {i+1}", "role": "driver", "asset_id": asset_id
            })
            self.assertEqual(r.status_code, 200, r.text)

        trip_ids = []
        for _ in range(2):
            r = c.post("/api/trips/new")
            self.assertEqual(r.status_code, 200, r.text)
            trip_ids.append(r.json()["trip_id"])
        self.assertEqual(c.post("/api/trips/new").status_code, 409)

        for trip_id in trip_ids:
            self.assertEqual(c.post(f"/api/trips/{trip_id}/action", json={"action": "depart"}).status_code, 409)
            for action in ("loading_start", "loaded"):
                r = c.post(f"/api/trips/{trip_id}/action", json={"action": action})
                self.assertEqual(r.status_code, 200, r.text)
            r = c.post("/api/load-ticket", json={"trip_id": trip_id, "volume_m3": 8.5})
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(c.post("/api/load-ticket", json={"trip_id": trip_id, "volume_m3": 8.5}).status_code, 409)
            for action in ("depart", "arrived_disposal", "unloaded", "returned"):
                r = c.post(f"/api/trips/{trip_id}/action", json={"action": action})
                self.assertEqual(r.status_code, 200, r.text)
        dashboard = c.get("/api/dashboard")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()["trips_completed"], 2)
        self.assertEqual(dashboard.json()["confirmed_m3"], 17.0)


if __name__ == "__main__":
    unittest.main()
