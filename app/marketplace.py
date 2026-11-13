"""Independent earthworks marketplace MVP. No escrow, agency authority or contract execution."""
import uuid, re, threading, time
from collections import defaultdict, deque
from datetime import datetime, timezone
from html import escape
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, Session
from .db import Base, get_db

router = APIRouter()
_lock=threading.Lock()
_hits=defaultdict(deque)

def now(): return datetime.now(timezone.utc)

class MarketRequest(Base):
    __tablename__="site_link_market_requests"
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    contact_name: Mapped[str]=mapped_column(String(120))
    contact_phone: Mapped[str]=mapped_column(String(50))
    site_area: Mapped[str]=mapped_column(String(160))
    description: Mapped[str]=mapped_column(Text)
    estimated_m3: Mapped[float|None]=mapped_column(Float,nullable=True)
    service: Mapped[str]=mapped_column(String(40))
    status: Mapped[str]=mapped_column(String(30),default="new")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class MarketPartner(Base):
    __tablename__="site_link_market_partners"
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    company_name: Mapped[str]=mapped_column(String(160))
    contact_phone: Mapped[str]=mapped_column(String(50))
    services: Mapped[str]=mapped_column(String(200))
    service_area: Mapped[str]=mapped_column(String(160))
    status: Mapped[str]=mapped_column(String(30),default="unverified")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class MarketOffer(Base):
    __tablename__="site_link_market_offers"
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    request_id: Mapped[str]=mapped_column(String(36),ForeignKey("site_link_market_requests.id"),index=True)
    partner_id: Mapped[str]=mapped_column(String(36),ForeignKey("site_link_market_partners.id"))
    price_bgn: Mapped[float]=mapped_column(Float)
    notes: Mapped[str]=mapped_column(Text,default="")
    status: Mapped[str]=mapped_column(String(30),default="proposed")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class RequestIn(BaseModel):
    contact_name: str=Field(min_length=2,max_length=120)
    contact_phone: str=Field(min_length=6,max_length=50)
    site_area: str=Field(min_length=3,max_length=160)
    description: str=Field(min_length=12,max_length=2000)
    estimated_m3: float|None=Field(default=None,gt=0,le=1000000)
    service: str=Field(pattern="^(excavation|haulage|combined)$")
    consent: bool
    website: str="" # honeypot

class PartnerIn(BaseModel):
    company_name: str=Field(min_length=2,max_length=160)
    contact_phone: str=Field(min_length=6,max_length=50)
    services: str=Field(min_length=3,max_length=200)
    service_area: str=Field(min_length=3,max_length=160)
    consent: bool
    website: str=""

class OfferIn(BaseModel):
    request_id: str
    partner_id: str
    price_bgn: float=Field(gt=0,le=100000000)
    notes: str=Field(default="",max_length=2000)

def limit(request):
    ip=request.client.host if request.client else "unknown"
    with _lock:
        q=_hits[ip]; t=time.monotonic()
        while q and q[0]<t-3600:q.popleft()
        if len(q)>=6:raise HTTPException(429,"Прекалено много заявки. Опитайте по-късно.")
        q.append(t)

