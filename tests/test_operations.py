"""Operational snapshot contract: isolated SQLite database, no production access."""
import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("BAGER_ADMIN_PASSWORD", "test-only-password-2026")
_tmp = tempfile.TemporaryDirectory(prefix="bager-operations-")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_tmp.name) / "ops.db")
os.environ.setdefault("COOKIE_SECURE", "0")
from fastapi.testclient import TestClient
from app.main import app

def test_operations_empty_fleet_and_role_guard():
    with TestClient(app) as client:
        assert client.get("/api/operations").status_code in (401, 403)
        login=client.post("/login", data={"password":"test-only-password-2026"}, follow_redirects=False)
        assert login.status_code==303
        r=client.get("/api/operations")
        assert r.status_code==200, r.text
        data=r.json()
        assert data["volume_unit"]=="loose_loaded_m3"
        assert data["completed_trips"]==0
        assert data["confirmed_loose_m3"]==0
        assert len(data["fleet"])==2
        assert len(data["excavators"])==1
        for truck in data["fleet"]:
            assert truck["gps"] is None
            assert truck["cargo_m3"] is None
            assert truck["completed_trips"]==0
            assert truck["status"]=="no_driver"
        assert data["excavators"][0]["indicative_loading_m3_per_hour"] is None
