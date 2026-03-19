import asyncio
from types import SimpleNamespace
from app.core.game_manager import game_manager
from app.models.action_model import ActionRequest
from app.models.game_state import GamePhase, ActionType
from unittest.mock import AsyncMock, Mock, patch

def test_ai_trigger():
    mock_completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"action": {"type": "pass"}}'))]
    )
    mock_client = Mock()
    mock_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=AsyncMock(return_value=mock_completion))
    )

    def _fake_create_task(coro):
        coro.close()
        return Mock()

    with patch("app.ai.agent.get_llm_config") as mock_llm_config, patch(
        "app.ai.agent.AsyncOpenAI"
    ) as mock_openai, patch("app.core.game_manager.asyncio.create_task", side_effect=_fake_create_task) as mock_create_task:
        mock_llm_config.return_value = SimpleNamespace(
            api_key="test-key",
            api_base=None,
            model="unit-test-model",
        )
        mock_openai.return_value = mock_client

        game = game_manager.create_game()
        session_id = game.session_id
        human_id = next(player.id for player in game.players if player.is_human)

        success, error = asyncio.run(
            game_manager.process_action(
                session_id,
                ActionRequest(
                    player_id=human_id,
                    type=ActionType.CONFIRM,
                ),
            )
        )
        assert success, error

        state = game_manager.get_game(session_id)
        assert state is not None
        assert state.phase == GamePhase.SHERIFF_ELECTION

        asyncio.run(game_manager.trigger_ai_actions(session_id))

        state = game_manager.get_game(session_id)
        assert state is not None
        assert any(
            event.name == "ai_decision_recorded"
            for event in game_manager.get_domain_events(session_id)
        )
        assert mock_openai.called
        assert mock_client.chat.completions.create.await_count >= 1
        assert mock_create_task.called
