from fastapi.testclient import TestClient
from main import app
from app.models.game_state import GamePhase, ActionType
from .helpers import create_game_session, get_human_player, get_state

client = TestClient(app)

def test_sheriff_election():
    # 1. Create game
    _, state, session_id, headers = create_game_session(client)
    human_id = get_human_player(state)["id"]
    
    # 2. Advance to the sheriff election opening phase
    client.post(f"/api/player/{session_id}/action", headers=headers, json={
        "player_id": human_id, "type": ActionType.CONFIRM, "timestamp": 0
    })

    state = get_state(client, session_id, headers)
    assert state["phase"] == GamePhase.SHERIFF_ELECTION
    
    # 3. Run for Sheriff
    client.post(f"/api/player/{session_id}/action", headers=headers, json={
        "player_id": human_id, "type": ActionType.RUN_FOR_SHERIFF, "timestamp": 0
    })

    state = get_state(client, session_id, headers)
    assert state["phase"] in [GamePhase.SHERIFF_ELECTION, GamePhase.SHERIFF_SPEECH]
    assert human_id in state["sheriff_candidate_ids"]
