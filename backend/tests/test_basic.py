from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "AI Werewolf VN Backend is running"
    assert data["status"] == "healthy"
    assert "version" in data

def test_create_game():
    response = client.post("/api/game/create")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert len(data["players"]) == 12
