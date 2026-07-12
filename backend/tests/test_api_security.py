from fastapi.testclient import TestClient

from app.config import reload_config
from app.core.game_manager import game_manager
from app.models.game_state import ActionType, GameLog, GamePhase, Role
from app.security import ADMIN_TOKEN_HEADER
from main import app
from .helpers import create_game_session, get_human_player, get_state

client = TestClient(app)


def test_public_game_state_hides_private_information():
    _, state, session_id, headers = create_game_session(client)
    human = get_human_player(state)
    game = game_manager.get_game(session_id)
    game.game_logs.append(GameLog(
        id="private-log",
        day=game.day,
        phase=GamePhase.DAY_DISCUSS,
        content="secret for me",
        player_id=human["id"],
        is_public=False,
    ))

    viewer_state = get_state(client, session_id, headers)
    public_state = get_state(client, session_id)

    assert next(player for player in viewer_state["players"] if player["is_human"])["role"] != "unknown"
    assert all(not player["is_human"] for player in public_state["players"])
    assert any(player["role"] == "unknown" for player in public_state["players"] if player["is_alive"])
    assert all("ai_memory" not in player for player in public_state["players"])
    assert any(log["content"] == "secret for me" for log in viewer_state["game_logs"])
    assert all(log["content"] != "secret for me" for log in public_state["game_logs"])


def test_player_action_requires_token():
    _, state, session_id, headers = create_game_session(client)
    human = get_human_player(state)
    action = {
        "player_id": human["id"],
        "type": ActionType.CONFIRM,
        "timestamp": 0,
    }

    response = client.post(f"/api/player/{session_id}/action", json=action)
    assert response.status_code == 403

    response = client.post(
        f"/api/player/{session_id}/action",
        headers={"X-Player-Token": "bad-token"},
        json=action,
    )
    assert response.status_code == 403

    response = client.post(f"/api/player/{session_id}/action", headers=headers, json=action)
    assert response.status_code == 200


def test_night_secret_fields_are_not_exposed_to_wrong_viewer():
    _, state, session_id, headers = create_game_session(client)
    game = game_manager.get_game(session_id)
    human = next(player for player in game.players if player.is_human)
    human.role = Role.VILLAGER
    game.phase = GamePhase.NIGHT_WITCH
    game.wolf_kill_target = 7

    viewer_state = get_state(client, session_id, headers)
    public_state = get_state(client, session_id)

    assert viewer_state["wolf_kill_target"] is None
    assert public_state["wolf_kill_target"] is None


def test_game_state_endpoint_hides_other_skill_state_and_live_votes():
    _, state, session_id, headers = create_game_session(client)
    game = game_manager.get_game(session_id)
    human = next(player for player in game.players if player.is_human)
    other_players = [player for player in game.players if player.id != human.id]
    witch = other_players[0]
    hunter = other_players[1]
    human.role = Role.VILLAGER
    witch.role = Role.WITCH
    witch.poison_used = True
    witch.antidote_used = True
    hunter.role = Role.HUNTER
    hunter.gun_used = True
    game.phase = GamePhase.DAY_VOTE
    game.votes = {human.id: witch.id, witch.id: human.id}

    viewer_state = get_state(client, session_id, headers)
    public_state = get_state(client, session_id)

    assert viewer_state["votes"] == {str(human.id): witch.id}
    assert public_state["votes"] == {}

    for payload in (viewer_state, public_state):
        projected_witch = next(player for player in payload["players"] if player["id"] == witch.id)
        projected_hunter = next(player for player in payload["players"] if player["id"] == hunter.id)
        assert projected_witch["role"] == "unknown"
        assert projected_witch["portrait"] == ""
        assert projected_witch["poison_used"] is False
        assert projected_witch["antidote_used"] is False
        assert projected_hunter["role"] == "unknown"
        assert projected_hunter["portrait"] == ""
        assert projected_hunter["gun_used"] is False


