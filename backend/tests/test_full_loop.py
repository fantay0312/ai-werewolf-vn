from fastapi.testclient import TestClient
from main import app
from app.models.game_state import GamePhase, ActionType, Role

client = TestClient(app)

def test_full_game_loop():
    # 1. Create game
    response = client.post("/api/game/create")
    assert response.status_code == 200
    data = response.json()
    session_id = data["session_id"]
    
    # Find human player
    human_id = next(p["id"] for p in data["players"] if p["is_human"])
    
    # 2. Advance from GAME_START to NIGHT_START -> NIGHT_WOLF_DISCUSS
    client.post(f"/api/player/{session_id}/action", json={
        "player_id": human_id, "type": ActionType.CONFIRM, "timestamp": 0
    })
    
    # 3. Simulate Wolf Discussion (3 rounds)
    # We need to find wolf players to act
    state = client.get(f"/api/game/{session_id}").json()
    wolves = [p for p in state["players"] if p["role"] in [Role.WOLF, Role.WOLF_KING]]
    
    for _ in range(3): # 3 rounds
        for wolf in wolves:
            client.post(f"/api/player/{session_id}/action", json={
                "player_id": wolf["id"], "type": ActionType.PASS, "timestamp": 0
            })
        # Check if advanced
        state = client.get(f"/api/game/{session_id}").json()
        
    assert state["phase"] == GamePhase.NIGHT_WOLF_VOTE
    
    # 4. Wolf Vote
    target_id = [p["id"] for p in state["players"] if p["role"] == Role.VILLAGER][0]
    for wolf in wolves:
        client.post(f"/api/player/{session_id}/action", json={
            "player_id": wolf["id"], "type": ActionType.KILL, "target_id": target_id, "timestamp": 0
        })
        
    state = client.get(f"/api/game/{session_id}").json()
    assert state["phase"] == GamePhase.NIGHT_SEER
    
    # 5. Seer Check
    seer = next(p for p in state["players"] if p["role"] == Role.SEER)
    client.post(f"/api/player/{session_id}/action", json={
        "player_id": seer["id"], "type": ActionType.CHECK, "target_id": target_id, "timestamp": 0
    })
    
    state = client.get(f"/api/game/{session_id}").json()
    assert state["phase"] == GamePhase.NIGHT_WITCH
    
    # 6. Witch Action (Pass)
    witch = next(p for p in state["players"] if p["role"] == Role.WITCH)
    client.post(f"/api/player/{session_id}/action", json={
        "player_id": witch["id"], "type": ActionType.PASS, "timestamp": 0
    })
    
    state = client.get(f"/api/game/{session_id}").json()
    assert state["phase"] == GamePhase.NIGHT_GUARD
    
    # 7. Guard Action (Pass)
    guard = next(p for p in state["players"] if p["role"] == Role.GUARD)
    client.post(f"/api/player/{session_id}/action", json={
        "player_id": guard["id"], "type": ActionType.PASS, "timestamp": 0
    })
    
    # Should auto-advance NIGHT_RESOLVE -> DAY_START -> DAY_DISCUSS
    state = client.get(f"/api/game/{session_id}").json()
    assert state["phase"] == GamePhase.DAY_DISCUSS
    
    # Check if target died
    dead_player = next(p for p in state["players"] if p["id"] == target_id)
    assert not dead_player["is_alive"]
