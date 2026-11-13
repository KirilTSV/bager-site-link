"""Read-only tool service intended for a future authenticated ChatGPT MCP adapter.

Not a public MCP server. The caller MUST supply a verified, active participant
from the application's existing authentication layer. Never accept a user-supplied
project/organization ID as authority. No SQL writes or background jobs here.
"""
import json
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from .models import Project, Trip, Asset, LoadTicket, Event


class ConnectorAccessDenied(PermissionError):
    pass


ALLOWED_ROLES = frozenset({"owner", "dispatcher", "site_manager", "client_viewer"})


def _scope(db: Session, actor):
    if actor is None or actor.status != "active" or actor.role not in ALLOWED_ROLES:
        raise ConnectorAccessDenied("No authorized active participant")
    project = db.query(Project).filter_by(
        id=actor.project_id, organization_id=actor.organization_id
    ).first()
    if project is None:
        raise ConnectorAccessDenied("Participant project is not valid")
    return project


def project_summary(db: Session, actor) -> dict:
    """Safe operational aggregates; client viewers never receive personnel or GPS."""
    project = _scope(db, actor)
    q = db.query(Trip).filter_by(project_id=project.id,
                                 organization_id=project.organization_id)
    counts = dict(q.with_entities(Trip.status, func.count(Trip.id)).group_by(Trip.status).all())
    tickets = db.query(LoadTicket).filter_by(project_id=project.id,
                                            organization_id=project.organization_id).all()
    return {
        "project_id": project.id, "project_name": project.name,
        "trips_by_status": counts, "trips_total": sum(counts.values()),
        "confirmed_volume_m3": round(sum(x.volume_m3 for x in tickets if x.confidence == "confirmed"), 3),
        "estimated_volume_m3": round(sum(x.volume_m3 for x in tickets if x.confidence != "confirmed"), 3),
        "volume_basis": "load_tickets", "source": "bager_site_link_database",
        "scope": "current_participant_project", "read_only": True,
    }


def recent_trips(db: Session, actor, limit: int = 20) -> dict:
    project = _scope(db, actor)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer from 1 to 100")
    trips = (db.query(Trip).filter_by(project_id=project.id,
                                     organization_id=project.organization_id)
             .order_by(desc(Trip.created_at)).limit(limit).all())
    # No driver names, location coordinates or personal identifiers.
    return {"project_id": project.id, "source": "bager_site_link_database",
            "read_only": True,
            "trips": [{"id": t.id, "number": t.trip_number, "status": t.status,
                       "created_at": t.created_at.isoformat() if t.created_at else None}
                      for t in trips]}


def monitoring_alerts(db: Session, actor, limit: int = 20) -> dict:
    project = _scope(db, actor)
    if actor.role == "client_viewer":
        raise ConnectorAccessDenied("Monitoring alerts are not available to client viewers")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer from 1 to 100")
    rows = (db.query(Event).filter_by(project_id=project.id,
                                     organization_id=project.organization_id,
                                     event_type="monitor.alert")
            .order_by(desc(Event.recorded_at)).limit(limit).all())
    return {"project_id": project.id, "source": "bager_site_link_audit_events",
            "read_only": True,
            "alerts": [{"event_id": row.id, "recorded_at": row.recorded_at.isoformat(),
                        "data": json.loads(row.payload_json)}
                       for row in rows]}
