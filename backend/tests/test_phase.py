from fastapi.testclient import TestClient
from main import app
from app.models.game_state import GamePhase, ActionType

client = TestClient(app)

def test_phase_transition():
    # Create game
    response = client.post("/api/game/create")
    assert response.status_code == 200
    data = response.json()
    session_id = data["session_id"]
    player_id = next(p["id"] for p in data["players"] if p["is_human"])

    # Initial phase should be GAME_START
    assert data["phase"] == GamePhase.GAME_START

    # Confirm to advance
    action = {
        "player_id": player_id,
        "type": ActionType.CONFIRM,
        "timestamp": 0
    }
    response = client.post(f"/api/player/{session_id}/action", json=action)
    assert response.status_code == 200

    # Check game state - should have advanced to a night phase
    # AI agents without LLM_API_KEY will use fallback PASS actions
    # so phases may advance quickly
    response = client.get(f"/api/game/{session_id}")
    data = response.json()

    # Game should be in one of the night phases
    night_phases = [
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
