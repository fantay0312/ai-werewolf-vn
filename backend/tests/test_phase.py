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

    # Check game state - should have advanced past GAME_START
    # Day 1 flow: GAME_START -> SHERIFF_ELECTION -> (SHERIFF_SPEECH/VOTE) -> NIGHT
    # AI agents without LLM_API_KEY use fallback PASS, so phases may advance quickly
    response = client.get(f"/api/game/{session_id}")
    data = response.json()

    acceptable_phases = [
        GamePhase.SHERIFF_ELECTION,
        GamePhase.SHERIFF_SPEECH,
        GamePhase.SHERIFF_VOTE,
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
    assert data["phase"] in [p.value for p in acceptable_phases], \
        f"Expected post-start phase, got {data['phase']}"
