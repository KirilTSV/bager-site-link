"""Marketplace MVP acceptance checks (isolated DB fixture is configured by tests/run_isolated.py)."""
from fastapi.testclient import TestClient
from app.asgi import app

def test_marketplace_public_page_and_validation():
    with TestClient(app) as client:
        page=client.get("/market")
        assert page.status_code==200
        assert "Заяви изкоп" in page.text
        bad=client.post("/api/market/requests",json={"contact_name":"А","contact_phone":"123","site_area":"София","description":"кратко","service":"combined","consent":True})
        assert bad.status_code==422
        no_consent=client.post("/api/market/requests",json={"contact_name":"Тест Клиент","contact_phone":"0888000000","site_area":"София Лозенец","description":"Изкоп с извозване на земни маси","service":"combined","consent":False})
        assert no_consent.status_code==400

def test_marketplace_public_intake_and_private_admin():
    with TestClient(app) as client:
        inquiry=client.post("/api/market/requests",json={"contact_name":"Тест Клиент","contact_phone":"0888000000","site_area":"София Лозенец","description":"Изкоп и извозване на земни маси, достъп за камиони","estimated_m3":120,"service":"combined","consent":True})
        assert inquiry.status_code==201
        assert inquiry.json()["status"]=="received"
        partner=client.post("/api/market/partners",json={"company_name":"Тест Изпълнител","contact_phone":"0888111111","services":"Багери и камиони","service_area":"София","consent":True})
        assert partner.status_code==201
        assert partner.json()["status"]=="pending_verification"
        assert client.get("/api/market/admin").status_code==401
        assert client.post("/api/market/offers",json={"request_id":inquiry.json()["id"],"partner_id":partner.json()["id"],"price_bgn":5000}).status_code==401
