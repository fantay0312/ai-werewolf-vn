from fastapi.testclient import TestClient

from app.config import reload_config
from app.core.game_manager import game_manager
from app.infrastructure.runtime_metrics import runtime_metrics
from app.security import ADMIN_TOKEN_HEADER, PLAYER_TOKEN_HEADER
from main import app, rate_limiter
from .helpers import create_game_session

client = TestClient(app)


def test_create_game_rate_limit_returns_429_and_limit_headers(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("RATE_LIMIT_CREATE_GAME", "1")
    reload_config()
    rate_limiter.clear()

    try:
        first = client.post("/api/game/create", headers={"X-Forwarded-For": "203.0.113.10"})
        second = client.post("/api/game/create", headers={"X-Forwarded-For": "203.0.113.10"})

        assert first.status_code == 200
        assert second.status_code == 429
        assert 1 <= int(second.headers["Retry-After"]) <= 60
        assert second.headers["X-RateLimit-Limit"] == "1"
        assert second.headers["X-RateLimit-Remaining"] == "0"
        assert second.headers["X-RateLimit-Window"] == "60"
        assert second.json()["detail"] == "Too Many Requests"
        assert "request_id" in second.json()
    finally:
        rate_limiter.clear()
        monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)
        monkeypatch.delenv("RATE_LIMIT_WINDOW_SECONDS", raising=False)
        monkeypatch.delenv("RATE_LIMIT_CREATE_GAME", raising=False)
        reload_config()


def test_player_action_rate_limit_uses_player_token_bucket(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("RATE_LIMIT_PLAYER_ACTION", "1")
    reload_config()
    rate_limiter.clear()

    try:
        _, state, session_id, headers = create_game_session(client)
        human_player = next(player for player in state["players"] if player["is_human"])
        action = {
            "player_id": human_player["id"],
            "type": "confirm",
            "timestamp": 0,
        }

        first = client.post(f"/api/player/{session_id}/action", headers=headers, json=action)
        second = client.post(f"/api/player/{session_id}/action", headers=headers, json=action)

        assert first.status_code == 200
        assert second.status_code == 429
        assert second.headers["X-RateLimit-Limit"] == "1"
        assert second.headers["X-RateLimit-Remaining"] == "0"
    finally:
        rate_limiter.clear()
        monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)
        monkeypatch.delenv("RATE_LIMIT_WINDOW_SECONDS", raising=False)
        monkeypatch.delenv("RATE_LIMIT_PLAYER_ACTION", raising=False)
        reload_config()


def test_metrics_endpoint_exposes_runtime_and_business_series(monkeypatch):
    monkeypatch.setenv("BACKEND_ADMIN_TOKEN", "metrics-secret")
    monkeypatch.setenv("METRICS_ENABLED", "true")
    reload_config()
    rate_limiter.clear()
    runtime_metrics.clear()

    try:
        create_game_session(client)

        response = client.get(
            "/metrics",
            headers={ADMIN_TOKEN_HEADER: "metrics-secret"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert "# TYPE http_requests_total counter" in response.text
        assert "game_sessions_created_total" in response.text
        assert "active_games" in response.text
    finally:
        rate_limiter.clear()
        runtime_metrics.clear()
        monkeypatch.delenv("BACKEND_ADMIN_TOKEN", raising=False)
        monkeypatch.delenv("METRICS_ENABLED", raising=False)
        reload_config()


def test_persistence_round_trip_restores_runtime_state(monkeypatch, tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    monkeypatch.setenv("PERSIST_GAMES", "true")
    monkeypatch.setenv("GAME_SNAPSHOT_DIR", str(snapshot_dir))
    reload_config()
    rate_limiter.clear()
    runtime_metrics.clear()
    game_manager.reset_runtime_state(preserve_snapshots=False)

    try:
        _, _, session_id, headers = create_game_session(client)

        snapshot_file = next(snapshot_dir.glob("*.json"))
        assert snapshot_file.is_file()
        assert snapshot_file.name == f"{session_id}.json"

        game_manager.reset_runtime_state(preserve_snapshots=True)
        assert game_manager.get_game(session_id) is None

        restored = game_manager.restore_persisted_games()
        restored_game = game_manager.get_game(session_id)

        assert restored == 1
        assert restored_game is not None
        assert restored_game.session_id == session_id
        assert len(game_manager.get_domain_events(session_id)) >= 1

        response = client.get(
            f"/api/game/{session_id}",
            headers={
                PLAYER_TOKEN_HEADER: headers[PLAYER_TOKEN_HEADER],
            },
        )
        assert response.status_code == 200
        assert response.json()["session_id"] == session_id
    finally:
        game_manager.reset_runtime_state(preserve_snapshots=False)
        rate_limiter.clear()
        runtime_metrics.clear()
        monkeypatch.delenv("PERSIST_GAMES", raising=False)
        monkeypatch.delenv("GAME_SNAPSHOT_DIR", raising=False)
        reload_config()
