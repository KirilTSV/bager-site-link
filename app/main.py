import os, uuid, hashlib, secrets, json, threading, time
from collections import defaultdict, deque
from urllib.parse import urlparse
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text
from pydantic import BaseModel, Field
from .db import Base, engine, get_db
from .marketplace import router as marketplace_router
from .models import Organization, Project, Participant, Asset, Shift, Invitation, WebSession, GpsPoint, Trip, LoadTicket, Quantity, Event, utcnow

BASE_DIR = Path(__file__).resolve().parent.parent
COOKIE = "bager_site_session"
SESSION_HOURS = int(os.getenv("SESSION_HOURS", "14"))
ADMIN_PASSWORD = os.getenv("BAGER_ADMIN_PASSWORD", "")
SECURE_COOKIE = os.getenv("COOKIE_SECURE", "0") == "1"
LOGIN_WINDOW_SECONDS = 900
LOGIN_MAX_ATTEMPTS = 8
_login_attempts = defaultdict(deque)
_login_lock = threading.Lock()
@asynccontextmanager
async def lifespan(application):
    seed()
    yield

app = FastAPI(title="BAGER SITE LINK v1.0", version="1.0.0", lifespan=lifespan)
app.include_router(marketplace_router)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.middleware("http")
async def verify_same_origin(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and not (request.method == "POST" and request.url.path.startswith("/join/")):
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc.lower() not in {request.headers.get("host", "").lower(), "bager-site-link-pilot.onrender.com"}:
            return JSONResponse({"detail": "Заявка от чужд произход е блокирана"}, status_code=403)
    return await call_next(request)
Base.metadata.create_all(bind=engine)

ROLE_LABELS = {"owner":"Собственик", "dispatcher":"Диспечер", "operator":"Оператор на багер", "driver":"Шофьор", "site_manager":"Ръководител обект", "client_viewer":"Клиент"}

class GpsIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0, le=10000)
    speed_mps: float | None = Field(default=None, ge=0, le=150)
    heading_deg: float | None = Field(default=None, ge=0, le=360)
    recorded_at: datetime | None = None
    device_event_id: str | None = Field(default=None, min_length=1, max_length=80)

class TicketIn(BaseModel):
    trip_id: str
    volume_m3: float = Field(gt=0, le=100)
    volume_basis: str = "operator_estimate"

class InviteIn(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    phone: str = ""
    role: str
    asset_id: str | None = None

class TripAction(BaseModel):
    action: str


def event(db, org, project, participant, typ, entity_type, entity_id, payload=None):
    db.add(Event(id=str(uuid.uuid4()), organization_id=org, project_id=project,
                 participant_id=participant, event_type=typ, entity_type=entity_type,
                 entity_id=str(entity_id), payload_json=json.dumps(payload or {}, ensure_ascii=False),
                 occurred_at=utcnow(), recorded_at=utcnow()))

def dt_utc(value):
    if value is None: return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value

def current_participant(request: Request, db: Session):
    sid = request.cookies.get(COOKIE)
    if not sid: return None
    s = db.get(WebSession, sid)
    if not s or dt_utc(s.expires_at) < utcnow(): return None
    p = db.get(Participant, s.participant_id)
    if not p or p.status != "active": return None
    return p

def require_user(request: Request, db: Session = Depends(get_db)):
    p = current_participant(request, db)
    if not p: raise HTTPException(401, "Няма активна сесия")
    return p

def require_roles(*roles):
    def dep(p: Participant = Depends(require_user)):
        if p.role not in roles: raise HTTPException(403, "Нямате права за това действие")
        return p
    return dep

def project_for(db, p):
    return db.get(Project, p.project_id)

def get_open_shift(db, p):
    return db.query(Shift).filter_by(participant_id=p.id, status="open").order_by(desc(Shift.started_at)).first()

def seed():
    db = next(get_db())
    try:
        if db.query(Organization).count() == 0:
            org_id, project_id = str(uuid.uuid4()), str(uuid.uuid4())
            db.add(Organization(id=org_id, name="BAGER SYSTEM — Пилот"))
            db.add(Project(id=project_id, organization_id=org_id, code="BS-PILOT-001", name="Пилотен обект — 1 багер / 2 камиона", address="София — въведете реалния адрес преди пилот", status="active"))
            db.flush()
            people = [("Пилотен диспечер", "dispatcher", "")]
            ids={}
            for name, role, phone in people:
                pid=str(uuid.uuid4()); ids[role+name]=pid
                db.add(Participant(id=pid, organization_id=org_id, project_id=project_id, display_name=name, phone=phone, role=role))
            excavator=Asset(id=str(uuid.uuid4()), organization_id=org_id, project_id=project_id, asset_type="tracked_excavator", code="BAGER-01", registration="", capacity_m3=1.0, status="available")
            truck1=Asset(id=str(uuid.uuid4()), organization_id=org_id, project_id=project_id, asset_type="dump_truck", code="KAMION-01", registration="", capacity_m3=10.0, status="available")
            truck2=Asset(id=str(uuid.uuid4()), organization_id=org_id, project_id=project_id, asset_type="dump_truck", code="KAMION-02", registration="", capacity_m3=10.0, status="available")
            db.add_all([excavator,truck1,truck2]); db.flush()
            db.commit()
    finally: db.close()

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session=Depends(get_db)):
    p=current_participant(request,db)
    if not p: return templates.TemplateResponse(request, "login.html", {"admin_configured":bool(ADMIN_PASSWORD)})
    return templates.TemplateResponse(request, "app.html", {"participant":p,"role_label":ROLE_LABELS.get(p.role,p.role)})

