from fastapi.testclient import TestClient
from main import app
from app.models.game_state import GamePhase, ActionType
from .helpers import create_game_session, get_human_player, get_state

client = TestClient(app)

def test_phase_transition():
    _, state, session_id, headers = create_game_session(client)
    player_id = get_human_player(state)["id"]

    # Initial phase should be GAME_START
    assert state["phase"] == GamePhase.GAME_START

    # Confirm to advance
    action = {
        "player_id": player_id,
        "type": ActionType.CONFIRM,
        "timestamp": 0
    }
    response = client.post(f"/api/player/{session_id}/action", headers=headers, json=action)
    assert response.status_code == 200

    # Check game state - should have advanced to a night phase
    # AI agents without LLM_API_KEY will use fallback PASS actions
    # so phases may advance quickly
    data = get_state(client, session_id, headers)

    # Game should be in one of the night phases
    night_phases = [
        GamePhase.SHERIFF_ELECTION,
        GamePhase.NIGHT_START,
        GamePhase.NIGHT_WOLF_DISCUSS,
        GamePhase.NIGHT_WOLF_VOTE,
        GamePhase.NIGHT_SEER,
        GamePhase.NIGHT_WITCH,
        GamePhase.NIGHT_GUARD,
        GamePhase.NIGHT_RESOLVE,
        GamePhase.DAY_START,
        GamePhase.DAY_LAST_WORDS,
    ]
    assert data["phase"] in [p.value for p in night_phases], f"Expected night phase, got {data['phase']}"