@router.get("/market",response_class=HTMLResponse)
def market():
    return """<!doctype html><html lang="bg"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BAGER SITE LINK — Заявки за земни работи</title><style>body{font:16px system-ui;background:#f5f7f7;color:#17312a;margin:0}main{max-width:700px;margin:40px auto;padding:22px}section{background:white;padding:24px;border-radius:14px;margin:20px 0}input,textarea,select,button{display:block;box-sizing:border-box;width:100%;padding:12px;margin:10px 0;border:1px solid #aaa;border-radius:7px;font:inherit}button{background:#157347;color:white;cursor:pointer}label{display:block;margin:14px 0}label input[type=checkbox]{width:auto;display:inline}small{color:#54675d}.hidden{display:none}</style></head><body><main><h1>BAGER SITE LINK</h1><p>Свързваме възложители с независими изпълнители на изкопни работи и извозване в София и околността. Не сме страна по договорите между тях.</p><section><h2>Заяви изкоп или извозване</h2><form id="request"><input name="contact_name" placeholder="Име за контакт" required minlength="2"><input name="contact_phone" placeholder="Телефон" required minlength="6"><input name="site_area" placeholder="Район / адрес на обекта" required><select name="service"><option value="combined">Изкоп и извозване</option><option value="excavation">Само изкоп</option><option value="haulage">Само извозване</option></select><input name="estimated_m3" type="number" min="0.1" step="any" placeholder="Приблизителни m³ (незадължително)"><textarea name="description" required minlength="12" placeholder="Опишете обекта, достъпа и сроковете"></textarea><input name="website" class="hidden" tabindex="-1" autocomplete="off"><label><input name="consent" type="checkbox" required> Съгласен съм данните ми да се използват за обработка на запитването и контакт с подходящи изпълнители.</label><button>Изпрати заявка</button></form><p id="requestResult" role="status"></p></section><section><h2>Регистрация на изпълнител</h2><form id="partner"><input name="company_name" placeholder="Фирма / име" required><input name="contact_phone" placeholder="Телефон" required><input name="services" placeholder="Багери, камиони, извозване, депа" required><input name="service_area" placeholder="Обслужван район" required><input name="website" class="hidden" tabindex="-1" autocomplete="off"><label><input name="consent" type="checkbox" required> Съгласен съм да бъда потърсен за проверка и потенциални заявки.</label><button>Кандидатствай</button></form><p id="partnerResult" role="status"></p></section><small>Заявките не са гаранция за оферта или сключен договор. Не се извършват плащания през платформата. За права по личните данни и изтриване се свържете с оператора на платформата.</small></main><script>for(const kind of ['request','partner'])document.getElementById(kind).addEventListener('submit',async e=>{e.preventDefault();const form=e.target;const obj=Object.fromEntries(new FormData(form));obj.consent=form.elements.consent.checked;if(kind==='request')obj.estimated_m3=obj.estimated_m3?Number(obj.estimated_m3):null;const out=document.getElementById(kind+'Result');try{const res=await fetch('/api/market/'+kind+'s',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)});const data=await res.json();if(!res.ok)throw Error(typeof data.detail==='string'?data.detail:'Невалидни данни');out.textContent='Получено. Номер на заявката: '+data.id;form.reset()}catch(err){out.textContent='Грешка: '+err.message}})</script></body></html>"""

@router.post("/api/market/requests",status_code=201)
def create_request(data:RequestIn,request:Request,db:Session=Depends(get_db)):
    limit(request)
    if not data.consent or data.website:raise HTTPException(400,"Невалидна заявка")
    row=MarketRequest(id=str(uuid.uuid4()),contact_name=data.contact_name.strip(),contact_phone=data.contact_phone.strip(),site_area=data.site_area.strip(),description=data.description.strip(),estimated_m3=data.estimated_m3,service=data.service)
    db.add(row);db.commit()
    return {"id":row.id,"status":"received"}

@router.post("/api/market/partners",status_code=201)
def create_partner(data:PartnerIn,request:Request,db:Session=Depends(get_db)):
    limit(request)
    if not data.consent or data.website:raise HTTPException(400,"Невалидна заявка")
    row=MarketPartner(id=str(uuid.uuid4()),company_name=data.company_name.strip(),contact_phone=data.contact_phone.strip(),services=data.services.strip(),service_area=data.service_area.strip())
    db.add(row);db.commit()
    return {"id":row.id,"status":"pending_verification"}

def admin(request:Request,db:Session):
    from .main import current_participant
    p=current_participant(request,db)
    if not p:raise HTTPException(401,"Влезте в системата")
    if p.role not in ("owner","dispatcher"):raise HTTPException(403,"Нямате достъп")
    return p

@router.get("/api/market/admin")
def market_admin(request:Request,db:Session=Depends(get_db)):
    admin(request,db)
    requests=db.query(MarketRequest).order_by(MarketRequest.created_at.desc()).limit(100).all()
    partners=db.query(MarketPartner).order_by(MarketPartner.created_at.desc()).limit(100).all()
    offers=db.query(MarketOffer).order_by(MarketOffer.created_at.desc()).limit(100).all()
    return {"requests":[{"id":r.id,"contact_name":r.contact_name,"contact_phone":r.contact_phone,"site_area":r.site_area,"description":r.description,"estimated_m3":r.estimated_m3,"service":r.service,"status":r.status} for r in requests],"partners":[{"id":p.id,"company_name":p.company_name,"contact_phone":p.contact_phone,"services":p.services,"service_area":p.service_area,"status":p.status} for p in partners],"offers":[{"id":o.id,"request_id":o.request_id,"partner_id":o.partner_id,"price_bgn":o.price_bgn,"status":o.status} for o in offers]}

@router.post("/api/market/offers",status_code=201)
def create_offer(data:OfferIn,request:Request,db:Session=Depends(get_db)):
    admin(request,db)
    if not db.get(MarketRequest,data.request_id) or not db.get(MarketPartner,data.partner_id):
        raise HTTPException(404,"Заявка или изпълнител не съществува")
    row=MarketOffer(id=str(uuid.uuid4()),request_id=data.request_id,partner_id=data.partner_id,price_bgn=data.price_bgn,notes=data.notes)
    db.add(row);db.commit()
    return {"id":row.id,"status":"proposed"}
