from fastapi.testclient import TestClient
from main import app
from app.models.game_state import GamePhase, ActionType
from .helpers import create_game_session, get_human_player, get_state

client = TestClient(app)

def test_full_game_loop():
    _, state, session_id, headers = create_game_session(client)
    human_id = get_human_player(state)["id"]
    
    client.post(f"/api/player/{session_id}/action", headers=headers, json={
        "player_id": human_id, "type": ActionType.CONFIRM, "timestamp": 0
    })

    state = get_state(client, session_id, headers)
    public_state = get_state(client, session_id)

    assert state["phase"] not in [GamePhase.GAME_START]
    assert next(player for player in state["players"] if player["is_human"])["role"] != "unknown"
    assert all(not player["is_human"] for player in public_state["players"])
    assert any(player["role"] == "unknown" for player in public_state["players"] if player["is_alive"])