@app.post("/login")
def login(request: Request, password: str=Form(...), db: Session=Depends(get_db)):
    # Simple per-instance limiter. Production should use a shared gateway/rate limiter.
    addr = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _login_lock:
        attempts = _login_attempts[addr]
        while attempts and now - attempts[0] > LOGIN_WINDOW_SECONDS:
            attempts.popleft()
        if len(attempts) >= LOGIN_MAX_ATTEMPTS:
            raise HTTPException(429, "Прекалено много опити. Опитайте по-късно")
        if not ADMIN_PASSWORD or not secrets.compare_digest(password, ADMIN_PASSWORD):
            attempts.append(now)
            raise HTTPException(401, "Невалидна парола")
        attempts.clear()
    p=db.query(Participant).filter_by(role="dispatcher",status="active").first()
    if not p: raise HTTPException(500,"Липсва диспечерски профил")
    sid=secrets.token_urlsafe(32)
    db.add(WebSession(id=hashlib.sha256(sid.encode()).hexdigest(),participant_id=p.id,project_id=p.project_id,expires_at=utcnow()+timedelta(hours=SESSION_HOURS)))
    db.commit()
    r=RedirectResponse("/",status_code=303); r.set_cookie(COOKIE,hashlib.sha256(sid.encode()).hexdigest(),httponly=True,samesite="lax",secure=SECURE_COOKIE,max_age=SESSION_HOURS*3600); return r

@app.get("/join/{token}", response_class=HTMLResponse)
def join_preview(token: str, request: Request, db: Session=Depends(get_db)):
    # GET must not consume the token. Viber and other chat clients fetch previews.
    h = hashlib.sha256(token.encode()).hexdigest()
    inv = db.query(Invitation).filter_by(token_hash=h, revoked=False, used_at=None).first()
    if not inv or dt_utc(inv.expires_at) < utcnow():
        raise HTTPException(410, "Поканата е невалидна или изтекла")
    return templates.TemplateResponse(request, "join.html", {"token":token})

