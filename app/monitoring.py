"""Authenticated, read-only operational analysis with persisted audit signals.

The scanner never changes trips, GPS, assignments, or financial records.
Each unique signal is written once to the existing site_link_events ledger.
"""
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session
from .db import get_db
from .models import Trip, Asset, LoadTicket, Event, utcnow
from .operations_monitor import analyze_snapshot

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


def build_snapshot(db: Session, project_id: str, now: datetime | None = None) -> dict:
    """Derive only observable facts; missing cost/telemetry is never fabricated."""
    now = now or utcnow()
    trips = db.query(Trip).filter_by(project_id=project_id).order_by(desc(Trip.created_at)).limit(500).all()
    tickets = {x.trip_id: x for x in db.query(LoadTicket).filter_by(project_id=project_id).all()}
    snapshot = {"trucks": [], "machines": [], "trips": []}
    for trip in trips:
        if trip.status == "queued" and trip.queued_at:
            since = trip.queued_at.replace(tzinfo=timezone.utc) if trip.queued_at.tzinfo is None else trip.queued_at
            wait_minutes = max(0, (now - since).total_seconds() / 60)
            snapshot["trucks"].append({"id": trip.truck_asset_id, "waiting_minutes": round(wait_minutes, 2)})
        ticket = tickets.get(trip.id)
        # No delivery-proof flag exists in the base Trip schema; avoid asserting absence.
        # A completed trip with no load ticket is independently verifiable.
        snapshot["trips"].append({"id": trip.id, "status": trip.status,
                                  "has_load_ticket": ticket is not None})
    return snapshot


def evaluate_project(db: Session, project_id: str, organization_id: str,
                     actor_id: str) -> dict:
    snapshot = build_snapshot(db, project_id)
    alerts = analyze_snapshot(snapshot)
    for trip in snapshot["trips"]:
        if trip["status"] == "completed" and not trip["has_load_ticket"]:
            alerts.append({
                "code": "COMPLETED_TRIP_WITHOUT_LOAD_TICKET",
                "severity": "warning", "entity_type": "trip", "entity_id": trip["id"],
                "evidence": {"status": "completed", "has_load_ticket": False},
                "recommendation": "Провери товарителницата и потвърждението за курса.",
                "observed_at": utcnow().isoformat(), "source": "rule_engine_v1",
                "requires_human_review": True,
            })
    inserted = 0
    for alert in alerts:
        # Stable ID for an unchanged signal: repeated scans do not spam the audit ledger.
        fingerprint = json.dumps([project_id, alert["code"], alert["entity_id"],
                                  utcnow().date().isoformat()], sort_keys=True, ensure_ascii=False)
        event_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "bager-monitor-v1:" + fingerprint))
        if db.get(Event, event_id) is not None:
            continue
        db.add(Event(id=event_id, organization_id=organization_id, project_id=project_id,
                     participant_id=actor_id, event_type="monitor.alert",
                     entity_type=alert["entity_type"], entity_id=alert["entity_id"],
                     payload_json=json.dumps(alert, ensure_ascii=False),
                     occurred_at=utcnow(), recorded_at=utcnow()))
        inserted += 1
    db.commit()
    return {"rules_engine": "v1", "scanned_trips": len(snapshot["trips"]),
            "alerts_detected": len(alerts), "new_audit_events": inserted,
            "alerts": alerts, "automated_decisions": False}


def register_routes(require_roles):
    """Avoid a circular import with main's existing authentication dependencies."""
    @router.post("/scan")
    def scan(p=Depends(require_roles("owner", "dispatcher", "site_manager")),
             db: Session = Depends(get_db)):
        return evaluate_project(db, p.project_id, p.organization_id, p.id)

    @router.get("/alerts")
    def history(p=Depends(require_roles("owner", "dispatcher", "site_manager")),
                db: Session = Depends(get_db)):
        rows = (db.query(Event).filter_by(project_id=p.project_id,
                                         organization_id=p.organization_id,
                                         event_type="monitor.alert")
                .order_by(desc(Event.recorded_at)).limit(100).all())
        return [{"id": row.id, "recorded_at": row.recorded_at.isoformat(),
                 "alert": json.loads(row.payload_json)} for row in rows]
