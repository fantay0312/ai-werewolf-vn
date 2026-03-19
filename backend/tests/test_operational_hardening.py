from fastapi.testclient import TestClient

from app.config import reload_config
from app.security import ADMIN_TOKEN_HEADER
from main import app
from .helpers import create_game_session

client = TestClient(app)


def test_health_and_root_include_request_id_header():
    root_response = client.get("/", headers={"X-Request-ID": "root-request-id"})
    assert root_response.status_code == 200
    assert root_response.headers["X-Request-ID"] == "root-request-id"
    assert root_response.json()["status"] == "healthy"

    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert "X-Request-ID" in health_response.headers
    payload = health_response.json()
    assert payload["status"] == "healthy"
    assert "uptime_seconds" in payload
    assert "version" in payload


def test_readiness_reports_ready_in_test_env():
    response = client.get("/ready", headers={"X-Request-ID": "ready-request"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "ready-request"
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["checks"]["config_loaded"] is True
    assert payload["checks"]["game_manager_available"] is True
    assert payload["checks"]["admin_token_ready"] is True


def test_readiness_reports_degraded_when_production_admin_token_missing(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("BACKEND_ADMIN_TOKEN", raising=False)
    reload_config()
    try:
        response = client.get("/ready")

        assert response.status_code == 503
        payload = response.json()
        assert payload["status"] == "degraded"
        assert payload["checks"]["admin_token_ready"] is False
    finally:
        monkeypatch.setenv("ENV", "test")
        reload_config()


def test_error_responses_include_request_id():
    response = client.get(
        "/api/game/missing-session/replay",
        headers={
            ADMIN_TOKEN_HEADER: "test-admin",
            "X-Request-ID": "missing-replay-request",
        },
    )

    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == "missing-replay-request"
    payload = response.json()
    assert payload["detail"] == "Game not found"
    assert payload["request_id"] == "missing-replay-request"


def test_validation_errors_include_request_id():
    _, _, session_id, headers = create_game_session(client)
    response = client.post(
        f"/api/player/{session_id}/action",
        json={"player_id": 1},
        headers={**headers, "X-Request-ID": "invalid-action-request"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"] == "Validation Error"
    assert payload["request_id"] == "invalid-action-request"
    assert "errors" in payload
