import pytest
import asyncio
from fastapi.testclient import TestClient
from main import app
from app.models.game_state import GamePhase, ActionType, Role
from unittest.mock import AsyncMock, patch

client = TestClient(app)

@pytest.mark.asyncio
async def test_ai_trigger():
    # Mock OpenAI to avoid real API calls and speed up tests
    with patch("app.ai.agent.AsyncOpenAI") as mock_openai:
        # Setup mock response
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client

        # Mock chat completion
        mock_completion = AsyncMock()
        mock_completion.choices = [
            AsyncMock(message=AsyncMock(content='{"action": {"type": "pass"}}'))
        ]
        mock_client.chat.completions.create.return_value = mock_completion

        # 1. Create game
        response = client.post("/api/game/create")
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]

        # 2. Human confirms to start game
        human_id = next(p["id"] for p in data["players"] if p["is_human"])
        client.post(f"/api/player/{session_id}/action", json={
            "player_id": human_id, "type": ActionType.CONFIRM, "timestamp": 0
        })

        # 3. After GAME_START confirm, game goes to SHERIFF_ELECTION (Day 1 flow).
        #    AI agents may also act asynchronously (pass for election),
        #    so game could be in SHERIFF_ELECTION or further along.
        state = client.get(f"/api/game/{session_id}").json()

        # Acceptable phases: SHERIFF_ELECTION, SHERIFF_SPEECH, SHERIFF_VOTE,
        # or NIGHT phases if all AI passed quickly
        acceptable_phases = [
            GamePhase.SHERIFF_ELECTION,
            GamePhase.SHERIFF_SPEECH,
            GamePhase.SHERIFF_VOTE,
            GamePhase.NIGHT_START,
            GamePhase.NIGHT_WOLF_DISCUSS,
            GamePhase.NIGHT_WOLF_VOTE,
        ]
        assert state["phase"] in [p.value for p in acceptable_phases], \
            f"Unexpected phase: {state['phase']}"

        print(f"Current Phase: {state['phase']}")

        # Verify game is progressing (logs were generated)
        logs = state["game_logs"]
        assert len(logs) > 0, "Expected some game logs after confirming"