@app.post("/join/{token}")
def join(token: str, request: Request, db: Session=Depends(get_db)):
    h = hashlib.sha256(token.encode()).hexdigest()
    inv = db.query(Invitation).filter_by(token_hash=h, revoked=False, used_at=None).first()
    if not inv or dt_utc(inv.expires_at) < utcnow():
        raise HTTPException(410, "Поканата е невалидна или изтекла")
    # Conditional UPDATE prevents two clients consuming the same token concurrently.
    count = db.query(Invitation).filter_by(id=inv.id, revoked=False, used_at=None).update({"used_at": utcnow()}, synchronize_session=False)
    if count != 1:
        db.rollback()
        raise HTTPException(410, "Поканата вече е използвана")
    sid = secrets.token_urlsafe(32)
    db.add(WebSession(id=hashlib.sha256(sid.encode()).hexdigest(), participant_id=inv.participant_id, project_id=inv.project_id, expires_at=utcnow()+timedelta(hours=SESSION_HOURS)))
    db.commit()
    r=RedirectResponse("/",status_code=303)
    r.set_cookie(COOKIE,hashlib.sha256(sid.encode()).hexdigest(),httponly=True,samesite="lax",secure=SECURE_COOKIE,max_age=SESSION_HOURS*3600)
    return r

@app.post("/logout")
def logout(request: Request, db: Session=Depends(get_db)):
    sid=request.cookies.get(COOKIE)
    if sid: db.query(WebSession).filter_by(id=sid).delete(); db.commit()
    r=RedirectResponse("/",status_code=303); r.delete_cookie(COOKIE); return r

@app.get("/api/me")
def me(p: Participant=Depends(require_user),db:Session=Depends(get_db)):
    project=project_for(db,p); return {"id":p.id,"name":p.display_name,"role":p.role,"role_label":ROLE_LABELS.get(p.role,p.role),"project":{"id":project.id,"code":project.code,"name":project.name,"address":project.address}}

@app.get("/api/shift/status")
def shift_status(p: Participant=Depends(require_user), db: Session=Depends(get_db)):
    shift=get_open_shift(db,p)
    return {"active":shift is not None,"shift_id":shift.id if shift else None}

@app.post("/api/shift/start")
def shift_start(p:Participant=Depends(require_user),db:Session=Depends(get_db)):
    if get_open_shift(db,p): return {"ok":True,"message":"Смяната вече е активна"}
    asset=None
    if p.role=="operator": asset=db.get(Asset,p.asset_id) if p.asset_id else db.query(Asset).filter_by(project_id=p.project_id,asset_type="tracked_excavator").first()
    if p.role=="driver": asset=db.get(Asset,p.asset_id) if p.asset_id else db.query(Asset).filter_by(project_id=p.project_id,asset_type="dump_truck").order_by(Asset.code).first()
    s=Shift(id=str(uuid.uuid4()),organization_id=p.organization_id,project_id=p.project_id,participant_id=p.id,asset_id=asset.id if asset else None)
    db.add(s); event(db,p.organization_id,p.project_id,p.id,"shift.started","shift",s.id,{"asset_id":s.asset_id}); db.commit(); return {"ok":True,"shift_id":s.id}

@app.post("/api/shift/end")
def shift_end(p:Participant=Depends(require_user),db:Session=Depends(get_db)):
    s=get_open_shift(db,p)
    if not s: raise HTTPException(409,"Няма активна смяна")
    s.ended_at=utcnow(); s.status="closed"; event(db,p.organization_id,p.project_id,p.id,"shift.ended","shift",s.id); db.commit(); return {"ok":True}

