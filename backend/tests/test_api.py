"""HTTP-level tests. Require fastapi + httpx; skipped otherwise."""
import io

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402


@pytest.fixture()
def client(tmp_env, monkeypatch):
    from app import classifier as cl
    from app.main import app

    # Force 'model unavailable' so the test never needs a download.
    monkeypatch.setattr(cl.classifier, "load", lambda: (_ for _ in ()).throw(RuntimeError("no model")))
    with TestClient(app) as c:
        yield c


def png():
    b = io.BytesIO()
    Image.new("RGB", (120, 120), (50, 60, 70)).save(b, "PNG")
    return b.getvalue()


def test_full_flow_with_unavailable_model(client):
    r = client.post("/api/analyze", files={"file": ("a.png", png(), "image/png")})
    assert r.status_code == 200
    a = r.json()
    assert a["status"] == "unavailable" and a["suggested_category"] is None  # honest fallback
    body = dict(description="Wire hanging from the lab wall", building="science_lab",
                category="exposed_wire", upload_id=a["upload_id"])
    rep = client.post("/api/reports", json=body)
    assert rep.status_code == 201 and rep.json()["ai_status"] == "unavailable"
    assert client.get("/api/stats").json()["total"] == 1
    p = client.patch(f"/api/reports/{rep.json()['id']}", json={"status": "resolved"})
    assert p.status_code == 422
    assert client.get(rep.json()["image_url"]).status_code == 200


def test_validation_errors(client):
    assert client.post("/api/analyze", files={"file": ("a.txt", b"hi", "text/plain")}).status_code == 415
    assert client.post("/api/reports", json={"description": "short", "building": "x", "category": "y"}).status_code == 422
    assert client.get("/api/reports/12345").status_code == 404
    assert client.get("/api/images/..%2f..%2fetc%2fpasswd").status_code == 404
