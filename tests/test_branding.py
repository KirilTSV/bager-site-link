"""Brand asset and shared shell regression checks."""
from fastapi.testclient import TestClient
from app.asgi import app


def test_brand_logo_is_served_and_present_for_all_roles():
    with TestClient(app) as client:
        asset = client.get("/static/bager-site-link-logo.jpg")
        assert asset.status_code == 200
        assert asset.headers["content-type"].startswith("image/jpeg")
        assert asset.content[:3] == bytes([255, 216, 255])
        login = client.get("/")
        assert login.status_code == 200
        assert '/static/bager-site-link-logo.jpg' in login.text
        assert client.post("/login", data={"password": "ci-test-only"}, follow_redirects=False).status_code == 303
        home = client.get("/")
        assert home.status_code == 200
        assert '<header class="topbar">' in home.text
        assert 'class="brand-logo small"' in home.text
        assert 'id="operationsPanel"' in home.text
        assert 'id="equipmentPanel"' in home.text
        assert 'id="equipmentList"' in home.text
        assert 'id="assignmentForm"' in home.text
        assert 'class="main-nav"' in home.text
        assert 'BAGER <span class="brand-accent">SITE LINK</span>' in home.text
        assert '/static/bager-site-link-logo.jpg' in home.text
