import time
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import reload_config
from app.core.game_manager import GameManager, game_manager
from app.infrastructure.event_store import event_store
from app.infrastructure.runtime_metrics import runtime_metrics
from app.models.game_state import ActionType
from app.security import ADMIN_TOKEN_HEADER
from main import app, rate_limiter
from .helpers import create_game_session


client = TestClient(app)


@pytest.fixture
def runtime_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("BACKEND_ADMIN_TOKEN", "secret-token")
    monkeypatch.setenv("PERSIST_GAMES", "true")
    monkeypatch.setenv("GAME_SNAPSHOT_DIR", str(tmp_path))
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("RATE_LIMIT_CREATE_GAME", "2")
    monkeypatch.setenv("RATE_LIMIT_PLAYER_ACTION", "2")
    monkeypatch.setenv("RATE_LIMIT_ADMIN", "1")
    monkeypatch.setenv("METRICS_ENABLED", "true")
    monkeypatch.setenv("METRICS_REQUIRE_ADMIN", "true")
    reload_config()

    rate_limiter.clear()
    runtime_metrics.clear()
    game_manager.games.clear()
    game_manager.game_timestamps.clear()
    game_manager.player_tokens.clear()
    game_manager.ai_locks.clear()
    event_store.clear_all()

    yield tmp_path

    rate_limiter.clear()
    runtime_metrics.clear()
    game_manager.games.clear()
    game_manager.game_timestamps.clear()
    game_manager.player_tokens.clear()
    game_manager.ai_locks.clear()
    event_store.clear_all()
    reload_config()


def test_game_manager_persists_and_restores_snapshots(runtime_env):
    manager = GameManager()
    game = manager.create_game()
    session_id = game.session_id
    snapshot_files = list(Path(runtime_env).glob("*.json"))

    assert session_id in manager.games
    assert snapshot_files
    assert manager.get_domain_events(session_id)

    restored_manager = GameManager()

    assert session_id in restored_manager.games
    assert restored_manager.get_player_token(session_id) == manager.get_player_token(session_id)
    assert restored_manager.get_domain_events(session_id)

    restored_manager.game_timestamps[session_id] = time.time() - restored_manager.game_ttl - 10
    restored_manager._cleanup_old_games()

    assert session_id not in restored_manager.games
    assert not list(Path(runtime_env).glob("*.json"))


def test_create_game_endpoint_is_rate_limited(runtime_env):
    first = client.post("/api/game/create")
    second = client.post("/api/game/create")
    third = client.post("/api/game/create")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert 1 <= int(third.headers["Retry-After"]) <= 60

    payload = third.json()
    assert payload["detail"] == "Too Many Requests"
    assert "request_id" in payload


def test_metrics_endpoint_exports_runtime_counters(runtime_env):
    payload, _, session_id, headers = create_game_session(client)
    action_response = client.post(
        f"/api/player/{session_id}/action",
        headers=headers,
        json={"player_id": 999, "type": ActionType.CONFIRM.value, "timestamp": 0},
    )

    assert action_response.status_code == 200

    response = client.get(
        "/metrics",
        headers={ADMIN_TOKEN_HEADER: "secret-token"},
    )

    assert response.status_code == 200
    text = response.text
    assert '# TYPE http_requests_total counter' in text
    assert "/api/game/create" in text
    assert "/api/player/:session_id/action" in text
    assert "http_request_duration_seconds_count" in text
    assert re.search(r"game_sessions_created_total \d+", text)
    assert 'player_actions_total{action_type="confirm",result="accepted",source="human"} 1' in text
    assert "active_games 1" in text

    assert payload["player_token"] == headers["X-Player-Token"]
