from fastapi.testclient import TestClient
from main import app
from .helpers import create_game_session

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "AI Werewolf VN Backend is running"
    assert data["status"] == "healthy"
    assert "version" in data

def test_create_game():
    payload, state, _, _ = create_game_session(client)
    assert "player_token" in payload
    assert "session_id" in state
    assert len(state["players"]) == 12
