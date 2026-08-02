from fastapi.testclient import TestClient
from app.app import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_missing_session():
    response = client.get("/emails")
    assert response.status_code == 401