"""Pilot live operations: approved disposal sites and per-truck daily assignments.

All endpoints are authenticated and scoped to the participant's project.
This module does not change existing trip or GPS tables.
"""
import uuid
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import String, Float, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, Session
from .db import Base, get_db

router = APIRouter(prefix="/api/operations", tags=["operations"])

def now():
    return datetime.now(timezone.utc)

class DisposalSite(Base):
    __tablename__ = "site_link_disposal_sites"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("site_link_projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    address: Mapped[str] = mapped_column(String(300))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(24), default="pending_verification")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class DailyAssignment(Base):
    __tablename__ = "site_link_daily_assignments"
    __table_args__ = (UniqueConstraint("project_id", "work_date", "truck_asset_id", name="uq_ops_truck_day"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("site_link_projects.id"), index=True)
    work_date: Mapped[date] = mapped_column(Date)
    truck_asset_id: Mapped[str] = mapped_column(ForeignKey("site_link_assets.id"))
    driver_participant_id: Mapped[str] = mapped_column(ForeignKey("site_link_participants.id"))
    disposal_site_id: Mapped[str] = mapped_column(ForeignKey("site_link_disposal_sites.id"))
    created_by: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class SiteIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    address: str = Field(min_length=3, max_length=300)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

class AssignmentIn(BaseModel):
    work_date: date
    truck_asset_id: str
    driver_participant_id: str
    disposal_site_id: str

def actor(request: Request, db: Session):
    from .main import current_participant
    p = current_participant(request, db)
    if not p:
        raise HTTPException(401, "Няма активна сесия")
    return p

def supervisor(p):
    if p.role not in ("owner", "dispatcher", "site_manager"):
        raise HTTPException(403, "Нямате права за това действие")

def site_json(s):
    return {"id": s.id, "name": s.name, "address": s.address,
            "latitude": s.latitude, "longitude": s.longitude, "status": s.status}

@router.post("/disposal-sites", status_code=201)
def create_site(data: SiteIn, request: Request, db: Session = Depends(get_db)):
    p = actor(request, db)
    supervisor(p)
    s = DisposalSite(id=str(uuid.uuid4()), organization_id=p.organization_id,
                     project_id=p.project_id, name=data.name.strip(), address=data.address.strip(),
                     latitude=data.latitude, longitude=data.longitude)
    db.add(s)
    db.commit()
    return site_json(s)

@router.get("/disposal-sites")
def list_sites(request: Request, db: Session = Depends(get_db)):
    p = actor(request, db)
    return [site_json(s) for s in db.query(DisposalSite).filter_by(project_id=p.project_id).all()]

@router.post("/disposal-sites/{site_id}/approve")
def approve_site(site_id: str, request: Request, db: Session = Depends(get_db)):
    p = actor(request, db)
    supervisor(p)
    s = db.query(DisposalSite).filter_by(id=site_id, project_id=p.project_id).first()
    if not s:
        raise HTTPException(404, "Разтоварището не е намерено")
    # Operational approval only; regulatory compliance remains a separate verification.
    s.status = "approved"
    db.commit()
    return site_json(s)

@router.post("/daily-assignments", status_code=201)
def create_assignment(data: AssignmentIn, request: Request, db: Session = Depends(get_db)):
    from .models import Asset, Participant
    p = actor(request, db)
    supervisor(p)
    truck = db.query(Asset).filter_by(id=data.truck_asset_id, project_id=p.project_id, asset_type="dump_truck").first()
    driver = db.query(Participant).filter_by(id=data.driver_participant_id, project_id=p.project_id, role="driver", status="active").first()
    site = db.query(DisposalSite).filter_by(id=data.disposal_site_id, project_id=p.project_id, status="approved").first()
    if not truck or not driver or not site:
        raise HTTPException(400, "Невалиден камион, шофьор или неодобрено разтоварище")
    if driver.asset_id != truck.id:
        raise HTTPException(400, "Шофьорът не е назначен към този камион")
    existing = db.query(DailyAssignment).filter_by(project_id=p.project_id, work_date=data.work_date, truck_asset_id=truck.id).first()
    if existing:
        raise HTTPException(409, "Камионът вече има задание за този ден")
    a = DailyAssignment(id=str(uuid.uuid4()), organization_id=p.organization_id,
                        project_id=p.project_id, work_date=data.work_date,
                        truck_asset_id=truck.id, driver_participant_id=driver.id,
                        disposal_site_id=site.id, created_by=p.id)
    db.add(a)
    db.commit()
    return {"id": a.id, "work_date": a.work_date.isoformat(), "truck_asset_id": a.truck_asset_id,
            "driver_participant_id": a.driver_participant_id, "disposal_site": site_json(site)}

@router.get("/daily-assignments")
def list_assignments(request: Request, work_date: date, db: Session = Depends(get_db)):
    p = actor(request, db)
    rows = db.query(DailyAssignment).filter_by(project_id=p.project_id, work_date=work_date).all()
    if p.role == "driver":
        rows = [a for a in rows if a.driver_participant_id == p.id]
    result = []
    for a in rows:
        site = db.get(DisposalSite, a.disposal_site_id)
        result.append({"id": a.id, "work_date": a.work_date.isoformat(),
                       "truck_asset_id": a.truck_asset_id,
                       "driver_participant_id": a.driver_participant_id,
                       "disposal_site": site_json(site)})
    return result
