import asyncio

from fastapi.testclient import TestClient

from main import app
from app.core.game_manager import GameManager, game_manager
from app.core.handlers.hunter_skill import HunterSkillHandler
from app.core.handlers.night_resolve import NightResolveHandler
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, GamePhase, Role
from .helpers import create_game_session, get_human_player


client = TestClient(app)


def test_day_vote_rejects_invalid_target():
    _, state, session_id, headers = create_game_session(client)
    human_id = get_human_player(state)["id"]

    game = game_manager.get_game(session_id)
    game.phase = GamePhase.DAY_VOTE
    for player in game.players:
        player.has_acted = False

    response = client.post(f"/api/player/{session_id}/action", headers=headers, json={
        "player_id": human_id,
        "type": ActionType.VOTE,
        "target_id": 999,
        "timestamp": 0,
    })

    assert response.status_code == 400


def test_wolf_vote_allows_teammate_target():
    gm = GameManager()
    game = gm.create_game()
    game.phase = GamePhase.NIGHT_WOLF_VOTE
    wolves = [p for p in game.players if p.role in (Role.WOLF, Role.WOLF_KING)]
    assert len(wolves) >= 2

    success, error = asyncio.run(
        gm.process_action(
            game.session_id,
            ActionRequest(
                player_id=wolves[0].id,
                type=ActionType.KILL,
                target_id=wolves[1].id,
            ),
        )
    )

    assert success is True, error
    assert game.votes[wolves[0].id] == wolves[1].id


def test_poisoned_hunter_is_not_selected_as_shooter():
    gm = GameManager()
    game = gm.create_game()
    hunter = game.players[0]
    wolf_king = game.players[1]
    hunter.role = Role.HUNTER
    wolf_king.role = Role.WOLF_KING

    for player in game.players:
        player.is_alive = True
        player.gun_used = False
        player.poisoned_by_witch = False
        player.killed_by_wolf = False

    hunter.poisoned_by_witch = True
    wolf_king.killed_by_wolf = True
    game.wolf_kill_target = wolf_king.id
    game.phase = GamePhase.NIGHT_RESOLVE

    resolve_handler = NightResolveHandler(gm, game)
    resolve_handler.on_enter()
    assert resolve_handler.try_advance() == GamePhase.HUNTER_SKILL

    skill_handler = HunterSkillHandler(gm, game)
    shooter = skill_handler._find_shooter()

    assert shooter is not None
    assert shooter.id == wolf_king.id
