from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from .db import Base

def utcnow(): return datetime.now(timezone.utc)

class Organization(Base):
    __tablename__ = "site_link_organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    core_organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Project(Base):
    __tablename__ = "site_link_projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("site_link_organizations.id"), index=True)
    core_project_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    address: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Participant(Base):
    __tablename__ = "site_link_participants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("site_link_organizations.id"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("site_link_projects.id"), index=True)
    core_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), default="")
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    asset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")

class Asset(Base):
    __tablename__ = "site_link_assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("site_link_organizations.id"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("site_link_projects.id"), index=True)
    core_asset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(24), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    registration: Mapped[str] = mapped_column(String(30), default="")
    capacity_m3: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="available")

class Shift(Base):
    __tablename__ = "site_link_shifts"
    __table_args__ = (Index("ux_site_link_one_open_shift", "participant_id", unique=True, sqlite_where=text("status = 'open'"), postgresql_where=text("status = 'open'")),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), index=True)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    participant_id: Mapped[str] = mapped_column(String(36), index=True)
    asset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="open")

class Invitation(Base):
    __tablename__ = "site_link_invitations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), index=True)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    participant_id: Mapped[str] = mapped_column(String(36), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class WebSession(Base):
    __tablename__ = "site_link_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    participant_id: Mapped[str] = mapped_column(String(36), index=True)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class GpsPoint(Base):
    __tablename__ = "site_link_gps_points"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[str] = mapped_column(String(36), index=True)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    participant_id: Mapped[str] = mapped_column(String(36), index=True)
    asset_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    shift_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    device_event_id: Mapped[str] = mapped_column(String(80), unique=True)

class Trip(Base):
    __tablename__ = "site_link_trips"
    __table_args__ = (
        UniqueConstraint("project_id", "trip_number", name="uq_site_link_project_trip_number"),
        Index("ux_site_link_active_trip_per_truck", "truck_asset_id", unique=True, sqlite_where=text("status NOT IN ('completed','cancelled')"), postgresql_where=text("status NOT IN ('completed','cancelled')")),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), index=True)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    truck_asset_id: Mapped[str] = mapped_column(String(36), index=True)
    driver_participant_id: Mapped[str] = mapped_column(String(36), index=True)
    shift_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    trip_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    loading_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    loaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disposal_arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class LoadTicket(Base):
    __tablename__ = "site_link_load_tickets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), index=True)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    trip_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    truck_asset_id: Mapped[str] = mapped_column(String(36), index=True)
    excavator_asset_id: Mapped[str] = mapped_column(String(36))
    operator_participant_id: Mapped[str] = mapped_column(String(36))
    volume_m3: Mapped[float] = mapped_column(Float)
    volume_basis: Mapped[str] = mapped_column(String(30), default="operator_estimate")
    confidence: Mapped[str] = mapped_column(String(20), default="estimated")
    confirmed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Quantity(Base):
    __tablename__ = "site_link_quantities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), index=True)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    trip_id: Mapped[str] = mapped_column(String(36), index=True)
    quantity_type: Mapped[str] = mapped_column(String(30), default="loose_loaded_m3")
    quantity_value: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(30), default="operator_estimate")
    verification_status: Mapped[str] = mapped_column(String(20), default="verified")
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Event(Base):
    __tablename__ = "site_link_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), index=True)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    participant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[str] = mapped_column(String(36))
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
