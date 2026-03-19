from fastapi.testclient import TestClient

from app.security import PLAYER_TOKEN_HEADER


def create_game_session(client: TestClient):
    response = client.post("/api/game/create")
    assert response.status_code == 200
    payload = response.json()
    state = payload["state"]
    session_id = state["session_id"]
    headers = {PLAYER_TOKEN_HEADER: payload["player_token"]}
    return payload, state, session_id, headers


def get_state(client: TestClient, session_id: str, headers: dict | None = None):
    response = client.get(f"/api/game/{session_id}", headers=headers or {})
    assert response.status_code == 200
    return response.json()


def get_human_player(state: dict):
    return next(player for player in state["players"] if player["is_human"])