@app.post("/api/gps")
def gps(point:GpsIn,p:Participant=Depends(require_user),db:Session=Depends(get_db)):
    if p.role not in ("driver","operator","site_manager","dispatcher"): raise HTTPException(403,"GPS не е разрешен за тази роля")
    # A retry can arrive after its shift has ended or its timestamp has aged out.
    # Acknowledge only the original participant's identical event before shift checks.
    if point.device_event_id:
        existing=db.query(GpsPoint).filter_by(device_event_id=point.device_event_id).first()
        if existing:
            if existing.participant_id != p.id or existing.organization_id != p.organization_id or existing.project_id != p.project_id:
                raise HTTPException(409,"GPS идентификаторът вече е използван")
            same=(existing.latitude==point.latitude and existing.longitude==point.longitude
                  and existing.accuracy_m==point.accuracy_m and existing.speed_mps==point.speed_mps
                  and existing.heading_deg==point.heading_deg
                  and (point.recorded_at is None or dt_utc(existing.recorded_at)==dt_utc(point.recorded_at)))
            if not same: raise HTTPException(409,"GPS идентификаторът е използван с различни данни")
            return {"ok":True,"duplicate":True}
    shift=get_open_shift(db,p)
    recorded=dt_utc(point.recorded_at) if point.recorded_at else utcnow()
    # Resolve the shift using measurement time to avoid attaching offline points to a newer shift.
    if shift and recorded < dt_utc(shift.started_at):
        shift=None
    if not shift:
        # Allow delayed offline sync only when the recorded time falls inside a recently closed shift.
        shift=db.query(Shift).filter(Shift.participant_id==p.id,Shift.status=="closed",Shift.started_at<=recorded,Shift.ended_at>=recorded).order_by(desc(Shift.started_at)).first()
    if not shift: raise HTTPException(409,"Няма активна смяна или валидна офлайн точка от приключена смяна")
    if recorded > utcnow()+timedelta(minutes=2) or recorded < utcnow()-timedelta(hours=48): raise HTTPException(422,"GPS времевият маркер е извън допустимия диапазон")
    aid=shift.asset_id
    ev_id=point.device_event_id or secrets.token_hex(16)
    gp=GpsPoint(organization_id=p.organization_id,project_id=p.project_id,participant_id=p.id,asset_id=aid,shift_id=shift.id,latitude=point.latitude,longitude=point.longitude,accuracy_m=point.accuracy_m,speed_mps=point.speed_mps,heading_deg=point.heading_deg,recorded_at=recorded,device_event_id=ev_id)
    db.add(gp); db.commit(); return {"ok":True,"received_at":gp.received_at.isoformat()}

@app.get("/api/gps/latest")
def gps_latest(p:Participant=Depends(require_roles("owner","dispatcher","site_manager")),db:Session=Depends(get_db)):
    people=db.query(Participant).filter_by(project_id=p.project_id,status="active").all(); out=[]
    for person in people:
        pt=db.query(GpsPoint).filter_by(participant_id=person.id).order_by(desc(GpsPoint.recorded_at)).first()
        if pt:
            age=(utcnow()-pt.received_at.replace(tzinfo=timezone.utc) if pt.received_at.tzinfo is None else utcnow()-pt.received_at).total_seconds()
            out.append({"participant":person.display_name,"role":person.role,"lat":pt.latitude,"lon":pt.longitude,"accuracy":pt.accuracy_m,"age_sec":int(age),"stale":age>90,"recorded_at":pt.recorded_at.isoformat()})
    return out

@app.get("/api/trips")
def trips(p:Participant=Depends(require_user),db:Session=Depends(get_db)):
    q=db.query(Trip).filter_by(project_id=p.project_id)
    if p.role=="driver": q=q.filter_by(driver_participant_id=p.id)
    rows=q.order_by(desc(Trip.created_at)).limit(100).all(); result=[]
    for t in rows:
        a=db.get(Asset,t.truck_asset_id); ticket=db.query(LoadTicket).filter_by(trip_id=t.id).first()
        result.append({"id":t.id,"trip_number":t.trip_number,"truck":a.code if a else "?","status":t.status,"volume_m3":ticket.volume_m3 if ticket else None,"created_at":t.created_at.isoformat()})
    return result

class NewTripIn(BaseModel):
    truck_asset_id: str | None = None

