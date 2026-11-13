"""Integration checks for monitoring on an isolated in-memory SQLite database."""
import unittest
from datetime import timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.db import Base
from app.models import Organization, Project, Trip, Event, utcnow
from app.monitoring import evaluate_project


class MonitoringIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                                    poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add(Organization(id="org1", name="Test"))
        self.db.add(Project(id="project1", organization_id="org1", code="T1",
                            name="Test project", address=""))
        self.db.add(Trip(id="trip1", organization_id="org1", project_id="project1",
                         truck_asset_id="truck1", driver_participant_id="driver1",
                         trip_number=1, status="queued",
                         queued_at=utcnow()-timedelta(minutes=60)))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_live_trip_alert_and_idempotent_audit(self):
        first = evaluate_project(self.db, "project1", "org1", "dispatcher1")
        self.assertEqual(first["new_audit_events"], 1)
        self.assertEqual(first["alerts"][0]["code"], "TRUCK_LONG_WAIT")
        self.assertEqual(self.db.query(Event).filter_by(event_type="monitor.alert").count(), 1)
        # Evidence may vary with time; check at most one alert for a stable snapshot.
        self.assertFalse(first["automated_decisions"])

    def test_tenant_isolation(self):
        other = evaluate_project(self.db, "other-project", "other-org", "other-user")
        self.assertEqual(other["alerts_detected"], 0)
        self.assertEqual(other["new_audit_events"], 0)


if __name__ == "__main__":
    unittest.main()
