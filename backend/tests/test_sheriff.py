from fastapi.testclient import TestClient
from main import app
from app.models.game_state import GamePhase, ActionType, Role

client = TestClient(app)

def test_sheriff_election():
    # 1. Create game
    response = client.post("/api/game/create")
    assert response.status_code == 200
    data = response.json()
    session_id = data["session_id"]
    
    # Find human player
    human_id = next(p["id"] for p in data["players"] if p["is_human"])
    
    # 2. Advance to SHERIFF_ELECTION (Day 1)
    # Start -> Night Start -> Night Wolf Discuss
    client.post(f"/api/player/{session_id}/action", json={
        "player_id": human_id, "type": ActionType.CONFIRM, "timestamp": 0
    })
    
    # Skip night phases (simulate by manually advancing or just running through)
    # For speed, let's just assume we can reach Day 1 via actions
    # Or we can cheat and set phase manually if we had a debug endpoint, but we don't.
    # So we must run through night.
    
    state = client.get(f"/api/game/{session_id}").json()
    wolves = [p for p in state["players"] if p["role"] in [Role.WOLF, Role.WOLF_KING]]
    
    # Wolf Discuss (3 rounds)
    for _ in range(3):
        for wolf in wolves:
            client.post(f"/api/player/{session_id}/action", json={
                "player_id": wolf["id"], "type": ActionType.PASS, "timestamp": 0
            })
        state = client.get(f"/api/game/{session_id}").json()
            
    # Wolf Vote
    target_id = [p["id"] for p in state["players"] if p["role"] == Role.VILLAGER][0]
    for wolf in wolves:
        client.post(f"/api/player/{session_id}/action", json={
            "player_id": wolf["id"], "type": ActionType.KILL, "target_id": target_id, "timestamp": 0
        })
        
    # Seer
    seer = next(p for p in state["players"] if p["role"] == Role.SEER)
    client.post(f"/api/player/{session_id}/action", json={
        "player_id": seer["id"], "type": ActionType.CHECK, "target_id": target_id, "timestamp": 0
    })
    
    # Witch
    witch = next(p for p in state["players"] if p["role"] == Role.WITCH)
    client.post(f"/api/player/{session_id}/action", json={
        "player_id": witch["id"], "type": ActionType.PASS, "timestamp": 0
    })
    
    # Guard
    guard = next(p for p in state["players"] if p["role"] == Role.GUARD)
    client.post(f"/api/player/{session_id}/action", json={
        "player_id": guard["id"], "type": ActionType.PASS, "timestamp": 0
    })
    
    # Should be DAY_START -> SHERIFF_ELECTION (auto-advance from DAY_START?)
    # DayStartHandler waits for CONFIRM.
    state = client.get(f"/api/game/{session_id}").json()
    assert state["phase"] == GamePhase.DAY_START
    
    client.post(f"/api/player/{session_id}/action", json={
        "player_id": human_id, "type": ActionType.CONFIRM, "timestamp": 0
    })
    
    state = client.get(f"/api/game/{session_id}").json()
    assert state["phase"] == GamePhase.SHERIFF_ELECTION
    
    # 3. Run for Sheriff
    # Human runs
    client.post(f"/api/player/{session_id}/action", json={
        "player_id": human_id, "type": ActionType.RUN_FOR_SHERIFF, "timestamp": 0
    })
    
    # Others pass
    for p in state["players"]:
        if p["id"] != human_id and p["is_alive"]:
            client.post(f"/api/player/{session_id}/action", json={
                "player_id": p["id"], "type": ActionType.PASS, "timestamp": 0
            })
            
    state = client.get(f"/api/game/{session_id}").json()
    assert state["phase"] == GamePhase.SHERIFF_SPEECH
    assert state["sheriff_candidate_ids"] == [human_id]