@app.get("/api/trips/assignments")
def trip_assignments(p:Participant=Depends(require_roles("owner","dispatcher","site_manager")),db:Session=Depends(get_db)):
    trucks=db.query(Asset).filter_by(project_id=p.project_id,asset_type="dump_truck").order_by(Asset.code).all()
    active_ids={t.truck_asset_id for t in db.query(Trip).filter_by(project_id=p.project_id).filter(Trip.status.notin_(["completed","cancelled"])).all()}
    drivers=db.query(Participant).filter_by(project_id=p.project_id,role="driver",status="active").all()
    return [{"truck_asset_id":a.id,"truck":a.code,"driver":next((d.display_name for d in drivers if d.asset_id==a.id),None),
             "available":a.id not in active_ids and any(d.asset_id==a.id for d in drivers),
             "reason":"Активен курс" if a.id in active_ids else ("Няма назначен шофьор" if not any(d.asset_id==a.id for d in drivers) else None)} for a in trucks]

@app.post("/api/trips/new")
def new_trip(data:NewTripIn | None=None,p:Participant=Depends(require_roles("owner","dispatcher","site_manager")),db:Session=Depends(get_db)):
    trucks=db.query(Asset).filter_by(project_id=p.project_id,asset_type="dump_truck").order_by(Asset.code).all()
    if data and data.truck_asset_id:
        trucks=[a for a in trucks if a.id==data.truck_asset_id]
        if not trucks: raise HTTPException(404,"Камионът не е намерен в този обект")
    active_ids={t.truck_asset_id for t in db.query(Trip).filter_by(project_id=p.project_id).filter(Trip.status.notin_(["completed","cancelled"])).all()}
    drivers=db.query(Participant).filter_by(project_id=p.project_id,role="driver",status="active").all()
    assignment=next(((a,d) for a in trucks if a.id not in active_ids for d in drivers if d.asset_id==a.id),None)
    if not assignment: raise HTTPException(409,"Няма свободна комбинация камион + назначен шофьор")
    truck,driver=assignment
    last=db.query(func.max(Trip.trip_number)).filter_by(project_id=p.project_id).scalar() or 0
    t=Trip(id=str(uuid.uuid4()),organization_id=p.organization_id,project_id=p.project_id,truck_asset_id=truck.id,driver_participant_id=driver.id,trip_number=last+1,status="queued",queued_at=utcnow())
    db.add(t); event(db,p.organization_id,p.project_id,p.id,"trip.created","trip",t.id,{"truck":truck.code,"driver":driver.display_name})
    try: db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(409,"Конфликт при създаване на курс. Обновете данните и опитайте отново.")
    return {"ok":True,"trip_id":t.id,"truck":truck.code,"driver":driver.display_name}

@app.post("/api/trips/{trip_id}/action")
def trip_action(trip_id:str,action:TripAction,p:Participant=Depends(require_user),db:Session=Depends(get_db)):
    t=db.get(Trip,trip_id)
    if not t or t.project_id!=p.project_id: raise HTTPException(404,"Курсът не е намерен")
    if p.role=="driver" and t.driver_participant_id!=p.id: raise HTTPException(403,"Този курс не е назначен на вас")
    if p.role not in ("driver","dispatcher","site_manager","owner"): raise HTTPException(403,"Нямате права")
    transitions={"queue":("queued","queued_at"),"loading_start":("loading","loading_started_at"),"loaded":("loaded","loaded_at"),"depart":("outbound",None),"arrived_disposal":("at_disposal","disposal_arrived_at"),"unloaded":("returning","unloaded_at"),"returned":("completed","returned_at")}
    if action.action not in transitions: raise HTTPException(400,"Непознато действие")
    status,field=transitions[action.action]
    allowed={"queued":["queue","loading_start"],"loading":["loaded"],"loaded":["depart"],"outbound":["arrived_disposal"],"at_disposal":["unloaded"],"returning":["returned"]}
    if action.action not in allowed.get(t.status,[]): raise HTTPException(409,f"Невалиден преход: {t.status} → {status}")
    if field: setattr(t,field,utcnow())
    t.status=status
    event(db,p.organization_id,p.project_id,p.id,"trip."+action.action,"trip",t.id,{"new_status":status}); db.commit(); return {"ok":True,"status":status}

