from fastapi.testclient import TestClient
from main import app
from app.models.game_state import GamePhase, ActionType, Role

client = TestClient(app)


def _get_state(session_id):
    return client.get(f"/api/game/{session_id}").json()


def _action(session_id, player_id, action_type, target_id=None):
    payload = {"player_id": player_id, "type": action_type, "timestamp": 0}
    if target_id is not None:
        payload["target_id"] = target_id
    return client.post(f"/api/player/{session_id}/action", json=payload)


def _all_pass(session_id, state, predicate=None):
    """Have players matching predicate PASS. Default: all alive."""
    for p in state["players"]:
        if not p["is_alive"]:
            continue
        if predicate and not predicate(p):
            continue
        _action(session_id, p["id"], ActionType.PASS)


def test_full_game_loop():
    # 1. Create game
    response = client.post("/api/game/create")
    assert response.status_code == 200
    data = response.json()
    session_id = data["session_id"]

    human_id = next(p["id"] for p in data["players"] if p["is_human"])

    # 2. Confirm game start -> SHERIFF_ELECTION
    _action(session_id, human_id, ActionType.CONFIRM)

    state = _get_state(session_id)

    # 3. Handle sheriff election (all pass -> no sheriff)
    if state["phase"] == GamePhase.SHERIFF_ELECTION:
        _all_pass(session_id, state)
        state = _get_state(session_id)

    # By now we should be in night phases (possibly advanced by AI)
    wolves = [p for p in state["players"] if p["role"] in [Role.WOLF, Role.WOLF_KING]]

    # 4. Wolf discuss (3 rounds) - skip if already past
    if state["phase"] == GamePhase.NIGHT_WOLF_DISCUSS:
        for _ in range(3):
            for wolf in wolves:
                _action(session_id, wolf["id"], ActionType.PASS)
        state = _get_state(session_id)

    # 5. Wolf vote - may already be past if AI acted
    if state["phase"] == GamePhase.NIGHT_WOLF_VOTE:
        target_id = [p["id"] for p in state["players"] if p["role"] == Role.VILLAGER][0]
        for wolf in wolves:
            _action(session_id, wolf["id"], ActionType.KILL, target_id)
        state = _get_state(session_id)

    # 6-8. Night skill phases - AI may auto-advance through these
    # Seer (if human is seer, act; otherwise AI handles it)
    seer = next(p for p in state["players"] if p["role"] == Role.SEER)
    if state["phase"] == GamePhase.NIGHT_SEER:
        villager_id = [p["id"] for p in state["players"] if p["role"] == Role.VILLAGER and p["is_alive"]][0]
        _action(session_id, seer["id"], ActionType.CHECK, villager_id)
        state = _get_state(session_id)

    # Witch
    witch = next(p for p in state["players"] if p["role"] == Role.WITCH)
    if state["phase"] == GamePhase.NIGHT_WITCH:
        _action(session_id, witch["id"], ActionType.PASS)
        state = _get_state(session_id)

    # Guard
    guard = next(p for p in state["players"] if p["role"] == Role.GUARD)
    if state["phase"] == GamePhase.NIGHT_GUARD:
        _action(session_id, guard["id"], ActionType.PASS)
        state = _get_state(session_id)

    # After night resolve, game should be in a day phase
    # NightResolve increments day and auto-advances to DAY_START,
    # which auto-advances further based on conditions.
    day_or_skill_phases = [
        GamePhase.NIGHT_RESOLVE,
        GamePhase.DAY_START,
        GamePhase.DAY_LAST_WORDS,
        GamePhase.DAY_DISCUSS,
        GamePhase.HUNTER_SKILL,
        GamePhase.SHERIFF_TRANSFER,
        GamePhase.SHERIFF_ELECTION,
    ]
    assert state["phase"] in [p.value for p in day_or_skill_phases], \
        f"Expected day/resolve phase, got {state['phase']}"

    # Verify at least one player died during the night
    dead_players = [p for p in state["players"] if not p["is_alive"]]
    assert len(dead_players) >= 1, "Expected at least one death after night"
