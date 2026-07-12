from app.application.projections.private_view_projector import PrivateViewProjector
from app.application.projections.public_view_projector import PublicViewProjector
from app.models.game_state import GameLog, GamePhase, GameState, Player, Role


def _player(player_id: int, role: Role) -> Player:
    return Player(id=player_id, name=f"{player_id}号玩家", role=role, portrait="")


def _sensitive_game(phase: GamePhase) -> GameState:
    witch = _player(1, Role.WITCH)
    witch.poison_used = True
    witch.antidote_used = True
    hunter = _player(2, Role.HUNTER)
    hunter.gun_used = True
    villager = _player(3, Role.VILLAGER)
    return GameState(
        session_id=f"projection-{phase.value.lower()}",
        day=2,
        phase=phase,
        players=[witch, hunter, villager],
        votes={1: 2, 2: 1},
        pk_votes={3: 1},
    )


def test_public_projection_hides_live_votes_roles_and_skill_usage():
    game = _sensitive_game(GamePhase.DAY_VOTE)
    game.game_logs.append(GameLog(
        id="legacy-public-live-vote",
        day=2,
        phase=GamePhase.DAY_VOTE,
        content="2号完成投票",
        player_id=2,
        is_public=True,
        data={"event": "day_vote_cast", "voter_id": 2, "target_id": 1},
    ))

    view = PublicViewProjector().project(game)

    assert view.votes == {}
    assert all(player.role == "unknown" for player in view.players)
    assert all(not player.poison_used for player in view.players)
    assert all(not player.antidote_used for player in view.players)
    assert all(not player.gun_used for player in view.players)
    assert all(log.id != "legacy-public-live-vote" for log in view.game_logs)


def test_private_projection_shows_only_owner_skill_usage_and_hides_live_votes():
    game = _sensitive_game(GamePhase.DAY_VOTE)
    witch = game.players[0]

    view = PrivateViewProjector().project(game, witch)

    own_view = next(player for player in view.players if player.id == witch.id)
    hunter_view = next(player for player in view.players if player.role == "unknown")
    assert own_view.role == Role.WITCH
    assert own_view.poison_used is True
    assert own_view.antidote_used is True
    assert hunter_view.gun_used is False
    assert view.votes == {}


def test_vote_details_appear_only_in_result_projection():
    day_game = _sensitive_game(GamePhase.DAY_VOTE_RESULT)
    pk_game = _sensitive_game(GamePhase.DAY_PK_RESULT)

    assert PublicViewProjector().project(day_game).votes == day_game.votes
    assert PublicViewProjector().project(pk_game).pk_votes == pk_game.pk_votes


def test_game_end_projection_fully_reveals_roles_and_skill_usage():
    game = _sensitive_game(GamePhase.GAME_END)

    view = PublicViewProjector().project(game)

    assert [player.role for player in view.players] == [Role.WITCH, Role.HUNTER, Role.VILLAGER]
    assert view.players[0].poison_used is True
    assert view.players[0].antidote_used is True
    assert view.players[1].gun_used is True