@app.post("/api/load-ticket")
def load_ticket(data:TicketIn,p:Participant=Depends(require_roles("owner","dispatcher","operator","site_manager")),db:Session=Depends(get_db)):
    t=db.get(Trip,data.trip_id)
    if not t or t.project_id!=p.project_id: raise HTTPException(404,"Курсът не е намерен")
    if t.status not in ("loaded","outbound","at_disposal","returning","completed"): raise HTTPException(409,"Първо маркирайте курса като натоварен")
    if db.query(LoadTicket).filter_by(trip_id=t.id).first(): raise HTTPException(409,"За този курс вече има товарен билет")
    excavator=db.get(Asset,p.asset_id) if p.role=="operator" and p.asset_id else db.query(Asset).filter_by(project_id=p.project_id,asset_type="tracked_excavator").first()
    if p.role=="operator" and (not excavator or excavator.asset_type!="tracked_excavator"):
        raise HTTPException(403,"Операторът няма назначен багер")
    operator_person=p if p.role=="operator" else db.query(Participant).filter_by(project_id=p.project_id,role="operator",status="active").first()
    ticket=LoadTicket(id=str(uuid.uuid4()),organization_id=p.organization_id,project_id=p.project_id,trip_id=t.id,truck_asset_id=t.truck_asset_id,excavator_asset_id=excavator.id if excavator else "",operator_participant_id=operator_person.id if operator_person else p.id,volume_m3=data.volume_m3,volume_basis=data.volume_basis,confidence="confirmed" if p.role in ("operator","dispatcher","owner") else "estimated",confirmed_by=p.id if p.role in ("operator","dispatcher","owner") else None,confirmed_at=utcnow() if p.role in ("operator","dispatcher","owner") else None)
    db.add(ticket); db.add(Quantity(id=str(uuid.uuid4()),organization_id=p.organization_id,project_id=p.project_id,trip_id=t.id,quantity_type="loose_loaded_m3",quantity_value=data.volume_m3,method=data.volume_basis,verification_status="verified" if ticket.confidence=="confirmed" else "unverified")); event(db,p.organization_id,p.project_id,p.id,"load_ticket.created","load_ticket",ticket.id,{"trip_id":t.id,"volume_m3":data.volume_m3,"confidence":ticket.confidence}); db.commit(); return {"ok":True,"ticket_id":ticket.id,"confidence":ticket.confidence}

@app.get("/api/dashboard")
def dashboard(p:Participant=Depends(require_roles("owner","dispatcher","site_manager","client_viewer")),db:Session=Depends(get_db)):
    ts=db.query(Trip).filter_by(project_id=p.project_id).all(); tickets=db.query(LoadTicket).filter_by(project_id=p.project_id).all()
    confirmed=sum(x.volume_m3 for x in tickets if x.confidence=="confirmed")
    estimated=sum(x.volume_m3 for x in tickets if x.confidence!="confirmed")
    if p.role=="client_viewer":
        return {"project":project_for(db,p).name,"trips_total":len(ts),"trips_active":sum(1 for t in ts if t.status not in ("completed","cancelled")),"trips_completed":sum(1 for t in ts if t.status=="completed"),"confirmed_m3":round(confirmed,3),"estimated_m3":round(estimated,3),"gps_points":None,"trucks":[]}
    truck_rows=[]
    for a in db.query(Asset).filter_by(project_id=p.project_id,asset_type="dump_truck").all():
        t=db.query(Trip).filter_by(truck_asset_id=a.id).filter(Trip.status.notin_(["completed","cancelled"])).order_by(desc(Trip.created_at)).first()
        d=db.get(Participant,t.driver_participant_id) if t else None
        truck_rows.append({"code":a.code,"status":t.status if t else "available","driver":d.display_name if d else "—","trip":t.trip_number if t else None})
    gps_count=db.query(GpsPoint).filter_by(project_id=p.project_id).count()
    return {"project":project_for(db,p).name,"trips_total":len(ts),"trips_active":sum(1 for t in ts if t.status not in ("completed","cancelled")),"trips_completed":sum(1 for t in ts if t.status=="completed"),"confirmed_m3":round(confirmed,3),"estimated_m3":round(estimated,3),"gps_points":gps_count,"trucks":truck_rows}

