import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.db import Base
from app.models import Organization, Project, Participant, Trip
from app.chatgpt_connector_readonly import (
    project_summary, recent_trips, monitoring_alerts, ConnectorAccessDenied,
)


class ConnectorTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                                    poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        for n in (1, 2):
            self.db.add(Organization(id=f"org{n}", name=f"Org {n}"))
            self.db.add(Project(id=f"project{n}", organization_id=f"org{n}",
                                code=f"P{n}", name=f"Project {n}", address=""))
            self.db.add(Trip(id=f"trip{n}", organization_id=f"org{n}",
                             project_id=f"project{n}", truck_asset_id=f"truck{n}",
                             driver_participant_id=f"driver{n}", trip_number=n,
                             status="queued"))
        self.owner = Participant(id="owner1", organization_id="org1",
                                 project_id="project1", display_name="Owner",
                                 role="owner", status="active")
        self.viewer = Participant(id="viewer1", organization_id="org1",
                                  project_id="project1", display_name="Viewer",
                                  role="client_viewer", status="active")
        self.db.add_all([self.owner, self.viewer])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_tenant_isolation(self):
        summary = project_summary(self.db, self.owner)
        self.assertEqual(summary["trips_total"], 1)
        self.assertEqual(recent_trips(self.db, self.owner)["trips"][0]["id"], "trip1")

    def test_inactive_and_foreign_project_denied(self):
        self.owner.status = "inactive"
        with self.assertRaises(ConnectorAccessDenied):
            project_summary(self.db, self.owner)
        self.owner.status = "active"
        self.owner.organization_id = "org2"
        with self.assertRaises(ConnectorAccessDenied):
            recent_trips(self.db, self.owner)

    def test_viewer_cannot_read_internal_alerts(self):
        with self.assertRaises(ConnectorAccessDenied):
            monitoring_alerts(self.db, self.viewer)

    def test_limit_validation(self):
        with self.assertRaises(ValueError):
            recent_trips(self.db, self.owner, 101)


if __name__ == "__main__":
    unittest.main()
