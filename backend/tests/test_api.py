from fastapi.testclient import TestClient
from app.main import app


def test_health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_reject_non_pdf():
    response = TestClient(app).post(
        "/analyze", files={"file": ("notes.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 415


def test_reject_invalid_pdf():
    response = TestClient(app).post(
        "/analyze", files={"file": ("fake.pdf", b"%PDF-not-a-pdf", "application/pdf")}
    )
    assert response.status_code == 400