@app.get("/api/operations")
def operations(p:Participant=Depends(require_roles("owner","dispatcher","site_manager")),db:Session=Depends(get_db)):
    """Auditable operational snapshot. Volume is loose loaded m³, not in-situ excavation."""
    now=utcnow()
    trips=db.query(Trip).filter_by(project_id=p.project_id).all()
    tickets={t.trip_id:t for t in db.query(LoadTicket).filter_by(project_id=p.project_id).all()}
    assets={a.id:a for a in db.query(Asset).filter_by(project_id=p.project_id).all()}
    people={d.id:d for d in db.query(Participant).filter_by(project_id=p.project_id).all()}
    gps={}
    for point in db.query(GpsPoint).filter_by(project_id=p.project_id).order_by(desc(GpsPoint.recorded_at)).all():
        if point.asset_id and point.asset_id not in gps:
            gps[point.asset_id]=point
    fleet=[]
    for asset in assets.values():
        if asset.asset_type!="dump_truck": continue
        assigned=next((d for d in people.values() if d.asset_id==asset.id and d.role=="driver" and d.status=="active"),None)
        active=next((t for t in trips if t.truck_asset_id==asset.id and t.status not in ("completed","cancelled")),None)
        pt=gps.get(asset.id)
        age=None
        if pt:
            received=pt.received_at.replace(tzinfo=timezone.utc) if pt.received_at.tzinfo is None else pt.received_at
            age=max(0,int((now-received).total_seconds()))
        ticket=tickets.get(active.id) if active else None
        fleet.append({"truck":asset.code,"driver":assigned.display_name if assigned else None,
                      "status":active.status if active else ("available" if assigned else "no_driver"),
                      "trip_number":active.trip_number if active else None,
                      "cargo_m3":ticket.volume_m3 if ticket else None,
                      "cargo_basis":ticket.volume_basis if ticket else None,
                      "gps":({"lat":pt.latitude,"lon":pt.longitude,"age_sec":age,"stale":age>90,"accuracy_m":pt.accuracy_m} if pt else None),
                      "completed_trips":sum(t.status=="completed" for t in trips if t.truck_asset_id==asset.id)})
    excavators=[]
    for asset in assets.values():
        if asset.asset_type!="tracked_excavator": continue
        linked=[ticket for ticket in tickets.values() if ticket.excavator_asset_id==asset.id]
        confirmed=sum(t.volume_m3 for t in linked if t.confidence=="confirmed")
        estimated=sum(t.volume_m3 for t in linked if t.confidence!="confirmed")
        # Only intervals with actual load tickets and timestamps; no fabricated working hours.
        times=[]
        timed_volume=0.0
        for ticket in linked:
            trip=next((t for t in trips if t.id==ticket.trip_id),None)
            if trip and trip.loading_started_at and trip.loaded_at:
                start=trip.loading_started_at.replace(tzinfo=timezone.utc) if trip.loading_started_at.tzinfo is None else trip.loading_started_at
                end=trip.loaded_at.replace(tzinfo=timezone.utc) if trip.loaded_at.tzinfo is None else trip.loaded_at
                if end>start:
                    times.append((start,end))
                    timed_volume+=ticket.volume_m3
        # Merge overlapping loading intervals to avoid double-counting machine time.
        merged=[]
        for start,end in sorted(times):
            if merged and start<=merged[-1][1]: merged[-1]=(merged[-1][0],max(merged[-1][1],end))
            else: merged.append((start,end))
        hours=sum((end-start).total_seconds() for start,end in merged)/3600
        excavators.append({"excavator":asset.code,"confirmed_loose_m3":round(confirmed,3),
                           "estimated_loose_m3":round(estimated,3),"ticket_count":len(linked),"timed_ticket_loose_m3":round(timed_volume,3),
                           "documented_loading_hours":round(hours,3),
                           "indicative_loading_m3_per_hour":round(timed_volume/hours,2) if hours>0 and timed_volume>0 else None,
                           "productivity_warning":"Само обем по товарни билети / отчетено време за товарене; не е реална производителност за цяла смяна."})
    return {"as_of":now.isoformat(),"volume_unit":"loose_loaded_m3","fleet":fleet,"excavators":excavators,
            "completed_trips":sum(t.status=="completed" for t in trips),
            "active_trips":sum(t.status not in ("completed","cancelled") for t in trips),
            "confirmed_loose_m3":round(sum(t.volume_m3 for t in tickets.values() if t.confidence=="confirmed"),3),
            "estimated_loose_m3":round(sum(t.volume_m3 for t in tickets.values() if t.confidence!="confirmed"),3)}