def test_config_requires_admin_token_when_set(monkeypatch):
    monkeypatch.setenv("BACKEND_ADMIN_TOKEN", "secret-token")
    try:
        response = client.get("/api/config/llm")
        assert response.status_code == 403

        response = client.get(
            "/api/config/llm",
            headers={ADMIN_TOKEN_HEADER: "secret-token"},
        )
        assert response.status_code == 200
    finally:
        monkeypatch.delenv("BACKEND_ADMIN_TOKEN", raising=False)
        reload_config()


def test_replay_api_requires_admin_token(monkeypatch):
    _, _, session_id, _ = create_game_session(client)
    monkeypatch.setenv("BACKEND_ADMIN_TOKEN", "secret-token")
    try:
        response = client.get(f"/api/game/{session_id}/replay")
        assert response.status_code == 403

        response = client.get(
            f"/api/game/{session_id}/replay",
            headers={ADMIN_TOKEN_HEADER: "wrong-token"},
        )
        assert response.status_code == 403

        response = client.get(
            f"/api/game/{session_id}/replay",
            headers={ADMIN_TOKEN_HEADER: "secret-token"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["game_id"] == session_id
        assert isinstance(payload["frames"], list)
        assert payload["frames"][0]["event_name"] == "game_created"
    finally:
        monkeypatch.delenv("BACKEND_ADMIN_TOKEN", raising=False)
        reload_config()


def test_eval_api_requires_admin_token(monkeypatch):
    _, _, session_id, _ = create_game_session(client)
    monkeypatch.setenv("BACKEND_ADMIN_TOKEN", "secret-token")
    try:
        response = client.get(f"/api/game/{session_id}/eval")
        assert response.status_code == 403

        response = client.get(
            f"/api/game/{session_id}/eval",
            headers={ADMIN_TOKEN_HEADER: "wrong-token"},
        )
        assert response.status_code == 403

        response = client.get(
            f"/api/game/{session_id}/eval",
            headers={ADMIN_TOKEN_HEADER: "secret-token"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["game_id"] == session_id
        assert payload["total_events"] >= 1
        assert payload["ai_decisions"] >= 0
    finally:
        monkeypatch.delenv("BACKEND_ADMIN_TOKEN", raising=False)
        reload_config()


def test_replay_and_eval_return_404_for_missing_session(monkeypatch):
    missing_session_id = "missing-session"
    monkeypatch.setenv("BACKEND_ADMIN_TOKEN", "secret-token")
    try:
        replay_response = client.get(
            f"/api/game/{missing_session_id}/replay",
            headers={ADMIN_TOKEN_HEADER: "secret-token"},
        )
        assert replay_response.status_code == 404
        assert replay_response.json()["detail"] == "Game not found"

        eval_response = client.get(
            f"/api/game/{missing_session_id}/eval",
            headers={ADMIN_TOKEN_HEADER: "secret-token"},
        )
        assert eval_response.status_code == 404
        assert eval_response.json()["detail"] == "Game not found"
    finally:
        monkeypatch.delenv("BACKEND_ADMIN_TOKEN", raising=False)
        reload_config()


def test_replay_and_eval_handle_existing_session_with_empty_event_stream(monkeypatch):
    _, _, session_id, _ = create_game_session(client)
    game_manager.event_store.clear(session_id)
    monkeypatch.setenv("BACKEND_ADMIN_TOKEN", "secret-token")
    try:
        replay_response = client.get(
            f"/api/game/{session_id}/replay",
            headers={ADMIN_TOKEN_HEADER: "secret-token"},
        )
        assert replay_response.status_code == 200
        replay_payload = replay_response.json()
        assert replay_payload == {
            "game_id": session_id,
            "frames": [],
        }

        eval_response = client.get(
            f"/api/game/{session_id}/eval",
            headers={ADMIN_TOKEN_HEADER: "secret-token"},
        )
        assert eval_response.status_code == 200
        eval_payload = eval_response.json()
        assert eval_payload == {
            "game_id": session_id,
            "total_events": 0,
            "ai_decisions": 0,
            "fallback_decisions": 0,
            "illegal_action_rate": 0.0,
            "fallback_rate": 0.0,
        }
    finally:
        monkeypatch.delenv("BACKEND_ADMIN_TOKEN", raising=False)
        reload_config()
