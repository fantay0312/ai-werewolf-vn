from app.application.projections.private_view_projector import PrivateViewProjector
from app.application.projections.public_view_projector import PublicViewProjector
from app.models.game_state import GameLog, GamePhase, GameState, Player, Role


def _player(player_id: int, role: Role) -> Player:
    return Player(
        id=player_id,
        name=f"{player_id}号玩家",
        role=role,
        portrait=f"/images/portraits/{role.value}.webp",
    )


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


def test_private_projection_shows_owner_skill_usage_and_only_owner_live_vote():
    game = _sensitive_game(GamePhase.DAY_VOTE)
    witch = game.players[0]

    view = PrivateViewProjector().project(game, witch)

    own_view = next(player for player in view.players if player.id == witch.id)
    hunter_view = next(player for player in view.players if player.role == "unknown")
    assert own_view.role == Role.WITCH
    assert own_view.poison_used is True
    assert own_view.antidote_used is True
    assert hunter_view.gun_used is False
    assert view.votes == {witch.id: game.votes[witch.id]}


def test_hidden_roles_also_hide_role_named_portraits():
    game = _sensitive_game(GamePhase.DAY_DISCUSS)
    witch = game.players[0]

    public_view = PublicViewProjector().project(game)
    private_view = PrivateViewProjector().project(game, witch)

    assert all(player.portrait == "" for player in public_view.players)
    assert private_view.players[0].portrait == witch.portrait
    assert all(player.portrait == "" for player in private_view.players[1:])


def test_night_has_acted_is_visible_only_for_private_viewer():
    game = _sensitive_game(GamePhase.NIGHT_WITCH)
    witch, hunter, _ = game.players
    witch.has_acted = True
    hunter.has_acted = True

    public_view = PublicViewProjector().project(game)
    private_view = PrivateViewProjector().project(game, witch)

    assert all(player.has_acted is False for player in public_view.players)
    assert private_view.players[0].has_acted is True
    assert all(player.has_acted is False for player in private_view.players[1:])

    game.phase = GamePhase.DAY_DISCUSS
    day_view = PublicViewProjector().project(game)
    assert [player.has_acted for player in day_view.players] == [True, True, False]


def test_active_vote_projections_show_only_private_viewers_own_ballot():
    game = _sensitive_game(GamePhase.DAY_VOTE)
    witch, hunter, villager = game.players

    assert PublicViewProjector().project(game).votes == {}
    assert PrivateViewProjector().project(game, witch).votes == {witch.id: 2}
    assert PrivateViewProjector().project(game, hunter).votes == {hunter.id: 1}
    assert PrivateViewProjector().project(game, villager).votes == {}

    game.phase = GamePhase.SHERIFF_VOTE
    assert PrivateViewProjector().project(game, witch).votes == {witch.id: 2}

    game.phase = GamePhase.DAY_PK_VOTE
    assert PublicViewProjector().project(game).pk_votes == {}
    assert PrivateViewProjector().project(game, villager).pk_votes == {villager.id: 1}


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
    assert [player.portrait for player in view.players] == [
        player.portrait for player in game.players
    ]