@app.get("/api/activity")
def activity(p:Participant=Depends(require_roles("owner","dispatcher","site_manager")),db:Session=Depends(get_db)):
    rows=db.query(Event).filter_by(project_id=p.project_id).order_by(desc(Event.recorded_at)).limit(30).all(); out=[]
    for e in rows:
        person=db.get(Participant,e.participant_id) if e.participant_id else None
        out.append({"time":e.recorded_at.isoformat(),"actor":person.display_name if person else "Система","type":e.event_type,"entity":e.entity_type,"payload":json.loads(e.payload_json or "{}")})
    return out

@app.post("/api/invitations")
def invite(data:InviteIn,p:Participant=Depends(require_roles("owner","dispatcher")),db:Session=Depends(get_db)):
    if data.role not in ("driver","operator","site_manager","client_viewer"): raise HTTPException(400,"Невалидна роля")
    if data.role in ("driver","operator"):
        expected="dump_truck" if data.role=="driver" else "tracked_excavator"
        if not data.asset_id or not db.query(Asset).filter_by(id=data.asset_id,project_id=p.project_id,asset_type=expected).first(): raise HTTPException(400,"Избери правилната машина за участника")
        if db.query(Participant).filter_by(project_id=p.project_id,role=data.role,asset_id=data.asset_id,status="active").first(): raise HTTPException(409,"Тази машина вече има активен участник с тази роля")
    pid=str(uuid.uuid4()); person=Participant(id=pid,organization_id=p.organization_id,project_id=p.project_id,display_name=data.display_name,phone=data.phone,role=data.role,asset_id=data.asset_id)
    token=secrets.token_urlsafe(32); inv=Invitation(id=str(uuid.uuid4()),organization_id=p.organization_id,project_id=p.project_id,participant_id=pid,token_hash=hashlib.sha256(token.encode()).hexdigest(),expires_at=utcnow()+timedelta(hours=24))
    db.add(person); db.add(inv); db.commit()
    return {"ok":True,"participant_id":pid,"invitation_id":inv.id,"invite_url":"/join/"+token,"expires_in_hours":24,"warning":"Изпратете линка само на конкретния участник. Линкът е еднократен."}

@app.post("/api/invitations/{invitation_id}/revoke")
def revoke_invitation(invitation_id:str,p:Participant=Depends(require_roles("owner","dispatcher")),db:Session=Depends(get_db)):
    inv=db.query(Invitation).filter_by(id=invitation_id,project_id=p.project_id).first()
    if not inv: raise HTTPException(404,"Поканата не е намерена")
    inv.revoked=True; db.commit(); return {"ok":True,"revoked":True}

@app.get("/api/assets")
def assets(p:Participant=Depends(require_roles("owner","dispatcher","site_manager")),db:Session=Depends(get_db)):
    return [{"id":a.id,"code":a.code,"type":a.asset_type} for a in db.query(Asset).filter_by(project_id=p.project_id).all()]

@app.get("/health")
def health(db: Session=Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Базата данни не отговаря")
    return {"status":"ok", "app":"BAGER SITE LINK", "version":"1.0.1", "database":"connected"}

@app.get("/manifest.webmanifest")
def manifest(): return JSONResponse({"name":"BAGER SITE LINK","short_name":"BAGER","start_url":"/","display":"standalone","background_color":"#0b1220","theme_color":"#111c2e","icons":[]})
